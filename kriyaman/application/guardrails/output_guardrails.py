import logging
import re
from typing import Literal

from application.guardrails.models import GuardrailDecision
from application.guardrails.pii import PIIMiddleware
from application.guardrails.regex_rules import CITATION_ID_PATTERN
from domain.models import Answer

logger = logging.getLogger(__name__)

HTML_SCRIPT_PATTERN = re.compile(r"<script[\s\S]*?>[\s\S]*?</script>", re.IGNORECASE)


class OutputGuardrails:
    """Post-generation validation and citation grounding verification."""

    def __init__(
        self,
        pii_mode: Literal["off", "detect", "mask", "reject"] = "mask",
        strict_citation_grounding: bool = True,
    ) -> None:
        self.pii_middleware = PIIMiddleware(mode=pii_mode)
        self.strict_citation_grounding = strict_citation_grounding

    def validate_answer(
        self,
        answer: Answer,
        valid_chunk_ids: set[str] | list[str] | None = None,
    ) -> tuple[bool, Answer, GuardrailDecision]:
        """Validates answer against schemas, citation IDs, and PII leakage.

        Returns:
            (allowed, sanitized_answer, decision)
        """
        valid_ids = set(valid_chunk_ids or [])
        text = answer.answer_text or ""

        # 1. Non-empty check
        if not text.strip():
            decision = GuardrailDecision(
                allowed=False,
                action="reject",
                category="empty_output",
                risk_score=1.0,
                reason_code="answer_text_is_empty",
            )
            return False, answer, decision

        # 2. Dangerous HTML/script stripping
        sanitized_text = HTML_SCRIPT_PATTERN.sub("", text)

        # 3. Citation grounding and validation
        verified_citations: list[str] = []
        hallucinated_citations: list[str] = []

        for cid in answer.citation_ids:
            # Check pattern format
            if not CITATION_ID_PATTERN.match(cid):
                hallucinated_citations.append(cid)
                continue

            # If we have valid chunk IDs from retrieved evidence, verify citation belongs to it
            if valid_ids and cid not in valid_ids:
                hallucinated_citations.append(cid)
            else:
                verified_citations.append(cid)

        if hallucinated_citations:
            logger.warning(
                "Hallucinated or invalid citations detected: %s (valid=%s)",
                hallucinated_citations,
                valid_ids,
            )
            if self.strict_citation_grounding and valid_ids and not verified_citations:
                # All citations hallucinated when evidence was present
                decision = GuardrailDecision(
                    allowed=False,
                    action="reject",
                    category="hallucinated_citations",
                    risk_score=0.9,
                    detected_entities=hallucinated_citations,
                    reason_code="citations_not_grounded_in_evidence",
                )
                return False, answer, decision

        # 4. PII check on answer
        pii_decision = self.pii_middleware.evaluate(sanitized_text)
        if not pii_decision.allowed:
            return False, answer, pii_decision

        final_text = pii_decision.sanitized_text or sanitized_text
        sanitized_answer = Answer(
            answer_text=final_text,
            citation_ids=verified_citations,
            confidence=answer.confidence,
            needs_follow_up=answer.needs_follow_up,
        )

        decision = GuardrailDecision(
            allowed=True,
            action="redact" if pii_decision.action == "redact" else "allow",
            category=pii_decision.category,
            risk_score=pii_decision.risk_score,
            detected_entities=pii_decision.detected_entities + hallucinated_citations,
            sanitized_text=final_text,
            reason_code="output_guardrails_passed",
        )
        return True, sanitized_answer, decision

