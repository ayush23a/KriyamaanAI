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
    PlanHistoryEntry,
    UsageSnapshot,
)
from domain.ports.llm import LLMProvider
from domain.ports.llm import LLMCallRole, LLMProvider
from domain.ports.tools import ToolRegistry
from application.evidence_judge import STOPWORDS, detect_query_intent

CONTROLLER_SYSTEM_PROMPT = """You are the Agent Controller for Kriyamaan Agentic RAG.
Your task is to plan the next information acquisition action based on the user query, uploaded documents, conversation history, current evidence, and execution budgets.

Actions available:
- 'vector_search': search internal document vector store. (DEFAULT for questions about documents, files, ledgers, statements, or domain topics).
- 'hybrid_search': search with keyword and vector match.
- 'web_search': search public web for real-time or external info (ONLY allowed when Web Search is enabled).
- 'memory_search': query long-term user memories.
- 'tool_call': execute an available registered tool.
- 'no_acquisition_required': for greetings, small talk, or self-contained logical queries.
- 'clarify': ONLY if the user query is completely unintelligible or nonsensical. Do NOT use clarify if internal document retrieval could answer it.
- 'abstain': if query is prohibited, harmful, or out-of-scope.

Decision Rules:
1. Always prefer 'vector_search' or 'hybrid_search' for questions referencing uploaded documents, files, accounts, ledgers, or business statements.
2. If session documents are present and the user asks general, summary, or follow-up questions referencing 'this document', 'this file', 'it', 'what is this about', or 'what does this convey':
   - ALWAYS choose 'vector_search'.
   - REWRITE the retrieval query into a targeted semantic search query matching the document's core content, overview, and responsibilities (e.g. including the document title or key terms like 'overview summary role responsibilities qualifications requirements').
   - NEVER choose 'clarify' when session documents are available.
3. If session documents are present, begin information acquisition by searching the internal vector store ('vector_search').
4. If Web Search is enabled and prior internal document retrieval yielded insufficient evidence or missing aspects (such as external company details, founders, public facts, or current information not in the files), switch to 'web_search' with a query targeted at the missing information.
5. If no session documents are uploaded and Web Search is enabled, choose 'web_search' for general, external, or factual questions.
6. If Web Search is NOT enabled, NEVER choose 'web_search'.
7. Never choose 'clarify' when the user provides specific domain or file references (e.g. General Ledger, Undeposited Funds, Bank Statement, COA).
8. Only choose 'clarify' if the query is truly indecipherable gibberish with no relevance to session documents or conversation.

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


def formulate_web_query(
    query: str,
    missing_aspects: list[str] | None = None,
    session_documents: list[str] | None = None,
) -> str:
    """Formulate a targeted public search query, resolving deictic references to grounded entities."""
    if not missing_aspects:
        return query.strip()

    aspect_text = " ".join(missing_aspects).strip()

    has_deictic = bool(
        re.search(
            r"\b(this|thsi|the)\s+(company|organization|firm|startup|agency|product|tool|system|app|service)\b",
            query,
            flags=re.IGNORECASE,
        )
        or re.search(r"\bwho\s+are\s+the\s+founders\b", query, flags=re.IGNORECASE)
    )

    if has_deictic and aspect_text:
        cleaned = re.sub(
            r"^(the\s+specific\s+names\s+of\s+the\s+founders\s+of\s+|the\s+specific\s+names\s+of\s+|the\s+specific\s+|the\s+names\s+of\s+|specific\s+|names\s+of\s+)",
            "",
            aspect_text,
            flags=re.IGNORECASE,
        ).strip()
        if cleaned:
            if "founder" in query.lower() and "founder" not in cleaned.lower():
                return f"founders of {cleaned}"
            return cleaned

    clean_aspects = [
        a for a in missing_aspects
        if a.lower() not in STOPWORDS and len(a) > 2
    ]
    if clean_aspects:
        return f"{query} {' '.join(clean_aspects)}".strip()

    return query.strip()


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
        session_documents: list[str] | None = None,
        session_history: list[str] | None = None,
        memory_items: list[MemoryItem] | None = None,
        prior_assessment: EvidenceAssessment | None = None,
        budgets: ExecutionBudgets | None = None,
        usage: UsageSnapshot | None = None,
        available_tools: list[str] | None = None,
        enable_web_search: bool = False,
    ) -> AcquisitionPlan:
        """Produce an initial or refined AcquisitionPlan."""
        # 1. Deterministic fast-path rules for pure greetings / pleasantries only
        lower_q = normalized_query.strip().lower()
        greetings = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon", "thanks", "thank you", "how are you"}
        tokens = set(re.findall(r"\b\w+\b", lower_q))
        pure_greeting_tokens = {"hi", "hello", "hey", "there", "thanks", "thank", "you", "good", "morning", "evening", "afternoon", "how", "are"}
        if (
            lower_q in greetings
            or (tokens and tokens <= pure_greeting_tokens and len(tokens) <= 4)
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

        # Identify if any session document is specifically referenced in the query
        matched_doc = None
        if session_documents:
            for doc in session_documents:
                doc_base = doc.lower().rsplit(".", 1)[0]
                if doc.lower() in lower_q or (len(doc_base) >= 3 and doc_base in lower_q):
                    matched_doc = doc
                    break

        # 3. If LLM provider is available, use structured generation
        if self.llm_provider is not None:
            doc_context = f"Uploaded Session Documents: {', '.join(session_documents)}" if session_documents else "Uploaded Session Documents: None"
            history_context = "\nRecent Conversation Turns:\n" + "\n".join(session_history[-4:]) if session_history else ""
            web_context = f"Web Search Enabled: {enable_web_search}"
            messages = [
                ChatMessage(role="system", content=CONTROLLER_SYSTEM_PROMPT),
                ChatMessage(
                    role="user",
                    content=(
                        f"Query: {normalized_query}\n"
                        f"{doc_context}\n"
                        f"{web_context}\n"
                        f"{history_context}\n"
                        f"Prior Assessment: {prior_assessment.model_dump_json() if prior_assessment else 'None'}\n"
                        f"Available Tools: {available_tools or []}\n"
                        "Choose the best AcquisitionPlan. If referencing an uploaded document, formulate a topical vector_search query. "
                        "If Web Search is enabled and no session documents exist, choose 'web_search' for general or external questions."
                    ),
                ),
            ]
            try:
                res = self.llm_provider.generate_structured(
                    messages=messages,
                    schema=AcquisitionPlan,
                    budget=CallBudget(max_tokens=1500, timeout_seconds=30.0),
                    role=LLMCallRole.PLANNER,
                )
                plan = res.data
                if plan.action == "web_search":
                    if not enable_web_search:
                        plan.action = "vector_search"
                    else:
                        plan.filters = {}
                        return plan

                if matched_doc and plan.action in ["vector_search", "hybrid_search"]:
                    plan.filters = dict(plan.filters)
                    if "document_name" not in plan.filters:
                        plan.filters["document_name"] = matched_doc
                    plan.top_k = max(plan.top_k, 8)
                return plan
            except Exception:
                pass  # Fallback to default first-pass search

        # 4. Default fallback:
        # If web search is explicitly enabled and no session documents exist, use web search
        if enable_web_search and not session_documents:
            return AcquisitionPlan(
                action="web_search",
                query=normalized_query,
                filters={},
                top_k=5,
                rerank=False,
                reason_code="web_search_no_documents",
                expected_information_gain="high",
            )

        fallback_query = normalized_query
        fallback_filters: dict[str, Any] = {}
        if session_documents:
            if matched_doc:
                fallback_query = f"{matched_doc} {normalized_query}"
                fallback_filters["document_name"] = matched_doc
            elif any(w in lower_q for w in ["what is this", "what does this", "about this", "summary", "overview", "this document", "this file", "convey", "tell us"]):
                fallback_query = f"{session_documents[0]} overview summary key details"

        return AcquisitionPlan(
            action="vector_search",
            query=fallback_query,
            filters=fallback_filters,
            top_k=8 if fallback_filters.get("document_name") else 5,
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
        session_documents: list[str] | None = None,
        plan_history: list[PlanHistoryEntry] | None = None,
        enable_web_search: bool = False,
    ) -> AcquisitionPlan:
        """Refine the acquisition plan when evidence is insufficient or conflicting."""
        if retrieval_iterations >= budgets.max_retrieval_iterations:
            return AcquisitionPlan(
                action="abstain" if prior_assessment.decision == "insufficient" else "no_acquisition_required",
                query=None,
                reason_code="max_iterations_reached",
                expected_information_gain="low",
            )

        lower_q = query.strip().lower()
        matched_doc = None
        if session_documents:
            for doc in session_documents:
                doc_base = doc.lower().rsplit(".", 1)[0]
                if doc.lower() in lower_q or (len(doc_base) >= 3 and doc_base in lower_q):
                    matched_doc = doc
                    break

        # Check memory of past failures
        last_action = None
        last_had_doc_filter = False
        has_tried_internal_search = False
        has_tried_web_search = False
        if plan_history:
            for entry in plan_history:
                p = entry.plan if hasattr(entry, "plan") else entry
                act = getattr(p, "action", None)
                if act in ["vector_search", "hybrid_search"]:
                    has_tried_internal_search = True
                elif act == "web_search":
                    has_tried_web_search = True
            last_entry = plan_history[-1]
            last_plan = last_entry.plan if hasattr(last_entry, "plan") else last_entry
            last_action = getattr(last_plan, "action", None)
            last_had_doc_filter = bool(getattr(last_plan, "filters", {}).get("document_name"))

        if self.llm_provider is not None:
            doc_context = f"Uploaded Session Documents: {', '.join(session_documents)}" if session_documents else ""
            
            history_lines = []
            if plan_history:
                for entry in plan_history:
                    p = entry.plan if hasattr(entry, "plan") else entry
                    v = getattr(entry, "verdict", None) or "insufficient"
                    rc = getattr(entry, "reason_code", None) or getattr(p, "reason_code", "")
                    missing = getattr(entry, "missing_aspects", []) or []
                    history_lines.append(
                        f"- Iteration {getattr(entry, 'iteration', len(history_lines)+1)}: "
                        f"action='{getattr(p, 'action', '')}', query='{getattr(p, 'query', '')}', "
                        f"filters={getattr(p, 'filters', {})} -> Verdict: {v} (reason: {rc}, missing: {missing})"
                    )
            history_context = "\nPrevious Acquisition Attempts & Verdicts:\n" + "\n".join(history_lines) if history_lines else ""

            web_guidance = (
                "Web Search is ENABLED. Since internal document retrieval did not yield sufficient evidence "
                f"(missing: {prior_assessment.missing_aspects}), "
                "you SHOULD switch action to 'web_search'. Formulate a clear, self-contained public search query (e.g. resolving references "
                "like 'this company' to the concrete entity from missing aspects or context)."
                if (enable_web_search and not has_tried_web_search)
                else f"Web Search Enabled: {enable_web_search}."
            )

            messages = [
                ChatMessage(role="system", content=CONTROLLER_SYSTEM_PROMPT),
                ChatMessage(
                    role="user",
                    content=(
                        f"Original Query: {query}\n"
                        f"{doc_context}\n"
                        f"Prior Assessment: {prior_assessment.model_dump_json()}\n"
                        f"{history_context}\n"
                        f"Current Retrieval Iterations: {retrieval_iterations}/{budgets.max_retrieval_iterations}\n"
                        "CRITICAL: The prior evidence was insufficient or conflicting. Examine the previous attempts above. "
                        "DO NOT execute an identical query or restrict to the same document filter that failed. "
                        f"{web_guidance} "
                        "If continuing with internal search, use 'hybrid_search'. If a document_name filter yielded insufficient content, broaden search across all session documents."
                    ),
                ),
            ]
            try:
                res = self.llm_provider.generate_structured(
                    messages=messages,
                    schema=AcquisitionPlan,
                    budget=CallBudget(max_tokens=1500, timeout_seconds=30.0),
                    role=LLMCallRole.PLANNER,
                )
                plan = res.data
                if plan.action == "web_search":
                    if not enable_web_search:
                        plan.action = "hybrid_search"
                    else:
                        plan.filters = {}
                        return plan

                # Only enforce document_name if it wasn't already tried and deemed insufficient
                if matched_doc and not last_had_doc_filter and plan.action in ["vector_search", "hybrid_search"]:
                    plan.filters = dict(plan.filters)
                    if "document_name" not in plan.filters:
                        plan.filters["document_name"] = matched_doc
                    plan.top_k = max(plan.top_k, 8)
                return plan
            except Exception:
                pass  # Fallback to heuristic refinement

        # Heuristic fallback escalation:
        # If Web Search is enabled and internal document search was tried and insufficient, escalate to web search
        if enable_web_search and has_tried_internal_search and not has_tried_web_search:
            web_q = formulate_web_query(query, prior_assessment.missing_aspects, session_documents)
            return AcquisitionPlan(
                action="web_search",
                query=web_q,
                filters={},
                top_k=5,
                rerank=False,
                reason_code="web_search_escalation_after_insufficient_documents",
                expected_information_gain="high",
            )

        intent = detect_query_intent(query)
        doc_prefix = f"{matched_doc or session_documents[0]} " if session_documents and not last_had_doc_filter else ""
        if intent == "summary":
            refined_query = f"{doc_prefix}document summary main findings key points"
        elif intent == "advantages":
            refined_query = "system strengths benefits advantages positive findings"
        elif intent == "limitations":
            refined_query = "limitations weaknesses risks problems"
        elif intent == "findings":
            refined_query = "main findings results conclusions"
        elif intent == "synthesis":
            refined_query = "common findings differences agreements disagreements"
        else:
            clean_aspects = [
                a for a in prior_assessment.missing_aspects
                if a.lower() not in STOPWORDS and len(a) > 2
            ]
            refined_query = query
            if clean_aspects:
                aspect = clean_aspects[0]
                refined_query = f"{query} {aspect}"

        # Escalate action from vector_search to hybrid_search
        action = "hybrid_search" if (last_action == "vector_search" or prior_assessment.decision == "conflicting") else "vector_search"

        # If previous search used document_name and was insufficient, drop it to search across session
        refine_filters: dict[str, Any] = {}
        if matched_doc and not last_had_doc_filter:
            refine_filters["document_name"] = matched_doc

        return AcquisitionPlan(
            action=action,
            query=refined_query,
            filters=refine_filters,
            top_k=8 if refine_filters.get("document_name") else 5,
            rerank=True,
            reason_code=f"refine_pass_{retrieval_iterations + 1}",
            expected_information_gain="medium",
        )
