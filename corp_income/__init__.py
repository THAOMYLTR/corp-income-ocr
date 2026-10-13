"""corp_income — OCR and check a corporate (KHDN) dossier for BRD Corp Income items 1-4.

    from corp_income import Settings, build_llm, run_corp_income

    settings = Settings.load(llm_provider="anthropic", llm_model="<model>", anthropic_api_key="…")
    llm = build_llm(settings)
    result = run_corp_income(llm, ["/path/to/dossier"], loan_date="13/10/2026", settings=settings)
    result.save("/path/to/logs/run_1")
"""

from corp_income.llm import LLMConfigError, build_llm, check_connection
from corp_income.pipeline import CorpIncomeResult, run_corp_income
from corp_income.settings import Settings

__all__ = ["Settings", "build_llm", "check_connection", "LLMConfigError", "run_corp_income", "CorpIncomeResult"]
__version__ = "0.1.0"
