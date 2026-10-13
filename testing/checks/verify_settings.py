"""Settings and LLM plumbing: clear errors for missing keys, robust JSON parsing."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "testing"))

from corp_income import LLMConfigError, Settings, build_llm, check_connection
from corp_income.llm import parse_json, response_text
from fake_llm import FakeLLM, FakeReply

failures = []


def expect(condition, message):
    print(("   ✓ " if condition else "   ✗ ") + message)
    if not condition:
        failures.append(message)


print("1. Thiếu cấu hình → báo đúng chỗ cần sửa")
for provider, needle in (("anthropic", "anthropic_api_key"), ("openai", "openai_api_key"),
                         ("databricks", "databricks_host")):
    s = Settings.load(llm_provider=provider, llm_model="m", anthropic_api_key="", openai_api_key="",
                      databricks_host="", databricks_token="")
    try:
        build_llm(s)
        expect(False, f"{provider}: phải báo lỗi")
    except LLMConfigError as exc:
        expect(needle in str(exc), f"{provider}: lỗi nhắc '{needle}'")
expect(any("llm_model" in p for p in Settings.load(llm_model="", anthropic_api_key="k").problems()),
       "thiếu llm_model được báo")
expect("must be one of" in Settings.load(llm_provider="gpt").problems()[0], "provider sai được báo")
try:
    Settings.load(anthropic_key="x")
    expect(False, "tên setting sai phải báo lỗi")
except TypeError as exc:
    expect("anthropic_key" in str(exc), "gõ sai tên setting → báo ngay")
described = Settings.load(anthropic_api_key="sk-ant-secret-value").describe()
expect("secret" not in str(described), "describe() che key")

print("\n2. Đọc JSON từ câu trả lời của model")
expect(parse_json('{"a": 1}') == {"a": 1}, "JSON thuần")
expect(parse_json('Kết quả:\n```json\n{"a": 1}\n```') == {"a": 1}, "JSON trong ```json")
expect(parse_json('Đây: {"a": {"b": 2}} xong.') == {"a": {"b": 2}}, "JSON lẫn chữ")
expect(response_text(FakeReply([{"type": "text", "text": "x"}, {"type": "text", "text": "y"}])) == "xy",
       "nội dung dạng block (Anthropic)")
try:
    parse_json("không có json")
    expect(False, "không có JSON phải báo lỗi")
except ValueError:
    expect(True, "không có JSON → ValueError")

print("\n3. Kiểm tra kết nối")
expect(check_connection(FakeLLM()) == '{"ok": true}', "check_connection trả lời được")

if failures:
    print(f"\n❌ {len(failures)} lỗi")
    sys.exit(1)
print("\n✅ settings OK")
