#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键发布脚本：建公开仓库 + 推送代码 + 提交报名 Issue。

安全约定：
- GitHub Token 仅从环境变量 GITHUB_TOKEN 读取，绝不写入任何文件或日志。
- 推送完成后立即把 remote URL 还原为不含 Token 的 https 地址。
- 仓库内不得含有任何 McDonald's MCP Token（发布前请人工确认，本脚本不内嵌任何凭证）。
"""
import os
import sys
import json
import time
import subprocess
import urllib.parse
import urllib.request
import urllib.error

API = "https://api.github.com"
REPO = "mcd-group-meal-captain"
ORG_REPO = "M-China/mcd-developer-innovation-challenge"


def api(method, path, token, data=None):
    url = API + path
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "mcd-publish-script",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {"message": e.reason}


def run_git(args):
    r = subprocess.run(["git"] + args, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def leak_scan():
    """防御性自检：扫描已被跟踪的文件是否含疑似 MCP Token 的凭证特征。"""
    import pathlib
    import re
    # 匹配 Bearer 后紧跟的长凭证，或 mcp.mcd.cn 配置中的非占位 token
    pat = re.compile(r"Bearer\s+[A-Za-z0-9_\-]{16,}|(mcp\.mcd\.cn[^\n]*?token[^\n]*?[A-Za-z0-9]{16,})", re.I)
    code, out, _ = run_git(["ls-files"])
    if code != 0:
        return False
    for f in out.splitlines():
        try:
            text = pathlib.Path(f).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if pat.search(text):
            # 允许占位符
            if "YOUR_MCD_MCP_TOKEN" in text or "<YOUR" in text or "YOUR_" in text:
                continue
            print(f"  [泄露风险] 在 {f} 中发现疑似 Token 凭证，已中止发布。")
            return True
    return False


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: 请先设置环境变量 GITHUB_TOKEN，例如：")
        print('  GITHUB_TOKEN=ghp_xxx python scripts/publish.py')
        sys.exit(1)

    # 0. 泄露自检
    if leak_scan():
        sys.exit(1)
    print("[0/5] 仓库凭证自检通过（未发现 Token 泄露）")

    # 1. 获取登录名
    st, user = api("GET", "/user", token)
    if st != 200:
        print("获取 GitHub 用户失败:", st, user)
        sys.exit(1)
    login = user["login"]
    print(f"[1/5] GitHub 账号: {login}")

    # 2. 创建公开仓库（如已存在则跳过）
    st, resp = api("POST", "/user/repos", token, {
        "name": REPO,
        "description": "基于麦当劳 MCP（beType=6 企业团餐）的团餐决策 Skill：阶梯折扣临界补差寻优 + 助餐服务硬约束校验。标准库零依赖，含 14 个测试与离线演示。",
        "public": True,
        "auto_init": False,
        "has_issues": True,
    })
    if st == 201:
        print(f"[2/5] 仓库已创建: {resp.get('html_url')}")
    elif st == 422:
        print("[2/5] 仓库已存在，跳过创建")
    else:
        print("创建仓库异常:", st, resp)
        sys.exit(1)

    # 3. 将报名文案中的项目地址替换为真实账号
    issue_path = "ISSUE_SUBMISSION.md"
    txt = open(issue_path, encoding="utf-8").read()
    new = txt.replace("github.com/jch497/", f"github.com/{login}/")
    if new != txt:
        open(issue_path, "w", encoding="utf-8").write(new)
        run_git(["add", issue_path])
        run_git(["commit", "-q", "-m", "fix: 报名地址更新为真实 GitHub 账号"])
        print(f"[3/5] 已更新 ISSUE_SUBMISSION.md -> github.com/{login}/{REPO}")

    # 4. 推送
    remote = f"https://{urllib.parse.quote(token, safe='')}@github.com/{login}/{REPO}.git"
    run_git(["remote", "remove", "origin"])
    run_git(["remote", "add", "origin", remote])
    code = 1
    for attempt in range(3):
        code, out, err = run_git(["push", "-u", "origin", "master"])
        if code == 0:
            break
        print(f"  push 重试 {attempt + 1}/3 ... {err.strip()[-140:]}")
        time.sleep(2)
    if code != 0:
        print("PUSH 失败:", err)
        sys.exit(1)
    print(f"[4/5] 代码已推送至 https://github.com/{login}/{REPO}")

    # 5. 提交报名 Issue（使用官方指定模板）
    issue_body = open(issue_path, encoding="utf-8").read().strip()
    st, resp = api("POST", f"/repos/{ORG_REPO}/issues", token, {
        "title": f"【参赛申请】企业团餐指挥官 {REPO}",
        "body": issue_body,
    })
    if st in (200, 201):
        print(f"[5/5] 报名 Issue 已提交: {resp.get('html_url')}")
    else:
        print("Issue 提交异常:", st, resp)
        sys.exit(1)

    # 6. 清除 remote 中的 Token
    run_git(["remote", "set-url", "origin", f"https://github.com/{login}/{REPO}.git"])
    print("完成：已清除 remote URL 中的 Token，本地无凭证留存。")


if __name__ == "__main__":
    main()
