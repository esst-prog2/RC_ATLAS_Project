## Purpose

Define a storage-neutral, tenant-safe persistence and transaction contract for Logical Framework writes while preserving the current RC Atlas APIs, domain behavior, snapshots, and derived relational projection.

## ADDED Requirements

### Requirement: Storage-neutral Logical Framework persistence
The system SHALL expose Logical Framework result and indicator-link persistence through a domain-specific contract that does not expose the application snapshot, JSON representation, SQLite connection details, or relational projection internals to Logical Framework business rules.

#### Scenario: Business rule executes independently of storage format
- **WHEN** a Logical Framework business operation retrieves or persists results or indicator links
- **THEN** it uses the Logical Framework persistence contract without receiving the complete application state or selecting a storage backend

#### Scenario: Alternative adapter remains possible
- **WHEN** a future persistence adapter implements the same contract
- **THEN** existing Logical Framework hierarchy and linking rules can execute without modification

### Requirement: Explicit organization and project scope
Every repository operation SHALL execute within an explicit organization and project scope and SHALL prevent records owned by another organization or project from being returned or mutated.

#### Scenario: Organization isolation
- **WHEN** an operation requests a result, indicator, or link owned by another organization
- **THEN** the operation is rejected using the existing non-disclosing API semantics and no state is changed

#### Scenario: Project isolation
- **WHEN** an operation requests a result, indicator, or link from another project in the same organization
- **THEN** the operation is rejected and no state is changed

#### Scenario: Scoped collection retrieval
- **WHEN** results or indicator links are listed for a project
- **THEN** only records belonging to the specified organization and project are returned

### Requirement: Existing result persistence semantics
The repository contract SHALL preserve the existing Goal, Outcome, and Output retrieval, creation, update, ordering, archive, and delete semantics, including stable identifiers and deterministic ordering.

#### Scenario: Result creation and update
- **WHEN** a valid result is created or updated within its scope
- **THEN** its identifier, ownership, hierarchy, status, ordering, and timestamps are persisted without changing existing API behavior

#### Scenario: Missing result
- **WHEN** a scoped operation requires a result identifier that does not exist in that scope
- **THEN** it reports the existing not-found behavior and does not create or mutate a record implicitly

#### Scenario: Duplicate or conflicting result identifier
- **WHEN** a result identifier already exists in the same or another ownership scope
- **THEN** the operation reports the applicable existing validation, conflict, or concealed-scope behavior and does not overwrite the existing record

#### Scenario: Sibling reordering
- **WHEN** a valid complete set of siblings is reordered
- **THEN** every sibling order change is committed together with deterministic resulting order

#### Scenario: Protected deletion
- **WHEN** a result still has child results or indicator links
- **THEN** deletion is rejected and neither the result nor its dependencies are changed

### Requirement: Existing hierarchy validation
The new persistence boundary SHALL preserve all current Logical Framework hierarchy invariants and SHALL NOT move responsibility for business hierarchy rules into a storage-specific adapter.

#### Scenario: Valid hierarchy
- **WHEN** an Outcome references a Goal or an Output references an Outcome in the same organization and project
- **THEN** the hierarchy operation is accepted

#### Scenario: Invalid hierarchy
- **WHEN** a Goal has a parent, a result has an invalid parent level, a result parents itself, or a parent is unknown or outside scope
- **THEN** the operation is rejected before commit

#### Scenario: Result-level transition
- **WHEN** an update attempts to change an existing result from one result level to another
- **THEN** the operation is rejected before commit

### Requirement: Existing indicator-result link semantics
The repository contract SHALL preserve the rule that an existing indicator can be unassigned or linked to one Outcome or one Output within the same organization and project.

#### Scenario: Link or relink indicator
- **WHEN** an authorized operation links an in-scope indicator to an in-scope Outcome or Output
- **THEN** one canonical link is persisted using the existing indicator and result identifiers

#### Scenario: Unlink indicator
- **WHEN** an authorized operation unlinks an existing canonical indicator-result relationship
- **THEN** the relationship is removed without deleting or recreating the indicator or result

#### Scenario: Invalid indicator link
- **WHEN** a link targets a Goal, an unknown record, or a record outside the indicator's organization or project
- **THEN** the operation is rejected and no link change is committed

### Requirement: Logical Framework unit of work
Every Logical Framework write operation SHALL execute within one explicit unit of work that owns scoped repository access and permits at most one successful commit.

#### Scenario: Unit of work begins after request authorization
- **WHEN** a request has passed existing authentication, permission, and project-access checks
- **THEN** one unit of work is opened for the requested Logical Framework operation

#### Scenario: Successful commit
- **WHEN** all business validation, repository mutations, and audit preparation succeed
- **THEN** the unit of work commits the canonical Logical Framework and audit changes once

#### Scenario: Read operation
- **WHEN** a Logical Framework request performs no mutation
- **THEN** it does not commit a write transaction

#### Scenario: Repeated commit
- **WHEN** code attempts to commit the same unit of work more than once
- **THEN** the repeated commit is rejected or has no persistence effect

### Requirement: Failure and rollback behavior
An unsuccessful Logical Framework operation SHALL NOT durably persist its proposed domain or audit changes to the canonical snapshot.

#### Scenario: Validation failure
- **WHEN** business validation fails after the unit of work has loaded state
- **THEN** the unit of work is discarded without a canonical save and without a success audit event

#### Scenario: Canonical persistence failure
- **WHEN** the JSON or SQLite canonical snapshot cannot be committed
- **THEN** the operation reports failure and neither its domain mutation nor its success audit event is treated as durably committed

#### Scenario: Unexpected operation failure
- **WHEN** an unexpected error occurs before canonical commit
- **THEN** the unit of work is rolled back or discarded and does not perform a later implicit save

### Requirement: Audit atomicity
Each successful Logical Framework mutation SHALL persist its corresponding success audit event in the same canonical snapshot commit as the domain mutation.

#### Scenario: Successful audited mutation
- **WHEN** a Logical Framework mutation commits successfully
- **THEN** the canonical state contains both the domain change and exactly the corresponding existing audit event data

#### Scenario: Failed mutation is not audited as success
- **WHEN** authorization, validation, repository mutation, or canonical persistence fails before commit
- **THEN** no success audit event for that mutation is durably persisted

### Requirement: Snapshot compatibility adapter
The initial adapter SHALL preserve existing JSON and SQLite snapshot formats, old-snapshot hydration, and current Logical Framework data without requiring migration or reseeding.

#### Scenario: Existing JSON snapshot
- **WHEN** RC Atlas loads and writes an existing JSON snapshot through the compatibility adapter
- **THEN** existing Logical Framework results, indicator links, identifiers, and unrelated application data remain usable

#### Scenario: Existing SQLite snapshot
- **WHEN** RC Atlas loads and writes the SQLite `app_state` snapshot through the compatibility adapter
- **THEN** the same Logical Framework and unrelated application data remain usable

#### Scenario: Snapshot without Logical Framework data
- **WHEN** an older snapshot contains no canonical Logical Framework collections
- **THEN** it loads as an empty Logical Framework without application failure or destructive migration

### Requirement: Relational projection reconciliation
The relational SQLite representation SHALL remain a derived projection updated after canonical snapshot commit and SHALL be reconcilable from canonical state.

#### Scenario: Projection synchronization succeeds
- **WHEN** canonical commit succeeds and projection synchronization is available
- **THEN** the projection is refreshed with the committed results, links, ownership, ordering, and audit data

#### Scenario: Projection synchronization fails after canonical commit
- **WHEN** the canonical snapshot has committed but projection synchronization fails
- **THEN** the canonical mutation and audit remain committed, the projection is identified as stale or failed through existing synchronization diagnostics, and a later reconciliation can rebuild it

#### Scenario: Projection is not treated as an independent authority
- **WHEN** the snapshot and projection differ during this compatibility phase
- **THEN** canonical Logical Framework reads and subsequent reconciliation use the snapshot as the source of truth

### Requirement: Client-independent API and current user-interface compatibility
The Logical Framework HTTP API SHALL remain a client-independent contract and SHALL preserve existing routes, authentication, permissions, request fields, response structures, status mappings, project-clone results, and Studio behavior. For the same authenticated request and persisted state, backend behavior SHALL be the same regardless of whether the caller is the current Studio or another authorized client, and SHALL NOT depend on Studio markup, DOM structure, JavaScript state, or a specific frontend implementation.

#### Scenario: Existing API regression suite
- **WHEN** current Logical Framework API requests are executed against the compatibility adapter
- **THEN** successful responses and existing validation, not-found, conflict, authentication, and authorization outcomes remain compatible

#### Scenario: Black-box successful contract
- **WHEN** a client exercises a successful Logical Framework request through HTTP
- **THEN** the existing method, route path, required path/query/body inputs, success status, complete response structure, field names, identifiers, ownership fields, hierarchy ordering, and mutation response behavior are preserved

#### Scenario: Black-box error contract
- **WHEN** a client submits an unauthenticated, unauthorized, missing-record, invalid-hierarchy, archived-project, cross-scope, or dependency-conflict request
- **THEN** the existing HTTP status and JSON error payload structure are preserved without requiring incidental human-readable wording to become a new formal error-code contract

#### Scenario: Permission matrix is enforced by the API
- **WHEN** Organization Admin, Programme Manager, MEAL Officer, Field Coordinator, and Executive Viewer identities exercise Logical Framework reads and mutations
- **THEN** every currently allowed operation succeeds and every currently rejected operation is denied by the backend independently of frontend visibility

#### Scenario: Persistence adapter does not change HTTP behavior
- **WHEN** the Logical Framework application boundary is exercised through any conforming persistence adapter
- **THEN** it produces the same externally observable request, response, permission, scope, ordering, mutation, and error behavior

#### Scenario: Project cloning
- **WHEN** a project is cloned under the existing project-clone policy
- **THEN** its Logical Framework hierarchy is cloned with independent result identifiers and the current indicator-link behavior, within the existing outer project persistence operation

#### Scenario: Existing Studio behavior
- **WHEN** users view or mutate the Logical Framework through the current Studio
- **THEN** no frontend source or interaction contract change is required

### Requirement: Concurrency-neutral contract
The persistence contract SHALL NOT require last-write-wins behavior and SHALL permit a future adapter to apply optimistic versioning, database locking, or another explicit conflict strategy.

#### Scenario: Current compatibility limitation
- **WHEN** multiple processes modify the current snapshot concurrently
- **THEN** the adapter documentation identifies that global lost-update prevention is not guaranteed by this change

#### Scenario: Future conflict handling
- **WHEN** a future adapter detects a concurrent-write conflict
- **THEN** it can report that conflict through the persistence boundary without changing Logical Framework business rules
