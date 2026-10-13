"""build_llm names exactly what is missing, before any call is made."""

import os
import unittest
from unittest import mock

from src.config import build_llm


class BuildLlmTest(unittest.TestCase):
    def test_unset_model_variable_is_named(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "MODEL_ECONOMY is not set"):
                build_llm("MODEL_ECONOMY")

    def test_missing_key_is_named_per_provider(self):
        for provider, needed in (("openai", "OPENAI_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY"),
                                 ("databricks", "DATABRICKS_HOST")):
            with self.subTest(provider=provider):
                env = {"MODEL_ECONOMY": "m", "LLM_PROVIDER": provider}
                with mock.patch.dict(os.environ, env, clear=True):
                    with self.assertRaisesRegex(ValueError, needed):
                        build_llm("MODEL_ECONOMY")

    def test_unknown_provider_is_refused(self):
        with mock.patch.dict(os.environ, {"MODEL_ECONOMY": "m", "LLM_PROVIDER": "gemini"}, clear=True):
            with self.assertRaisesRegex(ValueError, "LLM_PROVIDER"):
                build_llm("MODEL_ECONOMY")


if __name__ == "__main__":
    unittest.main()
