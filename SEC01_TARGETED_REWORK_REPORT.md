# SEC-01 targeted authorization rework

2026-10-29. Worktree: `D:\RC_ATLAS_INSTITUTIONAL_SECURITY_20261027`.
Branch: `remediation/institutional-security`.
Base/HEAD: `8113299e5bfa1c310015f6b30fd2680abca2538d`.
This supplements the historical `SEC01_IMPLEMENTATION_REPORT.md`; it does not
replace earlier evidence. All implementation changes remain uncommitted.

## Root cause and selected contract

The executive snapshot checked VIEW_EXECUTIVE_SNAPSHOT once, then returned a
mixed response containing detailed indicators, tasks, notifications, reporting
records, audit-derived activity, custom template configuration and nested copies
in narrative/widget content. The general BI dashboard required granular grants.
Tenant filtering was present; the defect was inconsistent within-tenant capability
enforcement, not a reproduced cross-tenant escape.

Use the existing capabilities, without role-name exceptions or new permissions:

| Response category | Required capability in addition to snapshot access |
| --- | --- |
| Project metadata, geography, budget/risk overview, scalar executive counts/statuses, analytical contract | VIEW_EXECUTIVE_SNAPSHOT alone; this is the authorized executive summary |
| Indicator calculation rows | VIEW_INDICATORS **and** VIEW_REPORTS |
| Reporting records, period trends, district analytical rows | VIEW_REPORTS |
| Activities, tasks, overdue tasks, detailed workflow breakdown | VIEW_WORKPLAN |
| Notification details | VIEW_NOTIFICATIONS |
| Custom template configuration | VIEW_REPORTS, matching the existing template API |
| Activity-feed events | Known task/workflow events: VIEW_WORKPLAN; reporting events: VIEW_REPORTS; notification events: VIEW_NOTIFICATIONS; arbitrary audit events: VIEW_AUDIT_LOG |
| Widgets and narratives | Same source-category requirements; no nested bypass |

`services/analytical_authorization.py` owns the shared capability requirements and
snapshot projection. The general indicator KPI and full dashboard consume the same
requirements. The full dashboard still requires all five existing capabilities.
The snapshot still requires its entry capability and tenant/project ownership,
then preserves only authorized detail. Explicit empty permissions cannot enter.

Restricted fields retain their list/object shapes and are named in
`restricted_sections`, distinguishing withheld data from absence. Without template
access, a static executive KPI widget preserves useful summary functionality.
Mixed narratives are rebuilt from authorized summary fields plus authorized
trend/notification sections. Unknown widget/event types do not silently acquire
access for restricted users. Known workplan events remain available to operational
users; arbitrary audit content does not. Report previews describe restricted
indicator detail explicitly and use the permitted aggregate alert count rather
than interpreting redacted lists as zero.

Fully authorized responses retain their previous fields and values, including
missing versus zero and Package 2 methodology/provenance limitations. A complete
synthetic response was captured before production edits and compared after them;
only transient `notif_` identifiers are normalized for comparison. Project summaries
and executive aggregates are also compared directly for restricted users.

## Changed files in this rework

- `LogiTrackRC v4.4.py`: reuse shared indicator/dashboard requirements.
- `services/demo_workspace.py`: apply snapshot projection; prevent misleading
  zero counts in dependent report previews.
- `services/analytical_authorization.py` (new): capability contract and projection.
- `sec01_snapshot_tests.py` (new): paired-route, redaction, full-response, operational
  history, report-preview, explicit-denial and tenant tests.
- `sec01_regression.py`: focused rework suites, baseline capture and source hashes.
- `demo_smoke_tests.py`: use an explicit synthetic actor for builder fixtures and
  pass session tokens in the authentication argument rather than the API-key slot.
- `PLANNING_LOG.md`: append-only decisions.
- `docs/SEC01_ROLLOUT_AND_DELEGATION_CONDITIONS.md` (new), this report (new), and
  new `sec01-evidence/rework-*` evidence artifacts.

Existing permission semantics/model/persistence code and the previous SEC-01
evidence files are preserved. Package 2 evidence and recovery archives were not
accessed or altered.

## Failure-before evidence

`sec01-evidence/rework-before`: seven tests, 22 failing assertions/subtests,
zero errors/skips. Restricted snapshots exposed data while equivalent hardened
routes returned 403. Tenant denial and full-access baseline capture passed.
The source hash record binds this run to the pre-rework implementation.

`rework-after-initial` retained three comparison failures caused by freshly
generated notification IDs. The comparison was narrowed only for those transient
IDs; the frozen baseline was not overwritten.

`rework-compatibility-initial` retained one fixture error among 145 tests: an old
service test supplied the session token in the API-key argument, triggering its
test stub's anonymous bypass. Correct authentication preserved the task journey.

`rework-dependent-before`: nine tests, four failing assertions/subtests, zero
errors/skips. These exposed over-restriction of ordinary operational history and
report-preview interpretation of withheld indicator/notification data as zero.
Both were corrected without changing roles or delegation rules.

## Pass-after verification

- `rework-final`: **147/147 passed**, zero failures/errors/skips. Covers snapshot
  authorization, existing SEC-01 semantics, analytical consumers, methodology,
  demo workflows, tenant isolation, session and CSRF boundaries.
- `rework-verified-boundaries`: **10/10 passed**, zero failures/errors/skips on
  final source. This adds unknown-widget rejection and checks every known task
  event, including started/completed, while rejecting unclassified audit events.
- These overlap: **148 distinct tests**, not 157 distinct tests. The later
  production adjustment only added started/completed to the operational-event
  allowlist and is covered by the final boundary run.
- `rework-final-boundaries` retains one test-fixture error (a newly added synthetic
  audit event omitted its required timestamp). It was corrected without changing
  production behavior; no failed or skipped coverage is silently discarded.
- `git diff --check` passed. All 30 historical SEC-01 evidence files and the
  original manifest remained byte-identical. No source was staged or committed.

Machine-readable results and exact hashes are recorded in
`sec01-evidence/rework-verification-summary.json` and
`sec01-evidence/rework-manifest.json`. No full suite or browser acceptance was run.
Tests use disposable synthetic children of
`D:\RC_ATLAS_SEC01_VALIDATION_20261028_76cb8cb6`, in-process HTTP clients and disabled
providers. No server, live database or production credential was used in rework.

## Compatibility conditions and remaining decisions

Legacy permission semantics are unchanged: v0 ambiguous empty lists still inherit;
v1 null inherits, [] denies, and recognized lists grant only those capabilities.
No legacy migration, delegation change, SEC-02/03/04 work or identity change occurred.

The [rollout/delegation conditions](docs/SEC01_ROLLOUT_AND_DELEGATION_CONDITIONS.md)
document the old-binary data-loss/access-restoration risk and an enforceable release
prerequisite. PostgreSQL already rejects unexpected migration manifests on reads
and writes, but the present shared schema does not distinguish old/new binaries.
A separately approved marker migration can reuse that gate. JSON/SQLite require
demonstrated external artifact/identity/filesystem exclusion. None of those
deployment controls was applied here; production v1 rollout remains blocked.

MANAGE_USERS still permits self-assignment of broader roles/grants. The proposed
minimum is a tenant-owned grant ceiling, an additional governance capability for
grant changes, and a different authorized approver for self/governance elevation.
Owner approval is needed before changing those existing semantics.

The specific HIGH snapshot-route finding is addressed by the implementation and
focused tests; a fresh independent review has not yet been performed. The two
MEDIUM findings remain explicit rollout and delegation conditions. This is not
certification of every analytical/export route or enterprise readiness.

Package 2 **CONDITIONAL**. RCQA-011 **OPEN**. Internet release **NO-GO**.
