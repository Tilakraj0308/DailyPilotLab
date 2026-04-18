# Active Context — DailyPilotLab

> **Last Updated**: 2026-04-18

## Current Focus
- Notion connector shipped: backend `NotionConnector`, page CRUD tools, app card + Tool Access, docs + env (`NOTION_*`).
- Next: run `npx supabase db push` if the remote DB does not yet have `20260418_notion_connector_provider.sql`.

## Recent Sessions
- **2026-04-18**: Notion connector — `GoogleOAuthConnector` split from generic naming, `oauth_common.py`, Notion OAuth + tools (`search_notion_pages`, `create_notion_page`, `update_notion_page`, `archive_notion_page`), UI + README + Memory Bank updates.
- **2026-03-18**: Created comprehensive API flow deep-dive analysis. Created `.notes/` Memory Bank structure.
- **2026-03-16**: Initial codebase walkthrough — created `walkthrough.md` covering all endpoints, DB schema, and LLM integration.
- **2026-03-13**: Implemented query duplication check in `widget_knowledge_servlet`.
- **2026-03-12**: Fixed KPI diff logic, refined API tester UI, resolved CORS issues.

## Agent / editor context (repo standard)

- Root **`AGENTS.md`** — commands, repo map, link to `.notes/`.
- **`.cursor/rules/*.mdc`** — always-on workflow + scoped server/app rules.
- **`tasks/todo.md`** / **`tasks/lessons.md`** — multi-step tracking and post-correction patterns.
- Nested **`server/AGENTS.md`** and **`app/AGENTS.md`** when working only in those packages.

## Open questions / next steps
- [ ] Apply Supabase migration for `notion` provider row on any environment that lacks it
- [ ] Consider adding error handling improvements (many endpoints return 200 even on errors)
- [ ] Evaluate whether `trait` table needs an API for direct read/query
