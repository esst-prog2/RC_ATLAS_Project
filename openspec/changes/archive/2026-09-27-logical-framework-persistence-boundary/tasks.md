## 1. Baseline and Characterization

- [x] 1.1 Run the existing Logical Framework domain/API tests and the complete `py -m unittest discover -v -p "*tests.py"` suite before implementation; record the 134-test baseline or stop and report any pre-existing failure.
- [x] 1.2 Add black-box HTTP characterization tests for current methods, route paths, required path/query/body inputs, success statuses, complete success shapes, field names, IDs and ownership fields, hierarchy ordering, mutation responses, error statuses and payload structures, success-audit payloads, project-clone outcomes, JSON/SQLite round trips, and relational projection contents; verify they pass against the unmodified persistence path before switching route wiring.
- [x] 1.3 Add a two-writer characterization test that demonstrates the current snapshot lost-update limitation without changing production behavior; verify the test documents the limitation rather than asserting false concurrency safety.

## 2. Persistence Contracts

- [x] 2.1 Define the immutable organization/project scope and the storage-neutral Logical Framework repository protocol for projects, results, indicators, and links; verify no public type or method exposes `LogiTrackData`, file paths, serialized dictionaries, SQLite connections, or projection tables.
- [x] 2.2 Define Logical Framework persistence error semantics for not found, concealed scope, duplicate/conflict, canonical persistence failure, and future concurrent-write conflict; verify existing service/API error mappings remain representable.
- [x] 2.3 Define the capability-specific unit-of-work protocol with scoped repository access, audit staging, one effective commit, discard/rollback, and context cleanup; verify it contains no PostgreSQL-specific or universal-repository behavior.
- [x] 2.4 Build an adapter-independent repository contract test harness covering scoped retrieval, save/update, deterministic ordering, protected deletion, indicators, links, missing records, and conflicts; verify the harness runs against a supplied isolated adapter factory.

## 3. Snapshot Compatibility Adapter

- [x] 3.1 Implement the Logical Framework snapshot unit of work so it privately loads current state and exposes only scoped repositories; verify application/domain services cannot access the complete aggregate through the new contract.
- [x] 3.2 Adapt current result and indicator-link persistence to the scoped repository contract while preserving hierarchy, stable IDs, timestamp, archive/delete, and link semantics; verify the shared repository contract suite passes.
- [x] 3.3 Implement request-local mutation and discard behavior so validation or pre-commit failure does not call canonical save; verify commit-count and persisted-reload tests prove zero writes on failure and one write on success.
- [x] 3.4 Stage the existing success audit event inside the unit of work and persist it with the domain mutation in one canonical snapshot save; verify failure-injection tests never persist only one side of the canonical domain/audit pair.
- [x] 3.5 Keep relational synchronization after canonical commit, preserve synchronization diagnostics, and support reconciliation from canonical state; verify a forced projection failure leaves canonical domain/audit data intact and a later rebuild restores matching projection rows.
- [x] 3.6 Verify the adapter against existing JSON snapshots, SQLite `app_state` snapshots, and snapshots with absent Logical Framework collections; confirm no migration, reseed, identifier change, or unrelated-data loss occurs.

## 4. Application and Route Integration

- [x] 4.1 Add the narrow Logical Framework application coordinator that owns unit-of-work lifetime, invokes the existing domain service, stages audit details, and commits once; verify existing hierarchy and linking service tests pass without duplicating business rules and that externally observable results do not depend on the persistence adapter.
- [x] 4.2 Replace route-owned `LogiTrackData`, repository construction, and `audit_and_save` orchestration with authorized scope plus application-service calls; verify black-box tests preserve every existing Logical Framework method, route path, required input, complete success/error shape, status, authentication outcome, and the allowed/rejected operation matrix for Organization Admin, Programme Manager, MEAL Officer, Field Coordinator, and Executive Viewer.
- [x] 4.3 Preserve read behavior without write commits and archived-project mutation guards before unit-of-work commit; verify read-only and archived-project API tests pass and commit counters remain zero for reads/rejections.
- [x] 4.4 Adapt project cloning to use scoped Logical Framework persistence inside the existing outer project snapshot operation, without a second canonical commit; verify cloned hierarchy IDs, parent mappings, current indicator-link behavior, organization scope, and archived-source policy remain unchanged.
- [x] 4.5 Wire the compatibility factory through the composition root without changing unrelated services or persistence selection; verify JSON and SQLite startup paths construct the same FastAPI application and no new dependency is required.

## 5. Isolation, Failure, and Compatibility Coverage

- [x] 5.1 Run repository-contract cases for cross-organization and cross-project access on every retrieval and mutation category; verify no foreign record is returned or changed.
- [x] 5.2 Add unit-of-work tests for successful commit, repeated commit, validation rollback, unexpected-error rollback, and canonical save failure; verify persisted reload results and commit counts match the specification.
- [x] 5.3 Extend audit tests for create, update, reorder, archive, delete, link, and unlink; verify successful operations produce exactly the existing action data and all failed operations produce no success audit.
- [x] 5.4 Run old-snapshot, JSON, SQLite, relational projection, indicator/reporting preservation, and clone integration tests; verify stable result/indicator IDs and unrelated RC Atlas records remain intact.
- [x] 5.5 Run existing Logical Framework API and Studio structural tests and verify `git diff --exit-code -- logitrack_studio.html`; confirm the current Logical Framework UI requires no source or interaction change while treating backend black-box tests, not Studio source inspection, as the evidence for API compatibility.

## 6. Documentation and Regression Gate

- [x] 6.1 Document the snapshot adapter as transitional, the canonical-commit versus projection-reconciliation boundary, and the remaining multi-process lost-update limitation; verify the documentation claims no PostgreSQL, global concurrency, or cross-store ACID guarantee.
- [x] 6.2 Run all focused repository, unit-of-work, Logical Framework domain, API, clone, persistence, and projection tests; report totals with zero failures and zero errors before full regression.
- [x] 6.3 Run `py -m unittest discover -v -p "*tests.py"`; verify every pre-existing test plus all new tests passes without weakening an existing expectation.
- [x] 6.4 Inspect `git diff --check`, `git diff --stat`, and `git status --short`; verify no frontend, dependency, seed/runtime data, PostgreSQL, Site.txt, unrelated refactor, staged file, commit, or push is part of the implementation change.
