from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from adapters.llm.litellm_gateway import LiteLLMGatewayAdapter, _extract_json_text
from domain.errors import ProviderError
from domain.models import CallBudget, ChatMessage
from domain.ports.llm import LLMCallRole


class DummySchema(BaseModel):
    name: str
    score: float


def test_extract_json_text():
    # Plain JSON
    assert _extract_json_text('{"name": "test"}') == '{"name": "test"}'
    # Markdown code block
    assert _extract_json_text('```json\n{"name": "test"}\n```') == '{"name": "test"}'
    # Markdown without json label
    assert _extract_json_text('```\n{"name": "test"}\n```') == '{"name": "test"}'
    # Wrapped in conversational text
    raw = 'Here is the requested object: {"name": "test", "score": 1.0} Thank you!'
    assert _extract_json_text(raw) == '{"name": "test", "score": 1.0}'


def test_litellm_gateway_role_routing():
    adapter = LiteLLMGatewayAdapter(
        google_api_key="mock_google_key",
        groq_api_key="mock_groq_key",
        planner_model="groq/openai/gpt-oss-20b",
        judge_model="groq/openai/gpt-oss-20b",
        generator_model="gemini/gemini-2.5-flash",
        planner_fallback_models=["groq/openai/gpt-oss-120b"],
        judge_fallback_models=["groq/openai/gpt-oss-120b"],
        generator_fallback_models=["groq/openai/gpt-oss-120b", "gemini/gemini-1.5-flash"],
    )

    assert adapter._get_models_for_role(LLMCallRole.PLANNER) == [
        "groq/openai/gpt-oss-20b",
        "groq/openai/gpt-oss-120b",
    ]
    assert adapter._get_models_for_role(LLMCallRole.JUDGE) == [
        "groq/openai/gpt-oss-20b",
        "groq/openai/gpt-oss-120b",
    ]
    assert adapter._get_models_for_role(LLMCallRole.GENERATOR) == [
        "gemini/gemini-2.5-flash",
        "groq/openai/gpt-oss-120b",
        "gemini/gemini-1.5-flash",
    ]


@patch("litellm.completion")
@patch("litellm.completion_cost")
def test_litellm_gateway_generate_text(mock_cost, mock_completion):
    mock_choice = MagicMock()
    mock_choice.message.content = "Refunds are processed in 5 business days."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 25
    mock_response.usage.completion_tokens = 10
    mock_completion.return_value = mock_response
    mock_cost.return_value = 0.000045

    adapter = LiteLLMGatewayAdapter(
        google_api_key="mock_key_12345",
        generator_model="gemini/gemini-2.5-flash",
    )

    messages = [ChatMessage(role="user", content="How long do refunds take?")]
    result = adapter.generate_text(
        messages=messages,
        budget=CallBudget(max_tokens=100, timeout_seconds=10.0),
        role=LLMCallRole.GENERATOR,
    )

    assert result.data == "Refunds are processed in 5 business days."
    assert result.usage.input_tokens == 25
    assert result.usage.output_tokens == 10
    assert result.usage.estimated_cost_usd == Decimal("0.000045")
    assert result.metadata["model"] == "gemini/gemini-2.5-flash"
    assert result.metadata["role"] == "generator"


@patch("litellm.completion")
def test_litellm_gateway_generate_structured(mock_completion):
    mock_choice = MagicMock()
    mock_choice.message.content = '```json\n{"name": "alpha", "score": 0.95}\n```'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 50
    mock_response.usage.completion_tokens = 15
    mock_completion.return_value = mock_response

    adapter = LiteLLMGatewayAdapter(
        groq_api_key="mock_groq_key_9999",
        planner_model="groq/openai/gpt-oss-20b",
    )

    messages = [ChatMessage(role="user", content="Score alpha")]
    result = adapter.generate_structured(
        messages=messages,
        schema=DummySchema,
        budget=CallBudget(max_tokens=200, timeout_seconds=10.0),
        role=LLMCallRole.PLANNER,
    )

    assert isinstance(result.data, DummySchema)
    assert result.data.name == "alpha"
    assert result.data.score == 0.95
    assert result.metadata["role"] == "planner"


@patch("litellm.completion")
def test_litellm_gateway_retry_and_fallback(mock_completion):
    mock_success_choice = MagicMock()
    mock_success_choice.message.content = '{"name": "beta", "score": 0.8}'
    mock_success_response = MagicMock()
    mock_success_response.choices = [mock_success_choice]
    mock_success_response.usage.prompt_tokens = 40
    mock_success_response.usage.completion_tokens = 10

    # First attempt raises transient error, second attempt succeeds
    mock_completion.side_effect = [
        Exception("Transient connection error"),
        mock_success_response,
    ]

    adapter = LiteLLMGatewayAdapter(
        groq_api_key="mock_groq_key_111",
        judge_model="groq/openai/gpt-oss-20b",
        max_retries=1,
        retry_backoff=0.01,
    )

    messages = [ChatMessage(role="user", content="Evaluate beta")]
    result = adapter.generate_structured(
        messages=messages,
        schema=DummySchema,
        budget=CallBudget(max_tokens=200, timeout_seconds=5.0),
        role=LLMCallRole.JUDGE,
    )

    assert result.data.name == "beta"
    assert mock_completion.call_count == 2


@patch("litellm.completion")
def test_litellm_gateway_secret_sanitization(mock_completion):
    mock_completion.side_effect = Exception("Failed connecting with key secret_token_xyz_12345678")

    adapter = LiteLLMGatewayAdapter(
        google_api_key="secret_token_xyz_12345678",
        generator_model="gemini/gemini-2.5-flash",
        generator_fallback_models=[],
        max_retries=0,
    )

    with pytest.raises(ProviderError) as exc_info:
        adapter.generate_text(
            messages=[ChatMessage(role="user", content="test")],
            budget=CallBudget(max_tokens=50),
        )

    # Key should never be present in the exception message
    assert "secret_token_xyz_12345678" not in str(exc_info.value)
    assert "[REDACTED_SECRET]" in str(exc_info.value)

