# WorkBuddy 联动说明 · workbuddy.md

本文件用于 **2026 麦当劳程序员创意开发大赛 · WorkBuddy 专项奖励**（前 100 名且真实使用腾讯 WorkBuddy 并提交本文件者，可得 3000 WorkBuddy 积分）。

---

## 1. 本作品如何真实使用腾讯 WorkBuddy

**企业团餐指挥官** 设计为可被 WorkBuddy 智能体直接编排调用的「团餐决策子 Agent」：

- 用户只需在 WorkBuddy 对话中说：「帮我给 30 个同事点团餐，人均 30 块，泰州海陵」，
  智能体即可加载本 Skill，按 `MCP_INTEGRATION.md` 的链路调用麦当劳 MCP，输出：
  - 可配送门店与预约时段；
  - 推荐的助餐服务（并提示专人服务需提前 4 小时预约）；
  - 当前满折档位与 **临界补差建议**（「再加 ¥480 升下一档，再省 4%」）；
  - 一份按预算生成的团餐组合清单。

- 本仓库的 `mcd_group_meal/cli.py` 即为 Skill 入口，`planner.py` 为编排核心，标准库零依赖，可无缝嵌入 WorkBuddy 运行时。

---

## 2. WorkBuddy 配置示例

将下方内容并入 WorkBuddy 的 MCP 配置（`mcp-config.example.json` 已同步提供脱敏版）：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "url": "https://mcp.mcd.cn",
      "transport": "streamable-http",
      "headers": {
        "Authorization": "Bearer ${MCD_MCP_TOKEN}"
      }
    }
  }
}
```

并在环境变量中注入 `MCD_MCP_TOKEN`（手机号登录 https://open.mcd.cn/mcp 获取）。

---

## 3. Skill 触发语（建议）

- 「企业团餐怎么点最划算」
- 「帮我算一下 30 人团餐多少钱，能不能更省」
- 「我们部门要团建，人均 30 块，来个麦当劳方案」
- 「团餐专人摆台怎么预约」

---

## 4. 联动价值

| 维度 | 说明 |
|---|---|
| 对参赛者 | 借 WorkBuddy 智能体自然触达团餐决策场景，降低使用门槛 |
| 对麦当劳 | 展示 MCP 在 B 端企业团餐的真实落地能力 |
| 对 WorkBuddy | 提供可复用的「企业采购 / 预算优化」类 Skill 范式 |

---

> 本作品已同时提交 `README.md`、`CONTEST_DECLARATION.md`、`MCP_INTEGRATION.md`、`mcp-config.example.json`、`workbuddy.md` 与 `SKILL.md`，符合活动全部文件要求。
