# Gmail Connector V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `gmail` connector that matches the approved spec: connect via Google OAuth, show a priority-focused inbox slice in the app, create drafts/reply drafts, and only send after explicit user approval, with Gmail tools available to the AI under the existing connector permission model.

**Architecture:** Add `server/connectors/providers/gmail/` as a Google OAuth-backed provider (same lifecycle as Calendar/Tasks), centralize Gmail REST calls in `gmail_api.py`, expose narrow `TOOL_DEFINITIONS`, and add explicit FastAPI routes in `server/connectors/router.py` for the app UI (priority list, thread detail, draft create, approved send). Extend the Expo app with a dedicated Gmail screen + API client functions, reusing existing connector OAuth return handling.

**Tech Stack:** FastAPI + Pydantic v2 + `requests` (existing), Expo React Native + React Navigation (existing), Supabase migrations for `connector_providers` seeding, `uv` for Python deps, `pytest` for new automated tests.

---

## File map (what changes, at a glance)

**Create**
- `server/connectors/providers/gmail/__init__.py`
- `server/connectors/providers/gmail/connector.py`
- `server/connectors/providers/gmail/gmail_api.py`
- `server/connectors/providers/gmail/tools/__init__.py`
- `server/connectors/providers/gmail/tools/read.py`
- `server/connectors/providers/gmail/tools/create.py`
- `server/connectors/providers/gmail/tools/update.py`
- `supabase/migrations/20260418_gmail_connector_provider.sql`
- `server/tests/test_gmail_connector.py` (or `server/tests/connectors/test_gmail_connector.py` if you prefer nesting; keep imports stable)
- `app/src/connectors/GmailConnectorScreen.tsx`

**Modify**
- `server/connectors/providers/__init__.py` (register `gmail`)
- `server/connectors/router.py` (Gmail routes)
- `server/connectors/models.py` (Gmail request/response models)
- `server/pyproject.toml` + `server/uv.lock` (add `pytest` dev dependency)
- `server/README.md` (Gmail setup: enable API, scopes, redirect URI)
- `server/.env.example` (Gmail redirect env var + notes)
- `app/src/connectors/api.ts` (Gmail API client helpers)
- `app/src/connectors/ConnectorsSection.tsx` (Gmail card + success label)
- `app/src/connectors/ToolAccessScreen.tsx` (Gmail icon/title + permission toggles + entry button to Gmail screen)
- `app/App.tsx` (register `GmailConnector` stack screen)
- `app/README.md` (document Gmail connector UX + env expectations)

**Canonical spec**
- `docs/superpowers/specs/2026-04-18-gmail-connector-design.md`

---

## Gmail API contracts (lock these in implementation)

**Base URL**
- `https://gmail.googleapis.com/gmail/v1`

**OAuth scopes (v1 baseline)**
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.compose`
- `https://www.googleapis.com/auth/gmail.send`
- `openid`
- `https://www.googleapis.com/auth/userinfo.email`

**Priority query (deterministic)**
Use a single Gmail `q` string for v1, for example:
- `in:inbox newer_than:14d`

Implementation detail: request `messages` list with `labelIds=INBOX` plus `q`, then hydrate minimal fields per message for UI (`format=metadata`).

**Draft create**
- `POST /gmail/v1/users/me/drafts` with JSON body:
  - `message.threadId` set for reply drafts
  - `message.raw` as RFC822 bytes base64url-encoded (this is the standard Gmail API shape)

**Approved send**
- `POST /gmail/v1/users/me/drafts/send` with JSON body `{ "id": "<draftId>" }`

Do not use `users.messages.send` for v1 UI sends. Draft-send keeps the “human approved an existing draft object” invariant obvious in code and logs.

---

### Task 0: Baseline verification (prove the repo runs tests today)

**Files:**
- Read: `server/pyproject.toml`

- [ ] **Step 1: Confirm there is no pytest wiring yet**

Run:

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab/server
ls
```

Expected: you see `pyproject.toml`, `uv.lock`, and **no** `pytest.ini` / `tests/` tree yet.

- [ ] **Step 2: Commit**

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab
git status
```

Expected: clean or only the new plan/spec files depending on what you already staged.

---

### Task 1: Add pytest as a dev dependency (enables TDD for connectors)

**Files:**
- Modify: `server/pyproject.toml`
- Modify: `server/uv.lock`

- [ ] **Step 1: Add pytest**

Run:

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab/server
uv add --dev pytest
```

Expected: `pyproject.toml` includes a dev dependency group entry for `pytest`, and `uv.lock` updates.

- [ ] **Step 2: Verify pytest runs (even with zero tests yet)**

Run:

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab/server
uv run pytest -q
```

Expected: exit code `0` with a message like `no tests ran` (exact text may vary by pytest version).

- [ ] **Step 3: Commit**

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab
git add server/pyproject.toml server/uv.lock
git commit -m "chore(server): add pytest for connector tests"
```

---

### Task 2: Failing test — `gmail` must be registered like other providers

**Files:**
- Create: `server/tests/test_gmail_connector.py`

- [ ] **Step 1: Write the failing test**

Create `server/tests/test_gmail_connector.py`:

```python
from connectors.providers import PROVIDER_MAP


def test_gmail_provider_registered():
    assert "gmail" in PROVIDER_MAP
    connector_cls = PROVIDER_MAP["gmail"]
    inst = connector_cls()
    assert getattr(inst, "provider_key", None) == "gmail"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab/server
uv run pytest -q server/tests/test_gmail_connector.py::test_gmail_provider_registered
```

Expected: **FAIL** with `AssertionError` on `"gmail" in PROVIDER_MAP` (or import error if miswired).

- [ ] **Step 3: Commit the failing test**

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab
git add server/tests/test_gmail_connector.py
git commit -m "test(connectors): expect gmail provider registration"
```

---

### Task 3: Minimal backend wiring — provider package + registry + DB seed

**Files:**
- Create: `server/connectors/providers/gmail/__init__.py`
- Create: `server/connectors/providers/gmail/connector.py`
- Modify: `server/connectors/providers/__init__.py`
- Create: `supabase/migrations/20260418_gmail_connector_provider.sql`

- [ ] **Step 1: Implement `GmailConnector`**

Create `server/connectors/providers/gmail/connector.py`:

```python
"""Gmail — Google OAuth connector configuration."""

import os

from connectors.base_connector import GoogleOAuthConnector


def _normalize_redirect_uri(raw: str) -> str:
    u = raw.strip()
    if len(u) >= 2 and ((u[0] == u[-1] == '"') or (u[0] == u[-1] == "'")):
        u = u[1:-1].strip()
    return u.rstrip("/")


class GmailConnector(GoogleOAuthConnector):
    provider_key = "gmail"

    default_scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    def _redirect_uri(self) -> str:
        explicit = _normalize_redirect_uri(os.getenv("GOOGLE_GMAIL_CONNECTOR_REDIRECT_URI", ""))
        if explicit:
            return explicit

        cal = _normalize_redirect_uri(os.getenv("GOOGLE_CONNECTOR_REDIRECT_URI", ""))
        if cal and "google_calendar" in cal:
            return cal.replace("google_calendar", "gmail", 1)

        raise RuntimeError(
            "Set GOOGLE_GMAIL_CONNECTOR_REDIRECT_URI "
            "(e.g. http://127.0.0.1:8000/connectors/gmail/callback) "
            "or set GOOGLE_CONNECTOR_REDIRECT_URI with …/google_calendar/… so Gmail URL can be derived."
        )
```

Create `server/connectors/providers/gmail/__init__.py`:

```python
from .connector import GmailConnector

__all__ = ["GmailConnector"]
```

- [ ] **Step 2: Register provider**

Modify `server/connectors/providers/__init__.py` to import and map:

```python
from .gmail import GmailConnector

PROVIDER_MAP = {
    "google_calendar": CalendarConnector,
    "google_tasks": TasksConnector,
    "notion": NotionConnector,
    "gmail": GmailConnector,
}
```

- [ ] **Step 3: Seed provider row**

Create `supabase/migrations/20260418_gmail_connector_provider.sql`:

```sql
INSERT INTO public.connector_providers (provider_key, display_name)
VALUES ('gmail', 'Gmail')
ON CONFLICT (provider_key) DO NOTHING;
```

- [ ] **Step 4: Run the registration test**

Run:

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab/server
uv run pytest -q server/tests/test_gmail_connector.py::test_gmail_provider_registered
```

Expected: **PASS**

- [ ] **Step 5: Commit**

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab
git add server/connectors/providers/gmail server/connectors/providers/__init__.py supabase/migrations/20260418_gmail_connector_provider.sql
git commit -m "feat(connectors): register gmail provider"
```

---

### Task 4: `gmail_api.py` — centralized Gmail REST helpers (mockable)

**Files:**
- Create: `server/connectors/providers/gmail/gmail_api.py`

- [ ] **Step 1: Write a failing unit test for list_messages URL assembly**

Append to `server/tests/test_gmail_connector.py`:

```python
from unittest.mock import patch, Mock

from connectors.providers.gmail import gmail_api


@patch("connectors.providers.gmail.gmail_api.requests.get")
def test_list_inbox_messages_builds_expected_url(mock_get: Mock):
    mock_get.return_value = Mock(status_code=200, json=lambda: {"messages": []})

    gmail_api.list_inbox_messages(access_token="token", max_results=10, q="in:inbox")

    args, kwargs = mock_get.call_args
    assert args[0].startswith("https://gmail.googleapis.com/gmail/v1/users/me/messages")
    assert "maxResults=10" in args[0]
    assert "q=" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer token"
```

Run:

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab/server
uv run pytest -q server/tests/test_gmail_connector.py::test_list_inbox_messages_builds_expected_url
```

Expected: **FAIL** with `ModuleNotFoundError` or missing function.

- [ ] **Step 2: Implement `gmail_api.py`**

Create `server/connectors/providers/gmail/gmail_api.py`:

```python
from __future__ import annotations

import logging
import urllib.parse
from typing import Any

import requests

logger = logging.getLogger(__name__)

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def list_inbox_messages(*, access_token: str, max_results: int, q: str) -> dict[str, Any]:
    params = {
        "maxResults": str(max(1, min(50, int(max_results)))),
        "labelIds": "INBOX",
        "q": q,
    }
    url = f"{GMAIL_API_BASE}/users/me/messages?{urllib.parse.urlencode(params)}"
    r = requests.get(url, headers=_auth_headers(access_token), timeout=30)
    if r.status_code != 200:
        logger.warning("gmail list messages failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def get_thread(*, access_token: str, thread_id: str, format: str = "metadata") -> dict[str, Any]:
    tid = urllib.parse.quote(thread_id, safe="")
    params = urllib.parse.urlencode({"format": format})
    url = f"{GMAIL_API_BASE}/users/me/threads/{tid}?{params}"
    r = requests.get(url, headers=_auth_headers(access_token), timeout=45)
    if r.status_code != 200:
        logger.warning("gmail get thread failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def create_draft(*, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"{GMAIL_API_BASE}/users/me/drafts"
    r = requests.post(url, headers=_auth_headers(access_token), json=body, timeout=45)
    if r.status_code != 200:
        logger.warning("gmail create draft failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def send_draft(*, access_token: str, draft_id: str) -> dict[str, Any]:
    did = urllib.parse.quote(draft_id, safe="")
    url = f"{GMAIL_API_BASE}/users/me/drafts/send"
    r = requests.post(url, headers=_auth_headers(access_token), json={"id": did}, timeout=45)
    if r.status_code != 200:
        logger.warning("gmail send draft failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()
```

- [ ] **Step 3: Re-run the unit test**

Run:

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab/server
uv run pytest -q server/tests/test_gmail_connector.py::test_list_inbox_messages_builds_expected_url
```

Expected: **PASS**

- [ ] **Step 4: Commit**

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab
git add server/connectors/providers/gmail/gmail_api.py server/tests/test_gmail_connector.py
git commit -m "feat(connectors): add gmail_api client helpers"
```

---

### Task 5: FastAPI models for Gmail routes

**Files:**
- Modify: `server/connectors/models.py`

- [ ] **Step 1: Add models**

Append to `server/connectors/models.py`:

```python
class GmailThreadSummaryOut(BaseModel):
    id: str
    snippet: str | None = None
    subject: str | None = None
    from_addr: str | None = None
    internal_date_ms: str | None = None
    label_ids: list[str] = Field(default_factory=list)


class GmailPriorityResponse(BaseModel):
    query: str
    items: list[GmailThreadSummaryOut]


class GmailDraftCreateRequest(BaseModel):
    thread_id: str | None = None
    to: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)
    subject: str
    body_text: str


class GmailDraftCreateResponse(BaseModel):
    draft_id: str
    message_id: str | None = None
    thread_id: str | None = None


class GmailDraftSendRequest(BaseModel):
    # Intentionally empty: sending is explicit by route + draft id path param
    pass
```

- [ ] **Step 2: Commit**

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab
git add server/connectors/models.py
git commit -m "feat(connectors): add gmail pydantic models"
```

---

### Task 6: Gmail routes — priority inbox + thread + draft + send

**Files:**
- Modify: `server/connectors/router.py`

Implementation guidance (keep it boring and explicit):
- Import `PROVIDER_MAP` usage pattern already in file.
- Import new models from `connectors.models`.
- Import `gmail_api`.
- Add helper functions in a small private section near the bottom of the file to normalize Gmail payloads for the UI.

**Suggested endpoints**
- `GET /connectors/gmail/priority`
- `GET /connectors/gmail/threads/{thread_id}`
- `POST /connectors/gmail/drafts`
- `POST /connectors/gmail/drafts/{draft_id}/send`

**Draft raw message construction**
Implement a helper in `router.py` (or `gmail_api.py` if you want purity) that builds RFC822:

```python
import base64
import email.message


def _build_rfc822_text_email(*, to: list[str], cc: list[str], bcc: list[str], subject: str, body_text: str) -> str:
    msg = email.message.EmailMessage()
    if to:
        msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)
    msg["Subject"] = subject
    msg.set_content(body_text)
    return msg.as_string()


def _gmail_raw_from_rfc822(rfc822: str) -> dict[str, str]:
    raw = base64.urlsafe_b64encode(rfc822.encode("utf-8")).decode("ascii").rstrip("=")
    return {"raw": raw}
```

**Priority list algorithm (v1)**
1. `list_inbox_messages` with `q="in:inbox newer_than:14d"` and `max_results=30`
2. For each message id, call metadata fetch (`format=metadata`) if needed, OR use `fields` parameter if you choose to optimize later
3. Group by `threadId` and return unique threads (cap final list to ~15)

Keep v1 simple even if it costs extra HTTP calls.

- [ ] **Step 1: Add a smoke test calling the FastAPI app (optional but recommended)**

If you want speed, skip full app tests until Task 8; otherwise add `httpx` dev dependency and use `fastapi.testclient`.

Minimal alternative without new deps:
- Keep coverage at unit level for `gmail_api` and tool routing.

- [ ] **Step 2: Manual API check**

Run server:

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab/server
uv sync
.venv/bin/fastapi dev server.py --host 0.0.0.0
```

Then with a real user JWT and connected Gmail account, call:

```bash
curl -sS -H "Authorization: Bearer <SUPABASE_ACCESS_TOKEN>" \
  http://127.0.0.1:8000/connectors/gmail/priority | head
```

Expected: JSON with `items` array (may be empty if inbox empty).

- [ ] **Step 3: Commit**

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab
git add server/connectors/router.py
git commit -m "feat(connectors): add gmail http routes"
```

---

### Task 7: Gmail tools — registry-compatible `TOOL_DEFINITIONS` + `execute()`

**Files:**
- Create: `server/connectors/providers/gmail/tools/__init__.py`
- Create: `server/connectors/providers/gmail/tools/read.py`
- Create: `server/connectors/providers/gmail/tools/create.py`
- Create: `server/connectors/providers/gmail/tools/update.py`

**Tool names (v1)**
- Read:
  - `gmail_list_priority_threads`
  - `gmail_get_thread`
- Create:
  - `gmail_create_draft`
- Update:
  - `gmail_send_draft`

**`execute()` signature must match existing providers**

Pattern (copy from Notion):

```python
def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    ...
```

**Permission mapping (explicit, because CRUD labels lie for Gmail)**
- `gmail_list_priority_threads`, `gmail_get_thread` → `crud_type="read"`
- `gmail_create_draft` → `crud_type="create"`
- `gmail_send_draft` → `crud_type="update"`

This matches the approved spec’s compromise: send is not `create`.

- [ ] **Step 1: Add a routing test for tools**

Append to `server/tests/test_gmail_connector.py`:

```python
from connectors.providers.gmail.tools import read as gmail_read


def test_gmail_read_tool_routes():
    class FakeConnector:
        def ensure_access_token(self, user_id: str) -> str:  # noqa: ARG002
            return "token"

    # This test should fail until execute() exists and routes correctly.
    try:
        gmail_read.execute(FakeConnector(), "user", "gmail_list_priority_threads", {})
    except ValueError as e:
        assert "Unknown" in str(e)
```

Adjust after implementation to assert a dict response by mocking `gmail_api`.

- [ ] **Step 2: Implement tools**

Implement `read.py` using `gmail_api.list_inbox_messages` + `gmail_api.get_thread`.

Implement `create.py` to build RFC822 and call `gmail_api.create_draft` with:

```python
body = {"message": {"raw": raw, "threadId": thread_id}}  # threadId optional
```

Implement `update.py` for `gmail_send_draft`.

Aggregate in `tools/__init__.py`:

```python
from .create import TOOL_DEFINITIONS as _create
from .read import TOOL_DEFINITIONS as _read
from .update import TOOL_DEFINITIONS as _update

TOOL_DEFINITIONS = [*_read, *_create, *_update]
```

- [ ] **Step 3: Run full pytest**

Run:

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab/server
uv run pytest -q
```

Expected: **PASS**

- [ ] **Step 4: Commit**

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab
git add server/connectors/providers/gmail/tools server/tests/test_gmail_connector.py
git commit -m "feat(connectors): add gmail tool definitions"
```

---

### Task 8: Docs + env example + README tables (so you do not rediscover setup pain)

**Files:**
- Modify: `server/.env.example`
- Modify: `server/README.md`
- Modify: `app/README.md`

- [ ] **Step 1: Extend `server/.env.example`**

Add:

```ini
# Gmail connector callback — must be registered on the SAME Google OAuth Web client as Calendar/Tasks.
GOOGLE_GMAIL_CONNECTOR_REDIRECT_URI=http://127.0.0.1:8000/connectors/gmail/callback
```

Add a short comment block that Gmail requires **Gmail API** enabled in Google Cloud.

- [ ] **Step 2: Update `server/README.md`**

Update the connectors section to list `gmail` alongside others, and document:
- redirect URI path must be `/connectors/gmail/callback`
- scopes list (same as spec)
- incremental auth behavior already implemented in `GoogleOAuthConnector`

- [ ] **Step 3: Update `app/README.md`**

Extend the connectors section to include Gmail and describe:
- connect card
- Tool Access permissions meaning for Gmail
- Gmail screen for priority slice + draft review + explicit send

- [ ] **Step 4: Commit**

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab
git add server/.env.example server/README.md app/README.md
git commit -m "docs: document gmail connector setup"
```

---

### Task 9: Expo app — API client + navigation + UI screen

**Files:**
- Modify: `app/src/connectors/api.ts`
- Modify: `app/src/connectors/ConnectorsSection.tsx`
- Modify: `app/src/connectors/ToolAccessScreen.tsx`
- Create: `app/src/connectors/GmailConnectorScreen.tsx`
- Modify: `app/App.tsx`

- [ ] **Step 1: Add typed client helpers**

In `app/src/connectors/api.ts`, add:

```ts
export const GMAIL_PROVIDER = "gmail";

export type GmailThreadSummary = {
  id: string;
  snippet?: string | null;
  subject?: string | null;
  from_addr?: string | null;
  internal_date_ms?: string | null;
  label_ids: string[];
};

export async function fetchGmailPriority(accessToken: string): Promise<{
  query: string;
  items: GmailThreadSummary[];
}> {
  const res = await fetch(`${getApiUrl()}/connectors/gmail/priority`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to load Gmail priority inbox (${res.status})`);
  }
  return res.json();
}
```

Add functions for:
- `fetchGmailThread(accessToken, threadId)`
- `createGmailDraft(accessToken, body)`
- `sendGmailDraft(accessToken, draftId)`

- [ ] **Step 2: Register navigation screen**

In `app/App.tsx`, import `GmailConnectorScreen` and add:

```tsx
<Stack.Screen name="GmailConnector" component={GmailConnectorScreen} />
```

- [ ] **Step 3: Build `GmailConnectorScreen.tsx`**

Minimum UX requirements:
- list from `fetchGmailPriority`
- tap thread → loads thread detail endpoint
- text box for draft body
- button: **Create draft**
- after draft id returned, show **Send** button disabled until user taps **I reviewed this draft** switch
- `Send` calls `sendGmailDraft`

This is intentionally clunky. Clunky beats deceptive.

- [ ] **Step 4: Wire entry points**
- `ConnectorsSection.tsx`: add a fourth `ConnectorCard` for Gmail; navigate to `GmailConnector` when connected (same pattern as ToolAccess navigation).
- `ToolAccessScreen.tsx`:
  - add Gmail to `PROVIDER_INFO`
  - extend permission toggle gating to include `gmail`
  - add a button: “Open Gmail priority inbox” → `navigation.navigate("GmailConnector")`

- [ ] **Step 5: Typecheck / lint (pick what your repo already uses)**

Run from `app/`:

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab/app
npm test --silent
```

If there is no test script, run:

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab/app
npx tsc -p tsconfig.json --noEmit
```

Expected: **PASS** (or fix TS errors until clean).

- [ ] **Step 6: Commit**

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab
git add app/src/connectors app/App.tsx
git commit -m "feat(app): add gmail connector screen and api client"
```

---

### Task 10: Database migration application (human step, still part of “done”)

**Files:**
- None (CLI)

- [ ] **Step 1: Push migration**

Run:

```bash
cd /home/bharat/vscode/DailyPilotLab/DailyPilotLab
npx supabase db push
```

Expected: migration applied; `connector_providers` contains `gmail`.

- [ ] **Step 2: Commit only if supabase generates artifacts**

If no files change, do not create an empty commit.

---

## Plan self-review (against the approved spec)

- **Priority slice:** covered by `/connectors/gmail/priority` + deterministic query string.
- **Thread detail:** covered by `/connectors/gmail/threads/{thread_id}`.
- **Draft-first compose:** covered by `/connectors/gmail/drafts`.
- **Human-confirmed send:** covered by separate `/drafts/{draft_id}/send` + UI gating.
- **Tools for AI:** covered by `connectors/providers/gmail/tools/*` with explicit names.
- **Permissions:** explicit mapping documented; UI must expose toggles for Gmail like other providers.
- **Docs/env:** covered in Task 8.

**Known gap you should accept or fix deliberately**
- “AI-assisted drafting” is not fully specified as an LLM endpoint in this plan. v1 can ship with **manual draft text** in the Gmail screen plus AI tools reading the thread, then add `POST /connectors/gmail/ai/suggest` later. If you want it in v1, add a new task that calls the existing chat/LLM stack with a strict prompt and schema — do not improvise in-router string prompts.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-18-gmail-connector.md`.

**Two execution options:**

1. **Subagent-driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration  
2. **Inline execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?