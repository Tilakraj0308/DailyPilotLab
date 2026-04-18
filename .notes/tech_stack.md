# Tech Stack — DailyPilotLab

## Runtime
| Component | Version / Detail |
|-----------|-----------------|
| Python | 3.12+ |
| Package Manager | `uv` (via `pyproject.toml` + `uv.lock`) |

## Framework
| Component | Detail |
|-----------|--------|
| Web Framework | **FastAPI** |
| Server | Uvicorn (implicit via FastAPI) |
| Validation | **Pydantic v2** (models, structured outputs) |

## Database
| Component | Detail |
|-----------|--------|
| Database | **Supabase Postgres** |
| Vector Extension | **pgvector** (cosine distance `<=>` operator) |
| Driver | **psycopg2** (with `RealDictCursor`, `execute_values`) |
| Server-side Functions | `assign_and_return_matches()`, `update_topic_recency_metrics()` |

## AI / LLM
| Component | Detail |
|-----------|--------|
| Provider | **OpenAI** |
| Chat Model | `gpt-5-nano` (via structured outputs / `responses.parse()`) |
| Embedding Model | `text-embedding-3-small` |
| Output Format | Pydantic schemas as `text_format` for structured outputs |

## Configuration
| Component | Detail |
|-----------|--------|
| Env Variables | `.env` file via `python-dotenv` |
| Prompt Templates | YAML files in `config/prompts/` |
| Persistent State | `config/memory/personal_state.json` |

## Key Libraries
| Library | Purpose |
|---------|---------|
| `fastapi` | HTTP framework |
| `pydantic` | Data validation + OpenAI structured output schemas |
| `psycopg2` | Postgres driver |
| `openai` | LLM + embeddings SDK |
| `pyyaml` | Prompt template loading |
| `python-dotenv` | Environment variable management |
| `requests` | HTTP to third-party APIs (Google APIs, Notion REST API) |

## Third-party integrations (connectors)

| Integration | Mechanism |
|-------------|-----------|
| Google Calendar / Tasks | OAuth 2.0 PKCE (Web client), Google REST APIs |
| Notion | Public integration OAuth 2.0 (`api.notion.com/v1/oauth/*`), Notion REST API with `Notion-Version` header |
