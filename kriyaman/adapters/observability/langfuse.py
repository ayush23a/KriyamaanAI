import logging
from typing import Any
from domain.ports.observability import ObservabilityPort
from adapters.observability.noop import NoOpObservabilityAdapter

logger = logging.getLogger(__name__)


class LangfuseObservabilityAdapter(ObservabilityPort):
    """Best-effort Langfuse observability adapter with safe failure degradation."""

    def __init__(
        self,
        public_key: str = "",
        secret_key: str = "",
        host: str = "https://cloud.langfuse.com",
        enabled: bool = True,
    ):
        self.enabled = enabled and bool(public_key and secret_key)
        self.public_key = public_key
        self.secret_key = secret_key
        self.host = host
        self._client: Any = None
        self._fallback = NoOpObservabilityAdapter()

        if self.enabled:
            try:
                from langfuse import Langfuse  # type: ignore[import-untyped]

                self._client = Langfuse(
                    public_key=self.public_key,
                    secret_key=self.secret_key,
                    host=self.host,
                )
            except Exception as e:
                logger.warning(
                    "Failed to initialize Langfuse client (%s); degrading to no-op observability.",
                    e,
                )
                self.enabled = False

    def start_trace(
        self,
        name: str,
        run_id: str,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        if not self.enabled or not self._client:
            return self._fallback.start_trace(name, run_id, session_id, metadata)
        try:
            # Clean metadata: never log secrets or sensitive payloads
            clean_meta = {
                k: v
                for k, v in (metadata or {}).items()
                if "key" not in k.lower() and "secret" not in k.lower()
            }
            trace = self._client.trace(
                name=name,
                id=run_id,
                session_id=session_id,
                metadata=clean_meta,
            )
            return trace
        except Exception as e:
            logger.warning("Langfuse start_trace failed: %s", e)
            return self._fallback.start_trace(name, run_id, session_id, metadata)

    def start_span(
        self,
        trace: Any,
        name: str,
        span_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        if not self.enabled or not self._client or not hasattr(trace, "span"):
            return self._fallback.start_span(trace, name, span_type, metadata)
        try:
            clean_meta = {
                k: v
                for k, v in (metadata or {}).items()
                if "key" not in k.lower() and "secret" not in k.lower()
            }
            if span_type == "generation" and hasattr(trace, "generation"):
                return trace.generation(name=name, metadata=clean_meta)
            return trace.span(name=name, metadata=clean_meta)
        except Exception as e:
            logger.warning("Langfuse start_span failed: %s", e)
            return self._fallback.start_span(trace, name, span_type, metadata)

    def end_span(
        self,
        span: Any,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled or not self._client or not hasattr(span, "end"):
            return self._fallback.end_span(span, output, metadata)
        try:
            update_kwargs: dict[str, Any] = {}
            if output is not None:
                update_kwargs["output"] = output
            if metadata:
                clean_meta = {
                    k: v
                    for k, v in metadata.items()
                    if "key" not in k.lower() and "secret" not in k.lower()
                }
                update_kwargs["metadata"] = clean_meta
            span.end(**update_kwargs)
        except Exception as e:
            logger.warning("Langfuse end_span failed: %s", e)

    def end_trace(
        self,
        trace: Any,
        status: str,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled or not self._client or not hasattr(trace, "update"):
            return self._fallback.end_trace(trace, status, output, metadata)
        try:
            update_kwargs: dict[str, Any] = {"status": status}
            if output is not None:
                update_kwargs["output"] = output
            if metadata:
                clean_meta = {
                    k: v
                    for k, v in metadata.items()
                    if "key" not in k.lower() and "secret" not in k.lower()
                }
                update_kwargs["metadata"] = clean_meta
            trace.update(**update_kwargs)
            if hasattr(self._client, "flush"):
                self._client.flush()
        except Exception as e:
            logger.warning("Langfuse end_trace failed: %s", e)

    def record_event(
        self,
        name: str,
        payload: dict[str, Any],
        run_id: str | None = None,
    ) -> None:
        if not self.enabled or not self._client:
            return self._fallback.record_event(name, payload, run_id)
        try:
            clean_payload = {
                k: v
                for k, v in payload.items()
                if "key" not in k.lower() and "secret" not in k.lower()
            }
            if hasattr(self._client, "event"):
                self._client.event(name=name, metadata=clean_payload, trace_id=run_id)
        except Exception as e:
            logger.warning("Langfuse record_event failed: %s", e)
