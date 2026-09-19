from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from pydantic import BaseModel, Field
from domain.models import ExecutionBudgets


# ---------------------------------------------------------------------------
# Standard Error Envelope
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    code: str
    message: str
    run_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Health Schema
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str = "1.0.0"
    dependencies: dict[str, str] = Field(
        default_factory=dict,
        description="Dependency status summary (e.g. db, cache, llm, embeddings) without secrets.",
    )


# ---------------------------------------------------------------------------
# Session Schemas
# ---------------------------------------------------------------------------

class SessionCreateRequest(BaseModel):
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnswerResponse(BaseModel):
    answer_text: str
    citation_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    needs_follow_up: bool = False


class TurnResponse(BaseModel):
    turn_id: str
    run_id: str
    user_query: str
    answer: AnswerResponse | None = None
    status: str
    created_at: datetime


class SessionResponse(BaseModel):
    session_id: str
    memory_principal_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionDetailResponse(BaseModel):
    session_id: str
    memory_principal_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    turns: list[TurnResponse] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Run Schemas
# ---------------------------------------------------------------------------

class RunCreateRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User query text")
    budgets: ExecutionBudgets | None = None
    response_mode: str = "concise"
    enable_web_search: bool = False


class EvidenceItemResponse(BaseModel):
    evidence_id: str
    source_type: str
    source_id: str
    content: str
    retrieval_method: str
    retrieval_score: float | None = None


class RunResponse(BaseModel):
    run_id: str
    session_id: str
    status: str
    poll_url: str
    events_url: str
    answer: AnswerResponse | None = None
    evidence: list[EvidenceItemResponse] = Field(default_factory=list)
    evidence_assessment: dict[str, Any] | None = None
    budgets: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    failure: dict[str, Any] | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class RunEventResponse(BaseModel):
    sequence: int
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class RunEventsResponse(BaseModel):
    run_id: str
    events: list[RunEventResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Document Schemas
# ---------------------------------------------------------------------------

class DocumentResponse(BaseModel):
    document_id: str
    session_id: str | None = None
    name: str
    mime_type: str
    sha256: str
    status: str
    chunk_count: int = 0
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Memory Schemas
# ---------------------------------------------------------------------------

class MemoryCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Explicit memory content")
    kind: str = "user_preference"


class MemoryResponse(BaseModel):
    memory_id: str
    memory_principal_id: str
    kind: str
    content: str
    status: str
    created_at: datetime


class MemoryListResponse(BaseModel):
    memories: list[MemoryResponse] = Field(default_factory=list)


class GenericActionResponse(BaseModel):
    success: bool
    message: str
    id: str | None = None

