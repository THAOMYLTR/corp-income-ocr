# Corp Income — Technical Solution

## 0. Scope

BRD *Corp Income Assessment*, sheet **Corp income (detail)**, use case **Pháp lý doanh
nghiệp**, items 1–4 (rows transcribed in `docs/BRD_corp_income_items_1-4.xlsx`). The
structure follows the SME repo's `refactor/ui-driven-inputs` branch so the two can share
infrastructure and, later, one upload screen.

| | SME repo | This repo |
|---|---|---|
| Graph | discover → classify → gap check → extract → reference data → specialist | same nodes, one branch (`single_corp_income`) |
| Agents | 4 LLM specialists | `CORP_INCOME_AGENT`, no LLM (checks + template in code) |
| Extraction passes | BCTC, proposal, CIC S10A/R20, site visit, ledger | M1–M4, one per BRD item |
| Upload boxes | 7 | the same 7 |
| Deterministic step | financial ratios, credit need | `legal_checks.py` (BRD B6) |
| Reading | PDF OCR, Excel, CSV, XML, PPTX | + PDF text layer, photos, Word |
| LLM | ChatOpenAI | + `LLM_PROVIDER` = anthropic / databricks |

## 0b. Phụ lục 01 — the report the credit officer receives

Template: `src/templates/corp-income-structure.md` (the user's "PHỤ LỤC 01 - THẨM ĐỊNH NGUỒN
THU DOANH NGHIỆP"). Guidance: `config/prompts/corp_income_guidance.md` (verbatim).

| Template part | Filled by | Where |
|---|---|---|
| 1.1, 1.2 (tên, MST, năm TL, ĐKKD, NĐDPL, tình trạng, thành viên, tỷ lệ, thay đổi 12 tháng) | code, from M1–M3 + checks | `src/utils/report/appendix_context.py` |
| 3. Bảng tài chính + chỉ số (biến động DT, ROS, thanh toán hiện hành), cột lịch sử mục 5 | code, from M5 (`financial_extraction`) | `src/agents/calculator/financial_metrics.py` |
| Thu nhập DN ghi nhận = (LNST − nghĩa vụ TDH + khấu hao) × tỷ lệ góp vốn | code (missing parts listed) | `financial_metrics.income_estimate` |
| Nhận xét, 2. HĐKD, 4. CIC, 5. kế hoạch, 6. kết luận + phân nhóm Bad/Normal/Good Corp | one LLM call (`report_writer_llm`) with the guidance, the code-filled values, checks, ratios, Bad-Corp signals and document excerpts | `src/agents/report_writer.py`, `config/prompts/report_writer.md` |

The LLM returns `{placeholder: text}` only for cells code left empty, so it can neither move
the layout nor change a number. A cell it cannot support reads "Chưa có thông tin trong hồ sơ".
The step log says how many cells each side filled; `corp_income.json → meta.llm_placeholders`
lists the LLM's.

## 1. BRD steps → code

| BRD step | Meaning | Where |
|---|---|---|
| B1 OCR output | read the customer's papers | `src/utils/reading/` + `config/prompts/*_extraction.md` |
| B2 Internal data | BCDE/BEP/DBX (KHDN ETC TCB) | `ho_so_noi_bo/` printouts (type `du_lieu_noi_bo`) or `process(internal_data=…)` |
| B3 External data | Cổng ĐKDN, cơ quan thuế, BHXH | `ho_so_noi_bo/` lookups (`tra_cuu_dkdn`, `tra_cuu_no_thue_bhxh`) or `process(external_data=…)` |
| B4 Fraud detection | AML/BL/WL | `process(watchlist=…)`; tamper detection out of scope |
| B5 Site visit / RBO | field report | `ho_so_soan_thao_noi_bo/` (type `bao_cao_thuc_dia`) |
| B6 Kiểm tra cụ thể | the checks | `src/agents/calculator/legal_checks.py` |

Each record carries its **source** (customer / field / external / internal). When sources
disagree, the summary shows external > customer > field > internal, and the finding lists all.

## 2. Checks (finding codes)

**Mục 1** — `tax_code_match` / `tax_code_mismatch` 🔴 · `name_mismatch` · `address_mismatch` ·
`establishment_mismatch` · `capital_mismatch` · `rep_mismatch` · `status_active` /
`status_not_active` 🔴 / `status_unknown` · `changes_12m` · `internal_current` / `internal_stale` /
`internal_absent` · `site_operating` / `site_not_operating` 🔴 / `site_unconfirmed` ·
`watchlist_company` 🔴.

**Mục 2** — `ownership_100` / `ownership_not_100` / `ownership_incomplete` ·
`capital_sum_mismatch` · `member_mismatch` · `transfer_12m` · `borrower_member` /
`borrower_not_member` / `borrower_new_member` 🔴 · `corporate_members` · `relationships` ·
`watchlist_member` 🔴.

**Mục 3** — `rep_match` / `rep_mismatch` / `no_rep` 🔴 · `rep_changed_12m` 🔴 ·
`operator_is_rep` / `operator_differs` / `operator_unknown` · `people_met` · `watchlist_rep` 🔴.
Leadership-capability assessment: removed per the BRD dependency note.

**Mục 4** — `thue_debt` / `bhxh_debt` 🔴 (count > 90 days) · `thue_clear` / `bhxh_clear` ·
`thue_unverified` / `bhxh_unverified` · `thue_conflict` / `bhxh_conflict` 🔴 · `penalty_open` /
`penalty_remediated` · `enforcement` 🔴 · `dispute` (🔴 when it affects operations/collateral) ·
`site_risk` · `inspection`.

A 12-month window ends at `loan_date`. Dates printed as month or year only count as the end of
that period (the conservative reading for "changed in the last 12 months").

## 3. Changing behaviour

| To change | Edit |
|---|---|
| Which documents are recognised, in which box, which BRD item reads them | `src/agents/documents/document_matrix.yaml` |
| What a pass extracts | `config/prompts/<item>_extraction.md` (keep the keys `legal_checks.py` reads) |
| A check | `src/agents/calculator/legal_checks.py` (one function per item) |
| The report layout | `src/templates/corp-income-structure.md` |
| The Excel layout | `src/utils/report/excel_export.py` |

Run the tests after any change (README, "Tests").

## 4. Cost

LLM calls per run = classification tie-breaks (only unsure documents) + Σ over documents of the
BRD items each feeds. A typical dossier of 8–12 files ≈ 15–25 calls. Digital PDFs skip OCR;
with `OCR_CACHE_DIR` on a Volume, re-runs do not OCR again.
