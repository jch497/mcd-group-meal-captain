"""麦当劳企业团餐 MCP 客户端。

封装 https://mcp.mcd.cn 的 JSON-RPC 调用，聚焦 beType=6 企业团餐场景。
设计要点：
- Token 仅从环境变量 MCD_MCP_TOKEN 读取，绝不落盘；
- 自动完成 MCP initialize 握手（服务端无状态也可跳过）；
- tools/call 的返回文本 = 说明文本 + 原始 JSON，本客户端负责截取首个 JSON 对象。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

DEFAULT_BASE_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2024-11-05"


class MCPError(Exception):
    """MCP 调用层异常。"""


class ToolError(Exception):
    """工具返回 isError=true 或业务错误码。"""

    def __init__(self, message: str, code: Optional[str] = None, raw: Any = None):
        super().__init__(message)
        self.code = code
        self.raw = raw


@dataclass
class ToolResult:
    """一次 tools/call 的归一化结果。"""

    ok: bool
    data: Any
    is_error: bool = False
    text: str = ""

    @property
    def error_code(self) -> Optional[str]:
        if isinstance(self.data, dict):
            return self.data.get("code")
        return None


class MCDMCPClient:
    """轻量麦当劳 MCP 客户端（仅依赖标准库）。"""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 30,
    ):
        self.token = token or os.environ.get("MCD_MCP_TOKEN", "")
        if not self.token:
            raise MCPError("缺少 MCP Token：请设置环境变量 MCD_MCP_TOKEN")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session_id: Optional[str] = None

    # ------------------------------------------------------------------ #
    # 底层传输
    # ------------------------------------------------------------------ #
    def _post(self, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url,
            data=body,
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                self._session_id = resp.headers.get("Mcp-Session-Id", self._session_id)
        except urllib.error.HTTPError as e:
            raise MCPError(f"HTTP {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise MCPError(f"网络错误: {e.reason}") from e
        return self._parse_jsonrpc(raw)

    @staticmethod
    def _parse_jsonrpc(raw: str) -> dict:
        """兼容纯 JSON 与 SSE(text/event-stream) 两种返回。"""
        raw = raw.strip()
        # SSE：取最后一个 data: 行
        if raw.startswith("event:") or "data:" in raw:
            last = None
            for line in raw.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    last = line[5:].strip()
            if last:
                raw = last
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise MCPError(f"无法解析 MCP 响应: {raw[:200]}") from e

    @staticmethod
    def _extract_json_object(text: str) -> dict:
        """从 '说明文本 + 原始 JSON' 中截取首个 JSON 对象。"""
        dec = json.JSONDecoder()
        for anchor in ('{"success"', '{"code"', '{"data"'):
            idx = text.find(anchor)
            if idx != -1:
                try:
                    obj, _ = dec.raw_decode(text[idx:])
                    return obj
                except json.JSONDecodeError:
                    continue
        # 退化：整段就是 JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"__raw__": text[:800]}

    # ------------------------------------------------------------------ #
    # MCP 协议方法
    # ------------------------------------------------------------------ #
    def initialize(self) -> dict:
        """完成 MCP 握手（部分服务端无状态可省略，但建议先调一次）。"""
        resp = self._post(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "mcd-group-meal-captain", "version": "1.0.0"},
                },
            }
        )
        if "result" not in resp:
            raise MCPError(f"initialize 失败: {resp}")
        return resp["result"]

    def list_tools(self) -> list[dict]:
        resp = self._post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        if "result" not in resp:
            raise MCPError(f"tools/list 失败: {resp}")
        return resp["result"].get("tools", [])

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> ToolResult:
        """调用任意工具，返回归一化结果。"""
        resp = self._post(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
        )
        if "result" not in resp:
            raise MCPError(f"tools/call({name}) 失败: {resp}")
        result = resp["result"]
        is_error = bool(result.get("isError"))
        # 文本可能有多段，拼接后截取 JSON
        text = ""
        for item in result.get("content", []):
            if item.get("type") == "text":
                text += item.get("text", "")
        data = self._extract_json_object(text)
        ok = (not is_error) and data.get("success", True) is not False
        return ToolResult(ok=ok, data=data, is_error=is_error, text=text)


# ---------------------------------------------------------------------- #
# 团餐专用便捷封装
# ---------------------------------------------------------------------- #
BE_TYPE_GROUP = 6
ORDER_TYPE_DELIVERY = 2


def group_base(store_code: str, be_code: str) -> dict:
    """企业团餐基础参数。"""
    return {
        "storeCode": store_code,
        "beCode": be_code,
        "beType": BE_TYPE_GROUP,
        "orderType": ORDER_TYPE_DELIVERY,
    }
