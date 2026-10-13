"""Text helpers shared by every module (no project imports, so nothing can cycle)."""

from __future__ import annotations

import re
import unicodedata

# Files the pipeline reads. Anything else in an input folder is listed as skipped.
SUPPORTED_EXTENSIONS = frozenset({
    ".pdf", ".docx", ".xlsx", ".xls", ".csv", ".txt", ".md", ".pptx", ".xml",
    # Phone photos and scans (GCN ĐKDN photographed on a desk is common).
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp",
})


def normalize_text(text: str) -> str:
    """Lowercase, strip Vietnamese accents, collapse punctuation to single spaces.

    OCR drops or mangles diacritics often enough that every keyword comparison
    has to be accent-insensitive: "Điều lệ", "dieu le" and "DIEU_LE" all become
    "dieu le".
    """

    lowered = (text or "").lower().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", lowered)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^0-9a-z]+", " ", stripped).strip()
