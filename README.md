# DailyPilotLab

A FastAPI service that captures raw ideas, groups them into topics using semantic embeddings (OpenAI), and exposes REST endpoints for idea management and semantic search — all backed by a Supabase Postgres database with the `pgvector` extension.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Supabase Setup](#supabase-setup)
3. [Environment Configuration](#environment-configuration)
4. [Install Dependencies](#install-dependencies)
5. [Seed the Database](#seed-the-database)
6. [Run the Server](#run-the-server)
7. [API Endpoints](#api-endpoints)

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | ≥ 3.12 |
| [uv](https://docs.astral.sh/uv/) | latest |
| A Supabase project | free tier is fine |

---

## Supabase Setup

1. **Create a project** at [supabase.com](https://supabase.com) → *New project*.
2. **Enable the `pgvector` extension** (the seed script does this automatically, but you can also do it manually):
   - Go to **Database → Extensions** in your project dashboard.
   - Search for **vector** and toggle it on.
3. **Get your connection credentials** from the **Session Pooler**:
   - In your Supabase dashboard go to **Project Settings → Database**.
   - Scroll to **Connection string** and click the **Session mode** tab (not *Transaction mode*).
     > **Why Session mode?** The seed script uses `psycopg2` with server-side cursors and pgvector operators that require a persistent session. Transaction-mode poolers (port 6543) reset the session between statements and will cause errors.
   - Switch the view to **Parameters** (instead of URI) to see individual fields.

   First, create your `.env` from the example:
   ```bash
   cp .env.example .env
   ```

   Then copy each credential into `.env`:

   | `.env` key | Pooler → Parameters field | Example value |
   |------------|--------------------------|---------------|
   | `user` | **User** | `postgres.abcxyz1234` |
   | `password` | *(the password you set at project creation)* | `supersecret` |
   | `host` | **Host** | `aws-0-ap-southeast-1.pooler.supabase.com` |
   | `port` | **Port** — use **5432** (Session mode) | `5432` |
   | `dbname` | **Database name** | `postgres` |

4. **Get your OpenAI API key** from [platform.openai.com/api-keys](https://platform.openai.com/api-keys).

---

## Environment Configuration

Open `.env` and verify the placeholder values match what you copied from Supabase:

```ini
# .env

# ── Supabase Postgres connection ──────────────────────────────────────────────
user=postgres.your-project-ref          # from Supabase → Settings → Database
password=your-supabase-password
host=aws-0-ap-southeast-1.pooler.supabase.com
port=5432
dbname=postgres

# ── OpenAI ───────────────────────────────────────────────────────────────────
OPENAPI=sk-...

# ── Tuning knobs (leave defaults unless you know what you're changing) ────────
TOPIC_ASSIGNMENT_THRESHOLD_SIMILARITY=0.48
TOPIC_SIMILARITY_THRESHOLD=0.2
IDEA_SIMILARITY_THRESHOLD=0.4
TOPIC_AUTO_REFINEMENT_THRESHOLD=3
BULK_IDEA_INSERTION_THRESHOLD=4
```

> **Never commit `.env`** — it is already listed in `.gitignore`.

---

## Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for fast, reproducible installs:

```bash
uv sync
```

This creates a `.venv` virtual environment and installs all packages pinned in `uv.lock`.

---

## Seed the Database

The seed script:
- Enables the `pgvector` extension.
- Creates the `trait_category` enum type.
- Creates all tables (`raw_idea`, `topic`, `idea_topics`, `trait`) and the HNSW index — **idempotent**, safe to re-run.
- Creates the `assign_and_return_matches` and `update_topic_recency_metrics` stored functions.
- Inserts 10 sample ideas so the app has real data to work with immediately.

```bash
.venv/bin/python -m db.seed
```

Expected output:

```
Applying DDL …
  ✓ Schema ready.
Inserting seed ideas …
  ✓ Inserted 10 ideas (ids: [...]).

Seed complete.
```

---

## Run the Server

```bash
.venv/bin/fastapi dev server.py
```

The API is then available at `http://127.0.0.1:8000`.  
Interactive docs: `http://127.0.0.1:8000/docs`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/ideas` | List all ideas |
| `POST` | `/ideas` | Create a single idea |
| `POST` | `/ideas/bulk` | Create multiple ideas at once |
| `POST` | `/ideas/update` | Update an idea |
| `POST` | `/ideas/delete` | Delete a single idea |
| `POST` | `/ideas/delete/bulk` | Delete multiple ideas by ID |
| `POST` | `/ideas/delete/all` | Delete all ideas |
| `GET` | `/topics/assign` | Run topic assignment for unprocessed ideas |
| `GET` | `/semantic-search?query=…` | Semantic search across ideas |
| `GET` | `/refine-ideas` | Refine raw ideas using AI |
