# RC Atlas System-Wide QA

This directory defines governance for coordinated audits of every implemented RC Atlas surface. It is not evidence that an audit has run. Product code, canonical runtime data, live providers, and protected local files remain outside this framework.

## Team

| Role | Primary ownership |
| --- | --- |
| QA Lead Engineer | Baseline, assignments, safety, browser lease, reconciliation, final coverage |
| Functional QA Agent | User workflows and business-state outcomes |
| Integration QA Agent | API contracts, module boundaries, notifications, imports/exports, providers |
| Data & Analytics QA Agent | Dataset quality, indicators, KPIs, dashboards, reports, analytical correctness |
| UI/UX QA Agent | Rendered Studio behavior, accessibility, responsive layout, localization, usability |
| Security & Access QA Agent | Authentication, authorization, tenant/project isolation, secret and data exposure |
| Reliability QA Agent | Persistence, projection, migration, recovery, concurrency, failure behavior |

Each scenario has one primary owner. Secondary reviewers can add evidence but cannot silently replace the primary result.

## Audit Lifecycle

1. The QA Lead copies or instantiates `audit_manifest.yaml`, assigns a unique audit ID, and freezes a full baseline commit SHA that contains the QA framework.
2. The Lead maps every row in `matrices/full_system_coverage.md` to scenario IDs. Missing execution remains visible as `NOT_TESTED` or `BLOCKED`.
3. The Lead resolves oracle classes through `oracle_readiness.yaml`. Current output is never used to manufacture an expectation.
4. Source inspection runs only in a verified committed-tree snapshot under `protocols/source_snapshot.md`. Automated and stateful work uses separately authorized per-agent isolated runtimes under `protocols/isolation.md`.
5. Real-browser work is serialized through a Lead-issued browser lease. External-provider checks require a sandbox and separate authorization.
6. Specialists report under `protocols/evidence.md`. The Lead reconciles duplicates and conflicts while preserving original evidence.
7. The Lead publishes coverage totals for all statuses and a finding register separating confirmed bugs from hypotheses.

## Verification Modes

- `source_inspection`: read-only implementation, configuration, and specification review.
- `automated_test`: repeatable test command against isolated state.
- `real_browser`: rendered interaction in a supported browser against isolated state.
- `external_provider`: authorized sandbox verification of a real third-party boundary.

A result in one mode does not imply a result in another.

## Controlled Vocabularies

Scenario status is exactly one of `PASS`, `FAIL`, `BLOCKED`, `NOT_TESTED`, or `INCONCLUSIVE`.

Finding severity is exactly one of:

- `P0`: active catastrophic data loss, broad compromise, or system-wide outage requiring immediate stop.
- `P1`: critical workflow/security/reliability failure with no acceptable workaround.
- `P2`: material defect with bounded impact or a practical workaround.
- `P3`: low-impact defect, polish issue, or maintainability risk with user-visible consequences.

Use `hypothesis` instead of a severity when evidence does not yet establish a confirmed product defect.

## Orchestration

Use `.agents/skills/rc-atlas-qa-audit/SKILL.md`. Actual Codex subagents are used only when lifecycle tools are available. Otherwise the QA Lead executes the role briefs sequentially and records that mode. Written role instructions alone never prove autonomous execution.

The QA Lead owns execution metadata and validates plans and reports against `schemas/`. Source specialists receive only a verified snapshot path, never the original checkout path. The snapshot is created from committed objects with `tools/New-SourceAuditSnapshot.ps1`; prompt restrictions and search exclusions are supplementary controls, not the isolation boundary.

## Oracle Readiness

`oracle_readiness.yaml` accounts for all 68 scenarios. As of 2026-10-09, 38 are `APPROVED_EXISTING`, six are `APPROVED_OWNER`, and 24 remain `UNDEFINED`. Undefined scenarios are retained but cannot execute until their independent expected behavior is approved.

The six owner decisions are QA-001 through QA-006. They cover notification acknowledgement, provider-failure containment, reproducible analytics, WCAG 2.2 AA as an evaluation target, four responsive viewports, and project-form feedback and persistence.

## Pilot Status

`RCATLAS-QA-PILOT-20261009-001` proved that actual Codex subagent lifecycle calls can coordinate source review in a capable session. Its product observations are preliminary where runtime evidence is required. One malformed search reached protected backup files in the original checkout, so the pilot also proved that prompt-only and glob-only controls are inadequate. No later source audit may resume from the original checkout.

The known empty-workspace bootstrap issue is pre-registered in the manifest: failed login attempts can create audit events that prevent demo seeding. Reproduction confirms an existing issue unless materially new scope or impact is established.
