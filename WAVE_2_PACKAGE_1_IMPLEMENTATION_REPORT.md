# Wave 2 Package 1 — Methodological Core & KPI Integrity

Implementation dates: 2026-10-24–2026-10-25. Synthetic data only.

**Determination: CONDITIONAL — Package 1 implemented; all final checks PASS.**
The supported methodological core is verified. Organization-specific configuration,
unsupported profiles and remaining legacy consumers retain explicit limitations;
specialist governance acceptance is not inferred. Wave 1 remains CONDITIONAL;
internet release remains **NO-GO**.
This report does not close Wave 2 or change specialist scenario readiness.

## Verified starting point and preservation

The professional worktree `D:\RC_ATLAS_REMEDIATION_W1_20261014` was verified on
`remediation/wave-1-security-integrity` at the exact consolidation commit
`2ec64f7b100c317daed4061efe46b896a38e2888`. The consolidation completion report,
Wave 1 closure/session-security reports, and PostgreSQL architecture/validation
reports were reviewed before implementation.

A separate worktree was created at `D:\RC_ATLAS_W2_METHOD_CORE_20261024`, branch
`remediation/wave-2-methodological-core`, from that exact commit. HEAD remains at
the base commit; all Package 1 changes are uncommitted and unstaged. No push,
merge, rebase, deployment, real-data migration or historical ownership repair occurred.

Wave 1's modified `PLANNING_LOG.md`, untracked pre-commit review and generated
evidence directories were inventoried, as were excluded runtime/cache files.
The final check confirms the same Git status and ignored-file inventory, and
165/165 source/review hashes unchanged. All nine methodology authority documents
retain their original hashes. The protected original checkout and its three
protected untracked files were not accessed. The audit archive was read only.

Both existing recovery checkpoints remain available and were rehashed:

| Checkpoint | Verified files |
| --- | ---: |
| `D:\RC_ATLAS_W1_RECOVERY_20261022_66feba61` | 186/186 |
| `D:\RC_ATLAS_GIT_RECOVERY_20261023_8347c31f` | 164/164 |

Evidence: `wave2-evidence/preflight.json`, `preservation-final.json`,
`recovery-final.json`, and `methodology-authorities.json`.

## Methodological authority and traceability

Primary authority is the approved specialist `METHODOLOGY_DECISION_REGISTER_V1.md`,
with `DEFECT_TO_IMPLEMENTATION_TRACEABILITY.md`,
`IMPLEMENTATION_WAVES_AND_DEPENDENCIES.md`, `RELEASE_GATE_CHECKLIST.md`,
`OWNER_DECISIONS.md`, the formal owner register, and the calculation-transparency,
explanation-UX and governance/versioning contracts. Exact read-only archive paths
and hashes are recorded in `methodology-authorities.json`.

The engineering contract and independent expected values were written in
`docs/WAVE_2_PACKAGE_1_CONTRACT.md` before implementation. Fictional test approvals
do not approve real organizational thresholds or indicator configurations.

| Decision / defect | Implementation | Independent tests / evidence | Closure boundary |
| --- | --- | --- | --- |
| OC-A01 / DAT-QUAL-001 | `services/methodology.py`: `validate_quality`, `quality_profile`; five dimensions and explicit rules/populations/exclusions | Core tests: `test_completeness_independent_45_of_50_fixture`, `test_uniqueness_independent_seven_of_eight_fixture`, `test_conformance_timeliness_traceability_explicit_rules`, `test_quality_respects_mapped_observation_state_and_domain`; Chrome quality disclosure | Foundation implemented; fitness gates and legacy quality consumers deferred |
| OC-A02 / DAT-KPI-001 | `definition`, `_calculate_value`, `calculate`; versioned profiles, uncapped exact values, separate final achievement and schedule attainment | Core approved-change/schedule/direction/zero-denominator/band tests; API explanation test; Chrome separate 50% and 100% results | Supported profiles implemented; milestone evidence/weights and remaining consumer migration deferred |
| OC-A03 / DAT-KPI-002 | `cell`, `observation`, coverage/exclusions; explicit primary states and optional flags | Core state fixture `[0,5,MISSING,INVALID,N/A]` → mean 2.5, included/applicable 2/4; incompatible-unit/currency and flag tests | Implemented in the new core; broad widget/import/export migration deferred |
| OC-A04 / DAT-PORT-001 | `portfolio_aggregation=NOT_ASSESSED`; explicit aggregation eligibility | `test_explicit_guardrails_and_source_data_minimization` | Guardrail only; no advanced portfolio implementation |
| OC-A05 / DAT-INTEL-001 | `statistical_trend=NOT_ASSESSED`; no inferential or causal output | Same guardrail test; explanation limitations | Guardrail only; no trend-analysis implementation |
| QA-003 / RCQA-011 | Explicit reporting period, UTC `as_of`, source revision, method/version and deterministic instance identity | Core boundary/reproducibility tests; API `test_exact_context_is_reproducible_across_auth_workspace_changes`; actual API/PG restart equality | **Partially addressed**, not closed system-wide; old consumers still use legacy logic |
| Wave 1 isolation/integrity/session protections | Existing permissions, cookie/CSRF controls and PostgreSQL transaction boundary reused | API foreign-tenant/role/CSRF tests; six real PG tests; Chrome login/logout; full regression | Preserved within tested scope; no change to release acceptance |

The specialist audit was not repeated. No `qa/oracle_readiness.yaml` or specialist
coverage/readiness record was changed. This was sequential implementation and
validation; no subagent audit delegation is claimed.

## Architecture and files changed

| Files | Purpose |
| --- | --- |
| `services/methodology.py` | Pure deterministic definitions, exact arithmetic, states, five quality dimensions, explanation instances and append-only validation |
| `api/methodology_routes.py` | Tenant-scoped registration, calculation and historical-instance endpoints |
| `LogiTrackRC v4.4.py` | Optional indicator extension, serialization, legacy-store history protection, route wiring and legacy-methodology response headers |
| `logitrack_platform/persistence_validation.py` | Validate the nested extension and same-tenant dataset integrity edges |
| `logitrack_platform/postgresql_store.py` | Validate append-only history against the locked canonical revision before transactional writes |
| `logitrack_studio.html` | Narrow inline explanation form/results in existing Indicator Intelligence; EN/PT/FR controls, stale-result clearing and refresh handling |
| `methodology_fixtures.py`, `methodology_core_tests.py`, `methodology_api_tests.py`, `methodology_postgresql_tests.py` | Fictional oracles and 48 new tests |
| `methodology_regression.py`, `methodology_runtime_acceptance.py`, `methodology_browser_acceptance.js` | Isolated reproducible runners, actual process/PG recovery and installed Chrome checks |
| `docs/WAVE_2_PACKAGE_1_CONTRACT.md`, this report, `PLANNING_LOG.md` | Contract, evidence/handoff and append-only decisions |
| `wave2-evidence/` | Generated local review evidence; not runtime storage or production data |

Definitions and explicitly saved calculation instances live under the canonical
indicator's optional `methodology` extension, schema version 1. Inputs come from
an explicitly selected same-tenant existing TidyDataset. There is no second
canonical observation store or new dual-write path. A bound dataset must represent
the intended indicator population; Package 1 applies explicit period/as-of filters,
not an inferred row-to-indicator mapping or general filter language.

PostgreSQL's existing JSONB aggregate and entity/relationship integrity index are
updated in one transaction. The application role and expected workspace version
remain mandatory. Dataset edges reject foreign-tenant references. Saved history
cannot be removed or edited by other aggregate writers, including deletion of its
parent; a governed retention/lifecycle operation is future work. JSON/SQLite
compatibility paths also preserve registered history.

No SQL DDL change was necessary. Existing `001_canonical.sql` and `002_postgis.sql`
and their checksum ledger remain unchanged; no migration runs at application startup.

## Calculation and explanation contracts

Definitions record tenant/project/indicator identity, method identity and semantic
version, engine version, approval reference/effective interval, intended use and
limitations, unit/currency/scale/domain/direction, baseline/target/reference period,
source mapping, aggregation rationale, quality rules, formula and applicable
numerator/denominator meanings. Definitions are immutable; overlapping approved
effective intervals for the same metric kind are rejected. Exact retries are no-ops.

Supported arithmetic is change from baseline in either approved direction,
upward target ratio, exact-date planned-target ratio, and inclusive maintenance
bands. `NO_AUTOMATIC_PROGRESS` returns unavailable numeric progress. `MILESTONE`
is recognized but `NOT_ASSESSED` pending its evidence/weights contract. No universal
cap, status band, missing target, downward ratio or schedule interpolation is inferred.

The approved example B=20, T=100, A=60 returns final-target achievement **50%**;
planned target=60 at the explicit reference date returns separate schedule
attainment **100%**. A=150/T=100 returns **150%**, uncapped. Rational arithmetic
preserves decimal inputs exactly; two-decimal display rounding is separate.
Zero denominators return INVALID and no numeric percentage.

Reporting dates are inclusive. Observations after the explicit UTC as-of date are
excluded; method effective intervals are start-inclusive/end-exclusive. `as_of`
is an analytical cutoff, not a reconstruction of historically available knowledge.
The actual source revision used is identified by hash. No internal clock controls
calculation values; saved-at audit metadata is separate.

Each instance carries its definition hash/version, context, formula, exact inputs,
actual/baseline/target/planned target, numerator/denominator, unrounded and display
results, filters, coverage, exclusions, source and row hashes, quality profile,
warnings, limitations and deterministic calculation/cache identity. Definition and
instance are separate objects. Numeric inputs are retained; arbitrary source rows
and personal identifiers are not copied into history. Overwritten source datasets
cannot be reconstructed from hashes alone.

## Data states and quality semantics

VALID, MISSING, INVALID and NOT_APPLICABLE remain distinct. Legitimate zero enters
arithmetic; missing does not. Invalid domains, units/currencies, dates, identities
and flags produce explicit exclusions. N/A is excluded from applicability.
PROVISIONAL/IMPUTED flags never erase primary state; they are excluded from Package
1 calculations, and imputation requires its original state. No imputation is performed.

`single` refuses multiple eligible observations. `mean` requires an approved
within-definition rationale. All duplicate identity members are excluded, avoiding
an arbitrary winner. Coverage distinguishes source total, in-period, applicable,
eligible, excluded and out-of-period observations, with state and flag counts.

Quality dimensions report their declared use, rules, population, numerator,
denominator, exclusions and exact/display ratios. Completeness uses applicable
required cells; conformance uses configured tests; uniqueness uses distinct
assessable keys / assessable records; timeliness uses an approved maximum age at
explicit as_of; traceability checks configured provenance fields. Mapped primary
observation validity and domain failures are reflected in quality assessment.

Missing rules or zero assessable populations yield NOT_ASSESSED. Fitness remains
FITNESS_NOT_CONFIGURED; no overall quality score, statistical precision or automatic
fitness judgment is produced. Traceability presence checks do not certify source
authenticity. General cross-field/domain-specific rules remain future configuration.

## Authorized user reachability and API compatibility

Use the existing **MEAL Officer → Indicator Intelligence** view. Select the
indicator and registered method, supply reporting dates and an explicit UTC
reference timestamp, then activate **How is this calculated?**. The panel shows
value or unavailable state, meaning, formula, period/as-of, version, coverage,
exclusions and limitations. Native disclosure contains intermediates and quality
dimensions. Inputs, errors, scope changes, refresh and logout clear stale results.

Read access requires VIEW_INDICATORS and VIEW_REPORTS. Method registration and
instance saving additionally require an organization administrator with
MANAGE_ORGANIZATION, existing CSRF protection and expected workspace version.
No methodology-authoring interface or role-menu expansion was introduced.

All new endpoints are under
`/v1/projects/{project_id}/indicators/{indicator_id}`: GET/POST `/methodology`,
GET `/calculation`, POST `/calculation-instances`, and GET
`/calculation-instances/{calculation_id}`. Full payload/query contracts are in the
contract document. Historical reads recheck tenant/source authorization. GET
calculation does not create history. Existing session-touch behavior is unchanged.

Existing KPI response bodies remain compatible; legacy analytics receive an
explicit unvalidated warning in the explanation view and response headers on
covered legacy routes. This is not a migration of every legacy KPI, quality,
narrative, dashboard or export consumer. They cannot be treated as newly validated.
Controls are localized EN/PT/FR; approved source prose and technical state codes
retain their recorded language. No full accessibility or dashboard-redesign claim.

## Validation evidence

All stateful execution used newly created disposable runtimes under
`D:\RC_ATLAS_W2_VALIDATION_20261024`, synthetic tenants and observations, disabled
providers, loopback listeners and isolated canonical paths. Existing validation
installations supplied binaries/dependencies only. PostgreSQL isolation checks
verified the actual data directory, port, server identity and loopback binding.
No test substituted a mock for PostgreSQL or Chrome acceptance.

| Run | Result | Evidence |
| --- | --- | --- |
| Fresh consolidation baseline before source changes | 319/319 PASS; 20 real PostgreSQL tests; zero failures/errors/skips | `wave2-evidence/baseline/results.json` |
| Final focused core/API/PostgreSQL | 48/48 PASS = 30 core + 12 API + 6 real PostgreSQL; zero failures/errors/skips | `wave2-evidence/focused-release/results.json` |
| Final full regression | 367/367 PASS, including 26 real PostgreSQL tests; zero failures/errors/skips | `wave2-evidence/full-release/results.json` |
| Actual process/database/browser/restore acceptance | 5/5 PASS groups (one group wraps the separately counted Chrome checks) | `wave2-evidence/runtime-refresh/runtime-results.json` |
| Installed Chrome workflow | 10/10 PASS; Chrome 155.0.8059.85; zero page errors | `wave2-evidence/runtime-refresh/browser/browser-results.json` |
| Preservation/recovery | 165/165 source/review hashes; nine authorities unchanged; recovery 186/186 and 164/164 | Preservation/recovery evidence above |

Real PostgreSQL tests cover JSONB roundtrip, same-transaction source edges,
cross-tenant atomic rejection, immutable history, stale writers, actual database
restart, corrupt-instance rejection and migration idempotency. The process runner
additionally checks a new API PID with exact definition/result/session recovery,
database outage returning 503, restart equality, foreign reads after restart and
pg_dump/restore into a different fresh database.

The accepted runtime reports PostgreSQL **17.11** and PostGIS **3.6.2**. Its
independently checked cluster is `cluster_u0pzl9dj`; the final regression used
`method_regression_vipmct0u` and separate fresh clusters `cluster_6mc4i3u4` and
`cluster_bcu868__`. The accepted runtime's API and database processes were stopped;
synthetic artifacts are retained outside the repository. `process-cleanup.json`
records the final cluster/process checks.

Chrome checked cookie login without persistent bearer storage, keyboard calculation
and exact 50% explanation, quality disclosure, separate 100% schedule attainment,
error/stale-result handling, UNCONFIGURED state, EN/PT/FR controls and unchanged
arithmetic, four viewports (360×800, 768×1024, 1366×768, 1920×1080), cross-tab
logout clearing, and absence of JavaScript page errors. Screenshots are under
`wave2-evidence/runtime-refresh/browser/`; the desktop and 360-pixel captures were
also visually inspected and are readable without horizontal panel overflow.

Final source/review hashes are in `wave2-evidence/source-manifest-final.json`;
`git diff --check` passes. The full regression ran on the final executable source.
Only report, planning-log and evidence updates followed. Timing is retained as
observed execution evidence, not claimed as a performance benchmark.

Earlier diagnostic browser runs are retained honestly: email-form fixture mismatch;
organization-admin navigation outside the MEAL workflow; missing then unscoped
synthetic dashboard templates; and a locale-refresh race exposed after six checks
passed. The fixtures were corrected without relaxing tenant or navigation controls.
The refresh race was fixed in the new panel. These failed diagnostic runs are not
counted as acceptance. Existing fault-injection test tracebacks and the Starlette
test-client deprecation warning are retained in logs and are not test failures.

## Remaining decisions, limitations and next package

No unapproved organization-specific methodology was adopted. Actual profile
selection, domains, baselines/targets, planned trajectories, bands, aggregation
rationale and quality rules still require owner configuration. Missing configuration
stays explicitly unavailable. No real indicator was automatically configured.

Remaining controlled work includes milestone evidence/weights, downward-ratio
semantics, provisional/imputed eligibility, schedule interpolation/change equivalents,
fitness gates, currency-conversion authority, method withdrawal/retirement,
historical source revision retention and role-specific lineage disclosure.
Open-ended approved versions cannot be retroactively shortened by editing history.
Retention/scale policy for saved instances remains to be governed.

**Recommended next controlled Wave 2 package:** migrate the remaining indicator
and data-quality consumers to the shared method/context/explanation contract,
with explicitly approved fixture bindings and configuration lifecycle decisions.
Complete the RCQA-011 consumer inventory and deterministic clock migration in that
controlled scope. Portfolio aggregation, statistical trend analysis and risk-signal
engines remain later packages; dashboard redesign, geography, PDF/PPTX, new
notification channels and predictive models remain out of this package.

QA Lead review and scenario-to-oracle binding remain necessary before changing
specialist readiness or broad acceptance. Package 1 evidence does not authorize
internet release, production use, deployment, or a commit.

## SESSION_HANDOFF

1. Work only in `D:\RC_ATLAS_W2_METHOD_CORE_20261024` on
   `remediation/wave-2-methodological-core`; verify HEAD remains
   `2ec64f7b100c317daed4061efe46b896a38e2888` and review all uncommitted files.
   Preserve the Wave 1 worktree, original protected checkout and recovery artifacts.
2. Read this report and `docs/WAVE_2_PACKAGE_1_CONTRACT.md`, then the nine hashed
   specialist authorities. Preserve the approved intent; do not infer thresholds
   or mark audit scenarios PASS from this report alone.
3. New routes are wired from the main application. The pure engine is
   `services/methodology.py`; PostgreSQL remains the single canonical store.
   No SQL migration or live configuration action is pending for this extension.
4. Reproduce only in disposable synthetic runtimes. Set
   `RCATLAS_PG_TEST_BIN=D:\RC_ATLAS_PG_VALIDATION_20261022_66feba61\postgres\pgsql\bin`
   and `RCATLAS_PG_TEST_ROOT=D:\RC_ATLAS_W2_VALIDATION_20261024`; invoke
   `D:\RC_ATLAS_PG_VALIDATION_20261022_66feba61\venv\Scripts\python.exe`
   with `methodology_regression.py --suite focused --evidence <new-evidence-dir>`
   or `--suite all`. Each run makes a fresh runtime and refuses skipped tests as success.
5. Browser/process reproduction uses `methodology_runtime_acceptance.py --evidence
   <new-evidence-dir>`, plus
   `PLAYWRIGHT_CORE_PATH=D:\RC_ATLAS_PG_VALIDATION_20261022_66feba61\browser-tools\node_modules\playwright-core`
   and `RCATLAS_CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe`.
   It starts/stops its own API and PostgreSQL processes, uses installed Chrome,
   and retains synthetic runtime evidence outside the repository. Never reuse
   a canonical workspace or live provider to reproduce acceptance.
6. Review the final source manifest and evidence before further changes. Keep
   `PLANNING_LOG.md` append-only. No commit, push, merge, rebase or deployment is
   authorized. The next package requires its own controlled scope; the internet
   release remains NO-GO.

Final accepted evidence directories: `focused-release`, `full-release` and
`runtime-refresh`. Earlier `*-initial`, `*-final`, `*-accepted` and diagnostic
directories are historical runs; they do not supersede these final runs.
