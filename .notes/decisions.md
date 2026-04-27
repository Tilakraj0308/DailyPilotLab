# Decisions Log — DailyPilotLab

> Why we chose X over Y. Prevents re-suggesting rejected approaches.

---

### psycopg2 over SQLAlchemy
**Decision**: Use raw `psycopg2` with `RealDictCursor` instead of an ORM.
**Why**: Direct SQL control, simpler pgvector integration, no ORM abstraction overhead. The app's queries (especially CTE-based semantic search and `execute_values` bulk ops) are easier to express in raw SQL.
**Trade-off**: No migration framework, no model-to-table mapping.

---

### Supabase Postgres over standalone Postgres
**Decision**: Use Supabase-hosted Postgres.
**Why**: Built-in pgvector support, server-side functions (`assign_and_return_matches`, `update_topic_recency_metrics`), managed infrastructure.
**Trade-off**: Vendor lock-in for DB functions.

---

### Structured Outputs over Free-text LLM Responses
**Decision**: All LLM calls use OpenAI's `responses.parse()` with Pydantic schemas.
**Why**: Guarantees type-safe, parseable responses. No regex parsing, no JSON extraction hacks.
**Trade-off**: Tied to OpenAI's structured output feature.

---

### Destructive Refinement (delete raw + insert refined)
**Decision**: Refinement deletes original raw ideas and replaces them with refined versions (new IDs).
**Why**: Keeps the `raw_idea` table clean — only one version of each idea exists. Avoids duplication.
**Trade-off**: Original wording is irrecoverably lost. Topic assignments on raw ideas are cascade-deleted.

---

### EMA Smoothing for Trait Confidence
**Decision**: Use Exponential Moving Average (0.9 × current + 0.1 × new) with clamped deltas.
**Why**: Prevents wild confidence swings from a single LLM extraction. Traits build confidence gradually through repeated evidence.
**Trade-off**: Slow to converge — a trait needs many re-evidencing cycles to reach high confidence.

---

### personal_state.json on Disk (not DB)
**Decision**: Store the user's personal profile as a flat JSON file instead of a DB table.
**Why**: Simple read/write, serves as direct LLM context (injected into prompts). Single-user system, no need for DB overhead.
**Trade-off**: Not scalable for multi-user. No version history.

---

### YAML for Prompt Templates (not hardcoded strings)
**Decision**: All LLM prompts live in `config/prompts/*.yaml`.
**Why**: Easy to iterate on prompts without touching code. Clean separation of concerns.
**Trade-off**: Extra file I/O on each LLM call (mitigated by OS file caching).

---

### Google-specific vs provider-neutral connector base
**Decision**: Rename the former generic `BaseConnector` to `GoogleOAuthConnector`; keep `BaseConnector` as an alias for Google connectors only. Add `NotionConnector` as a separate class with Notion OAuth/token semantics.
**Why**: The previous `BaseConnector` was entirely Google-coupled (URLs, env vars, consent, revoke). Pretending it was generic would force `if provider == "notion"` branches or silent wrong behavior.
**Trade-off**: Slightly more files; new providers either subclass Google (if ever justified) or implement their own connector class with the same public methods expected by the connector HTTP layer (`connectors/routes/`).

---

### DB connection pool + connector route split (2026-04-27)
**Decision**: Use `psycopg2.pool.ThreadedConnectionPool` in `db/dbConnection.py` (env `DB_POOL_MIN_CONN` / `DB_POOL_MAX_CONN`); call `close_connection_pool()` on app shutdown. Split monolithic `connectors/router.py` into `connectors/routes/*`; canonical connector list is `GET /connectors/` with `GET /connectors` → 307. Split LLM helpers out of `utils/helpers.py` into focused modules; add `utils/chat_facade.py` so `server.py` does not import `services/agent_chat_db` directly.
**Why**: Cuts connection churn under concurrency; reduces merge hotspots; enforces clearer boundaries without changing product behavior.
**Trade-off**: Slightly more files; clients should follow redirects for `/connectors` (or call `/connectors/`).

---

### Two-Phase Topic Assignment (Vector + LLM)
**Decision**: Phase 1 uses pgvector similarity (fast, cheap), Phase 2 uses LLM (smart, expensive).
**Why**: Handles easy matches at DB speed, falls back to LLM only for ambiguous cases.
**Trade-off**: Two different systems can produce inconsistent groupings.

---

### No Authentication / No Multi-tenancy
**Decision**: No auth layer. Single-user personal tool.
**Why**: Simplicity. This is a personal productivity tool, not a SaaS product.
**Trade-off**: Cannot be deployed as a shared service without significant rework.
