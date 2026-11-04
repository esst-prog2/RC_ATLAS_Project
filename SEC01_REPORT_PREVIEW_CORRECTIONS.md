# SEC-01 final report-preview corrections

Completed 2026-11-04 in `D:\RC_ATLAS_INSTITUTIONAL_SECURITY_20261027`.
Branch `remediation/institutional-security`; HEAD remains
`8113299e5bfa1c310015f6b30fd2680abca2538d`. Unstaged and uncommitted.

## Findings and correction

The portfolio report branch copied notification titles from a tenant-scoped
workspace without checking VIEW_NOTIFICATIONS. VIEW_PORTFOLIO and report access
therefore allowed details denied by the notification API. The project branch
consumed an already projected snapshot but discarded its notification restriction
marker, leaving an unexplained empty risk section.

Both report branches now use `allows_category(..., 'notifications')` from the
existing analytical authorization policy. The snapshot projector uses this same
helper. Without VIEW_NOTIFICATIONS, the report's risk section has empty bullets
and the body "Notification details are restricted by your permissions." The
report additionally returns `restricted_sections: ["notifications"]`. Authorized
summary text and aggregate counts are retained; withheld rows are not counted as
zero. Authorized empty notification results remain unmarked and distinct from
restricted results. No role name, report capability or portfolio capability
substitutes for the notification capability.

Fully authorized reports are unchanged, including all three audiences in both
project and portfolio scope. Existing report-entry permissions, project/tenant
scoping and all SEC-01 permission-mode behavior remain unchanged. No new
capabilities, roles, identity changes or SEC-02/03/04 work were introduced.

## Exact files changed for this correction

- `services/analytical_authorization.py`: reusable existing-category check.
- `services/demo_workspace.py`: retain the authenticated actor and apply the
  common notification restriction to the final report response.
- `sec01_report_preview_tests.py` (new): five focused tests, including paired
  notification routes, all audiences, explicit denial, tenant boundaries,
  authorized-empty versus restricted details, aggregates and exact reports.
- `sec01_snapshot_tests.py`: freeze the previously unfrozen local calendar date
  used by legacy workplan/deadline calculations in the synthetic fixture.
- `sec01_regression.py`: dedicated report suites and immutable baseline capture;
  allow the dedicated worktree-contained disposable root for this authorization.
- `PLANNING_LOG.md`: append-only decisions and verification outcome.
- This report (new), and new `sec01-evidence/report-preview-*` artifacts.

The historical implementation/rework reports, rollout/delegation conditions,
evidence and recovery manifests were not edited. Disposable synthetic runtimes
were created only under this worktree's `.sec01-disposable` directory; TEMP/TMP,
canonical JSON/SQLite and projection paths were isolated within each fresh child.
Providers and scheduling were disabled. No server, production data, credentials,
installation or external runtime writes were used.

## Reproduction and verification

- `report-preview-before`: 5 tests, 12 failures/subtests, no errors/skips.
  Captured all six authorized report responses before production edits. One
  failure came from an invalid synthetic foreign-project clone; retained intact.
- `report-preview-confirmed-before`: 15 tests, 12 failures/subtests, no
  errors/skips. The corrected foreign-project fixture passed. Eleven failures
  demonstrated notification disclosure or absent restriction metadata; one
  historical snapshot comparison failed because local `date.today()` was not
  frozen even though UTC was frozen.
- `report-preview-clocked-before`: **15 tests, 11 expected failures/subtests,
  zero errors/skips**, with production logic still unchanged. Snapshot, tenant
  denial and authorized-response checks passed. The two findings were reproduced
  with the protected notification route returning 403 for restricted grants.
- `report-preview-after`: **153/153 passed**, zero failures/errors/skips, with
  source hashes unchanged during execution. Covers both new findings, existing
  snapshot authorization, permission semantics, analytical consumers, missing
  versus zero, methodology/version history/provenance, demo workflows, tenant
  isolation, sessions and CSRF.
- All six fully authorized reports matched the immutable pre-correction JSON
  exactly, without response normalization. The older snapshot comparison retains
  its existing normalization of transient notification IDs only.

The fixture now freezes the local calendar day at each original capture day:
2026-10-29 for the older snapshot; 2026-10-30 for report previews. The existing
UTC fixture remains 2026-10-28T12:00:00Z. This reproduces the original test inputs
without altering production date behavior, rewriting baselines or relaxing data
assertions. All diagnostic runs remain available.

`git diff --check` passed. The final verification summary and new manifest bind
the tested files and evidence; all 62 evidence files present before this task
remain byte-identical, including both historical manifests. Historical manifests
describe their original source revisions; a new manifest records the current one.
No full suite, browser acceptance or PostgreSQL execution was needed for these
report-only changes; those are not claimed as newly verified.

## Readiness and remaining risks

Both report-preview findings are corrected and focused verification passes.
SEC-01 is ready for a controlled local checkpoint, subject to the owner's review;
no staging or commit has been performed, and this is not a new independent audit.

Production remains blocked by the existing incompatible-old-binary exclusion
requirement and unresolved MANAGE_USERS delegation/self-escalation policy.
See `docs/SEC01_ROLLOUT_AND_DELEGATION_CONDITIONS.md`; neither deployment controls
nor delegation semantics were changed. This correction does not certify unrelated
portfolio/export endpoints or enterprise readiness.

Package 2 **CONDITIONAL**. RCQA-011 **OPEN**. Internet release **NO-GO**.
