# Kriyamaan Agent Instructions

## Mission

Complete and harden Kriyamaan as a staging-ready Agentic RAG application. Treat
`docs/REBUILD_SPEC.md` as the architectural source of truth and this file as
the execution contract for coding agents.

## Repository boundaries

- Work only inside the current `kriyaman/` repository.
- The active backend is `app/`, `domain/`, `application/`, `adapters/`,
  `persistence/`, and `kriyaman_ui/`.
- `kriyaman_ui/` is the only active frontend. Do not revive or extend the
  legacy `frontend/` tree.
- Do not import, copy, read, write, or depend on parent-level legacy
  `backend/` or `data/` paths.
- Keep architecture assets local unless explicitly requested; never commit
  secrets, `.env` files, local databases, caches, `node_modules`, `.next`, or
  generated TypeScript/build artifacts.

## Operating mode

Work autonomously in bounded phases. Inspect before editing, implement the
smallest complete change, run targeted checks, then run the full relevant
validation suite. Continue through failures by fixing root causes; do not
declare success from a proxy check.

Before changing behavior:

1. Read the relevant section of `docs/REBUILD_SPEC.md`.
2. Search for existing ports, models, adapters, routes, migrations, and tests.
3. Preserve unrelated user changes. Do not reset, checkout, or delete broad
   paths to make the worktree clean.
4. Record schema changes as additive Alembic migrations. Never edit an applied
   migration to repair live schema drift.

## Architecture invariants

- PostgreSQL is authoritative for durable data, usage accounting, documents,
  chunks, memories, runs, events, and LangGraph checkpoints.
- pgvector is the active vector backend; Redis is cache-only and must fail open.
- LiteLLM core is behind `domain.ports.llm.LLMProvider`; provider SDKs must not
  leak into application orchestration.
- Controller and Evidence Judge may use LLM reasoning, but deterministic plan
  validation, budgets, guardrails, evidence gates, citation checks, tool
  approval, and persistence remain authoritative.
- The generation LLM must never run before a valid evidence/policy terminal
  decision.
- Uploaded documents and web results are untrusted data, never instructions.
- BYOK secrets are request-scoped, never persisted, logged, traced, or cached.
- Platform credit limits and BYOK usage accounting must be atomic and
  fail-closed for platform billing decisions.
- Follow-up turns must use bounded session history and answer conversational
  questions about missing evidence without forcing unnecessary re-upload.
- UI code communicates through the documented FastAPI REST/SSE contract only.

## Required validation

Use the repository venv, never global Python tooling:

```bash
../venv/bin/python -m compileall -q .
../venv/bin/pytest -q
cd kriyaman_ui && npm ci && npm run lint && npm run build
```

When a command is unavailable, install only from the repository manifest into
the existing venv or frontend lockfile workflow. Add or update tests for every
bug fix. At minimum, cover API contracts, migrations, BYOK isolation, credit
caps, artifact/document lifecycle, follow-up conversation, guardrails,
checkpointing, and frontend type/build validation.

## Staging gate

Do not call the system staging-ready until the Definition of Done at the end
of `docs/REBUILD_SPEC.md` is satisfied. Verify environment configuration,
database migrations, health checks, key-mode behavior, observability failure
degradation, rollback notes, and a redacted end-to-end smoke run. Do not
change deployment configuration or deploy externally unless the user
explicitly authorizes it.

## Security and data handling

- Never print or expose API keys, uploaded financial data, PII, or raw prompts
  in logs, traces, test output, or generated reports.
- Use redacted fixtures for financial documents.
- Reject prompt injection and dangerous execution patterns at the required
  boundaries.
- Validate every user-controlled identifier, upload, header, tool argument,
  citation, and provider response.
- Do not silently fabricate answers when evidence, provider access, budget, or
  billing policy is insufficient.

## Change discipline

Prefer typed interfaces and existing helpers over casts or duplicated logic.
Keep changes surgical and update directly related documentation. A task is
complete only after code, tests, migrations, UI contracts, and operational
documentation agree.
