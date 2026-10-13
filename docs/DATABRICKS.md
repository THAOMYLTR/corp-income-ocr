# Running on Databricks — step by step

## 1. Get the code (once)

1. Left sidebar **Workspace** → your folder → **Create → Git folder**.
2. Git URL: this repo's URL. Branch: `main`. **Create**.
3. Later updates: open the folder → **⋮ → Git → Pull**.

## 2. Install Tesseract on the cluster (once per cluster)

OCR needs the Tesseract program with Vietnamese, which clusters do not have.

1. In the Git folder, note the path of `scripts/install_tesseract.sh`
   (e.g. `/Workspace/Users/<you>/corp-income-ocr/scripts/install_tesseract.sh`).
2. **Compute → your cluster → Edit → Advanced options → Init scripts** → Source *Workspace* →
   paste that path → **Add** → **Confirm and restart**.
3. Use access mode **Single user** (dedicated). Shared clusters often block init scripts.

Check: after restart, cell ③ of the notebook prints `Tesseract: /usr/bin/tesseract`.

## 3. Store the API key as a secret (once)

Ask your workspace admin for a secret scope, or create one with the Databricks CLI:

```bash
databricks secrets create-scope corp-income
databricks secrets put-secret corp-income anthropic-key
```

In the notebook: `dbutils.secrets.get("corp-income", "anthropic-key")`. Never paste a key into
a cell — notebooks get shared and versioned.

Using a **model serving endpoint** instead? No key needed: cell ② option B reads the
workspace URL and your token from the notebook context.

## 4. Hồ sơ đầu vào — put the dossier in a Volume

**Catalog → your catalog/schema → Volume → Upload**, keeping this folder layout:

```
/Volumes/<catalog>/<schema>/<volume>/khdn_abc/
├── ho_so_phap_ly/                 GCN_DKDN.pdf, dieu_le.pdf, so_dang_ky_thanh_vien.pdf, QD_bo_nhiem_GD.pdf
├── ho_so_thue_bhxh_tranh_chap/    thong_bao_no_thue.pdf, QD_xu_phat.pdf, ban_an.pdf …
├── bao_cao_thuc_dia/              bao_cao_thuc_dia.pdf (any file here is treated as a field report)
├── tra_cuu_ben_ngoai/             masothue_0101234567.pdf, cong_dkdn.png (saved pages)
└── ho_so_khac/                    anything else
```

The folder decides the group; inside a group the file name and content decide the exact
type (filename matches count 3×, so `GCN_DKDN_ABC.pdf` beats `scan001.pdf`). If one file
is not recognised, name its type in `TYPE_OVERRIDES` (types are listed in
`corp_income/document_types.yaml`).

## 5. Run the notebook

Open `corp_income_notebook.ipynb`, attach the cluster.

| Cell | What to do | What you should see |
|---|---|---|
| ① | nothing (installs packages, restarts Python) | — |
| ② | **choose A/B/C, fill model + secret** | your settings, keys masked |
| ③ | nothing | `Kết nối OK: {"ok": true}` and the Tesseract path |
| ④ | **set `DOSSIER`, `OUTPUT_DIR`, `LOAN_DATE`, `BORROWER_NAMES`** | — |
| ⑤ | nothing (no LLM calls) | table of files, their folder, a first guess of type |
| ⑥ | nothing | one conclusion per BRD item, then a line per file |
| ⑦ | nothing | paths of the saved files |
| ⑧ ⑨ | nothing | the report; tables of how each file was read and what was extracted |

## 6. When something goes wrong

| Message | Meaning → fix |
|---|---|
| `LLM settings incomplete: - anthropic_api_key is empty` | Cell ② — the secret returned nothing or the wrong option is active |
| `401` / `authentication_error` | Wrong or expired key |
| `404` / `not_found` | Wrong model name (or endpoint name for option B) or wrong base URL |
| `TesseractNotFoundError` / `Tesseract: ❌` | Init script not applied → check step 2, restart the cluster |
| Vietnamese OCR is gibberish | `tesseract-ocr-vie` missing → step 2 |
| A file shows type `khac`, no items extracted | Move it to the right folder, rename it, or add it to `TYPE_OVERRIDES` |
| A field is wrong | Open `ocr/<file>.txt` in the run folder: wrong there = scan quality; right there = extraction — tighten that item's prompt in `corp_income/prompts/` |
| Slow | Normal: one LLM call per file per BRD item (a GCN = 3 calls). Raise `requests_per_minute` in cell ② if your quota allows; set `OCR_CACHE_DIR` so re-runs skip OCR |
| `ModuleNotFoundError: corp_income` | The notebook is not in the repo root, or cell ② was skipped |

## 7. Costs and speed

- LLM calls = Σ over files of the BRD items that file feeds (see `passes` in
  `document_types.yaml`). Typical dossier of 8–12 files ≈ 15–25 calls.
- Digital PDFs are read from their text layer (seconds); scans are OCR'd (≈1–3 s per page,
  pages in parallel). With `OCR_CACHE_DIR` on a Volume, a re-run of the same files does not
  OCR again.
