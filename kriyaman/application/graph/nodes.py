import re
import uuid
from typing import Any

from application.answer_service import AnswerService
from application.context_builder import ContextBuilder
from application.controller import AgentController
from application.evidence_judge import EvidenceJudge, STOPWORDS, detect_query_intent
from application.graph.policies import check_budgets_exceeded
from application.graph.state import GraphState
from application.guardrails.input_guardrails import InputGuardrails
from application.guardrails.output_guardrails import OutputGuardrails
from application.plan_validator import PlanValidator
from application.retrieval_agent import RetrievalAgent
from domain.errors import PolicyViolationError
from domain.models import (
    AcquisitionPlan,
    Answer,
    ExecutionBudgets,
    ExecutionEvent,
    UsageSnapshot,
)


class GraphNodes:
    """Encapsulates all LangGraph node functions with injected services."""

    def __init__(
        self,
        controller: AgentController,
        retrieval_agent: RetrievalAgent,
        evidence_judge: EvidenceJudge,
        context_builder: ContextBuilder | None = None,
        answer_service: AnswerService | None = None,
        plan_validator: PlanValidator | None = None,
        input_guardrails: InputGuardrails | None = None,
        output_guardrails: OutputGuardrails | None = None,
    ):
        self.controller = controller
        self.retrieval_agent = retrieval_agent
        self.evidence_judge = evidence_judge
        self.context_builder = context_builder or ContextBuilder()
        self.answer_service = answer_service
        self.plan_validator = plan_validator or PlanValidator()
        self.input_guardrails = input_guardrails or InputGuardrails()
        self.output_guardrails = output_guardrails or OutputGuardrails()

    def initialize_run(self, state: GraphState) -> dict[str, Any]:
        run_id = state.get("run_id") or str(uuid.uuid4())
        user_query = state.get("user_query", "").strip()
        normalized_query = re.sub(r"\s+", " ", user_query.strip())

        allowed, sanitized_query, decision = self.input_guardrails.validate_query(user_query)
        normalized_query = re.sub(r"\s+", " ", (sanitized_query if allowed else user_query).strip())

        events = list(state.get("execution_events", []))
        event = ExecutionEvent(
            run_id=run_id,
            sequence=len(events),
            event_type="run_initialized",
            payload={"normalized_query": normalized_query},
        )
        events.append(event)

        if not allowed:
            guardrail_event = ExecutionEvent(
                run_id=run_id,
                sequence=len(events),
                event_type="guardrail_rejected",
                payload={"category": decision.category, "reason_code": decision.reason_code},
            )
            events.append(guardrail_event)
            return {
                "run_id": run_id,
                "user_query": user_query,
                "normalized_query": normalized_query,
                "status": "abstention",
                "guardrail_rejected": True,
                "guardrail_reason_code": decision.reason_code,
                "retrieval_iterations": state.get("retrieval_iterations", 0),
                "tool_calls": state.get("tool_calls", 0),
                "plan_history": state.get("plan_history", []),
                "evidence": state.get("evidence", []),
                "memory_items": state.get("memory_items", []),
                "tool_results": state.get("tool_results", []),
                "budgets": state.get("budgets") or ExecutionBudgets(),
                "usage": state.get("usage") or UsageSnapshot(),
                "execution_events": events,
            }

        return {
            "run_id": run_id,
            "user_query": user_query,
            "normalized_query": normalized_query,
            "status": "running",
            "guardrail_rejected": False,
            "guardrail_reason_code": None,
            "retrieval_iterations": state.get("retrieval_iterations", 0),
            "tool_calls": state.get("tool_calls", 0),
            "plan_history": state.get("plan_history", []),
            "evidence": state.get("evidence", []),
            "memory_items": state.get("memory_items", []),
            "tool_results": state.get("tool_results", []),
            "budgets": state.get("budgets") or ExecutionBudgets(),
            "usage": state.get("usage") or UsageSnapshot(),
            "execution_events": [*state.get("execution_events", []), event],
            "execution_events": events,
        }

    def load_session_memory(self, state: GraphState) -> dict[str, Any]:
        event = ExecutionEvent(
            run_id=state["run_id"],
            sequence=len(state.get("execution_events", [])),
            event_type="memory_loaded",
            payload={"memory_count": len(state.get("memory_items", []))},
        )
        return {
            "execution_events": [*state.get("execution_events", []), event],
        }

    def controller_decide(self, state: GraphState) -> dict[str, Any]:
        if state.get("guardrail_rejected"):
            plan = AcquisitionPlan(
                action="abstain",
                reason_code=state.get("guardrail_reason_code") or "guardrail_rejected",
            )
            event = ExecutionEvent(
                run_id=state["run_id"],
                sequence=len(state.get("execution_events", [])),
                event_type="controller_plan_created",
                payload={"action": plan.action, "reason_code": plan.reason_code},
            )
            return {
                "controller_plan": plan,
                "plan_history": [*state.get("plan_history", []), plan],
                "execution_events": [*state.get("execution_events", []), event],
            }

        if check_budgets_exceeded(state):
            plan = AcquisitionPlan(
                action="abstain",
                reasoning="Execution budget exhausted before controller planning.",
                reason_code="budget_exhausted",
            )
            event = ExecutionEvent(
                run_id=state["run_id"],
                sequence=len(state.get("execution_events", [])),
                event_type="budget_exceeded_before_planning",
                payload={"action": "abstain"},
            )
            return {
                "controller_plan": plan,
                "plan_history": [*state.get("plan_history", []), plan],
                "execution_events": [*state.get("execution_events", []), event],
            }

        available_tools = []
        if self.retrieval_agent.tool_registry:
            available_tools = [t.name for t in self.retrieval_agent.tool_registry.describe_available()]

        plan = self.controller.decide(
            query=state["user_query"],
            normalized_query=state["normalized_query"],
            session_documents=state.get("session_documents"),
            session_history=[
                m.content
                for m in state.get("memory_items", [])
                if m.kind == "session_turn"
            ],
            memory_items=state.get("memory_items"),
            budgets=state["budgets"],
            usage=state["usage"],
            available_tools=available_tools,
        )

        val_result = self.plan_validator.validate(
            plan=plan,
            tool_registry=self.retrieval_agent.tool_registry,
            budgets=state.get("budgets"),
            usage=state.get("usage"),
        )
        final_plan = val_result.sanitized_plan

        events = list(state.get("execution_events", []))
        if not val_result.is_valid:
            val_event = ExecutionEvent(
                run_id=state["run_id"],
                sequence=len(events),
                event_type="plan_validation_failed",
                payload={
                    "errors": val_result.errors,
                    "action": final_plan.action,
                    "reason_code": final_plan.reason_code,
                },
            )
            events.append(val_event)

        event = ExecutionEvent(
            run_id=state["run_id"],
            sequence=len(events),
            event_type="controller_plan_created",
            payload={"action": final_plan.action, "reason_code": final_plan.reason_code},
        )
        events.append(event)

        return {
            "controller_plan": final_plan,
            "plan_history": [*state.get("plan_history", []), final_plan],
            "execution_events": events,
        }

    def acquisition_stage(self, state: GraphState) -> dict[str, Any]:
        plan = state["controller_plan"]
        event = ExecutionEvent(
            run_id=state["run_id"],
            sequence=len(state.get("execution_events", [])),
            event_type="acquisition_stage_routed",
            payload={"action": plan.action if plan else "none"},
        )
        return {
            "execution_events": [*state.get("execution_events", []), event],
        }

    def retrieval_agent_node(self, state: GraphState) -> dict[str, Any]:
        plan = state["controller_plan"]
        if not plan:
            return {}

        if check_budgets_exceeded(state):
            event = ExecutionEvent(
                run_id=state["run_id"],
                sequence=len(state.get("execution_events", [])),
                event_type="budget_exceeded_before_retrieval",
                payload={"action": plan.action},
            )
            return {
                "execution_events": [*state.get("execution_events", []), event],
            }

        iterations = state.get("retrieval_iterations", 0)
        tool_calls = state.get("tool_calls", 0)

        if plan.action in ["vector_search", "hybrid_search", "metadata_filter", "web_search", "memory_search"]:
            iterations += 1
        elif plan.action == "tool_call":
            tool_calls += 1

        new_evidence, new_tool_results = self.retrieval_agent.execute(
            plan=plan,
            session_id=state["session_id"],
            run_id=state["run_id"],
            memory_principal_id="anonymous",
            existing_evidence=state.get("evidence", []),
            is_tool_approved=False,
        )

        event = ExecutionEvent(
            run_id=state["run_id"],
            sequence=len(state.get("execution_events", [])),
            event_type="acquisition_executed",
            payload={
                "action": plan.action,
                "new_evidence_count": len(new_evidence),
                "new_tool_results": len(new_tool_results),
            },
        )

        return {
            "retrieval_iterations": iterations,
            "tool_calls": tool_calls,
            "evidence": [*state.get("evidence", []), *new_evidence],
            "tool_results": [*state.get("tool_results", []), *new_tool_results],
            "execution_events": [*state.get("execution_events", []), event],
        }

    def evidence_judge_node(self, state: GraphState) -> dict[str, Any]:
        assessment = self.evidence_judge.evaluate(
            query=state["normalized_query"],
            evidence=state.get("evidence", []),
            current_plan=state.get("controller_plan"),
            retrieval_iterations=state.get("retrieval_iterations", 0),
            max_iterations=state["budgets"].max_retrieval_iterations,
        )

        event = ExecutionEvent(
            run_id=state["run_id"],
            sequence=len(state.get("execution_events", [])),
            event_type="evidence_judged",
            payload={
                "decision": assessment.decision,
                "coverage_score": assessment.coverage_score,
                "confidence": assessment.confidence,
                "reason_code": assessment.reason_code,
            },
        )

        return {
            "evidence_assessment": assessment,
            "execution_events": [*state.get("execution_events", []), event],
        }

    def controller_refine_node(self, state: GraphState) -> dict[str, Any]:
        assessment = state.get("evidence_assessment")
        if not assessment:
            return {}

        plan = self.controller.refine(
            query=state["normalized_query"],
            prior_assessment=assessment,
            retrieval_iterations=state.get("retrieval_iterations", 0),
            budgets=state["budgets"],
            session_documents=state.get("session_documents"),
        )

        val_result = self.plan_validator.validate(
            plan=plan,
            tool_registry=self.retrieval_agent.tool_registry,
            budgets=state.get("budgets"),
            usage=state.get("usage"),
        )
        final_plan = val_result.sanitized_plan

        events = list(state.get("execution_events", []))
        if not val_result.is_valid:
            val_event = ExecutionEvent(
                run_id=state["run_id"],
                sequence=len(events),
                event_type="plan_validation_failed",
                payload={
                    "errors": val_result.errors,
                    "action": final_plan.action,
                    "reason_code": final_plan.reason_code,
                },
            )
            events.append(val_event)

        event = ExecutionEvent(
            run_id=state["run_id"],
            sequence=len(events),
            event_type="controller_plan_refined",
            payload={"action": final_plan.action, "reason_code": final_plan.reason_code},
        )
        events.append(event)

        return {
            "controller_plan": final_plan,
            "plan_history": [*state.get("plan_history", []), final_plan],
            "execution_events": events,
        }

    def context_builder_node(self, state: GraphState) -> dict[str, Any]:
        assessment = state.get("evidence_assessment")
        pkg = self.context_builder.build_context(
            query=state["normalized_query"],
            evidence=state.get("evidence", []),
            assessment=assessment,
            session_history=[m.content for m in state.get("memory_items", []) if m.kind == "session_turn"],
            memory_items=[m for m in state.get("memory_items", []) if m.kind != "session_turn"],
            tool_results=state.get("tool_results", []),
            max_tokens=state["budgets"].max_input_tokens,
        )

        event = ExecutionEvent(
            run_id=state["run_id"],
            sequence=len(state.get("execution_events", [])),
            event_type="context_constructed",
            payload={"total_tokens": pkg.total_tokens, "evidence_count": len(pkg.evidence_items)},
        )

        return {
            "context_package": pkg,
            "execution_events": [*state.get("execution_events", []), event],
        }

    def generate_answer_node(self, state: GraphState) -> dict[str, Any]:
        assessment = state.get("evidence_assessment")
        context_pkg = state.get("context_package")

        # 1. Strict Evidence-Before-Generation Gate Check
        if not assessment or assessment.decision not in ("sufficient", "conflicting"):
            decision_name = assessment.decision if assessment else "None"
            raise PolicyViolationError(
                f"Generation gate violation: Attempted generation with invalid assessment decision '{decision_name}'.",
                policy_name="strict_evidence_before_generation",
            )

        if not context_pkg:
            raise PolicyViolationError(
                "Generation gate violation: ContextPackage must be built before generate_answer.",
                policy_name="context_before_generation",
            )

        # 2. Check budgets before generation call
        if check_budgets_exceeded(state):
            answer = Answer(
                answer_text="Execution stopped: budget exceeded before answer generation.",
                citation_ids=[],
                confidence=0.0,
                needs_follow_up=False,
            )
            event = ExecutionEvent(
                run_id=state["run_id"],
                sequence=len(state.get("execution_events", [])),
                event_type="generation_budget_exceeded",
                payload={"reason": "Budget limit reached before generation"},
            )
            return {
                "answer": answer,
                "status": "abstention",
                "execution_events": [*state.get("execution_events", []), event],
            }

        # 3. Check LLM provider availability
        has_llm = self.answer_service and (
            getattr(self.answer_service, "llm_provider", None) or getattr(self.answer_service, "llm", None)
        )
        if not has_llm:
            answer = Answer(
                answer_text="Unable to generate answer: No generation LLM provider is configured.",
                citation_ids=[],
                confidence=0.0,
                needs_follow_up=False,
            )
            event = ExecutionEvent(
                run_id=state["run_id"],
                sequence=len(state.get("execution_events", [])),
                event_type="generation_abstained_no_llm",
                payload={"reason": "No generation LLM provider configured"},
            )
            return {
                "answer": answer,
                "status": "abstention",
                "execution_events": [*state.get("execution_events", []), event],
            }

        raw_answer = self.answer_service.generate(context_pkg, assessment)

        valid_ids = (
            {e.evidence_id for e in state.get("evidence", [])}
            | {e.chunk_id for e in state.get("evidence", []) if e.chunk_id}
            | {e.source_id for e in state.get("evidence", []) if e.source_id}
        )
        allowed, validated_answer, g_dec = self.output_guardrails.validate_answer(
            answer=raw_answer,
            valid_chunk_ids=valid_ids,
        )

        events = list(state.get("execution_events", []))
        if not allowed:
            val_event = ExecutionEvent(
                run_id=state["run_id"],
                sequence=len(events),
                event_type="output_guardrail_rejected",
                payload={"reason_code": g_dec.reason_code, "category": g_dec.category},
            )
            events.append(val_event)
            abstain_ans = Answer(
                answer_text=f"Output rejected by safety policy: {g_dec.reason_code}.",
                citation_ids=[],
                confidence=0.0,
            )
            return {
                "answer": abstain_ans,
                "status": "abstention",
                "execution_events": events,
            }

        answer = validated_answer

        event = ExecutionEvent(
            run_id=state["run_id"],
            sequence=len(events),
            event_type="answer_generated",
            payload={"citation_count": len(answer.citation_ids), "confidence": answer.confidence},
        )
        events.append(event)

        return {
            "answer": answer,
            "status": "answer",
            "execution_events": [*state.get("execution_events", []), event],
            "execution_events": events,
        }

    def persist_turn_node(self, state: GraphState) -> dict[str, Any]:
        event = ExecutionEvent(
            run_id=state["run_id"],
            sequence=len(state.get("execution_events", [])),
            event_type="run_persisted",
            payload={"final_status": state["status"]},
        )
        return {
            "execution_events": [*state.get("execution_events", []), event],
        }

    # Terminal state handlers
    def clarification_terminal(self, state: GraphState) -> dict[str, Any]:
        plan = state.get("controller_plan")
        text = "Could you please clarify your request?"
        reason_detail = getattr(plan, "reasoning", None) or getattr(plan, "reason_code", None)
        if plan and plan.query and plan.query.strip() and plan.query != state.get("normalized_query"):
            text = f"Could you please clarify: {plan.query.strip()}"
        elif reason_detail and str(reason_detail).strip():
            text = f"Could you please clarify: {str(reason_detail).strip()}"

        answer = Answer(
            answer_text=text,
            citation_ids=[],
            confidence=1.0,
            needs_follow_up=True,
        )
        event = ExecutionEvent(
            run_id=state["run_id"],
            sequence=len(state.get("execution_events", [])),
            event_type="clarification_terminal_reached",
            payload={"needs_follow_up": True},
        )
        return {
            "status": "clarification",
            "answer": answer,
            "execution_events": [*state.get("execution_events", []), event],
        }

    def abstention_terminal(self, state: GraphState) -> dict[str, Any]:
        if state.get("guardrail_rejected"):
            reason = state.get("guardrail_reason_code") or "guardrail_rejected"
            answer = Answer(
                answer_text=f"Request rejected by safety policy: {reason}.",
                citation_ids=[],
                confidence=0.0,
                needs_follow_up=False,
            )
            event = ExecutionEvent(
                run_id=state["run_id"],
                sequence=len(state.get("execution_events", [])),
                event_type="abstention_terminal_reached",
                payload={"reason_code": reason, "guardrail_rejected": True},
            )
            return {
                "status": "abstention",
                "answer": answer,
                "execution_events": [*state.get("execution_events", []), event],
            }

        assessment = state.get("evidence_assessment")
        missing: list[str] = assessment.missing_aspects if assessment else []
        reason_code = assessment.reason_code if assessment else ""
        query = state.get("normalized_query", "")
        intent = detect_query_intent(query) if query else "general"

        if not state.get("evidence") or reason_code in (
            "no_evidence_budget_exhausted",
            "no_relevant_evidence_retrieved",
            "empty_evidence_retrieve_again",
        ):
            answer_text = "No relevant passages were retrieved from the uploaded documents."
        elif intent == "advantages":
            answer_text = "Retrieved passages did not contain enough information about system advantages."
        elif intent == "limitations":
            answer_text = "Retrieved passages did not contain enough information about system limitations or risks."
        elif intent == "findings":
            answer_text = "Retrieved passages did not contain enough information about main findings or conclusions."
        elif intent in ("summary", "synthesis"):
            answer_text = "Retrieved passages did not contain enough information to provide an overview or synthesis."
        else:
            clean_missing = [m for m in missing if m.lower() not in STOPWORDS and len(m) > 2]
            if clean_missing:
                answer_text = (
                    f"I am unable to answer this request based on the available verified evidence. "
                    f"Missing information regarding: {', '.join(clean_missing)}."
                )
            else:
                answer_text = "I am unable to answer this request based on the available verified evidence."

        answer = Answer(
            answer_text=answer_text,
            citation_ids=[],
            confidence=0.0,
            needs_follow_up=False,
        )
        event = ExecutionEvent(
            run_id=state["run_id"],
            sequence=len(state.get("execution_events", [])),
            event_type="abstention_terminal_reached",
            payload={"missing_aspects": missing, "reason_code": reason_code},
        )
        return {
            "status": "abstention",
            "answer": answer,
            "execution_events": [*state.get("execution_events", []), event],
        }

    def conflicting_terminal(self, state: GraphState) -> dict[str, Any]:
        conflict_groups = []
        if state.get("evidence_assessment"):
            conflict_groups = state["evidence_assessment"].conflict_groups

        # Cite conflicting evidence items
        all_evidence = state.get("evidence", [])
        citation_ids = [
            e.evidence_id
            for e in all_evidence
            if any(e.evidence_id in grp for grp in conflict_groups)
        ]
        if not citation_ids and all_evidence:
            citation_ids = [e.evidence_id for e in all_evidence[:2]]

        answer = Answer(
            answer_text=(
                "Conflicting evidence was detected across available sources. "
                "The sources present contradictory information on key aspects of your question."
            ),
            citation_ids=citation_ids,
            confidence=0.3,
            needs_follow_up=True,
        )
        event = ExecutionEvent(
            run_id=state["run_id"],
            sequence=len(state.get("execution_events", [])),
            event_type="conflicting_terminal_reached",
            payload={"conflict_groups": conflict_groups, "citations": citation_ids},
        )
        return {
            "status": "conflicting",
            "answer": answer,
            "execution_events": [*state.get("execution_events", []), event],
        }

    def terminal_ready(self, state: GraphState) -> dict[str, Any]:
        return {"status": "answer"}
