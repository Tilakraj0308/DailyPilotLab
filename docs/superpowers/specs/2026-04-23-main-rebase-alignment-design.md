# Main Rebase Alignment Design

Date: 2026-04-23  
Status: Implemented

## Implementation Status
- [x] Feature branch rebased onto latest main
- [x] Connector permission schema/code contract aligned (`allowed_cruds`)
- [x] Agent-chat regressions verified post-rebase
- [x] Combined verification matrix passed

## 1) Context

Feature work for agent-first chat is being developed on `feat/agent-first-chat-integration` while `main` has moved ahead with connector/auth updates.

Observed runtime failure:

- `psycopg2.errors.UndefinedColumn: column "crud_type" does not exist`

Root cause:

- branch drift + schema contract drift between feature branch code and `main` migrations/connectors DB layer.

## 2) Goal

Align the feature branch with latest `main` so connector/auth DB contracts are consistent, while preserving and validating agent-first chat work.

## 3) Locked Decisions

- Alignment strategy: **rebase feature branch onto `main` first**.
- Conflict resolution rule: **main wins for connector/auth data contracts**, feature branch preserves agent-chat domain logic.
- Migration policy: **forward-only additive fixes**; do not rewrite shared historical migrations for already-applied environments.

## 4) Scope

In scope:

- branch alignment workflow
- conflict resolution policy
- migration consistency policy
- verification matrix and release gates
- rollback strategy if rebase quality degrades

Out of scope:

- new product behavior beyond alignment
- custom-agent UI buildout
- unrelated refactors

## 5) Architecture Boundaries During Alignment

Maintain backend layering:

- Route -> Manager -> Service -> DB

Alignment must not collapse boundaries by moving orchestration into routes or SQL logic into managers.

## 6) Execution Design

### Phase 1: Stabilize Current Feature State

1. Commit current feature branch changes (clean working tree required before rebase).
2. Create a safety backup branch pointer from current feature HEAD.

### Phase 2: Rebase onto Main

1. `git fetch origin`
2. `git rebase origin/main`
3. Resolve conflicts with strict priority:
   - connector/auth contract files follow `main`
   - agent-chat behavior reapplied on top
   - no drive-by formatting/refactor churn

### Phase 3: Migration Consistency Rules

1. Keep existing `main` migration history intact.
2. Keep agent-chat migration additive.
3. If post-rebase schema correction is required:
   - create a new migration file
   - do not mutate old shared migrations that may already be applied.

### Phase 4: Verification Matrix

Must pass before completion:

- Agent chat verification:
  - `tests/test_agent_chat_db.py`
  - `tests/test_chat_summary_windows.py`
  - `tests/test_agent_chat_routes.py`
- Connector regression verification:
  - `tests/test_gmail_routes.py`
  - `tests/test_gmail_tools.py`
- Runtime smoke:
  - start backend
  - exercise `/chat/stream`
  - confirm no `crud_type` path/column failures

## 7) Failure and Recovery Strategy

### If conflicts become ambiguous

- pause and resolve file-by-file using contract priority
- rerun focused tests after each conflict cluster

### If rebase quality drops

- execute `git rebase --abort`
- revert to pre-rebase safe point
- switch to merge-from-main fallback for this cycle

### If runtime still fails on schema contract

- treat as migration order/contract mismatch
- add forward migration for normalization
- re-verify query paths against actual DB columns

## 8) Exit Criteria

Alignment is complete when all are true:

- rebase completes cleanly
- verification matrix is green
- runtime smoke succeeds without connector permission schema errors
- feature branch remains architecture-consistent and merge-ready

## 9) Risks and Mitigations

- Risk: hidden connector contract conflicts after rebase.
  - Mitigation: prioritize `main` connector/auth schema contract and run connector regression suite.
- Risk: migration history corruption from in-place edits.
  - Mitigation: additive forward migrations only.
- Risk: incomplete confidence due environment variance.
  - Mitigation: run both test suite and live smoke on target environment before merge.
