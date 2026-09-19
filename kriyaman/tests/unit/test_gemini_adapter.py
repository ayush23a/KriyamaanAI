from unittest.mock import MagicMock
import pytest
from domain.errors import ProviderError
from domain.models import Answer, CallBudget, ChatMessage
from adapters.llm.google import GoogleGeminiAdapter


def test_gemini_adapter_messages_to_prompt():
    adapter = GoogleGeminiAdapter(api_key="test_key", client=MagicMock())
    messages = [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="Hello Gemini!"),
    ]
    prompt = adapter._format_messages_to_prompt(messages)
    assert "[SYSTEM]:" in prompt
    assert "You are a helpful assistant." in prompt
    assert "[USER]:" in prompt
    assert "Hello Gemini!" in prompt


def test_gemini_adapter_generate_text():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Generated text from Gemini."
    mock_response.usage_metadata.prompt_token_count = 15
    mock_response.usage_metadata.candidates_token_count = 10
    mock_client.models.generate_content.return_value = mock_response

    adapter = GoogleGeminiAdapter(api_key="test_key", client=mock_client)
    res = adapter.generate_text(
        messages=[ChatMessage(role="user", content="Test")],
        budget=CallBudget(max_tokens=100),
    )

    assert res.data == "Generated text from Gemini."
    assert res.usage is not None
    assert res.usage.input_tokens == 15
    assert res.usage.output_tokens == 10


def test_gemini_adapter_generate_structured():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"answer_text": "Structured answer.", "citation_ids": ["ev_1"], "confidence": 0.95, "needs_follow_up": false}'
    mock_response.usage_metadata.prompt_token_count = 20
    mock_response.usage_metadata.candidates_token_count = 15
    mock_client.models.generate_content.return_value = mock_response

    adapter = GoogleGeminiAdapter(api_key="test_key", client=mock_client)
    res = adapter.generate_structured(
        messages=[ChatMessage(role="user", content="Test")],
        schema=Answer,
        budget=CallBudget(max_tokens=100),
    )

    assert isinstance(res.data, Answer)
    assert res.data.answer_text == "Structured answer."
    assert res.data.citation_ids == ["ev_1"]
    assert res.data.confidence == 0.95


def test_gemini_adapter_no_client_error():
    adapter = GoogleGeminiAdapter(api_key="", client=None)
    with pytest.raises(ProviderError):
        adapter.generate_text([ChatMessage(role="user", content="Hi")], CallBudget())

