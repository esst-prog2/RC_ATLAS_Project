# PostgreSQL persistence architecture decision

Decision: 2026-10-22; validation updated 2026-10-23. Implementation and synthetic
PostgreSQL/PostGIS foundation: **PASS**. Actual-data migration/cutover remains
**BLOCKED pending separate authorization**. Wave 1 remains **CONDITIONAL** and
internet release **NO-GO**.

## Verified baseline and recovery

Professional worktree: `D:\RC_ATLAS_REMEDIATION_W1_20261014`; branch
`remediation/wave-1-security-integrity`; HEAD
`6ee278af46abe37968c03b256252d7824c75ecf5`.
Both Wave 1 reports and their uncommitted implementation were inspected. The
session-security report supersedes the earlier localStorage transport finding.
Wave 1 remains CONDITIONAL and internet release NO-GO.

Before persistence edits, 186 tracked/source/test/report/evidence files were copied
and individually SHA-256 verified at
`D:\RC_ATLAS_W1_RECOVERY_20261022_66feba61\files`.
Manifest: `manifest.json`, SHA-256
`0735A41BE0CB8CF09181092095843F8724F3CB101E033CB6487E0D21F57CDBCC`.
Six generated browser runtime JSON/backup files were excluded and left untouched.
No commit, stash, reset, original-checkout access, or archive modification occurred.

## Existing source of truth

The active entry point `logitrack_rc_v4_4_api.py` loads `LogiTrackRC v4.4.py`.
The similarly named lower-case legacy source is not that entry point.
`LogiTrackData` is a complete workspace aggregate: organizations, teams, projects
and nested indicators/assignments, operational activities/tasks, datasets and rows,
reporting records, mappings, templates, rules, users, audit events, sessions,
idempotency records, and one global workspace version.

JSON is canonical by default (`LOGITRACK_DATA_PATH`); saves replace the file and
retain a best-effort `.bak`. SQLite canonical mode stores the same JSON document
in `app_state` and retains bounded `state_revisions`. Missing SQLite can implicitly
import JSON. Neither behavior is acceptable as an implicit PostgreSQL cutover.

`logitrack_platform/relational_store.py` rebuilds a separate SQLite warehouse after
canonical saves. `migration/sync_helpers.py` writes users/rules/reporting records
again and can hydrate only missing snapshot keys from that warehouse. Those
operations are separate transactions. Ordinary services mutate a loaded aggregate
and call the injected save function. Logical-framework writes use a snapshot unit
of work with a direct canonical-save callback. The scheduler also saves directly.
All of these paths must use the new persistence boundary.

The existing RLock and load/check/save version sequence protect one process only.
Sessions (including CSRF hashes, expiry and revocation) and idempotency receipts
live in the aggregate. Authorization obtains tenant context from persisted users;
API views explicitly filter the workspace. Legacy ownership inference exists for
some domains. Blank historical activity ownership requires separate approval.

## Decision

Use an explicit PostgreSQL adapter with Psycopg 3, retaining the aggregate contract
to avoid a product-wide repository rewrite. PostgreSQL is the sole canonical
source when `LOGITRACK_STORAGE_BACKEND=postgresql`. There is no JSON/SQLite read,
fallback, migration on startup, warehouse write, or hydration in this mode.
The professional deployment must explicitly choose PostgreSQL. Production with no
backend selection fails closed; explicit legacy backends remain available for
compatibility testing and separately controlled rollback.

One PostgreSQL transaction locks the workspace row, compares the expected global
version, validates and replaces a relational integrity index, writes the complete
JSONB aggregate and advances its version. Thus sessions, business writes, audit
events and idempotency receipts commit or roll back together. The aggregate is the
source; relational rows are derived constraints in the SAME transaction, never an
independently writable canonical source. Composite foreign keys enforce tenant
ownership and references; unique constraints protect login names, token hashes,
project codes and active idempotency scope. Expired receipts remain in canonical
history and their keys can be reused; active scope is evaluated at database
transaction time. Identical entity IDs in different tenants use composite keys.
Failed concurrent saves return conflict and
the existing idempotency replay path reloads the winning receipt.

Retaining the global aggregate means trusted application-server database access
spans tenants; application authorization remains the tenant read boundary. This
is not a claim of per-tenant RLS for the entire application. Spatial foundation
storage has its own tenant RLS and composite project ownership foreign key.
Workspace-wide contention, full-document writes, and index rebuild cost remain
explicit scaling limitations; per-tenant units of work are a later design change.

Schema migrations are ordered SQL files with a checksum ledger and transaction/
advisory lock. Runtime requires the exact completed schema and PostGIS; it never
creates extensions or runs migrations. Migration credentials are separate from
the restricted application role. Production requires verified TLS and rejects
privileged roles and development credentials/settings. Errors exclude DSNs and
raw database messages. Unavailable or incomplete databases fail closed.

## Non-destructive migration and spatial foundation

Migration reads an explicitly supplied offline JSON file or read-only canonical
SQLite `app_state`. The warehouse is not a competing source; missing domains
require reconciliation rather than automatic merging. Validation runs on the raw
document before application normalization. Unknown/malformed top-level fields,
duplicate identifiers, missing ownership, conflicting ownership, or orphaned
references block apply. No ownership is inferred or repaired.

Dry-run performs no target writes. Apply requires an empty initialized target,
reviewed content hash and an explicit synthetic-execution flag for this package.
Identical re-execution is a no-op only while the imported target remains identical;
changed or subsequently edited targets conflict. Verify full payload equivalence,
entity/relationship counts and source-file hashes. Real-data execution is not
authorized or enabled by this package.

PostGIS stores WGS84 points (`geometry(Point,4326)`), longitude then latitude,
with range checks, tenant/project keys and a GiST index. Do not relabel another CRS
as 4326: use an explicitly chosen `ST_Transform`. Spatial storage remains a
foundation, without maps, dashboards, or automatic conversion of legacy locations.

## Validation and recovery

PostgreSQL 17.11 / PostGIS 3.6.2 with Psycopg 3.3.6: focused **20/20 PASS**;
full regression **319/319 PASS** (20 actual PostgreSQL and 299 legacy/source tests,
zero failures/errors/skips). Chrome 155.0.8059.85: **10/10 PASS**. The process
harness passed **8/8** checks, including two-process idempotency/stale-version
handling, tenant isolation, session revocation, API/server restart and dump/restore
into a fresh database. One harness check wraps the ten browser checks.

Synthetic JSON dry-run/apply/rerun verified 186 entities and 475 relationships;
SQLite input was also imported into actual PostgreSQL. Source hashes stayed
unchanged. Blank ownership, orphans, duplicate/conflicting records and silent
conversion fail closed. No real-data migration, cutover or ownership repair ran.

Restore source by verifying the checkpoint manifest and every file hash, then copy
its `files/` tree into a new empty directory. Restore database backups into a new
compatible PostgreSQL database and verify before changing configuration. After
PostgreSQL accepts new writes, the frozen legacy source is stale and cannot be
selected without reconciliation. See `docs/POSTGRESQL_OPERATIONS.md` for the
controlled procedure and the companion report for exact evidence and blockers.

## Sources

- [PostgreSQL row locking](https://www.postgresql.org/docs/17/explicit-locking.html)
- [Psycopg transaction contexts](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
- [Official Windows PostgreSQL distribution](https://www.postgresql.org/download/windows/)
- [PostGIS Windows binaries](https://postgis.net/documentation/getting_started/install_windows/released_versions/)
- [PostGIS SRID versus coordinate transformation](https://postgis.net/docs/ST_SetSRID.html)

## SESSION_HANDOFF

Read the companion validation report for final status, exact tests, files and
recovery instructions. Preserve the uncommitted Wave 1 changes and recovery
snapshot. Do not migrate real data, repair historical ownership, or change release
gates without separate authorization.

## Changed implementation and document files

Relative to the verified pre-package checkpoint, seven existing files changed:

```text
LogiTrackRC v4.4.py
PLANNING_LOG.md
api/logical_framework_routes.py
logitrack_studio.html
migration/sync_helpers.py
repositories/logical_framework_snapshot.py
requirements.txt
```

Thirteen source, test and document files were added:

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

The companion validation report and `postgresql-evidence/changed-files.json` list
every retained evidence file as well. Existing Wave 1 reports and other checkpoint
files remain unchanged. No committed baseline change was made.
