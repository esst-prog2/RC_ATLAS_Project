## Purpose

Define a reproducible, isolated, and complete system-wide QA audit contract for every implemented RC Atlas product surface and specialist team.

## ADDED Requirements

### Requirement: Source inspection uses a verified committed snapshot
The QA framework SHALL require every source-only specialist to work inside a QA Lead-verified archive of one committed baseline, SHALL exclude untracked and protected runtime paths, and SHALL prohibit original-checkout paths from specialist handoffs.

#### Scenario: Lead prepares a source-only assignment
- **WHEN** the QA Lead schedules source inspection
- **THEN** the Lead verifies the baseline, snapshot metadata, prohibited-path scan, execution plan, and specialist working root before delegation

#### Scenario: Snapshot controls are insufficient for stateful work
- **WHEN** an audit requires a process, runtime, browser, network, or provider
- **THEN** the clean snapshot alone does not authorize execution and the scenario remains blocked until the stronger phase-specific isolation is proven

### Requirement: Oracle readiness is explicit and complete
The QA framework SHALL classify every scenario as `APPROVED_EXISTING`, `APPROVED_OWNER`, or `UNDEFINED`, SHALL cite owner decision IDs for owner-approved expectations, and SHALL keep undefined scenarios non-executable and visible.

#### Scenario: Owner approves selected proposals
- **WHEN** the owner approves QA-001 through QA-006
- **THEN** only their six mapped scenarios become `APPROVED_OWNER` and every unrelated undefined oracle remains unchanged

### Requirement: Audit evidence uses Lead-controlled schemas
The QA framework SHALL define machine-readable contracts for execution plans, scenario results, confirmed findings, hypotheses, and reconciliation, with audit identity and lifecycle metadata controlled by the QA Lead.

#### Scenario: Specialist metadata conflicts with lifecycle evidence
- **WHEN** a specialist self-report conflicts with the Lead's verified baseline, execution mode, or agent ID
- **THEN** the report is retained but cannot override Lead-controlled metadata and requires reconciliation

### Requirement: Every audit has an immutable identity and baseline
The QA framework SHALL require a unique audit ID, an immutable full Git commit SHA, named specialist ownership, and an isolated runtime assignment before any stateful audit action begins.

#### Scenario: Lead opens an audit
- **WHEN** the QA Lead initializes an audit manifest
- **THEN** the manifest records a unique audit ID, full baseline commit SHA, scope, owners, runtime assignments, and protected-resource rules before scenarios can enter execution

### Requirement: Coverage includes every implemented product surface
The QA framework SHALL inventory RC Atlas modules, APIs, user workflows, persistence, datasets, analytics, dashboards, reports, administration, integrations, localization, access control, usability, and reliability, including features that are not executed.

#### Scenario: A feature cannot be exercised
- **WHEN** an implemented feature lacks credentials, a provider sandbox, data, or a safe execution path
- **THEN** its coverage record remains present with `BLOCKED` or `NOT_TESTED`, an owner, and a reason rather than disappearing from the audit

### Requirement: Every scenario has an independent oracle
Each scenario SHALL define its expected result independently of observed program output, or SHALL remain non-executable until an explicit oracle-definition requirement is resolved.

#### Scenario: Oracle is not yet approved
- **WHEN** a scenario has no independent expected result or authoritative reference
- **THEN** the specialist records `BLOCKED` or `NOT_TESTED` and does not infer an expectation from current behavior

### Requirement: Results and findings use controlled vocabularies
Scenario results SHALL use only `PASS`, `FAIL`, `BLOCKED`, `NOT_TESTED`, or `INCONCLUSIVE`. Confirmed findings SHALL use severity `P0`, `P1`, `P2`, or `P3`, while unconfirmed observations SHALL be labeled hypotheses.

#### Scenario: Evidence cannot establish causality
- **WHEN** observed behavior cannot be reproduced or attributed to RC Atlas with sufficient evidence
- **THEN** the result is `INCONCLUSIVE` and any observation remains a hypothesis rather than a confirmed bug

### Requirement: Evidence is reproducible and privacy safe
Every executed scenario SHALL record actor, scope, input, expected result, actual result, reproduction steps, relevant response or visual evidence, baseline SHA, runtime identity, and side effects while excluding secrets and unnecessary personal data.

#### Scenario: Specialist reports a failure
- **WHEN** a specialist records `FAIL`
- **THEN** the record includes repeatable steps, expected and actual behavior, evidence references, affected component, confidence, and confirmation that protected data was not accessed

### Requirement: Stateful work is isolated and fail safe
Stateful tests SHALL run only in verified disposable runtimes with dedicated canonical and derived persistence, disabled live providers, and before/after protection checks. The audit SHALL stop on unexpected protected-resource access, data-integrity loss, isolation ambiguity, or unsafe external side effects.

#### Scenario: Runtime path is ambiguous
- **WHEN** an agent cannot prove that application writes remain inside its assigned disposable runtime
- **THEN** the agent stops before mutation and reports `BLOCKED`

### Requirement: QA Lead coordinates and reconciles specialists
The QA Lead SHALL assign non-overlapping primary ownership, define shared boundaries, serialize shared browser access, collect specialist reports, and reconcile duplicate or conflicting findings without discarding source evidence.

#### Scenario: Specialists disagree
- **WHEN** two specialists report conflicting outcomes for the same behavior
- **THEN** the QA Lead preserves both records, compares baselines and evidence, reruns only in a safe isolated runtime if needed, and records a reconciliation decision with rationale

### Requirement: Delegation claims match available execution capability
The orchestration record SHALL distinguish actual Codex subagent delegation from sequential role-based execution and SHALL not claim autonomous multi-agent execution when only written role prompts were used.

#### Scenario: Subagent tools are unavailable
- **WHEN** the environment cannot spawn and coordinate Codex subagents
- **THEN** the QA Lead executes specialist roles sequentially, records that limitation, and preserves the same handoff and evidence contract

### Requirement: Known issues are separated from new findings
The framework SHALL register the known defect where failed login attempts in an uninitialized workspace create audit events that can block demo seeding as pre-existing context.

#### Scenario: Bootstrap defect appears during an audit
- **WHEN** the registered bootstrap behavior is reproduced without materially new scope or impact
- **THEN** the result references the existing issue and is not represented as a newly discovered failure
