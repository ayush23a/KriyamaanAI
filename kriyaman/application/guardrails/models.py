from typing import Literal
from pydantic import BaseModel, Field


class GuardrailDecision(BaseModel):
    allowed: bool = True
    action: Literal["allow", "warn", "redact", "reject"] = "allow"
    category: str | None = None
    risk_score: float = 0.0
    detected_entities: list[str] = Field(default_factory=list)
    sanitized_text: str | None = None
    reason_code: str = "guardrail_passed"

