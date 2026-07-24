"""LLM configuration and document parsing."""

import tuttle.llm as _llm

from ..core.intent_result import IntentResult


class LlmIntent:
    def get_config(self) -> IntentResult:
        return IntentResult(
            was_intent_successful=True,
            data=_llm.load_config(),
        )

    def save_config(self, config: dict) -> IntentResult:
        saved = _llm.save_config(_llm.LLMConfig(**config))
        return IntentResult(was_intent_successful=True, data=saved)

    def get_models(
        self,
        base_url: str = "http://localhost:11434",
        provider: str = "ollama",
        api_key: str = "",
    ) -> IntentResult:
        return IntentResult(
            was_intent_successful=True,
            data=_llm.get_available_models(base_url, provider=provider, api_key=api_key),
        )

    def parse_document(
        self,
        file_base64: str,
        file_name: str,
        entity_type: str = "contact",
    ) -> IntentResult:
        items = _llm.parse_document(
            file_base64,
            file_name,
            entity_type,
            _llm.load_config(),
        )
        return IntentResult(was_intent_successful=True, data=items)

    def parse_document_for_import(
        self,
        file_base64: str,
        file_name: str,
    ) -> IntentResult:
        result = _llm.parse_document_for_import(
            file_base64,
            file_name,
        )
        all_done = all(s["status"] == "done" for s in result.get("steps", []))
        if all_done:
            return IntentResult(was_intent_successful=True, data=result)
        failed = next(
            (s for s in result.get("steps", []) if s["status"] == "error"),
            None,
        )
        return IntentResult(
            was_intent_successful=False,
            data=result,
            error_msg=failed["error"] if failed else "Import failed.",
        )
