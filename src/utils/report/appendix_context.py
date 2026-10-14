"""Placeholders of "Phụ lục 01 - Thẩm định nguồn thu doanh nghiệp" filled in code.

Everything that is a fact read off a document, or arithmetic on such facts, is
filled here — names, MST, dates, members, every figure and ratio of the
financial table. What is left in the template after this (the "Nhận xét…",
business activity, CIC, conclusion) goes to the report writer LLM, which sees
these values too so its narrative cannot contradict them.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from src.agents.calculator import financial_metrics as fm
from src.agents.calculator.legal_checks import norm_person, parse_date, within_lookback

NO_INFO = "Chưa có thông tin"

# Template prefix → field of financial_metrics (figures) or ratio name.
FIGURE_PREFIXES = {
    "TongTaiSan": "total_assets", "TSNH": "current_assets", "TSDH": "non_current_assets",
    "TongNguonVon": "total_capital", "NoPhaiTra": "total_liabilities", "VCSH": "equity",
    "DTT": "net_revenue", "GVHB": "cogs", "LNG": "gross_profit", "DTTC": "financial_income",
    "CPTC": "financial_expenses", "CPQL": "admin_expenses", "CPBH": "selling_expenses",
    "LNThuan": "operating_profit", "LNTT": "profit_before_tax", "LNST": "profit_after_tax",
}
RATIO_PREFIXES = {"BienDongDT": "revenue_growth", "ROS": "ros", "CurrentRatio": "current_ratio"}
FINANCIAL_NAME = re.compile(
    r"^(" + "|".join(sorted({**FIGURE_PREFIXES, **RATIO_PREFIXES}, key=len, reverse=True)) + r")(\d{4}|Current)$"
)


def _summary_value(items: dict, field: str) -> Any:
    for entry in items[1]["summary"].values():
        if entry.get("field") == field:
            return entry.get("value")
    return None


def _relations(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for record in records:
        if record.get("pass") != "shareholders":
            continue
        for rel in record["data"].get("relationships") or []:
            if not isinstance(rel, dict):
                continue
            for me, other in (("member_a", "member_b"), ("member_b", "member_a")):
                if rel.get(me):
                    found.setdefault(norm_person(rel[me]), []).append(
                        f"{rel.get('relation') or 'có quan hệ'} với {rel.get(other) or '?'}")
    return found


def _ratio_text(name: str, value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}".replace(".", ",") if name == "current_ratio" else fm.pct(value)


def build_appendix_context(result: dict[str, Any], records: list[dict[str, Any]],
                           financials: dict[str, Any], as_of: date) -> dict[str, str]:
    items = result["items"]
    borrowers = {norm_person(n) for n in result["meta"]["borrower_names"]}
    ctx: dict[str, str] = {}

    # 1.1 Thông tin cơ bản
    ctx["TenDoanhNghiep"] = _summary_value(items, "company_name") or NO_INFO
    ctx["MST"] = _summary_value(items, "tax_code") or NO_INFO
    founded = _summary_value(items, "establishment_date")
    founded_date = parse_date(founded)
    ctx["NamThanhLap"] = str(founded_date.year) if founded_date else (str(founded) if founded else NO_INFO)
    number = _summary_value(items, "registration_change_number")
    latest = _summary_value(items, "latest_change_date")
    parts = [f"Lần đầu: {founded}" if founded else "", f"Thay đổi lần {number}: {latest}" if number or latest else ""]
    ctx["DKKD"] = "; ".join(p for p in parts if p) or NO_INFO
    ctx["NguoiDaiDien"] = _summary_value(items, "legal_representatives") or NO_INFO
    ctx["TinhTrangHoatDong"] = _summary_value(items, "operating_status") or "Chưa có kết quả tra cứu"
    ctx["TruSoChinh"] = _summary_value(items, "head_office_address") or NO_INFO

    # 1.2 Thành viên góp vốn
    reps = {norm_person(r.get("name")): r for r in items[3]["summary"].get("legal_representatives", [])}
    relations = _relations(records)
    members = items[2]["summary"].get("members", [])
    for index in range(max(3, len(members))):
        n = index + 1
        if index >= len(members):
            ctx.update({f"ThanhVien{n}": "", f"MoiQuanHe{n}": "", f"TyLe{n}": "", f"ThayDoi{n}": ""})
            continue
        member = members[index]
        key = norm_person(member.get("name"))
        relation = ["Khách hàng vay vốn"] if key in borrowers else []
        relation += relations.get(key, [])
        if key in reps:
            relation.append("Người đại diện theo pháp luật")
        pct = member.get("ownership_pct")
        changes = []
        if within_lookback(member.get("acquisition_date"), as_of):
            changes.append(f"Có — nhận vốn góp ngày {member['acquisition_date']}")
        rep = reps.get(key)
        if rep and within_lookback(rep.get("appointed_date"), as_of):
            changes.append(f"Có — bổ nhiệm NĐDPL ngày {rep['appointed_date']}")
        ctx[f"ThanhVien{n}"] = member.get("name") or NO_INFO
        ctx[f"MoiQuanHe{n}"] = "; ".join(relation) or "—"
        ctx[f"TyLe{n}"] = "—" if pct is None else f"{float(pct):.2f}".rstrip("0").rstrip(".").replace(".", ",") + "%"
        ctx[f"ThayDoi{n}"] = "; ".join(changes) or "Không"

    # 3. Tài chính
    ctx["NguonTaiChinh"] = fm.sources_text(financials)
    interim = financials.get("interim") or {}
    ctx["NamHienTai"] = interim.get("period") or str(as_of.year)
    periods = {**financials["years"], "Current": interim}
    for name, field in FIGURE_PREFIXES.items():
        for label, fig in periods.items():
            ctx[f"{name}{label}"] = fm.fmt(fig.get(field))
    for name, ratio in RATIO_PREFIXES.items():
        for label, values in financials["ratios"].items():
            ctx[f"{name}{label}"] = _ratio_text(ratio, values.get(ratio))
    return ctx


def fill_missing_financial_names(names: set[str], ctx: dict[str, str]) -> None:
    """A financial cell for a year with no statement is "—", not a question for the LLM."""

    for name in names:
        if name not in ctx and FINANCIAL_NAME.match(name):
            ctx[name] = "—"


def borrower_ownership(items: dict, borrower_names: list[str]) -> float | None:
    """Total % the individual borrower(s) hold, when printed or computed."""

    total, found = 0.0, False
    for row in items[2]["summary"].get("borrowers") or []:
        if row.get("ownership_pct") is not None:
            total += float(row["ownership_pct"])
            found = True
    return total if found else None


def bad_corp_signals(items: dict, financials: dict[str, Any], as_of: date) -> list[str]:
    """Facts the guidance lists under Bad Corp that code can see for sure."""

    signals = [f"Pháp lý: {f['message']}" for f in items[1]["findings"] if f["severity"] == "alert"]
    founded = parse_date(_summary_value(items, "establishment_date"))
    if founded and (as_of - founded).days < 365:
        signals.append(f"Pháp lý: thời gian thành lập dưới 12 tháng (thành lập {founded:%d/%m/%Y})")
    signals += [f"Tài chính: {w}" for w in financials.get("warnings") or []]
    return signals
