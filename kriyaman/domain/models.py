from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Generic, Literal, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ExecutionBudgets(BaseModel):
    max_retrieval_iterations: int = 3
    max_tool_calls: int = 3
    max_latency_ms: int = 30_000
    max_input_tokens: int = 12_000
    max_output_tokens: int = 2_000
    max_estimated_cost_usd: Decimal = Decimal("0.25")


class CallBudget(BaseModel):
    max_tokens: int = 2_000
    timeout_seconds: float = 30.0


class UsageSnapshot(BaseModel):
    retrieval_iterations: int = 0
    tool_calls: int = 0
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: Decimal = Decimal("0.0")


class AcquisitionPlan(BaseModel):
    action: Literal[
        "vector_search",
        "metadata_filter",
        "hybrid_search",
        "web_search",
        "memory_search",
        "tool_call",
        "refine_query",
        "clarify",
        "no_acquisition_required",
        "answer",
        "abstain",
    ]
    intent: Literal[
        "summary",
        "advantages",
        "limitations",
        "findings",
        "factual_lookup",
        "synthesis",
        "comparison",
        "memory",
        "web",
        "tool",
        "clarification",
        "unsupported",
        "other",
    ] = "factual_lookup"
    query: str | None = None
    query_variants: list[str] = Field(default_factory=list)
    source_preferences: list[Literal["document", "memory", "web", "tool"]] = Field(default_factory=list)
    filters: dict[str, str | int | bool] = Field(default_factory=dict)
    top_k: int = 5
    rerank: bool = True
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    reason_code: str
    reasoning: str | None = None
    expected_information_gain: Literal["low", "medium", "high"] = "medium"
    confidence: float | None = None


class EvidenceItem(BaseModel):
    evidence_id: str
    source_type: Literal["document", "web", "memory", "tool"]
    source_id: str
    title: str | None = None
    content: str
    uri: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    retrieval_method: str
    retrieval_score: float | None = None
    rerank_score: float | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceAssessment(BaseModel):
    decision: Literal["sufficient", "insufficient", "conflicting", "clarification", "abstain"]
    coverage_score: float = Field(ge=0.0, le=1.0)
    quality_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    missing_aspects: list[str] = Field(default_factory=list)
    conflict_groups: list[list[str]] = Field(default_factory=list)
    recommended_next_action: str | None = None
    reason_code: str


class MemoryPrincipal(BaseModel):
    id: str
    namespace_key: str
    kind: str = "anonymous"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryItem(BaseModel):
    id: str
    memory_principal_id: str
    kind: str = "explicit"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExplicitMemoryRequest(BaseModel):
    memory_principal_id: str
    kind: str = "explicit"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemorySearchRequest(BaseModel):
    memory_principal_id: str
    query: str
    top_k: int = 5


class Document(BaseModel):
    id: str
    session_id: str
    name: str
    mime_type: str
    sha256: str
    status: Literal["pending", "processed", "failed"] = "pending"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentChunk(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    content_hash: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorSearchRequest(BaseModel):
    query: str
    embedding: list[float] | None = None
    top_k: int = 5
    filters: dict[str, Any] = Field(default_factory=dict)


class WebSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class ToolContext(BaseModel):
    run_id: str
    session_id: str
    is_approved: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_name: str
    status: Literal["success", "error", "unapproved", "refused"]
    result: Any = None
    error: str | None = None
    requires_approval: bool = False


class ToolDescriptor(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    is_side_effect: bool = False


class ContextPackage(BaseModel):
    system_instructions: str
    normalized_query: str
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    session_history: list[str] = Field(default_factory=list)
    memory_items: list[MemoryItem] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    conflict_instructions: str | None = None
    total_tokens: int = 0


class Answer(BaseModel):
    answer_text: str
    citation_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    needs_follow_up: bool = False


class FailureInfo(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ExecutionEvent(BaseModel):
    run_id: str
    sequence: int
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ProviderResult(BaseModel, Generic[T]):
    data: T
    usage: UsageSnapshot | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

