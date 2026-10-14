"""mcd-group-meal-captain — 麦当劳企业团餐指挥官。

基于麦当劳 MCP（https://mcp.mcd.cn）能力，面向企业行政 / 团队负责人，
解决「团餐怎么点最划算」的核心痛点：
  - beType=6 企业团餐场景的门店 / 助餐服务 / 满折规则 / 菜单发现；
  - 阶梯折扣临界补差寻优（读取 calculate-price 的 enjoyable 预言机）；
  - 助餐服务硬约束校验（专人分餐/摆台需提前 4 小时预约）。
"""

from __future__ import annotations

__version__ = "1.0.0"

from .client import MCDMCPClient, MCPError, ToolError
from .models import (
    GroupPlan,
    GroupPlanLine,
    MealAssistance,
    PriceItem,
    PriceResult,
    Promotion,
    Store,
)
from .optimizer import optimize_live, suggest_topup, validate_assistance
from .planner import FixtureBundle, GroupMealAssistant

__all__ = [
    "MCDMCPClient",
    "MCPError",
    "ToolError",
    "Store",
    "MealAssistance",
    "Promotion",
    "PriceItem",
    "PriceResult",
    "GroupPlan",
    "GroupPlanLine",
    "optimize_live",
    "suggest_topup",
    "validate_assistance",
    "FixtureBundle",
    "GroupMealAssistant",
]
