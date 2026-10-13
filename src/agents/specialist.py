"""The corp-income agent: BRD items 1-4 from the extracted documents.

Same place and shape as the SME repo's specialists (``SPECIALIST_BY_AGENT``),
with one deliberate difference: this agent writes its report WITHOUT an LLM.
The LLM already did its job in the extraction passes (document → JSON); what is
left — comparing sources, counting 12-month windows, summing ownership, filling
the template — is arithmetic and lookups, so it is done in code
(``src/agents/calculator/legal_checks.py``). A figure in the report can only
come from a document, and the same input always gives the same report.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from src.agents.calculator.legal_checks import parse_date, run_all_checks
from src.agents.extraction import (
    legal_basic_extraction,
    legal_rep_extraction,
    liabilities_extraction,
    shareholders_extraction,
)
from src.types import ClassifiedDocument
from src.utils.report.report_template import load_template, render_markdown, unknown_placeholders

# pass name → (ClassifiedDocument result attribute, normaliser for provided data)
PASSES: dict[str, tuple[str, Any]] = {
    "legal_basic": ("legal_basic_extraction", legal_basic_extraction.normalize_amounts),
    "shareholders": ("shareholders_extraction", shareholders_extraction.normalize_amounts),
    "legal_rep": ("legal_rep_extraction", legal_rep_extraction.normalize_amounts),
    "liabilities": ("liabilities_extraction", liabilities_extraction.normalize_amounts),
}

PROVIDED_LABELS = {
    "internal": "Internal data (BCDE/BEP/DBX)",
    "external": "External data (Cổng ĐKDN/cơ quan thuế/BHXH)",
}


def records_from_documents(documents: list[ClassifiedDocument]) -> list[dict[str, Any]]:
    """One record per (document, BRD item) that came back with JSON."""

    records = []
    for doc in documents:
        for pass_name, (attr, _) in PASSES.items():
            data = getattr(doc, attr, None)
            if isinstance(data, dict):
                records.append({
                    "source": doc.source,
                    "document": doc.filename,
                    "document_type": doc.document_type,
                    "pass": pass_name,
                    "data": data,
                })
    return records


def records_from_reference_data(reference_data: dict[str, Any]) -> list[dict[str, Any]]:
    """internal_data / external_data handed in by the caller (BRD B2/B3)."""

    records = []
    for kind in ("internal", "external"):
        for pass_name, data in (reference_data.get(f"{kind}_data") or {}).items():
            if pass_name not in PASSES or not isinstance(data, dict):
                raise ValueError(
                    f"{kind}_data keys must be among {list(PASSES)}; got {pass_name!r}"
                )
            records.append({
                "source": kind,
                "document": PROVIDED_LABELS[kind],
                "document_type": f"{kind}_data",
                "pass": pass_name,
                "data": PASSES[pass_name][1](json.loads(json.dumps(data))),
            })
    return records


class CorpIncomeAnalysis:
    """BRD Corp Income items 1-4. ``llm`` is accepted for interface parity and unused."""

    agent_name = "CORP_INCOME_AGENT"

    def __init__(self, llm: Any = None):
        self.llm = llm

    def analyze(
        self,
        documents: list[ClassifiedDocument],
        reference_data: dict[str, Any] | None = None,
        loan_date: str | date | None = None,
        borrower_names: list[str] | None = None,
        template_path: str | None = None,
    ) -> dict[str, Any]:
        reference_data = reference_data or {}
        as_of = loan_date if isinstance(loan_date, date) else (parse_date(loan_date) or date.today())
        records = records_from_documents(documents) + records_from_reference_data(reference_data)
        items = run_all_checks(
            records,
            as_of=as_of,
            borrower_names=borrower_names or [],
            watchlist=reference_data.get("watchlist") or [],
        )
        template_text, template_source = load_template(template_path)
        meta = {
            "as_of": as_of.strftime("%d/%m/%Y"),
            "borrower_names": list(borrower_names or []),
            "template": template_source,
            "unknown_placeholders": unknown_placeholders(template_text),
        }
        documents_view = [
            {
                "filename": doc.filename,
                "label": doc.source_description or doc.document_type or "Chưa phân loại",
                "source": doc.source,
                "box": doc.declared_group,
                "read_method": doc.read_method,
                "chars": len(doc.content or ""),
                "passes_done": [
                    name for name, (attr, _) in PASSES.items()
                    if isinstance(getattr(doc, attr, None), dict)
                ],
                "errors": {
                    name: getattr(doc, f"{attr}_error")
                    for name, (attr, _) in PASSES.items()
                    if getattr(doc, f"{attr}_error", "")
                },
            }
            for doc in documents
        ]
        markdown = render_markdown(
            {"meta": meta, "documents": documents_view, "items": items}, template_text
        )
        return {
            "response": markdown,
            "meta": meta,
            "items": {str(number): item for number, item in items.items()},
            "records": records,
            "documents": documents_view,
        }


SPECIALIST_BY_AGENT = {
    "CORP_INCOME_AGENT": CorpIncomeAnalysis,
}
