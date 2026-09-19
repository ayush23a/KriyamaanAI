from enum import Enum
from typing import Protocol, TypeVar
from domain.models import CallBudget, ChatMessage, ProviderResult

T = TypeVar("T")


class LLMCallRole(str, Enum):
    PLANNER = "planner"
    JUDGE = "judge"
    GENERATOR = "generator"


class LLMProvider(Protocol):
    def generate_structured(
        self,
        messages: list[ChatMessage],
        schema: type[T],
        budget: CallBudget,
        role: LLMCallRole = LLMCallRole.GENERATOR,
    ) -> ProviderResult[T]:
        ...

    def generate_text(
        self,
        messages: list[ChatMessage],
        budget: CallBudget,
        role: LLMCallRole = LLMCallRole.GENERATOR,
    ) -> ProviderResult[str]:
        ...
