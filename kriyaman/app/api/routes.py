import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import Settings, settings
from app.api.schemas import (
    AnswerResponse,
    ClientCreditResponse,
    DocumentListResponse,
    DocumentResponse,
    ErrorDetail,
    ErrorResponse,
    EvidenceItemResponse,
    GenericActionResponse,
    HealthResponse,
    MemoryCreateRequest,
    MemoryListResponse,
    MemoryResponse,
    ProviderKeyStatus,
    RunCreateRequest,
    RunEventResponse,
    RunEventsResponse,
    RunResponse,
    SessionCreateRequest,
    SessionDetailResponse,
    SessionResponse,
    TestKeysRequest,
    TestKeysResponse,
    TurnResponse,
)
from app.dependencies import (
    get_cache_adapter,
    get_db,
    get_embedding_provider,
    get_ingestion_service,
    get_llm_provider,
    get_run_service,
    get_settings,
    get_vector_store,
)
from adapters.llm.litellm_gateway import LiteLLMGatewayAdapter
from adapters.web.adk_search import WebSearchAdapter
from adapters.web.fallback import MockWebSearchAdapter
from application.ingestion_service import IngestionService
from application.run_service import RunExecutionService
from domain.errors import (
    BudgetExceededError,
    KriyamanError,
    PolicyViolationError,
    ProviderError,
    ResourceNotFoundError,
    ValidationError,
)
from persistence.repositories.chunk_repo import DocumentChunkRepository
from persistence.repositories.credit_repo import ClientCreditRepository
from persistence.repositories.document_repo import DocumentRepository
from persistence.repositories.memory_repo import MemoryRepository
from persistence.repositories.principal_repo import MemoryPrincipalRepository
from persistence.repositories.run_repo import RunEventRepository, RunRepository
from persistence.repositories.session_repo import SessionRepository
from persistence.repositories.turn_repo import ConversationTurnRepository

router = APIRouter(prefix="/api/v1")


# ---------------------------------------------------------------------------
# 1. Health Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness and dependency status without secrets",
)
async def get_health(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HealthResponse:
    dep_status: dict[str, str] = {}

    # Database
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        dep_status["database"] = "healthy"
    except Exception as e:
        dep_status["database"] = f"unhealthy: {type(e).__name__}"

    # Cache
    try:
        cache = get_cache_adapter()
        dep_status["cache"] = "healthy" if cache is not None else "degraded"
    except Exception as e:
        dep_status["cache"] = f"degraded: {type(e).__name__}"

    # Vector store & embeddings
    try:
        get_vector_store()
        dep_status["vector_store"] = "healthy"
    except Exception as e:
        dep_status["vector_store"] = f"unhealthy: {type(e).__name__}"

    # LLM
    llm = get_llm_provider()
    dep_status["llm"] = "healthy" if llm is not None else "mock/unconfigured"

    overall_status = "healthy"
    if "unhealthy" in dep_status.get("database", ""):
        overall_status = "unhealthy"
    elif "unhealthy" in dep_status.get("vector_store", "") or "degraded" in dep_status.get("cache", ""):
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        dependencies=dep_status,
    )


@router.post(
    "/health/test-keys",
    response_model=TestKeysResponse,
    summary="Test connectivity for Gemini, Groq, and Tavily API keys",
)
async def test_api_keys(
    request: TestKeysRequest,
) -> TestKeysResponse:
    import time
    import httpx
    import litellm

    response = TestKeysResponse()

    # 1. Test Gemini
    if request.gemini_api_key and request.gemini_api_key.strip():
        t0 = time.time()
        try:
            await litellm.acompletion(
                model="gemini/gemini-3.6-flash",
                messages=[{"role": "user", "content": "ping"}],
                api_key=request.gemini_api_key.strip(),
                max_tokens=1,
                timeout=10.0,
            )
            lat = int((time.time() - t0) * 1000)
            response.gemini = ProviderKeyStatus(
                valid=True,
                message="Connected to Gemini 3.6 Flash.",
                latency_ms=lat,
            )
        except Exception as e:
            lat = int((time.time() - t0) * 1000)
            err_msg = str(e)
            if "API_KEY_INVALID" in err_msg or "400" in err_msg or "403" in err_msg:
                clean_msg = "Invalid or expired Gemini API key."
            else:
                clean_msg = f"Gemini connection failed: {err_msg[:120]}"
            response.gemini = ProviderKeyStatus(
                valid=False,
                message=clean_msg,
                latency_ms=lat,
            )

    # 2. Test Groq Primary
    if request.groq_api_key and request.groq_api_key.strip():
        t0 = time.time()
        try:
            await litellm.acompletion(
                model="groq/qwen/qwen3.8-27b",
                messages=[{"role": "user", "content": "ping"}],
                api_key=request.groq_api_key.strip(),
                max_tokens=1,
                timeout=10.0,
            )
            lat = int((time.time() - t0) * 1000)
            response.groq = ProviderKeyStatus(
                valid=True,
                message="Connected to Groq (Qwen 3.8-27B).",
                latency_ms=lat,
            )
        except Exception as e:
            lat = int((time.time() - t0) * 1000)
            err_msg = str(e)
            if "401" in err_msg or "Invalid API Key" in err_msg:
                clean_msg = "Invalid Groq API key."
            elif "rate_limit" in err_msg.lower() or "429" in err_msg:
                clean_msg = "Groq key valid, but currently rate-limited (TPM limit reached)."
            else:
                clean_msg = f"Groq connection failed: {err_msg[:120]}"
            response.groq = ProviderKeyStatus(
                valid=False,
                message=clean_msg,
                latency_ms=lat,
            )

    # 3. Test Groq Secondary (if provided)
    if request.groq_api_key_secondary and request.groq_api_key_secondary.strip():
        t0 = time.time()
        try:
            await litellm.acompletion(
                model="groq/qwen/qwen3.8-27b",
                messages=[{"role": "user", "content": "ping"}],
                api_key=request.groq_api_key_secondary.strip(),
                max_tokens=1,
                timeout=10.0,
            )
            lat = int((time.time() - t0) * 1000)
            response.groq_secondary = ProviderKeyStatus(
                valid=True,
                message="Connected to secondary Groq key.",
                latency_ms=lat,
            )
        except Exception as e:
            lat = int((time.time() - t0) * 1000)
            err_msg = str(e)
            clean_msg = "Invalid secondary Groq key." if ("401" in err_msg or "Invalid" in err_msg) else f"Groq secondary failed: {err_msg[:120]}"
            response.groq_secondary = ProviderKeyStatus(
                valid=False,
                message=clean_msg,
                latency_ms=lat,
            )

    # 4. Test Tavily (if provided)
    if request.tavily_api_key and request.tavily_api_key.strip():
        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                tav_res = await client.post(
                    "https://api.tavily.com/search",
                    json={"query": "test", "max_results": 1, "api_key": request.tavily_api_key.strip()},
                )
                lat = int((time.time() - t0) * 1000)
                if tav_res.status_code == 200:
                    response.tavily = ProviderKeyStatus(
                        valid=True,
                        message="Connected to Tavily Web Search.",
                        latency_ms=lat,
                    )
                else:
                    response.tavily = ProviderKeyStatus(
                        valid=False,
                        message=f"Tavily returned HTTP {tav_res.status_code} (check API key).",
                        latency_ms=lat,
                    )
        except Exception as e:
            lat = int((time.time() - t0) * 1000)
            response.tavily = ProviderKeyStatus(
                valid=False,
                message=f"Tavily connection error: {str(e)[:120]}",
                latency_ms=lat,
            )

    return response


@router.get(
    "/client/credits",
    response_model=ClientCreditResponse,
    summary="Get client cumulative usage and remaining credit",
)
async def get_client_credits(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_client_id: Annotated[str | None, Header()] = None,
) -> ClientCreditResponse:
    client_id = x_client_id or "default_client"
    credit_repo = ClientCreditRepository(db)
    record = await credit_repo.get_or_create(client_id)
    remaining = max(0.0, round(record.credit_limit_usd - record.default_spent_usd, 4))
    is_capped = (
        (record.default_spent_usd >= record.credit_limit_usd)
        if settings.enforce_client_credit_cap
        else False
    )
    return ClientCreditResponse(
        client_id=record.client_id,
        key_mode=record.key_mode,
        default_spent_usd=round(record.default_spent_usd, 4),
        byok_spent_usd=round(record.byok_spent_usd, 4),
        credit_limit_usd=record.credit_limit_usd,
        remaining_credit_usd=remaining,
        is_capped=is_capped,
    )


# ---------------------------------------------------------------------------
# 2. Session Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an anonymous session",
)
async def create_session(
    request: SessionCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionResponse:
    principal_repo = MemoryPrincipalRepository(db)
    session_repo = SessionRepository(db)

    # Ensure anonymous principal exists or create one
    namespace_key = f"anon_{uuid.uuid4().hex[:12]}"
    principal = await principal_repo.get_or_create(namespace_key=namespace_key)

    new_session = await session_repo.create(
        memory_principal_id=principal.id,
        title=request.title,
        metadata=request.metadata,
    )
    await db.commit()

    return SessionResponse(
        session_id=new_session.id,
        memory_principal_id=new_session.memory_principal_id,
        title=new_session.title,
        created_at=new_session.created_at,
        updated_at=new_session.updated_at,
        metadata=new_session.metadata_json or {},
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetailResponse,
    summary="Session summary and recent turns",
)
async def get_session(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionDetailResponse:
    session_repo = SessionRepository(db)
    turn_repo = ConversationTurnRepository(db)

    session = await session_repo.get_by_id(session_id)
    if not session:
        raise ResourceNotFoundError(
            f"Session '{session_id}' not found.", resource_type="session", resource_id=session_id
        )

    turns = await turn_repo.list_recent_turns(session_id, limit=20)
    turn_responses = []
    for t in turns:
        ans_resp = None
        if t.answer_json and isinstance(t.answer_json, dict):
            ans_resp = AnswerResponse(
                answer_text=t.answer_json.get("answer_text", ""),
                citation_ids=t.answer_json.get("citation_ids", []),
                confidence=float(t.answer_json.get("confidence", 0.0)),
                needs_follow_up=bool(t.answer_json.get("needs_follow_up", False)),
            )
        turn_responses.append(
            TurnResponse(
                turn_id=t.id,
                run_id=t.run_id,
                user_query=t.user_query,
                answer=ans_resp,
                status=t.status,
                created_at=t.created_at,
            )
        )

    return SessionDetailResponse(
        session_id=session.id,
        memory_principal_id=session.memory_principal_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        turns=turn_responses,
        metadata=session.metadata_json or {},
    )


# ---------------------------------------------------------------------------
# 3. Run Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/sessions/{session_id}/runs",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a query run",
)
async def create_run(
    session_id: str,
    request: RunCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    run_service: Annotated[RunExecutionService, Depends(get_run_service)],
    x_client_id: Annotated[str | None, Header()] = None,
    x_key_mode: Annotated[str | None, Header()] = None,
    x_gemini_api_key: Annotated[str | None, Header()] = None,
    x_groq_api_key: Annotated[str | None, Header()] = None,
    x_groq_secondary_api_key: Annotated[str | None, Header()] = None,
    x_tavily_api_key: Annotated[str | None, Header()] = None,
) -> RunResponse:
    client_id = x_client_id or session_id
    credit_repo = ClientCreditRepository(db)
    is_byok = (x_key_mode or "").lower() == "byok"

    custom_llm = None
    custom_web = None

    if is_byok:
        gemini_k = (x_gemini_api_key or "").strip()
        groq_k = (x_groq_api_key or "").strip()
        groq_sec_k = (x_groq_secondary_api_key or "").strip()
        tavily_k = (x_tavily_api_key or "").strip()

        if gemini_k or groq_k:
            custom_llm = LiteLLMGatewayAdapter(
                google_api_key=gemini_k,
                groq_api_key=groq_k,
                groq_api_key_secondary=groq_sec_k,
                planner_model=settings.planner_model,
                judge_model=settings.judge_model,
                generator_model=settings.generator_model,
                planner_fallback_models=settings.planner_fallback_models,
                judge_fallback_models=settings.judge_fallback_models,
                generator_fallback_models=settings.generator_fallback_models,
                temperature=settings.llm_temperature,
                timeout_seconds=settings.llm_timeout_seconds,
                max_retries=settings.llm_max_retries,
                retry_backoff=settings.llm_retry_backoff,
            )
        if tavily_k or gemini_k:
            custom_web = WebSearchAdapter(
                google_api_key=gemini_k,
                tavily_api_key=tavily_k,
                model_name="gemini-3.6-flash",
                offline_fallback=MockWebSearchAdapter(),
            )
    else:
        # Default Mode: Enforce $5.00 limit if enabled
        if settings.enforce_client_credit_cap:
            is_allowed, remaining, spent = await credit_repo.check_budget(client_id)
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=(
                        f"Free platform credit limit of $5.00 USD reached (spent: ${spent:.4f}). "
                        "Please switch to BYOK (Bring Your Own Key) in Settings -> General & API to continue."
                    ),
                )

    result = await run_service.execute_run(
        db=db,
        session_id=session_id,
        query=request.query,
        budgets=request.budgets,
        enable_web_search=request.enable_web_search,
        llm_provider=custom_llm,
        web_search=custom_web,
    )

    # Record usage in credit repository
    run_usage = result.get("state", {}).get("usage")
    if run_usage:
        cost = float(getattr(run_usage, "estimated_cost_usd", 0.0) or 0.0)
        await credit_repo.record_usage(client_id, cost, is_byok=is_byok)
        await db.commit()

    run_id = result["run_id"]
    state = result["state"]

    answer_resp = None
    if state.get("answer"):
        ans = state["answer"]
        answer_resp = AnswerResponse(
            answer_text=ans.answer_text,
            citation_ids=ans.citation_ids,
            confidence=ans.confidence,
            needs_follow_up=ans.needs_follow_up,
        )

    evidence_items = [
        EvidenceItemResponse(
            evidence_id=e.evidence_id,
            source_type=e.source_type,
            source_id=e.source_id,
            content=e.content,
            retrieval_method=e.retrieval_method,
            retrieval_score=e.retrieval_score,
        )
        for e in state.get("evidence", [])
    ]

    judge_assessment = None
    if state.get("evidence_assessment"):
        ass = state["evidence_assessment"]
        judge_assessment = ass.model_dump() if hasattr(ass, "model_dump") else dict(ass)

    budgets_dict = None
    if state.get("budgets"):
        b = state["budgets"]
        budgets_dict = b.model_dump() if hasattr(b, "model_dump") else dict(b)

    usage_dict = None
    if state.get("usage"):
        u = state["usage"]
        usage_dict = u.model_dump() if hasattr(u, "model_dump") else dict(u)

    return RunResponse(
        run_id=run_id,
        session_id=session_id,
        status=result["status"],
        poll_url=f"/api/v1/runs/{run_id}",
        events_url=f"/api/v1/runs/{run_id}/events",
        answer=answer_resp,
        evidence=evidence_items,
        evidence_assessment=judge_assessment,
        budgets=budgets_dict,
        usage=usage_dict,
    )


@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
    summary="Run status, answer, citations, budgets, and metrics",
)
async def get_run(
    run_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RunResponse:
    run_repo = RunRepository(db)
    turn_repo = ConversationTurnRepository(db)

    run = await run_repo.get_by_id(run_id)
    if not run:
        raise ResourceNotFoundError(
            f"Run '{run_id}' not found.", resource_type="run", resource_id=run_id
        )

    answer_resp = None
    if run.status in ["answer", "completed", "clarification", "abstention"]:
        # Find turn associated with this run
        from sqlalchemy import select
        from persistence.models import ConversationTurnModel
        res = await db.execute(
            select(ConversationTurnModel).where(ConversationTurnModel.run_id == run_id)
        )
        turn = res.scalars().first()
        if turn and turn.answer_json:
            answer_resp = AnswerResponse(
                answer_text=turn.answer_json.get("answer_text", ""),
                citation_ids=turn.answer_json.get("citation_ids", []),
                confidence=float(turn.answer_json.get("confidence", 0.0)),
                needs_follow_up=bool(turn.answer_json.get("needs_follow_up", False)),
            )

    return RunResponse(
        run_id=run.id,
        session_id=run.session_id,
        status=run.status,
        poll_url=f"/api/v1/runs/{run.id}",
        events_url=f"/api/v1/runs/{run.id}/events",
        answer=answer_resp,
        budgets=run.budgets_json or {},
        usage=run.usage_json or {},
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


@router.get(
    "/runs/{run_id}/events",
    response_model=RunEventsResponse,
    summary="Structured event stream or replay",
)
async def get_run_events(
    run_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RunEventsResponse:
    event_repo = RunEventRepository(db)
    events = await event_repo.list_by_run(run_id)

    return RunEventsResponse(
        run_id=run_id,
        events=[
            RunEventResponse(
                sequence=e.sequence,
                event_type=e.event_type,
                payload=e.payload_json or {},
                timestamp=e.created_at,
            )
            for e in events
        ],
    )


# ---------------------------------------------------------------------------
# 4. Document Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/sessions/{session_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a supported document",
)
async def upload_document(
    session_id: str,
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    ingestion_service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> DocumentResponse:
    session_repo = SessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise ResourceNotFoundError(
            f"Session '{session_id}' not found.", resource_type="session", resource_id=session_id
        )

    content = await file.read()
    if not content:
        raise ValidationError("Uploaded file is empty.")

    filename = file.filename or "uploaded_document"
    res = await ingestion_service.ingest_document(
        session=db,
        session_id=session_id,
        filename=filename,
        content=content,
    )
    await db.commit()

    return DocumentResponse(
        document_id=res.document_id,
        session_id=session_id,
        name=res.name,
        mime_type=res.mime_type,
        sha256=res.sha256,
        status=res.status,
        chunk_count=res.chunks_count,
        created_at=session.created_at,
    )


@router.get(
    "/sessions/{session_id}/documents",
    response_model=DocumentListResponse,
    summary="List ingestion status for a session",
)
async def list_documents(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentListResponse:
    doc_repo = DocumentRepository(db)
    docs = await doc_repo.list_by_session(session_id)

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                document_id=d.id,
                session_id=d.session_id,
                name=d.name,
                mime_type=d.mime_type,
                sha256=d.sha256,
                status=d.status,
                created_at=d.created_at,
            )
            for d in docs
        ]
    )


@router.delete(
    "/documents/{document_id}",
    response_model=GenericActionResponse,
    summary="Delete document, chunks, and associated search data",
)
async def delete_document(
    document_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GenericActionResponse:
    doc_repo = DocumentRepository(db)
    chunk_repo = DocumentChunkRepository(db)

    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise ResourceNotFoundError(
            f"Document '{document_id}' not found.", resource_type="document", resource_id=document_id
        )

    await chunk_repo.delete_by_document(document_id)
    await doc_repo.delete(document_id)
    await db.commit()

    return GenericActionResponse(
        success=True,
        message=f"Document '{document_id}' and all associated chunks deleted successfully.",
        id=document_id,
    )


# ---------------------------------------------------------------------------
# 5. Memory Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/sessions/{session_id}/memories",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Explicitly save a long-term memory",
)
async def create_memory(
    session_id: str,
    request: MemoryCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MemoryResponse:
    session_repo = SessionRepository(db)
    memory_repo = MemoryRepository(db)

    session = await session_repo.get_by_id(session_id)
    if not session:
        raise ResourceNotFoundError(
            f"Session '{session_id}' not found.", resource_type="session", resource_id=session_id
        )

    # Embed memory content if embedding provider available
    embedding = None
    try:
        embedder = get_embedding_provider()
        if embedder:
            embedding = embedder.embed_query(request.content)
    except Exception:
        pass

    memory = await memory_repo.create_explicit(
        memory_principal_id=session.memory_principal_id,
        kind=request.kind,
        content=request.content,
        embedding=embedding,
    )
    await db.commit()

    return MemoryResponse(
        memory_id=memory.id,
        memory_principal_id=memory.memory_principal_id,
        kind=memory.kind,
        content=memory.content,
        status=memory.status,
        created_at=memory.created_at,
    )


@router.get(
    "/sessions/{session_id}/memories",
    response_model=MemoryListResponse,
    summary="List explicit memories for a session principal",
)
async def list_memories(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MemoryListResponse:
    session_repo = SessionRepository(db)
    memory_repo = MemoryRepository(db)

    session = await session_repo.get_by_id(session_id)
    if not session:
        raise ResourceNotFoundError(
            f"Session '{session_id}' not found.", resource_type="session", resource_id=session_id
        )

    memories = await memory_repo.list_by_principal(session.memory_principal_id)
    return MemoryListResponse(
        memories=[
            MemoryResponse(
                memory_id=m.id,
                memory_principal_id=m.memory_principal_id,
                kind=m.kind,
                content=m.content,
                status=m.status,
                created_at=m.created_at,
            )
            for m in memories
        ]
    )


@router.delete(
    "/memories/{memory_id}",
    response_model=GenericActionResponse,
    summary="Delete an explicit memory",
)
async def delete_memory(
    memory_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GenericActionResponse:
    memory_repo = MemoryRepository(db)

    memory = await memory_repo.get_by_id(memory_id)
    if not memory:
        raise ResourceNotFoundError(
            f"Memory '{memory_id}' not found.", resource_type="memory", resource_id=memory_id
        )

    await memory_repo.delete(memory_id)
    await db.commit()

    return GenericActionResponse(
        success=True,
        message=f"Memory '{memory_id}' deleted successfully.",
        id=memory_id,
    )
