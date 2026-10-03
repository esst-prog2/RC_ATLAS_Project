## Context

See proposal.md for motivation. The canonical task currently stores assignee username/name, status, timestamps, evidence placeholders, and history, but no stable assignee ID or review policy. `DemoWorkspaceService` permits normal updates broadly for non-Field roles, restricts assignee ownership only for Field Coordinators, rejects every non-Field submission, and hard-codes validation before approval. The Studio mirrors those role assumptions in `taskWorkflowActionButtons()`.

The accepted Golden Journey and current status vocabulary are constraints. Snapshot persistence remains authoritative; tenant-safe actor and project scope must precede task lookup and mutation; the current route family, Workplan, drawer handoff, Logical Framework boundary, and derived projection architecture remain in place.

## Goals / Non-Goals

**Goals:**
- Make task-specific identity, capability, policy, and state the shared backend/frontend authorization model.
- Represent four understandable review shapes without a generic workflow engine.
- Keep the accepted Golden Journey as one explicit configuration.
- Extend snapshots additively and provide deterministic compatibility for existing tasks.
- Keep failure paths atomic and tenant safe.

**Non-Goals:**
- Add arbitrary reviewer chains, parallel reviews, delegation, conditional routing, project-level workflow configuration, or a BPM designer.
- Add self-validation, self-approval, hidden manager override, post-start reassignment, or reviewer substitution.
- Redesign authentication, tenant security, notifications, audit architecture, persistence, Logical Framework, Project Configuration, Workplan layout, or task statuses.
- Introduce a relational migration or mutate legacy tasks during read hydration.

## Decisions

### 1. Persist one fixed review policy per task

Extend Task additively with:

- `assignee_user_id: str`
- `review_mode: str` with `direct_completion`, `validation`, `approval`, or `validation_and_approval`
- `validator_user_id: str`
- `approver_user_id: str`
- `evidence_required: bool`
- `review_stage: str` with `execution`, `validation`, `approval`, or `complete`

Existing username/name fields remain compatibility/display caches derived from the scoped canonical user. Reviewer display information is resolved from scoped users for responses rather than persisted as authority. Stable user IDs are authoritative for all task-specific authorization.

Every task has an effective review mode, but new task creation may omit `review_mode`; omission uses the application compatibility default `validation_and_approval`. An explicit task-level mode overrides that default. No project-level workflow-default subsystem is added in this slice. Reviewer IDs are mandatory only when required by the effective mode, while irrelevant reviewer fields are rejected rather than ignored. `evidence_required` defaults to false when omitted.

Alternative considered: add review defaults to Project Configuration. Rejected for this slice because the existing application-level compatibility default is sufficient and a project-default subsystem would expand project schema and UI.

Alternative considered: dynamically choose any capable reviewer at action time. Rejected because routing would be unstable, auditable responsibility would be unclear, and a broad capability could become task-specific authority.

### 2. Use current status plus explicit review stage

Do not add Pending Approval or Validated statuses. `pending_validation` remains the compatibility status for any submitted task waiting on a configured review stage. `review_stage` disambiguates what is pending:

- active execution: existing open status plus `execution`
- validation pending: `pending_validation` plus `validation`
- approval pending: `pending_validation` plus `approval`
- terminal completion: `completed` plus `complete`

The Studio presents policy-aware labels such as Pending Validation or Pending Approval from this pair. `validated_at` records a completed validation checkpoint; `approved_at` records approval. Direct and validation-only completion leave non-applicable timestamps empty and rely on status/history for terminal truth.

Alternative considered: add Pending Approval. Rejected because review-stage metadata is sufficient, keeps existing API consumers and dashboards compatible, and honors the no-validated-status contract.

### 3. One completion-of-execution action dispatches by policy

Add a policy-neutral request intent to the existing task update route, conceptually `complete_execution: true`. The backend dispatches solely from the persisted effective policy:

- direct completion -> Completed
- validation -> pending validation
- approval -> pending approval
- validation and approval -> pending validation

The current `submit_for_validation` input remains a bounded compatibility alias only for legacy/default-two-stage or configured validation-first tasks. It is rejected for direct or approval-only tasks so a client cannot override routing.

Starting, updating, directly completing, or submitting assigned execution requires canonical assignee identity and `UPDATE_TASK_PROGRESS`; `SUBMIT_EVIDENCE` is not a completion permission. Attaching or submitting evidence is a distinct evidence action that additionally requires `SUBMIT_EVIDENCE`. When `evidence_required` is false, absence of that evidence capability does not block otherwise authorized completion. When true, evidence must already exist before completion, and an assignee who must add it needs `SUBMIT_EVIDENCE`.

To satisfy PM-self-assigned execution without a special role bypass, add `UPDATE_TASK_PROGRESS` to the Programme Manager default bundle. MEAL Officer already has that capability. Do not add `SUBMIT_EVIDENCE` to either bundle merely to permit task completion; evidence-required assignment remains valid only when the selected assignee has the evidence capability or an explicit permission override provides it.

Alternative considered: treat `MANAGE_WORKPLAN` as execution authority. Rejected because that would preserve the current risk that broad managers can mutate another person's assigned work.

### 4. Reviewer authorization is designated identity plus capability

Task creation and pre-execution routing validation resolve assignee and reviewers from active users in the task organization and project membership. Validator needs `VALIDATE_EVIDENCE`; approver needs `APPROVE_TASKS`. The assignee must differ from every reviewer, and two-stage reviewer IDs must differ.

At action time, the backend checks in this order:

1. authenticated tenant context;
2. scoped project and task resolution;
3. required capability;
4. canonical assignee or designated reviewer ID;
5. effective review policy and active review stage;
6. current status and business preconditions.

This preserves 401/403/404/409 semantics: authentication failure is 401, missing capability or wrong task-specific identity is 403, foreign scoped resources are concealed, and invalid same-tenant transition order is 409.

### 5. Evidence policy is a single independent gate

`evidence_required` is evaluated only when the assignee completes execution. At least one non-empty evidence item is sufficient. The flag defaults to false for new and legacy tasks because the current application permits submission with no evidence and treats `evidence_note` as optional. Evidence may still be attached when false, but attaching it requires canonical assignee identity plus `SUBMIT_EVIDENCE`. Validation and approval do not independently reinterpret evidence completeness.

Alternative considered: mode-specific evidence rules. Rejected because they would become a rules engine and obscure the independent product concepts.

### 6. Returns restart the configured review sequence

The existing review endpoint and decision vocabulary remain, but return authorization becomes stage-aware. A designated validator or approver can return only while their stage is active. Return restores In Progress and `review_stage=execution`, retains assignment/policy/reviewer configuration and immutable history, and clears current-cycle `submitted_at`, `validated_at`, and `approved_at`. Resubmission starts the policy from its first configured stage, so an approval-stage return in a two-stage policy requires validation again.

Alternative considered: preserve prior validation after approval return. Rejected for the first slice because corrected execution may invalidate the previous validation; restarting is conservative and matches the current return-to-execution model.

### 7. Routing can change only before execution through an explicit operation

Add an explicit routing update contract under the current task route family, conceptually `PATCH /v1/demo/tasks/{task_id}/routing`, requiring `ASSIGN_TASKS`. It can atomically change assignee, review mode, reviewers, and evidence requirement only while the task is Not Started with zero progress, no evidence, no submission/review timestamps, and no execution history after assignment. The complete proposed routing is validated before mutation.

Normal execution requests cannot change routing fields. Once work starts, this slice returns 409 and requires product work outside this change for cancellation/reopen/reassignment. There is no hidden manager override.

Alternative considered: overload the current execution update body. Rejected because it mixes task ownership administration with assignee execution and makes authorization ordering less reviewable.

### 8. Escalation remains orthogonal

Existing escalation can mark an active task Escalated and affect visibility/attention. It does not rewrite assignee, policy, reviewers, stage, or capabilities. An escalated assignee can continue eligible execution, and completion follows the same configured policy.

### 9. Legacy compatibility is resolved without mutate-on-read

For a task missing new fields, an effective compatibility view is built:

- missing `review_mode` -> `validation_and_approval`
- missing `review_stage` -> derive from status and existing timestamps
- missing `evidence_required` -> false
- missing `assignee_user_id` -> resolve stored username against active users in the same organization and project
- missing validator/approver IDs -> accept only exactly one active in-project capability-eligible user for each required stage after separation-of-duties filtering

Zero, multiple, foreign, inactive, or contradictory matches mark routing unresolved. Authorized reads remain possible and expose a routing resolution state, but mutations fail closed with 409 until repaired. The authenticated caller is never used as an ownership or reviewer fallback.

Implement a guarded explicit backfill utility or migration command after characterization. It runs dry first, reports resolved and unresolved tasks, requires a canonical backup for apply, writes only uniquely resolved routing fields, preserves task IDs/status/history, and saves atomically. Ordinary startup and reads never run it. No relational schema migration is required because relational state is derived from the canonical snapshot.

Alternative considered: assign the first capable user or current caller. Rejected because it can silently transfer responsibility and violate tenant/task authorization.

### 10. Keep API and Studio decisions client independent

The current creation, update, and review route paths remain. Creation accepts an optional task-level review-mode override, defaults omission to `validation_and_approval`, and requires only the reviewer IDs applicable to the effective mode. Reads return effective routing resolution. A narrow routing endpoint handles pre-execution correction. Review decisions continue on the existing validation endpoint but are interpreted against designated reviewer and stage.

The Studio task form adds a Review selector preselected to the `validation_and_approval` application default, capability-filtered reviewer selectors shown only when needed, and an evidence-required toggle defaulted off. Assignee options require `UPDATE_TASK_PROGRESS` and additionally require `SUBMIT_EVIDENCE` only when evidence is required. Workplan action generation uses returned stable IDs, effective policy, stage, and capabilities; it does not infer authority from profile/role labels. The task drawer continues handing off to these authoritative Workplan controls.

### 11. Validate all routing and side effects before mutation

Creation, routing changes, execution completion, validation, approval, and return build and validate their proposed transition before changing the task or appending audit/notification state. Denied operations produce no canonical save, success audit, notification, external dispatch, or projection mutation. Existing tenant-scoped task resolution remains the outer boundary.

## Risks / Trade-offs

- [Risk] Adding `UPDATE_TASK_PROGRESS` to the Programme Manager default bundle could appear to broaden authority. -> Mitigation: every normal execution action also requires stable assignee identity and project/tenant scope; explicit tests prove broad permission holders cannot mutate others' tasks.
- [Risk] `pending_validation` is linguistically imperfect for approval-only work. -> Mitigation: preserve it as compatibility storage while all UI and API posture use explicit `review_stage`; document a future status cleanup as out of scope.
- [Risk] Some legacy projects may contain multiple capable reviewers, making deterministic reviewer backfill impossible. -> Mitigation: keep reads available, fail closed for mutations, report unresolved tasks in dry-run, and require explicit operator resolution rather than guessing.
- [Trade-off] Clients may omit review mode and receive the compatibility default. -> Mitigation: responses expose the effective mode, the Studio shows the preselected default, and applicable designated reviewers remain explicit.
- [Risk] Approval-stage return restarting validation may surprise users. -> Mitigation: label the return consequence in Studio and protect the behavior with explicit regression scenarios.

## Migration Plan

1. Add characterization tests for current Field-only submission, broad non-Field mutation, current Golden Journey, legacy snapshots, and frontend action generation.
2. Add additive task fields and pure policy/routing resolution helpers with no transition behavior change.
3. Implement scoped assignee/reviewer validation, separation of duties, execution permissions, and atomic creation/routing contracts.
4. Implement policy-aware execution completion, validation, approval, return, escalation preservation, and audit behavior.
5. Update Studio creation and Workplan controls to consume backend routing fields and capability-filtered members.
6. Add the guarded legacy dry-run/backfill utility and validate it against copied fixtures before any optional local data authorization.
7. Run focused workflow, tenant-security, projection-reliability, Logical Framework, and full authoritative suites.
8. Run manual browser acceptance for all four policy modes, the Golden Journey, return/resubmission, escalation, refresh/re-login, and cross-user denial.

Application rollback is the pre-Apply Git checkpoint. Any separately authorized legacy backfill rollback uses its verified canonical backup followed by derived projection reconciliation; stale projection data must never replace canonical state.
