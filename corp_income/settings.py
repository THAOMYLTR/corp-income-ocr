"""All run settings in one place.

Set them in the notebook's settings cell (recommended on Databricks), or as
environment variables / a ``.env`` file. A value passed in code wins over the
environment; the environment wins over the defaults below.

    settings = Settings.load(llm_provider="anthropic", llm_model="claude-...",
                             anthropic_api_key=dbutils.secrets.get("scope", "key"))
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields

PROVIDERS = ("anthropic", "openai", "databricks")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass
class Settings:
    # --- LLM --------------------------------------------------------------
    # anthropic  : Anthropic API (or an Anthropic-compatible gateway via anthropic_base_url)
    # openai     : OpenAI, or any gateway that speaks the OpenAI format (openai_base_url)
    # databricks : a Databricks model serving endpoint; llm_model = the endpoint name
    llm_provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "anthropic").lower())
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL"))
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    anthropic_base_url: str = field(default_factory=lambda: _env("ANTHROPIC_BASE_URL"))
    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    openai_base_url: str = field(
        default_factory=lambda: _env("OPENAI_BASE_URL") or _env("OPENAI_API_BASE"))
    databricks_host: str = field(default_factory=lambda: _env("DATABRICKS_HOST"))
    databricks_token: str = field(default_factory=lambda: _env("DATABRICKS_TOKEN"))
    temperature: float = 0.0
    max_output_tokens: int = field(default_factory=lambda: int(_env("LLM_MAX_OUTPUT_TOKENS", "8000")))
    timeout_seconds: float = field(default_factory=lambda: float(_env("LLM_TIMEOUT_SECONDS", "120")))
    max_retries: int = field(default_factory=lambda: int(_env("LLM_MAX_RETRIES", "3")))
    # Shared ceiling across all calls in the run. Keep it below your real quota.
    requests_per_minute: float = field(
        default_factory=lambda: float(_env("LLM_REQUESTS_PER_MINUTE", "20")))

    # --- Run --------------------------------------------------------------
    max_workers: int = field(default_factory=lambda: int(_env("MAX_WORKERS", "3")))
    max_chars_per_document: int = 120_000
    ocr_timeout_seconds: float | None = None

    @classmethod
    def load(cls, **overrides) -> "Settings":
        """Defaults ← environment ← ``overrides``. Unknown names raise, so typos surface."""

        known = {f.name for f in fields(cls)}
        unknown = sorted(set(overrides) - known)
        if unknown:
            raise TypeError(f"Unknown setting(s): {unknown}. Valid: {sorted(known)}")
        settings = cls()
        for name, value in overrides.items():
            if value is not None:
                setattr(settings, name, value)
        settings.llm_provider = str(settings.llm_provider).lower()
        return settings

    def problems(self) -> list[str]:
        """Everything missing for the chosen provider, in plain words. [] = ready."""

        issues = []
        if self.llm_provider not in PROVIDERS:
            return [f"llm_provider must be one of {PROVIDERS}, got {self.llm_provider!r}"]
        if not self.llm_model:
            issues.append("llm_model is empty — set the model name (for databricks: the serving endpoint name)")
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            issues.append("anthropic_api_key is empty (or set ANTHROPIC_API_KEY)")
        if self.llm_provider == "openai" and not self.openai_api_key:
            issues.append("openai_api_key is empty (or set OPENAI_API_KEY)")
        if self.llm_provider == "databricks":
            if not self.databricks_host:
                issues.append("databricks_host is empty — e.g. https://<workspace>.cloud.databricks.com")
            if not self.databricks_token:
                issues.append("databricks_token is empty — in a notebook use the token from "
                              "dbutils (see the settings cell)")
        return issues

    def describe(self) -> dict[str, str]:
        """Safe to print: keys are masked."""

        def mask(value: str) -> str:
            return f"set ({value[:4]}…)" if value else "—"

        return {
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model or "—",
            "anthropic_api_key": mask(self.anthropic_api_key),
            "anthropic_base_url": self.anthropic_base_url or "default",
            "openai_api_key": mask(self.openai_api_key),
            "openai_base_url": self.openai_base_url or "default",
            "databricks_host": self.databricks_host or "—",
            "databricks_token": mask(self.databricks_token),
            "requests_per_minute": str(self.requests_per_minute),
        }
