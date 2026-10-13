"""One entry point for reading a file: ``read_document(path) -> (text, method)``.

PDFs are the slow case. Many PDFs a bank receives are *digital* (exported from
the tax portal, Cổng ĐKDN, an accounting system) and already carry a text layer;
OCR-ing those is slower and less accurate than reading the text directly. So a
PDF is read in two steps:

1. Read the embedded text layer with pypdfium2.
2. If the text is too thin (a scan) or looks broken (old TCVN3/VNI fonts render
   Vietnamese as mojibake), fall back to Tesseract OCR.

Set ``PDF_TEXT_LAYER=0`` to always OCR.

The ``method`` returned ("pdf_text_layer", "ocr_pdf", "ocr_image", "docx",
"spreadsheet", "text"...) is written to the run log so a wrong field can be
traced to how the file was read.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Below this many readable characters per page, the PDF is treated as a scan.
MIN_CHARS_PER_PAGE = 200
# Share of characters that must look like normal Vietnamese/Latin text.
MIN_CLEAN_RATIO = 0.85
_CLEAN = re.compile(r"[0-9A-Za-zÀ-ỹĐđ\s.,;:()/%\-–—'\"!?&+*=#@_\[\]|<>]")


def _looks_clean(text: str) -> bool:
    sample = text[:20_000]
    if not sample.strip():
        return False
    return len(_CLEAN.findall(sample)) / len(sample) >= MIN_CLEAN_RATIO


def pdf_text_layer(path: str) -> tuple[str, int]:
    """Embedded text of a PDF, pages separated by '--- Page N ---' markers."""

    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(path)
    pages = []
    try:
        for index in range(len(pdf)):
            page = pdf[index]
            textpage = page.get_textpage()
            pages.append(f"--- Page {index + 1} ---\n{textpage.get_text_range().strip()}")
            textpage.close()
            page.close()
        return "\n\n".join(pages), len(pdf)
    finally:
        pdf.close()


def docx_text(path: str) -> str:
    """Paragraphs and tables of a Word file, tables as tab-separated rows."""

    import docx  # python-docx

    document = docx.Document(path)
    lines = [p.text for p in document.paragraphs if p.text.strip()]
    for table_number, table in enumerate(document.tables, start=1):
        lines.append(f"\n[Bảng {table_number}]")
        for row in table.rows:
            lines.append("\t".join(cell.text.strip() for cell in row.cells))
    return "\n".join(lines)


def read_document(path: str | Path, ocr_timeout_seconds: float | None = None) -> tuple[str, str]:
    """Return ``(text, method)`` for one file. Raises on unreadable files."""

    path = str(path)
    extension = Path(path).suffix.lower()

    if extension == ".pdf":
        if os.getenv("PDF_TEXT_LAYER", "1") != "0":
            try:
                text, pages = pdf_text_layer(path)
                body = re.sub(r"--- Page \d+ ---", "", text)
                if pages and len(body.strip()) / pages >= MIN_CHARS_PER_PAGE and _looks_clean(body):
                    return text, "pdf_text_layer"
            except Exception:
                pass  # damaged or encrypted text layer: OCR below
        from corp_income.reading.ocr import ocr_pdf

        return ocr_pdf(path, timeout_seconds=ocr_timeout_seconds), "ocr_pdf"

    if extension == ".docx":
        return docx_text(path), "docx"

    from corp_income.reading.extractors import extract_document_text
    from corp_income.reading.ocr import IMAGE_EXTENSIONS

    text = extract_document_text(path, ocr_timeout_seconds=ocr_timeout_seconds)
    if extension in IMAGE_EXTENSIONS:
        method = "ocr_image"
    elif extension in {".xlsx", ".xls", ".csv"}:
        method = "spreadsheet"
    else:
        method = "text"
    return text, method
