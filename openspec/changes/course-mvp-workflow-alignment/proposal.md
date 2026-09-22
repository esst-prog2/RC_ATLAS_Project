## Why

RC Atlas already contains the course workflow, but the browser task composer does not persist the canonical assignee identity required by Field authorization, and backend transition checks do not yet guarantee the role sequence described in the README. The course MVP needs the existing workflow to be demonstrably correct, persistent, and reproducible without expanding the wider product scope.

## What Changes

- Assign manager-created tasks through an eligible project user so the existing canonical username and display name remain consistent.
- Restrict Field Coordinator mutations to assigned-task execution updates: progress, evidence notes, comments, starting work, and submission for validation.
- Enforce the existing workflow order: Field submission, MEAL validation or return, then Programme Manager approval and completion.
- Preserve pending_validation after MEAL validation while recording validated_at; do not introduce a new validated task status.
- Show Programme Managers that MEAL validation is complete and final approval is required, while removing validated items from the active MEAL validation queue.
- Preserve existing route shapes, task IDs, statuses, persistence, role permissions, Portfolio, Workplan presentation architecture, and all non-MVP RC Atlas modules.
- Add regression coverage for the README demonstration, including authorization failures, transition guards, role changes, and persistence.

## Capabilities

### New Capabilities

- operational-task-workflow: Canonical task assignment and the authenticated Programme Manager -> Field Coordinator -> MEAL Officer -> Programme Manager workflow required by the course MVP.

### Modified Capabilities

None.

## Impact

- Affected application areas: task assignment in logitrack_studio.html, task workflow rules in services/demo_workspace.py, and focused workflow/UI tests.
- Existing /v1/demo/tasks route paths and response shapes remain compatible; validation becomes stricter for invalid assignees, unauthorized fields, and out-of-order transitions.
- Existing JSON/SQLite persistence, demo identities, task statuses, role permissions, and broader RC Atlas functionality remain intact.
- No new dependency, migration, reseed, new workflow state, or visual redesign is required.
