from datetime import datetime, timezone
from domain.models import EvidenceItem, WebSearchRequest
from domain.ports.web_search import WebSearchProvider


class MockWebSearchAdapter(WebSearchProvider):
    """Mock web search provider for offline tests and non-networked environments."""

    def __init__(self, mocked_results: list[EvidenceItem] | None = None):
        self._mocked_results = mocked_results or []

    def set_results(self, results: list[EvidenceItem]) -> None:
        self._mocked_results = results

    def search(self, request: WebSearchRequest) -> list[EvidenceItem]:
        if self._mocked_results:
            return self._mocked_results[: request.top_k]

        # Default fallback synthetic result
        return [
            EvidenceItem(
                evidence_id=f"web_mock_{hash(request.query) % 10000}",
                source_type="web",
                source_id="mock_web_source",
                title=f"Web search results for: {request.query}",
                content=f"Synthetic web snippet relevant to query: '{request.query}'.",
                uri="https://mock.web/search",
                retrieval_method="web_search",
                retrieval_score=0.85,
                retrieved_at=datetime.now(timezone.utc),
            )
        ]

