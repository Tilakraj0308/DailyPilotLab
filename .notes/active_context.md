# Active Context — DailyPilotLab

> **Last Updated**: 2026-04-27

## Current Focus
- Backend stabilization and standardization: DB pool, chat/connector backpressure, background worker telemetry, split `connectors/routes/` and helper modules, `chat_facade`, `IdeaService` filter hardening, docs + scoped `ruff` + tests.

## Recent Sessions
- **2026-04-27**: Implemented plan: `ThreadedConnectionPool`, lifespan pool close, `CHAT_STREAM_*` / `CONNECTOR_HTTP_*` semaphores, worker metrics + queue snapshots, connector route modules, helpers split + `helpers.py` re-exports, `GET /connectors/` + redirect, `pytest` + `test_ideas_service_filters`, `ruff` dev dep (F-only tree-wide; scoped check in AGENTS), app `npm run typecheck`.
- **2026-04-18**: Notion connector shipped (see progress).

## Agent / editor context (repo standard)
- Root **`AGENTS.md`** — commands, repo map, link to `.notes/`.
- **`.cursor/rules/*.mdc`** — always-on workflow + scoped server/app rules.
- **`tasks/todo.md`** / **`tasks/lessons.md`** — multi-step tracking and post-correction patterns.
- Nested **`server/AGENTS.md`** and **`app/AGENTS.md`** when working only in those packages.

## Open questions / next steps
- [ ] Widen `ruff` beyond pyflakes / expand paths as legacy files are cleaned
- [ ] Optional: separate worker process (vs in-process poller) for horizontal scaling
- [ ] Error handling improvements (endpoints returning 200 on errors)
