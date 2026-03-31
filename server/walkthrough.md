# DailyPilotLab — Complete Codebase Walkthrough

## What Is This App?

**DailyPilotLab** is a **FastAPI REST service** that acts as an **intelligent idea capture & organization system**. You throw raw thoughts/ideas at it, and it:

1. **Classifies** each input (idea / personal info / secret / gibberish) using an LLM
2. **Auto-refines** raw ideas into clean, atomic, third-person statements
3. **Generates embeddings** (OpenAI `text-embedding-3-small`) for semantic intelligence
4. **Groups ideas into topics** using both vector similarity (pgvector) and LLM-based organization
5. **Supports semantic search** — "find ideas similar to X"

**Stack**: Python 3.12+ · FastAPI · Supabase Postgres (pgvector) · OpenAI (embeddings + structured outputs) · psycopg2

---

## Architecture Overview

```
┌───────────────────────────────────────────────────────────┐
│                      server.py (FastAPI)                  │
│         10 API endpoints — routes & HTTP plumbing         │
└──────────┬──────────────────────────────────┬─────────────┘
           │                                  │
  ┌────────▼─────────┐            ┌───────────▼──────────┐
  │ utils/            │            │ utils/                │
  │ idea_manager.py   │            │ topic_manager.py      │
  │ (Idea CRUD +      │            │ (Topic CRUD +         │
  │  refinement)      │            │  recency)             │
  └────────┬──────────┘            └───────────┬───────────┘
           │                                   │
  ┌────────▼──────────────────────────────────▼───────────┐
  │               utils/helpers.py                         │
  │  classify_ideas() · organize_ideas_into_topics()       │
  │  semantic_search_memories() · refine_raw_ideas()       │
  │  update_personal_state() · assign_idea_to_topic()      │
  └────────┬──────────────────────────────────┬────────────┘
           │                                  │
  ┌────────▼─────────┐            ┌───────────▼────────────┐
  │ services/         │            │ utils/openAi.py        │
  │ ideas_service.py  │            │ OpenAIWrapper          │
  │ topics_service.py │            │ - get_embeddings()     │
  │ (SQL / DB logic)  │            │ - get_chat_completion()│
  └────────┬──────────┘            └────────────────────────┘
           │
  ┌────────▼─────────┐
  │ db/dbConnection.py│  ← psycopg2 context managers
  └──────────────────┘
```

---

## Directory Structure

| Path | Purpose |
|------|---------|
| [server.py](file:///d:/tilak/DailyPilotLab/server.py) | FastAPI app — all route definitions |
| [db/dbConnection.py](file:///d:/tilak/DailyPilotLab/db/dbConnection.py) | Postgres connection (context managers) |
| [db/seed.py](file:///d:/tilak/DailyPilotLab/db/seed.py) | DDL + sample data seeder |
| [models/ideas.py](file:///d:/tilak/DailyPilotLab/models/ideas.py) | Pydantic models for Idea CRUD |
| [models/topics.py](file:///d:/tilak/DailyPilotLab/models/topics.py) | Pydantic models for Topic CRUD |
| [models/output_schemas.py](file:///d:/tilak/DailyPilotLab/models/output_schemas.py) | Pydantic schemas for OpenAI structured outputs |
| [services/ideas_service.py](file:///d:/tilak/DailyPilotLab/services/ideas_service.py) | [IdeaService](file:///d:/tilak/DailyPilotLab/services/ideas_service.py#7-241) — all idea SQL queries |
| [services/topics_service.py](file:///d:/tilak/DailyPilotLab/services/topics_service.py) | [TopicsService](file:///d:/tilak/DailyPilotLab/services/topics_service.py#5-223) — all topic SQL queries |
| [utils/helpers.py](file:///d:/tilak/DailyPilotLab/utils/helpers.py) | LLM orchestration (classify, organize, search, refine) |
| [utils/idea_manager.py](file:///d:/tilak/DailyPilotLab/utils/idea_manager.py) | High-level idea business logic |
| [utils/topic_manager.py](file:///d:/tilak/DailyPilotLab/utils/topic_manager.py) | High-level topic business logic |
| [utils/openAi.py](file:///d:/tilak/DailyPilotLab/utils/openAi.py) | [OpenAIWrapper](file:///d:/tilak/DailyPilotLab/utils/openAi.py#7-31) — embeddings + chat |
| `config/prompts/*.yaml` | 4 LLM prompt templates |
| [config/memory/personal_state.json](file:///d:/tilak/DailyPilotLab/config/memory/personal_state.json) | Persistent user profile (key-value) |

---

## Database Schema (3 Tables)

### [raw_idea](file:///d:/tilak/DailyPilotLab/utils/idea_manager.py#19-22)
| Column | Type | Notes |
|--------|------|-------|
| [id](file:///d:/tilak/DailyPilotLab/services/ideas_service.py#17-21) | BIGINT (auto) | PK |
| `created_at` | TIMESTAMPTZ | Default `now()` |
| `content` | TEXT | The idea text |
| [embeddings](file:///d:/tilak/DailyPilotLab/utils/openAi.py#12-18) | vector | OpenAI embedding (set after refinement) |
| [raw](file:///d:/tilak/DailyPilotLab/utils/idea_manager.py#19-22) | BOOLEAN | `TRUE` = unrefined, `FALSE` = refined |

### [topic](file:///d:/tilak/DailyPilotLab/services/topics_service.py#15-19)
| Column | Type | Notes |
|--------|------|-------|
| [id](file:///d:/tilak/DailyPilotLab/services/ideas_service.py#17-21) | BIGINT (auto) | PK |
| `created_at` / `updated_at` | TIMESTAMP | Auto-managed |
| `title` | TEXT | Topic name |
| `summary` | TEXT | Theme description |
| `summary_embedding` | vector | For semantic search |
| `activity_7d` / `activity_30d` | SMALLINT | Rolling activity counts |
| `lifetime_size` | INTEGER | Total ideas ever assigned |
| `last_activity_at` | TIME | Last activity timestamp |
| `is_archived` | BOOLEAN | Soft-delete |
| `recency_strength` | REAL | Computed metric |
| `dominance` | REAL | Computed metric |

### `idea_topics` (Junction Table)
| Column | Type | Notes |
|--------|------|-------|
| [idea_id](file:///d:/tilak/DailyPilotLab/services/topics_service.py#133-159) | BIGINT | FK → `raw_idea.id` (CASCADE) |
| `topic_id` | BIGINT | FK → `topic.id` (CASCADE) |
| | | Composite PK ([idea_id](file:///d:/tilak/DailyPilotLab/services/topics_service.py#133-159), `topic_id`) |

> An idea can belong to **multiple topics** (many-to-many).

---

## All 10 API Endpoints — Detailed Flows

### 1. `GET /ideas` — List All Ideas

**Flow**: [server.py](file:///d:/tilak/DailyPilotLab/server.py) → `idea_manager.get_ideas()` → `IdeaService.get_all_ideas()` → `SELECT * FROM raw_idea`

Returns all ideas (both raw and refined) with their [id](file:///d:/tilak/DailyPilotLab/services/ideas_service.py#17-21), `created_at`, `content`, [embeddings](file:///d:/tilak/DailyPilotLab/utils/openAi.py#12-18), and `topic_ids`.

---

### 2. `POST /ideas` — Create a Single Idea

**Input**: `{ "content": "some thought" }`

**Flow**:
1. If content is empty → return "No text to add"
2. **Classify** the input via LLM ([classify_ideas()](file:///d:/tilak/DailyPilotLab/utils/helpers.py#13-37))  
   → Calls OpenAI with [ideaFiltering.yaml](file:///d:/tilak/DailyPilotLab/config/prompts/ideaFiltering.yaml) prompt + [personal_state.json](file:///d:/tilak/DailyPilotLab/config/memory/personal_state.json) as context
   → Returns one of: [idea](file:///d:/tilak/DailyPilotLab/services/ideas_service.py#17-21), `gibberish`, `secrets`, `personal_information`
3. Based on classification:
   - `gibberish` → return "Gibberish text" (no DB write)
   - `secrets` → return "Can't save sensitive data" (no DB write)
   - `personal_information` → calls [update_personal_state()](file:///d:/tilak/DailyPilotLab/utils/helpers.py#38-70) which uses OpenAI to merge into [personal_state.json](file:///d:/tilak/DailyPilotLab/config/memory/personal_state.json)
   - [idea](file:///d:/tilak/DailyPilotLab/services/ideas_service.py#17-21) → **insert into [raw_idea](file:///d:/tilak/DailyPilotLab/utils/idea_manager.py#19-22)** with `raw=TRUE`
4. After insert, checks if raw idea count > `TOPIC_AUTO_REFINEMENT_THRESHOLD` (default: 3)
   - If yes → auto-triggers [raw_to_refined_ideas()](file:///d:/tilak/DailyPilotLab/utils/idea_manager.py#196-221) (see endpoint #9)

---

### 3. `POST /ideas/bulk` — Create Multiple Ideas

**Input**: `[{ "content": "idea1" }, { "content": "idea2" }, ...]`

**Flow**:
1. Checks limit: max `BULK_IDEA_INSERTION_THRESHOLD` ideas (default: 4)
2. Filters out empty content
3. If only 1 valid idea → delegates to single [create_idea()](file:///d:/tilak/DailyPilotLab/services/ideas_service.py#75-89)
4. **Batch classifies** all ideas in one LLM call
5. Separates into `ideas[]` and `personal_info[]`
6. Updates personal state if personal info found
7. Bulk-inserts valid ideas via `execute_values`
8. Auto-triggers refinement if threshold reached

---

### 4. `POST /ideas/update` — Update an Idea

**Input**: `{ "id": 123, "content": "updated text", "topic_ids": [1, 2] }`

**Flow**:
1. If content changed → generates **new embedding** via OpenAI
2. Updates the [raw_idea](file:///d:/tilak/DailyPilotLab/utils/idea_manager.py#19-22) row
3. If `topic_ids` provided → updates `idea_topics` junction table

---

### 5. `POST /ideas/delete` — Delete Single Idea

**Input**: `{ "id": 123 }`

Deletes from [raw_idea](file:///d:/tilak/DailyPilotLab/utils/idea_manager.py#19-22). Junction table entries are **cascade-deleted**.

---

### 6. `POST /ideas/delete/bulk` — Bulk Delete Ideas

**Input**: `[1, 2, 3]` (list of idea IDs)

Uses `DELETE ... WHERE id = ANY(...)` for efficient batch deletion.

---

### 7. `POST /ideas/delete/all` — Delete All Ideas

Truncates all rows from [raw_idea](file:///d:/tilak/DailyPilotLab/utils/idea_manager.py#19-22). Cascades to `idea_topics`.

---

### 8. `GET /topics/assign` — Assign Ideas to Topics (⭐ Core Intelligence)

This is the **heart of the system**. Two-phase approach:

**Phase 1 — Vector Similarity** (DB-level):
- Calls a Supabase function `assign_and_return_matches(threshold)` that uses pgvector to match unassigned ideas to existing topics by embedding similarity
- Threshold: `TOPIC_ASSIGNMENT_THRESHOLD_SIMILARITY` (default: 0.48, converted to distance = 1 - 0.48 = 0.52)

**Phase 2 — LLM Organization** (for remaining unassigned ideas):
1. Fetches all still-unassigned ideas (`LEFT JOIN idea_topics ... WHERE topic_id IS NULL`)
2. Fetches all existing topics
3. Sends both to OpenAI via [topic_organization.yaml](file:///d:/tilak/DailyPilotLab/config/prompts/topic_organization.yaml) prompt
4. LLM returns a [TopicsList](file:///d:/tilak/DailyPilotLab/models/output_schemas.py#69-72) with each topic marked `is_new: true/false`
   - **New topics**: creates with title, summary, embeddings, and assigned idea_ids
   - **Existing topics**: appends idea_ids to existing topics

---

### 9. `GET /refine-ideas` — Refine Raw Ideas into Atomic Statements

**Flow**:
1. Fetches all ideas where `raw = TRUE`
2. Sends to OpenAI with [idea_refiner.yaml](file:///d:/tilak/DailyPilotLab/config/prompts/idea_refiner.yaml) prompt
3. LLM returns [RefinedIdeaList](file:///d:/tilak/DailyPilotLab/models/output_schemas.py#78-82) — deduped, third-person, atomic sentences
4. **Deletes** all raw ideas (`DELETE WHERE raw = TRUE`)
5. Generates **embeddings** for each refined idea
6. **Bulk inserts** refined ideas with `raw = FALSE` and embeddings set

> [!IMPORTANT]
> This is a destructive + constructive operation: raw ideas are replaced by refined versions. The original raw text is lost.

---

### 10. `GET /semantic-search?query=...` — Semantic Search

**Flow**:
1. Generates embedding for the query string
2. Runs a **two-level semantic search** via a single SQL CTE:
   - **Level 1**: Find top N topics by `summary_embedding <=> query` (cosine distance)
     - Threshold: `TOPIC_SIMILARITY_THRESHOLD` (default: 0.2 → 80% similarity)
   - **Level 2**: For each matched topic, find top K ideas by `embeddings <=> query`
     - Threshold: `IDEA_SIMILARITY_THRESHOLD` (default: 0.4 → 60% similarity)
3. Groups results by topic and returns structured JSON

---

### 11. `GET /update-topic-recency` — Refresh Topic Metrics

Calls a Supabase internal function `update_topic_recency_metrics()` to update `activity_7d`, `activity_30d`, and `lifetime_size` columns on the [topic](file:///d:/tilak/DailyPilotLab/services/topics_service.py#15-19) table.

---

## LLM Integration (4 Prompt Templates)

| Prompt File | Used By | OpenAI Schema | Purpose |
|-------------|---------|---------------|---------|
| [ideaFiltering.yaml](file:///d:/tilak/DailyPilotLab/config/prompts/ideaFiltering.yaml) | [classify_ideas()](file:///d:/tilak/DailyPilotLab/utils/helpers.py#13-37) | [ClassificationResultList](file:///d:/tilak/DailyPilotLab/models/output_schemas.py#9-11) | Classify input as idea/personal_info/secrets/gibberish |
| [personal_info_updater.yaml](file:///d:/tilak/DailyPilotLab/config/prompts/personal_info_updater.yaml) | [update_personal_state()](file:///d:/tilak/DailyPilotLab/utils/helpers.py#38-70) | [PersonalState](file:///d:/tilak/DailyPilotLab/models/output_schemas.py#21-27) | Extract & merge personal info into state file |
| [topic_organization.yaml](file:///d:/tilak/DailyPilotLab/config/prompts/topic_organization.yaml) | [organize_ideas_into_topics()](file:///d:/tilak/DailyPilotLab/utils/helpers.py#72-131) | [TopicsList](file:///d:/tilak/DailyPilotLab/models/output_schemas.py#69-72) | Group unassigned ideas into new/existing topics |
| [idea_refiner.yaml](file:///d:/tilak/DailyPilotLab/config/prompts/idea_refiner.yaml) | [refine_raw_ideas()](file:///d:/tilak/DailyPilotLab/utils/helpers.py#186-205) | [RefinedIdeaList](file:///d:/tilak/DailyPilotLab/models/output_schemas.py#78-82) | Convert raw thoughts → atomic third-person statements |

All LLM calls use **OpenAI structured outputs** (`responses.parse()` with `text_format`) via `gpt-5-nano` model, with `text-embedding-3-small` for embeddings.

---

## Key Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TOPIC_ASSIGNMENT_THRESHOLD_SIMILARITY` | 0.48 | Min similarity for auto-assigning idea → topic via pgvector |
| `TOPIC_SIMILARITY_THRESHOLD` | 0.2 | Min similarity for topic matches in semantic search |
| `IDEA_SIMILARITY_THRESHOLD` | 0.4 | Min similarity for idea matches in semantic search |
| `TOPIC_AUTO_REFINEMENT_THRESHOLD` | 3 | Raw idea count that triggers auto-refinement |
| `BULK_IDEA_INSERTION_THRESHOLD` | 4 | Max batch size for bulk idea creation |
| `RECENCY_THRESHOLD` | 7 | For high-signal topic filtering (recency_strength) |
| `DOMINANCE_THRESHOLD` | 15 | For high-signal topic filtering (dominance) |

---

## Data Lifecycle — The Full Journey of an Idea

```
User Input → POST /ideas
    │
    ▼
Classify (LLM) ──→ gibberish? ──→ Rejected
    │                secrets?  ──→ Rejected
    │                personal? ──→ Update personal_state.json
    │
    ▼ (category == "idea")
Insert into raw_idea (raw=TRUE, no embedding)
    │
    ▼ (when raw count > threshold)
GET /refine-ideas (auto or manual)
    │
    ▼
LLM Refinement → Delete raws → Insert refined (raw=FALSE, with embeddings)
    │
    ▼
GET /topics/assign
    │
    ├──▶ Phase 1: pgvector similarity match (DB function)
    │
    └──▶ Phase 2: LLM organizes remaining into topics
              │
              ├── Assign to existing topics
              └── Create new topics (with embeddings)
    │
    ▼
GET /semantic-search?query=...
    └── Two-level search: Topics → Ideas within topics
```
