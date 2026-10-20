"""[Sửa 20/10] Tự nhận diện KH cá nhân vay vốn khi BORROWER_NAMES để trống.

Không cần LLM, không cần điền tay. Cách làm:
  1. Ứng viên = thành viên góp vốn là cá nhân + người đại diện theo pháp luật,
     lấy từ các bản trích xuất đã có (sổ cổ đông, điều lệ, GCN ĐKDN…).
  2. Tìm tên ứng viên trong văn bản OCR của HỒ SƠ VAY VỐN (giấy đề nghị vay vốn,
     phương án vay…) và hồ sơ soạn thảo nội bộ (tờ trình) — so khớp không dấu,
     bỏ "Ông/Bà".
  3. Ứng viên nào có tên trong hồ sơ vay → là KH vay.

BORROWER_NAMES khai báo trong notebook vẫn luôn được ưu tiên.
"""

from __future__ import annotations

from typing import Any

from src.agents.calculator.legal_checks import norm_person
from src.utils.common import normalize_text

# Ô upload chứa giấy tờ vay của KH (ho_so_vay_von) và tờ trình nội bộ (ho_so_soan_thao_noi_bo).
LOAN_GROUPS = ("ho_so_vay_von", "ho_so_soan_thao_noi_bo")


def _candidates(records: list[dict[str, Any]]) -> dict[str, str]:
    """{tên chuẩn hóa: tên như in} của cá nhân góp vốn và người đại diện theo pháp luật."""

    names: dict[str, str] = {}

    def add(name: Any) -> None:
        key = norm_person(name)
        if len(key.split()) >= 2:          # bỏ tên một chữ — dễ khớp nhầm
            names.setdefault(key, str(name).strip())

    for record in records:
        data = record.get("data") or {}
        for member in data.get("members") or []:
            if isinstance(member, dict) and member.get("member_type") != "phap_nhan":
                add(member.get("name"))
        for rep in data.get("legal_representatives") or []:
            add(rep.get("name") if isinstance(rep, dict) else rep)
    return names


def detect_borrowers(documents: list[Any], records: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """``(tên KH vay, file làm căn cứ)``; ([], []) khi hồ sơ vay không nêu tên ai trong số ứng viên."""

    candidates = _candidates(records)
    # Giấy đề nghị vay của KH trước; tờ trình nội bộ (hay liệt kê mọi thành viên) chỉ dùng khi thiếu.
    for group in LOAN_GROUPS:
        found: list[str] = []
        files: list[str] = []
        for doc in documents:
            if getattr(doc, "declared_group", "") != group or not getattr(doc, "content", ""):
                continue
            text = " " + normalize_text(doc.content) + " "
            hits = [shown for key, shown in candidates.items() if f" {key} " in text]
            found += [name for name in hits if name not in found]
            if hits:
                files.append(doc.filename)
        if found:
            return found, files
    return [], []
