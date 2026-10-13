"""LLM extraction for BRD mục 1 — thông tin cơ bản về pháp lý doanh nghiệp.

Runs on the GCN ĐKDN, the charter, the shareholder register, the national-register
lookup (Cổng ĐKDN / thuế), internal-system printouts and the site-visit report. Every
one of them states some of: name, MST, legal form, founding date, charter capital,
head office, legal representative, operating status, registration changes — and
the site-visit report whether the company really operates at the address. The
same JSON comes back from each, so src/agents/calculator/legal_checks.py can
compare the sources field by field (MST must match exactly).

Amounts are read exactly as printed plus ``source_unit`` and scaled to đồng in
``normalize_amounts`` — the only place a figure is converted.
"""

from typing import Any

from src.agents.extraction.structured_extraction import (
    build_extraction_chain,
    run_extraction,
    scale_listed_amounts,
)
from src.prompts import system_prompt


REQUIRED_TOP_LEVEL_KEYS = {"company_name", "tax_code", "legal_representatives"}

_AMOUNT_FIELDS: dict[str | None, tuple[str, ...]] = {None: ("charter_capital",)}


def normalize_amounts(result: dict[str, Any]) -> dict[str, Any]:
    """Convert every amount to đồng using the result's source_unit, in place."""

    scale_listed_amounts(result, _AMOUNT_FIELDS)
    return result


def build_legal_basic_extraction_chain(llm: Any):
    """Build the JSON-output extraction chain for BRD mục 1 — thông tin cơ bản về pháp lý doanh nghiệp."""

    return build_extraction_chain(system_prompt("legal_basic_extraction"), llm)


def extract_legal_basic_structured_data(
    chain: Any,
    filename: str,
    content: str,
    path: str = "",
) -> tuple[dict[str, Any] | None, str]:
    """Run the extraction chain and validate its shape. Never raises."""

    return run_extraction(
        chain,
        filename,
        content,
        REQUIRED_TOP_LEVEL_KEYS,
        "No legal_basic_extraction_llm configured.",
        normalize_amounts,
    )
