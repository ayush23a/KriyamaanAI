import logging
from typing import Literal

from application.guardrails.models import GuardrailDecision
from application.guardrails.regex_rules import (
    BANK_ACCOUNT_PATTERN,
    CREDIT_CARD_PATTERN,
    EMAIL_PATTERN,
    IBAN_PATTERN,
    IFSC_CODE_PATTERN,
    PHONE_PATTERN,
    ROUTING_NUMBER_PATTERN,
    SSN_PATTERN,
)

logger = logging.getLogger(__name__)


class PIIMiddleware:
    """Detects and redacts or rejects personally identifiable information."""

    def __init__(self, mode: Literal["off", "detect", "mask", "reject"] = "mask") -> None:
        self.mode = mode

    def evaluate(self, text: str) -> GuardrailDecision:
        if self.mode == "off" or not text:
            return GuardrailDecision(allowed=True, action="allow", sanitized_text=text)

        detected_entities: list[str] = []
        sanitized = text

        # 1. Credit Cards
        if CREDIT_CARD_PATTERN.search(sanitized):
            detected_entities.append("credit_card")
            sanitized = CREDIT_CARD_PATTERN.sub("[CREDIT_CARD_REDACTED]", sanitized)

        # 2. SSN
        if SSN_PATTERN.search(sanitized):
            detected_entities.append("ssn")
            sanitized = SSN_PATTERN.sub("[SSN_REDACTED]", sanitized)

        # 3. Emails
        if EMAIL_PATTERN.search(sanitized):
            detected_entities.append("email")
            sanitized = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", sanitized)

        # 4. Bank Account / Routing / IBAN / IFSC
        has_fin = (
            BANK_ACCOUNT_PATTERN.search(sanitized)
            or ROUTING_NUMBER_PATTERN.search(sanitized)
            or IBAN_PATTERN.search(sanitized)
            or IFSC_CODE_PATTERN.search(sanitized)
        )
        if has_fin:
            detected_entities.append("financial_identifier")
            sanitized = BANK_ACCOUNT_PATTERN.sub("[FINANCIAL_ID_REDACTED]", sanitized)
            sanitized = ROUTING_NUMBER_PATTERN.sub("[FINANCIAL_ID_REDACTED]", sanitized)
            sanitized = IBAN_PATTERN.sub("[FINANCIAL_ID_REDACTED]", sanitized)
            sanitized = IFSC_CODE_PATTERN.sub("[FINANCIAL_ID_REDACTED]", sanitized)

        # 5. Phone numbers
        if PHONE_PATTERN.search(sanitized):
            detected_entities.append("phone_number")
            sanitized = PHONE_PATTERN.sub("[PHONE_REDACTED]", sanitized)

        if not detected_entities:
            return GuardrailDecision(
                allowed=True,
                action="allow",
                sanitized_text=text,
                reason_code="pii_clean",
            )

        logger.info(
            "PII detected: entities=%s, mode=%s",
            detected_entities,
            self.mode,
        )

        if self.mode == "reject":
            return GuardrailDecision(
                allowed=False,
                action="reject",
                category="pii",
                risk_score=1.0,
                detected_entities=detected_entities,
                reason_code="pii_rejected",
            )
        elif self.mode == "mask":
            return GuardrailDecision(
                allowed=True,
                action="redact",
                category="pii",
                risk_score=0.5,
                detected_entities=detected_entities,
                sanitized_text=sanitized,
                reason_code="pii_redacted",
            )
        else:  # detect
            return GuardrailDecision(
                allowed=True,
                action="warn",
                category="pii",
                risk_score=0.5,
                detected_entities=detected_entities,
                sanitized_text=text,
                reason_code="pii_warned",
            )

