# SEC-01 implementation and focused verification

2026-10-28. Worktree: `D:\RC_ATLAS_INSTITUTIONAL_SECURITY_20261027`.
Branch: `remediation/institutional-security`.
Base/unchanged HEAD: `8113299e5bfa1c310015f6b30fd2680abca2538d`.
Preflight status was clean. Changes remain unstaged and uncommitted.

## Result and compatibility boundary

SEC-01 is implemented for new accounts and explicit permission updates, with the
required legacy compatibility exception. BI reads now enforce capabilities before
building the tenant-scoped response. No role templates or identity matching rules
were expanded. SEC-02, SEC-03 and SEC-04 were not implemented.

Source inspection and synthetic reproduction confirmed that legacy deserialization
normalizes missing, null and empty permissions to the same empty list. Effective
permissions then fall back to the role template. The original intent of those
persisted records cannot be recovered. No legacy-data migration was performed.

| Stored policy | Permission value | Effective permissions |
| --- | --- | --- |
| Missing version / version 0 | Missing, null, empty, or legacy normalization produces empty | Existing role-default fallback retained |
| Version 0 | Recognized nonempty grants | Existing normalized individual grants |
| Version 1 | `null` | Inherited role defaults |
| Version 1 | `[]` | No permissions |
| Version 1 | List of recognized IDs/aliases | Only those normalized, deduplicated grants |

New account creation uses version 1; omitted permissions mean inheritance. Updates
that omit permissions preserve the current mode, including legacy version 0.
Explicit permission updates opt that account into version 1. Role/profile changes
cannot turn explicit denial into inheritance. New API writes reject malformed or
unknown grants and client-supplied `permission_policy_version` with HTTP 400.

Canonical JSON/SQLite workspace snapshots and PostgreSQL JSONB retain the version
and null/list distinction. Relational user projections and repository writes use
the existing `permissions_json` column: legacy lists retain their encoding, while
v1 uses `{"permission_policy_version":1,"permissions":null}` or a list value.
No SQL schema change is needed. Malformed stored JSON or an invalid tagged policy
is rejected rather than granting defaults; invalid in-memory versioned policies
yield no permissions. Public account responses keep the existing effective
`permissions` list and add `permission_mode` and `permission_policy_version`.
The raw serializer retains the actual null/list value.

Backward compatibility here means old valid records retain their authorization
meaning under this code. Older application binaries cannot safely interpret v1
records; mixed-version writers or rollback after v1 writes require a separately
approved compatibility/conversion procedure. Legacy empty lists remain inherited
until an explicit permission update or a separately approved versioned migration.
Clients previously sending `[]` for inheritance must use null or omit permissions
on creation. Existing BI clients without the required capabilities now receive 403.

## BI capability contract

All listed capabilities are required together. Session authentication and tenant
filtering remain mandatory; API keys alone do not authorize access. A capable
foreign-tenant actor receives 404 on a foreign project dashboard; a caller lacking
capabilities receives 403 before resource lookup.

| GET route | Capabilities |
| --- | --- |
| `/v1/projects` | `VIEW_EXECUTIVE_SNAPSHOT` |
| `/v1/indicators`, `/v1/indicator_locations` | `VIEW_INDICATORS` |
| `/v1/activities`, `/v1/tasks`, `/v1/activity_indicator_links`, `/v1/kpi/workplan` | `VIEW_WORKPLAN` |
| `/v1/kpi/project`, `/v1/kpi/district` | `VIEW_REPORTS` |
| `/v1/kpi/indicator` | `VIEW_INDICATORS`, `VIEW_REPORTS` |
| `/v1/projects/{project_id}/dashboard` | `VIEW_EXECUTIVE_SNAPSHOT`, `VIEW_INDICATORS`, `VIEW_REPORTS`, `VIEW_WORKPLAN`, `VIEW_NOTIFICATIONS` |

Selected methodological calculations also retain their existing indicator/report
capabilities. Authorized collection responses are compared with the administrator
response; dashboard data fields are compared separately from transient operational
messages. The existing `/v1/dashboard/summary` portfolio check remains unchanged.

## Exact changed files

Production:

- `LogiTrackRC v4.4.py`: permission resolution, account builder/deserialization,
  public mode metadata, bootstrap validation response, eleven BI route checks.
- `shared/domain_models.py`: optional grants and default legacy version marker.
- `shared/permission_policy.py` (new): strict version/shape validation and relational codec.
- `repositories/users.py`: preserve policy in upsert, replacement and reload.
- `logitrack_platform/relational_store.py`: preserve policy in user projection writes.

Tests and evidence:

- `sec01_permission_tests.py` (new): 29 unit/API regression and contract tests.
- `sec01_permission_postgresql_tests.py` (new): two actual database tests.
- `sec01_regression.py` (new): isolated focused runner and evidence capture.
- `security_tenant_stabilization_tests.py`: retain foreign-resource 404 using a
  capable actor and separately assert the newly required capability 403.
- `PLANNING_LOG.md`: append-only decisions.
- This report (new) and `sec01-evidence/` (new); the evidence manifest inventories
  every evidence artifact. No existing Package 2 report/evidence was edited.

## Reproduction and verification

| Evidence directory under `sec01-evidence/` | Result |
| --- | --- |
| `before-final` | Before production edits: 24 tests, 57 failing assertions/subtests, 0 errors, 0 skips |
| `postgresql-before-final` | Before production edits: 2 tests, 4 failing assertions/subtests, 0 errors, 0 skips |
| `after-initial` | Same initial 24 tests passed |
| `postgresql-after` | 11/11 passed: two SEC-01, six existing methodology, three existing analytical tests |
| `compatibility-initial` | 186 tests: 183 passed, two failures, one error; all diagnostics retained |
| `final-focused` | 62/62 passed, zero errors/failures/skips; tested source hashes unchanged during the run |

The initial compatibility problems were two repository sync tests run with that
feature disabled by the runner, and the tenant-detail test expecting 404 from an
account now correctly denied at the capability gate. Repository tests now enable
sync within their synthetic fixture scope; the tenant assertion retains both
capability and tenant checks. No production permission grant was added to satisfy
a test. The final run includes all affected repository/tenant tests and five new
edge-case tests. The other 129 compatibility tests remain passing from the earlier
run. The aggregate is **202 distinct passing tests**, not a single 202-test run:
62 final focused + 129 unaffected compatibility + 11 PostgreSQL. The only later
production edit after the broad run removed an unused repository import.

Earlier diagnostic runs `before` and `postgresql-before` are retained. They include
test assertion errors from directly indexing a version field absent in the old
implementation; corrected assertions produced the error-free failure-before runs
above. Failure counts include subtests and are not counts of failing test methods.
The five later edge-case tests were added after remediation, not represented as
failure-before evidence. Source hashes were added to the runner for final-focused;
earlier logs do not contain a contemporaneous hash manifest.

Coverage includes legacy/inherited/empty/individual grants; both account APIs;
invalid writes without persisted mutation; bootstrap validation; JSON and relational
round trips; PostgreSQL restart; anonymous/API-key denial; capabilities; tenant
boundaries; existing analytical contracts; missing versus zero; methodology
provenance/history; session cookies and CSRF; and assignment-aware task permissions.
No tests were skipped. The full suite, browser acceptance, production/deployment
checks, live providers and complete route authorization certification were not run.
The installed TestClient emitted an existing deprecation warning; no dependencies
were installed or changed.

Tests used fresh synthetic children of
`D:\RC_ATLAS_SEC01_VALIDATION_20261028_76cb8cb6`, outside Git worktrees, with disposable
paths and external providers disabled. PostgreSQL isolation was independently
verified by SQL data-directory, port, loopback address and system-ID checks.
Three after-remediation clusters were stopped; no `postmaster.pid` remained anywhere
under this task's disposable parent at verification. Only nonsecret isolation
metadata is retained in the worktree evidence. No production credentials were used.

## Remaining decisions and limits

- A legacy permission migration needs an explicit institutional compatibility
  policy. SEC-01 deliberately does not claim to convert ambiguous stored empty lists.
- Rollback/mixed-writer support for versioned permission records needs a separately
  approved procedure before deployment. Malformed stored permission JSON now fails
  closed instead of the old parser's default-grant fallback.
- Tenant login namespaces and other audit findings remain open. This targeted
  review does not certify every demo/report/export/CLI authorization boundary.
- SEC-02 session revocation, SEC-03 scheduler isolation and SEC-04 import metadata
  remain separate work. No release, migration, commit or deployment was performed.

Package 2 remains **CONDITIONAL**. **RCQA-011 remains OPEN**.
**Internet release remains NO-GO**. No enterprise or production readiness claim.
