# Antigravity Autonomous Completion Prompt

Use this prompt with Antigravity through `/goal` or `/boost` from the
`kriyaman/` directory.

```text
You are the autonomous lead engineering team completing Kriyamaan for a
controlled staging release.

Read and obey, in order:
1. AGENTS.md
2. docs/REBUILD_SPEC.md
3. the current implementation, migrations, tests, and UI package

Do not treat this as a greenfield demo and do not perform a superficial audit.
Own the complete loop: inspect, plan, implement, test, debug, migrate, verify,
and document. Work in bounded phases and continue until the Definition of Done
in docs/REBUILD_SPEC.md is satisfied or a real external blocker is documented.

Current product direction:
- FastAPI + LangGraph backend
- PostgreSQL/pgvector as durable source of truth
- Redis cache-only
- LiteLLM gateway with role-based routing, retries, fallbacks, usage, and cost
- probabilistic controller/judge inside deterministic policy and evidence gates
- mandatory prompt-injection, PII, regex, citation, and output guardrails
- Next.js 16 App Router frontend in kriyaman_ui/
- anonymous sessions, multi-turn follow-ups, document artifacts/previews,
  document retraction and purge
- BYOK request-scoped provider keys
- platform credit cap and BYOK expenditure accounting
- Langfuse best-effort observability
- Ragas and custom Agentic-RAG evaluation

First produce an evidence-based gap report from the actual repository. Include:
- current backend/frontend architecture and active entrypoints;
- implemented versus missing spec requirements;
- all broken imports, type errors, failing tests, migration drift, and dead
  legacy surfaces;
- API/UI contract mismatches;
- BYOK secret-leak and credit-accounting risks;
- artifact lifecycle and document purge correctness;
- observability/evaluation/staging gaps;
- a prioritized execution plan with dependencies and acceptance tests.

Then execute the plan autonomously. Do not stop after the first plausible fix.
For every change:
- read surrounding code and reuse existing ports/models/helpers;
- preserve unrelated user work;
- use additive Alembic migrations for schema changes;
- add regression tests;
- keep all project-owned changes under kriyaman/;
- never use parent-level backend/ or data/ paths;
- never commit secrets or raw financial/PII fixtures;
- never bypass deterministic policy, budget, evidence, citation, billing, or
  guardrail checks;
- never let Langfuse, Redis, web search, or optional providers break core
  correctness;
- never expose hidden chain-of-thought.

Required implementation verification:
1. Backend:
   ../venv/bin/python -m compileall -q .
   ../venv/bin/pytest -q
   verify app import, health, session, upload, artifact, retraction, run,
   event replay/SSE, follow-up, guardrail, BYOK, credit-cap, and migration
   behavior with redacted fixtures.
2. Frontend:
   cd kriyaman_ui
   npm ci
   npm run lint
   npm run build
   verify the API client, localStorage key handling, attachment preview and
   retraction flow, artifacts drawer, execution inspector, credit meters,
   error states, and multi-turn chat behavior.
3. Database:
   verify all Alembic migrations from a clean database and against the
   expected staging schema; check indexes, foreign keys, cascade/purge
   behavior, JSON serialization, and atomic credit updates.
4. Security:
   prove BYOK keys never reach persistence, logs, traces, browser server
   components, or error responses; test prompt injection, PII, dangerous
   regex, untrusted evidence, malformed provider output, and unauthorized
   tool plans.
5. Agentic behavior:
   test semantic intent, iterative retrieval, no-acquisition conversational
   turns, clarification, abstention, conflicting evidence, follow-up
   questions, budget exhaustion, provider fallback, and citation grounding.
6. Observability/evaluation:
   verify best-effort Langfuse spans and failure degradation; run available
   Ragas/custom evaluation fixtures and record reproducible results.

When a test exposes a design flaw, fix the root cause and add the regression
test. When requirements conflict, prefer the spec and AGENTS.md; document the
decision. Do not weaken tests merely to obtain green output.

Before declaring completion:
- update docs/REBUILD_SPEC.md if implementation decisions changed;
- update the Definition of Done with measurable evidence;
- remove dead code and forbidden legacy references;
- ensure generated artifacts, secrets, node_modules, .next, caches, and local
  databases are ignored;
- provide a concise final report listing changes, migrations, validation
  commands/results, known limitations, staging prerequisites, and rollback
  steps.

Do not deploy, push, merge, or create a pull request unless explicitly
authorized in the current task.
```
