## Context

The active task workflow is implemented in `services/demo_workspace.py`, persisted through the existing snapshot/SQLite infrastructure, and rendered by `logitrack_studio.html`. Tasks already store the fields needed for the course handoff (`assignee_username`, `assignee_name`, `submitted_at`, `validated_at`, `approved_at`, and `activity_log`), so this change does not require a new model or workflow status.

Two boundaries currently fail to align. The browser composer sends only a free-text assignee name even though Field authorization compares the authenticated username with `Task.assignee_username`. The workflow service also accepts structural Field edits and out-of-order MEAL or manager decisions. Project membership is already canonical in `Project.team_assignments`, with user identity and organization ownership available from the existing account records.

The implementation must preserve the current `/v1/demo/tasks` routes, response fields, JSON/SQLite persistence, role permissions, and approved Programme Manager Portfolio and Workplan presentation architecture. See `proposal.md` for motivation and `specs/operational-task-workflow/spec.md` for observable requirements.

## Goals / Non-Goals

**Goals:**

- Make canonical project membership the source of truth for task assignment.
- Enforce the existing Field -> MEAL -> Programme Manager sequence in the backend before any mutation is persisted.
- Represent the MEAL-complete/manager-pending checkpoint with `status=pending_validation` plus `validated_at`, without adding a status.
- Keep role-specific UI actions and queues consistent with the same backend predicates.
- Prove the complete README demonstration and its rejection paths through isolated automated tests.

**Non-Goals:**

- Redesigning Portfolio, Workplan, the task drawer, navigation, or other role workspaces.
- Adding workflow states, changing permissions, migrating stored tasks, or reseeding demo data.
- Changing project, indicator, reporting, logical-framework, notification, or administration behavior.
- Introducing a new task repository, frontend framework, dependency, or API version.

## Decisions

### 1. Resolve assignees from project membership in the workflow service

`DemoWorkspaceService.create_task` will accept a canonical assignee identifier already supported by the task contract, resolve it to an active `UserAccount`, and verify that the user belongs to the project's organization and has an active `ProjectTeamAssignment` for that project. The service will write `assignee_username`, `assignee_name`, and `owner` from the resolved account and will ignore any conflicting display identity supplied by the client.

This keeps identity validation authoritative in the backend and preserves existing task fields and IDs. Using a free-text name was rejected because it cannot support authorization. Creating a new assignee model or replacing usernames with user IDs was rejected because it would require a broader migration and would break the current ownership checks.

### 2. Add eligible assignees to the authorized workplan payload

`project_workplan_snapshot` will add an `eligible_assignees` collection derived from active project assignments joined to active, same-organization users. Each item will expose only the identity and role metadata needed by the task composer. The existing response fields remain unchanged.

The composer will render this collection as a project-member selector and send the selected canonical username. This avoids depending on `/v1/admin/projects`, which is an administration/configuration surface, and avoids loading organization-wide users into the operational Workplan. Reusing the current free-text input was rejected because it perpetuates the broken identity contract.

### 3. Centralize workflow guards before mutation

Small service-level predicates will validate actor scope, allowed fields, current state, and decision before changing the task. All validation will occur before task fields, history, audit events, or persistence are touched.

The transition contract is:

| Actor/action | Required current state | Result |
| --- | --- | --- |
| Assigned Field starts work | `not_started` | `in_progress` |
| Assigned Field updates execution | `not_started`, `in_progress`, `overdue`, or `escalated` | State retained except existing overdue normalization |
| Assigned Field submits | `in_progress`, `overdue`, or `escalated` | `pending_validation`, set `submitted_at` |
| MEAL validates | unvalidated `pending_validation` submission | retain `pending_validation`, set `validated_at` |
| MEAL returns | unvalidated `pending_validation` submission | `in_progress`, retain assignee and history |
| Programme Manager approves | `pending_validation` with `validated_at` | `completed`, 100% progress, set `approved_at` |

Field payloads will be checked against an execution-only allowlist. Assignment, deadline, priority, category, linked indicator, project/organization identity, and arbitrary status changes will be rejected atomically for Field actors. Existing broader management permissions remain unchanged except that every workflow transition must satisfy its state prerequisite.

Alternatives considered were frontend-only guards and separate endpoints per transition. Frontend-only enforcement is not an authorization boundary, while new routes are unnecessary for this checkpoint because the existing update and validation routes can express the approved workflow compatibly.

### 4. Derive queue and action posture from status plus timestamps

The frontend will use the same two-step interpretation everywhere:

- MEAL review required: `status === pending_validation` and `validated_at` is empty.
- Manager approval required: `status === pending_validation` and `validated_at` is present and `approved_at` is empty.
- Complete: existing completed status or `approved_at` according to the current display helpers.

The validation inbox and Validate/Return actions will exclude already validated tasks. Programme Manager approval actions will appear only after `validated_at`, and the existing task detail surface will state that MEAL validation is complete and final approval is pending. This is a state-derivation correction, not a visual redesign.

### 5. Preserve existing persistence and audit mechanisms

No schema change is needed because all required identity, checkpoint, and history fields already serialize. Successful operations will continue through the existing task activity log, audit-event dependency, and `save_data` path. Rejected operations will fail before those calls, preventing success history or partial persistence.

The workflow integration test will reload the configured test datastore between role handoffs to prove persistence rather than relying only on an in-memory object.

### 6. Test the contract at service, HTTP, and UI-boundary levels

Focused service and FastAPI tests will cover canonical assignment, role authorization, every accepted transition, out-of-order rejection, audit/history, and persistence. Existing workflow, role-integrity, reporting, and UI suites remain regression gates. Frontend tests will verify selector wiring and the predicates controlling MEAL and manager actions; the complete browser path remains a manual course-demo check where browser automation is unavailable.

## Risks / Trade-offs

- **Legacy tasks with an empty or noncanonical `assignee_username` cannot be mutated by a Field user** -> Do not guess or backfill identity; retain manager-authorized correction paths and guarantee canonical identity for newly created tasks.
- **Adding assignee metadata to the workplan payload slightly increases its size** -> Return only active project members and the minimal fields required by the composer.
- **Stricter transition guards may reject calls that previously succeeded** -> Treat those calls as invalid behavior, preserve response shapes for valid calls, and add explicit rejection tests.
- **Frontend and backend predicates could drift later** -> Keep backend checks authoritative and cover the UI predicates with targeted structural/behavioral tests.
- **A task returned by MEAL retains prior submission history** -> Preserve the timestamp and activity trail as historical evidence; eligibility for a new MEAL review is governed by the new submission cycle and an empty current validation checkpoint.

## Migration Plan

1. Add service helpers and the additive `eligible_assignees` workplan field without altering existing fields.
2. Harden create, update, and validation operations with pre-mutation guards.
3. Wire the existing composer and workflow controls to the canonical identifier and checkpoint predicates.
4. Run focused workflow tests, then the complete regression suite and the manual authenticated role handoff.

No datastore migration or reseed is required. Existing snapshots continue to load because the task model is unchanged. Rollback consists of reverting the service and frontend changes; no persisted schema cleanup is necessary.
