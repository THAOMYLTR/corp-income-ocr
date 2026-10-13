"""LLM client factory + runtime Config (extracted from the notebook).

Same contract as the SME repo: ``build_llm("MODEL_PREMIUM")`` reads the model name
from that environment variable and raises at startup if it is unset. One
addition — ``LLM_PROVIDER`` picks how the model is reached:

    LLM_PROVIDER=openai      (default) ChatOpenAI; OPENAI_API_KEY, OPENAI_API_BASE.
                             Also any gateway that speaks the OpenAI format.
    LLM_PROVIDER=anthropic   ChatAnthropic; ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL.
    LLM_PROVIDER=databricks  a Databricks model serving endpoint (OpenAI format);
                             DATABRICKS_HOST, DATABRICKS_TOKEN. MODEL_* = endpoint name.
"""

import os
from dataclasses import dataclass
from typing import Any

PROVIDERS = ("openai", "anthropic", "databricks")

# What each provider needs, so a missing value is named before any call is made.
_REQUIRED_ENV = {
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "databricks": ("DATABRICKS_HOST", "DATABRICKS_TOKEN"),
}


def _rate_limiter():
    """One limiter shared by every client, from LLM_REQUESTS_PER_MINUTE (0 = off)."""

    per_minute = float(os.getenv("LLM_REQUESTS_PER_MINUTE", "0") or 0)
    if per_minute <= 0:
        return None
    global _SHARED_LIMITER
    try:
        return _SHARED_LIMITER
    except NameError:
        from langchain_core.rate_limiters import InMemoryRateLimiter

        _SHARED_LIMITER = InMemoryRateLimiter(
            requests_per_second=per_minute / 60.0,
            check_every_n_seconds=0.1,
            max_bucket_size=1,
        )
        return _SHARED_LIMITER


def build_llm(
    model_env: str,
    temperature: float = 0.1,
    timeout_env: str = "LLM_TIMEOUT_SECONDS",
    max_tokens_env: str = "LLM_MAX_TOKENS",
):
    """Build one chat client from environment variables."""

    model = os.getenv(model_env, "")
    if not model:
        raise ValueError(
            f"{model_env} is not set; add it to .env or point this pass at a "
            f"variable that is"
        )
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider not in PROVIDERS:
        raise ValueError(f"LLM_PROVIDER={provider!r}; expected one of {PROVIDERS}")
    missing = [name for name in _REQUIRED_ENV[provider] if not os.getenv(name)]
    if missing:
        raise ValueError(
            f"LLM_PROVIDER={provider} needs {', '.join(missing)} — set it in "
            f".env or in the notebook (dbutils.secrets) before building the config"
        )

    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "timeout": float(os.getenv(timeout_env, "60")),
        "max_retries": int(os.getenv("LLM_CLIENT_MAX_RETRIES", "1")),
        "max_tokens": int(os.getenv(max_tokens_env, "8192")),
    }
    limiter = _rate_limiter()
    if limiter is not None:
        kwargs["rate_limiter"] = limiter

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs["api_key"] = os.getenv("ANTHROPIC_API_KEY")
        if os.getenv("ANTHROPIC_BASE_URL"):
            kwargs["base_url"] = os.getenv("ANTHROPIC_BASE_URL")
        return ChatAnthropic(**kwargs)

    from langchain_openai import ChatOpenAI

    if provider == "databricks":
        host = os.getenv("DATABRICKS_HOST", "").rstrip("/")
        if not host.startswith("http"):
            host = "https://" + host
        return ChatOpenAI(
            **kwargs,
            api_key=os.getenv("DATABRICKS_TOKEN"),
            base_url=f"{host}/serving-endpoints",
        )
    return ChatOpenAI(**kwargs, base_url=os.getenv("OPENAI_API_BASE") or None)


@dataclass
class Config:
    """Runtime config for the local notebook workflow."""

    document_llm: Any = None
    # One per BRD item (Corp Income, "Pháp lý doanh nghiệp" 1-4).
    legal_basic_extraction_llm: Any = None
    shareholders_extraction_llm: Any = None
    legal_rep_extraction_llm: Any = None
    liabilities_extraction_llm: Any = None
    max_files: int = 50
    max_chars_per_document: int = 120_000
    max_extraction_calls: int = 60
    max_extraction_input_chars: int = 3_000_000
    result_content_char_limit: int = 2_000
    document_classifier_rule_confidence_threshold: float = 0.80
    document_classifier_grouped_confidence_threshold: float = 0.80
    enable_plan_and_execute: bool = True
    enable_self_ask_gap_analysis: bool = True
