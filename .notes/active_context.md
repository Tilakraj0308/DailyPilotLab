# Active Context — DailyPilotLab

> **Last Updated**: 2026-03-18

## Current Focus
- Deep-diving into every API flow to understand mental flow, logical flow, interconnectedness, impact, and lifecycle placement
- Building a Memory Bank (`.notes/`) for long-term project context

## Recent Sessions
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
- [ ] Decide on what features or improvements to build next
- [ ] Consider adding error handling improvements (many endpoints return 200 even on errors)
- [ ] Evaluate whether `trait` table needs an API for direct read/query
