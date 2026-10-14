"""企业团餐指挥官 CLI（同时也是 WorkBuddy 可调用的创意 Skill 入口）。

用法示例：
  # 离线演示（无需 Token，使用 fixtures 真实样例）
  python -m mcd_group_meal.cli plan --headcount 30 --budget 30
  python -m mcd_group_meal.cli price --qty 20 --unit 26

  # 实时模式（需环境变量 MCD_MCP_TOKEN）
  export MCD_MCP_TOKEN=xxxx
  python -m mcd_group_meal.cli stores --address 1036729580159600382506293145
  python -m mcd_group_meal.cli optimize --store 1990562 --qty 20 --unit 26 --gms GMS001
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .client import MCDMCPClient
from .models import PriceItem
from .planner import GroupMealAssistant


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_stores(a: GroupMealAssistant, args) -> None:
    stores = a.fetch_stores(args.address)
    out = [
        {"storeName": s.store_name, "storeCode": s.store_code, "beCode": s.be_code,
         "reservation": s.reservation}
        for s in stores
    ]
    _print({"count": len(out), "stores": out})


def cmd_assist(a: GroupMealAssistant, args) -> None:
    if a.store is None:
        a.select_store(0)
    assists = a.fetch_assistance(a.store)
    out = [
        {"code": x.gm_service_code, "name": x.gm_service_name,
         "enable": x.available_now, "needsBooking": x.needs_advance_booking,
         "reason": x.unusable_reason}
        for x in assists
    ]
    _print(out)


def cmd_promos(a: GroupMealAssistant, args) -> None:
    if a.store is None:
        a.select_store(0)
    promos = a.fetch_promotions(a.store)
    out = [
        {"id": p.promotion_id, "gms": p.gm_service_code,
         "discount": p.discount, "thresholdYuan": p.threshold_yuan}
        for p in promos
    ]
    _print(out)


def cmd_price(a: GroupMealAssistant, args) -> None:
    items = [PriceItem(product_code=args.product, quantity=args.qty)]
    res = a.calculate(items, unit_price=args.unit, reservation_date=args.reservation)
    _print(res)


def cmd_optimize(a: GroupMealAssistant, args) -> None:
    a.select_store(0)
    a.select_assistance(args.gms)
    items = [PriceItem(product_code=args.product, quantity=args.qty)]
    res = a.calculate(items, unit_price=args.unit, reservation_date=args.reservation)
    _print(res)


def cmd_plan(a: GroupMealAssistant, args) -> None:
    plan = a.build_plan(args.headcount, args.budget, unit_price=args.unit)
    out = {
        "headcount": plan.headcount,
        "perPersonBudget": plan.per_person_budget,
        "lines": [
            {"productCode": l.product_code, "name": l.name, "quantity": l.quantity,
             "unitPrice": l.unit_price}
            for l in plan.lines
        ],
        "totalQuantity": plan.total_quantity,
        "subtotal": plan.subtotal,
        "notes": plan.notes,
    }
    _print(out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mcd-group-meal-captain", description="麦当劳企业团餐指挥官")
    p.add_argument("--offline", action="store_true", help="强制离线模式（使用 fixtures，无需 Token）")
    p.add_argument("--fixtures", default=None, help="fixtures 目录路径")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("stores", help="查询团餐可配送门店")
    sp.add_argument("--address", default="1036729580159600382506293145")
    sp.set_defaults(func=cmd_stores)

    sp = sub.add_parser("assist", help="查询助餐服务")
    sp.set_defaults(func=cmd_assist)

    sp = sub.add_parser("promos", help="查询团餐满折规则")
    sp.set_defaults(func=cmd_promos)

    sp = sub.add_parser("price", help="计算团餐价格")
    sp.add_argument("--qty", type=int, default=20)
    sp.add_argument("--unit", type=float, default=26.0)
    sp.add_argument("--product", default="521316")
    sp.add_argument("--reservation", default=None)
    sp.set_defaults(func=cmd_price)

    sp = sub.add_parser("optimize", help="阶梯折扣临界补差寻优")
    sp.add_argument("--qty", type=int, default=20)
    sp.add_argument("--unit", type=float, default=26.0)
    sp.add_argument("--product", default="521316")
    sp.add_argument("--gms", default="GMS001")
    sp.add_argument("--reservation", default=None)
    sp.set_defaults(func=cmd_optimize)

    sp = sub.add_parser("plan", help="按人均预算生成团餐组合")
    sp.add_argument("--headcount", type=int, default=30)
    sp.add_argument("--budget", type=float, default=30.0)
    sp.add_argument("--unit", type=float, default=26.0)
    sp.set_defaults(func=cmd_plan)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    offline = args.offline or not os.environ.get("MCD_MCP_TOKEN")
    client = None
    if not offline:
        try:
            client = MCDMCPClient()
        except Exception as e:  # noqa: BLE001
            print(f"[warn] 无法初始化 MCP 客户端（{e}），回退离线模式。", file=sys.stderr)
            offline = True
    a = GroupMealAssistant(client=client, fixtures_dir=args.fixtures or "fixtures")
    if offline:
        print("[mode] 离线演示模式（fixtures 真实样例）\n", file=sys.stderr)
    args.func(a, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
