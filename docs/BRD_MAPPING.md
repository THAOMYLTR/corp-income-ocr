# BRD → code

Source: *Corp Income Assessment*, sheet **Corp income (detail)**, use case **Pháp lý doanh
nghiệp**, items 1–4 (transcribed in `docs/BRD_corp_income_items_1-4.xlsx`). Each BRD row has
steps B1–B6; this is where each one lives.

| BRD step | Meaning | Code |
|---|---|---|
| B1 OCR output | read the customer's papers | `corp_income/reading/` (text layer → Tesseract) + `prompts/<item>.md` |
| B2 Internal data | BCDE/BEP/DBX for KHDN ETC TCB | `INTERNAL_DATA` in notebook cell ④ (same JSON shape as the prompt) |
| B3 External data | Cổng ĐKDN, cơ quan thuế, BHXH | files in `tra_cuu_ben_ngoai/`, or `EXTERNAL_DATA` |
| B4 Fraud detection | AML/BL/WL lists | `WATCHLIST` (name / MST / CCCD match). Tamper detection: out of scope |
| B5 Site visit / RBO | field report | files in `bao_cao_thuc_dia/` |
| B6 Kiểm tra cụ thể | the checks | `corp_income/checks.py` — codes below |

Severity: 🔴 `alert` (cảnh báo) · 🟠 `warning` (cần làm rõ) · 🔵 `info` · 🟢 `ok`.

## Mục 1 — Thông tin cơ bản về pháp lý doanh nghiệp (`check_legal_basic`)

| BRD B6 check | Finding code(s) |
|---|---|
| Tên DN có khớp không | `name_match` / `name_mismatch` |
| MST có khớp tuyệt đối giữa các nguồn | `tax_code_match` / `tax_code_mismatch` 🔴 / `tax_code_missing` |
| Trạng thái hoạt động (ĐKDN, thuế, masothue) | `status_active` / `status_not_active` 🔴 / `status_unknown` |
| Thay đổi tên/vốn/địa chỉ/ĐDPL/thành viên trong 12 tháng | `changes_12m` |
| Hệ thống nội bộ đã cập nhật theo GCN/external chưa | `internal_current` / `internal_stale` / `internal_absent` |
| Cảnh báo nếu tên, TSC, ĐDPL, năm thành lập không phù hợp | `name_mismatch`, `address_mismatch`, `rep_mismatch`, `establishment_mismatch`, `capital_mismatch` |
| B5 hoạt động thực tế tại địa chỉ | `site_operating` / `site_not_operating` 🔴 / `site_unconfirmed` |
| B4 DN thuộc AML/BL/WL | `watchlist_company` 🔴 |

## Mục 2 — Cổ đông, thành viên góp vốn (`check_shareholders`)

| BRD B6 check | Finding code(s) |
|---|---|
| Tỷ lệ sở hữu có đủ và hợp lý | `ownership_100` / `ownership_not_100` / `ownership_incomplete` / `capital_sum_mismatch` |
| Chuyển nhượng vốn gần thời điểm vay | `transfer_12m` |
| Cổ đông pháp nhân nhiều tầng có minh bạch | `corporate_members` |
| Biến động sở hữu, quan hệ giữa chủ sở hữu | `member_mismatch`, `relationships` |
| Tỷ lệ sở hữu + thời điểm nhận vốn của KH cá nhân vay vốn | `borrower_member` / `borrower_not_member` |
| Cảnh báo: KH cá nhân mới nhận vốn góp trong 12 tháng | `borrower_new_member` 🔴 |
| B4 cổ đông thuộc AML/WL/BL | `watchlist_member` 🔴 |

## Mục 3 — Người đại diện pháp luật (`check_legal_rep`)

| BRD B6 check | Finding code(s) |
|---|---|
| Người đại diện theo pháp luật từ các nguồn | `rep_match` / `rep_mismatch` / `no_rep` |
| Người đại diện/điều hành có thay đổi gần đây | `rep_changed_12m` 🔴 |
| Người điều hành thực tế (B3 site visit/RBO) | `operator_is_rep` / `operator_differs` / `operator_unknown`, `people_met` |
| B4 AML/WL/BL | `watchlist_rep` 🔴 |
| ~~Đánh giá năng lực, kinh nghiệm ban lãnh đạo~~ | removed per BRD dependency note — not implemented |

## Mục 4 — Nợ thuế, BHXH, phạt hành chính, tranh chấp (`check_liabilities`)

| BRD B6 check | Finding code(s) |
|---|---|
| Có nợ thuế/BHXH không; số tiền, thời gian kéo dài | `thue_debt` 🔴, `bhxh_debt` 🔴 (count > 90 days) / `thue_clear`, `bhxh_clear` / `thue_unverified`, `bhxh_unverified` |
| Nguồn mâu thuẫn (xác nhận không nợ vs có nợ) | `thue_conflict`, `bhxh_conflict` 🔴 |
| Quyết định cưỡng chế/xử phạt | `enforcement` 🔴, `penalty_open` / `penalty_remediated` |
| Vi phạm đã khắc phục chưa | `penalty_open` / `penalty_remediated` |
| Tranh chấp ảnh hưởng hoạt động/TSBĐ/dòng tiền | `dispute` (🔴 when it affects operations/collateral) |
| B5 rủi ro môi trường/PCCC tại địa điểm | `site_risk` |
| Kết luận thanh tra | `inspection` |

## Changing a rule

- A field the LLM should read → add it to the JSON schema in `prompts/<item>.md`.
- A check → `checks.py` (each item is one function; findings are added with `add(code, severity, message, evidence)`).
- Which documents feed which item → `passes:` in `document_types.yaml`.
- Run `python testing/run_checks.py` after any change.
