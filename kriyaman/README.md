# Kriyamaan (क्रियामाण)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-FF6F00.svg)](https://langchain-ai.github.io/langgraph/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_pgvector-336791.svg?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-Gateway-yellow.svg)](https://litellm.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Kriyamaan** is a production-hardened, staging-ready **Conversational Agentic RAG (Retrieval-Augmented Generation)** application built from first principles.

Engineered with **deterministic evidence gating**, **probabilistic planning inside a deterministic envelope**, **PostgreSQL/pgvector durability**, **fail-open caching**, **request-scoped BYOK isolation**, and an editorial-grade **Next.js 16 research interface**, Kriyamaan delivers verifiable, hallucination-resistant answers with complete document-level provenance.

---

## Architecture Overview

```mermaid
flowchart LR
    U[User] --> UI[Next.js 16 Web Client / API Client]
    UI --> API[FastAPI Application API]
    API --> G[LangGraph Runtime Engine]
    
    G --> C[Agent Controller]
    C -->|typed acquisition plan| R[Retrieval Agent]
    
    R --> V[VectorStore Port]
    V --> PG[(PostgreSQL + pgvector)]
    R --> W[WebSearch Port]
    R --> M[Memory Store Port]
    M --> PG
    R --> T[Tool Registry Port]
    
    G --> CA[Cache Port]
    CA -. fail-open .-> RD[(Redis Cache)]
    
    R --> J[Evidence / Sufficiency Judge]
    J -->|insufficient & budget remaining| C
    J -->|sufficient / clarify / abstain / conflict| CB[Context Builder]
    
    CB --> L[Generation LLM Port]
    L --> LGW[LiteLLM Gateway]
    LGW --> API
    
    G --> CP[(PostgreSQL Checkpoints)]
    G -. traces .-> LF[Langfuse Observability]
```

---

## Core Architectural Invariants

1. **Controller / Executor Separation**: The Agent Controller analyzes queries, classifies intent, and formulates typed acquisition plans. Execution engines (Vector store, Web search, Memory, and Tools) strictly execute requested actions without making hidden routing decisions.
2. **Strict Evidence Gate Before Generation**: The final generation LLM **never** runs before the **Evidence/Sufficiency Judge** makes an explicit terminal decision (`sufficient`, `clarification`, `abstention`, or `conflicting`).
3. **Probabilistic Planning in a Deterministic Envelope**: While LLMs assist in intent extraction and synthesis, deterministic validators enforce graph policies, monotonic iteration/latency/token/cost budgets, citation integrity, and safety guardrails.
4. **PostgreSQL as the Authoritative Source of Truth**: All documents, text chunks, vector embeddings, memories, sessions, turns, execution runs, events, credit ledgers, and LangGraph checkpoints are persisted durably in PostgreSQL via `pgvector`.
5. **Fail-Open Redis Cache**: Redis serves strictly as an acceleration layer. Any cache disconnect or failure gracefully falls back to PostgreSQL without interrupting application flow.
6. **Request-Scoped BYOK Isolation**: Bring-Your-Own-Key (BYOK) secrets are ephemeral and request-scoped—they are never persisted, logged, traced, or cached. Platform credit caps and quotas are enforced atomically and fail-closed.
7. **Conversational Multi-Turn Memory & Dynamic Ingestion**: Maintains bounded conversation context across turns for coreference resolution (*"compare that to the first clause"*). Users can dynamically upload files (PDF, DOCX, TXT, MD, HTML) mid-session; documents are immediately chunked, embedded, and cited with `[evidence_id]` attribution.

---

## Key Features

- **Multi-Turn Research Conversational Assistant**: Interactive chat supporting continuous query refinement, follow-up clarification, and coreference resolution.
- **On-The-Fly Document Ingestion**: Instant drag-and-drop parsing and chunking for PDF, Word (.docx), Markdown, Plain Text, and HTML with SHA-256 deduplication.
- **Hybrid Retrieval & Semantic Reranking**: Combines dense vector similarity (`all-MiniLM-L6-v2`) with keyword metadata matching and relevance reranking.
- **Iterative Bounded Retrieval**: Dynamically expands and refines searches when initial evidence is insufficient, bounded by strict iteration and cost caps.
- **Comprehensive Safety Guardrails**: Built-in PII detection/masking, prompt-injection defense, query length ceilings, and output sanitation.
- **Real-Time SSE Event Streaming**: Live event transport providing granular status updates (*Searching knowledge...*, *Checking evidence...*, *Preparing answer...*).
- **Execution Inspector & Telemetry**: Detailed telemetry drawer displaying token breakdown, latency metrics, cost estimations, and verified citation cards.
- **Offline Evaluation Suite**: Integrated benchmark runner calculating Context Precision, Context Recall, Faithfulness, and Answer Relevance.

---

## Repository Structure

```text
kriyaman/
├── app/                        # FastAPI application layer
│   ├── api/
│   │   ├── routes.py           # REST and SSE API endpoints
│   │   └── schemas.py          # Pydantic request/response schemas
│   ├── config.py               # Application settings and environment parsing
│   ├── dependencies.py         # Dependency injection graph (DB, Cache, LLM, Vector)
│   └── main.py                 # FastAPI application factory and lifespan
├── domain/                     # Pure domain layer (no external framework dependencies)
│   ├── models.py               # Core domain entities (Documents, Runs, Turns, Budgets)
│   ├── errors.py               # Domain error hierarchy
│   └── ports/                  # Abstract port interfaces
│       ├── llm.py              # LLMProvider port
│       ├── embeddings.py       # EmbeddingProvider port
│       ├── vector_store.py     # VectorStore port
│       ├── memory.py           # MemoryStore port
│       ├── web_search.py       # WebSearch port
│       ├── cache.py            # Cache port
│       └── observability.py    # Observability port
├── application/                # Application orchestration and business logic
│   ├── graph/                  # LangGraph workflow definition
│   │   ├── state.py            # Typed state schema
│   │   ├── builder.py          # StateGraph compilation
│   │   ├── nodes.py            # Workflow execution nodes
│   │   └── policies.py         # Routing rules and terminal edge decisions
│   ├── controller.py           # Query classification and acquisition planning
│   ├── retrieval_agent.py      # Multi-source retrieval orchestration
│   ├── evidence_judge.py       # Evidence quality, sufficiency, and conflict scoring
│   ├── context_builder.py      # Deterministic prompt and evidence assembly
│   ├── answer_service.py       # Final response generation with citation validation
│   ├── ingestion_service.py    # Document parsing, chunking, and vector ingestion
│   ├── plan_validator.py       # Deterministic acquisition plan validation
│   ├── run_service.py          # Execution management and SSE streaming
│   └── guardrails/             # PII masking, regex rules, and prompt injection defense
├── adapters/                   # Concrete implementations of domain ports
│   ├── llm/                    # Google Gemini and LiteLLM Gateway adapters
│   ├── embeddings/             # Sentence Transformers adapter
│   ├── vectorstores/           # PostgreSQL + pgvector adapter
│   ├── cache/                  # Redis fail-open and in-memory cache adapters
│   ├── web/                    # Google ADK / Tavily web search adapter
│   └── observability/          # Langfuse tracing and No-Op adapters
├── persistence/                # Database layer
│   ├── db.py                   # SQLAlchemy async engine and session factory
│   ├── models.py               # SQLAlchemy ORM models
│   ├── checkpoint.py           # Async Postgres LangGraph checkpointer
│   ├── repositories/           # Repository pattern data access layer
│   └── migrations/             # Alembic migration environment and versions
├── kriyaman_ui/                # Next.js 16 + React 19 Frontend
│   ├── src/
│   │   ├── app/                # App router pages and layouts
│   │   ├── components/         # Chat, Execution Drawer, Knowledge Library, Memory
│   │   └── lib/                # API client, SSE stream handler, state hooks
│   └── package.json
├── evaluation/                 # Offline evaluation and benchmark runners
│   ├── datasets/               # JSONL evaluation benchmark cases
│   ├── metrics.py              # Precision, Recall, Faithfulness metric calculations
│   └── runner.py               # Repeatable benchmark execution runner
├── tests/                      # Automated test suite (Unit & Integration)
├── docs/                       # Architectural specifications and prompt assets
├── alembic.ini                 # Alembic configuration
├── requirements.txt            # Python dependencies manifest
└── main.py                     # Root entrypoint
```

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (asyncpg), Alembic, Uvicorn
- **Orchestration**: LangGraph, LangChain Core
- **LLM Gateway**: LiteLLM (supporting Google Gemini, Groq, Anthropic, OpenAI)
- **Vector & Embeddings**: PostgreSQL 16 + `pgvector`, Sentence Transformers (`all-MiniLM-L6-v2`)
- **Cache**: Redis 7+ (asyncio, fail-open)
- **Frontend**: Next.js 16, React 19, Tailwind CSS, Lucide Icons, Framer Motion
- **Observability**: Langfuse Tracing
- **Testing & Quality**: Pytest, Pytest-Asyncio, Compileall, ESLint, TypeScript

---

## Quickstart Guide

### 1. Prerequisites

Ensure you have the following installed:
- **Python 3.11+**
- **Node.js 18+** (or **Bun**)
- **PostgreSQL 16+** with the `pgvector` extension enabled
- **Redis 7+** (optional, recommended for caching)

### 2. Environment Configuration

Copy `.env.example` to `.env` and fill in your database credentials and API keys:

```bash
cp .env.example .env
```

Key environment variables:
```dotenv
# Database (PostgreSQL + pgvector)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/kriyaman
DATABASE_URL_SYNC=postgresql+psycopg://postgres:postgres@localhost:5432/kriyaman

# Redis Cache
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true

# LLM Providers & Routing
GOOGLE_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
PLANNER_MODEL=groq/openai/gpt-oss-20b
JUDGE_MODEL=groq/openai/gpt-oss-20b
GENERATOR_MODEL=gemini/gemini-2.5-flash

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Web Search (Optional)
WEB_SEARCH_ENABLED=false
TAVILY_API_KEY=your_tavily_key_here
```

### 3. Setup Virtual Environment & Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Run Database Migrations

Apply the Alembic schema migrations to set up tables, indexes, and vector extensions:

```bash
alembic upgrade head
```

### 5. Start the Backend API

Run the FastAPI application with live reload:

```bash
python main.py
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The REST API and interactive OpenAPI documentation will be available at:
- **API Root**: `http://localhost:8000/api/v1`
- **Swagger Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/v1/health`

### 6. Start the Frontend UI

In a new terminal window:

```bash
cd kriyaman_ui
npm install   # or: bun install
npm run dev   # or: bun run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## API Reference

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/v1/health` | `GET` | Health check and dependency status (DB, Vector store, Cache). |
| `/api/v1/keys/test` | `POST` | Validates custom BYOK API keys against provider gateways. |
| `/api/v1/credits` | `GET` | Retrieves client platform credit balance and usage limits. |
| `/api/v1/sessions` | `POST` / `GET` | Create a new research session or list active sessions. |
| `/api/v1/sessions/{id}` | `GET` / `DELETE` | Retrieve session history or delete an existing session. |
| `/api/v1/sessions/{id}/documents` | `POST` / `GET` | Upload documents (PDF, DOCX, TXT, MD, HTML) or list ingested files. |
| `/api/v1/sessions/{id}/documents/{doc_id}` | `DELETE` | Remove a document and purge its vector embeddings. |
| `/api/v1/sessions/{id}/runs` | `POST` | Execute an agentic run with a user query and optional BYOK headers. |
| `/api/v1/sessions/{id}/runs/{run_id}` | `GET` | Retrieve the execution details and answer of a specific run. |
| `/api/v1/sessions/{id}/runs/{run_id}/events` | `GET` | Fetch all structured timeline events for a run. |
| `/api/v1/sessions/{id}/runs/{run_id}/events/stream` | `GET` | Server-Sent Events (SSE) stream for live agent execution telemetry. |
| `/api/v1/sessions/{id}/turns` | `GET` | List all historical conversation turns in a session. |
| `/api/v1/memories` | `POST` / `GET` | Create explicit long-term memory or list memories by principal. |
| `/api/v1/memories/{memory_id}` | `DELETE` | Delete a stored long-term memory entry. |

---

## Testing & Validation Suite

Run the full validation suite to ensure backend correctness, schema integrity, and frontend build readiness:

```bash
# 1. Bytecode compilation verification
python3 -m compileall -q .

# 2. Run backend test suite
pytest -q

# 3. Frontend linting and production build
cd kriyaman_ui
npm run lint
npm run build
```

### Running the Evaluation Suite

To run offline Ragas-style benchmark evaluations on test datasets:

```bash
python3 -m pytest tests/unit/test_evaluation_runner.py -v
```

---

## Security & BYOK Policy

- **No Key Storage**: Headers containing `x-gemini-api-key`, `x-groq-api-key`, or `x-openai-api-key` are treated as request-scoped secrets and injected only into runtime adapters. They are never written to disk, PostgreSQL, Redis, or trace logs.
- **Untrusted Input Ingestion**: All uploaded documents, text files, and external web search results are treated as untrusted data and strictly isolated from orchestration instructions.
- **Deterministic Guardrails**: Prompts are sanitized against prompt injection patterns, and sensitive PII entities are automatically masked before context assembly.

---

## License

This project is licensed under the [MIT License](LICENSE).
