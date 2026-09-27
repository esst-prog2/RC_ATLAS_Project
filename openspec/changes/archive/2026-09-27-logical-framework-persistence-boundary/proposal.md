## Why

Logical Framework writes currently mutate the complete `LogiTrackData` snapshot and rely on route-level audit-and-save coordination, so application rules remain coupled to snapshot storage and do not have an explicit transaction boundary. RC Atlas needs one narrow, compatibility-first persistence boundary before future database adapters can be introduced without rewriting Logical Framework business rules or changing approved application behavior.

## What Changes

- Introduce a storage-neutral, organization- and project-scoped Logical Framework repository contract expressed in domain operations rather than whole-state persistence.
- Introduce a Logical Framework unit-of-work contract that owns repository access, one successful commit, rollback/discard behavior, and the audit event associated with each write operation.
- Add a snapshot compatibility adapter that keeps `LogiTrackData`, JSON persistence, SQLite snapshot persistence, old snapshot hydration, and relational projection synchronization behind the new boundary.
- Refactor Logical Framework write orchestration to use the unit of work while preserving current routes, payloads, responses, permissions, hierarchy rules, stable IDs, clone behavior, and frontend behavior.
- Treat the existing Logical Framework HTTP API as a client-independent contract whose behavior does not depend on Studio markup, DOM state, or any specific frontend implementation.
- Define explicit missing-record, scope, duplicate/conflict, ordering, archive/delete, and indicator-link semantics that can be reused by a future persistence adapter.
- Add reusable repository and unit-of-work contract tests plus API, snapshot, projection, tenant-isolation, audit-atomicity, and full regression coverage.
- Document the existing global lost-update limitation without claiming or implementing global concurrency safety.

## Capabilities

### New Capabilities

- `logical-framework-persistence-boundary`: Storage-neutral repository, unit-of-work, tenant-scope, commit, rollback, audit, and compatibility requirements for Logical Framework writes.

### Modified Capabilities

None.

## Impact

- Affected planning targets: `repositories/logical_framework_repository.py`, `services/logical_framework_service.py`, `api/logical_framework_routes.py`, focused persistence adapters, composition-root dependency wiring, and Logical Framework tests.
- Existing Logical Framework API paths and externally observable request/response behavior remain compatible.
- Existing `ResultNode` and `IndicatorResultLink` models, hierarchy rules, permissions, ownership checks, stable identifiers, project cloning behavior, JSON/SQLite snapshots, and relational projection remain available.
- The current snapshot remains the persistence implementation for this change; PostgreSQL, schema migration, global concurrency control, and unrelated domain extraction are explicitly deferred.
- No frontend file, future parallel frontend, dependency, seed data, runtime data, or unrelated RC Atlas domain is changed by this proposal.
