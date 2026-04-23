# Agent-First Chat Integration Design

Date: 2026-04-23  
Status: Implemented (Task 6 verification complete in worktree)

## 1) Context and Goal

DailyPilotLab already has:

- working chat streaming endpoint and persistence by session
- connector/tool infrastructure
- idea/thought/topic extraction helpers

The next module integration introduces explicit user agents while preserving existing chat behavior as the default agent runtime.

Primary goal:

- move from chat-only identity to agent-first identity without breaking existing UX
- support future custom agents cleanly
- preserve conversation essence through periodic summary compression

## 2) Locked Decisions

- Default agent source of truth: **explicit DB record per user**
- Conversation identity key: **`user_id + agent_id + session_id`**
- Personal state location: **user-level only**
- Summary storage: **separate `chat_summaries` table**
- Summary failure behavior: **non-blocking + retryable pending**
- Extraction input policy: **hybrid (recent raw turns + historical summaries)**
- Architecture direction: **Approach 2 (clean domain split)**

## 3) Scope

In scope:

- default agent bootstrap and persistence
- agent-scoped chat sessions and messages
- 10-turn summary windowing and retryable async summarization
- context assembly updates for hybrid memory feed
- API surface for agent-aware chat flows
- migration strategy from existing chat tables/endpoints
- tests and observability requirements

Out of scope (for this phase):

- custom agent creation UX/spec details
- agent-level memory store (user-level state only for now)
- event-sourced chat core

## 4) Architecture and Boundaries

### 4.1 Domain model

Use explicit entities with clear boundaries:

- `agents`
  - one row per user agent (`default` and future `custom`)
  - ownership by `user_id`
  - runtime/config metadata
- `agent_sessions`
  - one row per conversation thread
  - bound to exactly one `user_id` and one `agent_id`
- `agent_messages`
  - append-only raw turns for a session
  - includes deterministic `turn_index`
- `chat_summaries`
  - compressed windows over conversation turns
  - canonical summary persistence (not synthetic chat messages)

### 4.2 Backend layering fit

Follow existing backend pattern:

- Route: validate request/auth and call manager
- Manager: orchestrate ownership checks, persistence, summary triggers
- Helper: LLM summarization and extraction formatting
- Service: SQL-only table operations

`server.py` remains thin.

## 5) Runtime Data Flow

### 5.1 Inbound chat request

Input requires:

- `agent_id`
- `session_id`
- `content`

Flow:

1. Verify authenticated user.
2. Ensure session ownership for `(session_id, user_id, agent_id)`.
3. Persist user turn to `agent_messages` with next `turn_index`.
4. Build model context from:
   - user-level personal state
   - latest successful historical summaries
   - recent raw turns
5. Stream assistant response.
6. Persist final assistant message as one message row.
7. Update session `updated_at`.
8. Evaluate summary window trigger.

### 5.2 Summary windowing policy

- Turn definition: one **exchange** = one user message + one assistant response.
- Window size: 10 exchanges (20 messages total).
- At each assistant completion, detect newly closed windows.
- For each closed unsummarized window:
  - create/upsert `chat_summaries` row
  - run summarization asynchronously
  - store status transitions (`pending -> done` or retryable failure status)

### 5.3 Failure behavior

- Chat response is never blocked by summary generation.
- Failed summary work is retried with capped backoff.
- Persistent failure moves to terminal status for operational visibility.

## 6) Memory and Compression Strategy

### 6.1 Personal state

- Keep user-level personal state as current baseline.
- Apply to all agents consistently.
- Known trade-off: potential cross-agent contamination.

### 6.2 Context construction

Hybrid memory feed:

- Recent raw turns for precision and immediate dialog continuity.
- Older summaries for context compression and token control.

### 6.3 Summary schema requirements

Each summary payload should preserve:

- core conversation essence
- extracted ideas and thoughts
- topic compression/tags aligned with existing topic vocabulary where possible

## 7) API Surface (Incremental)

Proposed endpoints:

- `POST /agents/default/ensure`
  - idempotently create/get default agent for user
- `GET /agents`
  - list user agents
- `POST /agent-chat/stream`
  - agent-aware streaming chat endpoint
- `GET /agent-chat/sessions?agent_id=...`
  - list sessions for user+agent
- `GET /agent-chat/sessions/{session_id}/history?agent_id=...`
  - load history with strict scope checks

Note:

- Existing `/chat/*` can be maintained temporarily behind compatibility mapping to default agent during migration.

## 8) Data Integrity and Constraints

Required protections:

- strict ownership checks for every read/write path
- uniqueness for summary window identity:
  - `(user_id, agent_id, session_id, window_index)`
- idempotent upsert semantics for summary jobs
- session access denial on mismatched `user_id` or `agent_id`

## 9) Migration Plan

### Phase 1: Additive foundation

- add new tables and constraints
- deploy without traffic switching

### Phase 2: Dual write

- route chat writes to legacy and new agent tables for default-agent traffic
- compare parity

### Phase 3: Read switch

- serve session/history reads from agent tables
- keep fallback switch for safety window

### Phase 4: Legacy retirement

- stop legacy writes
- remove old chat paths/tables after stability criteria

## 10) Testing Strategy

### Unit tests

- session ownership guard with `user_id + agent_id + session_id`
- window index math (10-turn boundaries)
- summary upsert idempotency

### Integration tests

- stream flow persists user + assistant rows
- summary record created at boundary and status transitions work
- retry worker processes pending/failed windows

### Security/regression

- cross-user and cross-agent access blocked
- default-agent experience remains equivalent to current chat UX

## 11) Observability

Track and alert on:

- summary success rate
- retry attempts and terminal failures
- summary lag (window closed to summary done)
- request correlation by `user_id`, `agent_id`, `session_id`, `window_index`

## 12) Risks and Mitigations

- Risk: user-level-only memory causes agent context bleed.
  - Mitigation: reserve extension path for optional agent-scoped memory later.
- Risk: migration drift between legacy and new tables.
  - Mitigation: dual-write parity checks before read switch.
- Risk: summary backlog growth under load.
  - Mitigation: queue visibility, retry caps, dead-letter handling.

## 13) Acceptance Criteria

This design is considered ready for implementation planning when:

- default agent auto-provisioning is idempotent and backend-controlled
- all chat persistence uses agent-scoped identity
- 10-turn summary pipeline is asynchronous, retryable, and observable
- hybrid context assembly is implemented and tested
- migration path is staged with rollback points

## Implementation Status

- [x] Schema introduced for agents/sessions/messages/summaries
- [x] Agent-aware endpoints added with `/chat/*` compatibility mapping
- [x] 10-exchange summary windowing with retryable statuses
- [x] Targeted verification executed in worktree (`agent_chat_db`, `chat_summary_windows`, `agent_chat_routes`)
- [x] Connector smoke regressions executed (`gmail_routes`, `gmail_tools` substituted for missing `chat_tool_schema`)
