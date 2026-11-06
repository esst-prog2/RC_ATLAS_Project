# PostgreSQL operations and controlled migration

This runbook applies to the professional PostgreSQL foundation. It does not
authorize execution on real data. Wave 1 remains CONDITIONAL; internet release
remains NO-GO. Never point the validation tools at an existing server.

## Supported configuration

The verified combination is PostgreSQL **17.11**, PostGIS **3.6.2**, and Psycopg
**3.3.6**, on Windows x64. The runtime requires PostgreSQL major 17 and PostGIS
3.6.x. Other combinations require a deliberate compatibility change and tests.
Install the Python dependencies from `requirements.txt` in a dedicated environment.

Professional application environment:

```text
LOGITRACK_STORAGE_BACKEND=postgresql
LOGITRACK_ENVIRONMENT=production
LOGITRACK_DATABASE_URL=<secret PostgreSQL connection string supplied by your secret manager>
LOGITRACK_SESSION_COOKIE_SECURE=true
LOGITRACK_RUN_SCHEDULER=false
LOGITRACK_EMAIL_ENABLED=false
```

The connection string must explicitly contain host, database, user, password,
`sslmode=verify-full`, and `sslrootcert`. Use a dedicated generated secret (at least
24 characters); never put it in source control, a command argument, a report, or a
shell history example. The runtime rejects common development credentials,
privileged application roles, a schema-owning production role, insecure production
cookies, unsupported versions, unknown backends, and incomplete/checksum-mismatched
migrations. Production without an explicit backend fails closed. Explicit legacy
backend selection remains possible for separately controlled rollback; configuration
review must enforce PostgreSQL for the professional deployment.

Development/test mode is explicitly loopback-only and is not a deployment setting.
The application never prints the DSN or raw driver error. It uses bounded connection,
statement and lock timeouts. Cookie transport, origin configuration, trusted proxy
handling, HTTPS, and secure external secret delivery remain deployment gates.

## Roles and schema setup

Use a DBA-controlled migrator role separately from an unprivileged application
login. The DBA provisions the PostGIS binaries and extension capability. A DBA may
create PostGIS first; the repeatable migration then recognizes the existing
extension. Do not grant extension or schema ownership privileges to the application.

Supply the **migrator** connection through `LOGITRACK_DATABASE_URL` and run:

```powershell
python -m logitrack_platform.postgresql_store migrate
```

The numbered SQL files run under one transaction and migration advisory lock;
their SHA-256 values are recorded in `rcatlas.schema_migrations`. Reruns are no-ops.
Never edit an applied SQL file. Add the next version. A failed upgrade rolls back
both its DDL and ledger writes. There are deliberately no destructive down scripts.

For a dedicated database, grant the application role the following permissions
(replace the role name through an operator-reviewed SQL script):

```sql
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA rcatlas TO rcatlas_app;
GRANT SELECT ON rcatlas.schema_migrations TO rcatlas_app;
GRANT SELECT, UPDATE ON rcatlas.workspace TO rcatlas_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON
  rcatlas.organizations, rcatlas.entities, rcatlas.relationships,
  rcatlas.import_receipts, rcatlas.geographic_points TO rcatlas_app;
```

Also restrict database CONNECT and role membership to authorized services. Restore
the application connection and run `python -m logitrack_platform.postgresql_store
check`. Startup only verifies readiness; it never migrates, imports, initializes a
missing schema, reads legacy data, or falls back to SQLite/JSON.

## Source-of-truth and field mapping

| Source | PostgreSQL destination | Mapping and validation |
| --- | --- | --- |
| Canonical JSON document | `workspace.payload` JSONB | Complete field values, array order, nulls, IDs, hashes and versions retained; semantic JSON equivalence checked. JSON formatting is not retained. |
| Canonical SQLite `app_state` / `primary` | Same `workspace.payload` | Offline, checkpointed read-only input; WAL/journal source rejected; no fallback or backup recovery. |
| `workspace_version` | `workspace.version` and payload field | Imported unchanged; every subsequent aggregate commit advances once under a row lock and expected-version comparison. |
| Organizations | `organizations.id`, `entities` | Exact nonblank identifiers; every owned entity references an existing organization. |
| Projects, indicators, assignments, activities, tasks | `entities`, `relationships` | Composite tenant identity; exact declared ownership, parent project, activity, indicator and user/team references. Nested payload remains canonical. |
| Users, teams, sessions | Same index | Global case-insensitive login uniqueness; scoped teams/users; unique session token hashes; expiry, CSRF hashes and revocation retained in JSONB. |
| Datasets/rows, mappings, reporting records, rules, templates | Same index | Dataset rows remain arbitrary imported data; typed dataset/project/indicator references are checked. Builtin global templates are explicitly distinguished. |
| Logical-framework nodes/links | Same index | Tenant/project references retained; the existing service validates hierarchy semantics. |
| Audit events | Same index | Actor relationships checked where present; anonymous system/security events may be unowned. Historical target IDs remain audit evidence and are not deletion-blocking FKs. |
| Idempotency receipts | Same index | Actor/tenant/operation/key scope; project result references; full original response retained. Expired receipts remain in the payload; only active scopes are unique at DB transaction time. |
| Separate SQLite warehouse | No import source | Derived projection. Missing canonical domains require reviewed reconciliation; automatic warehouse merging is prohibited. |
| New geographic points | `geographic_points` | Explicit tenant and project, WGS84 `geometry(Point,4326)`, range checks and RLS. Existing latitude/longitude fields are preserved, not silently converted. |

`entities`/`relationships` are integrity indexes rebuilt inside the same commit as
the canonical document. Services never read them as an alternative source of truth.
The trusted application connection loads all tenants; existing API authorization is
the read boundary. Spatial rows additionally have FORCE RLS; set tenant context
transaction-locally. No geographic user-facing functionality is added.

The whole workspace remains the transaction unit. Different-tenant writes can
conflict; callers reload and retry explicit intents after 409. Do not blindly
retry a non-idempotent write after an ambiguous connection failure. A lost COMMIT
acknowledgement can be resolved with the original idempotency key where supported.
Full-document/index write cost and global contention need capacity measurements
before wider deployment. This package makes no throughput/SLA claim.

## Synthetic migration procedure

1. Create and independently verify a fresh disposable runtime/database. The test
   helper records resolved data directory, actual loopback binding, port and
   PostgreSQL system identifier. It refuses to attach to existing clusters.
2. Build synthetic canonical data through the existing application serializer.
   Export to a new file and hash it. Real source files were not inspected here.
3. Dry-run with an explicit file and source format:

   ```powershell
   python -m migration.postgresql_import --source <synthetic-offline-file> --format json
   ```

4. Review all counts and issues. Dry-run does no target writes. Blank-owner
   activities, orphaned/conflicting relationships, ambiguous IDs, duplicate unique
   keys, duplicate JSON object keys, multiple SQLite primary records, missing
   domains, and application normalization that would change values or scalar types
   block the operation. No activity ownership is inferred.
5. With `LOGITRACK_ENVIRONMENT=test`, a loopback `rcatlas_test_*` database, and
   reviewed source hash, apply only synthetic data:

   ```powershell
   python -m migration.postgresql_import --source <synthetic-offline-file> --format json --apply --synthetic --reviewed-sha256 <reviewed-hash>
   ```

6. Verify payload equality, entity/relationship row counts, migration receipt and
   unchanged source hash. Repeat with the same source: unchanged target is a no-op.
   A nonempty different target or later application edits block replay. SQLite
   input uses `--format sqlite` and is still verified against actual PostgreSQL.

This tool deliberately has no production apply option. An explicit synthetic flag
is an operator acknowledgement, not a content classifier; do not supply real data
to it. Library-level adapter methods are trusted internal interfaces, not an
authorization barrier against an operator with database credentials.

## Future authorized cutover

Separate approval must name the source, tenant scope, reviewed hash, ownership
findings, maintenance window, database/role, backup locations and rollback owner.
Do not run the synthetic-only apply tool against real data. Review an appropriate
production migration entry point as part of that approval.

Stop **all** legacy writers and scheduler workers. Freeze the approved canonical
source and an independently verified backup; reconcile any missing repository
domains offline. Resolve ambiguous ownership only under its separate gate. Import
into a new empty target, verify full payload and counts/relationships, and run the
approved critical workflows. Switch configuration for all workers together; never
run legacy and PostgreSQL writers simultaneously. Keep the frozen source read-only.
Enable traffic only after the cutover acceptance gate passes.

Before any new PostgreSQL writes, rollback may point all stopped workers back to
the frozen legacy source. Once PostgreSQL accepts writes, that source is stale:
do **not** switch back and lose them. Stop writers and restore a verified PostgreSQL
backup to a fresh database, or approve a separate lossless reverse migration and
reconciliation. There is no automatic reverse conversion or fallback.

## Database backup, restore and spatial maintenance

Use matching PostgreSQL tools, secret injection, and a protected backup location.
`pg_dump -Fc` creates a consistent database dump; `pg_restore --exit-on-error` into
a new empty database is the tested recovery path. Include role/grant provisioning
and PostGIS binaries in the operational recovery plan. Verify full payload, schema
checksums, extension version, ownership, sessions/receipts and scoped point reads
before changing the application DSN. For an older valid schema, restore the matching
application release as well. Automated backup schedules, WAL/PITR, retention,
encrypted backup storage, RPO and RTO remain unverified operational work.

Use longitude/latitude only with SRID 4326; `ST_SetSRID` labels coordinates and does
not transform them. Transform another known CRS with `ST_Transform`. Use geography
or a suitable projected CRS for metric distances. The foundation includes GiST on
point geometry and a tenant/project B-tree. Future spatial filters must include
tenant context and use index-aware predicates; confirm query plans and statistics
at representative scale. Other geometry types and geographic dashboards are out
of scope.

## Recover the complete pre-package Wave 1 source

Snapshot: `D:\RC_ATLAS_W1_RECOVERY_20261022_66feba61`.
Verify `manifest.json` SHA-256 equals
`0735A41BE0CB8CF09181092095843F8724F3CB101E033CB6487E0D21F57CDBCC`, then verify
every listed `files/<path>` hash. Copy that file tree into a **new empty** directory
outside all existing worktrees. It contains the complete 186-file Wave 1 source,
untracked implementation, reports and evidence at the checkpoint. It does not
contain generated runtime data, credentials, `.git`, or the six excluded disposable
browser JSON/backups. Those excluded artifacts remain untouched in the professional
worktree. The manifest records branch, baseline HEAD and original Git status.

Do not reset/clean the professional checkout or modify other worktrees. To undo
this package in place later, first retain a second snapshot, then restore only the
package's explicitly listed changed existing files from the checkpoint; retain new
package artifacts separately. No such rollback, commit or source deletion was
performed by this implementation.
