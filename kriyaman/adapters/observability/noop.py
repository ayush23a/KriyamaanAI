from typing import Any
from domain.ports.observability import ObservabilityPort


class NoOpObservabilityAdapter(ObservabilityPort):
    """No-op observability adapter for Phase 1 foundation and offline testing."""

    def start_trace(
        self,
        name: str,
        run_id: str,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        return {"name": name, "run_id": run_id, "session_id": session_id}

    def start_span(
        self,
        trace: Any,
        name: str,
        span_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        return {"name": name, "span_type": span_type, "parent": trace}

    def end_span(
        self,
        span: Any,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        pass

    def end_trace(
        self,
        trace: Any,
        status: str,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        pass

    def record_event(
        self,
        name: str,
        payload: dict[str, Any],
        run_id: str | None = None,
    ) -> None:
        pass

