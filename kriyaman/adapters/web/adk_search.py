import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from google.adk.tools import google_search

from domain.models import EvidenceItem, WebSearchRequest
from domain.ports.web_search import WebSearchProvider

logger = logging.getLogger(__name__)


class WebSearchAdapter(WebSearchProvider):
    """Web search adapter using Google ADK's google_search with Tavily fallback."""

    def __init__(
        self,
        google_api_key: str = "",
        tavily_api_key: str = "",
        model_name: str = "gemini-2.5-flash",
        offline_fallback: WebSearchProvider | None = None,
    ):
        self.google_api_key = google_api_key
        self.tavily_api_key = tavily_api_key
        self.model_name = model_name
        self.offline_fallback = offline_fallback
        self.adk_search_tool = google_search

    def search(self, request: WebSearchRequest) -> list[EvidenceItem]:
        query = request.query.strip() if request.query else ""
        if not query:
            return []

        # 1. Primary: Google Search via Google ADK / GenAI
        if self.google_api_key:
            try:
                evidence = self._search_google_adk(query, request.top_k)
                if evidence:
                    return evidence
            except Exception as exc:
                logger.warning(
                    "Google ADK search failed (%s); cascading to Tavily fallback.",
                    exc,
                )

        # 2. Secondary Fallback: Tavily API
        if self.tavily_api_key:
            try:
                evidence = self._search_tavily(query, request.top_k)
                if evidence:
                    return evidence
            except Exception as exc:
                logger.warning("Tavily search fallback failed (%s).", exc)

        # 3. Tertiary Fallback: Offline / Mock
        if self.offline_fallback is not None:
            logger.debug("Falling back to offline mock search for query: %s", query)
            return self.offline_fallback.search(request)

        # Default synthetic item if all fallbacks exhausted
        return [
            EvidenceItem(
                evidence_id=f"ev_web_fallback_{abs(hash(query)) % 10000}",
                source_type="web",
                source_id="web_fallback",
                title=f"Web search for {query}",
                content=f"No live web search results available for: '{query}'.",
                uri="https://web.fallback",
                retrieval_method="web_search_fallback",
                retrieval_score=0.5,
                retrieved_at=datetime.now(timezone.utc),
            )
        ]

    def _search_google_adk(self, query: str, top_k: int) -> list[EvidenceItem]:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.google_api_key)

        # Use Google Search tool from Google ADK / GenAI
        response = client.models.generate_content(
            model=self.model_name,
            contents=f"Search the web and provide detailed factual findings for: {query}",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.0,
            ),
        )

        evidence_items: list[EvidenceItem] = []
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            grounding_meta = getattr(candidate, "grounding_metadata", None)
            grounding_chunks = getattr(grounding_meta, "grounding_chunks", []) or []

            for i, chunk in enumerate(grounding_chunks[:top_k]):
                web = getattr(chunk, "web", None)
                if web:
                    uri = getattr(web, "uri", None) or f"https://www.google.com/search?q={query}"
                    title = getattr(web, "title", None) or "Google Search Result"
                    evidence_items.append(
                        EvidenceItem(
                            evidence_id=f"ev_web_adk_{i}_{abs(hash(uri)) % 10000}",
                            source_type="web",
                            source_id=uri,
                            title=title,
                            content=response.text or f"Search result for {query}",
                            uri=uri,
                            retrieval_method="google_adk_search",
                            retrieval_score=0.9,
                            retrieved_at=datetime.now(timezone.utc),
                        )
                    )

            # If chunks weren't parsed but grounded answer text exists
            if not evidence_items and response.text:
                evidence_items.append(
                    EvidenceItem(
                        evidence_id=f"ev_web_adk_{abs(hash(query)) % 10000}",
                        source_type="web",
                        source_id="google_adk_search",
                        title=f"Google Search: {query}",
                        content=response.text,
                        uri="https://www.google.com",
                        retrieval_method="google_adk_search",
                        retrieval_score=0.85,
                        retrieved_at=datetime.now(timezone.utc),
                    )
                )

        return evidence_items

    def _search_tavily(self, query: str, top_k: int) -> list[EvidenceItem]:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "max_results": top_k,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        items: list[EvidenceItem] = []
        for i, res in enumerate(data.get("results", [])[:top_k]):
            url = res.get("url") or f"https://tavily.search/{i}"
            items.append(
                EvidenceItem(
                    evidence_id=f"ev_web_tavily_{i}_{abs(hash(url)) % 10000}",
                    source_type="web",
                    source_id=url,
                    title=res.get("title") or "Web Search Result",
                    content=res.get("content") or "",
                    uri=url,
                    retrieval_method="web_search_tavily",
                    retrieval_score=float(res.get("score") or 0.8),
                    retrieved_at=datetime.now(timezone.utc),
                )
            )
        return items
