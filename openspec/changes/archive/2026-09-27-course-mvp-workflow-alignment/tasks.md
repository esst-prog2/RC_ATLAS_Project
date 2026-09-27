## 1. Regression Baseline and Test Harness

- [x] 1.1 Run the complete existing automated suite plus the focused Programme Manager UI, workflow, role-permission, and reporting tests; record the passing baseline before implementation and stop on any unexplained pre-existing failure.
- [x] 1.2 Add isolated workflow test fixtures that use a temporary datastore and authenticated demo-role clients; verify tests can reload persisted state without reading or changing the local demo workspace.

## 2. Canonical Task Assignment

- [x] 2.1 Add a `DemoWorkspaceService` assignee resolver that accepts the canonical username, joins it to an active same-organization user and active project assignment, and derives display identity; verify focused tests accept Aline and reject unknown, inactive, cross-organization, and non-member users without persisting a task or success audit event.
- [x] 2.2 Add the minimal `eligible_assignees` collection to `project_workplan_snapshot`; verify response-contract tests prove it is project- and organization-scoped while all existing workplan fields remain unchanged.
- [x] 2.3 Replace the task composer's free-text assignee value with the eligible project-member selector and submit the canonical username; verify Studio UI tests cover localized labels, selection wiring, and the absence of a client-trusted display identity.
- [x] 2.4 Harden `create_task` to persist `assignee_username`, `assignee_name`, and `owner` from the resolved account; verify a conflicting supplied display name cannot override the canonical user and the task begins in `not_started`.

## 3. Field Execution Authorization

- [x] 3.1 Validate Field update payloads against an execution-only allowlist before mutation; verify assignment, deadline, priority, category, indicator, project/organization, and arbitrary status changes return an authorization error and leave every task field, history entry, and audit event unchanged.
- [x] 3.2 Enforce canonical assignee scope and the allowed start/update/submit states in `update_task`; verify Aline can start, update progress, add evidence/comments, and submit her own eligible task but cannot mutate another user's, pending, or completed task.
- [x] 3.3 Preserve existing manager-authorized task-management behavior outside the Field restrictions; verify focused tests cover valid Programme Manager updates without weakening the Field ownership checks.

## 4. MEAL Review and Final Approval

- [x] 4.1 Guard MEAL validation and return decisions so they accept only an unvalidated `pending_validation` submission; verify validation records `validated_at` without changing the status, return restores `in_progress` with the assignee intact, and repeated or out-of-order decisions are rejected atomically.
- [x] 4.2 Guard Programme Manager approval so it requires `pending_validation` plus `validated_at`; verify approval records `approved_at`, sets `completed` and 100 percent progress, preserves validation history, and pre-validation approval is rejected without side effects.
- [x] 4.3 Align Studio queue, posture, and action predicates with the two checkpoints; verify UI tests show Validate/Return only before `validated_at`, remove validated tasks from the MEAL inbox, and show Programme Managers “validated by MEAL, awaiting final approval” with Approve only after validation.

## 5. Audit and Persistence

- [x] 5.1 Record authenticated actor, task/project identifiers, transition outcome, and timestamp through the existing task history and audit mechanisms for assignment, Field update/submission, MEAL validation/return, and manager approval; verify chronological history and that rejected operations emit no successful workflow event.
- [x] 5.2 Add a persistence regression covering logout/reload boundaries between Teresa, Aline, Raimundo, and Teresa; verify canonical ownership, deadline, progress, checkpoint timestamps, final completion, and history survive the configured JSON/SQLite save-load path.

## 6. MVP Integration and Regression Gate

- [x] 6.1 Add an authenticated HTTP integration test for the README demonstration: Teresa assigns “Finalize Buzi monitoring report” to Aline, Aline updates and submits it, Raimundo validates it, and Teresa performs final approval; verify existing route paths and response fields are used throughout.
- [x] 6.2 Run the complete automated suite and all focused workflow, permission, UI, reporting, indicator, logical-framework, Portfolio, and Workplan regressions; verify no previously passing test fails and no existing test is weakened to accommodate a regression.
- [x] 6.3 Perform the local browser course-demo handoff across the four authenticated sessions; verify Teresa sees the post-MEAL final-approval posture, invalid actions are unavailable, state survives reload, and the approved Portfolio/Workplan layout has no visual or containment regression.
