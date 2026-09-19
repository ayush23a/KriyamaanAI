from typing import Any, TypeVar
from domain.models import CallBudget, ChatMessage, ProviderResult, UsageSnapshot
from domain.ports.llm import LLMCallRole, LLMProvider

T = TypeVar("T")


class FakeLLMProvider(LLMProvider):
    """Deterministic fake LLM provider for unit and contract testing."""

    def __init__(
        self,
        default_text: str = "Fake LLM text response.",
        structured_response: Any = None,
    ):
        self.default_text = default_text
        self.structured_response = structured_response
        self.recorded_calls: list[list[ChatMessage]] = []
        self.recorded_roles: list[LLMCallRole] = []

    def generate_structured(
        self,
        messages: list[ChatMessage],
        schema: type[T],
        budget: CallBudget,
        role: LLMCallRole = LLMCallRole.GENERATOR,
    ) -> ProviderResult[T]:
        self.recorded_calls.append(messages)
        self.recorded_roles.append(role)
        if self.structured_response is not None:
            if isinstance(self.structured_response, schema):
                data = self.structured_response
            elif isinstance(self.structured_response, dict):
                data = schema(**self.structured_response)
            else:
                data = self.structured_response
        else:
            data = schema()  # type: ignore

        usage = UsageSnapshot(input_tokens=50, output_tokens=30, latency_ms=10)
        return ProviderResult(data=data, usage=usage)

    def generate_text(
        self,
        messages: list[ChatMessage],
        budget: CallBudget,
        role: LLMCallRole = LLMCallRole.GENERATOR,
    ) -> ProviderResult[str]:
        self.recorded_calls.append(messages)
        self.recorded_roles.append(role)
        usage = UsageSnapshot(input_tokens=40, output_tokens=20, latency_ms=10)
        return ProviderResult(data=self.default_text, usage=usage)
