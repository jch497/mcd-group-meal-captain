"""企业团餐指挥官：把散落的 MCP 工具编排成一个工作流。

典型链路：
  delivery-query-stores(beType=6) → 选门店
  → query-meal-assistance(beType=6) → 选助餐服务(强约束：GMS002/003 需提前4h)
  → query-meals(beType=6) → 选套餐
  → query-promotions(beType=6) → 看满折规则
  → calculate-price(beType=6, gmServiceCode) → 算价 + 临界补差寻优
  → create-order(beType=6, gmServiceCode) → 下单

离线模式：从 fixtures/ 加载真实接口返回的样例数据，无需 Token 即可演示全链路。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from .client import MCDMCPClient, group_base
from .models import (
    GroupPlan,
    GroupPlanLine,
    MealAssistance,
    PriceItem,
    Promotion,
    Store,
)
from .optimizer import (
    estimate_discount_rate,
    optimize_live,
    parse_price_result,
    validate_assistance,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_FIXTURES = os.path.join(os.path.dirname(_HERE), "fixtures")


@dataclass
class FixtureBundle:
    stores: list[Store] = field(default_factory=list)
    assist: list[MealAssistance] = field(default_factory=list)
    promotions: list[Promotion] = field(default_factory=list)
    menu_raw: dict = field(default_factory=dict)

    @classmethod
    def load(cls, fixtures_dir: str = _DEFAULT_FIXTURES) -> "FixtureBundle":
        b = cls()

        def _jd(name):
            p = os.path.join(fixtures_dir, name)
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            return {}

        stores = _jd("delivery-query-stores.json").get("data") or []
        b.stores = [Store.from_dict(s) for s in stores]

        assist_data = _jd("query-meal-assistance.json").get("data") or {}
        b.assist = [
            MealAssistance.from_dict(a)
            for a in assist_data.get("mealAssistanceItems", [])
        ]

        promos = _jd("query-promotions.json").get("data") or []
        b.promotions = [Promotion.from_dict(p) for p in promos]

        b.menu_raw = _jd("query-meals.json")
        return b


class GroupMealAssistant:
    """团餐指挥官核心类。"""

    def __init__(self, client: Optional[MCDMCPClient] = None, fixtures_dir: str = _DEFAULT_FIXTURES):
        self.client = client
        self.fixtures_dir = fixtures_dir
        self._fixtures = FixtureBundle.load(fixtures_dir) if os.path.isdir(fixtures_dir) else None
        self.store: Optional[Store] = None
        self.assistance: Optional[MealAssistance] = None

    # ----------------------------- 数据获取 ----------------------------- #
    def fetch_stores(self, address_id: str) -> list[Store]:
        if self.client:
            r = self.client.call_tool(
                "delivery-query-stores", {"addressId": address_id, "beType": 6}
            )
            if r.ok:
                self._fixtures = self._fixtures or FixtureBundle()
                self._fixtures.stores = [
                    Store.from_dict(s) for s in (r.data.get("data") or [])
                ]
        return self._fixtures.stores if self._fixtures else []

    def fetch_assistance(self, store: Store) -> list[MealAssistance]:
        if self.client:
            r = self.client.call_tool("query-meal-assistance", group_base(store.store_code, store.be_code))
            if r.ok:
                items = (r.data.get("data") or {}).get("mealAssistanceItems", [])
                self._fixtures.assist = [MealAssistance.from_dict(a) for a in items]
        return self._fixtures.assist if self._fixtures else []

    def fetch_promotions(self, store: Store) -> list[Promotion]:
        if self.client:
            r = self.client.call_tool("query-promotions", group_base(store.store_code, store.be_code))
            if r.ok:
                self._fixtures.promotions = [Promotion.from_dict(p) for p in (r.data.get("data") or [])]
        return self._fixtures.promotions if self._fixtures else []

    # ----------------------------- 选品/算价 ----------------------------- #
    def select_store(self, index: int = 0) -> Optional[Store]:
        if self._fixtures and self._fixtures.stores:
            self.store = self._fixtures.stores[min(index, len(self._fixtures.stores) - 1)]
        return self.store

    def select_assistance(self, gm_service_code: str) -> Optional[MealAssistance]:
        if self._fixtures:
            for a in self._fixtures.assist:
                if a.gm_service_code == gm_service_code:
                    self.assistance = a
                    return a
        return None

    def calculate(
        self,
        items: list[PriceItem],
        unit_price: float = 26.0,
        reservation_date: Optional[str] = None,
    ) -> dict:
        """算价：实时优先，离线降级到近似估算。"""
        if self.store is None:
            self.select_store(0)
        if self.assistance is None and self._fixtures and self._fixtures.assist:
            self.assistance = next((a for a in self._fixtures.assist if a.available_now), None)

        # 助餐服务约束校验（离线也能做）
        constraints: dict = {"ok": True, "warnings": [], "errors": []}
        gms_code = ""
        if self.assistance:
            gms_code = self.assistance.gm_service_code
            constraints = validate_assistance(self.assistance, reservation_date)

        if self.client and self.store and gms_code and not constraints["errors"]:
            return optimize_live(
                self.client,
                self.store.store_code,
                self.store.be_code,
                items,
                gms_code,
                reservation_date,
                unit_price,
            )

        # 离线近似
        subtotal = sum(it.quantity * unit_price for it in items)
        rate, note = estimate_discount_rate(subtotal)
        payable = round(subtotal * rate, 2)
        return {
            "ok": True,
            "offline": True,
            "offline_note": note,
            "subtotal": round(subtotal, 2),
            "payable": payable,
            "discount_rate": rate,
            "balance_yuan": None,
            "next_rate": None,
            "topup": {
                "reached_top": False,
                "message": "离线模式无法获取实时下一档差额，请配置 MCD_MCP_TOKEN 后使用实时补差寻优。",
                "add_yuan": 0.0,
                "add_items": 0,
            },
            "constraints": constraints,
        }

    # ----------------------------- 计划生成 ----------------------------- #
    def build_plan(
        self,
        headcount: int,
        per_person_budget: float,
        unit_price: float = 26.0,
    ) -> GroupPlan:
        """按人均预算生成团餐组合（贪心：每人 1 份主餐 + 按需加小食/饮料）。"""
        budget = headcount * per_person_budget
        # 默认组合：每人 1 份单价 unit_price 的主餐
        per_person_qty = max(1, int(per_person_budget // unit_price))
        lines = [
            GroupPlanLine(
                product_code="521316",
                name="团餐主餐（参考品）",
                quantity=per_person_qty * headcount,
                unit_price=unit_price,
            )
        ]
        total_qty = sum(l.quantity for l in lines)
        subtotal = sum(l.quantity * l.unit_price for l in lines)
        notes = []
        if subtotal < budget:
            notes.append(f"当前组合 ¥{subtotal:.0f}，预算余 ¥{budget - subtotal:.0f}，可再加小食/饮料提升档位。")
        else:
            notes.append(f"当前组合 ¥{subtotal:.0f} 已超预算 ¥{budget:.0f}，建议减少份数或换低价品。")
        return GroupPlan(
            headcount=headcount,
            per_person_budget=per_person_budget,
            lines=lines,
            total_quantity=total_qty,
            subtotal=round(subtotal, 2),
            notes=notes,
        )


def plan_to_items(plan: GroupPlan, product_code: str = "521316") -> list[PriceItem]:
    return [PriceItem(product_code=product_code, quantity=plan.total_quantity)]
