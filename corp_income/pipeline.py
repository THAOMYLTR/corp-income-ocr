"""The whole run: files → text → classify → extract (LLM) → BRD checks → report.

    from corp_income import run_corp_income
    result = run_corp_income(llm, ["/Volumes/.../khdn_abc"], loan_date="13/10/2026",
                             borrower_names=["Nguyễn Văn A"])
    result.save("/Volumes/.../logs/khdn_abc")   # report.md, corp_income.xlsx, result.json, ocr/*.txt

No prompt and no routing: this package does one job.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from corp_income.checks import parse_date, run_all_checks
from corp_income.documents import box_of, classify, discover
from corp_income.extraction import PASSES, extract_document, normalize_amounts
from corp_income.reading import read_document
from corp_income.report import load_template, render_markdown, unknown_placeholders
from corp_income.settings import Settings

PROVIDED_LABELS = {
    "internal": "Internal data (BCDE/BEP/DBX)",
    "external": "External data (Cổng ĐKDN/cơ quan thuế/BHXH)",
}


@dataclass
class CorpIncomeResult:
    meta: dict[str, Any]
    documents: list[dict[str, Any]]
    records: list[dict[str, Any]]
    items: dict[int, dict[str, Any]]
    steps: list[str] = field(default_factory=list)
    markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": self.meta,
            "steps": self.steps,
            "documents": self.documents,
            "records": self.records,
            "items": {str(k): v for k, v in self.items.items()},
        }

    def save(self, out_dir: str | Path) -> dict[str, Path]:
        """Write every output into ``out_dir`` (created if needed)."""

        from corp_income.excel_export import write_excel

        out = Path(out_dir)
        (out / "ocr").mkdir(parents=True, exist_ok=True)
        paths = {
            "report": out / "report.md",
            "excel": out / "corp_income.xlsx",
            "json": out / "result.json",
            "ocr": out / "ocr",
        }
        paths["report"].write_text(self.markdown, encoding="utf-8")
        data = self.to_dict()
        paths["json"].write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        write_excel(data, paths["excel"])
        for doc in self.documents:
            (out / "ocr" / f"{doc['filename']}.txt").write_text(
                f"# {doc['filename']} — read by: {doc.get('read_method') or '—'}\n\n{doc.get('content', '')}",
                encoding="utf-8",
            )
        return paths


def _provided(kind: str, provided: dict[str, Any] | None) -> list[dict[str, Any]]:
    """internal_data / external_data → records shaped like extracted ones."""

    records = []
    for pass_name, data in (provided or {}).items():
        if pass_name not in PASSES or not isinstance(data, dict):
            raise ValueError(f"{kind}_data keys must be among {PASSES}; got {pass_name!r}")
        records.append({
            "source": kind, "document": PROVIDED_LABELS[kind], "document_type": f"{kind}_data",
            "pass": pass_name, "data": normalize_amounts(pass_name, json.loads(json.dumps(data))),
        })
    return records


def run_corp_income(
    llm: Any,
    input_paths: list[str | Path] | None = None,
    *,
    loan_date: str | date | None = None,
    borrower_names: list[str] | None = None,
    internal_data: dict[str, Any] | None = None,
    external_data: dict[str, Any] | None = None,
    watchlist: list[dict[str, Any]] | None = None,
    type_overrides: dict[str, str] | None = None,
    texts: dict[str, str] | None = None,
    template_path: str | None = None,
    settings: Settings | None = None,
) -> CorpIncomeResult:
    """Run BRD items 1-4 on a dossier.

    llm            any LangChain chat model (build it with corp_income.llm.build_llm)
    input_paths    files or folders; sub-folders named like the upload boxes
                   (ho_so_phap_ly, bao_cao_thuc_dia, …) narrow classification
    loan_date      the 12-month checks end here (dd/mm/yyyy; default today)
    borrower_names individual borrower(s), for the BRD item-2 warning
    internal_data  {pass: JSON} from BCDE/BEP/DBX;  external_data: from Cổng ĐKDN/thuế/BHXH
    watchlist      [{"name", "tax_code", "id_number", "list": "AML|BL|WL"}]
    type_overrides {filename: type id} when a file cannot be recognised
    texts          {filename: text} — skip reading files (tests, re-runs)
    """

    settings = settings or Settings.load()
    started = time.monotonic()
    steps: list[str] = []
    as_of = loan_date if isinstance(loan_date, date) else (parse_date(loan_date) or date.today())
    overrides = type_overrides or {}

    files, skipped = discover(input_paths or [])
    steps.append(f"Found {len(files)} file(s)" + (f", skipped {len(skipped)}" if skipped else ""))
    steps += [f"Skipped: {s}" for s in skipped]
    jobs = [(f.name, None, f) for f in files] + [(name, text, None) for name, text in (texts or {}).items()]

    def work(job):
        filename, text, path = job
        doc = {"filename": filename, "path": str(path or ""), "box": box_of(path) if path else "",
               "read_method": "provided" if text is not None else "", "errors": {}, "passes_done": []}
        if text is None:
            try:
                text, doc["read_method"] = read_document(path, settings.ocr_timeout_seconds)
            except Exception as exc:  # one unreadable scan must not end the run
                doc.update(type="khac", label="Không đọc được", source="customer", method="none",
                           scores={}, chars=0, content="")
                doc["errors"]["read"] = f"{type(exc).__name__}: {exc}"[:300]
                return doc, []
        text = (text or "")[: settings.max_chars_per_document]
        found = classify(filename, text, doc["box"], overrides.get(filename))
        results, errors = extract_document(llm, filename, text, found["passes"])
        doc.update(type=found["type"], label=found["label"], source=found["source"],
                   method=found["method"], scores=found["scores"], chars=len(text), content=text,
                   passes_done=sorted(results), errors=errors)
        records = [{"source": found["source"], "document": filename, "document_type": found["type"],
                    "pass": name, "data": data} for name, data in results.items()]
        return doc, records

    with ThreadPoolExecutor(max_workers=max(1, min(settings.max_workers, len(jobs) or 1))) as pool:
        outcomes = list(pool.map(work, jobs))

    documents = [doc for doc, _ in outcomes]
    records = [record for _, recs in outcomes for record in recs]
    records += _provided("internal", internal_data) + _provided("external", external_data)
    for doc in documents:
        steps.append(f"{doc['filename']}: {doc['type']} ({doc['method']}, read by {doc['read_method'] or '—'})"
                     f" → {', '.join(doc['passes_done']) or 'no extraction'}"
                     + (f" | errors: {doc['errors']}" if doc["errors"] else ""))

    items = run_all_checks(records, as_of=as_of, borrower_names=borrower_names, watchlist=watchlist)
    template_text, template_source = load_template(template_path)
    meta = {
        "as_of": as_of.strftime("%d/%m/%Y"),
        "borrower_names": list(borrower_names or []),
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "seconds": round(time.monotonic() - started, 1),
        "files": len(documents),
        "template": template_source,
        "unknown_placeholders": unknown_placeholders(template_text),
        "llm": f"{settings.llm_provider}:{settings.llm_model}",
    }
    result = CorpIncomeResult(meta=meta, documents=documents, records=records, items=items, steps=steps)
    result.markdown = render_markdown({"meta": meta, "documents": documents, "items": items}, template_text)
    return result
