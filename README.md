# 🍔 企业团餐指挥官 · mcd-group-meal-captain

> 基于 **麦当劳 MCP（Model Context Protocol）** 能力开发的创意 Skill，专为企业行政、团队负责人、活动组织者解决一个真实痛点：**「企业团餐怎么点最划算？」**

不同于海量的「个人点单 / 卡路里估算」类作品，本工具聚焦于 **beType=6 企业团餐场景**——这是麦当劳 MCP 中少有人深挖、却最具 B 端价值的能力分支。

---

## ✨ 核心能力

| 能力 | 说明 | 差异化 |
|---|---|---|
| **团餐门店发现** | `delivery-query-stores(beType=6)` 查询可配送门店与预约时段 | 锁定企业团餐专属供给 |
| **助餐服务选择** | `query-meal-assistance(beType=6)` 列出保鲜速达 / 专人分餐 / 专人摆台 | 唯一在算价前就处理团餐约束的层 |
| **满折规则透视** | `query-promotions(beType=6)` 返回真实满折原始规则 | 看懂「满多少打几折」 |
| **阶梯折扣临界补差寻优** 🚀 | 读取 `calculate-price` 返回的 `enjoyable` 预言机，反推「再加多少就能升下一档折扣」 | **全榜独有能力**：大多数作品只展示价格，本工具做决策 |
| **助餐服务硬约束校验** | GMS002/GMS003 需提前 4 小时预约，`calculate-price` 强校验（600062） | 下单前主动拦截，避免失败 |
| **按预算生成组合** | 根据人数 × 人均预算贪心生成团餐清单 | 行政 30 秒出方案 |

---

## 🎯 目标用户

- **企业行政 / 行政外包**：每月固定团餐、会议餐、节日聚餐。
- **团队负责人 / 项目经理**：研发团建、冲刺奖励餐。
- **活动组织者**：发布会、培训、赛事补给。
- **WorkBuddy 智能体开发者**：作为可调用的团餐决策子 Agent。

---

## 📦 安装

```bash
# 克隆后，仅依赖 Python 标准库（≥3.9）
cd mcd-group-meal-captain
python -m mcd_group_meal.cli --help
```

可选（发布到 PyPI 形态）：

```bash
pip install -e .
mcd-group-meal --help
```

---

## 🔑 配置麦当劳 MCP Token

1. 用手机号登录 [open.mcd.cn/mcp](https://open.mcd.cn/mcp) 激活并获取 Token。
2. 将 Token 写入环境变量（**切勿提交到仓库**）：

```bash
export MCD_MCP_TOKEN="你的Token"
```

配置示例见 [`mcp-config.example.json`](./mcp-config.example.json)（已脱敏，仅含环境变量占位符）。

---

## 🚀 使用示例

### 离线演示（无需 Token，使用 `fixtures/` 真实样例）

```bash
# 1) 按 30 人、人均 30 元生成团餐组合
python -m mcd_group_meal.cli --offline plan --headcount 30 --budget 30

# 2) 估算 20 份主餐的价格档位
python -m mcd_group_meal.cli --offline price --qty 20 --unit 26

# 3) 查看门店 / 助餐服务 / 满折规则
python -m mcd_group_meal.cli --offline stores
python -m mcd_group_meal.cli --offline assist
python -m mcd_group_meal.cli --offline promos
```

### 实时模式（需 `MCD_MCP_TOKEN`）

```bash
# 查询指定地址可配送的团餐门店
python -m mcd_group_meal.cli stores --address 1036729580159600382506293145

# 临界补差寻优：20 份主餐，选 GMS001，看能否升下一档
python -m mcd_group_meal.cli optimize --store 1990562 --qty 20 --unit 26 --gms GMS001
```

实时返回示例（节选）：

```json
{
  "ok": true,
  "subtotal": 520.0,
  "payable": 384.8,
  "discount_rate": 0.74,
  "balance_yuan": 480.0,
  "next_rate": 0.70,
  "topup": {
    "message": "再加约 ¥480（≈19 份单价 ¥26 商品）即可升入下一档折扣，预计再省 4.0%。",
    "add_yuan": 480.0,
    "add_items": 19
  }
}
```

> 这正是本工具的核心价值：**不只是告诉你「多少钱」，而是告诉你「再加一点就能更省」**，把团餐预算花在刀刃上。

---

## 🧩 作为 WorkBuddy Skill 调用

详见 [`workbuddy.md`](./workbuddy.md) 与 [`SKILL.md`](./SKILL.md)。本工具可被 WorkBuddy 智能体直接编排进对话流，用户说「帮我给 30 个同事点团餐，人均 30 块」即可触发完整链路。

---

## 📁 目录结构

```
mcd-group-meal-captain/
├── README.md                  # 本文件
├── CONTEST_DECLARATION.md    # 参赛声明（不可修改）
├── MCP_INTEGRATION.md        # MCP 接入说明
├── mcp-config.example.json   # 脱敏 MCP 配置示例
├── workbuddy.md              # WorkBuddy 专项奖励说明
├── SKILL.md                  # 创意 Skill 定义
├── mcd_group_meal/           # 核心源码
│   ├── client.py             # 麦当劳 MCP JSON-RPC 客户端
│   ├── models.py             # 业务数据模型
│   ├── optimizer.py          # 阶梯折扣临界补差寻优 + 助餐约束校验
│   ├── planner.py            # 团餐工作流编排
│   └── cli.py                # 命令行 / Skill 入口
├── fixtures/                 # 真实接口返回样例（已脱敏）
└── tests/                    # 14 个单元测试（标准库运行）
```

---

## ✅ 合规

- 仅使用麦当劳官方 MCP（`https://mcp.mcd.cn`），遵循 [MCPServerRules](https://cdn.mcd.cn/cms/pages/MCPServerRules.html)。
- 原创开发，无恶意脚本 / 外链 / 品牌对比。
- 详见 [`CONTEST_DECLARATION.md`](./CONTEST_DECLARATION.md)。

---

🏆 参加 **2026 麦当劳程序员创意开发大赛**。
