"""The corp-income agent: "Phụ lục 01 - Thẩm định nguồn thu doanh nghiệp".

Same place and shape as the SME repo's specialists (``SPECIALIST_BY_AGENT``).
Two layers, so a figure in the report can only come from a document:

1. Code — BRD legal checks (legal_checks.py), financial figures and ratios
   (financial_metrics.py), and every template cell that is a fact or a number
   (appendix_context.py).
2. One LLM call (report_writer.py) — only the cells code cannot write: the
   "Nhận xét…" paragraphs, business activity, CIC and the conclusion, written
   from the guidance (config/prompts/corp_income_guidance.md) and the evidence.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from src.agents.calculator.legal_checks import parse_date, run_all_checks
from src.agents.calculator import financial_metrics
from src.agents.extraction import (
    financial_extraction,
    legal_basic_extraction,
    legal_rep_extraction,
    liabilities_extraction,
    shareholders_extraction,
)
from src.agents.report_writer import write_placeholders
from src.types import ClassifiedDocument
from src.utils.report.appendix_context import (
    bad_corp_signals,
    borrower_ownership,
    build_appendix_context,
    fill_missing_financial_names,
)
from src.utils.report.report_template import (
    HTML_COMMENT,
    build_context,
    load_template,
    render_markdown,
    template_placeholders,
)

# pass name → (ClassifiedDocument result attribute, normaliser for provided data)
PASSES: dict[str, tuple[str, Any]] = {
    "legal_basic": ("legal_basic_extraction", legal_basic_extraction.normalize_amounts),
    "shareholders": ("shareholders_extraction", shareholders_extraction.normalize_amounts),
    "legal_rep": ("legal_rep_extraction", legal_rep_extraction.normalize_amounts),
    "liabilities": ("liabilities_extraction", liabilities_extraction.normalize_amounts),
    "financial": ("financial_extraction", financial_extraction.normalize_amounts),
}

# Documents whose text the report writer reads first (business activity, CIC,
# business plan); then everything else. Characters per document.
EXCERPT_FIRST = ("bao_cao_thuc_dia", "bao_cao_cic", "de_nghi_cap_tin_dung", "chung_tu_kinh_doanh",
                 "to_khai_vat", "hinh_anh_thuc_dia", "")
EXCERPT_CHARS = {"first": 6_000, "other": 2_500}
EXCERPT_TOTAL = 80_000

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


def _excerpts(documents: list[ClassifiedDocument]) -> list[dict[str, Any]]:
    ordered = sorted(documents, key=lambda d: 0 if (d.document_type or "") in EXCERPT_FIRST else 1)
    out, budget = [], EXCERPT_TOTAL
    for doc in ordered:
        limit = EXCERPT_CHARS["first" if (doc.document_type or "") in EXCERPT_FIRST else "other"]
        text = (doc.content or "")[: min(limit, budget)]
        if not text:
            continue
        budget -= len(text)
        out.append({"file": doc.filename, "loai": doc.source_description or doc.document_type or "Chưa phân loại",
                    "nguon": doc.source, "noi_dung": text})
        if budget <= 0:
            break
    return out


def _compact_items(items: dict[int, dict[str, Any]]) -> dict[str, Any]:
    return {
        str(n): {
            "tieu_de": item["title"],
            "ket_luan": item["conclusion"],
            "kiem_tra": [{"muc_do": f["severity"], "noi_dung": f["message"], "can_cu": f.get("evidence") or []}
                         for f in item["findings"]],
            "tom_tat": item["summary"],
        }
        for n, item in items.items()
    }


class CorpIncomeAnalysis:
    """Phụ lục 01. ``llm`` writes the narrative cells; everything else is code."""

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
        borrower_names = list(borrower_names or [])
        as_of = loan_date if isinstance(loan_date, date) else (parse_date(loan_date) or date.today())
        records = records_from_documents(documents) + records_from_reference_data(reference_data)
        items = run_all_checks(
            records,
            as_of=as_of,
            borrower_names=borrower_names,
            watchlist=reference_data.get("watchlist") or [],
        )
        financials = financial_metrics.compute(records)
        income = financial_metrics.income_estimate(financials, borrower_ownership(items, borrower_names))

        template_text, template_source = load_template(template_path)
        template_body = HTML_COMMENT.sub("", template_text)
        meta = {
            "as_of": as_of.strftime("%d/%m/%Y"),
            "borrower_names": borrower_names,
            "template": template_source,
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
        base = {"meta": meta, "documents": documents_view, "items": items}

        # 1. Code fills every fact and figure.
        names = template_placeholders(template_body)
        ctx = {**build_context(base), **build_appendix_context(base, records, financials, as_of)}
        fill_missing_financial_names(set(names), ctx)

        # 2. The LLM writes only what is left.
        remaining = [name for name in names if name not in ctx]
        evidence = {
            "ngay_tham_chieu": meta["as_of"],
            "khach_hang_vay": borrower_names,
            "gia_tri_da_dien": {name: ctx[name] for name in names if name in ctx},
            "phap_ly": _compact_items(items),
            "tai_chinh": {
                "nguon": financials["sources"],
                "so_lieu_theo_nam": {y: {k: v for k, v in fig.items() if k != "_source"}
                                     for y, fig in financials["years"].items()},
                "ky_giua_nien_do": {k: v for k, v in financials["interim"].items() if k != "_source"},
                "chi_so": financials["ratios"],
                "canh_bao": financials["warnings"],
                "don_vi": "đồng (bảng trong báo cáo hiển thị triệu đồng)",
            },
            "thu_nhap_ghi_nhan": {
                **income,
                "gia_tri_trieu_dong": financial_metrics.fmt(income["value"]),
                "cong_thuc": "(LNST hợp lý - Nghĩa vụ TDH của DN + Khấu hao) x Tỷ lệ góp vốn",
            },
            "dau_hieu_bad_corp": bad_corp_signals(items, financials, as_of),
            "ho_so": [{"file": d["filename"], "loai": d["label"], "nguon": d["source"],
                       "doc_bang": d["read_method"]} for d in documents_view],
            "trich_doan_ho_so": _excerpts(documents),
            "du_lieu_noi_bo_ngoai": {k: v for k, v in reference_data.items() if k != "watchlist"},
        }
        written, writer_error = write_placeholders(self.llm, template_body, remaining, evidence)
        ctx.update(written)
        meta.update({
            "code_placeholders": [n for n in names if n not in remaining],
            "llm_placeholders": remaining,
            "writer_error": writer_error,
            "unknown_placeholders": [],
        })

        markdown = render_markdown(base, template_text, ctx)
        return {
            "response": markdown,
            "meta": meta,
            "items": {str(number): item for number, item in items.items()},
            "financials": financials,
            "income_estimate": income,
            "records": records,
            "documents": documents_view,
        }


SPECIALIST_BY_AGENT = {
    "CORP_INCOME_AGENT": CorpIncomeAnalysis,
}
