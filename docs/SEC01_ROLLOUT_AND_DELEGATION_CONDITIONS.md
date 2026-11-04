# SEC-01 compatibility and delegation conditions

2026-10-29. These are release conditions and recommendations, not deployment,
migration execution, or a change to current delegation behavior.

## Versioned permission data: mandatory deployment fence

**Do not permit production v1 permission writes until incompatible application
readers and writers are technically excluded.** Stopping traffic alone is
insufficient: include background jobs, CLI tools, projections and recovery tools.
Never roll an old binary forward onto a store containing v1 policies. Restoring
an old binary requires a separately approved matching data restore/conversion;
an empty v1 grant cannot safely be converted to a legacy empty grant.

The inspected approved base ignores the new canonical marker, restores role
defaults for empty grants, and drops the marker when saving. Its relational
reader treats the new object envelope as an empty legacy list. Documentation or
a startup check added only to the new binary cannot restrain that old code.

### Existing PostgreSQL gate

`logitrack_platform/postgresql_store.py:103` checks the complete ordered
`schema_migrations` name/checksum list against the binary's migration files.
Both canonical `load()` and `save()` call it before accessing the workspace
payload (`:157`, `:165`). The current two-migration list is unchanged, so it
**does not distinguish** pre-SEC-01 and SEC-01 permission semantics today.

A narrowly scoped, separately reviewed permission-policy marker migration can
reuse this existing mechanism: an additional immutable migration entry causes
the old two-entry binary to reject canonical reads/writes, while the new binary
requires the additional entry before accessing data. Do not change old migration
checksums, manually forge the migration ledger, or claim that workspace_version
(an optimistic-concurrency counter) is a binary compatibility version.

Required release evidence before enabling production v1 writes:

1. Drain/stop old processes and in-flight requests; apply the approved marker
   migration with the explicit migrator, never at automatic application startup.
2. Verify with disposable data that the exact old approved binary rejects both
   reads and writes against the upgraded schema, and the approved new binary
   round-trips inheritance, denial and individual grants.
3. Keep application credentials unprivileged so they cannot remove/bypass the
   schema marker. Restrict deployable artifacts to the reviewed build and record
   its source/build digest. Exclude legacy direct-SQL and recovery writers too.
4. Demonstrate rollback refusal or the separately approved matching restore;
   retaining old credentials or an old running worker is not an accepted fence.

No marker migration was added or executed in this rework. The enforcement gate
therefore remains an explicit **deployment blocker**, not a completed safeguard.

### JSON, canonical SQLite and relational projections

The inspected readers have no equivalent old-binary format gate. A field that
only the new reader recognizes cannot make old readers safe. Before any production
use of these backends with v1 data, require a dedicated service identity with
exclusive filesystem access, a deployment/launch allowlist bound to the approved
artifact digest, and revoked access for legacy jobs/service identities. Test that
the old launch artifact and old identities cannot open/read/write the actual
versioned data path (including projections, backups and restores).

If those controls cannot be demonstrated, production v1 use on that backend is
blocked. Merely pointing the new binary at a different filename is not sufficient.
This rework does not alter ACLs, credentials, service configuration or deployment.

## MANAGE_USERS: current behavior and policy decision

Both admin PATCH and legacy user upsert authorize with MANAGE_USERS, scope the
target to the caller's institution, and accept recognized role/grant values.
There is no distinct assignment privilege or grant ceiling. A holder can update
their own account to organization_admin with permissions=null and obtain its
defaults, or directly assign broader recognized capabilities. This predates
SEC-01; versioned permission semantics do not create or close it.

Proposed minimum policy, requiring owner approval before implementation:

- Treat MANAGE_USERS as account administration, not unlimited delegation.
  Role/grant changes additionally require MANAGE_ORGANIZATION and a documented
  institution-owned grantable-capability ceiling.
- Assigned effective capabilities must be within the actor's current effective
  capabilities and that ceiling. Resolve aliases, role defaults and inherited
  permissions before checking; null or a role change must not bypass the ceiling.
- Disallow self-approval of privilege increases and edits to one's own delegation
  ceiling. A different authorized institution administrator approves increases
  to governance capabilities. Preserve at least one governed recovery custodian.
- Record before/after effective grants and the approving actor in tenant audit
  records. Do not link identities across institutions to obtain an approver.
- Future institution-defined roles map to the same ceiling rules; a role label
  alone never overrides them. Decide bootstrap/recovery exceptions explicitly.

The owner must decide whether MANAGE_USERS intentionally remains full tenant
administration or adopts this narrower policy, including protected capabilities
and recovery exceptions. No delegation semantics were changed here.

Package 2 CONDITIONAL. RCQA-011 OPEN. Internet release NO-GO.
