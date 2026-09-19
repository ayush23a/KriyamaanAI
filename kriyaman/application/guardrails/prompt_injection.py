import logging
import re
from typing import Literal

from application.guardrails.models import GuardrailDecision
from application.guardrails.regex_rules import PROMPT_INJECTION_PATTERNS

logger = logging.getLogger(__name__)

DELIMITER_ATTACK_PATTERNS = [
    re.compile(r"(?i)<\s*\|\s*im_start\s*\|>"),
    re.compile(r"(?i)<\s*\|\s*im_end\s*\|>"),
    re.compile(r"(?i)\[\s*INST\s*\]"),
    re.compile(r"(?i)\[\s*/\s*INST\s*\]"),
    re.compile(r"(?i)<\s*s\s*>|<\s*/\s*s\s*>"),
]


class PromptInjectionDetector:
    """Detects and mitigates prompt injection and jailbreak attempts."""

    def __init__(self, mode: Literal["detect", "reject", "off"] = "reject") -> None:
        self.mode = mode

    def evaluate(self, text: str) -> GuardrailDecision:
        if self.mode == "off" or not text:
            return GuardrailDecision(allowed=True, action="allow", risk_score=0.0)

        detected_reasons: list[str] = []

        # 1. Check direct prompt injection patterns
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                detected_reasons.append(f"regex_match:{pattern.pattern[:30]}")

        # 2. Check token delimiter injection patterns
        for pattern in DELIMITER_ATTACK_PATTERNS:
            if pattern.search(text):
                detected_reasons.append("special_token_delimiter")

        if detected_reasons:
            logger.warning(
                "Prompt injection attempt detected: reasons=%s, mode=%s",
                detected_reasons,
                self.mode,
            )
            if self.mode == "reject":
                return GuardrailDecision(
                    allowed=False,
                    action="reject",
                    category="prompt_injection",
                    risk_score=1.0,
                    detected_entities=detected_reasons,
                    reason_code="prompt_injection_detected",
                )
            else:
                return GuardrailDecision(
                    allowed=True,
                    action="warn",
                    category="prompt_injection",
                    risk_score=1.0,
                    detected_entities=detected_reasons,
                    reason_code="prompt_injection_warning",
                )

        return GuardrailDecision(
            allowed=True,
            action="allow",
            risk_score=0.0,
            reason_code="prompt_injection_passed",
        )

