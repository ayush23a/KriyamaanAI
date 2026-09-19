import hashlib
import logging
from typing import Any
from domain.models import (
    AcquisitionPlan,
    EvidenceItem,
    MemorySearchRequest,
    ToolContext,
    ToolResult,
    VectorSearchRequest,
    WebSearchRequest,
)
from domain.ports.memory import MemoryStore
from domain.ports.reranker import Reranker
from domain.ports.tools import ToolRegistry
from domain.ports.vector_store import VectorStore
from domain.ports.web_search import WebSearchProvider

logger = logging.getLogger(__name__)


class RetrievalAgent:
    """Executor of controller AcquisitionPlans across vector store, memory, tools, and web."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        reranker: Reranker | None = None,
        memory_store: MemoryStore | None = None,
        web_search: WebSearchProvider | None = None,
        tool_registry: ToolRegistry | None = None,
    ):
        self.vector_store = vector_store
        self.reranker = reranker
        self.memory_store = memory_store
        self.web_search = web_search
        self.tool_registry = tool_registry

    def execute(
        self,
        plan: AcquisitionPlan,
        session_id: str,
        run_id: str,
        memory_principal_id: str,
        existing_evidence: list[EvidenceItem] | None = None,
        is_tool_approved: bool = False,
    ) -> tuple[list[EvidenceItem], list[ToolResult]]:
        """Execute the plan and return newly acquired deduplicated evidence and tool results."""
        new_evidence: list[EvidenceItem] = []
        tool_results: list[ToolResult] = []

        query = plan.query or ""

        # 1. Vector / Hybrid / Metadata search
        if plan.action in ["vector_search", "hybrid_search", "metadata_filter"]:
            if self.vector_store is not None:
                search_filters = dict(plan.filters)
                search_filters.setdefault("session_id", session_id)

                req = VectorSearchRequest(
                    query=query,
                    top_k=plan.top_k,
                    filters=search_filters,
                )
                items = self.vector_store.search(req)

                # Rerank if requested
                if plan.rerank and self.reranker is not None and items:
                    items = self.reranker.rerank(query, items, top_k=plan.top_k)

                new_evidence.extend(items)

        # 2. Web search
        elif plan.action == "web_search":
            if self.web_search is not None:
                req = WebSearchRequest(query=query, top_k=plan.top_k)
                items = self.web_search.search(req)
                new_evidence.extend(items)

        # 3. Memory search
        elif plan.action == "memory_search":
            if self.memory_store is not None:
                req = MemorySearchRequest(
                    memory_principal_id=memory_principal_id,
                    query=query,
                    top_k=plan.top_k,
                )
                memories = self.memory_store.search_long_term(req)
                for mem in memories:
                    new_evidence.append(
                        EvidenceItem(
                            evidence_id=f"ev_mem_{mem.id}",
                            source_type="memory",
                            source_id=mem.id,
                            title="Long-term Memory",
                            content=mem.content,
                            metadata=mem.metadata,
                            retrieval_method="memory_search",
                            retrieval_score=0.9,
                        )
                    )

        # 4. Tool call
        elif plan.action == "tool_call":
            if self.tool_registry is not None and plan.tool_name:
                ctx = ToolContext(
                    run_id=run_id,
                    session_id=session_id,
                    is_approved=is_tool_approved,
                )
                result = self.tool_registry.invoke(plan.tool_name, plan.tool_arguments, ctx)
                tool_results.append(result)

                if result.status == "success" and result.result is not None:
                    new_evidence.append(
                        EvidenceItem(
                            evidence_id=f"ev_tool_{plan.tool_name}_{run_id[:8]}",
                            source_type="tool",
                            source_id=plan.tool_name,
                            title=f"Tool: {plan.tool_name}",
                            content=str(result.result),
                            retrieval_method="tool_call",
                            retrieval_score=1.0,
                        )
                    )

        # 5. Deduplicate against existing and current evidence
        existing_hashes = set()
        for item in existing_evidence or []:
            h = hashlib.sha256(item.content.strip().encode("utf-8")).hexdigest()
            existing_hashes.add(h)

        deduped_new_evidence: list[EvidenceItem] = []
        for item in new_evidence:
            h = hashlib.sha256(item.content.strip().encode("utf-8")).hexdigest()
            if h not in existing_hashes:
                existing_hashes.add(h)
                deduped_new_evidence.append(item)

        return deduped_new_evidence, tool_results

