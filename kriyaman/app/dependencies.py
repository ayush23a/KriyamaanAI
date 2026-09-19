from collections.abc import AsyncGenerator
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from adapters.cache.memory import InMemoryCacheAdapter
from adapters.cache.redis import RedisCacheAdapter
from adapters.embeddings.sentence_transformers import SentenceTransformerEmbeddingAdapter
from adapters.llm.google import GoogleGeminiAdapter
from adapters.reranking.baseline import DeterministicBaselineReranker
from adapters.vectorstores.pgvector import PgVectorStore
from adapters.web.fallback import MockWebSearchAdapter
from app.config import settings
from application.cache_service import CacheService
from application.chunker import TextChunker
from application.ingestion_service import IngestionService
from application.run_service import RunExecutionService
from domain.ports.cache import CachePort
from domain.ports.embeddings import EmbeddingProvider
from domain.ports.llm import LLMProvider
from domain.ports.reranker import Reranker
from domain.ports.vector_store import VectorStore
from domain.ports.web_search import WebSearchProvider
from persistence.db import get_async_session, get_sync_session_factory


# ---------------------------------------------------------------------------
# Database Session Dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_session():
        yield session


# ---------------------------------------------------------------------------
# Singletons / Component Providers
# ---------------------------------------------------------------------------

@lru_cache
def get_cache_adapter() -> CachePort:
    try:
        return RedisCacheAdapter(
            redis_url=settings.redis_url,
            socket_timeout=settings.redis_socket_timeout_seconds,
        )
    except Exception:
        return InMemoryCacheAdapter()


@lru_cache
def get_cache_service() -> CacheService:
    return CacheService(cache_adapter=get_cache_adapter())


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return SentenceTransformerEmbeddingAdapter(
        model_name=settings.embedding_model_name,
        dimension=settings.vector_dim,
    )


@lru_cache
def get_vector_store() -> VectorStore:
    return PgVectorStore(
        session_factory=get_sync_session_factory(),
        embedding_provider=get_embedding_provider(),
    )


from adapters.llm.litellm_gateway import LiteLLMGatewayAdapter


@lru_cache
def get_llm_provider() -> LLMProvider | None:
    if not settings.llm_enabled:
        return None
    if settings.google_api_key or settings.groq_api_key:
        return LiteLLMGatewayAdapter(
            google_api_key=settings.google_api_key,
            groq_api_key=settings.groq_api_key,
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
    return None


@lru_cache
def get_reranker() -> Reranker:
    return DeterministicBaselineReranker()


@lru_cache
def get_web_search_provider() -> WebSearchProvider:
    return MockWebSearchAdapter()


def get_ingestion_service() -> IngestionService:
    return IngestionService(
        embedding_provider=get_embedding_provider(),
        chunker=TextChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        ),
        cache_port=get_cache_adapter(),
    )


def get_run_service() -> RunExecutionService:
    return RunExecutionService(
        vector_store=get_vector_store(),
        llm_provider=get_llm_provider(),
        reranker=get_reranker(),
        web_search=get_web_search_provider(),
        cache_port=get_cache_adapter(),
    )

