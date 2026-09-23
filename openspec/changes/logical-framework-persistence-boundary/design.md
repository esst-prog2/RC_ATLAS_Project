## Context

See `proposal.md` for motivation. The active Logical Framework routes currently load the complete application aggregate, construct `LogicalFrameworkService(LogicalFrameworkRepository(data))`, mutate in-memory collections, append an audit event in the route, and call the global save function. The repository enforces useful ownership and relationship semantics but is concretely coupled to a `LogicalFrameworkState` containing projects, results, links, and embedded indicators.

The canonical write path serializes the complete `LogiTrackData` aggregate to JSON or to the SQLite `app_state` JSON blob. Relational SQLite tables are rebuilt afterward as a derived projection. JSON replacement and the SQLite blob transaction protect an individual save, but no transaction owns the full load, validation, mutation, audit, canonical save, and projection sequence. The process lock is not a multi-process concurrency guarantee.

The existing `ResultNode` and `IndicatorResultLink` models, domain rules, API routes, permission behavior, project cloning, snapshot formats, projection tables, and Studio interface are protected compatibility contracts.

## Goals / Non-Goals

**Goals:**

- Establish the dependency direction `API -> Logical Framework application service -> unit of work -> scoped repository contract -> compatibility adapter`.
- Keep `LogiTrackData` private to the compatibility adapter and legacy outer operations.
- Give each ordinary Logical Framework write one canonical commit containing both domain and success-audit changes.
- Define repository semantics that can be exercised by one reusable contract suite and later implemented by another datastore.
- Preserve current APIs, business rules, permissions, IDs, snapshots, projection behavior, project cloning, and frontend behavior.
- Define the existing Logical Framework HTTP behavior as a black-box, client-independent contract that remains stable across persistence adapters.
- Make current atomicity and concurrency limits explicit instead of overstating guarantees.

**Non-Goals:**

- Making relational SQLite or PostgreSQL authoritative.
- Solving global or task-workflow concurrency.
- Moving Project, Indicator, Task, or Activity models.
- Rewriting hierarchy, clone, authorization, audit, snapshot, or projection behavior.
- Adding a universal repository base class, generic ORM abstraction, migration framework, or new dependency.
- Changing frontend files, API DTOs, seed data, runtime data, or unrelated domains.
- Creating RC Atlas Next or introducing React, TypeScript, frontend modularization, CORS changes, token/session changes, multi-session authentication, API v2, or broad error-contract redesign.

## Decisions

### 1. Add a Logical Framework application coordinator rather than moving rules into routes or adapters

A narrow application-service layer will coordinate authorization-derived scope, unit-of-work lifetime, the existing domain service, audit preparation, commit, and error propagation. The existing `LogicalFrameworkService` remains responsible for hierarchy, ordering, link, archive, delete, and clone rules and will depend only on a repository contract.

The coordinator will not contain FastAPI response construction or storage-specific code. Routes will continue mapping the existing validation categories to their current HTTP responses.

**Alternatives considered:** Keeping transaction orchestration in routes would perpetuate duplicated audit/save ordering. Moving business validation into repositories would couple rules to storage. Rewriting the existing service would create unnecessary regression risk.

### 2. Use a capability-specific unit of work

The new unit of work will expose only the repository access and audit staging needed by the Logical Framework slice. It will support explicit commit and discard/rollback semantics and will prevent a second effective commit.

Conceptually, a write operation is:

1. Existing authentication, permission, and project-access checks establish an immutable actor and requested organization/project context.
2. The application service begins one Logical Framework unit of work.
3. The unit of work provides a repository bound to an explicit scope.
4. The existing domain service performs validation and mutations through that repository.
5. The application service stages the existing audit payload through the unit of work.
6. The unit of work performs one canonical commit.
7. Derived projection synchronization runs after canonical commit.

A read operation may use the same scoped repository factory but closes without a write commit.

**Alternatives considered:** A global RC Atlas unit of work would force premature decisions for every domain. A generic snapshot transaction callback would formalize whole-state mutation as the long-term abstraction. Neither is appropriate for the first slice.

### 3. Bind repository access to explicit scope

A small immutable scope value containing `organization_id` and `project_id` will be required to obtain a project repository from the unit of work. Once scoped, repository methods operate on result and indicator identifiers without accepting arbitrary replacement scope values.

The contract will cover project existence, result listing/retrieval/save/delete, indicator existence, link listing/retrieval/save/delete, and the current exception categories. Every adapter query or in-memory selection must include both ownership dimensions. Cross-scope records must never be returned; existing route mapping continues to conceal those records as not found.

For same-organization project cloning, one unit of work may request repositories for the source and destination scopes. Cross-organization cloning remains rejected.

**Alternatives considered:** Passing organization/project parameters to every method is explicit but easier to mix accidentally. Hiding scope only in caller conventions would not create a tenant-safe persistence boundary.

### 4. Keep the current aggregate private inside a snapshot compatibility adapter

The first concrete unit of work will load one fresh `LogiTrackData` instance through the existing persistence functions and retain it privately. Its scoped repository adapter will operate on that private state. The application service and domain service will not receive or return the aggregate.

On commit, the adapter will stage the audit event into the same private aggregate and call the canonical snapshot save exactly once. Validation failures and pre-commit exceptions discard the private state without calling save. Existing deserialization continues treating missing Logical Framework collections as empty.

This adapter is deliberately transitional. Its public contract must contain no JSON paths, SQLite handles, serialized dictionaries, relational-table operations, or full-state replacement methods.

**Alternatives considered:** Copying the current `LogicalFrameworkState` protocol unchanged would expose aggregate collections and make a future SQL adapter imitate in-memory lists. Directly writing the relational projection would create two authorities and require migration now.

### 5. Define canonical commit and projection synchronization separately

The compatibility adapter defines canonical commit as successful persistence of the complete snapshot containing both the domain mutation and success audit. JSON atomic replacement and the SQLite `app_state` transaction retain their current behavior for this step.

Relational synchronization remains an after-commit projection operation. If synchronization fails after canonical commit, the operation is canonically committed and must not be reported as rolled back. Existing synchronization diagnostics record the failure, and reconciliation rebuilds projection tables from canonical state.

This design therefore guarantees domain/audit atomicity only within the canonical snapshot. It does not claim an atomic transaction spanning the snapshot and relational projection. The implementation must make this phase distinction testable and must not emit a second domain commit during reconciliation.

**Alternatives considered:** Treating projection failure as canonical rollback is impossible after the snapshot has committed. Writing projection first can expose uncommitted state. Distributed transaction machinery is outside scope.

### 6. Stage success audit events inside the unit of work

Routes will provide the existing actor, action, target, endpoint, and details information to the application operation. The unit of work stages the corresponding `AuditEvent` only after domain validation and mutation succeed and before canonical commit.

If validation or authorization fails, no unit of work commit occurs and no success audit is staged. If canonical save fails, the staged domain and audit changes are discarded together from the request-local state. Existing failure logging may remain outside this success-audit contract.

**Alternatives considered:** Appending audit after persistence permits successful mutations without their audit. Appending to separately persistent audit storage before domain commit creates false success records.

### 7. Preserve project-clone outer transaction ownership

Project cloning is a cross-domain operation that currently creates a project and copies its Logical Framework before one snapshot save. This change will not split it into independent project and Logical Framework commits.

The compatibility implementation will allow the clone orchestration to use the scoped Logical Framework repository against the same request-private compatibility unit of work while the existing project-clone operation remains the outer transaction owner. The domain clone rules continue producing independent result IDs and preserve current indicator-link behavior. This narrow participation path is transitional and does not expose `LogiTrackData` to the Logical Framework service.

**Alternatives considered:** Committing Logical Framework cloning separately could leave a project without its hierarchy or a hierarchy without a project. Migrating the complete project repository is outside this change.

### 8. Preserve the existing error taxonomy and API contract

Repository adapters will report missing records, ownership violations, and conflicts using the current Logical Framework repository error categories. The domain service continues translating these to validation categories, and routes continue their current HTTP mappings.

No new route, payload field, response field, status code, permission, or frontend expectation is introduced. Persistence infrastructure failures remain server errors and must not be translated into business validation failures.

The HTTP contract is defined independently of `logitrack_studio.html`. For the same authenticated request and canonical state, the route must expose the same methods, paths, required inputs, status codes, complete response shapes, field names, ownership identifiers, hierarchy ordering, mutation results, and structured error form to any authorized client. Current human-readable error text is characterized only where existing behavior already relies on it; this change does not introduce a broad error-code system or freeze incidental prose.

The application coordinator and serializers remain on the server side of the persistence boundary, so replacing the compatibility adapter in the future cannot require a frontend contract change.

### 9. Use adapter-independent contract tests

A shared repository contract suite will be expressed as tests against a factory that supplies an isolated unit of work and fixture data. The snapshot compatibility adapter will be its first implementation. A future adapter must pass the same scope, CRUD, ordering, link, conflict, and transaction scenarios before integration.

Separate black-box API compatibility tests will preserve current route behavior without using Studio source inspection as evidence of the server contract. They will cover the complete success/error shapes and the allowed/rejected operations for Organization Admin, Programme Manager, MEAL Officer, Field Coordinator, and Executive Viewer. Studio structural tests remain a client regression gate, while JSON, SQLite snapshot, old-snapshot, projection, audit, clone, and full RC Atlas regression tests remain integration gates.

### 10. Leave concurrency policy open behind the contract

The unit-of-work API will allow a persistence conflict to be represented distinctly from domain validation, but the compatibility adapter will not claim cross-process lost-update prevention. It may retain the current process-local locking behavior.

A later stabilization change can add snapshot revisions, optimistic compare-and-swap, or database locking without changing hierarchy rules or API orchestration. Last-write-wins is not part of the repository contract.

## Risks / Trade-offs

- **[Risk] The compatibility adapter can look permanent because it passes the new contracts.** -> Name and document it explicitly as snapshot compatibility infrastructure; prohibit aggregate-specific methods in the public contracts.
- **[Risk] Adding an application coordinator duplicates some existing route orchestration temporarily.** -> Migrate only Logical Framework routes and delete their old local audit/save helper once equivalent tests pass.
- **[Risk] Scope binding can change internal error classification.** -> Preserve existing repository exception categories and API mapping with contract and route tests.
- **[Risk] Projection failure occurs after an irreversible canonical commit.** -> Treat projection as derived, surface stale synchronization diagnostics, and test reconciliation rather than claiming rollback.
- **[Risk] Project cloning crosses the new and legacy boundaries.** -> Keep one outer compatibility unit of work and one canonical commit; defer Project repository extraction.
- **[Risk] Two concurrent processes can still overwrite snapshot changes.** -> Document the limitation, avoid specifying last-write-wins, and defer explicit conflict control to the next stabilization slice.
- **[Risk] Contract tests may accidentally encode list-based implementation details.** -> Assert domain outcomes, scope, ordering, errors, commit behavior, and persisted reload results only.

## Migration Plan

1. Capture the current Logical Framework API, audit, JSON/SQLite round-trip, projection, and clone behavior with focused regression tests.
2. Define the scoped repository and Logical Framework unit-of-work protocols plus persistence-level error semantics.
3. Implement the snapshot compatibility unit of work over existing load/save, hydration, audit, and projection functions without changing file formats.
4. Adapt the existing repository implementation to the scoped contract while retaining current domain models and validation behavior.
5. Add the application coordinator and migrate ordinary Logical Framework reads and writes from route-owned state/save orchestration.
6. Adapt project cloning to participate in one outer compatibility unit of work without creating a second commit.
7. Run adapter contract tests, Logical Framework unit/API tests, Studio structural regression tests, and the complete unittest suite.

Rollback consists of restoring the prior route dependency wiring and aggregate-backed repository construction. No data rollback or migration is required because snapshot formats and canonical records do not change.

## Open Questions

- The later concurrency stabilization change must choose between optimistic snapshot revisions and another conflict mechanism; this design intentionally preserves that option.
- The point at which the relational representation becomes authoritative will be decided with the future database-adapter and migration design, not by this compatibility slice.
