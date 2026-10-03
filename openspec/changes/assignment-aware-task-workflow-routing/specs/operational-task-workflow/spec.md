## MODIFIED Requirements

### Requirement: Canonical project-member assignment
The system SHALL allow an authorized task assigner to create a task only for an active user in the same organization who has an active assignment to the selected project and `UPDATE_TASK_PROGRESS`. When `evidence_required` is true, the assignee SHALL also have `SUBMIT_EVIDENCE` so the required evidence can be supplied. The system SHALL derive and persist the assignee's stable user ID, username, and display name from the selected user record rather than trusting free-text identity fields. Every new task SHALL have an effective supported review mode: an explicit task override when supplied, otherwise the `validation_and_approval` application default; only reviewer identities applicable to that effective mode are required.

#### Scenario: Manager assigns the course task to Aline
- **WHEN** Teresa selects eligible project member Aline Duarte, selects `validation_and_approval`, designates Raimundo as validator and Teresa as approver, and creates the task
- **THEN** the task persists Aline's stable user ID and canonical identity, the selected routing policy, Not Started status, and the selected deadline

#### Scenario: Programme Manager is an eligible execution assignee
- **WHEN** Teresa has the required execution capabilities and is an active member of the selected project
- **THEN** Teresa can be selected as the canonical assignee without inserting a Field Coordinator

#### Scenario: MEAL Officer is an eligible execution assignee
- **WHEN** Raimundo has the required execution capabilities and is an active member of the selected project
- **THEN** Raimundo can be selected as the canonical assignee without inserting a Field Coordinator

#### Scenario: Ineligible assignee is rejected
- **WHEN** assignment names an unknown, inactive, cross-organization, non-member, or execution-incapable user
- **THEN** the system rejects the request without creating a task or successful assignment event

#### Scenario: Display identity cannot override canonical identity
- **WHEN** assignment supplies a valid assignee identifier with conflicting username or display fields
- **THEN** the system uses the canonical scoped user record for all assignee identity fields

### Requirement: Field execution is limited to the canonical assignee
The system SHALL allow normal task execution mutations only by the authenticated canonical assignee who has `UPDATE_TASK_PROGRESS`; role labels SHALL NOT confer execution ownership. Starting work, progress, comments, and completing execution SHALL NOT require `SUBMIT_EVIDENCE`. Attaching or submitting evidence SHALL additionally require `SUBMIT_EVIDENCE`. Execution mutations SHALL NOT change assignment, routing policy, reviewer identities, evidence policy, deadline, priority, category, indicator relationship, organization, project, or arbitrary workflow state.

#### Scenario: Assigned Field Coordinator updates execution
- **WHEN** an authenticated user opens a task whose canonical assignee user ID matches that user and records a permitted progress, evidence, or comment update
- **THEN** the system persists the execution update and records the actor in task history

#### Scenario: Field Coordinator cannot update another user's task
- **WHEN** a Programme Manager, MEAL Officer, Field Coordinator, or other actor attempts a normal execution mutation on another user's task
- **THEN** the system returns HTTP 403 and leaves task, audit, notification, canonical, and projection state unchanged

#### Scenario: Assignee lacking execution capability is rejected
- **WHEN** the canonical assignee attempts an execution update without `UPDATE_TASK_PROGRESS`
- **THEN** the system returns HTTP 403 and leaves the task unchanged

#### Scenario: Field Coordinator cannot alter structural fields
- **WHEN** the canonical assignee submits assignment, routing, reviewer, evidence-policy, deadline, priority, category, indicator, organization, project, or unsupported status fields through the execution operation
- **THEN** the system rejects the mutation atomically

### Requirement: Field submission opens the MEAL checkpoint
The system SHALL allow only the canonical assignee with `UPDATE_TASK_PROGRESS` to complete execution from an eligible active state. `SUBMIT_EVIDENCE` SHALL NOT be a universal completion prerequisite. Completion SHALL route the task according to its configured review mode: `direct_completion` completes the task, `validation` opens validation, `approval` opens approval, and `validation_and_approval` opens validation followed by approval. Review-pending tasks SHALL retain the existing `pending_validation` status while persisted review-stage metadata identifies the active checkpoint.

#### Scenario: Direct completion closes assigned work
- **WHEN** Teresa is the assignee of an eligible `direct_completion` task with `evidence_required=false` and has `UPDATE_TASK_PROGRESS` but not `SUBMIT_EVIDENCE`
- **THEN** the task becomes Completed with 100 percent progress and no validator or approver is inserted

#### Scenario: Field Coordinator submits assigned work
- **WHEN** Aline completes execution of an eligible `validation` task
- **THEN** the task enters `pending_validation`, records submission, identifies validation as the active review stage, and remains assigned to Aline

#### Scenario: Approval-only submission opens approval
- **WHEN** Raimundo completes execution of an eligible `approval` task
- **THEN** the task enters `pending_validation`, records submission, identifies approval as the active review stage, and does not require a validation checkpoint

#### Scenario: Two-stage submission opens validation first
- **WHEN** Aline completes execution of an eligible `validation_and_approval` task
- **THEN** the task enters `pending_validation` at the validation stage and retains its configured approver for the later stage

#### Scenario: Out-of-order submission is rejected
- **WHEN** an actor attempts to complete execution for an unassigned, already pending, completed, or otherwise ineligible task
- **THEN** the system returns the established authorization or conflict status and preserves the prior state

### Requirement: MEAL review is limited to unvalidated submissions
The system SHALL offer validation only when the configured policy includes validation, the task is submitted at the validation stage, and the authenticated actor is the designated validator with `VALIDATE_EVIDENCE`. Successful validation SHALL complete a `validation` task or advance a `validation_and_approval` task to approval without introducing a validated task status. The designated validator SHALL be able to return eligible work for rework.

#### Scenario: Designated validator completes validation-only task
- **WHEN** Raimundo validates Aline's submitted `validation` task
- **THEN** the system records validation and completes the task with no approval stage

#### Scenario: MEAL validates submitted work
- **WHEN** Raimundo validates Aline's submitted `validation_and_approval` task
- **THEN** the system records validation, keeps status `pending_validation`, changes the active review stage to approval, and offers no further validation action

#### Scenario: MEAL returns submitted work
- **WHEN** Raimundo returns an eligible submitted task with a comment
- **THEN** the task returns to In Progress for its unchanged assignee, current-cycle review timestamps are cleared, history is preserved, and resubmission restarts the configured review sequence

#### Scenario: Validated work leaves the MEAL queue
- **WHEN** a `validation_and_approval` task has a non-empty validation timestamp and approval is the active review stage
- **THEN** it is no longer presented as requiring validation and no further validation action is offered

#### Scenario: Non-designated validator is rejected
- **WHEN** an actor with `VALIDATE_EVIDENCE` who is not the task's designated validator attempts validation or return
- **THEN** the system returns HTTP 403 and leaves the task unchanged

#### Scenario: MEAL cannot validate out of order
- **WHEN** the designated validator acts before submission, during approval, after completion, or on a policy without validation
- **THEN** the system returns HTTP 409 and leaves the task unchanged

### Requirement: Programme Manager performs final approval
The system SHALL offer approval only when the configured policy includes approval, the task is submitted at the approval stage, and the authenticated actor is the designated approver with `APPROVE_TASKS`. Approval SHALL complete an `approval` task directly or complete a `validation_and_approval` task after its validation checkpoint. The designated approver SHALL be able to return eligible work for rework.

#### Scenario: Designated approver completes approval-only task
- **WHEN** Teresa approves Raimundo's submitted `approval` task
- **THEN** the system records approval, sets Completed status and 100 percent progress, and does not require validation

#### Scenario: Manager approves validated work
- **WHEN** Teresa approves Aline's `validation_and_approval` task after Raimundo's validation
- **THEN** the task becomes Completed with submission, validation, approval, and history preserved

#### Scenario: Teresa sees validated work awaiting approval
- **WHEN** Teresa opens a two-stage task after its designated validator has completed validation
- **THEN** the interface identifies approval as the active stage while retaining `pending_validation` as stored status

#### Scenario: Designated approver returns work
- **WHEN** the designated approver returns an eligible approval-stage task with a comment
- **THEN** the task returns to In Progress for its unchanged assignee, current-cycle review timestamps are cleared, history is preserved, and resubmission restarts the configured review sequence

#### Scenario: Non-designated approver is rejected
- **WHEN** an actor with `APPROVE_TASKS` who is not the task's designated approver attempts approval or return
- **THEN** the system returns HTTP 403 and leaves the task unchanged

#### Scenario: Manager cannot approve before MEAL validation
- **WHEN** the designated approver acts before submission, while required validation is incomplete, after completion, or on a policy without approval
- **THEN** the system returns HTTP 409 and leaves the task unchanged

### Requirement: Workflow state persists across authenticated sessions
The system SHALL persist canonical assignee identity, review mode, designated reviewers, evidence policy, active review stage, execution updates, submission, validation, return, approval, direct completion, and activity history in the configured local datastore so each authorized actor observes the latest committed state after logout, login, and application reload.

#### Scenario: Role handoff observes persisted state
- **WHEN** a configured workflow passes from assignee to validator to approver across separate authenticated sessions
- **THEN** each actor observes the same task routing, reviewer identities, timestamps, history, and current workflow posture

#### Scenario: Approved state survives reload
- **WHEN** an assignee directly completes a task and the application reloads the configured datastore
- **THEN** the task remains Completed with its routing policy and completion history intact

### Requirement: Successful transitions are auditable
The system SHALL record the authenticated actor, task, project, canonical assignee, review mode, active review stage, transition outcome, and timestamp for successful assignment, execution update, completion of execution, validation, return, approval, direct completion, reassignment, or pre-execution routing change. Rejected operations SHALL NOT emit a successful workflow event.

#### Scenario: Course workflow produces traceable history
- **WHEN** the configured Golden Journey succeeds
- **THEN** task history and audit identify assignment to Aline, Aline's execution and submission, Raimundo's validation, and Teresa's approval in chronological order

#### Scenario: Denied task-specific action has no success event
- **WHEN** an actor has a broad capability but is not the assignee or designated reviewer for the attempted action
- **THEN** the request is denied without a success audit entry or workflow side effect

### Requirement: Existing external contracts remain compatible
The change SHALL preserve existing task IDs, route paths, response envelopes, status vocabulary, tenant-security behavior, JSON/SQLite snapshot authority, and unrelated RC Atlas modules. Successful task responses SHALL add routing fields. New task creation MAY omit review mode and receive the `validation_and_approval` application default; it SHALL require only reviewer IDs applicable to the effective mode. The existing submission request field SHALL remain a compatibility alias only for legacy or configured workflows whose first review stage is validation. The change SHALL NOT add a validated status or require a relational schema change.

#### Scenario: Existing clients read the hardened workflow
- **WHEN** an authorized client reads a configured or compatible legacy task
- **THEN** it receives existing response fields plus effective assignee and routing metadata without a response-envelope change

#### Scenario: Existing validation-first submission alias remains bounded
- **WHEN** an existing authorized client uses the legacy validation-submission field on a legacy task or configured workflow whose first stage is validation
- **THEN** the system treats it as completion of execution under the effective policy

#### Scenario: Validation alias cannot bypass another policy
- **WHEN** a client uses the legacy validation-submission field on `direct_completion` or `approval`
- **THEN** the system rejects the incompatible action without changing the task

#### Scenario: Broader RC Atlas surfaces remain unaffected
- **WHEN** Portfolio, Logical Framework, indicators, reporting, notifications, administration, Project Configuration, or persistence projections are used
- **THEN** their contracts remain unchanged except for displaying effective task routing where task data already appears

### Requirement: Browser acceptance preserves the canonical workflow
The Studio SHALL derive task creation choices and workflow actions from the same assignment, capability, policy, reviewer, and state rules enforced by the backend. Browser acceptance SHALL preserve the configured Golden Journey and SHALL additionally prove direct completion, approval-only, validation-only, return/resubmission, escalation, and cross-user denial through the current Studio.

#### Scenario: Golden Journey completes through existing controls
- **WHEN** Teresa assigns Aline with `validation_and_approval`, Raimundo as validator, and Teresa as approver; Aline executes and submits; Raimundo validates; and Teresa approves
- **THEN** the task becomes Completed through the existing Workplan controls without a validated status

#### Scenario: Programme Manager directly completes own task
- **WHEN** Teresa is the assignee of a `direct_completion` task with `evidence_required=false` and has `UPDATE_TASK_PROGRESS`
- **THEN** the Studio offers Teresa the permitted execution and completion controls and does not insert Aline or any reviewer

#### Scenario: MEAL assignee submits for approval
- **WHEN** Raimundo is the assignee of an `approval` task with Teresa as approver
- **THEN** the Studio offers Raimundo execution controls and later offers approval only to Teresa

#### Scenario: Return and resubmission remain valid
- **WHEN** a designated reviewer returns submitted work and the unchanged assignee corrects and resubmits it
- **THEN** the task follows the existing In Progress and `pending_validation` statuses through its configured review sequence

#### Scenario: No validated task status is introduced
- **WHEN** validation succeeds for a two-stage task
- **THEN** the task remains `pending_validation` with approval as the active review stage until designated approval completes it

#### Scenario: Browser handoffs persist across sessions
- **WHEN** each configured workflow actor refreshes or signs in again after a successful transition
- **THEN** the next actor observes the latest canonical routing and task state without an unexpected 401 or 403 for an authorized action

#### Scenario: Frontend does not broaden backend authority
- **WHEN** a user is not the assignee or designated reviewer for an action
- **THEN** the Studio does not offer that action and a crafted HTTP request remains denied by the backend

## ADDED Requirements

### Requirement: Review policy and reviewers are explicit and valid
Each new task SHALL have exactly one effective review mode: explicit `direct_completion`, `validation`, `approval`, or `validation_and_approval`, or `validation_and_approval` by application default when omitted. `validation` SHALL require one designated validator, `approval` SHALL require one designated approver, `validation_and_approval` SHALL require both, and `direct_completion` SHALL require neither. Reviewer fields not applicable to the effective mode SHALL NOT be required. Designated reviewers SHALL be active members of the same organization and project and SHALL have the capability required for their stage.

#### Scenario: Omitted policy uses application default
- **WHEN** task creation omits review mode and supplies the validator and approver required by the application default
- **THEN** the system creates the task with effective mode `validation_and_approval`

#### Scenario: Missing required reviewer is rejected
- **WHEN** task creation selects a review mode but omits a reviewer required by that mode
- **THEN** the system returns HTTP 400 without mutation

#### Scenario: Reviewer lacking capability is rejected
- **WHEN** a selected validator lacks `VALIDATE_EVIDENCE` or a selected approver lacks `APPROVE_TASKS`
- **THEN** the system rejects the configuration without disclosing unrelated tenant details

#### Scenario: Foreign or non-member reviewer is rejected
- **WHEN** a selected reviewer belongs to another organization or is not an active member of the task project
- **THEN** the system rejects the configuration without mutation

### Requirement: Separation of duties is enforced
The canonical assignee SHALL NOT also be the designated validator or approver. In `validation_and_approval`, validator and approver SHALL be different users. Identity comparisons SHALL use scoped stable user IDs rather than role names, usernames, or display names.

#### Scenario: Assignee cannot validate own task
- **WHEN** a configuration selects the assignee as validator
- **THEN** the system rejects the configuration

#### Scenario: Assignee cannot approve own reviewed task
- **WHEN** a configuration selects the assignee as approver
- **THEN** the system rejects the configuration

#### Scenario: Two-stage reviewers must differ
- **WHEN** `validation_and_approval` selects the same user as validator and approver
- **THEN** the system rejects the configuration

#### Scenario: Direct completion is the self-closing policy
- **WHEN** independent review is not required and the assignee must close their own work
- **THEN** the task uses `direct_completion` with no reviewer identities

### Requirement: Evidence requirement is independent of review routing
Each task SHALL persist `evidence_required` independently from review mode and SHALL default it to false when absent. When true, the assignee SHALL NOT complete execution until at least one non-empty evidence item exists, and adding that evidence SHALL require `SUBMIT_EVIDENCE`. When false, evidence SHALL remain optional and absence of `SUBMIT_EVIDENCE` SHALL NOT block otherwise authorized completion.

#### Scenario: Required evidence blocks direct completion
- **WHEN** an assignee attempts to directly complete an evidence-required task with no evidence
- **THEN** the system returns HTTP 409 and leaves the task unchanged

#### Scenario: Required evidence blocks submission for review
- **WHEN** an assignee attempts to complete execution for a reviewed evidence-required task with no evidence
- **THEN** the system returns HTTP 409 and does not open a review stage

#### Scenario: Optional evidence does not block workflow
- **WHEN** `evidence_required` is false and all other execution and routing conditions pass
- **THEN** the assignee may complete execution without adding evidence

#### Scenario: Evidence attachment requires evidence capability
- **WHEN** the canonical assignee attempts to attach or submit evidence without `SUBMIT_EVIDENCE`
- **THEN** the system returns HTTP 403 and leaves evidence and task state unchanged

### Requirement: Routing is stable after execution begins
Assignee, review mode, validator, approver, and evidence requirement SHALL be changeable only through an explicit authorized routing operation while the task remains Not Started and has no execution progress, evidence, submission, or review history. Once work begins, changes to those fields SHALL be rejected; no implicit managerial execution override is introduced.

#### Scenario: Pre-execution routing correction succeeds
- **WHEN** an actor with `ASSIGN_TASKS` changes a Not Started untouched task to another valid assignee or valid routing configuration
- **THEN** the system persists the complete validated routing change and records its audit history atomically

#### Scenario: In-progress routing change is rejected
- **WHEN** an actor attempts reassignment or policy/reviewer/evidence-policy change after execution begins
- **THEN** the system returns HTTP 409 and preserves existing assignment and routing

#### Scenario: Broad manager capability does not imply execution override
- **WHEN** a manager who is not the assignee attempts a normal execution update instead of explicit pre-execution reassignment
- **THEN** the system returns HTTP 403

### Requirement: Escalation does not transfer ownership or routing
Escalation SHALL remain an attention condition. It SHALL NOT change assignee, reviewer identities, review mode, evidence requirement, active review stage, or action authorization, and SHALL NOT bypass a configured checkpoint.

#### Scenario: Escalated task remains with assignee
- **WHEN** an authorized actor escalates Aline's active task
- **THEN** Aline remains the canonical assignee and retains only the execution actions otherwise allowed by policy and state

#### Scenario: Escalation preserves review route
- **WHEN** an escalated task completes execution
- **THEN** it follows its previously configured review mode and designated reviewers

### Requirement: Legacy tasks resolve conservatively without mutate-on-read
A task lacking review mode SHALL have effective mode `validation_and_approval`. A task lacking stable assignee identity SHALL resolve its stored assignee username only against active same-organization project members. Missing reviewer identities SHALL resolve only when exactly one active same-organization project member has the required capability and satisfies separation of duties. Compatibility resolution SHALL NOT mutate persisted data during reads; ambiguous or contradictory identity SHALL fail closed for mutations.

#### Scenario: Legacy Golden Journey resolves uniquely
- **WHEN** a legacy task has a uniquely resolved assignee and exactly one eligible validator and approver in its project
- **THEN** reads expose the effective `validation_and_approval` route and authorized transitions preserve the existing Golden Journey

#### Scenario: Ambiguous legacy assignee fails closed
- **WHEN** a legacy assignee username does not resolve to exactly one active in-scope project member
- **THEN** the task remains readable to authorized users but execution and review mutations are rejected until repaired

#### Scenario: Ambiguous legacy reviewer fails closed
- **WHEN** a legacy task lacks reviewer IDs and a required stage has zero or multiple eligible reviewers
- **THEN** that transition is rejected without selecting a reviewer from the caller's identity or role

#### Scenario: Compatibility read does not backfill silently
- **WHEN** effective legacy routing is calculated during a task read
- **THEN** canonical snapshot bytes and derived projections are not changed

#### Scenario: Guarded backfill preserves identity and history
- **WHEN** an explicit migration/backfill operation is later authorized for uniquely resolvable legacy tasks
- **THEN** it writes stable identities and policy fields without recreating tasks, changing statuses, or rewriting activity history

## RENAMED Requirements

- FROM: `Field execution is limited to the canonical assignee`
- TO: `Assignee execution is limited to the canonical assignee`
- FROM: `Field submission opens the MEAL checkpoint`
- TO: `Assignee completion follows configured review policy`
- FROM: `MEAL review is limited to unvalidated submissions`
- TO: `Designated validation is policy and capability scoped`
- FROM: `Programme Manager performs final approval`
- TO: `Designated approval is policy and capability scoped`
