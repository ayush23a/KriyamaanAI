from decimal import Decimal
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from domain.models import ExecutionBudgets

_BASE_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"

    # Database (PostgreSQL + pgvector)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kriyaman"
    database_url_sync: str = "postgresql+psycopg://postgres:postgres@localhost:5432/kriyaman"

    # Cache (Redis)
    redis_url: str = "redis://localhost:6379/0"
    cache_enabled: bool = True
    cache_default_ttl_seconds: int = 300

    # LLM & Model Routing (LiteLLM Gateway)
    llm_enabled: bool = True
    google_api_key: str = ""
    groq_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_model: str = "gemini/gemini-3.6-flash"
    llm_temperature: float = 0.0
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 1
    llm_retry_backoff: float = 1.0

    # Role-based models
    planner_model: str = "groq/openai/gpt-oss-20b"
    judge_model: str = "groq/openai/gpt-oss-20b"
    generator_model: str = "gemini/gemini-2.5-flash"
    planner_fallback_models: list[str] = Field(default_factory=lambda: ["groq/openai/gpt-oss-120b"])
    judge_fallback_models: list[str] = Field(default_factory=lambda: ["groq/openai/gpt-oss-120b"])
    generator_fallback_models: list[str] = Field(default_factory=lambda: ["groq/openai/gpt-oss-120b", "gemini/gemini-1.5-flash"])
    generator_model: str = "gemini/gemini-3.6-flash"
    planner_fallback_models: list[str] = Field(default_factory=lambda: ["groq/openai/gpt-oss-120b", "gemini/gemini-3.6-flash", "gemini/gemini-3.1-flash-lite"])
    judge_fallback_models: list[str] = Field(default_factory=lambda: ["groq/openai/gpt-oss-120b", "gemini/gemini-3.6-flash", "gemini/gemini-3.1-flash-lite"])
    generator_fallback_models: list[str] = Field(default_factory=lambda: ["groq/openai/gpt-oss-120b", "gemini/gemini-3.1-flash-lite"])

    # Guardrails
    pii_mode: str = "mask"  # "detect", "mask", "reject", "off"
    prompt_injection_mode: str = "reject"  # "warn", "reject", "off"
    max_query_length: int = 2000
    max_evidence_length: int = 20000
    guardrail_failure_behavior: str = "reject"
    trace_raw_prompts: bool = False

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Web Search
    web_search_enabled: bool = False
    tavily_api_key: str = ""

    # Execution Budgets Defaults
    max_retrieval_iterations: int = 3
    max_tool_calls: int = 3
    max_latency_ms: int = 30_000
    max_input_tokens: int = 12_000
    max_output_tokens: int = 2_000
    max_estimated_cost_usd: Decimal = Decimal("0.25")

    # Observability (Deferred to Phase 6)
    observability_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    def get_execution_budgets(self) -> ExecutionBudgets:
        return ExecutionBudgets(
            max_retrieval_iterations=self.max_retrieval_iterations,
            max_tool_calls=self.max_tool_calls,
            max_latency_ms=self.max_latency_ms,
            max_input_tokens=self.max_input_tokens,
            max_output_tokens=self.max_output_tokens,
            max_estimated_cost_usd=self.max_estimated_cost_usd,
        )

    @property
    def embedding_model_name(self) -> str:
        return self.embedding_model

    @property
    def vector_dim(self) -> int:
        return self.embedding_dimension

    @property
    def gemini_api_key(self) -> str:
        return self.google_api_key

    @property
    def gemini_model_name(self) -> str:
        return self.llm_model

    @property
    def temperature(self) -> float:
        return self.llm_temperature

    @property
    def request_timeout_seconds(self) -> float:
        return self.llm_timeout_seconds

    @property
    def redis_socket_timeout_seconds(self) -> float:
        return 2.0

    @property
    def chunk_size(self) -> int:
        return 500

    @property
    def chunk_overlap(self) -> int:
        return 50


settings = Settings()


