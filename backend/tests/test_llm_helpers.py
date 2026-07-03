"""纯逻辑单测（不触网）：JSON 解析 + 合规状态合并。"""

import pytest

from app.compliance.semantic import merge_status
from app.llm import parse_json


def test_parse_json_plain():
    assert parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_fenced():
    assert parse_json('```json\n[{"x": 2}]\n```') == [{"x": 2}]


def test_parse_json_with_noise():
    assert parse_json('好的：\n[{"status":"pass"}]\n以上') == [{"status": "pass"}]


def test_parse_json_invalid_raises():
    with pytest.raises(ValueError):
        parse_json("这里没有 JSON")


def test_merge_status_takes_worst():
    assert merge_status("pass", "soft") == "soft"
    assert merge_status("soft", "blocked") == "blocked"
    assert merge_status("pass", "pass") == "pass"
    assert merge_status("blocked", "pass", "soft") == "blocked"
