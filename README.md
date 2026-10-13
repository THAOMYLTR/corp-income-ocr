# Corp Income OCR — pháp lý doanh nghiệp (BRD mục 1–4)

Reads a **corporate (KHDN) loan dossier**, OCRs it, extracts the fields required by the BRD
*Corp Income Assessment* → use case **"Pháp lý doanh nghiệp"**, runs the BRD cross-checks in
code, and writes the result as **Excel + Markdown report + JSON + the OCR text of every file**.

| BRD | Sub-component | What you get |
|---|---|---|
| 1 | Thông tin cơ bản về pháp lý DN | Legal profile with a source per field; active status; MST exact match; changes in 12 months; internal data out of date; site-visit confirmation |
| 2 | Cổ đông, thành viên góp vốn | Members table (%, capital, date acquired); ownership totals; transfers in 12 months; **borrower received capital in 12 months → alert** |
| 3 | Người đại diện pháp luật | Legal rep(s) vs actual operator; **rep changed in 12 months → alert** (no leadership-capability assessment, per BRD) |
| 4 | Nợ thuế, BHXH, phạt, tranh chấp | Tax/BHXH debts, penalties, enforcement, inspections, disputes, remediation status |

Built from the ideas of [SME-creditmemo-multi-agent `refactor/ui-driven-inputs`](https://github.com/hodongtu/SME-creditmemo-multi-agent/tree/refactor/ui-driven-inputs):
**no user prompt, no routing** — you point it at a folder, files are grouped by the upload
folder they sit in, extraction prompts live in Markdown files, and every figure in the report
comes from a document (the LLM extracts; code checks and writes).

## Quick start (Databricks)

1. **Workspace → Create → Git folder** → this repo, branch `main`.
2. Cluster → **Init scripts** → add `scripts/install_tesseract.sh` → restart (Single-user cluster).
3. Open **`corp_income_notebook.ipynb`**, edit cell **②** (LLM: provider, model, key) and cell **④** (dossier folder, loan date, borrower name).
4. **Run all.** Results land in `OUTPUT_DIR/<dossier>_<time>/`.

Full walkthrough: **[docs/DATABRICKS.md](docs/DATABRICKS.md)**.

## Dossier layout

Put each file in the folder for its group (folder names matter; file names help):

```
khdn_abc/
├── ho_so_phap_ly/                 GCN ĐKDN, điều lệ, sổ cổ đông, chuyển nhượng vốn, QĐ bổ nhiệm
├── ho_so_thue_bhxh_tranh_chap/    thông báo nợ thuế, BHXH, QĐ xử phạt, biên bản kiểm tra, tòa án, thuyết minh BCTC
├── bao_cao_thuc_dia/              báo cáo thực địa / AI Site Visit / RBO
├── tra_cuu_ben_ngoai/             bản tra cứu Cổng ĐKDN, masothue, nợ thuế/BHXH (saved as PDF/image)
└── ho_so_khac/                    anything else (classified by content)
```

Files outside these folders still work; they are classified by name and content only.
Reads **PDF** (text layer first, OCR if scanned), **photos** (JPG/PNG/TIFF), **Word (.docx)**,
**Excel/CSV**, TXT, PPTX.

## Outputs (one folder per run)

| File | Content |
|---|---|
| `corp_income.xlsx` | Sheets: Tóm tắt · 1. Pháp lý cơ bản · 2. Cổ đông · 3. Người đại diện · 4. Nợ thuế - tranh chấp · Kiểm tra · Hồ sơ |
| `report.md` | Report laid out by `corp_income/templates/corp-income-structure.md` |
| `result.json` | Everything: files, how each was read, OCR text, extracted fields (đồng), findings |
| `ocr/<file>.txt` | What OCR / the text layer read from each file — check here first when a field is wrong |

## LLM access — one setting

`llm_provider` = `anthropic` (Anthropic API key) · `databricks` (model serving endpoint) ·
`openai` (OpenAI or any OpenAI-format gateway). Set it in notebook cell ②; cell ③ makes one
tiny call to prove the key, URL and model work before anything else runs. Missing settings
fail with a message naming exactly what to set.

## Project structure

```
corp_income_notebook.ipynb     the notebook (10 cells)
corp_income/
  settings.py                  all settings (code > env > defaults), masked printing
  llm.py                       build_llm (3 providers), JSON parsing, connection check
  reading/                     PDF text layer → OCR fallback, photos, Word, Excel (Tesseract)
  document_types.yaml          14 document types, 5 upload folders, which BRD items each feeds
  documents.py                 discovery (dedupe, skipped files listed) + classification
  prompts/*.md                 the 4 extraction prompts (BRD items 1–4) — editable
  extraction.py                runs the prompts, converts money to đồng
  checks.py                    BRD B6 checks (dates, matching, sums, 12-month windows, watchlist)
  report.py + templates/       Markdown report from a template with {{placeholders}}
  excel_export.py              the Excel workbook
  pipeline.py                  run_corp_income(...) and result.save(...)
testing/run_checks.py          python testing/run_checks.py
docs/                          DATABRICKS.md · BRD_MAPPING.md · REPORT_TEMPLATE.md · the BRD rows (xlsx)
scripts/install_tesseract.sh   cluster init script
```

## Tests

```bash
pip install -r requirements.txt
python testing/run_checks.py
```

`verify_pipeline` runs the whole flow with a fake LLM; `verify_reading` reads a real digital
PDF, a Word file, a scanned image and a scanned PDF through Tesseract; `verify_settings`
covers configuration errors and messy model replies. No API key needed.

## Limits

- Web search is not done (BRD item 1 note for the POC). Save the masothue / Cổng ĐKDN page as
  PDF into `tra_cuu_ben_ngoai/`, or pass an API result as `EXTERNAL_DATA`.
- Fraud detection (tampered documents) is out of scope; AML/BL/WL = match against the
  `WATCHLIST` you pass in.
- Customer files and outputs are git-ignored; keep them in a Volume, never in the repo.
