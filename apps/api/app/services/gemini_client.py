"""Minimal Google Gemini client for structured LLM output.

Centralizes model name, credentials and retry/timeout configuration so the
agent layer never constructs model clients directly (see
``docs/backend/llm-integration.md``). Structured output is requested through
``response_schema`` and always re-validated by the caller before it is trusted.
"""
import json
from typing import Any, Type

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.core.config import settings


class GeminiLLMError(Exception):
    def __init__(self, message: str, *, code: str = "gemini_llm_error"):
        super().__init__(message)
        self.code = code


def _schema_without_additional_properties(schema: Any) -> Any:
    """Deep-copy a JSON schema with the ``additionalProperties`` keyword removed.

    Pydantic v2 emits ``additionalProperties: false`` for ``extra="forbid"``
    models, which the Gemini Developer API rejects. Only the wire schema is
    relaxed; callers still re-validate the untrusted model output with the
    strict Pydantic schema (``docs/backend/llm-integration.md``).
    """
    if isinstance(schema, dict):
        return {
            key: _schema_without_additional_properties(value)
            for key, value in schema.items()
            if key not in ("additionalProperties", "additional_properties")
        }
    if isinstance(schema, list):
        return [_schema_without_additional_properties(item) for item in schema]
    return schema


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str = settings.gemini_api_key,
        model: str = settings.gemini_llm_model,
        max_retries: int = settings.gemini_max_retries,
    ) -> None:
        if not api_key:
            raise GeminiLLMError(
                "GeminiClient requires GEMINI_API_KEY to be configured",
                code="missing_api_key",
            )
        self.model = model
        self.max_retries = max_retries
        self._client = genai.Client(api_key=api_key)

    def generate_structured(
        self,
        *,
        system_instruction: str,
        contents: str,
        response_schema: Type[BaseModel],
    ) -> dict[str, Any]:
        """Return structured (JSON-schema constrained) model output as a dict.

        Only transient server-side failures are retried; client errors and
        validation problems surface immediately.
        """
        last_error: Exception | None = None
        wire_response_schema = _schema_without_additional_properties(
            response_schema.model_json_schema()
        )
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=wire_response_schema,
                    ),
                )
                return self._extract(response, response_schema)
            except GeminiLLMError:
                raise
            except (errors.ServerError, ConnectionError) as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
            except Exception as exc:
                raise GeminiLLMError(
                    f"Unhandled Gemini error: {exc}", code="gemini_request_failed"
                ) from exc

        raise GeminiLLMError(
            f"Gemini request failed after {self.max_retries} attempts: {last_error}",
            code="gemini_unavailable",
        )

    def _extract(
        self, response: Any, response_schema: Type[BaseModel]
    ) -> dict[str, Any]:
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            if isinstance(parsed, dict):
                return parsed
            return parsed.model_dump()
        text = getattr(response, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise GeminiLLMError(
                    f"Gemini returned non-JSON output: {exc}",
                    code="invalid_llm_json",
                ) from exc
        raise GeminiLLMError(
            "Gemini returned an empty structured response",
            code="empty_llm_response",
        )