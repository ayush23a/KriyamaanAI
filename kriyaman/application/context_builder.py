from typing import Any
from domain.models import (
    ContextPackage,
    EvidenceAssessment,
    EvidenceItem,
    MemoryItem,
    ToolResult,
)

SYSTEM_CITATION_INSTRUCTIONS = """You are the Generation Engine for Kriyamaan Agentic RAG.
Your task is to answer the user query accurately, strictly adhering to the provided context.

Rules:
1. Answer ONLY based on the facts directly mentioned in the supplied Context and Evidence.
2. Do NOT extrapolate, speculate, or invent any information, sources, or citations.
3. For every substantive statement, cite the corresponding evidence ID in your citation_ids list (e.g. ['ev_1']).
4. If conflicting information is noted in the instructions, present both perspectives neutrally with their citations.
5. Provide a structured response with answer_text, citation_ids, confidence (0.0 to 1.0), and needs_follow_up (boolean).
6. If the user asks a follow-up about what is missing, why a prior answer was insufficient,
   or what they can provide, answer it using the session history and prior run results.
   Explain concrete next steps in plain language; do not ask the user to clarify the
   follow-up itself unless it is genuinely ambiguous.
7. Do NOT output private reasoning, chain-of-thought, or internal justifications."""


class ContextBuilder:
    """Deterministically formats the ContextPackage for LLM answer generation."""

    def __init__(self, chars_per_token: int = 4):
        self.chars_per_token = chars_per_token

    def build_context(
        self,
        query: str,
        evidence: list[EvidenceItem],
        assessment: EvidenceAssessment | None = None,
        session_history: list[str] | None = None,
        memory_items: list[MemoryItem] | None = None,
        tool_results: list[ToolResult] | None = None,
        max_tokens: int = 12_000,
    ) -> ContextPackage:
        max_chars = max_tokens * self.chars_per_token

        conflict_instructions = None
        if assessment and assessment.decision == "conflicting":
            conflict_instructions = (
                "ATTENTION: Contradictory evidence has been detected across sources. "
                "You must present the conflicting viewpoints explicitly and cite each supporting source."
            )

        # 1. Order evidence by rank / score while preserving source diversity
        sorted_evidence = sorted(
            evidence,
            key=lambda e: (e.rerank_score or e.retrieval_score or 0.0),
            reverse=True,
        )

        # 2. Token/character budget trimming
        # Estimate fixed overhead (system prompt, query, history, memory, tools)
        overhead_chars = len(SYSTEM_CITATION_INSTRUCTIONS) + len(query)
        if session_history:
            overhead_chars += sum(len(h) for h in session_history)
        if memory_items:
            overhead_chars += sum(len(m.content) for m in memory_items)
        if tool_results:
            overhead_chars += sum(len(t.output_payload) for t in tool_results)
        overhead_chars += 50

        remaining_chars = max(0, max_chars - overhead_chars)

        trimmed_evidence: list[EvidenceItem] = []
        current_chars = 0

        for item in sorted_evidence:
            item_chars = len(item.content) + len(item.evidence_id) + 20
            if current_chars + item_chars <= remaining_chars:
                trimmed_evidence.append(item)
                current_chars += item_chars
            elif not trimmed_evidence and remaining_chars >= item_chars // 2:
                # If budget is tight, keep at least the top evidence item
                trimmed_evidence.append(item)
                current_chars += item_chars
                break
            else:
                # Trimming reached budget
                break

        total_estimated_tokens = (overhead_chars + current_chars) // self.chars_per_token

        return ContextPackage(
            system_instructions=SYSTEM_CITATION_INSTRUCTIONS,
            normalized_query=query,
            evidence_items=trimmed_evidence,
            session_history=session_history or [],
            memory_items=memory_items or [],
            tool_results=tool_results or [],
            conflict_instructions=conflict_instructions,
            total_tokens=total_estimated_tokens,
        )
