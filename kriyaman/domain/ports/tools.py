from typing import Any, Protocol
from domain.models import ToolContext, ToolDescriptor, ToolResult


class Tool(Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def input_schema(self) -> dict[str, Any]:
        ...

    @property
    def is_side_effect(self) -> bool:
        ...

    def invoke(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        ...


class ToolRegistry(Protocol):
    def describe_available(self) -> list[ToolDescriptor]:
        ...

    def invoke(self, name: str, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        ...

