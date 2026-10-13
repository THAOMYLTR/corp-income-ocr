"""Build the chat model and talk to it.

The rest of the package only ever calls ``ask_json(llm, system, user)``, so the
provider is a single setting. Any LangChain chat model works, which is also how
the tests run without a key: they pass an object with an ``invoke`` method.
"""

from __future__ import annotations

import json
import re
from typing import Any

from corp_income.settings import Settings


class LLMConfigError(ValueError):
    """Settings are incomplete — the message says exactly what to set."""


def build_llm(settings: Settings):
    """Chat model for ``settings.llm_provider``. Raises LLMConfigError with a fix."""

    problems = settings.problems()
    if problems:
        raise LLMConfigError("LLM settings incomplete:\n- " + "\n- ".join(problems))

    from langchain_core.rate_limiters import InMemoryRateLimiter

    limiter = InMemoryRateLimiter(
        requests_per_second=max(settings.requests_per_minute, 0.1) / 60.0,
        check_every_n_seconds=0.1,
        max_bucket_size=1,
    )
    common = {
        "model": settings.llm_model,
        "temperature": settings.temperature,
        "max_tokens": settings.max_output_tokens,
        "timeout": settings.timeout_seconds,
        "max_retries": settings.max_retries,
        "rate_limiter": limiter,
    }

    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = {**common, "api_key": settings.anthropic_api_key}
        if settings.anthropic_base_url:
            kwargs["base_url"] = settings.anthropic_base_url
        return ChatAnthropic(**kwargs)

    from langchain_openai import ChatOpenAI

    if settings.llm_provider == "openai":
        kwargs = {**common, "api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)

    # databricks: serving endpoints speak the OpenAI chat format.
    host = settings.databricks_host.rstrip("/")
    if not host.startswith("http"):
        host = "https://" + host
    return ChatOpenAI(**common, api_key=settings.databricks_token, base_url=f"{host}/serving-endpoints")


def response_text(response: Any) -> str:
    """Plain text from a chat response (Anthropic may return a list of blocks)."""

    content = getattr(response, "content", response)
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block) for block in content
        )
    return str(content)


def parse_json(text: str) -> dict[str, Any]:
    """The JSON object in a model reply, tolerating ```json fences and stray prose."""

    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text.strip())
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(f"No JSON object in model reply: {text[:200]!r}")
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError(f"Model returned {type(value).__name__}, expected a JSON object")
    return value


def ask_json(llm: Any, system: str, user: str) -> dict[str, Any]:
    """One call: system + user message in, parsed JSON object out."""

    return parse_json(response_text(llm.invoke([("system", system), ("human", user)])))


def check_connection(llm: Any) -> str:
    """Tiny real call to prove key, URL and model all work. Returns the reply or raises."""

    reply = response_text(llm.invoke([("human", 'Reply with exactly: {"ok": true}')]))
    parse_json(reply)
    return reply.strip()
