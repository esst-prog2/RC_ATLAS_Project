## Purpose

Defines how authoritative canonical snapshot collections remain protected from stale derived projections and how local duplicate coordination activity data is repaired safely.

## ADDED Requirements

### Requirement: Canonical collection presence controls hydration
For each repository-backed domain, hydration SHALL preserve the canonical snapshot collection whenever that domain key is present in the serialized snapshot. An explicitly present empty collection SHALL remain authoritative. Derived repository data MAY backfill a supported domain only when its canonical key is genuinely absent under an explicit legacy compatibility path, and SHALL NOT overwrite newer canonical authentication or operational state.

#### Scenario: Present canonical users override stale projection
- **WHEN** the canonical snapshot contains a users collection with a newer token hash and the derived user projection contains stale user state
- **THEN** hydration preserves the canonical users collection and the newly issued token remains valid for the authenticated identity endpoint

#### Scenario: Present but empty remains authoritative
- **WHEN** a supported canonical domain key is present with an empty collection while its derived repository contains rows
- **THEN** hydration keeps the canonical collection empty and does not repopulate it from the projection

#### Scenario: Absent legacy domain can be backfilled
- **WHEN** a genuine legacy snapshot omits a supported canonical domain key and a valid compatible repository projection exists
- **THEN** the explicitly supported compatibility path may backfill that absent domain

#### Scenario: Presence is decided per domain
- **WHEN** one supported canonical domain key is present and another supported domain key is absent
- **THEN** hydration preserves the present domain independently and considers backfill only for the absent domain

### Requirement: Derived synchronization failures are isolated after canonical commit
After canonical snapshot persistence succeeds, synchronization of the broad relational projection and synchronization of independently repository-backed domains SHALL be attempted as distinct derived operations. Failure in one derived operation SHALL NOT silently skip another eligible synchronization attempt, replace canonical state, or be reported as canonical rollback. Each failure SHALL remain separately diagnosable while preserving the existing strict and non-strict external synchronization policy.

#### Scenario: Broad projection failure does not skip repository synchronization
- **WHEN** canonical persistence succeeds and broad relational projection synchronization fails
- **THEN** eligible repository-backed domain synchronization is still attempted and its outcome is recorded separately

#### Scenario: Newly issued token survives unrelated projection failure
- **WHEN** login writes a fresh token hash to canonical users and a non-auth relational projection domain fails afterward
- **THEN** a later load preserves the canonical token and the authenticated identity request accepts it

#### Scenario: Repository synchronization failure is separately diagnosable
- **WHEN** broad relational projection synchronization succeeds but a repository-backed domain synchronization fails
- **THEN** the system records the repository failure independently and does not claim that canonical data was rolled back

#### Scenario: Canonical commit truth is preserved
- **WHEN** any derived synchronization fails after canonical persistence
- **THEN** diagnostics and any returned strict-mode failure distinguish the committed canonical state from the stale or failed derived projection

### Requirement: Duplicate coordination activity repair is guarded and lossless
The system SHALL provide a dry-run-first local repair for the known duplicate default coordination activity. Apply mode SHALL require a stopped local server, a timestamped canonical backup, exact organization/project/activity identity validation, task-ID collision checks, and successful staged validation before one atomic canonical save. The repair SHALL retain one valid activity, preserve both task objects and their fields and history, stable-deduplicate linked indicator identifiers, remove only the redundant activity container, and rebuild the derived projection from corrected canonical state.

#### Scenario: Dry run identifies known corruption without mutation
- **WHEN** dry-run examines the expected org_blue_delta and proj_resilience workspace containing two act_proj_resilience_coordination activities, 11 activities, and 20 tasks
- **THEN** it reports the proposed merge and expected 10-activity and 20-task result without changing canonical or derived data

#### Scenario: Apply requires backup and exact preconditions
- **WHEN** repair apply mode is requested
- **THEN** it proceeds only after server-stop confirmation, timestamped canonical backup creation, exact ownership and project checks, and validation that task identifiers will remain unique

#### Scenario: Repair preserves both browser-created tasks
- **WHEN** the known duplicate containers hold task_proj_resilience_test and task_proj_resilience_test2
- **THEN** the repaired canonical project retains both complete task objects under the retained coordination activity with their organization, project context, assignee, status, progress, timestamps, evidence, comments, and history unchanged

#### Scenario: Repair produces validated canonical postconditions
- **WHEN** the staged repair passes all checks and is applied
- **THEN** canonical state contains exactly 10 activities, 20 tasks, one act_proj_resilience_coordination activity, unique activity and task IDs, valid ownership, and stable-deduplicated linked indicator IDs

#### Scenario: Derived projection is rebuilt from corrected canonical state
- **WHEN** the corrected canonical snapshot is saved successfully
- **THEN** the relational projection is rebuilt from that snapshot and succeeds without making the projection authoritative

#### Scenario: Pre-save validation failure aborts safely
- **WHEN** any expected count, identifier, ownership, compatibility, task collision, staged postcondition, or projection rehearsal check fails
- **THEN** repair aborts before canonical mutation and reports the failed condition

#### Scenario: Unexpected post-commit projection failure remains truthful
- **WHEN** canonical repair commits after successful rehearsal but the production projection rebuild unexpectedly fails
- **THEN** the tool reports canonical repair as committed, reports projection reconciliation as failed, retains the backup, and does not claim canonical rollback or hydrate stale projection data over canonical state
