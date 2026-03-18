# Architecture — DailyPilotLab

## Layer Diagram
```
┌─────────────────────────────────────────────────────┐
│                  server.py (FastAPI)                 │
│              12 API endpoints — routing              │
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

## Folder Conventions
```
DailyPilotLab/
├── server.py            # All route definitions (thin controller)
├── config/
│   ├── prompts/         # 5 YAML prompt templates for LLM calls
│   └── memory/          # personal_state.json (persistent user profile)
├── db/
│   ├── dbConnection.py  # get_dict_cursor() context manager
│   └── seed.py          # DDL + sample data
├── models/
│   ├── ideas.py         # Pydantic: IdeaCreateInput, IdeaOut, etc.
│   ├── topics.py        # Pydantic: TopicCreateInput, TopicUpdateInput
│   ├── traits.py        # Pydantic: TraitCandidate, TraitExtractionResponse
│   └── output_schemas.py# Pydantic schemas for OpenAI structured outputs
├── services/
│   ├── ideas_service.py # IdeaService — all idea SQL queries
│   ├── topics_service.py# TopicsService — all topic SQL queries
│   └── trait_service.py # TraitsService — embed, dedup, EMA upsert
├── utils/
│   ├── helpers.py       # LLM orchestration (classify, organize, refine, traits)
│   ├── idea_manager.py  # Idea business logic (create, refine, delete)
│   ├── topic_manager.py # Topic business logic (create, update, recency)
│   └── openAi.py        # OpenAIWrapper singleton
└── .notes/              # Memory Bank (this folder)
```

## Data Flow Pattern
All endpoints follow: **Route → Manager → Helper/Service → DB/LLM**

- `server.py` is a thin routing layer (no business logic)
- `*_manager.py` files orchestrate multi-step flows
- `helpers.py` handles all LLM interactions
- `*_service.py` files contain raw SQL queries
- `dbConnection.py` provides cursor context managers

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
