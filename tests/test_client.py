"""client.py 解析逻辑测试（不依赖网络）。"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcd_group_meal.client import MCDMCPClient  # noqa: E402


def test_extract_json_object_with_prefix_text():
    text = '以下是价格结果：{"success":true,"code":200,"data":{"payable":384.8}}'
    obj = MCDMCPClient._extract_json_object(text)
    assert obj["success"] is True
    assert obj["data"]["payable"] == 384.8


def test_extract_json_object_sse():
    raw = 'event: message\ndata: {"jsonrpc":"2.0","id":2,"result":{"tools":[]}}'
    parsed = MCDMCPClient._parse_jsonrpc(raw)
    assert parsed["result"]["tools"] == []


def test_extract_json_object_pure():
    raw = json.dumps({"jsonrpc": "2.0", "result": {"ok": 1}})
    parsed = MCDMCPClient._parse_jsonrpc(raw)
    assert parsed["result"]["ok"] == 1


def test_group_base():
    b = MCDMCPClient  # placeholder to keep import used
    from mcd_group_meal.client import group_base

    g = group_base("1990562", "199056281")
    assert g["beType"] == 6
    assert g["orderType"] == 2
    assert g["storeCode"] == "1990562"
