"""Placeholders of "Phụ lục 01 - Thẩm định nguồn thu doanh nghiệp" filled in code.

Rule of thumb: a FACT read off a document, a NUMBER, a CHECK or a GROUP is filled
here (same input → same report). Only what needs reading free text and judging
it — business activity (mục 2), addresses, the business-plan comment and the
wording of the final conclusion — is left to the report writer LLM, which sees
every value below so its text cannot contradict them.

Changes for the BRD of 16/10/2026 are tagged [BRD 16/10]:
  - 1.1 source priority per field (ĐKKD → Điều lệ/Sổ cổ đông → báo cáo thực địa),
    T24 ID, "Đăng ký lần đầu … thay đổi lần thứ …", status in bold red when the
    company does not operate, and a "không khớp" mark.
  - The two legal comments are written in code from the checks.
  - 3. VAT column, TT133 note, the financial comment and the finance group.
  - 4. CIC table, dates, credit quality and the bureau group (cic_metrics.py).
  - 5. Plan columns computed from the plan; the table is hidden without a plan.
  - 6. Corp group (Bad/Normal/Good) and the income value with its formula.
"""

from __future__ import annotations

import os
import re
from datetime import date
from typing import Any

from src.agents.calculator import cic_metrics
from src.agents.calculator import financial_metrics as fm
from src.agents.calculator.legal_checks import norm_person, parse_date, within_lookback

NO_INFO = "Chưa có thông tin"

# [BRD 16/10] Phân nhóm finance / bureau / corp is "chỉ hiển thị khi POC, không khuyến
# khích hiển thị tại credit memo ver final". Set CORP_INCOME_SHOW_GROUPS=0 to hide.
SHOW_GROUPS = os.getenv("CORP_INCOME_SHOW_GROUPS", "1") != "0"

# [BRD 16/10] 1.1: "ưu tiên ĐKKD, sau đó Điều lệ / Sổ cổ đông / Báo cáo khảo sát thực địa".
LEGAL_DOC_PRIORITY = ("gcn_dkdn", "dieu_le", "so_dang_ky_co_dong", "bao_cao_thuc_dia")
NOT_OPERATING = ("tam_ngung", "ngung_hoat_dong", "giai_the", "pha_san")
NOT_OPERATING_LABELS = ("Tạm ngừng hoạt động", "Ngừng hoạt động", "Giải thể", "Phá sản")
# Finding codes (legal_checks.py) that mean "thông tin pháp lý không phù hợp".
LEGAL_MISMATCH_CODES = ("tax_code_mismatch", "name_mismatch", "address_mismatch",
                        "establishment_mismatch", "rep_mismatch")

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
    r"^(" + "|".join(sorted({**FIGURE_PREFIXES, **RATIO_PREFIXES}, key=len, reverse=True))
    + r")(\d{4}|Current|N-1|N-2|N1|N2)$"
)


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _summary_value(items: dict, field: str) -> Any:
    for entry in items[1]["summary"].values():
        if entry.get("field") == field:
            return entry.get("value")
    return None


def _pick_by_document(records: list[dict], field: str) -> tuple[Any, str]:
    """[BRD 16/10] First non-empty value following LEGAL_DOC_PRIORITY, then any other document."""

    order = {t: i for i, t in enumerate(LEGAL_DOC_PRIORITY)}
    legal = [r for r in records if r.get("pass") == "legal_basic"]
    for record in sorted(legal, key=lambda r: order.get(r.get("document_type"), 50)):
        value = record["data"].get(field)
        if value not in (None, "", [], {}):
            if isinstance(value, list):
                value = ", ".join(str(v.get("name") if isinstance(v, dict) else v) for v in value)
            return value, record.get("document", "")
    return None, ""


def _codes(items: dict, *numbers: int) -> dict[str, dict]:
    return {f["code"]: f for n in numbers for f in items[n]["findings"]}


def _relations(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Relations between members; [BRD 16/10] the field report (thực địa) first."""

    found: dict[str, list[str]] = {}
    shareholders = [r for r in records if r.get("pass") == "shareholders"]
    shareholders.sort(key=lambda r: 0 if r.get("source") == "field" else 1)
    for record in shareholders:
        for rel in record["data"].get("relationships") or []:
            if not isinstance(rel, dict):
                continue
            for me, other in (("member_a", "member_b"), ("member_b", "member_a")):
                if rel.get(me):
                    text = f"{rel.get('relation') or 'có quan hệ'} với {rel.get(other) or '?'}"
                    if text not in found.setdefault(norm_person(rel[me]), []):
                        found[norm_person(rel[me])].append(text)
    return found


def _ratio_text(name: str, value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}".replace(".", ",") if name == "current_ratio" else fm.pct(value)


def _bullets(lines: list[str], empty: str) -> str:
    """A Markdown list on its own lines (placed after an inline label in the template)."""

    # Lines that already start with spaces are sub-items ("  + …") and keep their indent.
    return ("\n\n" + "\n".join(line if line.startswith(" ") else f"- {line}" for line in lines)
            if lines else empty)


def _age(founded: date | None, as_of: date) -> str:
    if not founded:
        return ""
    months = (as_of.year - founded.year) * 12 + as_of.month - founded.month - (as_of.day < founded.day)
    return f"{months // 12} năm {months % 12} tháng" if months >= 0 else ""


def borrower_ownership(items: dict, borrower_names: list[str]) -> float | None:
    """Total % the individual borrower(s) hold, when printed or computed."""

    total, found = 0.0, False
    for row in items[2]["summary"].get("borrowers") or []:
        if row.get("ownership_pct") is not None:
            total += float(row["ownership_pct"])
            found = True
    return total if found else None


def business_type(records: list[dict]) -> tuple[str, str]:
    """[BRD 16/10] Loại hình chính (field report / internal first) for the bureau threshold."""

    ranked = sorted((r for r in records if r.get("pass") == "legal_basic"),
                    key=lambda r: {"field": 0, "internal": 1}.get(r.get("source"), 2))
    for record in ranked:
        if record["data"].get("business_type"):
            return record["data"]["business_type"], record["data"].get("business_type_note") or ""
    return "", ""


# --------------------------------------------------------------------------- #
# [BRD 16/10] corp group — mục 6 "Phân nhóm doanh nghiệp"
# --------------------------------------------------------------------------- #
def corp_group(items: dict, financials: dict, cic: dict, as_of: date) -> dict[str, Any]:
    """Bad corp if ANY criterion; Good corp if Good finance AND Good bureau; else Normal."""

    codes = _codes(items, 1)
    bad: list[str] = []
    if "status_not_active" in codes:
        bad.append("Pháp lý: " + codes["status_not_active"]["message"])
    for code in LEGAL_MISMATCH_CODES:
        if code in codes and codes[code]["severity"] == "alert":
            bad.append("Pháp lý: " + codes[code]["message"])
    founded = parse_date(_summary_value(items, "establishment_date"))
    if founded and (as_of - founded).days < 365:
        bad.append(f"Pháp lý: thời gian thành lập dưới 12 tháng (thành lập {founded:%d/%m/%Y})")
    if "site_not_operating" in codes:
        bad.append("Hoạt động kinh doanh: " + codes["site_not_operating"]["message"])
    if financials["group"] == "Bad finance":
        bad.append("Tài chính: thuộc nhóm Bad finance — " + financials["group_reason"])
    if cic["group"] == "Bad bureau":
        bad.append("Tín dụng: thuộc nhóm Bad bureau — " + cic["group_reason"])
    if bad:
        group = "Bad corp"
    elif financials["group"] == "Good finance" and cic["group"] == "Good bureau":
        group = "Good corp"
    else:
        group = "Normal corp"
    return {"group": group, "bad_reasons": bad,
            "finance": f"{financials['group']} ({financials['group_reason']})",
            "bureau": f"{cic['group']} ({cic['group_reason']})"}


# --------------------------------------------------------------------------- #
# main builder
# --------------------------------------------------------------------------- #
def build_appendix_context(result: dict[str, Any], records: list[dict[str, Any]],
                           financials: dict[str, Any], as_of: date,
                           cic: dict[str, Any] | None = None,
                           corp: dict[str, Any] | None = None,
                           income: dict[str, Any] | None = None) -> dict[str, str]:
    items = result["items"]
    borrower_names = result["meta"]["borrower_names"]
    borrowers = {norm_person(n) for n in borrower_names}
    codes = _codes(items, 1, 2, 3)
    ctx: dict[str, str] = {}

    # ---- 1.1 Thông tin cơ bản [BRD 16/10: field priority + mismatch mark] -----------
    def legal_cell(field: str, mismatch_code: str = "") -> str:
        value, _ = _pick_by_document(records, field)
        value = value or _summary_value(items, field)
        if not value:
            return NO_INFO
        mark = " ⚠ không khớp giữa các nguồn" if mismatch_code in codes else ""
        return f"{value}{mark}"

    ctx["TenDoanhNghiep"] = legal_cell("company_name", "name_mismatch")
    ctx["MST"] = legal_cell("tax_code", "tax_code_mismatch")
    ctx["NguoiDaiDien"] = legal_cell("legal_representatives", "rep_mismatch")
    t24, _ = _pick_by_document(records, "t24_id")
    ctx["T24ID"] = str(t24) if t24 else "Chưa có thông tin (tra cứu MST trên T24)"
    founded_text, _ = _pick_by_document(records, "establishment_date")
    founded_text = founded_text or _summary_value(items, "establishment_date")
    founded = parse_date(founded_text)
    number, _ = _pick_by_document(records, "registration_change_number")
    latest, _ = _pick_by_document(records, "latest_change_date")
    note = "; ".join(x for x in (
        f"Đăng ký lần đầu {founded_text}" if founded_text else "",
        "thay đổi lần thứ " + " ".join(y for y in (str(number) if number not in (None, "") else "",
                                                   f"ngày {latest}" if latest else "") if y)
        if number not in (None, "") or latest else "") if x)
    ctx["NamThanhLap"] = (f"{founded.year} ({note})" if founded else note or NO_INFO) + (
        " ⚠ không khớp giữa các nguồn" if "establishment_mismatch" in codes else "")
    ctx["DKKD"] = note or NO_INFO
    status = _summary_value(items, "operating_status")
    if not status:
        ctx["TinhTrangHoatDong"] = "Chưa có kết quả tra cứu (masothue.com / Cổng ĐKDN)"
    elif status in NOT_OPERATING_LABELS or "status_not_active" in codes:
        # [BRD 16/10] "Bôi đỏ, đậm nếu doanh nghiệp không hoạt động / tạm dừng hoạt động"
        ctx["TinhTrangHoatDong"] = f'<b><span style="color:#C00000">{status}</span></b>'
    else:
        ctx["TinhTrangHoatDong"] = str(status)

    # ---- 1.2 Thành viên góp vốn ---------------------------------------------------
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
        if key in reps:
            relation.append("Người đại diện theo pháp luật")   # [BRD 16/10] note if NĐDPL
        relation += relations.get(key, [])
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

    # ---- Nhận xét pháp lý [BRD 16/10: written in code from the checks] ------------
    entity_warnings = [f["message"] for f in items[1]["findings"] if f["severity"] in ("alert", "warning")]
    ctx["NhanXetPhapLyDN"] = _bullets([f"⚠ {w}" for w in entity_warnings],
                                      "Thông tin pháp lý cơ bản khớp giữa các nguồn; không ghi nhận cảnh báo.")
    lines = []
    age = _age(founded, as_of)
    if age:
        lines.append(f"Doanh nghiệp đã hoạt động {age} (đăng ký lần đầu {founded:%d/%m/%Y}).")
    if borrower_names:
        pct = borrower_ownership(items, borrower_names)
        is_rep = any(norm_person(n) in reps for n in borrower_names)
        lines.append(f"KH cá nhân vay vốn {', '.join(borrower_names)} nắm giữ "
                     + (f"{pct:g}% vốn góp".replace(".", ",") if pct is not None else "tỷ lệ vốn góp chưa xác định")
                     + f"; {'là' if is_rep else 'không phải là'} người đại diện theo pháp luật của doanh nghiệp.")
    else:
        lines.append("Chưa khai báo KH cá nhân vay vốn (BORROWER_NAMES) — chưa xác định tỷ lệ góp vốn.")
    warn = [codes[c]["message"] for c in LEGAL_MISMATCH_CODES if c in codes]
    warn += [codes[c]["message"] for c in ("status_not_active", "status_unknown") if c in codes]
    warn += [f["message"] for f in items[2]["findings"]
             if f["code"] in ("ownership_not_100", "ownership_incomplete", "capital_sum_mismatch")]
    warn += [f["message"] for n in (2, 3) for f in items[n]["findings"]
             if f["severity"] == "alert" and f["message"] not in warn]
    if warn:
        lines.append("Cảnh báo pháp lý cần đánh giá lại:")
        lines += [f"  + {w}" for w in warn]
    ctx["NhanXet"] = _bullets(lines, NO_INFO)

    # ---- 3. Tài chính -------------------------------------------------------------
    ctx["NguonTaiChinh"] = fm.sources_text(financials)
    interim = financials.get("interim") or {}
    vat = financials.get("vat") or {}
    ctx["NamHienTai"] = interim.get("period") or (
        f"{vat['current_year']} (đến T{max(vat['by_year'][vat['current_year']]['months']):02d})"
        if vat.get("current_year") else str(as_of.year))
    periods = {**financials["years"], "Current": interim}
    for name, field in FIGURE_PREFIXES.items():
        for label, fig in periods.items():
            ctx[f"{name}{label}"] = fm.fmt(fig.get(field))
    if not interim.get("net_revenue") and vat.get("current_year"):
        # [BRD 16/10] Nguyên tắc 2: "Cập nhật các tháng năm N" = doanh thu theo tờ khai VAT
        ctx["DTTCurrent"] = f"{fm.fmt(vat['by_year'][vat['current_year']]['revenue'])} (tờ khai VAT)"
    for name, ratio in RATIO_PREFIXES.items():
        for label, values in financials["ratios"].items():
            ctx[f"{name}{label}"] = _ratio_text(ratio, values.get(ratio))

    # [BRD 16/10] Relative years, so the template does not hard-code 2024 / 2025:
    #   N-1 = the latest full year with a BCTC in the dossier (else the year before the
    #   loan date), N-2 = the year before it. Headers: {{Nam-1}}, {{Nam-2}};
    #   cells: {{DTTN-1}}, {{TongTaiSanN-2}}, {{ROSN-1}} … ("N1"/"N2" also accepted).
    n1 = financials.get("latest_year") or str(as_of.year - 1)
    n2 = str(int(n1) - 1)
    ctx["Nam-1"], ctx["Nam-2"] = n1, n2
    for prefix in (*FIGURE_PREFIXES, *RATIO_PREFIXES):
        for alias, year in (("N-1", n1), ("N-2", n2), ("N1", n1), ("N2", n2)):
            ctx[f"{prefix}{alias}"] = ctx.get(f"{prefix}{year}", "—")

    fin_lines = ["**Cảnh báo dấu hiệu bất thường của BCTC**"]
    fin_lines += [f"- ⚠ {w}" for w in financials["material_warnings"]] or ["- Không ghi nhận mâu thuẫn trọng yếu"]
    fin_lines += [f"- {w}" for w in financials["other_warnings"]]
    derived = {f for fig in financials["years"].values() for f in fig.get("_derived", [])}
    if {"current_assets", "current_liabilities"} & derived:   # only the TT133 derivation
        fin_lines.append("- Ghi chú: BCTC không chia ngắn hạn/dài hạn (TT133) — TSNH/TSDH/nợ ngắn hạn được tính "
                         "theo Nguyên tắc 1")
    fin_lines.append("\n**Nhận xét về trạng thái tài chính của KH**")
    fin_lines += [f"- {s}" for s in financials["status_remarks"]] or ["- Chưa có BCTC để đánh giá"]
    if vat.get("text"):
        fin_lines.append(f"- {vat['text']}")
    if SHOW_GROUPS:
        fin_lines.append(f"\n_Phân nhóm tài chính (POC):_ **{financials['group']}** — {financials['group_reason']}")
    ctx["NhanXetTaiChinh"] = "\n".join(fin_lines)

    # ---- 4. Dư nợ tại TCTD [BRD 16/10: cic_metrics.py] ----------------------------
    cic = cic or {"available": False}
    if cic.get("available"):
        ctx["NgayDuLieuCIC"] = cic["query_dates"] + "".join(f"\n\n⚠ {w}" for w in cic["warnings"])
        for prefix, key in (("TCB", "TCB"), ("OtherBank", "OtherBank"), ("Total", "Total")):
            row = cic["rows"][key]
            ctx[f"{prefix}_ST"] = fm.fmt(row["short_term"])
            ctx[f"{prefix}_MLT"] = fm.fmt(row["long_term"])
            ctx[f"{prefix}_Other"] = fm.fmt(row["other"])
            ctx[f"{prefix}_CKNB"] = fm.fmt(row["off_balance"])
            ctx[f"{prefix}_Total" if prefix != "Total" else "Total_Credit"] = fm.fmt(row["total"])
            # No R20 → collateral unknown, not zero.
            ctx[f"{prefix}_Collateral"] = fm.fmt(row["collateral"]) if cic.get("has_r20") else "—"
            if prefix != "Total":
                ctx[f"{prefix}_CollateralOwner"] = ", ".join(sorted(row["owners"])) or "—"
        ctx["SpecialMention"] = cic_metrics.describe_items(cic["special_mention"], "nợ cần chú ý trong 12 tháng gần nhất")
        ctx["BadDebt"] = cic_metrics.describe_items(cic["bad_debt"], "nợ xấu trong 05 năm gần nhất")
        ctx["CreditQuality"] = ("Không có nợ cần chú ý trong 12 tháng và nợ xấu trong 05 năm gần nhất"
                                if not cic["special_mention"] and not cic["bad_debt"]
                                else "Có phát sinh nợ cần chú ý / nợ xấu — xem chi tiết bên dưới")
        duno = [f"- ⚠ {w}" for w in cic["warnings"]]
        interest = fm.interest_vs_cic(financials, cic.get("avg_balance_12m"))
        if interest:
            duno.append(f"- ⚠ {interest}")
        if cic.get("leverage") is not None:
            duno.append(f"- Dư nợ BQ 12 tháng / doanh thu BQ tháng = {cic['leverage']:.1f} (ngưỡng {cic['limit']})"
                        .replace(".", ","))
        if SHOW_GROUPS:
            duno.append(f"\n_Phân nhóm bureau (POC):_ **{cic['group']}** — {cic['group_reason']}")
        ctx["NhanXetDuNo"] = "\n".join(duno) or "Không ghi nhận cảnh báo."
    else:
        missing = "Chưa có bản tin CIC S10A/R20 trong hồ sơ"
        ctx["NgayDuLieuCIC"] = missing
        for prefix in ("TCB", "OtherBank", "Total"):
            for suffix in ("ST", "MLT", "Other", "CKNB", "Collateral"):
                ctx[f"{prefix}_{suffix}"] = "—"
        ctx.update({"TCB_Total": "—", "OtherBank_Total": "—", "Total_Credit": "—",
                    "TCB_CollateralOwner": "—", "OtherBank_CollateralOwner": "—",
                    "CreditQuality": missing, "SpecialMention": missing, "BadDebt": missing,
                    "NhanXetDuNo": missing + " — chưa đánh giá được thông tin tín dụng."})

    # ---- 5. Phương án kinh doanh [BRD 16/10: computed from the plan] --------------
    plans = [r["data"] for r in records if r.get("pass") == "plan" and r["data"].get("has_plan")]
    if plans:
        plan = plans[0]
        year = financials.get("latest_year")
        prev_revenue = (financials["years"].get(year) or {}).get("net_revenue") if year else None
        revenue, profit = plan.get("plan_revenue"), plan.get("plan_profit_after_tax")
        label = f" ({plan['plan_year']})" if plan.get("plan_year") else ""
        ctx["PAKD_DTT_KeHoach"] = fm.fmt(revenue) + label
        ctx["PAKD_TangTruong_KeHoach"] = fm.pct(revenue / prev_revenue - 1) if revenue and prev_revenue else "—"
        ctx["PAKD_LNST_KeHoach"] = fm.fmt(profit) + label
        ctx["PAKD_ROS_KeHoach"] = fm.pct(profit / revenue) if profit is not None and revenue else "—"
        ctx["PAKD_DTT_CoSo"] = (plan.get("basis") or "—").replace("\n", " ")
        ctx.update({"PAKD_TangTruong_CoSo": "", "PAKD_LNST_CoSo": "", "PAKD_ROS_CoSo": ""})
        ctx["_has_plan"] = "1"
    else:
        ctx["_has_plan"] = ""
        ctx["NhanXetPAKD"] = "Khách hàng không cung cấp phương án kinh doanh."
        for row in ("DTT", "TangTruong", "LNST", "ROS"):          # table is hidden anyway
            ctx[f"PAKD_{row}_KeHoach"] = ctx[f"PAKD_{row}_CoSo"] = ""

    # ---- 6. Kết luận — value in code; the wording of the conclusion is the LLM's ----
    if corp and income is not None:
        ctx["KetLuan"] = income_block(corp, income)
    return ctx


def income_block(corp: dict[str, Any], income: dict[str, Any]) -> str:
    """[BRD 16/10] "Giá trị nguồn thu doanh nghiệp để đánh giá năng lực trả nợ"."""

    lines = ["**Giá trị nguồn thu doanh nghiệp để đánh giá năng lực trả nợ**", ""]
    if SHOW_GROUPS:
        lines += [f"_Phân nhóm doanh nghiệp (POC):_ **{corp['group']}** — tài chính: {corp['finance']}; "
                  f"tín dụng: {corp['bureau']}", ""]
    if corp["group"] == "Bad corp":
        lines += ["Không sử dụng nguồn thu doanh nghiệp, không thực hiện đánh giá dự phóng. Cơ sở:"]
        lines += [f"- {r}" for r in corp["bad_reasons"]]
        return "\n".join(lines)
    year = income.get("year") or "N-1"
    lines += [
        f"- LNST hợp lý = LNST {year} − DT tài chính − Thu nhập khác = {fm.fmt(income['lnst'])} − "
        f"{fm.fmt(income['financial_income'] or 0)} − {fm.fmt(income['other_income'] or 0)} = "
        f"**{fm.fmt(income['reasonable_lnst'])}** triệu đồng",
        f"- LNST sử dụng để trả nghĩa vụ TDH = Nghĩa vụ gốc TDH hằng năm − Khấu hao = "
        f"{fm.fmt(income['annual_lt_principal'] or 0)} − {fm.fmt(income['depreciation'] or 0)} → "
        f"**{fm.fmt(income['lnst_for_lt_debt'])}** triệu đồng (không âm)",
        "- Lợi tức / cổ tức tối đa chia được cho KHCN = (LNST hợp lý − LNST trả nợ TDH) × tỷ lệ góp vốn"
        + (f" = **{fm.fmt(income['value'])}** triệu đồng" if income["value"] is not None else ": chưa tính được"),
    ]
    if income["missing"]:
        lines.append(f"- Thiếu dữ liệu: {'; '.join(income['missing'])}")
    return "\n".join(lines)


def fill_missing_financial_names(names: set[str], ctx: dict[str, str]) -> None:
    """A financial cell for a year with no statement is "—", not a question for the LLM."""

    for name in names:
        if name not in ctx and FINANCIAL_NAME.match(name):
            ctx[name] = "—"


# --------------------------------------------------------------------------- #
# [BRD 16/10] output conditions applied to the rendered Markdown
# --------------------------------------------------------------------------- #
_EMPTY_PARTNER_ROW = re.compile(
    r"<tr><td>(?:—|-||Chưa có thông tin(?: trong hồ sơ)?)</td>(?:<td></td>){3}</tr>")


def apply_output_conditions(markdown: str, ctx: dict[str, str]) -> str:
    """Rules the BRD states as "hiển thị khi …" rather than as a value.

    - Đầu ra / đầu vào: "hồ sơ có ít hơn 5 đối tác thì XÓA HẲN các dòng thừa".
    - Phương án kinh doanh: "TH không có phương án kinh doanh, ẩn đi bảng tính này".
    """

    markdown = _EMPTY_PARTNER_ROW.sub("", markdown)
    if not ctx.get("_has_plan"):
        out, in_section = [], False
        for line in markdown.split("\n"):
            if line.startswith("### 5."):
                in_section = True
            elif line.startswith("### ") or line.startswith("**Nhận xét về phương án"):
                in_section = False
            if in_section and line.lstrip().startswith("|"):
                continue
            out.append(line)
        markdown = "\n".join(out)
    return markdown
