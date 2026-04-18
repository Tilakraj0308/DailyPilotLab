# Architecture — DailyPilotLab

## Layer diagram

All backend paths below are under **`server/`** (run commands from that directory unless documented otherwise).

```
┌─────────────────────────────────────────────────────┐
│              server/server.py (FastAPI)              │
│              API endpoints — routing                 │
└──────────┬─────────────────────────────┬────────────┘
           │                             │
  ┌────────▼────────┐         ┌──────────▼──────────┐
  │ utils/           │         │ utils/               │
  │ idea_manager.py  │         │ topic_manager.py     │
  │ (Idea CRUD +     │         │ (Topic CRUD +        │
  │  refinement)     │         │  recency)            │
  └────────┬─────────┘         └──────────┬───────────┘
           │                              │
  ┌────────▼──────────────────────────────▼──────────┐
  │              utils/helpers.py                     │
  │  classify · organize · search · refine · traits   │
  └────────┬─────────────────────────────┬───────────┘
           │                             │
  ┌────────▼────────┐         ┌──────────▼───────────┐
  │ services/        │         │ utils/openAi.py      │
  │ ideas_service    │         │ OpenAIWrapper        │
  │ topics_service   │         │ - get_embeddings()   │
  │ trait_service    │         │ - get_chat_completion │
  │ (SQL layer)      │         └─────────────────────┘
  └────────┬─────────┘
           │
  ┌────────▼─────────┐
  │ db/dbConnection   │  ← psycopg2 context managers
  └──────────────────┘
```

## Folder conventions

```
DailyPilotLab/
├── server/
│   ├── server.py            # All route definitions (thin controller)
│   ├── config/
│   │   ├── prompts/         # YAML prompt templates for LLM calls
│   │   └── memory/          # personal_state.json (persistent user profile)
│   ├── db/
│   │   ├── dbConnection.py  # get_dict_cursor() context manager
│   │   └── seed.py          # sample data
│   ├── models/
│   │   ├── ideas.py         # Pydantic: IdeaCreateInput, IdeaOut, etc.
│   │   ├── topics.py        # Pydantic: TopicCreateInput, TopicUpdateInput
│   │   ├── traits.py        # Pydantic: TraitCandidate, TraitExtractionResponse
│   │   └── output_schemas.py# Pydantic schemas for OpenAI structured outputs
│   ├── services/
│   │   ├── ideas_service.py # IdeaService — all idea SQL queries
│   │   ├── topics_service.py# TopicsService — all topic SQL queries
│   │   └── trait_service.py # TraitsService — embed, dedup, EMA upsert
│   └── utils/
│       ├── helpers.py       # LLM orchestration (classify, organize, refine, traits)
│       ├── idea_manager.py  # Idea business logic (create, refine, delete)
│       ├── topic_manager.py # Topic business logic (create, update, recency)
│       └── openAi.py        # OpenAIWrapper singleton
├── app/                     # Expo client (see app/README.md)
└── .notes/                  # Memory Bank (this folder)
```

## Data Flow Pattern
All endpoints follow: **Route → Manager → Helper/Service → DB/LLM**

- `server/server.py` is a thin routing layer (no business logic)
- `*_manager.py` files orchestrate multi-step flows
- `helpers.py` handles all LLM interactions
- `*_service.py` files contain raw SQL queries
- `dbConnection.py` provides cursor context managers

## Connectors (integrations)

Third-party OAuth and tool execution live under **`server/connectors/`** (mounted at `/connectors`).

- **Registry:** `connectors/providers/__init__.py` maps `provider_key` → connector class (`google_calendar`, `google_tasks`, `notion`).
- **Google:** `GoogleOAuthConnector` in `connectors/base_connector.py` — Google OAuth PKCE, token refresh, revoke.
- **Notion:** `NotionConnector` in `connectors/providers/notion/` — Notion OAuth token endpoint (HTTP Basic), refresh, local-only disconnect.
- **Tools:** Each provider can expose `tools/` with `TOOL_DEFINITIONS`; `tool_registry.py` and `tool_executor.py` resolve tools and enforce CRUD permissions + history.
- **Client:** Expo app `app/src/connectors/` — Profile integrations, OAuth return handling, Tool Access screen.

## Database Schema (4 Tables)
| Table | Purpose |
|-------|---------|
| `raw_idea` | All ideas (raw + refined), with optional embeddings |
| `topic` | Topic clusters with summaries, embeddings, and activity metrics |
| `idea_topics` | Many-to-many junction (idea ↔ topic) |
| `trait` | User behavioral traits with confidence scores + embeddings |

## API Patterns
- All create/write endpoints return `{ status, message }`
- Response status codes are set via `Response` object injection
- LLM calls use OpenAI structured outputs (Pydantic schema as `text_format`)
- Embeddings use `text-embedding-3-small`, chat uses `gpt-5-nano`
