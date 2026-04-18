# Gmail Connector V1 Design

## Goal
Add a new `gmail` connector to DailyPilotLab that lets the user connect Gmail through the existing connector architecture, review a light-weight priority inbox UI, generate AI-assisted drafts/replies, and explicitly approve sends before any message is sent.

## Non-Goals
- Building a full Gmail client inside the app
- Adding attachment upload or download flows
- Managing arbitrary labels, folders, or mailbox settings
- Letting the AI send mail without explicit user confirmation
- Designing a provider-neutral messaging abstraction for future mail providers

## Product Decisions
- **Connector shape:** Gmail is implemented as a normal connector provider under the existing connector system.
- **User capability:** Compose-enabled, but send is always human-confirmed.
- **UI level:** Light UI only, integrated into the existing connector/profile flow.
- **Inbox surface:** Priority-oriented view, not a full inbox browser.
- **Safety boundary:** Draft creation and sending are separate actions.

## Existing Project Constraints
- Backend connector lifecycle already exists under `server/connectors/`.
- Google Calendar and Google Tasks already share `GoogleOAuthConnector`.
- Notion proved the system can support non-Google provider-specific behavior without pretending everything is generic.
- The app already has connector cards, OAuth return handling, tool-access screens, permission toggles, and activity history.
- The current permission model is CRUD-based, which is imperfect for Gmail but acceptable for a narrow v1 if documented carefully.

## Recommended Architecture

### Backend
Create a new provider package at `server/connectors/providers/gmail/` with focused responsibilities:

- `connector.py`
  - Subclass the existing Google OAuth base.
  - Define Gmail-specific scopes.
  - Use its own redirect URI env var and callback path.
- `gmail_api.py`
  - Centralize Gmail REST requests and payload shaping.
  - Keep raw Gmail API details out of route handlers and tool modules.
- `tools/read.py`
  - List priority-focused threads/messages.
  - Search messages/threads.
  - Fetch thread detail for AI and UI consumption.
- `tools/create.py`
  - Create draft replies from an existing thread.
  - Create draft new messages from a simple compose flow.
- `tools/update.py`
  - Send an already-created draft after explicit user approval.
  - Support safe mailbox mutations such as mark read/unread and star/unstar.
- `tools/__init__.py`
  - Aggregate `TOOL_DEFINITIONS` for registry discovery.

Update shared backend integration points:

- `server/connectors/providers/__init__.py`
  - Register `gmail` in `PROVIDER_MAP`.
- `server/connectors/router.py`
  - Add Gmail-specific app endpoints for priority view, thread detail, draft creation, and approved send.
- `server/connectors/models.py`
  - Add Gmail request/response models for thread summaries, draft bodies, and send approval input.
- `server/connectors/db.py`
  - Reuse existing connector storage and history.
  - Do not add mailbox resource selection for v1.
- `supabase/migrations/20260418_gmail_connector_provider.sql`
  - Seed `gmail` in `public.connector_providers`.

### App
Extend the existing connector UI instead of inventing a new product area:

- Add `GMAIL_PROVIDER = "gmail"` to `app/src/connectors/api.ts`.
- Show Gmail in `ConnectorsSection.tsx` as a normal connector card.
- Reuse the current OAuth start/return flow.
- Add a Gmail-specific provider screen under the existing connector access flow with:
  - loading / empty / error states
  - priority thread list
  - thread detail view
  - draft review composer
  - explicit approve-and-send action
- Reuse existing permission and activity/history patterns where possible.

## Gmail Scopes
Use the smallest set that supports the selected v1 baseline:

- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.compose`
- `https://www.googleapis.com/auth/gmail.send`
- `openid`
- `https://www.googleapis.com/auth/userinfo.email`

If the team decides to include mark read/unread or star/unstar in the first implementation slice, add `https://www.googleapis.com/auth/gmail.modify`; otherwise leave those mailbox mutations out of v1 to keep the scope request narrower and the trust model cleaner.

## API Surface

### Provider-Specific App Endpoints
These exist for stable app behavior and should not be forced through generic tool execution:

- `GET /connectors/gmail/priority`
  - Return a capped set of priority-oriented messages or threads.
- `GET /connectors/gmail/threads/{thread_id}`
  - Return normalized thread detail for reading and drafting.
- `POST /connectors/gmail/drafts`
  - Create a draft new message or draft reply.
- `POST /connectors/gmail/drafts/{draft_id}/send`
  - Send only an already-created draft after explicit user approval.
- Optional safe mutation endpoints if included in v1:
  - mark read/unread
  - star/unstar

### Tool Definitions
Expose Gmail to the AI/tool system with narrow, explicit semantics:

- Read/list/search tools
- Fetch-thread-detail tool
- Create-draft / create-reply-draft tools
- Send-approved-draft tool
- Optional safe state update tools

Do not expose vague “manage inbox” tools in v1.

## Priority View Definition
The priority screen must be deterministic and understandable, not magic:

- prefer unread messages first
- prefer inbox / important signals available from Gmail metadata
- restrict to recent messages
- cap result size for performance and focus
- return enough metadata for triage:
  - sender
  - subject
  - snippet
  - timestamp
  - unread state

V1 should rely on Gmail-native metadata and query capabilities, not a custom AI ranking system.

## Draft and Send Lifecycle
This is the trust-critical workflow:

1. User opens a priority thread or taps a simple compose action.
2. AI suggests reply content or a new-message draft.
3. Backend creates a Gmail draft.
4. UI shows draft content clearly as a draft.
5. User explicitly approves sending.
6. App calls approved-send endpoint.
7. Backend sends through Gmail API and logs the result to connector history.

Rules:
- Draft creation must not imply send.
- UI copy must make draft status obvious.
- Send must be a distinct user action.
- Failures after approval must still preserve clear draft state or actionable error messaging.

## Permissions and Trust Model
The existing CRUD permission system is not a perfect semantic fit for Gmail:

- `read` fits listing/search/detail
- `create` can map to draft creation
- `update` can map to mailbox state changes and approved send
- `delete` should remain disabled by default and is probably unused in v1

This is acceptable for v1 only because the feature is intentionally narrow. The design should document that future high-risk connectors may require a richer permission model than CRUD.

## Data Model Choices
- Reuse existing connector tables and encrypted token storage.
- Reuse provider email / external account metadata fields for Gmail account display.
- Do not add `user_connector_resources` selection for Gmail in v1.
- Reuse connector history logging for draft creation, approved send, and safe mailbox mutations.

## Error Handling
Normalize Gmail/API failures into the current connector error patterns:

- invalid or expired token -> `reauth_required` when appropriate
- insufficient scope -> actionable connector error
- missing thread or draft -> 404-like app response shape
- Gmail upstream or quota failure -> 502-style connector/app response
- send failure after user approval -> preserve user trust with explicit UI error and no fake “sent” state

The app must distinguish:
- connector auth failure
- empty priority inbox
- upstream load error
- draft creation failure
- approved send failure

## Testing Strategy

### Backend
- provider registration test for `gmail`
- tool registry loading test
- OAuth redirect and scope configuration test
- draft creation test
- approved send separation test
- token refresh path test
- Gmail API error mapping tests

### App
- Gmail card rendering in connector list
- OAuth success and failure return handling
- priority view loading / empty / error / populated states
- thread detail rendering
- draft review state clarity
- approve-and-send explicit action path

### Manual Verification
- Connect Gmail from web
- Connect Gmail from native flow if supported in the current dev setup
- Load priority thread list
- Open a thread
- Create a reply draft
- Approve and send a draft
- Confirm activity/history entry appears

## Docs and Configuration
Update:

- `server/.env.example`
  - Gmail redirect env var and notes
- `server/README.md`
  - Gmail OAuth setup, scopes, redirect URI registration, API behavior
- `app/README.md`
  - Gmail connector setup and user flow
- `.notes/active_context.md`
  - note that Gmail connector planning/spec is now current work
- `.notes/progress.md` and `.notes/decisions.md`
  - only if implementation materially changes project state or introduces a durable architecture decision

## Risks
- Gmail scopes may push the connector beyond the clarity of the current CRUD permission UX.
- Send approval UX can easily become ambiguous if draft and send states are not visibly separated.
- Gmail payload normalization is more complex than Tasks or Notion and can create fragile UI contracts if shaped ad hoc.
- Overbuilding the UI would quietly turn this into a mail client project.

## V1 Acceptance Criteria
- User can connect Gmail through the existing connector system.
- Gmail appears in the app’s Integrations list.
- User can open a Gmail provider screen with a priority-focused thread list.
- User can open thread detail and request an AI-assisted draft.
- Backend creates drafts without sending them.
- User can explicitly approve and send a draft.
- Connector history records important Gmail actions.
- Docs and env examples explain how to configure the connector locally.

## Deferred Work
- attachments
- archive/delete-heavy mailbox management
- full inbox search UX
- label management UX
- mailbox resource selection
- provider-neutral message connector abstraction
- richer non-CRUD permission taxonomy
