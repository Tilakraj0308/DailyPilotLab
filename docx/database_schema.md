# DailyPilotLab — Database Schema Reference

> **Living document** — update this file whenever a migration adds, modifies, or drops a table.
>
> Last updated: **2026-09-05** · Migration head: `20260614_simplify_connectors_schema.sql`

---

## Table Map

| Table | Domain | Purpose |
|-------|--------|---------|
| `users` | Identity | User profiles, auth mapping, onboarding state |
| `raw_idea` | Memory | Atomic captured thoughts with vector embeddings |
| `topic` | Memory | Clustered themes with activity/recency metrics |
| `idea_topics` | Memory | M:N junction linking ideas ↔ topics |
| `trait` | Memory | AI-inferred user personality traits with confidence scores |
| `chat_messages` | Chat | Continuous multi-turn conversation history |
| `tasks` | Productivity | User to-do items with status, priority, and due dates |
| `user_connectors` | Integrations | Per-user provider connections, tokens, permissions, resources |
| `oauth_state_sessions` | Integrations | Ephemeral PKCE state for OAuth redirect flows |
| `connector_tool_history` | Integrations | Append-only audit log of external tool executions |
| `token_usage_traces` | Analytics | Request-level token consumption metadata and aggregate cost |
| `token_usage_timeline` | Analytics | Step-by-step granular request timeline events and token breakdown |

---

## Detailed Table Reference

### `users`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `BIGINT` (PK) | Auto-generated identity |
| `auth_id` | `TEXT UNIQUE NOT NULL` | Supabase / Google OAuth UID — used as tenant FK everywhere |
| `email` | `TEXT UNIQUE NOT NULL` | |
| `display_name` | `TEXT` | |
| `avatar_url` | `TEXT` | |
| `personal_state` | `JSONB` | Onboarding questionnaire data (name, DOB, occupation, etc.) |
| `onboarding_completed` | `BOOLEAN` | Gates first-login questionnaire |
| `created_at` | `TIMESTAMPTZ` | |

**Written by**: `auth_service.py`, `user_service.py`, `onboarding_service.py`
**Read by**: Auth middleware, onboarding checks, system prompt builder

---

### `raw_idea`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `BIGINT` (PK) | |
| `user_id` | `TEXT` (FK → `users.auth_id`) | Tenant isolation |
| `content` | `TEXT` | The captured thought/note |
| `embeddings` | `vector(1536)` | OpenAI `text-embedding-3-small` |
| `raw` | `BOOLEAN` | Legacy flag |
| `status` | `VARCHAR(30)` | `active`, `archived`, etc. |
| `created_at` | `TIMESTAMPTZ` | |

**Written by**: `ideas_service.py` (manual entry + background memory extraction from chat)
**Read by**: `ideas_service.search_topics_and_ideas()` for RAG, `assign_and_return_matches()` stored proc
**Background job**: Unlinked ideas are auto-matched to topics via vector cosine similarity

---

### `topic`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `BIGINT` (PK) | |
| `user_id` | `TEXT` (FK → `users.auth_id`) | |
| `title` | `TEXT NOT NULL` | LLM-generated |
| `summary` | `TEXT NOT NULL` | LLM-generated |
| `summary_embedding` | `vector(1536)` | Embedding of the summary |
| `activity_7d` | `SMALLINT` | Ideas linked in last 7 days |
| `activity_30d` | `SMALLINT` | Ideas linked in last 30 days |
| `lifetime_size` | `INTEGER` | Total ideas ever linked |
| `recency_strength` | `REAL` | `(activity_7d × 2) + (activity_30d − activity_7d)` |
| `dominance` | `REAL` | `(lifetime_size × 0.3) + (activity_30d × 0.7)` |
| `is_archived` | `BOOLEAN` | |
| `updated_at` | `TIMESTAMP` | Auto-updated by trigger |

**Written by**: `topics_service.py`
**Metrics updated by**: Stored function `update_topic_recency_metrics(p_user_id)`
**Trigger**: `update_topic_updated_at` keeps `updated_at` current

---

### `idea_topics` (Junction)

| Column | Type | Notes |
|--------|------|-------|
| `idea_id` | `BIGINT` (FK → `raw_idea.id`, CASCADE) | |
| `topic_id` | `BIGINT` (FK → `topic.id`, CASCADE) | |

PK: `(idea_id, topic_id)`

**Written by**: Stored function `assign_and_return_matches(dist_threshold, p_user_id)`, `topics_service.append_idea_ids()`
**Cascade**: Deleting an idea or topic auto-removes junction rows

---

### `trait`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `BIGINT` (PK) | |
| `user_id` | `TEXT` (FK → `users.auth_id`) | |
| `trait_text` | `TEXT NOT NULL` | e.g. "Prefers morning focus time" |
| `trait_type` | `trait_category` enum | `interest`, `goal`, `skill`, `routine`, `workstyle`, `preference`, `avoidance`, `value`, `constraint` |
| `confidence` | `REAL [0.0 – 1.0]` | EMA-smoothed confidence score |
| `embedding` | `vector(1536)` | HNSW-indexed for fast ANN lookups |
| `updated_at` | `TIMESTAMPTZ` | Auto-updated by trigger |

**Written by**: `trait_service.process_and_upsert_traits()` — embeds, deduplicates, applies EMA smoothing
**Read by**: System prompt builder (injects top traits into agent personality)
**Index**: `idx_trait_embedding` (HNSW, cosine)

---

### `chat_messages`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `UUID` (PK) | |
| `user_id` | `TEXT NOT NULL` (FK → `users.auth_id`) | |
| `role` | `TEXT` | `user`, `assistant`, `tool`, `system` |
| `content` | `TEXT NOT NULL` | Message payload |
| `tool_calls` | `JSONB` | OpenAI tool call definitions (assistant role) |
| `tool_call_id` | `TEXT` | References specific tool invocation (tool role) |
| `processed_for_ideas` | `BOOLEAN` | `false` → pending memory extraction |
| `created_at` | `TIMESTAMPTZ` | |

**Written by**: `chat_db.save_message()`
**Read by**: `chat_db.load_history()` for frontend display, `chat_db.fetch_unprocessed_messages()` for memory pipeline
**Memory pipeline**: Background workers query `processed_for_ideas = false`, extract ideas/traits, then call `mark_messages_processed()`

---

### `tasks`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `UUID` (PK) | `gen_random_uuid()` |
| `user_id` | `TEXT` (FK → `users.auth_id`, CASCADE) | Tenant isolation |
| `title` | `TEXT NOT NULL` | Short task name |
| `description` | `TEXT` | Optional notes |
| `status` | `task_status` enum | `todo`, `in_progress`, `done`, `cancelled` (default: `todo`) |
| `priority` | `task_priority` enum | `low`, `medium`, `high`, `urgent` (default: `medium`) |
| `due_date` | `TIMESTAMPTZ` | Nullable — no due date means open-ended |
| `completed_at` | `TIMESTAMPTZ` | Auto-set when `status` → `done`, cleared otherwise |
| `created_at` | `TIMESTAMPTZ` | `now()` default |
| `updated_at` | `TIMESTAMPTZ` | Auto-updated by `moddatetime` trigger |

**Written by**: `tasks/db.py` (via `tasks/service.py`)
**Read by**: `tasks/router.py` (REST API for UI), `tasks/tools.py` (LLM agent tools)
**RLS**: Row Level Security enabled — users can only access their own rows
**Index**: `idx_tasks_user_id` on `user_id`

---

### `user_connectors`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `BIGSERIAL` (PK) | |
| `user_id` | `TEXT` (FK → `users.auth_id`) | |
| `provider_key` | `TEXT` | `google_calendar`, `google_tasks`, `gmail` |
| `status` | `connector_status` enum | `disconnected`, `connecting`, `connected`, `error`, `reauth_required` |
| `scopes` | `TEXT[]` | Granted OAuth scopes |
| `external_account_id` | `TEXT` | Provider's account ID |
| `provider_email` | `TEXT` | |
| `access_token` | `BYTEA` | Fernet-encrypted |
| `refresh_token` | `BYTEA` | Fernet-encrypted |
| `token_expires_at` | `TIMESTAMPTZ` | |
| `metadata` | `JSONB` | Permissions, selected resources (e.g. task list ID) |
| `connected_at` / `disconnected_at` | `TIMESTAMPTZ` | |
| `updated_at` | `TIMESTAMPTZ` | Auto-updated by trigger |

**Unique constraint**: `(user_id, provider_key)`
**Written by**: `connectors/db.py` (OAuth flow, token refresh, permission updates)
**Read by**: `token_manager` (decrypt tokens for API calls), `connectors/db.list_connectors_status()`
**Trigger**: `update_user_connectors_updated_at`

> **Schema note**: This table consolidates the former `connector_providers`, `user_connector_tokens`, `user_connector_resources`, and `connector_tool_permissions` tables (dropped in migration `20260614`).

---

### `oauth_state_sessions`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `BIGSERIAL` (PK) | |
| `state` | `TEXT UNIQUE NOT NULL` | Random state string for CSRF protection |
| `user_id` | `TEXT` (FK → `users.auth_id`) | |
| `provider_key` | `TEXT` | |
| `code_verifier` | `TEXT NOT NULL` | PKCE verifier |
| `oauth_redirect_uri` | `TEXT NOT NULL` | |
| `return_to` | `TEXT` | Deep-link to resume after OAuth |
| `expires_at` | `TIMESTAMPTZ NOT NULL` | Short TTL |

**Written by**: `connectors/oauth_common.py` when user initiates provider connection
**Consumed by**: `connectors/db.consume_oauth_state()` on callback — row is deleted after use
**Cleanup**: `cleanup_expired_oauth_states()` purges rows past `expires_at`

---

### `connector_tool_history`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `UUID` (PK) | |
| `user_id` | `TEXT` (FK → `users.auth_id`) | |
| `provider_key` | `TEXT` | |
| `tool_name` | `TEXT` | e.g. `create_calendar_event` |
| `crud_type` | `TEXT` | `create`, `read`, `update`, `delete` |
| `params` | `JSONB` | Input parameters |
| `result_summary` | `JSONB` | Outcome summary |
| `status` | `TEXT` | `success` or `error` |
| `error_message` | `TEXT` | |
| `triggered_by` | `TEXT` | `user` or `system` |
| `created_at` | `TIMESTAMPTZ` | |

**Written by**: `connectors/history.log_tool_call()`
**Read by**: `connectors/history.get_recent_history()` → powers Activity Feed UI
**Security**: Row Level Security — users can only SELECT their own rows (`auth.uid() = user_id`)

---

## Stored Functions

| Function | Purpose |
|----------|---------|
| `assign_and_return_matches(dist_threshold, p_user_id)` | Auto-links unlinked ideas to topics within cosine distance threshold |
| `update_topic_recency_metrics(p_user_id)` | Recomputes `activity_7d`, `activity_30d`, `recency_strength`, `dominance` for all user topics |

## Custom Enums

| Enum | Values |
|------|--------|
| `trait_category` | `interest`, `goal`, `skill`, `routine`, `workstyle`, `preference`, `avoidance`, `value`, `constraint` |
| `connector_status` | `disconnected`, `connecting`, `connected`, `error`, `reauth_required` |
| `tool_crud_type` | `create`, `read`, `update`, `delete` |
| `task_status` | `todo`, `in_progress`, `done`, `cancelled` |
| `task_priority` | `low`, `medium`, `high`, `urgent` |

---

## Dropped Tables (Historical)

| Table | Dropped In | Reason |
|-------|-----------|--------|
| `chat_sessions` | `20260424` | Replaced by continuous stream in `chat_messages` |
| `connector_providers` | `20260614` | Merged into `user_connectors` |
| `user_connector_tokens` | `20260614` | Merged into `user_connectors` |
| `user_connector_resources` | `20260614` | Merged into `user_connectors.metadata` |
| `connector_tool_permissions` | `20260614` | Merged into `user_connectors.metadata` |
