## Purpose

Defines the authenticated, persistent task-assignment and validation workflow that RC Atlas must demonstrate as the course MVP without expanding into unrelated product capabilities.

## ADDED Requirements

### Requirement: Canonical project-member assignment
The system SHALL allow an authorized Programme Manager to create a task only for an active user who belongs to the same organization as the project and has an active assignment to that project. The system SHALL derive and persist the task assignee username and display name from the selected user record rather than trusting free-text identity fields.

#### Scenario: Manager assigns the course task to Aline
- **WHEN** Teresa selects Aline Duarte from the eligible members of the configured project and creates "Finalize Buzi monitoring report" with a deadline
- **THEN** the task is persisted with Aline's canonical username and display name, the selected deadline, and Not Started status

#### Scenario: Ineligible assignee is rejected
- **WHEN** an assignment request names an unknown, inactive, cross-organization, or non-member user
- **THEN** the system rejects the request without creating a task or recording a successful assignment event

#### Scenario: Display identity cannot override canonical identity
- **WHEN** an assignment request supplies a valid assignee identifier with a conflicting display name
- **THEN** the system uses the canonical user record for both assignee identity fields

### Requirement: Field execution is limited to the canonical assignee
The system SHALL allow a Field Coordinator to mutate only tasks canonically assigned to that authenticated user. Field execution mutations SHALL be limited to starting work, progress, evidence notes, comments, and submission for validation; they SHALL NOT change assignment, deadline, priority, category, indicator relationship, organization, project, or arbitrary workflow state.

#### Scenario: Assigned Field Coordinator updates execution
- **WHEN** Aline opens a task whose canonical assignee username is her authenticated username and records progress, evidence, or a comment
- **THEN** the system persists the execution update and records it in task activity history

#### Scenario: Field Coordinator cannot update another user's task
- **WHEN** Aline attempts to mutate a task assigned to another canonical user
- **THEN** the system returns an authorization error and leaves the task unchanged

#### Scenario: Field Coordinator cannot alter structural fields
- **WHEN** a Field Coordinator submits assignment, deadline, priority, category, indicator, organization, project, or unsupported status fields through the task-update operation
- **THEN** the system rejects the prohibited mutation atomically and leaves the task unchanged

### Requirement: Field submission opens the MEAL checkpoint
The system SHALL allow the canonical Field assignee to submit an active assigned task for validation. Submission SHALL preserve the existing pending_validation status, record submitted_at, and prevent Field users from validating, approving, completing, or continuing to mutate the task until it is returned.

#### Scenario: Field Coordinator submits assigned work
- **WHEN** Aline submits her In Progress, Overdue, or Escalated assigned task for validation
- **THEN** the task enters pending_validation, records submitted_at, remains assigned to Aline, and appears in the MEAL validation queue

#### Scenario: Out-of-order submission is rejected
- **WHEN** a Field Coordinator attempts to submit an unassigned, already pending, completed, or otherwise ineligible task
- **THEN** the system rejects the transition and preserves the prior task state

### Requirement: MEAL review is limited to unvalidated submissions
The system SHALL include in the MEAL validation queue only submitted tasks in pending_validation that do not yet have validated_at. An authorized MEAL Officer SHALL be able either to validate such a task or return it for rework, and SHALL NOT review an ineligible or already validated task again.

#### Scenario: MEAL validates submitted work
- **WHEN** Raimundo validates Aline's submitted task
- **THEN** the system records validated_at and the validation activity while keeping the task in pending_validation for final Programme Manager approval

#### Scenario: MEAL returns submitted work
- **WHEN** Raimundo returns Aline's submitted task with a review comment
- **THEN** the system restores the task to In Progress, preserves its canonical assignment, records the return activity, and allows Aline to continue execution

#### Scenario: Validated work leaves the MEAL queue
- **WHEN** a pending_validation task has a non-empty validated_at value
- **THEN** it is no longer presented as requiring MEAL validation and no further MEAL validation action is offered

#### Scenario: MEAL cannot validate out of order
- **WHEN** a MEAL Officer attempts to validate or return a task that is not an unvalidated pending submission
- **THEN** the system rejects the transition and leaves the task unchanged

### Requirement: Programme Manager performs final approval
The system SHALL permit final approval only for a pending_validation task with a completed MEAL validation checkpoint. Approval SHALL record approved_at, set the existing Completed status and 100 percent progress, and preserve the validation history.

#### Scenario: Teresa sees validated work awaiting approval
- **WHEN** Teresa opens a task after Raimundo has validated it
- **THEN** the interface clearly identifies it as validated by MEAL and awaiting final Programme Manager approval while retaining pending_validation as the stored workflow status

#### Scenario: Manager approves validated work
- **WHEN** Teresa approves a pending_validation task with validated_at recorded
- **THEN** the task becomes Completed, progress becomes 100 percent, approved_at is recorded, and the project workplan reflects the completed state

#### Scenario: Manager cannot approve before MEAL validation
- **WHEN** a Programme Manager attempts to approve a submitted task whose validated_at value is empty
- **THEN** the system rejects the transition, leaves the task pending validation, and does not record a successful approval event

### Requirement: Workflow state persists across authenticated sessions
The system SHALL persist canonical assignment, execution updates, submission, validation, return, approval, and activity history in the configured local datastore so each role observes the latest committed state after logout, login, and application reload.

#### Scenario: Role handoff observes persisted state
- **WHEN** Teresa creates and assigns a task, Aline updates and submits it, Raimundo validates it, and each user signs out before the next user signs in
- **THEN** every subsequent session loads the same task with the canonical owner, deadline, progress, timestamps, and current workflow posture

#### Scenario: Approved state survives reload
- **WHEN** Teresa approves a MEAL-validated task and the application reloads the configured datastore
- **THEN** the task remains Completed with its submission, validation, approval, and activity history intact

### Requirement: Successful transitions are auditable
The system SHALL record the authenticated actor, task, project, transition outcome, and timestamp for successful assignment, execution update, submission, validation, return, and approval operations. Rejected operations SHALL NOT emit a successful workflow event.

#### Scenario: Course workflow produces traceable history
- **WHEN** the complete course workflow succeeds
- **THEN** the task history and audit feed identify the manager assignment, Field updates and submission, MEAL decision, and Programme Manager approval in chronological order

### Requirement: Existing external contracts remain compatible
The change SHALL preserve existing task IDs, route paths, response shapes, task status vocabulary, role-permission model, and current JSON/SQLite persistence behavior. It SHALL NOT introduce a validated status or require migration, reseeding, or changes to unrelated RC Atlas modules.

#### Scenario: Existing clients read the hardened workflow
- **WHEN** an existing authorized client calls the current demo task and workplan routes after the change
- **THEN** it receives the established response fields and status values with stricter rejection only for invalid identity, authorization, or transition requests

#### Scenario: Broader RC Atlas surfaces remain unaffected
- **WHEN** Portfolio, Workplan presentation, logical framework, indicators, reporting, notifications, administration, or other non-MVP modules are used
- **THEN** their existing data contracts and behavior remain unchanged except where they display the corrected task workflow state
