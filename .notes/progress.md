# Progress — DailyPilotLab

## Core Features

### Idea Management
- [x] Single idea creation with LLM classification
- [x] Bulk idea creation with batch classification
- [x] Idea update with re-embedding
- [x] Single / bulk / full idea deletion
- [x] Auto-refinement trigger when raw count exceeds threshold

### Idea Refinement
- [x] LLM-based refinement (raw → atomic third-person statements)
- [x] Embedding generation for refined ideas
- [x] Delete-and-replace pipeline for raw → refined

### Topic Assignment
- [x] Phase 1: pgvector similarity matching via DB function
- [x] Phase 2: LLM-based organization for unassigned leftovers
- [x] New topic creation with embeddings
- [x] Existing topic augmentation (append idea_ids)

### Semantic Search
- [x] Two-level CTE query (topic → ideas within topic)
- [x] Configurable similarity thresholds via env vars

### Topic Recency
- [x] DB function for metric refresh (activity_7d, activity_30d, etc.)

### Trait Extraction
- [x] High-signal topic filtering (recency + dominance thresholds)
- [x] LLM-based trait extraction from topic + memory snippets
- [x] Semantic dedup (cosine distance ≤ 0.12)
- [x] EMA smoothing for confidence (capped at ±0.05/0.03)
- [x] New trait insertion with confidence cap at 0.5

### Personal State
- [x] LLM-based personal info extraction
- [x] JSON file persistence for user profile

## Infrastructure
- [x] FastAPI server with 12 endpoints
- [x] Supabase Postgres + pgvector
- [x] OpenAI integration (structured outputs + embeddings)
- [x] YAML prompt templates
- [x] Pydantic models for all I/O
- [x] Connectors: Google Calendar, Google Tasks, **Notion** (OAuth + encrypted tokens + tool registry CRUD for Notion pages)

## Pending / Ideas
- [ ] Error handling improvements (currently swallows errors with 200 status)
- [ ] Trait read/query API
- [ ] Pagination for `GET /ideas`
- [ ] WebSocket or SSE for long-running operations (refinement, topic assign)
- [ ] Rate limiting for LLM calls
- [ ] Tests (unit + integration)
