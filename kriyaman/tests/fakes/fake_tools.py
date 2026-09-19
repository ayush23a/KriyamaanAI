from typing import Any
from domain.models import ToolContext, ToolDescriptor, ToolResult
from domain.ports.tools import Tool, ToolRegistry


class FakeFormatTool(Tool):
    @property
    def name(self) -> str:
        return "format_text"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"text": {"type": "string"}}}

    @property
    def is_side_effect(self) -> bool:
        return False

    def invoke(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        text = arguments.get("text", "")
        return ToolResult(
            tool_name=self.name,
            status="success",
            result=text.strip().upper(),
        )


class FakeSideEffectTool(Tool):
    @property
    def name(self) -> str:
        return "send_email"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"recipient": {"type": "string"}}}

    @property
    def is_side_effect(self) -> bool:
        return True

    def invoke(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        if not context.is_approved:
            return ToolResult(
                tool_name=self.name,
                status="unapproved",
                result=None,
                error="Explicit user approval required for side-effect tool",
                requires_approval=True,
            )
        return ToolResult(
            tool_name=self.name,
            status="success",
            result={"sent_to": arguments.get("recipient")},
        )


class FakeToolRegistry(ToolRegistry):
    def __init__(self, tools: list[Tool] | None = None):
        self._tools: dict[str, Tool] = {}
        for t in tools or [FakeFormatTool(), FakeSideEffectTool()]:
            self._tools[t.name] = t

    def describe_available(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name=t.name,
                description=f"Fake tool: {t.name}",
                input_schema=t.input_schema,
                is_side_effect=t.is_side_effect,
            )
            for t in self._tools.values()
        ]

    def invoke(self, name: str, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                status="error",
                error=f"Tool '{name}' not found",
            )
        return tool.invoke(arguments, context)

