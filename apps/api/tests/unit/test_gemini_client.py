"""Unit tests for the Gemini structured-output client.

``GeminiClient`` must present a wire schema the Developer API accepts while the
callers still validate the untrusted LLM output with strict Pydantic models
(``docs/backend/llm-integration.md``). Pydantic ``extra="forbid"`` models emit
``additionalProperties: false``, which the Developer API rejects — the client
strips that keyword from the wire schema only.
"""
import json
import pytest

from app.models.enums import AIDecision, ClaimPriority
from app.schemas.assessment import AuditAssessment
from app.schemas.validation import ValidationReasoningOutput
from app.services.gemini_client import GeminiClient, GeminiLLMError


def _payload() -> dict:
    return {
        "summary": "Dinner claim is compliant with policy and validation checks.",
        "ai_decision": "approve",
        "priority": "low",
        "confidence": 0.95,
    }


def _assert_no_additional_properties(value) -> None:
    if isinstance(value, dict):
        assert "additionalProperties" not in value
        assert "additional_properties" not in value
        for child in value.values():
            _assert_no_additional_properties(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_additional_properties(child)


def test_schemas_with_extra_forbid_emit_additional_properties():
    """Regression context: strict models build ``additionalProperties: false``."""
    assert AuditAssessment.model_json_schema()["additionalProperties"] is False


def test_sanitizer_strips_additional_properties_recursively():
    from app.services.gemini_client import _schema_without_additional_properties

    for model in (AuditAssessment, ValidationReasoningOutput):
        sanitized = _schema_without_additional_properties(model.model_json_schema())
        _assert_no_additional_properties(sanitized)


def test_sanitizer_preserves_the_rest_of_the_schema():
    from app.services.gemini_client import _schema_without_additional_properties

    sanitized = _schema_without_additional_properties(
        AuditAssessment.model_json_schema()
    )

    assert sanitized["type"] == "object"
    assert set(sanitized["required"]) == {
        "summary",
        "ai_decision",
        "priority",
        "confidence",
    }
    assert sanitized["$defs"]["AIDecision"]["enum"] == [
        "approve",
        "reject",
        "review",
    ]


def test_sanitized_wire_schema_passes_developer_api_conversion():
    from google.genai import types
    from google.genai._transformers import t_schema

    from app.services.gemini_client import _schema_without_additional_properties

    class FakeClient:
        vertexai = False

    wire = _schema_without_additional_properties(
        AuditAssessment.model_json_schema()
    )
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=wire,
    )
    schema = t_schema(FakeClient(), config.response_schema)

    assert schema.additional_properties is None
    assert schema.type is types.Type.OBJECT


class _FakeResponse:
    def __init__(self, *, parsed=None, text=None):
        self.parsed = parsed
        self.text = text


class _FakeModels:
    def __init__(self, response):
        self._response = response
        self.last_config = None
        self.last_kwargs = None

    def generate_content(self, model, contents, config):
        self.last_kwargs = {"model": model, "contents": contents}
        self.last_config = config
        return self._response


class _FakeTransport:
    def __init__(self, response):
        self.models = _FakeModels(response)


def _client_for(response):
    client = GeminiClient(api_key="test-key")
    client._client = _FakeTransport(response)
    return client


def test_generate_structured_sends_sanitized_schema_and_returns_parsed_dict():
    response = _FakeResponse(parsed=_payload())
    client = _client_for(response)

    result = client.generate_structured(
        system_instruction="be fair",
        contents="claim under review",
        response_schema=AuditAssessment,
    )

    assert result == _payload()
    wire = client._client.models.last_config.response_schema
    assert isinstance(wire, dict)
    _assert_no_additional_properties(wire)


def test_generate_structured_handles_pydantic_parsed_output():
    response = _FakeResponse(parsed=AuditAssessment(**_payload()))
    client = _client_for(response)

    result = client.generate_structured(
        system_instruction="be fair",
        contents="claim under review",
        response_schema=AuditAssessment,
    )

    assert result == _payload()


def test_generate_structured_falls_back_to_text_parsing():
    response = _FakeResponse(text=json.dumps(_payload()))
    client = _client_for(response)

    result = client.generate_structured(
        system_instruction="be fair",
        contents="claim under review",
        response_schema=AuditAssessment,
    )

    assert result == _payload()


def test_generate_structured_rejects_non_json_text():
    response = _FakeResponse(text="not json")
    client = _client_for(response)

    with pytest.raises(GeminiLLMError) as exc:
        client.generate_structured(
            system_instruction="be fair",
            contents="claim under review",
            response_schema=AuditAssessment,
        )
    assert exc.value.code == "invalid_llm_json"


def test_generate_structured_requires_api_key(monkeypatch):
    monkeypatch.setattr(
        "app.services.gemini_client.settings.gemini_api_key", None
    )

    with pytest.raises(GeminiLLMError) as exc:
        GeminiClient(api_key="")
    assert exc.value.code == "missing_api_key"