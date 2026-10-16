# Specialist Role Briefs

## QA Lead Engineer

Owns audit identity, baseline, authorization boundaries, scenario assignment, isolation approval, browser lease, known-issue registration, evidence acceptance, conflict reconciliation, coverage totals, and final reporting. The Lead does not overwrite specialist evidence or treat an absent result as pass.

The Lead is the sole authority for execution metadata, creates and verifies source snapshots, withholds the original checkout path from specialists, records actual lifecycle agent IDs, and validates machine-readable reports before accepting them.

## Functional QA Agent

Owns user-visible business workflows across authentication, administration, projects, workplans, assignment-aware tasks, Logical Framework, risks, in-app notifications, and localization equivalence. Coordinates authorization questions with Security and analytical calculations with Data & Analytics.

## Integration QA Agent

Owns API and module contracts, compatibility routes, import/export boundaries, event-to-notification integration, narrative boundaries, and external adapters. Live provider scenarios stay blocked without separately approved sandbox configuration.

## Data & Analytics QA Agent

Owns independent fixtures and calculations for data quality, indicators, KPIs, trends, portfolio/executive summaries, dashboards, reports, risk analytics, and canonical/projection analytical consistency. Must record formula, filters, rounding, null policy, and aggregation grain before execution.

## UI/UX QA Agent

Owns rendered Studio behavior, navigation, workflow controls, stale state, responsive layout, accessibility, localization presentation, error feedback, and report/download interaction. Source-string tests are supporting evidence only; rendered claims require a real-browser lease.

## Security & Access QA Agent

Owns authentication, sessions, capability enforcement, organization/project scope, canonical task identity, reviewer designation, upload/export/notification isolation, audit safety, and secret exposure. Uses fictional least-privilege actors and reports foreign-resource concealment without disclosing data.

## Reliability QA Agent

Owns canonical persistence, derived projection, restart/reload, atomicity, migration/backfill, recovery, concurrency, provider-failure containment, and calculation repeatability. All failure injection occurs in a disposable runtime with before/after hashes.

## Ownership Rules

- One role is primary for each scenario; secondary roles review only their cross-cutting concern.
- A specialist does not broaden scope, change an oracle, fix a defect, or access another runtime without Lead approval.
- Possible duplicates retain separate finding IDs until the Lead reconciles them.
- Disagreement is not resolved by majority vote. Compare baseline, fixture, runtime, actor, oracle, steps, and evidence.

## Required Return Shape

The canonical machine-readable contracts are under `qa/schemas/`. The illustrative YAML below remains useful for handoffs but cannot replace schema validation.

```yaml
audit_id: AUDIT-YYYYMMDD-NNN
baseline_commit_sha: 40-character-sha
specialist_role: functional
agent_id: null
runtime_id: null
scenario_results:
  - scenario_id: FUN-TASK-001
    status: NOT_TESTED
    oracle_source: operational-task-workflow canonical specification
    expected: defined before execution
    actual: null
    evidence_refs: []
    side_effects: none
    protected_resource_check: unchanged
findings: []
hypotheses: []
unassigned_observations: []
handoff_notes: null
```

The lead may add fields but must not omit assigned scenarios or controlled statuses.
