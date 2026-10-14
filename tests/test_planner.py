"""planner.py 集成测试（离线 fixtures）。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcd_group_meal.models import PriceItem  # noqa: E402
from mcd_group_meal.planner import GroupMealAssistant  # noqa: E402


def _assistant():
    return GroupMealAssistant(client=None, fixtures_dir="fixtures")


def test_fixtures_load():
    a = _assistant()
    assert len(a._fixtures.stores) >= 1
    assert len(a._fixtures.assist) >= 1
    assert len(a._fixtures.promotions) >= 1


def test_offline_price():
    a = _assistant()
    res = a.calculate([PriceItem("521316", 20)], unit_price=26.0)
    assert res["ok"] is True
    assert res["offline"] is True
    assert res["payable"] < res["subtotal"]


def test_offline_plan():
    a = _assistant()
    plan = a.build_plan(headcount=30, per_person_budget=30.0, unit_price=26.0)
    assert plan.total_quantity == 30
    assert plan.subtotal == 780.0


def test_select_assistance_gms001():
    a = _assistant()
    a.select_store(0)
    sel = a.select_assistance("GMS001")
    assert sel is not None
    assert sel.gm_service_code == "GMS001"
