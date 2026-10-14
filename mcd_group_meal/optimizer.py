"""企业团餐优化器：阶梯折扣临界补差寻优 + 助餐服务约束校验。

核心差异点（相对榜单已有团餐类作品）：
1. 团餐阶梯折扣由服务端在 calculate-price 返回，绝大多数作品只展示价格；
   本工具读取返回的 `enjoyable` 预言机，反推「再加多少就能升到下一档折扣」，
   实现真正的「临界补差寻优」(threshold top-up optimization)。
2. 助餐服务 GMS002/GMS003（专人分餐/摆台）需提前 4 小时预约，
   calculate-price 会强校验（错误码 600062），本工具在算价前即给出约束提示。
"""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from .client import MCDMCPClient, ToolError, group_base
from .models import (
    MealAssistance,
    PriceItem,
    PriceResult,
)

# 离线参考锚点：基于真实 calculate-price 实测（beType=6, GMS001）反推的阶梯。
# 注意：这是离线近似，实时模式以 MCP 返回的 enjoyable 预言机为准。
_OFFLINE_ANCHORS = [
    (260.0, 0.78),
    (520.0, 0.74),
    (1000.0, 0.70),
]
_OFFLINE_FLOOR = 0.65  # 离线估算下限（折率不会低于 65 折）


def estimate_discount_rate(amount: float) -> tuple[float, str]:
    """离线估算当前订单折率（近似）。返回 (rate, note)。

    rate=0.78 表示当前约 78 折（即支付 78% 原价）。
    """
    if amount <= 0:
        return 1.0, "金额为 0，无折扣"
    pts = sorted(_OFFLINE_ANCHORS, key=lambda x: x[0])
    if amount <= pts[0][0]:
        note = f"离线近似：低于 {pts[0][0]:.0f} 元，约 {pts[0][1] * 100:.0f} 折档"
        return pts[0][1], note
    if amount >= pts[-1][0]:
        note = f"离线近似：超过 {pts[-1][0]:.0f} 元，约 {_OFFLINE_FLOOR * 100:.0f} 折（封底）"
        return _OFFLINE_FLOOR, note
    for i in range(len(pts) - 1):
        a0, r0 = pts[i]
        a1, r1 = pts[i + 1]
        if a0 <= amount <= a1:
            ratio = (amount - a0) / (a1 - a0)
            rate = r0 + (r1 - r0) * ratio
            note = f"离线近似：{a0:.0f}~{a1:.0f} 元区间，约 {rate * 100:.1f} 折"
            return round(rate, 4), note
    return pts[-1][1], "离线近似"


def parse_price_result(raw: dict, items_subtotal: float = 0.0) -> PriceResult:
    """将 calculate-price 的原始返回归一化为 PriceResult。

    不同版本返回结构略有差异，这里做容错解析：
    - 优先取 data.orderPrice / data.payable / data.realDiscount / data.enjoyable
    """
    res = PriceResult(raw=raw)
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    if not data and isinstance(raw.get("data"), list) and raw["data"]:
        data = raw["data"][0]

    res.subtotal = float(data.get("subtotal") or data.get("orderPrice") or items_subtotal)
    res.payable = float(data.get("payable") or data.get("payAmount") or res.subtotal)

    rd = data.get("realDiscount")
    if rd is not None:
        # realDiscount 可能为 '7.8'（折）或 0.78
        try:
            v = float(rd)
            res.discount_rate = v / 10.0 if v > 1 else v
        except (TypeError, ValueError):
            pass

    enjoy = data.get("enjoyable") or {}
    if isinstance(enjoy, dict):
        bal = enjoy.get("balance")
        if bal is not None:
            try:
                res.balance_points = int(bal)
            except (TypeError, ValueError):
                pass
        nr = enjoy.get("realDiscount") or enjoy.get("nextDiscount")
        if nr is not None:
            try:
                v = float(nr)
                res.next_rate = v / 10.0 if v > 1 else v
            except (TypeError, ValueError):
                pass
    return res


def suggest_topup(
    balance_points: int,
    unit_price: float,
    current_rate: Optional[float] = None,
    next_rate: Optional[float] = None,
) -> dict:
    """临界补差寻优：根据距下一档的差额，给出最低补单建议。

    返回结构化建议，供 CLI / Skill 展示。
    """
    if balance_points <= 0:
        return {
            "reached_top": True,
            "message": "已处于最优折扣档，无需补单。",
            "add_yuan": 0.0,
            "add_items": 0,
        }
    gap_yuan = balance_points / 100.0
    add_items = max(1, round(gap_yuan / unit_price)) if unit_price > 0 else 0
    save_rate = (current_rate or 1.0) - (next_rate or (current_rate or 1.0) * 0.96)
    save_pct = f"{save_rate * 100:.1f}%" if save_rate > 0 else "未知"
    return {
        "reached_top": False,
        "message": (
            f"再加约 ¥{gap_yuan:.0f}（≈{add_items} 份单价 ¥{unit_price:.0f} 商品）"
            f"即可升入下一档折扣，预计再省 {save_pct}。"
        ),
        "add_yuan": round(gap_yuan, 2),
        "add_items": add_items,
        "next_rate": next_rate,
    }


def validate_assistance(
    assistance: MealAssistance,
    reservation_date: Optional[str] = None,
    now: Optional[_dt.datetime] = None,
) -> dict:
    """校验助餐服务约束。GMS002/GMS003 需提前 4 小时预约。

    返回 {ok, warnings[], errors[]}。
    """
    warnings: list[str] = []
    errors: list[str] = []
    if not assistance.available_now:
        errors.append(
            f"{assistance.gm_service_name}({assistance.gm_service_code}) 当前不可用："
            f"{assistance.unusable_reason}"
        )
        return {"ok": False, "warnings": warnings, "errors": errors}

    if assistance.needs_advance_booking:
        if not reservation_date:
            warnings.append(
                f"{assistance.gm_service_name}({assistance.gm_service_code}) 需提前 4 小时预约，"
                f"请在下单时传入 reservationDate，否则 calculate-price 会返回 600062。"
            )
        else:
            now = now or _dt.datetime.now()
            try:
                rd = _dt.datetime.strptime(reservation_date, "%Y-%m-%d %H:%M")
                delta = (rd - now).total_seconds() / 3600.0
                if delta < 4:
                    errors.append(
                        f"预约时间 {reservation_date} 距当前不足 4 小时，"
                        f"{assistance.gm_service_name} 无法服务（需提前 4h）。"
                    )
            except ValueError:
                warnings.append(f"预约时间格式应为 yyyy-MM-dd HH:mm，收到：{reservation_date}")
    return {"ok": not errors, "warnings": warnings, "errors": errors}


def optimize_live(
    client: MCDMCPClient,
    store_code: str,
    be_code: str,
    items: list[PriceItem],
    gm_service_code: str,
    reservation_date: Optional[str] = None,
    unit_price: float = 26.0,
) -> dict:
    """实时模式：调用 calculate-price，解析阶梯预言机并给出补差建议。

    这是本工具的核心能力，只在持有有效 Token 时可用。
    """
    args = group_base(store_code, be_code)
    args["items"] = [it.to_dict() for it in items]
    args["gmServiceCode"] = gm_service_code
    if reservation_date:
        args["reservationDate"] = reservation_date

    result = client.call_tool("calculate-price", args)
    if not result.ok:
        code = result.error_code
        err = result.data.get("message") if isinstance(result.data, dict) else ""
        return {
            "ok": False,
            "error_code": code,
            "error_message": err,
            "hint": _error_hint(code, err),
        }

    subtotal = sum(it.quantity * unit_price for it in items)
    pr = parse_price_result(result.data, subtotal)
    topup = suggest_topup(pr.balance_points, unit_price, pr.discount_rate, pr.next_rate)
    return {
        "ok": True,
        "subtotal": pr.subtotal,
        "payable": pr.payable,
        "discount_rate": pr.discount_rate,
        "balance_yuan": pr.balance_yuan,
        "next_rate": pr.next_rate,
        "topup": topup,
        "raw": result.data,
    }


def _error_hint(code, msg: str) -> str:
    msg = str(msg)
    if "600061" in msg or "gmServiceCode" in msg:
        return "团餐 calculate-price 必须传 gmServiceCode（来自 query-meal-assistance）。"
    if "600062" in msg:
        return "专人分餐/摆台需提前 4 小时预约，请设置 reservationDate 或更换为 GMS001。"
    return "请检查门店/商品参数或稍后重试。"
