import logging
from typing import Literal

from application.guardrails.models import GuardrailDecision
from application.guardrails.pii import PIIMiddleware
from application.guardrails.prompt_injection import PromptInjectionDetector
from application.guardrails.regex_rules import DANGEROUS_EXECUTION_PATTERNS

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 4000


class InputGuardrails:
    """Pre-execution validation and sanitization for incoming user requests."""

    def __init__(
        self,
        prompt_injection_mode: Literal["detect", "reject", "off"] = "reject",
        pii_mode: Literal["off", "detect", "mask", "reject"] = "mask",
        max_query_length: int = MAX_QUERY_LENGTH,
    ) -> None:
        self.injection_detector = PromptInjectionDetector(mode=prompt_injection_mode)
        self.pii_middleware = PIIMiddleware(mode=pii_mode)
        self.max_query_length = max_query_length

    def validate_query(self, query: str) -> tuple[bool, str, GuardrailDecision]:
        """Validates and sanitizes a query.

        Returns:
            (allowed, sanitized_query, decision)
        """
        stripped = query.strip() if query else ""

        # 1. Length validation
        if not stripped:
            decision = GuardrailDecision(
                allowed=False,
                action="reject",
                category="empty_input",
                risk_score=1.0,
                reason_code="query_is_empty",
            )
            return False, stripped, decision

        if len(stripped) > self.max_query_length:
            decision = GuardrailDecision(
                allowed=False,
                action="reject",
                category="length_violation",
                risk_score=1.0,
                reason_code="query_too_long",
            )
            return False, stripped, decision

        # 2. Dangerous Execution Patterns (system shell, SQL injection attempts)
        for pattern in DANGEROUS_EXECUTION_PATTERNS:
            if pattern.search(stripped):
                logger.warning("Dangerous pattern detected in query: %s", pattern.pattern[:30])
                decision = GuardrailDecision(
                    allowed=False,
                    action="reject",
                    category="dangerous_content",
                    risk_score=1.0,
                    reason_code="dangerous_content_detected",
                )
                return False, stripped, decision

        # 3. Prompt Injection Detection
        inj_decision = self.injection_detector.evaluate(stripped)
        if not inj_decision.allowed:
            return False, stripped, inj_decision

        # 4. PII Middleware
        pii_decision = self.pii_middleware.evaluate(stripped)
        if not pii_decision.allowed:
            return False, stripped, pii_decision

        sanitized_query = pii_decision.sanitized_text or stripped

        final_decision = GuardrailDecision(
            allowed=True,
            action="redact" if pii_decision.action == "redact" else "allow",
            category=pii_decision.category or inj_decision.category,
            risk_score=max(inj_decision.risk_score, pii_decision.risk_score),
            detected_entities=inj_decision.detected_entities + pii_decision.detected_entities,
            sanitized_text=sanitized_query,
            reason_code="input_guardrails_passed",
        )
        return True, sanitized_query, final_decision

