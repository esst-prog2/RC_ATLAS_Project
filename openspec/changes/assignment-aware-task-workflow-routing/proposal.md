## Why

RC Atlas currently treats Field Coordinator as the universal execution role even when a task is canonically assigned to a Programme Manager, MEAL Officer, or another eligible project member. This makes assignment contradict execution authorization and prevents legitimate assignees from completing their work.

## What Changes

- Make the canonical assignee, rather than a role label, the task's execution owner.
- Add four explicit review modes: `direct_completion`, `validation`, `approval`, and `validation_and_approval`; when creation omits the mode, use `validation_and_approval` as the application compatibility default.
- Require explicit capability-eligible validator and approver selections for review stages while enforcing separation of duties.
- Separate evidence from execution completion: `SUBMIT_EVIDENCE` governs evidence actions, while `evidence_required` alone gates whether evidence must exist and defaults to false for backward compatibility.
- Preserve the existing task status vocabulary by using review-stage metadata to distinguish validation from approval while a task remains `pending_validation`.
- Preserve the accepted Programme Manager to Field Coordinator to MEAL Officer to Programme Manager Golden Journey as a configured `validation_and_approval` workflow.
- Add conservative compatibility resolution and guarded backfill planning for legacy tasks that lack stable assignee IDs or explicit review policy fields.
- Align backend and Studio action eligibility with the intersection of tenant/project scope, task-specific identity, capability, policy, and current state.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `operational-task-workflow`: Generalize execution ownership from Field-only behavior to the canonical assignee and add explicit capability-based review routing, evidence gating, separation of duties, compatibility behavior, and policy-aware transitions.

## Impact

- Expected implementation areas are the task model and snapshot hydration/serialization in `LogiTrackRC v4.4.py`, `services/demo_workspace.py`, `api/demo_routes.py`, the current Studio task creation and workflow controls in `logitrack_studio.html`, demo seed compatibility, and focused API/service/UI regression tests.
- Existing `/v1/demo/tasks` route paths remain. Successful task responses gain additive routing fields, task creation accepts an optional policy override plus only the reviewer IDs applicable to its effective mode, and task execution/review decisions become policy-aware.
- Programme Manager's default permission bundle needs `UPDATE_TASK_PROGRESS` so a Programme Manager assignee can execute ordinary work. `SUBMIT_EVIDENCE` remains evidence-specific and is not added as a universal completion permission; assignee identity remains mandatory, so capability does not grant authority over another user's task.
- Existing snapshot structure remains authoritative and is extended additively. No relational schema, PostgreSQL, authentication, tenant-security, Logical Framework, Project Configuration, or frontend-framework redesign is introduced.
