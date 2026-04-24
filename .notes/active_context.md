# Active Context — DailyPilotLab

> **Last Updated**: 2026-04-23

## Current Focus
- Main rebase alignment for agent-first chat is complete, including connector/auth contract parity and verification closure.
- Current focus is integration handoff: decide PR/merge path and watch first runtime window after deploy.

## Recent Sessions
- **2026-04-23**: Agent-first chat Task 6 — ran target suite (`test_agent_chat_db.py`, `test_chat_summary_windows.py`, `test_agent_chat_routes.py`), ran smoke regressions (`test_gmail_routes.py`, `test_gmail_tools.py` as substitution for missing `test_chat_tool_schema.py`), updated feature spec + memory bank.
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
- [ ] Open PR or merge locally for the rebased `feat/agent-first-chat-integration` branch.
- [ ] Monitor connector and summary runtime behavior after deployment.
- [ ] Begin custom-agent UI integration workstream.
