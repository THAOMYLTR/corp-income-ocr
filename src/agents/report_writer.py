"""Fill the template placeholders that code cannot: one LLM call per report.

Code fills every fact and figure first (appendix_context). The placeholders
still empty — "Nhận xét…", business activity, CIC, the conclusion — are sent
to the LLM together with the guidance (config/prompts/corp_income_guidance.md),
the writer rules (config/prompts/report_writer.md), the values code already
filled, the BRD checks, the financial ratios and excerpts of the documents.
The LLM answers ``{placeholder: text}``; code puts the text in place, so the
template layout and every code-filled number stay exactly as they are.

Never raises: without an LLM, or when the call fails, the cells read
"Chưa có thông tin" and the reason is returned for the run log.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.llm_errors import explain_llm_error
from src.prompts import system_prompt

NO_INFO = "Chưa có thông tin trong hồ sơ"
MAX_EVIDENCE_CHARS = 120_000


def build_writer_chain(llm: Any):
    system = system_prompt("corp_income_guidance") + "\n\n" + system_prompt("report_writer")
    prompt = ChatPromptTemplate.from_messages(
        [SystemMessage(content=system), ("human", system_prompt("report_writer_user"))]
    )
    return prompt | llm | JsonOutputParser()


def describe_fields(template: str, names: list[str]) -> str:
    """Each name with the template line it sits on, so the LLM knows its meaning."""

    lines = template.splitlines()
    out = []
    for name in names:
        where = next((line.strip() for line in lines if "{{" + name + "}}" in line), "")
        in_table = where.startswith("|") or "<td>" in where
        if len(where) > 240:
            start = max(0, where.find("{{" + name + "}}") - 120)
            where = "…" + where[start:start + 240] + "…"
        # Nearest heading above, for context.
        heading = ""
        for line in lines[: next((i for i, l in enumerate(lines) if "{{" + name + "}}" in l), 0)]:
            if line.startswith("#"):
                heading = line.strip("# ").strip()
        out.append(json.dumps({"o": name, "phan": heading, "dong_mau": where, "trong_bang": in_table},
                              ensure_ascii=False))
    return "\n".join(out)


def write_placeholders(
    llm: Any,
    template: str,
    names: list[str],
    evidence: dict[str, Any],
) -> tuple[dict[str, str], str]:
    """``({name: text}, error)``. Missing names come back as NO_INFO."""

    if not names:
        return {}, ""
    fallback = {name: NO_INFO for name in names}
    if llm is None:
        return fallback, "No report_writer_llm configured — narrative cells left as 'Chưa có thông tin'."
    payload = json.dumps(evidence, ensure_ascii=False, default=str)
    if len(payload) > MAX_EVIDENCE_CHARS:
        payload = payload[:MAX_EVIDENCE_CHARS] + "…(cắt bớt)"
    try:
        answer = build_writer_chain(llm).invoke(
            {"fields": describe_fields(template, names), "evidence": payload}
        )
    except Exception as exc:  # noqa: BLE001 — reported, never raised
        return fallback, f"Report writer failed: {explain_llm_error(exc)}"
    if not isinstance(answer, dict):
        return fallback, f"Report writer returned {type(answer).__name__}, not a JSON object."
    filled = {}
    for name in names:
        value = answer.get(name)
        filled[name] = str(value).strip() if value not in (None, "") else NO_INFO
    missing = [n for n in names if answer.get(n) in (None, "")]
    return filled, (f"Report writer left {len(missing)} cell(s) empty: {', '.join(missing)}" if missing else "")
