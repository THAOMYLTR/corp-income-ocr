"""A stand-in chat model for tests: answers each BRD pass with fixed JSON.

It reads which pass is being asked from the system prompt ("BRD mục 1" … "mục 4")
and which file from the user message, so tests can give different answers per file.
"""

from __future__ import annotations

import copy
import json
import re


class FakeReply:
    def __init__(self, content):
        self.content = content


PASS_BY_MARKER = {"(BRD mục 1)": "legal_basic", "(BRD mục 2)": "shareholders",
                  "(BRD mục 3)": "legal_rep", "(BRD mục 4)": "liabilities"}


class FakeLLM:
    """``answers[(filename, pass)]`` → dict. Missing entries get an empty, valid answer."""

    EMPTY = {
        "legal_basic": {"company_name": "", "tax_code": "", "legal_representatives": [], "source_unit": "dong",
                        "change_history": []},
        "shareholders": {"members": [], "source_unit": "dong"},
        "legal_rep": {"legal_representatives": []},
        "liabilities": {"tax_debts": [], "social_insurance_debts": [], "administrative_penalties": [],
                        "disputes": [], "source_unit": "dong"},
    }

    def __init__(self, answers=None, wrap_in_fence=False, as_blocks=False):
        self.answers = answers or {}
        self.calls: list[tuple[str, str]] = []
        self.wrap_in_fence = wrap_in_fence
        self.as_blocks = as_blocks

    def invoke(self, messages):
        system = next((m[1] for m in messages if m[0] == "system"), "")
        human = next((m[1] for m in messages if m[0] == "human"), "")
        pass_name = next((p for marker, p in PASS_BY_MARKER.items() if marker in system), None)
        if pass_name is None:  # connection check
            return FakeReply('{"ok": true}')
        filename = re.search(r"Tên file: (.+)", human).group(1).strip()
        self.calls.append((filename, pass_name))
        answer = copy.deepcopy(self.answers.get((filename, pass_name), self.EMPTY[pass_name]))
        text = json.dumps(answer, ensure_ascii=False)
        if self.wrap_in_fence:
            text = f"Đây là kết quả:\n```json\n{text}\n```"
        if self.as_blocks:
            return FakeReply([{"type": "text", "text": text}])
        return FakeReply(text)
