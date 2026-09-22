import re
from typing import Any
from domain.models import (
    AcquisitionPlan,
    CallBudget,
    ChatMessage,
    EvidenceAssessment,
    EvidenceItem,
    ExecutionBudgets,
    MemoryItem,
    UsageSnapshot,
)
from domain.ports.llm import LLMProvider
from domain.ports.llm import LLMCallRole, LLMProvider
from domain.ports.tools import ToolRegistry
from application.evidence_judge import STOPWORDS, detect_query_intent

CONTROLLER_SYSTEM_PROMPT = """You are the Agent Controller for Kriyamaan Agentic RAG.
Your task is to plan the next information acquisition action based on the user query, current evidence, and execution budgets.

Actions available:
- 'vector_search': search internal document vector store. (DEFAULT for questions about documents, files, ledgers, statements, or domain topics).
- 'hybrid_search': search with keyword and vector match.
- 'web_search': search public web for real-time or external info.
- 'memory_search': query long-term user memories.
- 'tool_call': execute an available registered tool.
- 'no_acquisition_required': for greetings, small talk, or self-contained logical queries.
- 'clarify': ONLY if the user query is completely unintelligible or nonsensical. Do NOT use clarify if internal document retrieval could answer it.
- 'abstain': if query is prohibited, harmful, or out-of-scope.

Decision Rules:
1. Always prefer 'vector_search' or 'hybrid_search' for questions referencing uploaded documents, files, accounts, ledgers, or business statements.
2. Even if a query asks to cross-reference multiple sources or mentions using the web, begin information acquisition by searching the internal vector store ('vector_search').
3. Never choose 'clarify' when the user provides specific domain or file references (e.g. General Ledger, Undeposited Funds, Bank Statement, COA).

Return structured AcquisitionPlan."""

FOLLOW_UP_HELP_PATTERNS = (
    r"\bwhat\s+(?:additional\s+)?(?:information|details|documents?|files?)\s+"
    r"(?:do\s+you\s+need|can\s+i\s+provide|would\s+help)\b",
    r"\bhow\s+can\s+i\s+(?:help|provide|clarify)\b",
    r"\bwhat\s+(?:is\s+)?missing\b",
    r"\bwhy\s+(?:can'?t|cannot|couldn'?t)\s+you\s+(?:answer|find|verify)\b",
    r"\bwhat\s+do\s+you\s+need\s+(?:from\s+me|to\s+answer)\b",
    r"\bdo\s+i\s+need\s+to\s+(?:upload|provide|share)\b",
)


class AgentController:
    """Controller responsible for deciding information-acquisition actions."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        tool_registry: ToolRegistry | None = None,
    ):
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry

    def decide(
        self,
        query: str,
        normalized_query: str,
        session_history: list[str] | None = None,
        memory_items: list[MemoryItem] | None = None,
        prior_assessment: EvidenceAssessment | None = None,
        budgets: ExecutionBudgets | None = None,
        usage: UsageSnapshot | None = None,
        available_tools: list[str] | None = None,
    ) -> AcquisitionPlan:
        """Produce an initial or refined AcquisitionPlan."""
        # 1. Deterministic fast-path rules for greetings / simple conversational inputs
        lower_q = normalized_query.strip().lower()
        greetings = ["hi", "hello", "hey", "good morning", "good evening", "good afternoon", "thanks", "thank you", "how are you"]
        tokens = set(re.findall(r"\b\w+\b", lower_q))
        if (
            lower_q in greetings
            or any(lower_q.startswith(g) for g in ["hi ", "hello ", "hey "])
            or (tokens and tokens <= {"hi", "hello", "hey", "there", "thanks", "thank", "you"})
        ):
            return AcquisitionPlan(
                action="no_acquisition_required",
                query=None,
                reason_code="conversational_greeting",
                expected_information_gain="low",
            )

        if any(re.search(pattern, lower_q) for pattern in FOLLOW_UP_HELP_PATTERNS):
            return AcquisitionPlan(
                action="no_acquisition_required",
                query=None,
                reason_code="conversation_follow_up_help",
                expected_information_gain="low",
            )

        # 2. Check if a registered tool is explicitly requested
        if available_tools:
            for tool_name in available_tools:
                if f"call tool {tool_name}" in lower_q or f"use tool {tool_name}" in lower_q:
                    return AcquisitionPlan(
                        action="tool_call",
                        query=normalized_query,
                        tool_name=tool_name,
                        reason_code="explicit_tool_request",
                        expected_information_gain="high",
                    )

        # 3. If LLM provider is available, use structured generation
        if self.llm_provider is not None:
            messages = [
                ChatMessage(role="system", content=CONTROLLER_SYSTEM_PROMPT),
                ChatMessage(
                    role="user",
                    content=(
                        f"Query: {normalized_query}\n"
                        f"Prior Assessment: {prior_assessment.model_dump_json() if prior_assessment else 'None'}\n"
                        f"Available Tools: {available_tools or []}\n"
                        "Choose the best AcquisitionPlan."
                    ),
                ),
            ]
            try:
                res = self.llm_provider.generate_structured(
                    messages=messages,
                    schema=AcquisitionPlan,
                    budget=CallBudget(max_tokens=500, timeout_seconds=10.0),
                    role=LLMCallRole.PLANNER,
                )
                return res.data
            except Exception:
                pass  # Fallback to default first-pass vector search

        # 4. Default fallback: internal vector search on normalized query
        return AcquisitionPlan(
            action="vector_search",
            query=normalized_query,
            top_k=5,
            rerank=True,
            reason_code="first_pass_vector_search",
            expected_information_gain="high",
        )

    def refine(
        self,
        query: str,
        prior_assessment: EvidenceAssessment,
        retrieval_iterations: int,
        budgets: ExecutionBudgets,
    ) -> AcquisitionPlan:
        """Refine the acquisition plan when evidence is insufficient or conflicting."""
        if retrieval_iterations >= budgets.max_retrieval_iterations:
            return AcquisitionPlan(
                action="abstain" if prior_assessment.decision == "insufficient" else "no_acquisition_required",
                query=None,
                reason_code="max_iterations_reached",
                expected_information_gain="low",
            )

        if self.llm_provider is not None:
            messages = [
                ChatMessage(role="system", content=CONTROLLER_SYSTEM_PROMPT),
                ChatMessage(
                    role="user",
                    content=(
                        f"Original Query: {query}\n"
                        f"Prior Assessment: {prior_assessment.model_dump_json()}\n"
                        f"Current Retrieval Iterations: {retrieval_iterations}/{budgets.max_retrieval_iterations}\n"
                        "The prior evidence was insufficient or conflicting. Produce a refined AcquisitionPlan with a specific search query or action to address the missing aspects."
                    ),
                ),
            ]
            try:
                res = self.llm_provider.generate_structured(
                    messages=messages,
                    schema=AcquisitionPlan,
                    budget=CallBudget(max_tokens=500, timeout_seconds=10.0),
                    role=LLMCallRole.PLANNER,
                )
                return res.data
            except Exception:
                pass  # Fallback to heuristic refinement

        intent = detect_query_intent(query)
        if intent == "summary":
            refined_query = "document summary main findings key points"
        elif intent == "advantages":
            refined_query = "system strengths benefits advantages positive findings"
        elif intent == "limitations":
            refined_query = "limitations weaknesses risks problems"
        elif intent == "findings":
            refined_query = "main findings results conclusions"
        elif intent == "synthesis":
            refined_query = "common findings differences agreements disagreements"
        else:
            # Filter missing aspects against STOPWORDS so generic stopwords are never appended
            clean_aspects = [
                a for a in prior_assessment.missing_aspects
                if a.lower() not in STOPWORDS and len(a) > 2
            ]
            refined_query = query
            if clean_aspects:
                aspect = clean_aspects[0]
                refined_query = f"{query} {aspect}"

        action = "vector_search"
        if prior_assessment.decision == "conflicting":
            # For conflicting evidence, try hybrid search or corroborating source
            action = "hybrid_search"

        return AcquisitionPlan(
            action=action,
            query=refined_query,
            top_k=5,
            rerank=True,
            reason_code=f"refine_pass_{retrieval_iterations + 1}",
            expected_information_gain="medium",
        )
