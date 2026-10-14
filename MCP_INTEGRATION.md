# MCP 接入说明 · MCP_INTEGRATION.md

本文档说明 **企业团餐指挥官** 实际使用的麦当劳 MCP Server、Tool、调用流程与业务价值。

---

## 1. 接入的 MCP Server

| 项 | 值 |
|---|---|
| Server 地址 | `https://mcp.mcd.cn` |
| 协议 | JSON-RPC 2.0 over Streamable HTTP（兼容 SSE 返回） |
| 认证 | `Authorization: Bearer ${MCD_MCP_TOKEN}`（Token 经 `open.mcd.cn/mcp` 手机号激活） |
| 限流 | 600 次 / 分钟（官方规则） |
| 服务声明 | [MCPServerRules](https://cdn.mcd.cn/cms/pages/MCPServerRules.html) |

> Token 仅从环境变量 `MCD_MCP_TOKEN` 读取，绝不落盘；脱敏配置见 [`mcp-config.example.json`](./mcp-config.example.json)。

---

## 2. 实际使用的 Tools

本项目聚焦 **beType=6 企业团餐** 场景，核心使用以下 6 个工具（均来自官方 `tools/list`，共 35 个）：

| 工具 | 用途 | 关键入参 | 业务价值 |
|---|---|---|---|
| `delivery-query-stores` | 查团餐可配送门店 + 预约时段 | `addressId`, `beType=6` | 锁定企业团餐专属供给 |
| `query-meal-assistance` | 查助餐服务（保鲜速达/专人分餐/专人摆台） | `storeCode`, `beType=6` | 唯一在算价前处理团餐约束的层 |
| `query-meals` | 查团餐菜单（按 20/30/40/50 元档搭配建议） | `storeCode`, `beType=6`, `orderType=2` | 选品依据 |
| `query-promotions` | 查当前门店团餐满折规则原始数据 | `storeCode`, `beType=6`, `orderType=2` | 透视「满多少打几折」 |
| `calculate-price` | 计算价格（含阶梯折扣）+ 返回 `enjoyable` 预言机 | `storeCode`,`beCode`,`beType=6`,`orderType=2`,`items`,`gmServiceCode` | **临界补差寻优的数据源** |
| `now-time-info` | 获取服务器时间 | — | 预约时间 4 小时校验基准 |

> 注：`create-order` 亦在链路末端可用（下单），本项目以「决策辅助 + 预算优化」为主定位，未强制实现下单，避免误下单风险；如需闭环可在 `planner.py` 追加 `create_order()` 封装。

---

## 3. 调用流程（业务编排）

```
[用户] 30 人，人均 30 元，泰州海陵
   │
   ▼
① delivery-query-stores(beType=6, addressId)
   → 返回可配送门店列表（含 beCode、预约时段）
   │
   ▼
② query-meal-assistance(beType=6, storeCode, beCode)
   → 返回助餐服务：GMS001(保鲜速达,可立即用)
                    GMS002(专人分餐,需提前4h)
                    GMS003(专人摆台,需提前4h)
   │
   ▼
③ query-promotions(beType=6) + query-meals(beType=6)
   → 透视满折规则 + 按预算选品
   │
   ▼
④ calculate-price(beType=6, gmServiceCode, items)
   → 返回 payable + realDiscount + enjoyable{balance, nextRate}
   │
   ▼
⑤ 临界补差寻优（optimizer.suggest_topup）
   → "再加 ¥480（≈19 份）即升下一档，再省 4%"
   │
   ▼
[输出] 团餐方案 + 最优补单建议 + 约束提醒
```

---

## 4. 关键技术发现（真实接口实测）

通过真实 Token 调用，确认了以下官方文档未明示的行为，构成本工具的技术壁垒：

1. **团餐 `calculate-price` 强制 `gmServiceCode`**：不传返回 `600061`。助餐服务是团餐的必填项，而非可选项。
2. **`query-meal-assistance` / `query-promotions` 仅在 `beType=6` 生效**：个人点单场景（beType=1/2）调用会被拒绝或返回空。这从技术上印证「企业团餐」是被忽视的空白地带。
3. **阶梯折扣由服务端计算，且暴露 `enjoyable` 预言机**：`calculate-price` 返回 `enjoyable.balance`（距下一档还差多少分）与 `enjoyable.realDiscount`（下一档折率）。绝大多数作品只展示 `payable`，本工具据此实现 **临界补差寻优**。
4. **专人服务硬约束**：GMS002/GMS003 需提前 4 小时预约，否则 `calculate-price` 返回 `600062`。本工具在算价前即做约束校验，避免失败。

---

## 5. 业务价值

- **对行政/负责人**：把「凭经验点团餐」变成「数据驱动的预算优化」，明确「再加一点就能升档省更多」。
- **对开发者**：提供可复用的 `MCDMCPClient`（标准库零依赖）+ 团餐工作流编排，便于嵌入自有系统或 WorkBuddy 智能体。
- **对大赛**：真实、深度使用麦当劳 MCP 的 beType=6 能力，覆盖门店/助餐/满折/算价全链路，且产出差异化算法能力。

---

## 6. 复现方式

```bash
export MCD_MCP_TOKEN="你的Token"
python -m mcd_group_meal.cli optimize --store 1990562 --qty 20 --unit 26 --gms GMS001
```

无 Token 时可使用 `--offline` 加载 `fixtures/` 中的真实接口样例进行演示与测试（见 `tests/`）。
