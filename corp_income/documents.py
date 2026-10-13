"""Find the files, read which upload folder each sits in, and classify them.

Classification is keyword scoring (accent-insensitive; a filename hit counts 3×
a content hit). The upload folder narrows the candidates first, so the folder
you drop a file into is the strongest signal — see ``boxes`` in
``document_types.yaml``. No LLM is used here.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from corp_income.extraction import PASSES
from corp_income.text import SUPPORTED_EXTENSIONS, normalize_text

TYPES_PATH = Path(__file__).resolve().parent / "document_types.yaml"
SOURCES = ("customer", "field", "external", "internal")
UNCLASSIFIED = "khac"
FILENAME_WEIGHT = 3


@dataclass(frozen=True)
class DocType:
    id: str
    label: str
    source: str
    keywords: tuple[str, ...]
    passes: tuple[str, ...]


@dataclass(frozen=True)
class Box:
    id: str
    label: str
    types: tuple[str, ...]
    default_type: str


@lru_cache(maxsize=1)
def catalogue() -> tuple[dict[str, DocType], dict[str, Box]]:
    """Load and validate document_types.yaml. Fails loudly on a bad entry."""

    raw = yaml.safe_load(TYPES_PATH.read_text(encoding="utf-8")) or {}
    types: dict[str, DocType] = {}
    for entry in raw.get("types", []):
        type_id = entry["id"]
        if type_id in types:
            raise ValueError(f"document_types.yaml: duplicate type {type_id!r}")
        if entry.get("source", "customer") not in SOURCES:
            raise ValueError(f"{type_id}: source must be one of {SOURCES}")
        bad = set(entry.get("passes", [])) - set(PASSES)
        if bad:
            raise ValueError(f"{type_id}: unknown passes {sorted(bad)}")
        types[type_id] = DocType(
            id=type_id,
            label=entry.get("label", type_id),
            source=entry.get("source", "customer"),
            keywords=tuple(normalize_text(k) for k in entry.get("keywords", []) if k),
            passes=tuple(entry.get("passes", [])),
        )
    boxes: dict[str, Box] = {}
    for box_id, entry in (raw.get("boxes") or {}).items():
        members = tuple(entry.get("types") or [])
        unknown = [t for t in members if t not in types]
        default = entry.get("default_type", "")
        if unknown or (default and default not in types):
            raise ValueError(f"box {box_id}: unknown types {unknown or [default]}")
        boxes[box_id] = Box(box_id, entry.get("label", box_id), members, default)
    return types, boxes


# --------------------------------------------------------------------------- #
def box_of(path: str | Path) -> str:
    """The nearest ancestor folder that is an upload box, or ''."""

    boxes = catalogue()[1]
    for parent in Path(path).parents:
        if parent.name in boxes:
            return parent.name
    return ""


def discover(input_paths: list[str | Path]) -> tuple[list[Path], list[str]]:
    """Supported files under the inputs (recursive), duplicates by content removed.

    Returns ``(files, skipped_messages)`` — nothing is dropped silently.
    """

    files: list[Path] = []
    skipped: list[str] = []
    seen: dict[str, Path] = {}
    for raw in input_paths:
        path = Path(raw).expanduser()
        if not path.exists():
            skipped.append(f"{path}: does not exist")
            continue
        candidates = sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]
        for file in candidates:
            if file.name.startswith(".") or file.name.startswith("~$"):
                continue
            if file.suffix.lower() not in SUPPORTED_EXTENSIONS:
                skipped.append(f"{file.name}: unsupported file type {file.suffix or '(none)'}")
                continue
            digest = hashlib.sha256(file.read_bytes()).hexdigest()
            if digest in seen:
                skipped.append(f"{file.name}: same content as {seen[digest].name}, skipped")
                continue
            seen[digest] = file
            files.append(file)
    return files, skipped


def _count(keyword: str, padded: str) -> int:
    return padded.count(f" {keyword} ")


def type_scores(filename: str, content: str, candidates: tuple[str, ...] | None = None) -> dict[str, int]:
    types = catalogue()[0]
    name = f" {normalize_text(Path(filename).stem)} "
    # The title is on the first pages; incidental mentions later ("theo điều lệ…")
    # must not outvote it.
    body = f" {normalize_text(content[:6000])} "
    scores: dict[str, int] = {}
    for type_id in candidates or tuple(types):
        score = 0
        for keyword in types[type_id].keywords:
            score += FILENAME_WEIGHT * _count(keyword, name) + min(_count(keyword, body), 3)
        if score:
            scores[type_id] = score
    return scores


def classify(filename: str, content: str, box: str = "", override: str | None = None) -> dict[str, Any]:
    """→ {type, label, source, passes, box, method, scores}."""

    types, boxes = catalogue()
    order = list(types)
    if override:
        if override not in types:
            raise ValueError(f"Unknown document type override {override!r}. Valid: {order}")
        chosen, method, scores = override, "override", {}
    else:
        box_def = boxes.get(box)
        candidates = box_def.types if box_def and box_def.types else None
        scores = type_scores(filename, content, candidates)
        if scores:
            chosen = max(scores, key=lambda t: (scores[t], -order.index(t)))
            method = f"keyword in {box}" if candidates else "keyword"
        elif box_def and box_def.default_type:
            chosen, method = box_def.default_type, f"folder {box}"
        else:
            chosen, method = UNCLASSIFIED, "none"

    doc_type = types.get(chosen)
    return {
        "type": chosen,
        "label": doc_type.label if doc_type else "Chưa phân loại",
        "source": doc_type.source if doc_type else "customer",
        "passes": list(doc_type.passes) if doc_type else [],
        "box": box,
        "method": method,
        "scores": scores,
    }
