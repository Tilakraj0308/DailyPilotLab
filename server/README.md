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
# JWT Secret from Supabase → Project Settings → API (label: JWT Secret). Not the anon key.
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# ── Connectors (Google Calendar / Google Tasks / Gmail) ──────────────────────
# Google: same `GOOGLE_CONNECTOR_CLIENT_*` Web client; add Calendar, Tasks, and Gmail redirect URIs in Google Cloud.
# Shared: `CONNECTOR_ENCRYPTION_SECRET`, `CONNECTOR_OAUTH_STATE_TTL_SECONDS`, `FRONTEND_CONNECTOR_BASE_URL`.

# ── Tuning knobs (leave defaults unless you know what you're changing) ────────
TOPIC_ASSIGNMENT_THRESHOLD_SIMILARITY=0.48
TOPIC_SIMILARITY_THRESHOLD=0.2
IDEA_SIMILARITY_THRESHOLD=0.4
TOPIC_AUTO_REFINEMENT_THRESHOLD=3
BULK_IDEA_INSERTION_THRESHOLD=4
```

> **Never commit `.env`** — it is already listed in `.gitignore`.

If the app shows `{"detail":"Invalid token"}` when calling authenticated routes (for example **Connectors → Connect Google Calendar**), the server cannot verify the Supabase session JWT. This is **not** caused by the Google connector redirect URI.

- **HS256 (legacy JWT secret):** set **`SUPABASE_JWT_SECRET`** to the exact **JWT Secret** from Supabase → **Project Settings → API**.
- **ES256 / JWT Signing Keys (common on newer projects):** HS256 verification will always fail. Set **`SUPABASE_URL`** in `server/.env` to the same value as **`EXPO_PUBLIC_SUPABASE_URL`** in the app (for example `https://<ref>.supabase.co`). The API verifies tokens using **`/auth/v1/.well-known/jwks.json`**.

Restart the API after changing `.env`.

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
| `20260415_connectors_foundation.sql`   | Connector providers, `user_connectors`, encrypted tokens, OAuth state sessions                                    |
| `20260417_google_tasks_connector_resources.sql` | Seeds `google_tasks` provider; `user_connector_resources` for selected task list metadata              |
| `20260418_notion_connector_provider.sql`        | Seeds `notion` provider row                                                                           |
| `20260418150000_gmail_connector_provider.sql`   | Seeds `gmail` provider row (timestamp distinct from `20260418_notion_*`; see note below)               |

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

### Connectors and Google consent

Calendar, Tasks, and **Gmail** use separate provider keys but the **same** `GOOGLE_CONNECTOR_CLIENT_ID`. Register **Gmail API** in Google Cloud (Library) and add **`GOOGLE_GMAIL_CONNECTOR_REDIRECT_URI`** (for example `http://127.0.0.1:8000/connectors/gmail/callback`) alongside the Calendar and Tasks callback URIs on the OAuth Web client. Authorization URLs omit `prompt=consent` by default so Google can offer **incremental** consent when you connect additional Google products; `prompt=consent` is added only when the connector row is `reauth_required` or `error` (see `should_force_google_oauth_consent_prompt` in [`connectors/db.py`](connectors/db.py)). When the Supabase JWT includes `email`, it is sent as Google’s **`login_hint`** so Google can prefill / skip the account chooser when that matches the user’s Google session (not guaranteed if multiple accounts or policies require a picker).

**Database:** every connector `provider_key` must exist in `public.connector_providers` before OAuth starts (FK on `oauth_state_sessions`). If `POST /connectors/gmail/start` returns **503** mentioning `connector_providers`, apply migrations so `20260418150000_gmail_connector_provider.sql` has run (`npx supabase db push`), or insert the `gmail` row manually.

**Migration timestamps:** use a **unique** `YYYYMMDDHHMMSS` prefix per file. Two files sharing the same eight-digit day prefix (e.g. `20260418_foo.sql` and `20260418_bar.sql`) map to the same `schema_migrations.version` and **`db push` will fail** with a duplicate key on `schema_migrations`.

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
| `GET`  | `/auth/profile`             | Sync Supabase user into `public.users`     |
| `GET`  | `/connectors`               | List connector status per provider (auth)   |
| `POST` | `/connectors/{provider}/start` | Start OAuth (`google_calendar` \| `google_tasks` \| `gmail`) — returns `authorization_url` (auth) |
| `GET`  | `/connectors/{provider}/callback` | OAuth redirect — **public** (Google; Gmail uses `/connectors/gmail/callback`)   |
| `POST` | `/connectors/{provider}/disconnect` | Revoke tokens and disconnect (auth)   |
| `GET`  | `/connectors/gmail/priority` | Priority-oriented Gmail thread summaries for the connected account (auth) |
| `GET`  | `/connectors/gmail/threads/{thread_id}` | Gmail thread detail (auth) |
| `POST` | `/connectors/gmail/drafts` | Create a Gmail draft (auth) |
| `POST` | `/connectors/gmail/drafts/{draft_id}/send` | Send an existing draft after user approval (auth) |
| `POST` | `/connectors/gmail/ai/suggest-reply` | JSON `{ "thread_id" }` — AI reply draft (`subject` optional, `body_text`) from thread context (auth) |
| `GET`  | `/connectors/google_tasks/lists` | Task lists for the connected account (auth) |
| `POST` | `/connectors/google_tasks/select-list` | Persist one selected task list (`task_list_id`, optional `task_list_title`) (auth) |
| `GET`  | `/connectors/google_tasks/tasks` | Tasks in the selected list (`show_completed` query) (auth) |
| `POST` | `/connectors/google_tasks/tasks` | Create task in selected list (auth) |
| `PATCH` | `/connectors/google_tasks/tasks/{task_id}` | Update task (e.g. `completed`) (auth) |
| `DELETE` | `/connectors/google_tasks/tasks/{task_id}` | Delete task (auth) |
| `POST` | `/chat/stream`              | SSE chat (auth)                            |
