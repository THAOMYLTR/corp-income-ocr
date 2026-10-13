"""Run the BRD extraction passes (items 1-4) on one document's text.

Each pass = one LLM call with the prompt in ``corp_income/prompts/<pass>.md``.
Amounts come back exactly as printed plus a ``source_unit``; they are scaled to
đồng here and only here, so a figure can never be converted twice.

Never raises: a failed pass is returned as an error string, and the run goes on.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from corp_income.llm import ask_json
from corp_income.text import normalize_text

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
PASSES = ("legal_basic", "shareholders", "legal_rep", "liabilities")

# Keys a reply must contain to count as a real answer to that pass.
REQUIRED_KEYS = {
    "legal_basic": {"company_name", "tax_code", "legal_representatives"},
    "shareholders": {"members"},
    "legal_rep": {"legal_representatives"},
    "liabilities": {"tax_debts", "social_insurance_debts", "administrative_penalties", "disputes"},
}

# Per pass: (list key, or None for top level) → amount fields to scale.
AMOUNT_FIELDS: dict[str, tuple[tuple[str | None, tuple[str, ...]], ...]] = {
    "legal_basic": ((None, ("charter_capital",)),),
    "shareholders": (
        (None, ("charter_capital",)),
        ("members", ("capital_amount",)),
        ("transfers", ("capital_amount",)),
    ),
    "legal_rep": (),
    "liabilities": (
        ("tax_debts", ("amount",)),
        ("social_insurance_debts", ("amount",)),
        ("administrative_penalties", ("amount",)),
        ("enforcement_actions", ("amount",)),
        ("disputes", ("claim_amount",)),
    ),
}

USER_MESSAGE = """Tên file: {filename}

Văn bản đọc được từ tài liệu (OCR hoặc text layer):
{content}

Trích xuất theo đúng schema JSON đã mô tả. Chỉ trả về JSON."""


@lru_cache(maxsize=None)
def load_prompt(pass_name: str) -> str:
    """The prompt file, minus the <!-- notes --> at the top."""

    text = (PROMPT_DIR / f"{pass_name}.md").read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()


def money_multiplier(source_unit: Any) -> int:
    """'triệu đồng' → 10^6, 'tỷ VNĐ' → 10^9, 'nghìn' → 10^3, anything else → 1 (đồng)."""

    tokens = normalize_text(str(source_unit or "")).split()
    if "ty" in tokens:
        return 10 ** 9
    if "trieu" in tokens:
        return 10 ** 6
    if "nghin" in tokens or "ngan" in tokens:
        return 10 ** 3
    return 1


def _scale(value: Any, multiplier: int) -> Any:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    return round(value * multiplier, 2)


def normalize_amounts(pass_name: str, result: dict[str, Any]) -> dict[str, Any]:
    """Scale every amount of one pass result to đồng, in place."""

    multiplier = money_multiplier(result.get("source_unit"))
    for list_key, names in AMOUNT_FIELDS.get(pass_name, ()):
        rows = [result] if list_key is None else result.get(list_key) or []
        for row in rows:
            if isinstance(row, dict):
                for name in names:
                    row[name] = _scale(row.get(name), multiplier)
    if "source_unit" in result:
        result["source_unit"] = "dong"
    return result


def run_pass(llm: Any, pass_name: str, filename: str, content: str) -> tuple[dict | None, str]:
    """One extraction pass. Returns ``(result, "")`` or ``(None, reason)``."""

    if llm is None:
        return None, "No LLM configured."
    try:
        result = ask_json(llm, load_prompt(pass_name), USER_MESSAGE.format(filename=filename, content=content))
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"[:500]
    missing = REQUIRED_KEYS[pass_name] - result.keys()
    if missing:
        return None, f"Reply is missing keys {sorted(missing)}"
    return normalize_amounts(pass_name, result), ""


def extract_document(llm: Any, filename: str, content: str, passes: list[str]):
    """Run ``passes`` on one document → ``(results, errors)``, both keyed by pass name."""

    results: dict[str, dict] = {}
    errors: dict[str, str] = {}
    for pass_name in passes:
        result, error = run_pass(llm, pass_name, filename, content)
        if result is None:
            errors[pass_name] = error
        else:
            results[pass_name] = result
    return results, errors
