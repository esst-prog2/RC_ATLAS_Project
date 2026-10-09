## Why

RC Atlas has broad API, Studio, persistence, analytics, reporting, integration, localization, and tenant-security surfaces, but no single audit contract that records complete coverage or coordinates specialist evidence. A system-wide QA framework is needed before a full audit can run safely and reproducibly against isolated data.

## What Changes

- Add a QA governance area with a versioned audit manifest, isolation and evidence protocols, and a full-system coverage matrix.
- Define scenario catalogs for functional, integration, data and analytics, UI/UX, security and access, and reliability specialists.
- Define a QA Lead coordination protocol for actual Codex subagents when available and sequential role execution when they are not.
- Require independent expected results, immutable baseline SHAs, isolated runtimes, reproducible evidence, explicit untested coverage, and fail-safe stop conditions.
- Standardize scenario outcomes as `PASS`, `FAIL`, `BLOCKED`, `NOT_TESTED`, or `INCONCLUSIVE` and finding severities as `P0` through `P3`.
- Record the known empty-workspace login-audit bootstrap defect as pre-existing audit context rather than a newly discovered result.
- Register owner-approved oracle decisions separately from repository-derived oracles while preserving all unresolved scenarios.
- Require source-only specialists to operate from a verified committed-tree snapshot and never receive the original checkout path.
- Define machine-readable execution, result, finding, hypothesis, and reconciliation contracts controlled by the QA Lead.
- Keep this phase limited to governance and orchestration artifacts; it does not run the audit, add CI or dependencies, change product behavior, or contact live providers.

## Capabilities

### New Capabilities

- `system-wide-qa-audit`: Defines complete audit planning, specialist coordination, isolation, evidence, status, finding, reconciliation, and coverage-retention requirements for RC Atlas.

### Modified Capabilities

None.

## Impact

- Adds files under `qa/`, one Codex skill under `.agents/skills/rc-atlas-qa-audit/`, and one active OpenSpec change.
- Extends `AGENTS.md`, `docs/DEVELOPMENT.md`, and the append-only planning log with QA governance guidance.
- Does not change application source, production tests, runtime persistence, external-provider configuration, or existing OpenSpec capabilities.
