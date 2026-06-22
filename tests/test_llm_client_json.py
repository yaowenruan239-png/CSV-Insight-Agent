from src.llm.client import LLMClient
from src.utils.json_utils import extract_json_object


def test_extract_plain_json():
    assert extract_json_object('{"mode": "quick_chart"}') == {"mode": "quick_chart"}


def test_extract_markdown_json_block():
    text = '```json\n{"mode": "full_report"}\n```'
    assert extract_json_object(text) == {"mode": "full_report"}


def test_extract_embedded_json_object():
    text = '前置说明 {"mode": "planner_loop", "reason": "需要自动规划"} 后置说明'
    assert extract_json_object(text) == {"mode": "planner_loop", "reason": "需要自动规划"}


def test_chat_json_returns_fallback_when_no_backends():
    client = LLMClient(backends=[], max_retries=1)
    result = client.chat_json([{"role": "user", "content": "hi"}], fallback={"ok": False})

    assert result == {"ok": False}
