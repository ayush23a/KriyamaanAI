from typing import Any, Protocol


class ObservabilityPort(Protocol):
    def start_trace(
        self,
        name: str,
        run_id: str,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Start a trace for a run. Best-effort and non-blocking."""
        ...

    def start_span(
        self,
        trace: Any,
        name: str,
        span_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Start a child span or generation. Best-effort and non-blocking."""
        ...

    def end_span(
        self,
        span: Any,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """End a child span with optional output/metadata. Best-effort and non-blocking."""
        ...

    def end_trace(
        self,
        trace: Any,
        status: str,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """End a trace with status and optional output. Best-effort and non-blocking."""
        ...

    def record_event(
        self,
        name: str,
        payload: dict[str, Any],
        run_id: str | None = None,
    ) -> None:
        """Record an application event. Best-effort and non-blocking."""
        ...

