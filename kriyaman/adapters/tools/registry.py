import json
from typing import Any
from domain.models import ToolContext, ToolDescriptor, ToolResult
from domain.ports.tools import Tool, ToolRegistry


class TableFormatterTool:
    """Formats structured row/column records into Markdown tables."""

    @property
    def name(self) -> str:
        return "table_formatter"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "headers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of column header titles",
                },
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "description": "List of rows, each containing cell string values",
                },
            },
            "required": ["headers", "rows"],
        }

    @property
    def is_side_effect(self) -> bool:
        return False

    def invoke(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        headers = arguments.get("headers", [])
        rows = arguments.get("rows", [])
        if not headers or not rows:
            return ToolResult(
                tool_name=self.name,
                status="error",
                error="Both 'headers' and 'rows' must be non-empty lists.",
            )

        header_line = "| " + " | ".join(str(h) for h in headers) + " |"
        sep_line = "| " + " | ".join("---" for _ in headers) + " |"
        row_lines = [
            "| " + " | ".join(str(cell) for cell in row) + " |"
            for row in rows
        ]
        markdown_table = "\n".join([header_line, sep_line, *row_lines])

        return ToolResult(
            tool_name=self.name,
            status="success",
            result={"markdown_table": markdown_table},
        )


class CalculationReconciliationTool:
    """Performs deterministic financial and mathematical reconciliation calculations."""

    @property
    def name(self) -> str:
        return "calculator_reconciliation"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["sum", "difference", "variance_percentage", "multiply", "divide"],
                    "description": "Mathematical operation to perform",
                },
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "List of numeric values",
                },
            },
            "required": ["operation", "values"],
        }

    @property
    def is_side_effect(self) -> bool:
        return False

    def invoke(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        op = arguments.get("operation")
        raw_values = arguments.get("values", [])
        try:
            values = [float(v) for v in raw_values]
        except (ValueError, TypeError) as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                error=f"Invalid numeric values: {e}",
            )

        if not values:
            return ToolResult(
                tool_name=self.name,
                status="error",
                error="Values list must not be empty.",
            )

        if op == "sum":
            res = sum(values)
        elif op == "difference":
            if len(values) < 2:
                return ToolResult(tool_name=self.name, status="error", error="Difference requires at least 2 values.")
            res = values[0] - sum(values[1:])
        elif op == "multiply":
            res = 1.0
            for v in values:
                res *= v
        elif op == "divide":
            if len(values) < 2:
                return ToolResult(tool_name=self.name, status="error", error="Divide requires at least 2 values.")
            res = values[0]
            for v in values[1:]:
                if v == 0.0:
                    return ToolResult(tool_name=self.name, status="error", error="Division by zero.")
                res /= v
        elif op == "variance_percentage":
            if len(values) != 2:
                return ToolResult(tool_name=self.name, status="error", error="Variance percentage requires exactly 2 values [actual, expected].")
            actual, expected = values[0], values[1]
            if expected == 0.0:
                return ToolResult(tool_name=self.name, status="error", error="Cannot calculate variance against zero expected value.")
            res = ((actual - expected) / abs(expected)) * 100.0
        else:
            return ToolResult(tool_name=self.name, status="error", error=f"Unsupported operation: {op}")

        return ToolResult(
            tool_name=self.name,
            status="success",
            result={"operation": op, "result": round(res, 6)},
        )


class DefaultToolRegistry(ToolRegistry):
    """Allowlisted tool registry supporting formatting, reconciliation, and search tools."""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        default_tools: list[Tool] = tools or [
            TableFormatterTool(),
            CalculationReconciliationTool(),
        ]
        self._tools: dict[str, Tool] = {t.name: t for t in default_tools}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def describe_available(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name=t.name,
                description=t.__doc__ or f"Allowlisted tool {t.name}",
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
                error=f"Tool '{name}' is not registered in ToolRegistry.",
            )
        return tool.invoke(arguments, context)
