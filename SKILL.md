---
name: mcd-group-meal-captain
version: 1.0.0
description: 麦当劳企业团餐指挥官——基于麦当劳 MCP(beType=6) 的团餐阶梯折扣临界补差寻优与助餐服务约束校验。当用户需要为企业/团队点麦当劳团餐、比较团餐折扣档位、计算「再加多少能升档更省」、或处理团餐专人摆台/分餐预约时使用。
type: skill
entry: mcd_group_meal.cli:main
requires:
  mcp:
    - url: https://mcp.mcd.cn
      auth_env: MCD_MCP_TOKEN
  python: ">=3.9"
---

# 企业团餐指挥官 · SKILL

## 何时使用

- 用户要为企业/团队/活动点 **麦当劳团餐**（beType=6 企业团餐场景）。
- 用户问「团餐怎么点最划算」「再加点能不能更省」「团餐专人摆台怎么预约」。
- 用户给出人数与人均预算，需要快速出团餐方案。

## 核心能力

1. **团餐门店发现**：`delivery-query-stores(beType=6)` 查可配送门店 + 预约时段。
2. **助餐服务选择**：`query-meal-assistance(beType=6)` → GMS001 保鲜速达（即时）/ GMS002 专人分餐 / GMS003 专人摆台（后两者需提前 4h 预约）。
3. **满折规则透视**：`query-promotions(beType=6)` 返回真实满折原始规则。
4. **阶梯折扣临界补差寻优** 🚀：读取 `calculate-price` 的 `enjoyable` 预言机，反推「再加多少升下一档」。
5. **助餐约束校验**：GMS002/GMS003 提前 4h 预约，下单前主动拦截。
6. **按预算生成组合**：人数 × 人均预算 → 贪心团餐清单。

## 调用流程

```
delivery-query-stores(beType=6)
  → query-meal-assistance(beType=6)
  → query-promotions(beType=6) + query-meals(beType=6)
  → calculate-price(beType=6, gmServiceCode, items)   # 读取 enjoyable 预言机
  → 临界补差寻优 + 约束校验
  → 输出团餐方案
```

## 命令行入口

```bash
export MCD_MCP_TOKEN="你的Token"

# 实时：临界补差寻优
python -m mcd_group_meal.cli optimize --store 1990562 --qty 20 --unit 26 --gms GMS001

# 离线演示（无需 Token，fixtures 真实样例）
python -m mcd_group_meal.cli --offline plan --headcount 30 --budget 30
```

## 关键业务约束（务必遵守）

- 团餐 `calculate-price` **必须传 `gmServiceCode`**（来自 `query-meal-assistance`），否则报 `600061`。
- `query-meal-assistance` / `query-promotions` **仅在 `beType=6` 生效**。
- GMS002/GMS003 需提前 4 小时预约，`calculate-price` 会强校验（错码 `600062`）。

## 合规

- 仅使用官方麦当劳 MCP，遵循 MCPServerRules；不对比其他品牌，不含恶意脚本/外链。
- 原创开发，详见 `CONTEST_DECLARATION.md`。
