## ADDED Requirements

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
