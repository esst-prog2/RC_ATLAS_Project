## 1. Baseline and Characterization

- [x] 1.1 Run `py -m unittest discover -v -p "*tests.py"` before source edits and verify the 201-test main baseline passes with zero failures, errors, or skips.
- [ ] 1.2 Add focused service/API characterization tests for current Field submission, PM self-assigned rejection, MEAL-assigned execution, broad non-assignee mutation, validation, approval, return, and escalation; verify the tests capture current behavior before implementation.
- [ ] 1.3 Add task snapshot characterization fixtures covering legacy username-only assignment, missing policy fields, existing submission/validation/approval timestamps, history, and status vocabulary; verify byte-for-byte reads do not mutate fixtures.
- [ ] 1.4 Add Studio characterization assertions for task creation fields, `taskWorkflowActionButtons()`, task drawer handoff, role-derived action assumptions, and pending-review labels; verify the current PM/MEAL execution gaps are represented.
- [ ] 1.5 Record focused Golden Journey, tenant-security, canonical-projection, and Logical Framework regression commands and verify their pre-change baselines pass.

## 2. Task Model and Effective Routing

- [x] 2.1 Add the stable assignee ID, review mode, validator ID, approver ID, evidence-required flag, and review-stage fields to canonical Task hydration and serialization; verify old snapshots still load without mutation.
- [x] 2.2 Add strict review-mode and review-stage normalization with only the approved values; verify omitted review mode defaults to validation-and-approval while an explicitly unknown value fails as same-tenant business input.
- [x] 2.3 Implement a pure effective-routing resolver for configured and legacy tasks; verify missing legacy policy maps to validation-and-approval and present configured fields remain authoritative.
- [x] 2.4 Resolve legacy assignee usernames only within active same-organization project membership and verify zero or multiple matches are marked unresolved without using the caller as fallback.
- [x] 2.5 Resolve missing legacy reviewers only when exactly one in-scope capability-eligible user satisfies each stage and separation-of-duties rules; verify ambiguous reviewers fail closed.
- [x] 2.6 Expose additive effective-routing and resolution-state fields in task responses while preserving existing fields and envelopes; verify authenticated legacy and configured reads remain compatible.

## 3. Scoped Identity, Capabilities, and Policy Validation

- [x] 3.1 Add scoped project-member lookup by stable user ID for assignee, validator, and approver selection; verify inactive, foreign-organization, and non-member identities are rejected before mutation.
- [x] 3.2 Validate every assignee has `UPDATE_TASK_PROGRESS` and require `SUBMIT_EVIDENCE` additionally only when `evidence_required` is true; verify ordinary and evidence-required eligibility independently.
- [x] 3.3 Validate designated validators have `VALIDATE_EVIDENCE` and designated approvers have `APPROVE_TASKS`; verify role labels alone never establish reviewer eligibility.
- [x] 3.4 Enforce assignee-reviewer and validator-approver separation using stable IDs; verify every self-review and same-two-stage-reviewer configuration is rejected atomically.
- [x] 3.5 Add `UPDATE_TASK_PROGRESS` to the Programme Manager default bundle without adding universal evidence permissions; verify PM and MEAL assignees can complete evidence-optional work while no capability authorizes another assignee's task.
- [x] 3.6 Centralize action authorization as tenant scope, project scope, capability, task-specific identity, policy, stage, and state; verify 401/403/404/409 semantics remain distinct.

## 4. Creation and Pre-Execution Routing

- [x] 4.1 Default omitted review mode to validation-and-approval and validate required or irrelevant reviewer fields against the effective mode; verify explicit direct, validation, approval, two-stage, and omitted-mode payloads.
- [x] 4.2 Persist canonical identity and complete routing configuration only after assignee, reviewers, separation of duties, activity, task ID, and payload validation; verify failed creation performs no save, success audit, notification, or projection mutation.
- [x] 4.3 Add the explicit pre-execution routing endpoint requiring `ASSIGN_TASKS`; verify a complete valid routing replacement on an untouched Not Started task commits atomically and is audited.
- [x] 4.4 Reject routing changes after progress, evidence, execution history, submission, validation, or approval begins; verify status 409 and byte-for-byte task preservation.
- [x] 4.5 Reject all routing fields submitted through the normal execution update route; verify no implicit managerial override or structural-field mutation remains.

## 5. Policy-Aware Execution and Review Transitions

- [x] 5.1 Restrict start, progress, comment, and completion-of-execution to the canonical assignee with `UPDATE_TASK_PROGRESS`, and evidence attachment additionally to `SUBMIT_EVIDENCE`; verify permissions remain separate and no actor can execute another user's task.
- [x] 5.2 Implement the policy-neutral completion-of-execution intent and verify direct-completion tasks become Completed without reviewers.
- [x] 5.3 Route validation-only, approval-only, and two-stage tasks to `pending_validation` with the correct persisted review stage; verify no new user-facing status is introduced.
- [x] 5.4 Keep the legacy validation-submission input as an alias only for legacy or validation-first policies; verify direct and approval-only policies reject it without mutation.
- [x] 5.5 Enforce `evidence_required` at execution completion, default it to false when absent, and verify evidence-optional direct/reviewed completion does not require `SUBMIT_EVIDENCE` while evidence attachment does.
- [x] 5.6 Restrict validation and validation-stage return to the designated validator with `VALIDATE_EVIDENCE`; verify validation-only completes and two-stage advances to approval.
- [x] 5.7 Restrict approval and approval-stage return to the designated approver with `APPROVE_TASKS`; verify approval-only and two-stage tasks complete correctly.
- [x] 5.8 Make reviewer return restore In Progress and execution stage, clear current-cycle timestamps, preserve routing/history, and restart the configured sequence on resubmission; verify both validation and approval returns.
- [x] 5.9 Preserve escalation as attention-only state and verify it changes no assignee, reviewer, policy, stage, or authorization and follows normal routing after execution.
- [x] 5.10 Stage transition, history, audit, notification, canonical save, and projection effects after all authorization and business validation; verify every denial has zero success side effects.

## 6. Legacy Backfill Safety

- [ ] 6.1 Add a focused dry-run-first legacy routing backfill utility that reports uniquely resolved and unresolved tasks without running at startup; verify dry-run is byte-for-byte non-mutating.
- [ ] 6.2 Require explicit apply mode, a verified canonical backup, and unchanged-input/precondition checks before backfill; verify any failed precondition aborts before mutation.
- [ ] 6.3 Backfill only uniquely resolved stable identities, default review policy, evidence flag, and derived stage while preserving task IDs, status, timestamps, evidence, notes, and activity history; verify fixture comparisons field-for-field.
- [ ] 6.4 Save a validated backfill atomically and rebuild derived projection from canonical state; verify projection failure never replaces or rolls back the canonical snapshot.
- [ ] 6.5 Leave ambiguous tasks unchanged and report the exact unresolved identity/routing reason; verify no caller-derived or first-match assignment occurs.

## 7. Studio Compatibility and Workflow UX

- [ ] 7.1 Extend task creation with an assignee selector filtered by the effective evidence policy, a four-mode Review selector preselected to validation-and-approval, conditional capability-filtered reviewer selectors, and an evidence-required toggle defaulted off; verify payloads match backend defaults.
- [ ] 7.2 Update Workplan action generation to use stable actor/assignee/reviewer IDs, permissions, effective policy, review stage, and state rather than profile role labels; verify crafted requests remain backend-enforced.
- [ ] 7.3 Present approval-only and post-validation approval posture as Pending Approval while preserving stored `pending_validation`; verify no visual or persistence contract introduces a validated status.
- [ ] 7.4 Preserve the existing task-drawer handoff and focus behavior for PM, MEAL, and Field assignees; verify the drawer does not duplicate workflow authorization.
- [ ] 7.5 Label return behavior and routing configuration clearly without redesigning Workplan, Portfolio, Project Configuration, or Studio navigation; verify existing visual regression assertions remain green.

## 8. Contract and Regression Tests

- [x] 8.1 Add black-box tests for PM direct completion, MEAL execution with approval, Field validation-only, and the configured Golden Journey; verify persisted HTTP outcomes and reload behavior.
- [x] 8.2 Add black-box denial tests for non-assignee execution, self-validation, self-approval, duplicate two-stage reviewer, missing reviewer capability, cross-organization reviewer, and non-project-member reviewer; verify zero mutation and success audit.
- [x] 8.3 Add evidence-required and evidence-optional tests across direct and reviewed modes; verify evidence attachment requires `SUBMIT_EVIDENCE`, evidence-optional completion does not, and missing required evidence returns 409.
- [x] 8.4 Add transition-order tests proving validators cannot act before submission, approvers cannot act before their stage, and same-tenant malformed input retains 400 while lifecycle conflicts retain 409.
- [x] 8.5 Add escalation and pre-execution-routing tests proving ownership is stable, valid untouched-task correction succeeds, and post-start changes fail closed.
- [ ] 8.6 Add legacy compatibility tests for unique resolution, ambiguous assignee, ambiguous reviewers, read non-mutation, guarded backfill, and no schema migration.
- [ ] 8.7 Add Studio source/behavior tests proving controls match backend identity/capability/policy decisions and all four modes render the correct actions and labels.
- [x] 8.8 Run protected tenant-security, canonical-projection-reliability, Course MVP, and Logical Framework suites and verify no existing expectation is weakened or deleted for convenience.

## 9. Final Verification and Acceptance

- [x] 9.1 Run all focused assignment-aware workflow tests and verify every policy, denial, compatibility, audit, and side-effect contract passes.
- [x] 9.2 Run `py -m unittest discover -v -p "*tests.py"` and verify all original 201 tests plus new tests pass with zero failures, errors, or skips.
- [x] 9.3 Run strict OpenSpec validation and `git diff --check`; inspect the full diff for accidental authentication, tenant-security, persistence, Logical Framework, Project Configuration, or unrelated UI expansion.
- [ ] 9.4 Manually verify in Studio: PM direct completion, MEAL execution plus approval, Field validation-only, escalation without ownership transfer, return/resubmission, and refresh/re-login persistence.
- [ ] 9.5 Manually run the protected Golden Journey as Aline assignee, Raimundo validator, and Teresa approver through Completed; verify no validated status and no unexpected 401/403.
- [ ] 9.6 Review any proposed real legacy-data backfill dry-run and obtain separate explicit authorization before applying it; do not treat automated fixtures as authorization to mutate local runtime data.
