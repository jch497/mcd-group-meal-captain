# 发布与上榜指引 · PUBLISH.md

本仓库已 `git init` 并提交（commit `462a11c`）。最后两步需在 **你的 GitHub 账号** 下完成：
1. 创建公开仓库并推送；
2. 用指定模板提交参赛 Issue。

> ⚠️ 同一 GitHub 账号多个项目只有 Star 最高的入榜。**本账号只推这一个团餐项目**即可。

---

## 方式 A：把 PAT 给 AI，由 AI 代劳（推荐，最快）

1. 在 GitHub → Settings → Developer settings → Personal access tokens → 生成 `repo` 权限的 PAT。
2. 把 PAT 发给我，我会：
   - 调用 GitHub API 创建公开仓库 `mcd-group-meal-captain`；
   - `git push -u origin main`；
   - 用官方模板提交参赛 Issue。

## 方式 B：你自己 2 分钟搞定

### 1) 创建仓库（网页）
打开 https://github.com/new ，仓库名填 `mcd-group-meal-captain`，**Public**，不要勾选初始化 README（已是空仓推送）。

### 2) 推送
在本目录执行（注意把 `jch497` 换成你的 GitHub 用户名）：

```bash
git remote add origin https://github.com/jch497/mcd-group-meal-captain.git
git branch -M main
git push -u origin main
```

> 若提示登录：用户名填 GitHub 账号，密码处用 **PAT**（不是登录密码）。

### 3) 提交参赛 Issue
打开 https://github.com/M-China/mcd-developer-innovation-challenge/issues/new
，把 [`ISSUE_SUBMISSION.md`](./ISSUE_SUBMISSION.md) 的纯文本内容粘贴提交（**不要带图片**，≤1000 字）。

---

## 冲榜提醒（决定能否获奖）

榜单按 **GitHub 公开 Star 数** 排名，Star=0 不进榜。代码写完只是开始：
- 把仓库分享到技术社群、朋友圈、掘金/知乎/V2EX 等，请同行 Star；
- 在 README 突出「临界补差寻优」这一独有能力作为传播钩子；
- 截止：2026-10-25 23:59（北京时间）前提交 Issue；榜单冻结 2026-10-26 00:00。
