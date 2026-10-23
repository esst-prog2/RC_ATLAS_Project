# PostgreSQL migration and validation report

Date: 2026-10-23. Work performed on 2026-10-22/23.

## Determination

- PostgreSQL canonical persistence and PostGIS synthetic acceptance: **PASS**.
- Complete regression: **PASS: 319/319**, comprising 20 PostgreSQL integration
  tests and 299 legacy/backend-independent tests; zero failures/errors/skips.
- Actual-data migration/cutover: **BLOCKED — separately authorized operation**.
- Wave 1: **CONDITIONAL**, unchanged. Internet release: **NO-GO**, unchanged.

The new backend is implemented and demonstrated with actual PostgreSQL, PostGIS,
independent API processes, Chrome, server restart, and database backup/restore.
No running deployment or real-data source has been switched. Selecting
`LOGITRACK_STORAGE_BACKEND=postgresql` makes PostgreSQL canonical; there is no
SQLite/JSON dual write, read fallback, or automatic legacy import in that mode.

## Verified pre-flight and preservation

Professional worktree: `D:\RC_ATLAS_REMEDIATION_W1_20261014`.
Branch: `remediation/wave-1-security-integrity`.
HEAD before and after implementation: `6ee278af46abe37968c03b256252d7824c75ecf5`.
Pre-flight found 18 modified tracked files and the untracked Wave 1 implementation,
tests, reports and evidence. Both named Wave 1 reports were read; the later
session-security report correctly supersedes the original bearer-storage blocker.

Before persistence edits, the complete source checkpoint was established at
`D:\RC_ATLAS_W1_RECOVERY_20261022_66feba61`: 138 tracked files plus 48 approved
untracked implementation/report/evidence files, all individually SHA-256 verified.
The manifest SHA-256 is
`0735A41BE0CB8CF09181092095843F8724F3CB101E033CB6487E0D21F57CDBCC`.
Six generated browser runtime JSON/backups were excluded and left in place.
The 186 checkpoint hashes were verified again after implementation. Earlier
planning-log bytes remain an unchanged prefix. Evidence:
`postgresql-evidence/recovery-verification.json`.

The original checkout and immutable QA archive were not accessed or modified.
No protected untracked files, canonical user data, production credentials, HW6
branch, or live provider was used. No commit, reset, clean, stash, merge, rebase,
push, deployment or external notification occurred. No subagents were used;
this was targeted implementation and sequential review, not a new specialist audit.

## Architecture and implemented changes

The active API loads `LogiTrackRC v4.4.py`. Its prior canonical unit is the complete
`LogiTrackData` snapshot: JSON or SQLite `app_state`, with separate best-effort
SQLite warehouse/repository writes. Repository hydration can supply missing
users/rules/reporting keys. Prior optimistic checks are protected only by a
process-local RLock. Sessions, CSRF hashes, expiry/revocation, receipts and the
global workspace version are all snapshot state.

The PostgreSQL adapter retains that application contract. A row lock and expected
version check precede one atomic commit of the canonical JSONB document, relational
ownership/reference index, audit/session/receipt state and incremented version.
Foreign keys include tenant ownership; unique indexes protect login names, session
hashes, scoped project codes and active idempotency keys. Expired receipts remain
in history and can be reused after expiry. No historical owner is inferred.

Both ordinary API saves and direct logical-framework/scheduler saves now pass
through PostgreSQL version protection. Logical-framework conflicts map to 409.
PostgreSQL load/save outages use redacted errors and do not create fallback stores.
Startup verifies schema checksums, versions, extension and restricted application
credentials before starting background work; no runtime DDL occurs.

The two SQL migrations establish the canonical/integrity schema and PostGIS point
storage. A checksum ledger and transaction/advisory lock make reruns repeatable.
An injected failing DDL migration was rolled back on the actual server, including
its attempted table and ledger entry. Unknown/tampered schema history fails closed.

Chrome also reproduced an existing registry-response race under PostgreSQL timing:
the loader restored a draft captured before awaiting the response and erased a
newly typed project name. The narrow UI fix captures the current draft after the
response. A deliberately delayed browser request now verifies preservation.

See `POSTGRESQL_PERSISTENCE_ARCHITECTURE_DECISION.md` for rationale and
`docs/POSTGRESQL_OPERATIONS.md` for field mapping, configuration, role grants,
explicit migration commands, cutover gates and recovery steps.

## Actual infrastructure and isolation

| Component | Verified version / mode |
| --- | --- |
| PostgreSQL | 17.11, Windows x64 portable EDB distribution; server version integer 170011 |
| PostGIS | 3.6.2, matching PostgreSQL 17 OSGeo bundle |
| Psycopg / binary wheel | 3.3.6, separate validation virtual environment |
| Python | 3.14.7 |
| Browser | Google Chrome 155.0.8059.85, actual installed Chrome via Playwright |

Portable binaries and disposable clusters live only under
`D:\RC_ATLAS_PG_VALIDATION_20261022_66feba61`. No Windows service was installed.
Fresh clusters use generated SCRAM secrets, loopback binding and unique ports.
The helper independently queries the actual server data directory, listener, port
and system identifier before fixtures run. Application SQL uses an unprivileged
role; the migrator uses a separate owner. Runtime/source paths and disabled providers
are recorded in isolation evidence. Owned API/browser/database processes are
stopped after testing; disposable data and synthetic dumps remain for review.

Downloaded archive SHA-256 values:

- PostgreSQL: `80379b2c04d51c30225532e0ae04509899141e9957ed096fe749d7fd9df8f82f`.
- PostGIS: `7ba180ee2a352987b9a2f194673652c59483b55852295ccf401dceccd8765425`.

These are recorded download fingerprints, not a claim of independent publisher
signature verification. Distribution links are recorded in the architecture ADR.

## Migration results

Only synthetic JSON and offline checkpointed SQLite snapshots were inspected and
imported. JSON and SQLite are **input formats**, never substitutes for the target
PostgreSQL integration backend. Dry-run validates raw data before application
normalization and makes no target writes. Apply requires explicit synthetic
acknowledgement, `test` environment, loopback `rcatlas_test_*` database, reviewed
source hash and an empty initialized target. There is no real-data apply option.

Verified behaviors: source bytes/hash unchanged; full payload equality after
import; entity and relationship counts matched; exact rerun returned UNCHANGED;
wrong hash, altered/nonempty target, missing domain, unknown field, duplicate key,
duplicate identifier, orphan, conflicting ownership, and blank activity owner were
rejected. The conversion guard uses JSON-type-sensitive fingerprints to reject input the
existing deserializer would silently normalize, including boolean/integer and
integer/float changes. Duplicate JSON object keys and multiple SQLite primary
records are rejected before normalization. A flag cannot identify whether file contents are synthetic;
the operator must obey the scope restriction. Internal adapter methods are trusted
interfaces, not authorization against someone already holding database credentials.

Final JSON dry-run/apply/rerun evidence:
`postgresql-evidence/focused-final-source/json-import-evidence.json`.

| Integrity entity | Verified count |
| --- | ---: |
| Organizations / users / teams | 2 / 6 / 4 |
| Projects / indicators / project assignments | 3 / 9 / 12 |
| Operational activities / tasks | 9 / 18 |
| Datasets / semantic mappings / reporting records | 2 / 2 / 108 |
| Templates / rules / audit events | 3 / 3 / 3 |
| Sessions | 2 |
| Total indexed entities / relationships | 186 / 475 |

The import fixture contains no logical-framework nodes/links or idempotency
receipts; those paths have separate API tests. Dataset row contents and nested
indicator locations are verified by complete payload equality, not represented as
separate canonical relational tables. Source SHA-256:
`c519e815f1f737147cb7e67976c4092b04cc111713df385e9e8b3bb49cd4bc6d`.

Historical blank-owner activity repair remains a distinct gate. No historical
dry-run against real data, ownership assignment, or real-data apply was performed.

## Acceptance evidence

| Test group | Backend / mode | Exact final result |
| --- | --- | --- |
| Focused PostgreSQL integration | Actual PostgreSQL/PostGIS | **20/20 PASS**, 92.655 s; zero failures/errors/skips |
| Full regression | Separately counted legacy/source and actual PostgreSQL tests | **319/319 PASS**, 282.483 s; 20 PostgreSQL + 299 legacy/source; zero failures/errors/skips |
| Real browser critical workflows | Chrome + PostgreSQL | **10/10 PASS** |
| Process/recovery harness | Two concurrent Uvicorn processes, process replacement, PostgreSQL restart and restore | **8/8 PASS** (one harness check summarizes the ten browser checks; do not add them as independent tests) |
| Diff whitespace | Git | PASS; existing CRLF conversion warnings only |

The focused tests cover schema initialization/rerun/failure rollback/checksum
mismatch; no JSON/SQLite fallback; DB-enforced foreign keys/uniqueness and atomic
rollback; scoped duplicate IDs; direct concurrent writers; idempotent submission,
payload mismatch and stale versions; expired-key reuse; tenant reads/writes;
cookie/CSRF/origin/rotation/logout; idle and absolute expiry and tenant-bound
sessions; JSON/SQLite synthetic migration; conversion rejection; project update,
logical-framework write and dataset import; outage recovery; production
configuration rejection; and PostGIS/RLS/CRS operations.

The runtime harness at `postgresql-evidence/runtime-accepted/runtime-results.json`
records two separate API PIDs (29812 and 26652) submitting one identical intent:
one project and one receipt committed, both responses matched. A stale request
returned 409. API PID 29812 was replaced by 9748; session identity, project,
imported dataset, version 4 and the receipt survived, and replay returned the same
response. Tenant B could not see tenant A's project. Stopping PostgreSQL returned
503; starting the same independently verified cluster retained version 5 and all
payload data. Logout remained revoked after another API restart (401), while the
other tenant's session stayed valid (200).

After stopping application writers, `pg_dump -Fc` and `pg_restore --exit-on-error`
into a **new database** reproduced the entire canonical document and PostGIS
version. Synthetic dump SHA-256:
`20f507c181079b54939ecb080a73ea216bc75b0894d4dfe11d0e12234364655e`.
This proves a tested logical-backup recovery path, not PITR or production recovery.

Chrome verified unauthorized/authorized setup, invalid/valid login, HttpOnly
session/no browser bearer storage, reload restoration, cross-tab logout and revoked
cookie rejection, delayed-refresh draft preservation, one request/record after
double activation, visible failed-save feedback with retained draft, and expected
console errors only. Evidence:
`postgresql-evidence/runtime-accepted/browser/browser-results.json` plus screenshots.
Tenant isolation was exercised by actual APIs and separate processes; a second
tenant's rendered browser session was not separately tested in this package.

PostGIS tests round-trip WGS84 longitude/latitude with SRID 4326, measure a roughly
111 m geography distance, transform to 3857, reject a wrong-SRID assignment and
out-of-range coordinates, hide rows without/with another tenant context through
FORCE RLS, reject another tenant's project ownership, and preserve points across
canonical saves. GiST and tenant/project indexes are provisioned. No map/dashboard
or implicit conversion of old coordinates was implemented.

Detailed final-source test records: `postgresql-evidence/focused-final-source/results.json`
and `postgresql-evidence/full-final-source/results.json`; each directory includes
the complete test log. Earlier successful runs are retained separately.

## Failed iterations retained

`focused-initial.txt` records 18 tests with two failures and four errors: fixture
normalization/defaults, a wrong fixture method name, a missing update field and a
checksum mismatch caused by editing an unapplied migration while a disposable run
was in flight. The subsequent 18-test and 19-test runs passed. The accepted run adds
duplicate-key dry-run coverage and passes all 20. A later review strengthened the
same tests for JSON scalar types, duplicate object keys and ambiguous SQLite primary
records; the final-source focused rerun passed 20/20 and full rerun passed 319/319.
The earlier full regression also passed 319/319 (294.355 s). These earlier logs remain.

The first and second browser runs each passed six checks before exposing the
project-draft race. The diagnostic run traced the exact stale-draft assignment;
its screenshot and call stacks remain. The accepted run includes the targeted
regression and passes all ten. No earlier FAIL is relabeled or removed.
An initial Windows `pg_ctl` harness timeout was caused by inherited captured pipe
handles; using an owned output file resolved it, and that disposable server was
stopped. It did not touch application persistence.

## Compatibility, limits and remaining gates

1. This is an aggregate adapter, not a complete normalized-domain rewrite. The
   trusted server DB connection spans tenants; existing API authorization remains
   the tenant read boundary. Full application RLS is not claimed. Spatial storage
   has its own tenant RLS. Raw database credentials are not exposed to tenants.
2. Workspace version remains global. Full JSONB writes and integrity-index rebuilds
   can cause cross-tenant contention and write amplification. Capacity, pooling,
   sustained load and horizontal throughput remain unmeasured. Multiple processes
   are safe against lost updates in the tested conflicts; this is not a scale SLA.
3. PostgreSQL selection disables legacy warehouse hydration/mirroring. External
   consumers querying the SQLite warehouse must move to an approved read model
   before cutover; this package did not discover or change external BI consumers.
4. Unknown/ambiguous legacy data can block migration by design. The complete real
   source has not been inventoried. Historical activity repair requires separate
   approval and is never folded into this importer.
5. Local acceptance uses explicit loopback development HTTP cookies. Actual
   production TLS, certificate/secret delivery, deployment role configuration,
   managed PostGIS availability, operational backup retention/PITR and recovery
   objectives remain unvalidated. Insecure configuration rejection is tested.
6. Only PostgreSQL 17 / PostGIS 3.6 are admitted. The tested patch versions are
   17.11 / 3.6.2; other major/minor extension combinations fail closed.
7. A connection loss at COMMIT can leave an uncertain acknowledgement. There is no
   automatic retry of non-idempotent operations; use the original key for supported
   idempotent writes and reconcile other cases. No application falls back to legacy
   state during outages.
8. Existing FastAPI lifespan and Starlette/httpx deprecation warnings remain.
   Deliberate failure-injection logging is expected. Providers remain disabled;
   Wave 2 methodology, Wave 3 dashboards, deployment and internet release are out
   of scope.

## Recovery and next controlled step

Follow `docs/POSTGRESQL_OPERATIONS.md`. Source recovery first verifies the snapshot
manifest and all 186 hashes, then copies `files/` into a new empty directory; it
does not reset or overwrite another worktree. Database rollback restores a checked
dump into a fresh compatible PostgreSQL database. Before PostgreSQL accepts any
new writes, an approved cutover can revert to the frozen source; afterward that
source is stale and must never be selected without separate reconciliation.

Next: review this package and its aggregate/tenant-boundary limits, then separately
authorize an offline real-source inventory/dry-run with an approved backup and
ownership review. A real apply/cutover needs its own reviewed entry point, explicit
approval, stopped writers, complete comparison and recovery rehearsal. No such
authorization is inferred here.

## SESSION_HANDOFF

Use the professional worktree/branch/HEAD above; all implementation remains
uncommitted. Read this report, the ADR and operations runbook. Recovery checkpoint:
`D:\RC_ATLAS_W1_RECOVERY_20261022_66feba61`. Portable validation environment:
`D:\RC_ATLAS_PG_VALIDATION_20261022_66feba61`; use its venv and the explicit
`RCATLAS_PG_TEST_BIN`/`RCATLAS_PG_TEST_ROOT` variables. Run
`postgresql_regression.py --suite focused|all --evidence <new-output-directory>`
and `postgresql_runtime_acceptance.py --browser --evidence <new-output-directory>`.
PostgreSQL mode requires explicit configuration/migrations. No real data or
historical ownership repair is authorized. Keep Wave 1 CONDITIONAL and release
NO-GO. Exact package files are listed below and in the inventory artifact.

## Exact changed files

Relative to the verified Wave 1 checkpoint: **7 modified existing files**,
**13 new implementation/test/document files**, and **69 new evidence files**.
The prior Wave 1 changes are not attributed to this package. Machine-readable
inventory: `postgresql-evidence/changed-files.json`. Final source hashes, branch,
HEAD, recovery checks and whitespace result: `postgresql-evidence/final-verification.json`.
Process cleanup: `postgresql-evidence/process-cleanup.json` (no owned processes left).

Modified existing files:

```text
LogiTrackRC v4.4.py
PLANNING_LOG.md
api/logical_framework_routes.py
logitrack_studio.html
migration/sync_helpers.py
repositories/logical_framework_snapshot.py
requirements.txt
```

New implementation, tests and documents:

```text
POSTGRESQL_MIGRATION_AND_VALIDATION_REPORT.md
POSTGRESQL_PERSISTENCE_ARCHITECTURE_DECISION.md
docs/POSTGRESQL_OPERATIONS.md
logitrack_platform/persistence_validation.py
logitrack_platform/postgresql_store.py
migration/postgresql/001_canonical.sql
migration/postgresql/002_postgis.sql
migration/postgresql_import.py
postgresql_browser_acceptance.js
postgresql_persistence_tests.py
postgresql_regression.py
postgresql_runtime_acceptance.py
postgresql_test_support.py
```

New evidence (including earlier failed iterations):

```text
postgresql-evidence/browser-diagnostic/01-unauthorized-setup-rejected.png
postgresql-evidence/browser-diagnostic/02-trusted-setup-complete.png
postgresql-evidence/browser-diagnostic/03-invalid-login-feedback.png
postgresql-evidence/browser-diagnostic/04-authorized-login.png
postgresql-evidence/browser-diagnostic/05-cross-tab-logout.png
postgresql-evidence/browser-diagnostic/browser-results.json
postgresql-evidence/browser-diagnostic/failure-browser-state.png
postgresql-evidence/browser-diagnostic/failure-project-pending.png
postgresql-evidence/browser-diagnostic/isolation.json
postgresql-evidence/browser-diagnostic/project-name-writes.json
postgresql-evidence/browser-diagnostic/run.txt
postgresql-evidence/changed-files.json
postgresql-evidence/final-verification.json
postgresql-evidence/focused-accepted/isolation.json
postgresql-evidence/focused-accepted/json-import-evidence.json
postgresql-evidence/focused-accepted/results.json
postgresql-evidence/focused-accepted/tests.txt
postgresql-evidence/focused-final-source-console.txt
postgresql-evidence/focused-final-source/isolation.json
postgresql-evidence/focused-final-source/json-import-evidence.json
postgresql-evidence/focused-final-source/results.json
postgresql-evidence/focused-final-source/tests.txt
postgresql-evidence/focused-final.txt
postgresql-evidence/focused-initial.txt
postgresql-evidence/focused-second.txt
postgresql-evidence/full-final-source-console.txt
postgresql-evidence/full-final-source/isolation.json
postgresql-evidence/full-final-source/json-import-evidence.json
postgresql-evidence/full-final-source/results.json
postgresql-evidence/full-final-source/tests.txt
postgresql-evidence/full-regression-console.txt
postgresql-evidence/full-regression/results.json
postgresql-evidence/full-regression/tests.txt
postgresql-evidence/process-cleanup.json
postgresql-evidence/recovery-verification.json
postgresql-evidence/runtime-accepted/browser-run.txt
postgresql-evidence/runtime-accepted/browser/01-unauthorized-setup-rejected.png
postgresql-evidence/runtime-accepted/browser/02-trusted-setup-complete.png
postgresql-evidence/runtime-accepted/browser/03-invalid-login-feedback.png
postgresql-evidence/runtime-accepted/browser/04-authorized-login.png
postgresql-evidence/runtime-accepted/browser/05-cross-tab-logout.png
postgresql-evidence/runtime-accepted/browser/06-duplicate-submit-prevented.png
postgresql-evidence/runtime-accepted/browser/07-project-save-error-feedback.png
postgresql-evidence/runtime-accepted/browser/browser-results.json
postgresql-evidence/runtime-accepted/runtime-isolation.json
postgresql-evidence/runtime-accepted/runtime-results.json
postgresql-evidence/runtime-final.txt
postgresql-evidence/runtime-first.txt
postgresql-evidence/runtime-first/browser-run.txt
postgresql-evidence/runtime-first/browser/01-unauthorized-setup-rejected.png
postgresql-evidence/runtime-first/browser/02-trusted-setup-complete.png
postgresql-evidence/runtime-first/browser/03-invalid-login-feedback.png
postgresql-evidence/runtime-first/browser/04-authorized-login.png
postgresql-evidence/runtime-first/browser/05-cross-tab-logout.png
postgresql-evidence/runtime-first/browser/browser-results.json
postgresql-evidence/runtime-first/runtime-isolation.json
postgresql-evidence/runtime-first/runtime-results.json
postgresql-evidence/runtime-second.txt
postgresql-evidence/runtime-second/browser-run.txt
postgresql-evidence/runtime-second/browser/01-unauthorized-setup-rejected.png
postgresql-evidence/runtime-second/browser/02-trusted-setup-complete.png
postgresql-evidence/runtime-second/browser/03-invalid-login-feedback.png
postgresql-evidence/runtime-second/browser/04-authorized-login.png
postgresql-evidence/runtime-second/browser/05-cross-tab-logout.png
postgresql-evidence/runtime-second/browser/browser-results.json
postgresql-evidence/runtime-second/browser/failure-browser-state.png
postgresql-evidence/runtime-second/browser/failure-project-pending.png
postgresql-evidence/runtime-second/runtime-isolation.json
postgresql-evidence/runtime-second/runtime-results.json
```
