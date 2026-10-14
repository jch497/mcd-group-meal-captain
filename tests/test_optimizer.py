"""optimizer.py 逻辑测试（离线）。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcd_group_meal.models import MealAssistance  # noqa: E402
from mcd_group_meal.optimizer import (  # noqa: E402
    estimate_discount_rate,
    parse_price_result,
    suggest_topup,
    validate_assistance,
)


def test_estimate_monotonic_decreasing():
    r1, _ = estimate_discount_rate(260)
    r2, _ = estimate_discount_rate(520)
    r3, _ = estimate_discount_rate(1000)
    assert r1 > r2 > r3  # 折扣率随金额下降（更划算）


def test_suggest_topup_with_balance():
    s = suggest_topup(balance_points=4000, unit_price=26.0, current_rate=0.78, next_rate=0.74)
    assert s["add_yuan"] == 40.0
    assert s["add_items"] >= 1
    assert "下一档" in s["message"]


def test_suggest_topup_reached_top():
    s = suggest_topup(balance_points=0, unit_price=26.0)
    assert s["reached_top"] is True


def test_validate_assistance_gms001_no_booking():
    a = MealAssistance("GMS001", "保鲜速达", [], enable=True)
    v = validate_assistance(a)
    assert v["ok"] is True


def test_validate_assistance_gms003_needs_booking():
    a = MealAssistance("GMS003", "专人摆台", [], enable=True, unusable_reason="x")
    v = validate_assistance(a)
    assert v["ok"] is True  # 未传预约时间 → 仅 warning，不阻断
    assert any("4 小时" in w for w in v["warnings"])


def test_parse_price_result_realdiscount():
    raw = {
        "data": {
            "subtotal": 520,
            "payable": 384.8,
            "realDiscount": 7.4,
            "enjoyable": {"balance": 48000, "realDiscount": 7.0},
        }
    }
    pr = parse_price_result(raw, 520)
    assert abs(pr.discount_rate - 0.74) < 1e-6
    assert pr.balance_points == 48000
    assert abs(pr.next_rate - 0.70) < 1e-6
