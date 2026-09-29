## Why

Manual browser acceptance exposed two pre-existing defects that block the canonical task Golden Journey and one persistence-ordering defect that can invalidate a newly issued login token after an unrelated relational projection failure. RC Atlas needs a narrow reliability correction that restores the existing workflow while preserving the canonical snapshot as the authoritative store.

## What Changes

- Add a focused task-drawer handoff that closes the drawer, navigates to Workplan, and targets the selected task's existing authorized workflow controls without duplicating workflow authorization.
- Make default project coordination activity resolution idempotent and tenant/project safe when task creation omits `activity_id`; reject duplicate, foreign, or structurally incompatible stable-ID states without partial mutation.
- Preserve present canonical repository-backed collections during hydration, including explicitly empty collections, and allow repository data only as a narrowly defined legacy backfill when the canonical key is genuinely absent.
- Isolate repository-domain synchronization from failures in the broader derived relational projection while retaining truthful diagnostics and canonical-commit semantics.
- Provide a guarded, dry-run-first local repair operation for the known duplicate coordination activity that preserves both browser-created tasks, validates all preconditions and postconditions, saves canonical state once, and rebuilds the derived projection.
- Add focused regression coverage and require a manual browser Golden Journey, including the MEAL return branch, before the change is accepted.

## Capabilities

### New Capabilities
- `canonical-projection-reliability`: Defines canonical snapshot hydration precedence, independent derived-domain synchronization, projection-failure diagnostics, and guarded repair of duplicate project coordination activities.

### Modified Capabilities
- `operational-task-workflow`: Adds reliable Field navigation from a task drawer to the existing Workplan controls and idempotent, ownership-safe default coordination activity placement during task creation without changing workflow states or permissions.

## Impact

- Expected implementation areas are `logitrack_studio.html`, `services/demo_workspace.py`, `migration/sync_helpers.py`, narrowly related composition-root synchronization wiring, a focused repair utility, and workflow/persistence/UI regression tests.
- The current `/v1` task and authentication contracts, token format, snapshot schema, relational schema, role/permission model, Workplan workflow rules, Logical Framework boundary, and tenant-security behavior remain unchanged.
- The current local canonical workspace will require a separately authorized, backup-protected repair after implementation; this proposal does not mutate persisted data.
- No new dependency, database technology, frontend framework, role, workflow status, or visual redesign is introduced.
