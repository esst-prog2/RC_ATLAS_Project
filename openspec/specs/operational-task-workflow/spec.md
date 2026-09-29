# operational-task-workflow Specification

## Purpose
Defines the authenticated, persistent task-assignment and validation workflow that RC Atlas must demonstrate as the course MVP without expanding into unrelated product capabilities.

## Requirements

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

### Requirement: Task drawer hands off to authoritative Workplan controls
The Studio SHALL provide a task-specific handoff from the task drawer to the existing Workplan Operational Coordination Engine. The handoff SHALL retain the selected task identifier only while targeting, close the drawer before navigation, keep the existing Workplan action generation authoritative, expand the matching task controls after hydration, focus the progress input or first valid action, and clear temporary targeting state after success. It SHALL NOT duplicate or broaden workflow authorization in the drawer.

#### Scenario: Assigned Field user opens existing workflow controls
- **WHEN** an authenticated Field Coordinator selects Open workflow controls for a task canonically assigned to that user
- **THEN** the drawer closes before Workplan is shown and the existing Workplan task controls are targeted for that task

#### Scenario: Correct task is expanded and focused after hydration
- **WHEN** Workplan hydration completes for a pending drawer handoff and the selected task is present
- **THEN** the matching task control is expanded, its progress input or first valid workflow action receives focus, and the temporary target is cleared

#### Scenario: Target cannot be located
- **WHEN** Workplan hydration completes but the selected task is absent, inaccessible, or no longer actionable
- **THEN** the system clears the temporary target, reports the failure gracefully, and does not reveal or create additional workflow controls

#### Scenario: Field authorization remains authoritative
- **WHEN** a Field Coordinator reaches Workplan for a task assigned to another user
- **THEN** the existing Workplan authorization does not offer a permitted update action and the backend continues to reject any attempted mutation

### Requirement: Default coordination activity placement is idempotent and scoped
When task creation omits activity_id, the system SHALL derive the stable project-local coordination activity identifier and create at most one compatible default coordination activity for that organization and project. It SHALL reuse exactly one compatible existing activity, SHALL NOT identify the activity by title, and SHALL reject duplicate, foreign, cross-project, malformed, or structurally incompatible stable-ID states without persisting any part of the attempted task creation. Explicit activity identifiers SHALL also resolve within the authenticated organization and selected project.

#### Scenario: First implicit activity is created
- **WHEN** an authorized manager creates a task without activity_id and no matching default coordination activity exists in the scoped project
- **THEN** the system creates one compatible project-local coordination activity and places the task in it

#### Scenario: Repeated implicit creation reuses one activity
- **WHEN** two tasks are created without activity_id in the same organization and project
- **THEN** both tasks use the same single default coordination activity and no duplicate activity identifier is appended

#### Scenario: Different projects receive distinct defaults
- **WHEN** tasks without activity_id are created in two different projects
- **THEN** each task uses the stable default coordination activity belonging to its own organization and project

#### Scenario: Existing duplicate default activities fail closed
- **WHEN** more than one matching default coordination activity already exists for the scoped project
- **THEN** task creation rejects the corrupted state without choosing an activity or persisting a task, audit event, notification, or projection change

#### Scenario: Foreign or incompatible stable identifier fails closed
- **WHEN** the derived stable activity identifier exists only under another organization or project, or the scoped record is structurally incompatible with a coordination activity
- **THEN** task creation rejects the request without mutating canonical or derived state

#### Scenario: Explicit activity identifier is scoped
- **WHEN** task creation supplies an activity_id
- **THEN** the system accepts exactly one compatible activity in the authenticated organization and selected project and conceals or rejects foreign and colliding matches without mutation

#### Scenario: Failed creation is atomic
- **WHEN** activity resolution, assignee validation, task validation, or persistence fails during task creation
- **THEN** no partial activity, task, successful audit event, notification, canonical save, or attributable projection mutation remains

### Requirement: Browser acceptance preserves the canonical workflow
The browser workflow SHALL continue to use the existing task states, permissions, routes, and role transitions. Acceptance SHALL require the full Programme Manager to Field to MEAL to Programme Manager journey and the MEAL return branch to succeed through the current Studio and remain persisted after refresh or re-login.

#### Scenario: Golden Journey completes through existing controls
- **WHEN** a Programme Manager assigns a task, the assigned Field Coordinator opens the Workplan controls from the drawer, updates and submits it, a MEAL Officer validates it, and the Programme Manager approves it
- **THEN** the task becomes Completed with the existing submission, validation, approval, activity-history, and audit semantics

#### Scenario: Return and resubmission remain valid
- **WHEN** a MEAL Officer returns submitted work and the assigned Field Coordinator corrects and resubmits it
- **THEN** the task follows the existing In Progress and pending_validation transitions and remains eligible for later validation and final approval

#### Scenario: No validated task status is introduced
- **WHEN** MEAL validation succeeds
- **THEN** the task remains in pending_validation with validated_at recorded until Programme Manager approval completes it

#### Scenario: Browser handoffs persist across sessions
- **WHEN** each Golden Journey actor refreshes or signs in again after a successful transition
- **THEN** the next actor observes the latest canonical task state without an unexpected 401 or 403 for an otherwise authorized action
