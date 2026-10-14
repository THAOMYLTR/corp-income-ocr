"""Phụ lục 01 mục 3 and 7 — financial figures, ratios and warnings, in code.

The LLM only reads numbers off the BCTC (financial_extraction). Everything the
guidance asks to compute is done here, so a ratio in the report is always the
same arithmetic on the same printed figures:

    Biến động doanh thu        = DTT năm N / DTT năm N-1 - 1
    ROS                        = LNST / DTT
    Hệ số thanh toán hiện hành = TSNH / Nợ ngắn hạn
    Thu nhập DN ghi nhận        = (LNST - nghĩa vụ TDH + khấu hao) x tỷ lệ góp vốn

Warnings follow the guidance: tổng tài sản ≠ tổng nguồn vốn, doanh thu giảm
> 20%, ROS < 0, hệ số thanh toán < 1, khoản mục bất thường.
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.calculator.legal_checks import SOURCE_LABELS

FIELDS = (
    "total_assets", "current_assets", "non_current_assets", "total_liabilities",
    "current_liabilities", "long_term_liabilities", "equity", "total_capital",
    "net_revenue", "cogs", "gross_profit", "financial_income", "financial_expenses",
    "selling_expenses", "admin_expenses", "operating_profit", "other_profit",
    "profit_before_tax", "profit_after_tax", "depreciation",
)
REVENUE_DROP_ALERT = -0.20
BALANCE_TOLERANCE = 0.005  # 0,5% — rounding in printed statements


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _year_of(period: dict[str, Any]) -> str:
    text = str(period.get("period") or period.get("end_date") or "")
    match = re.search(r"(19|20)\d{2}", text)
    return match.group(0) if match else ""


def _ratio(a: float | None, b: float | None) -> float | None:
    return None if a is None or not b else a / b


def merge_periods(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Years (and the latest interim period) with one value per field.

    Audited statements win over unaudited; within the same rank the first
    document that prints a field keeps it. Each figure remembers its file.
    """

    fin = [r for r in records if r.get("pass") == "financial" and isinstance(r.get("data"), dict)]
    fin.sort(key=lambda r: 0 if r["data"].get("audited") else 1)
    years: dict[str, dict[str, Any]] = {}
    interim: dict[str, Any] = {}
    unusual: list[str] = []
    sources: list[str] = []
    for record in fin:
        data = record["data"]
        label = f"{record.get('document')} ({'kiểm toán' if data.get('audited') else 'chưa kiểm toán/không rõ'})"
        if label not in sources:
            sources.append(label)
        unusual += [f"{u} — {record.get('document')}" for u in data.get("unusual_items") or [] if u]
        for period in data.get("periods") or []:
            if not isinstance(period, dict):
                continue
            if period.get("period_type") == "interim":
                target = interim if not interim or str(period.get("period")) == interim.get("period") else None
                if target is None:
                    continue
                target.setdefault("period", str(period.get("period") or ""))
            else:
                year = _year_of(period)
                if not year:
                    continue
                target = years.setdefault(year, {"period": year})
            for field in FIELDS:
                value = _num(period.get(field))
                if value is not None and target.get(field) is None:
                    target[field] = value
                    target.setdefault("_source", {})[field] = record.get("document")
    return {"years": dict(sorted(years.items())), "interim": interim,
            "unusual_items": unusual, "sources": sources}


def compute(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Figures, ratios per year, warnings and the Bad-Finance signals."""

    merged = merge_periods(records)
    years = merged["years"]
    ratios: dict[str, dict[str, float | None]] = {}
    warnings: list[str] = []
    ordered = list(years)
    for index, year in enumerate(ordered):
        fig = years[year]
        if fig.get("total_capital") is None and None not in (fig.get("total_liabilities"), fig.get("equity")):
            fig["total_capital"] = fig["total_liabilities"] + fig["equity"]
        prev = years[ordered[index - 1]] if index and int(ordered[index - 1]) == int(year) - 1 else {}
        growth = _ratio(fig.get("net_revenue"), prev.get("net_revenue"))
        ratios[year] = {
            "revenue_growth": None if growth is None else growth - 1,
            "ros": _ratio(fig.get("profit_after_tax"), fig.get("net_revenue")),
            "current_ratio": _ratio(fig.get("current_assets"), fig.get("current_liabilities")),
        }
        r = ratios[year]
        assets, capital = fig.get("total_assets"), fig.get("total_capital")
        if assets and capital and abs(assets - capital) > BALANCE_TOLERANCE * assets:
            warnings.append(f"{year}: Tổng tài sản ({fmt(assets)}) khác tổng nguồn vốn ({fmt(capital)})")
        if r["revenue_growth"] is not None and r["revenue_growth"] < REVENUE_DROP_ALERT:
            warnings.append(f"{year}: Doanh thu thuần giảm {pct(-r['revenue_growth'])} so với năm trước (> 20%)")
        if r["ros"] is not None and r["ros"] < 0:
            warnings.append(f"{year}: LNST/DTT âm ({pct(r['ros'])})")
        if r["current_ratio"] is not None and r["current_ratio"] < 1:
            warnings.append(f"{year}: Hệ số thanh toán hiện hành < 1 ({r['current_ratio']:.2f})".replace(".", ","))
    warnings += [f"Khoản mục bất thường: {u}" for u in merged["unusual_items"]]
    return {**merged, "ratios": ratios, "warnings": warnings,
            "latest_year": ordered[-1] if ordered else ""}


def income_estimate(financials: dict[str, Any], ownership_pct: float | None,
                    long_term_obligation: float | None = None) -> dict[str, Any]:
    """(LNST - nghĩa vụ TDH + khấu hao) x tỷ lệ góp vốn, with what was missing."""

    year = financials.get("latest_year")
    fig = financials["years"].get(year, {}) if year else {}
    lnst, dep = fig.get("profit_after_tax"), fig.get("depreciation")
    missing = []
    if lnst is None:
        missing.append("LNST")
    if ownership_pct is None:
        missing.append("tỷ lệ góp vốn của KH vay")
    if dep is None:
        missing.append("khấu hao (tính = 0)")
    if long_term_obligation is None:
        missing.append("nghĩa vụ trả nợ TDH của DN (chưa có CIC, tính = 0)")
    value = None
    if lnst is not None and ownership_pct is not None:
        value = (lnst - (long_term_obligation or 0) + (dep or 0)) * ownership_pct / 100
    return {"year": year, "lnst": lnst, "depreciation": dep,
            "long_term_obligation": long_term_obligation, "ownership_pct": ownership_pct,
            "value": value, "missing": missing}


def fmt(value: float | None) -> str:
    """Money in triệu đồng, the unit a credit memo table uses."""

    if value is None:
        return "—"
    return f"{value / 1e6:,.0f}".replace(",", ".")


def pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%".replace(".", ",")


def sources_text(financials: dict[str, Any]) -> str:
    return "; ".join(financials.get("sources") or []) or "Chưa có BCTC trong hồ sơ"


__all__ = ["compute", "income_estimate", "fmt", "pct", "sources_text", "SOURCE_LABELS"]
