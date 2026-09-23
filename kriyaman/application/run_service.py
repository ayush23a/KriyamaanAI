import asyncio
import re
import uuid
from typing import Any
from langgraph.checkpoint.base import BaseCheckpointSaver
from persistence.checkpoint import PostgresCheckpointSaver
from persistence.db import get_sync_session_factory
from sqlalchemy.ext.asyncio import AsyncSession
from domain.errors import ResourceNotFoundError
from domain.models import (
    Answer,
    ExecutionBudgets,
    MemoryItem,
    UsageSnapshot,
)
from domain.ports.cache import CachePort
from domain.ports.embeddings import EmbeddingProvider
from domain.ports.llm import LLMProvider
from domain.ports.reranker import Reranker
from domain.ports.vector_store import VectorStore
from domain.ports.web_search import WebSearchProvider
from application.answer_service import AnswerService
from application.context_builder import ContextBuilder
from application.controller import AgentController
from application.evidence_judge import EvidenceJudge
from application.graph.builder import create_kriyaman_graph
from application.graph.nodes import GraphNodes
from application.graph.state import GraphState
from application.retrieval_agent import RetrievalAgent
from persistence.repositories.document_repo import DocumentRepository
from persistence.repositories.memory_repo import MemoryRepository
from persistence.repositories.run_repo import RunEventRepository, RunRepository
from persistence.repositories.session_repo import SessionRepository
from persistence.repositories.turn_repo import ConversationTurnRepository


class RunExecutionService:
    """Coordinates execution of query runs across repositories and LangGraph runtime."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        llm_provider: LLMProvider | None = None,
        reranker: Reranker | None = None,
        web_search: WebSearchProvider | None = None,
        cache_port: CachePort | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
    ):
        self.vector_store = vector_store
        self.llm_provider = llm_provider
        self.reranker = reranker
        self.web_search = web_search
        self.cache_port = cache_port
        self.checkpointer = checkpointer or PostgresCheckpointSaver()

    def build_graph(
        self,
        enable_web_search: bool = False,
        llm_provider: LLMProvider | None = None,
        web_search: WebSearchProvider | None = None,
    ):
        """Assemble the compiled Kriyamaan graph using configured providers and checkpointer."""
        active_llm = llm_provider or self.llm_provider
        controller = AgentController(llm_provider=active_llm)
        active_web = web_search or self.web_search
        web_provider = active_web if enable_web_search else None
        retrieval_agent = RetrievalAgent(
            vector_store=self.vector_store,
            reranker=self.reranker,
            web_search=web_provider,
        )
        evidence_judge = EvidenceJudge(llm_provider=active_llm)
        context_builder = ContextBuilder()
        answer_service = AnswerService(llm=active_llm) if active_llm else None

        nodes = GraphNodes(
            controller=controller,
            retrieval_agent=retrieval_agent,
            evidence_judge=evidence_judge,
            context_builder=context_builder,
            answer_service=answer_service,
        )
        return create_kriyaman_graph(nodes=nodes, checkpointer=self.checkpointer)


    async def execute_run(
        self,
        db: AsyncSession,
        session_id: str,
        query: str,
        budgets: ExecutionBudgets | None = None,
        enable_web_search: bool = False,
        llm_provider: LLMProvider | None = None,
        web_search: WebSearchProvider | None = None,
    ) -> dict[str, Any]:
        session_repo = SessionRepository(db)
        turn_repo = ConversationTurnRepository(db)
        memory_repo = MemoryRepository(db)
        run_repo = RunRepository(db)
        event_repo = RunEventRepository(db)

        # 1. Verify session
        session = await session_repo.get_by_id(session_id)
        if not session:
            raise ResourceNotFoundError(
                f"Session '{session_id}' not found.", resource_type="session", resource_id=session_id
            )

        # 2. Retrieve session context, documents & memories
        principal_id = session.memory_principal_id
        memories = await memory_repo.list_by_principal(principal_id)
        recent_turns = await turn_repo.list_recent_turns(session_id, limit=10)
        doc_repo = DocumentRepository(db)
        docs = await doc_repo.list_by_session(session_id)
        session_documents = [d.name for d in docs if getattr(d, "name", None)]

        session_history: list[str] = []
        for t in recent_turns:
            ans_text = ""
            if t.answer_json and isinstance(t.answer_json, dict):
                ans_text = t.answer_json.get("answer_text", "")
            session_history.append(f"User: {t.user_query}\nAssistant: {ans_text}")

        memory_items: list[MemoryItem] = [
            MemoryItem(
                id=m.id,
                memory_principal_id=m.memory_principal_id,
                content=m.content,
                kind=m.kind,
            )
            for m in memories
        ]
        memory_items.extend(
            MemoryItem(
                id=f"turn_{turn.id}",
                memory_principal_id=principal_id,
                content=f"User: {turn.user_query}\nAssistant: {answer_text}",
                kind="session_turn",
            )
            for turn in recent_turns
            for answer_text in [
                (
                    turn.answer_json.get("answer_text", "")
                    if turn.answer_json and isinstance(turn.answer_json, dict)
                    else ""
                )
            ]
        )

        # 3. Create run record
        run_id = str(uuid.uuid4())
        active_budgets = budgets or ExecutionBudgets()
        await run_repo.create(
            session_id=session_id,
            budgets=active_budgets.model_dump(mode="json"),
            run_id=run_id,
            status="running",
        )

        # 4. Assemble Graph Nodes & Graph
        graph = self.build_graph(
            enable_web_search=enable_web_search,
            llm_provider=llm_provider,
            web_search=web_search,
        )

        # 5. Initialize State
        normalized_query = re.sub(r"\s+", " ", query.strip())
        initial_state: GraphState = {
            "run_id": run_id,
            "session_id": session_id,
            "user_query": query,
            "normalized_query": normalized_query,
            "status": "running",
            "controller_plan": None,
            "plan_history": [],
            "evidence": [],
            "evidence_assessment": None,
            "memory_items": memory_items,
            "tool_results": [],
            "retrieval_iterations": 0,
            "tool_calls": 0,
            "budgets": active_budgets,
            "usage": UsageSnapshot(),
            "execution_events": [],
            "context_package": None,
            "answer": None,
            "failure": None,
            "guardrail_rejected": False,
            "guardrail_reason_code": None,
            "session_documents": session_documents,
        }

        # 6. Execute Graph
        active_llm = llm_provider or self.llm_provider
        if hasattr(active_llm, "reset_cumulative_usage"):
            active_llm.reset_cumulative_usage()

        final_state: GraphState = await asyncio.to_thread(
            graph.invoke, initial_state, {"configurable": {"thread_id": run_id}}
        )

        if hasattr(active_llm, "cumulative_usage") and active_llm.cumulative_usage:
            final_state["usage"] = active_llm.cumulative_usage

        # 7. Persist Events
        for event in final_state.get("execution_events", []):
            await event_repo.append_event(
                run_id=run_id,
                sequence=event.sequence,
                event_type=event.event_type,
                payload=event.payload,
            )

        # 8. Persist Turn if terminal answer exists
        ans = final_state.get("answer")
        ans_dict = None
        if ans:
            ans_dict = ans.model_dump(mode="json") if hasattr(ans, "model_dump") else dict(ans)
            await turn_repo.create(
                session_id=session_id,
                run_id=run_id,
                user_query=query,
                answer=ans_dict,
                status="completed",
            )

        # 9. Update Terminal Run Record
        final_decision = None
        if final_state.get("evidence_assessment"):
            final_decision = final_state["evidence_assessment"].decision

        usage_dict = None
        if final_state.get("usage"):
            usage = final_state["usage"]
            usage_dict = usage.model_dump(mode="json")

        await run_repo.update_terminal(
            run_id=run_id,
            status=final_state["status"],
            final_decision=final_decision,
            usage=usage_dict,
        )

        await db.commit()

        return {
            "run_id": run_id,
            "session_id": session_id,
            "status": final_state["status"],
            "state": final_state,
        }
