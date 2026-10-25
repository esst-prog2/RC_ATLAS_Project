# Wave 2 Package 1: frozen implementation contract

Date: 2026-10-24. Baseline: `2ec64f7b100c317daed4061efe46b896a38e2888`.
Authority: approved `METHODOLOGY_DECISION_REGISTER_V1.md` (2026-10-14),
OC-A01–A05, QA-003 and RCQA-011; current owner authorization for Package 1.
This freezes engineering fixtures before implementation; it does not approve
organization-specific rules or change the specialist audit's oracle readiness.

## Storage and authorization

Use the existing canonical aggregate, with one optional `methodology` object on
each indicator (schema version 1, append-only definitions and saved instances).
Inputs come from an explicitly bound, same-tenant existing TidyDataset; no new
observation store, automatic mapping, historical ownership repair or dual writes.
The existing PostgreSQL JSONB document and same-transaction integrity index store
the extension. No SQL DDL change is needed; applied migration files stay immutable.
Validate dataset ownership, definition scope and append-only history at persistence.

Organization administrators with MANAGE_ORGANIZATION may register approved
definitions, recording an external owner decision reference. Registration records
an approval; it does not grant engineering authority to approve methodology.
Missing approval/configuration produces UNCONFIGURED/NOT_ASSESSED. Reads require
both VIEW_INDICATORS and VIEW_REPORTS; source values are numeric and source rows
are represented by hashes, never arbitrary source fields or personal identifiers.
Writes use the existing authorization, CSRF, workspace version and transaction
boundary. Identical definition/instance retries are idempotent by content identity.

## Calculation semantics

Definitions contain explicit scope, unit/currency, direction/scale/domain,
baseline/target, reference period, source field mapping, selection/aggregation,
quality rules, effective date interval, approval and method version. No formula
expressions are evaluated. Approved versions cannot overlap for the same metric
kind (final achievement, schedule attainment, maintenance or qualitative review).

Implement CHANGE_FROM_BASELINE, upward TARGET_RATIO, exact-point TIME_PHASED
without inferred interpolation, inclusive MAINTENANCE_BAND, and
NO_AUTOMATIC_PROGRESS. MILESTONE is recognized but NOT_ASSESSED until its evidence
and weight contract is implemented in a later controlled package. Downward ratio,
unspecified domains, missing targets/schedule and unapproved flags fail explicitly.
Use exact rational arithmetic from decimal inputs; emit numerator/denominator
fractions plus a display value rounded to two decimal places, without caps or bands.
`single` refuses multiple eligible observations; `mean` requires an explicit
aggregation rationale. No portfolio aggregation or unit/currency conversion.

Every calculation requires reporting start/end and timezone-aware as_of. Observation
dates are strict ISO calendar dates. Reporting boundaries are inclusive; observations
after the UTC as_of date are excluded. Effective versions use [from, to) UTC dates.
as_of is an analytical cutoff, not a reconstruction of what was known historically;
the instance preserves the source revision actually used. No hidden clock affects
values or identities. Timestamping a saved instance is separate audit metadata.

VALID/MISSING/INVALID/NOT_APPLICABLE are primary states. PROVISIONAL/IMPUTED remain
flags and are excluded in this package; original state must be retained for imputation.
Zero is valid. N/A is excluded from applicability. Invalid period, unit/currency,
domain, duplicate identity and unapproved flags have separate exclusion reasons.

Quality is a five-dimension profile with explicit declared use, rules, population,
numerators/denominators and exclusions. Missing rules yield NOT_ASSESSED. Zero
population yields NOT_ASSESSED, never 100%. Uniqueness is distinct assessable keys
divided by assessable records, as in OC-A01. No overall score or fitness inference.
OC-A04/05 are guardrails: portfolio aggregation and statistical trend are NOT_ASSESSED.

## Independent methodological oracles

These expected values come from approved fixtures or elementary substitutions,
not observed program output. Synthetic configuration is test-only approval.

| Case | Exact expectation |
| --- | --- |
| OC-A02: B=20, T=100, A=60, upward change | (60-20)/(100-20)=1/2; 50% |
| Same actual, planned target=60 at explicit as_of | 60/60=1; 100% schedule attainment, separately named |
| Downward: B=100, T=20, A=60 | (100-60)/(100-20)=1/2; 50% |
| Upward target ratio A=150, T=100 | 3/2; 150%, uncapped |
| Zero target, or baseline=target | INVALID with zero-denominator reason; null result |
| A=0, T=100 | VALID zero; missing A is MISSING/null |
| OC-A03: 0,5,MISSING,INVALID,N/A | valid mean=5/2; included=2, applicable=4, total=5 |
| OC-A01: 45 populated of 50 applicable cells | completeness=9/10; 90% |
| OC-A01: 7 distinct keys among 8 assessable records | uniqueness=7/8; 87.5% |
| Missing quality rule | NOT_ASSESSED, null fraction and value |
| Inclusive maintenance band [10,20] | 10 and 20 IN_BAND; 9 BELOW_BAND; 21 ABOVE_BAND |
| Inclusive report 2026-09-01 through 2026-09-30 | both endpoints included; 08-31/10-01 excluded |
| Fixed scope/source/method/period/as_of/locale | identical ordered instance and identity |
| Foreign tenant or unauthorized role | denied, no source/definition/instance disclosure |

## Reachability and compatibility

Add an inline explanation panel to the existing Indicator Intelligence view with
explicit period/as_of inputs, localized EN/PT/FR controls and clear unavailable
states. It displays the engine result, formula, coverage, exclusions, quality and
version. Existing analytics retain their response shapes but are explicitly
deprecated as unvalidated legacy analytics; full consumer migration is a later
Wave 2 package. No claim of closing RCQA-011 system-wide is permitted here.

Historical saved instances are immutable and explicitly historical. Recalculation
after source/method/context change has a different identity; it never replaces one.
No exports, dashboard redesign, risk signals, inference or live data are included.

## API and Studio use

All paths below start with `/v1/projects/{project_id}/indicators/{indicator_id}`.

| Operation | Contract |
| --- | --- |
| GET `/methodology` | Authorized definitions, historical instance identifiers and workspace version. |
| POST `/methodology` | Organization administrator; `{definition, expected_workspace_version}`. A previously registered identical version replays without a write. A changed version or overlapping effective period returns 409. |
| GET `/calculation` | Required `start`, `end`, `as_of`; optional `locale` (EN/PT/FR), `methodology_id` and `version`. Missing selection returns UNCONFIGURED; an unknown selected version returns 404. Returns separate `definition` and `result`. |
| POST `/calculation-instances` | Organization administrator; the same calculation arguments plus `expected_workspace_version`. Stores the computed result atomically, with separate audit `saved_at`; identical retries return the existing instance. |
| GET `/calculation-instances/{calculation_id}` | Explicit historical result and its exact definition; current tenant/source authorization remains mandatory. |

Normal browser writes require the existing session cookie and CSRF header. There
is no new authentication mechanism. Existing controlled API-token clients retain
their established transport. GET does not create calculation history (normal
session-touch persistence remains existing application behavior).

The Studio entry point is **MEAL Officer → Indicator Intelligence**. Select an
indicator and registered method, enter reporting dates and an explicit UTC
reference timestamp, then activate **How is this calculated?**. The inline panel
shows a value/state, formula, period, version, coverage, exclusions and limitations;
native details disclose intermediates and the quality profile. EN/PT/FR controls
are localized; organization-authored methodology prose retains its recorded
language. Form changes, errors, project/indicator changes and logout clear results.
This package does not add a methodology-authoring interface or change role menus.

Approved configuration must be registered explicitly; legacy indicators are not
auto-configured. `methodology_fixtures.definition_payload()` documents a complete
fictional example for isolated tests, never an approval for actual indicators.
Use bounded effective intervals when approved future revisions are expected;
closing/withdrawing an existing open-ended version needs a later governed lifecycle
operation, not an in-place edit.

Historical instances preserve authorized numeric inputs, exclusions, exact output,
quality intermediates, source hashes and the definition. They do not copy arbitrary
raw dataset rows or guarantee reconstruction of an overwritten source dataset.
Raw source revision retention and export snapshots remain later controlled work.
