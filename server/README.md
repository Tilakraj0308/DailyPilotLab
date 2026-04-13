# DailyPilotLab

A FastAPI service that captures raw ideas, groups them into topics using semantic embeddings (OpenAI), and exposes REST endpoints for idea management and semantic search — all backed by a Supabase Postgres database with the `pgvector` extension.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Supabase Setup](#supabase-setup)
3. [Environment Configuration](#environment-configuration)
4. [Install Dependencies](#install-dependencies)
5. [Apply Migrations &amp; Seed the Database](#apply-migrations--seed-the-database)
6. [Run the Server](#run-the-server)
7. [API Endpoints](#api-endpoints)

---

## Prerequisites

| Tool                                                              | Version           |
| ----------------------------------------------------------------- | ----------------- |
| Python                                                            | ≥ 3.12           |
| [uv](https://docs.astral.sh/uv/)                                     | latest            |
| [Supabase CLI](https://supabase.com/docs/guides/cli/getting-started) | latest            |
| A Supabase project                                                | free tier is fine |

---

## Supabase Setup

1. **Create a project** at [supabase.com](https://supabase.com) → *New project*.
2. **Enable the `pgvector` extension** (the migration files do this automatically, but you can also do it manually):

   - Go to **Database → Extensions** in your project dashboard.
   - Search for **vector** and toggle it on.
3. **Get your connection credentials** from the **Session Pooler**:

   - In your Supabase dashboard go to **Project Settings → Database**.
   - Scroll to **Connection string** and click the **Session mode** tab (not *Transaction mode*).
     > **Why Session mode?** The seed script uses `psycopg2` with server-side cursors and pgvector operators that require a persistent session. Transaction-mode poolers (port 6543) reset the session between statements and will cause errors.
     >
   - Switch the view to **Parameters** (instead of URI) to see individual fields.

   First, create your `.env` from the example:

   ```bash
   cp .env.example .env
   ```

   Then copy each credential into `.env`:

   | `.env` key | Pooler → Parameters field                          | Example value                                |
   | ------------ | --------------------------------------------------- | -------------------------------------------- |
   | `user`     | **User**                                      | `postgres.abcxyz1234`                      |
   | `password` | *(the password you set at project creation)*      | `supersecret`                              |
   | `host`     | **Host**                                      | `aws-0-ap-southeast-1.pooler.supabase.com` |
   | `port`     | **Port** — use **5432** (Session mode) | `5432`                                     |
   | `dbname`   | **Database name**                             | `postgres`                                 |
4. **Get your OpenAI API key** from [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
5. **Get your Supabase Anon Key** from **Project Settings → API**.

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

# ── Supabase Auth ────────────────────────────────────────────────────────────
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
SUPABASE_ANON_KEY=your-supabase-anon-key

# ── Google Connectors ────────────────────────────────────────────────────────
# See setup.md for instructions on creating these credentials
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/connectors/google/calendar/callback

# Token Encryption Key
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CONNECTOR_TOKEN_ENCRYPTION_KEY=your-generated-key

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

## Apply Migrations & Seed the Database

The database schema is managed via **Supabase migration files** in `supabase/migrations/`:

| Migration                                | Contents                                                                                                               |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `20260309_create_core_tables.sql`      | pgvector extension, enums, tables (`raw_idea`, `topic`, `idea_topics`, `trait`, `users`), indexes & triggers |
| `20260310_create_stored_functions.sql` | `assign_and_return_matches`, `update_topic_recency_metrics`                                                        |
| `20260327_create_chat_tables.sql`      | `chat_sessions`, `chat_messages`                                                                                   |

**1. Install the Supabase CLI(if you don't already have)** by following the [official install guide](https://supabase.com/docs/guides/cli/getting-started).

**2. Login to Supabase CLI:**

```bash
npx supabase login
```

*(This generates an access token so you can link and push to your remote project)*

**3. Link your project** (find your project ref in Supabase Dashboard → Project Settings → General):

```bash
npx supabase link --project-ref <your-project-ref>
```

**4. Push the migrations:**

```bash
npx supabase db push
```

Once the schema is in place, run the **seed script** to insert 10 sample ideas:

```bash
.venv/bin/python -m db.seed
```

Expected output:

```
Inserting seed ideas …
  ✓ Inserted 10 ideas (ids: [...]).

Seed complete.
```

---

## Run the Server

```bash
.venv/bin/fastapi dev server.py --host 0.0.0.0
```

The API is then available at `http://127.0.0.1:8000`.
Interactive docs: `http://127.0.0.1:8000/docs`


---

## Connector Setup

The application supports external connectors (e.g., Google Calendar). To set up a connector:

1. **Create a Google Web Client ID** in the Google Cloud Console.
2. **Enable required APIs** (Calendar, Tasks, Gmail) in the [Google API Library](https://console.cloud.google.com/apis/library).
3. **Add Test Users** to your OAuth consent screen.
4. **Configure the Redirect URI** to `http://localhost:8000/connectors/google/calendar/callback`.
5. **Update your `.env`** with the Client ID, Secret, and an encryption key.

For detailed, step-by-step instructions, see [setup.md](setup.md).

---

## API Endpoints

| Method   | Path                          | Description                                |
| -------- | ----------------------------- | ------------------------------------------ |
| `GET`  | `/ideas`                    | List all ideas                             |
| `POST` | `/ideas`                    | Create a single idea                       |
| `POST` | `/ideas/bulk`               | Create multiple ideas at once              |
| `POST` | `/ideas/update`             | Update an idea                             |
| `POST` | `/ideas/delete`             | Delete a single idea                       |
| `POST` | `/ideas/delete/bulk`        | Delete multiple ideas by ID                |
| `POST` | `/ideas/delete/all`         | Delete all ideas                           |
| `GET`  | `/topics/assign`            | Run topic assignment for unprocessed ideas |
| `GET`  | `/semantic-search?query=…` | Semantic search across ideas               |
| `GET`  | `/refine-ideas`             | Refine raw ideas using AI                  |
