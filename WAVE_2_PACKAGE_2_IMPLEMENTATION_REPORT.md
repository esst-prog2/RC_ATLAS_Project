# Wave 2 Package 2 — Analytical Consumer Migration

Implementation dates: 2026-10-25–26; evidence and handoff finalized 2026-10-27.
Synthetic data only. No commit or deployment.

**Determination: CONDITIONAL.** The supported migration passes final regression,
real PostgreSQL and real Chrome validation. Deferred consumers, source bindings
and unapproved methodological policies remain outside that acceptance.
RCQA-011 remains partially addressed. Internet release remains **NO-GO**.

## 1. Verified starting point

The existing Package 1 worktree `D:\RC_ATLAS_W2_METHOD_CORE_20261024` was read at
branch `remediation/wave-2-methodological-core`, HEAD
`fadf7de6781c7fb96e3978e7b3b5aac5f195af26`. The commit message is
`feat(methodology): establish versioned KPI and data-quality core`; its diff
contains exactly 16 files. Git ancestry confirms that
`2ec64f7b100c317daed4061efe46b896a38e2888` is an ancestor.

The Package 1 report, SESSION_HANDOFF, frozen contract, tests and nine methodology
authority documents were reviewed. The Package 1 report/handoff describe the
pre-consolidation state; their old HEAD/uncommitted instructions are superseded
by the supplied and independently verified consolidation commit. No previous
conversation was relied on.

The new branch and proposed directory did not exist. A new worktree was created:

- Branch: `remediation/wave-2-analytical-consumers`.
- Worktree: `D:\RC_ATLAS_W2_ANALYTICAL_CONSUMERS_20261025`.
- HEAD/base: `fadf7de6781c7fb96e3978e7b3b5aac5f195af26`.
- Package 2 work remains uncommitted and unstaged.

Existing worktrees and the immutable QA archive were not edited. The protected
original checkout and its three protected untracked files were not inspected.
Only the explicitly authorized shared Git worktree/branch metadata was added.
No push, merge, rebase, cherry-pick, real-data migration, historical ownership
repair, live provider call or deployment occurred. This was sequential
implementation and validation; no specialist subagent delegation is claimed.

## 2. Recovery evidence

Independent checkpoint:
`D:\RC_ATLAS_W2_P2_RECOVERY_20261025_2d8be532`.

Before implementation, `git archive` exported the exact baseline to
`baseline.zip`, then restored it into the checkpoint's new
`restore-verification` directory. **175/175** source/restored SHA256 pairs matched.
The archive SHA256 is
`DCEC0D5D4C7445D8BD929EF6EE230FCC3EE49A5B6BF0A694812746399F0F4AC6`.
The manifest records every relative source path, byte length and hash, base commit,
branch, source path and restoration instructions.

The Package 1 checkpoint
`D:\RC_ATLAS_W2_GIT_RECOVERY_20261025_09229041` remains accessible; **175/175**
manifest file hashes were verified again. The nine read-only authority hashes
also matched Package 1's authority manifest.

Evidence: `wave2-package2-evidence/preflight-recovery.json` and the independent
checkpoint's `manifest.json`. Restoration means extracting the baseline archive
into another **new empty directory** and verifying all hashes. It requires no
overwrite, reset, clean, deletion or modification of an existing worktree. This
is a source recovery checkpoint, not a copy of canonical runtime data or secrets.

Final rechecks are retained in `preservation-recovery-final.json` and
`package1-preservation-analysis.json` under the evidence directory. Comparing the
Package 1 working-tree bytes to the committed archive found eleven line-ending-only
differences and its existing one-line consolidation authorization receipt in
PLANNING_LOG.md. Git confirms that receipt is its only tracked semantic difference.
Those files were not edited or normalized. Package 2 starts from the committed
tree, not from Package 1's uncommitted receipt.

## 3. Approved methodology applied

Primary authority: `METHODOLOGY_DECISION_REGISTER_V1.md`, supported by
`DEFECT_TO_IMPLEMENTATION_TRACEABILITY.md`,
`IMPLEMENTATION_WAVES_AND_DEPENDENCIES.md`, `RELEASE_GATE_CHECKLIST.md`,
`OWNER_DECISIONS.md`, the formal owner register and the transparency/UX/governance
contracts. Exact archive paths/hashes are in the preflight evidence.

| Authority | Package 2 application |
| --- | --- |
| OC-A01 | Five rule-specific dimensions, declared scope, population, coverage and exclusions. Universal quality composite removed from supported consumers; no fitness inference. |
| OC-A02 | Registered profile/version is the only calculation authority. Final achievement and schedule attainment stay separately named. No global threshold bands. |
| OC-A03 | Missing, invalid, N/A and excluded provisional observations never become zero. Legitimate zero survives API and browser presentation. Source values remain distinct from derived values. |
| OC-A04 | Cross-indicator/project/district/portfolio aggregates remain NOT_ASSESSED without approved compatible groups and a named estimand. No cross-currency total inferred. |
| OC-A05 | Legacy period records are an inventory, not an approved statistical series. No trend model, significance claim or beneficial-change threshold added. |
| QA-003 / RCQA-011 | Selected calculations require explicit period, UTC as_of, scope, method/version and source revision. Entire canonical result reconciles across consumers and restarts. |

No organization-specific method, quality rule, threshold, aggregation weight or
source binding was invented. Fictional test definitions are test-only approvals.
The independent oracle table was recorded in
`docs/WAVE_2_PACKAGE_2_CONTRACT.md` before adapter validation.

## 4. Inventory and classification

The companion `WAVE_2_PACKAGE_2_CONSUMER_MIGRATION_MATRIX.md` inventories **47
logical consumer boundaries**: **10 MIGRATE_NOW**, **24 ADAPT_WITH_GUARDRAILS**,
**11 DEFER_APPROVED**, **2 BLOCKED_DECISION**. These are not 47 individual widgets
or 47 separate engines. Related helpers sharing one decision are named in each
row. The candidate scan and manual call-site review include the inactive older
application, source ingestion, operational composites, reports and exporters.

Each row records code/functions, inputs, old assumptions, P1 compatibility,
implementation decision, methodological dependency, tests, entry point and
remaining limitation. Deferred/blocked consumers are preserved in the record;
regression success does not certify their methods.

## 5. Implementation architecture

`services/analytical_consumers.py` is a read adapter, not a second calculation
engine. It validates project/indicator/source ownership and immutable history,
resolves an explicitly selected registered definition, and invokes the unchanged
`services.methodology.calculate`. It is used by the canonical explanation API,
BI indicator rows, KPI API, project dashboard, selected dataset quality and
selected dataset narrative. Each carries the same complete calculation envelope.

`api/analytical_context.py` validates optional context for the existing endpoints.
No context yields an honest unavailable result; partial context is rejected.
Unknown/repeated parameters and conflicting URL/query project/indicator scope are
rejected, so an unsupported filter cannot silently produce an apparently filtered
answer. Context is not inferred from the clock, latest row or legacy target.
Mixed legacy endpoints retain their whole-response warning headers; the selected
calculation envelope identifies its own methodology. An as_of parameter cannot
certify deferred consumers or surrounding operational metrics.

The old `progress_mean_pct` and `progress_weighted_pct` keys retain their collection
positions but are null: the selected canonical metric is exposed as
`calculated_value` plus `calculation`, not silently renamed as a district mean.
Registered source population, period exclusions, exact arithmetic, display
rounding, method identity, source revision, quality profile and limitations remain
those of P1. No automatic binding of locations/history to TidyDataset was added.

Unconfigured quality returns all five dimensions as NOT_ASSESSED, with null
overall score and FITNESS_NOT_CONFIGURED. Selected quality uses the calculation's
exact assessed population/rules/coverage/exclusions. Selected narrative derives
deterministic text from that same result. It does not invoke freshness clocks or
interpretive threshold heuristics.

Legacy calculation implementations remain named `_legacy_*` references for
review; supported public helpers do not call them. Unsupported source-bound
progress and aggregate values are unavailable. Reported history percentages are
preserved separately as `reported_progress_value`; no source record was rewritten.
The CSV writer projects declared columns and appends state/limitation fields so
new adapter metadata does not break old rows. Atomic artifact publication and
full calculation exports remain Wave 4; RCQA-012 is not closed.

## 6. Files changed

Modified tracked files:

1. `LogiTrackRC v4.4.py` — integrate adapters, guard legacy derived outputs and
   composites, deterministic selected narrative, CSV projection, existing routes.
2. `api/methodology_routes.py` — canonical API delegates to the common adapter;
   strict context validation; existing write/CSRF/history flow retained.
3. `api/reporting_routes.py` — optional selected quality/narrative context.
4. `services/reporting.py` — authorize selected calculations before tenant scoping.
5. `services/demo_workspace.py` — guard indicator-derived delivery/quality
   composites, retain source records/workflows and explicit unavailable highlights.
6. `logitrack_studio.html` — canonical card/table/explanation reconciliation,
   five-dimension rendering, null/zero distinction and stale-result clearing.
7. `PLANNING_LOG.md` — append-only user/Codex decisions.

New source/test/document files:

8. `services/analytical_consumers.py`.
9. `api/analytical_context.py`.
10. `analytical_consumer_tests.py`.
11. `analytical_postgresql_tests.py`.
12. `analytical_regression.py`.
13. `analytical_runtime_acceptance.py`.
14. `analytical_browser_acceptance.js`.
15. `docs/WAVE_2_PACKAGE_2_CONTRACT.md`.
16. `WAVE_2_PACKAGE_2_CONSUMER_MIGRATION_MATRIX.md`.
17. This implementation report.

`wave2-package2-evidence/` contains generated manifests, logs, discovery output,
diagnostic edit scripts, response evidence and screenshots. Its final evidence
inventory enumerates these separately from the 17 reviewable source/test/docs.
No existing test file, methodology engine, SQL migration, PostgreSQL store,
authentication implementation or QA readiness/coverage record was changed.
`tested-source-inventory.json` freezes 116 executable/configuration source hashes
before final validation. `final-source-inventory.json` records all 185 source
files and the exact 17 changed deliverables; `final-evidence-inventory.json`
separately hashes the retained evidence (excluding its own hash).

## 7. Mathematical and consistency evidence

`analytical_consumer_tests.py` compares independently established expectations
with a direct canonical-engine call, the canonical API, KPI API, dashboard
indicator row, dataset quality and dataset narrative. It compares the entire
result/envelope, not only a rounded percentage.

| Independent input | Required result and tested distinction |
| --- | --- |
| B20/T100/A60 | 50.00%; exact50/1; numerator40/denominator80 |
| Planned150/A150 versus final target100 | Schedule100.00%; final ratio150.00%, uncapped; distinct meaning and identity |
| A0 versus missing/invalid/N/A | VALID0.00 versus null with distinct primary state |
| B=T | INVALID/null, ZERO_DENOMINATOR; no ratio fallback |
| Down B100/T20/A60 | 50.00%; direction follows approved definition |
| Mean0,5,MISSING,INVALID,N/A | Actual5/2, display2.50 for target100, included2/applicable4/source5; partial-coverage warning |
| Provisional and incompatible unit | Excluded, numeric result unavailable, explicit reason and flag counts |
| September1/30 with August31/October1 | Inclusive endpoints; two out-of-period exclusions; earlier as_of excludes September30 |
| Version2 target180 after approved effective boundary | 25.00%, distinct definition/calculation identity; P1 history remains immutable |
| Changed source60→100 | 50.00→100.00; changed source revision; saved original instance retained |
| MILESTONE/unconfigured method | NOT_ASSESSED/UNCONFIGURED with null numeric result |
| Missing quality rules | Five NOT_ASSESSED dimensions, no overall score |

P1's independent 45/50 completeness, 7/8 uniqueness, maintenance-band,
currency/state/domain/effective-date tests are rerun, not treated as historical
evidence. New tests also cover unknown filters, ownership blocking without repair,
API permission boundaries, no calculation writes and synthetic CSV compatibility.

Methodological differences are intentional and documented in the matrix: old
location aggregates/quality composites have no approved authority, while a
registered dataset result does. The migration does not alter formulas or filters
to make the legacy answer appear correct.

## 8. PostgreSQL, security and recovery

The existing PostgreSQL JSONB aggregate, relational constraints, same-transaction
integrity edges and append-only history remain unchanged. There is no schema
change, parallel canonical store, dual write or startup migration.

Selected calculation/quality/narrative reads require both VIEW_INDICATORS and
VIEW_REPORTS and validate organization/project/indicator/source ownership.
Context-free metadata retains its established API contract. Registration and
saved instances retain organization-admin, CSRF, session and workspace-version
requirements. Unresolved ownership is explicitly blocked rather than repaired.

Actual disposable PostgreSQL tests verify complete result equality, no canonical
write on consumer reads, source revision changes, immutable saved history,
foreign-tenant denial and database restart. The process acceptance runner also
verifies a different API PID, restored session/definition/history, a database
outage returning503, subsequent database recovery and dump/restore into a new
database. This is actual PostgreSQL17.11/PostGIS3.6.2, not mocks.

Stateful runs use fresh disposable paths, synthetic tenants and disabled
providers. PostgreSQL/process runtime roots are under
`D:\RC_ATLAS_W2_P2_VALIDATION_20261025`; existing unit/API fixtures also allocate
their own fresh temporary directories. Each PostgreSQL cluster uses loopback
listeners and is independently checked by SQL for
data directory, port, listen address and server identity. Existing validation
installations supply binaries/dependencies only. The accepted runtime cluster is
`cluster_ci_erzyi`, independently verified at loopback port 60888, server identity
7701045105803783164. API process 24728 was replaced by process 7620; owned API and
database processes were stopped by the runner. Full isolation evidence is in
`runtime-final/runtime-isolation.json`.

## 9. Validation results

| Run | Outcome | Evidence |
| --- | --- | --- |
| Fresh P1 baseline in new disposable runtime | 367/367 PASS, including 26 actual PostgreSQL tests; zero failures/errors/skips | `wave2-package2-evidence/baseline/results.json` |
| P1 compatibility after initial adapter | 48/48 PASS, including 6 actual PostgreSQL tests | `core-compatibility/results.json` |
| Initial complete regression before header correction | 387/387 PASS, including 29 actual PostgreSQL tests; correction and added test verified separately below | `full-release/results.json` |
| Final focused consumer/core/API/PG | 69/69 PASS, including 9 actual PostgreSQL tests; zero failures/errors/skips; 72.067 seconds | `focused-final/results.json` |
| Complete final regression | 388/388 PASS, including 29 actual PostgreSQL tests; zero failures/errors/skips; 355.026 seconds | `full-final/results.json` |
| Final process/database/restore acceptance | 6/6 PASS groups | `runtime-final/runtime-results.json` |
| Final installed Chrome acceptance | 13/13 PASS; Chrome 155.0.8059.85; zero page errors | `runtime-final/browser/browser-results.json` |

Earlier failed diagnostic runs are retained. `focused-initial` exposed an adapter
reauthorization after tenant scoping had deliberately removed sessions; authorization
was moved before scoping. `focused-corrected` exposed an overly specific provisional
reason assertion and a restart comparison of whole operational dashboards with
new notification IDs. The test now checks the approved P1 reason
FLAG_POLICY_NOT_APPROVED and independently verifies the provisional flag/null
result. Restart reconciliation compares all calculation fields, while retaining
full responses and explicitly excluding the unclaimed operational envelope.
`runtime-initial` preserves the same diagnostic restart failure. No existing test
was weakened or removed. Operational envelope nondeterminism remains an RCQA-011
limitation, not a claimed PASS.

Final review also reproduced a query-based response-header mislabel in
`header-diagnostic.txt`: an as_of parameter could label a deferred KPI response as
the new contract. That override was removed, the legacy whole-response warning
was retained, and a new regression test covers the boundary. Final validation
uses the frozen corrected source; earlier runs remain diagnostic evidence.

`wave2-package2-evidence/acceptance-summary.json` consolidates final run results,
the 47-row classification count, recovery/authority hash rechecks and cleanup.
No PostgreSQL postmaster PID files remain under the disposable validation parent;
the process acceptance runner confirms that its API/database processes stopped.
All 116 frozen executable/configuration hashes match the final source inventory.

## 10. Authorized browser reachability

Use the existing MEAL Officer → Indicator Intelligence workflow. An authorized
user selects a project/indicator, registered method/version, reporting start/end
and explicit UTC reference time. **How is this calculated?** loads the canonical
explanation and the existing KPI consumer. Both must match before display.
The card displays the canonical value; **View indicator table** moves focus to
the second representation with the same value, scope, method version, coverage,
calculation ID and source revision. No browser-side KPI formula is used.

The real Chrome run proves 50% final achievement, separate 100% schedule attainment,
quality disclosure, zero/missing presentation, unavailable unconfigured state,
error/input preservation, stale clearing, EN/PT/FR controls, all four specified
viewports, cross-tab logout and a foreign cookie session denied at the KPI API.
The desktop reconciliation table and 360px explanation screenshot were visually
inspected and are readable. This is not a full dashboard redesign/accessibility
or statistical/portfolio acceptance claim.

## 11. Unsupported consumers and approval dependencies

The matrix preserves all 11 deferred boundaries and 2 decision-blocked boundaries.
Remaining work includes comparable portfolio/geographic groups, historical
observation binding, descriptive-series comparability, approved operational
confidence/risk rules, organization quality/fitness gates, currency authority,
full dashboard filter/renderer migration and immutable report/export snapshots.
The older `logitrack_rc_v4_4.py` application is outside the supported entry point
and must not be used as an alternate validated deployment.

Some retained legacy overview/rendering paths still have assumptions about absent
aggregate values. They are recorded as deferred, unvalidated and release-blocking;
they are not counted among the ten migrated consumers. Operational task-based
confidence/load/risk values likewise retain their separate legacy status and
require approved policy before methodological acceptance. No new policy was
invented to replace them. Approved unsupported states cover migrated boundaries.

P1 limitations persist: milestone evidence/weights, downward target-ratio semantics,
provisional/imputed eligibility, schedule interpolation, quality fitness gates,
configuration retirement, raw historical source retention and role-specific
lineage depth. Raw source revision hashes do not reconstruct overwritten datasets.

## 12. RCQA-011 and acceptance boundary

Package 2 is **CONDITIONAL**, not blocked for further controlled review. Its
supported calculations and authorized Studio workflow pass the stated synthetic
acceptance checks. Numerical enablement of the blocked profiles and methodological
acceptance of deferred renderers/operational scores require separate approved work.

RCQA-011 is **PARTIALLY ADDRESSED, NOT CLOSED**. Supported migrated calculations
have deterministic explicit context and reconcile across engine/API/Studio/PG
restart. Operational clocks/notification IDs, deferred consumers, report artifacts
and broader release gates still prevent system-wide closure. Specialist oracle
readiness was not changed. Internet release remains **NO-GO**.

Recommended next controlled Wave 2 package: approved historical observation/source
bindings and configuration lifecycle, followed by remaining operational clock and
consumer-state propagation. Freeze independent population/filter/ownership and
time-boundary oracles first. Portfolio, geographic/risk and full artifact work
must retain their approved later-wave boundaries.

## SESSION_HANDOFF

1. Work only in `D:\RC_ATLAS_W2_ANALYTICAL_CONSUMERS_20261025`, branch
   `remediation/wave-2-analytical-consumers`. Verify HEAD is still
   `fadf7de6781c7fb96e3978e7b3b5aac5f195af26`; review the uncommitted diff and new
   files. No commit/push/merge/deploy authorization is implied.
2. Read this report, the consumer matrix, `docs/WAVE_2_PACKAGE_2_CONTRACT.md`, P1's
   contract and the nine hashed authority documents. Preserve all deferred and
   blocked rows and keep `PLANNING_LOG.md` append-only.
3. Recovery checkpoint is `D:\RC_ATLAS_W2_P2_RECOVERY_20261025_2d8be532`.
   Verify `manifest.json` and archive hash; restore only into another new empty
   directory. Preserve all old worktrees/checkpoints and the read-only archive.
4. The pure methodology engine and schema are unchanged. New adapters are in
   `services/analytical_consumers.py`; strict read context is in
   `api/analytical_context.py`. All registered source bindings remain explicit.
5. For isolated tests set `RCATLAS_PG_TEST_BIN` to
   `D:\RC_ATLAS_PG_VALIDATION_20261022_66feba61\postgres\pgsql\bin` and
   `RCATLAS_PG_TEST_ROOT` to `D:\RC_ATLAS_W2_P2_VALIDATION_20261025` (or another new
   disposable parent). Invoke
   `D:\RC_ATLAS_PG_VALIDATION_20261022_66feba61\venv\Scripts\python.exe`
   with `analytical_regression.py --suite focused --evidence <new-path>` or
   `--suite all`. The runner creates fresh isolated paths and rejects skips as
   success. Never set these variables to a canonical workspace.
6. For actual process/Chrome/restore acceptance run
   `analytical_runtime_acceptance.py --evidence <new-path>` with
   `PLAYWRIGHT_CORE_PATH=D:\RC_ATLAS_PG_VALIDATION_20261022_66feba61\browser-tools\node_modules\playwright-core`
   and `RCATLAS_CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe`.
   It owns and stops its API/database processes. Providers remain disabled.
7. Reconcile complete calculation envelopes, not only display values. Surrounding
   operational timestamps/notification identity remain explicitly outside this
   package's reproducibility claim. Never mask that boundary with a broad PASS.
8. Use the final source/evidence manifests before further work. Report, matrix and
   SESSION_HANDOFF contain the necessary continuation context; previous chats are
   unnecessary. RCQA-011 remains open and internet release remains NO-GO.
9. Final evidence is in `focused-final` (69/69, 9 PostgreSQL), `full-final`
   (388/388, 29 PostgreSQL) and `runtime-final` (6/6 groups, 13/13 real Chrome).
   All runs have zero skips; complete regression also has zero failures/errors.
   Source hashes cover the final header correction and its new regression test.
   Do not substitute the earlier diagnostic runs for these final results.
