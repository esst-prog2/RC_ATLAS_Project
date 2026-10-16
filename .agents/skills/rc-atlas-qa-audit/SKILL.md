---
name: rc-atlas-qa-audit
description: Coordinate a complete RC Atlas system-wide QA audit with specialist ownership, isolated runtimes, reproducible evidence, and honest Codex subagent orchestration.
---

# RC Atlas QA Audit

Use this skill only when the user explicitly authorizes audit planning or execution. Phase authorization is strict: creating governance does not authorize tests, browser work, runtime creation, provider calls, fixes, commits, or publication.

## Required Inputs

Read these files before acting:

- `qa/audit_manifest.yaml`
- `qa/matrices/full_system_coverage.md`
- `qa/protocols/isolation.md`
- `qa/protocols/source_snapshot.md`
- `qa/protocols/evidence.md`
- `qa/oracle_readiness.yaml`
- all `qa/scenarios/*.yaml` catalogs in the authorized scope
- `.agents/skills/rc-atlas-qa-audit/references/roles.md`
- repository `AGENTS.md` and relevant active OpenSpec changes

## Lead Startup

1. Confirm repository root, branch, clean/expected status, protected files, and exact full baseline SHA.
2. Assign a unique audit ID. Never reuse an ID for a different baseline or scope.
3. Record the authorized phases and prohibited actions.
4. Validate that every coverage row maps to at least one scenario and every scenario has a primary owner.
5. Resolve each independent oracle before execution. Keep unresolved items `BLOCKED` or `NOT_TESTED`.
6. Register known issues, including `KNOWN-BOOTSTRAP-001`, before receiving specialist results.
7. For source inspection, require a verified committed-tree snapshot and execution plan. Never hand an agent the original checkout path.
8. Prove separately authorized stateful isolation before starting any process or browser interaction.

## Actual Subagent Orchestration

Inspect the tools available in the current Codex session. Actual delegation is supported only when subagent lifecycle tools equivalent to `spawn_agent`, `send_input`, `wait_agent`, and `close_agent` are callable.

When lifecycle tools are available and the user authorized multi-agent execution:

1. Keep baseline verification, safety decisions, coverage accounting, and reconciliation with the QA Lead.
2. Spawn specialists only for concrete, independent assignments. Give each agent the audit ID, full baseline SHA, verified snapshot path, role brief, scenario IDs, read/write scope, runtime ID, prohibited actions, expected output schema, and stop conditions. Never include the original checkout path.
3. Source specialists work only inside the verified snapshot. Use separate runtimes and disjoint write/evidence paths for parallel stateful agents.
4. Do useful lead work while agents run. Do not duplicate their assignment.
5. Use `send_input` for corrections or bounded follow-up. Use `wait_agent` only when the result is needed for the next step.
6. Review every result against the evidence protocol. Request missing evidence before accepting a status.
7. Close completed agents so they do not occupy concurrency capacity. Preserve their report and agent ID in the audit record.

Never claim subagents ran merely because this skill names roles. If lifecycle tools are missing, unavailable, or unauthorized, set `execution_mode: sequential_roles` and execute each role brief serially with explicit handoffs.

## Browser Serialization

Browser control is shared state unless the environment proves otherwise. The QA Lead grants one browser lease at a time. The handoff records runtime, port, tab, actor, scenario, and browser storage state. The receiving specialist verifies all six before interacting. Source and API specialists must not manipulate the browser while another lease is active.

## Specialist Handoff Contract

Every assignment message includes:

- audit ID and baseline SHA;
- specialist role and scenario IDs;
- primary and secondary ownership boundaries;
- verification modes authorized;
- isolated runtime and writable evidence path, if any;
- independent oracle sources;
- known issues and duplicate candidates;
- stop conditions and protected resources;
- required scenario/finding report fields.

Every return message includes all assigned scenario IDs, including those not executed, with one controlled status each. It lists findings separately from hypotheses and confirms runtime/protected-resource disposition.

The Lead validates `qa/schemas/audit-execution-plan.schema.json` before delegation. Specialists return records conforming to the scenario, finding, or hypothesis schemas; the Lead alone creates reconciliation records. Lifecycle agent IDs and execution modes come from actual tool calls, not specialist self-description.

## Lead Reconciliation

1. Validate stable IDs, status vocabulary, baseline, runtime, oracle, and evidence completeness.
2. Preserve original specialist reports.
3. Reconcile duplicate and conflicting findings in a separate record with rationale.
4. Never convert a blocked, untested, or inconclusive record into pass.
5. Account for every coverage row and scenario before producing totals.
6. Stop the affected audit work on any isolation, integrity, credential, or unexpected external-side-effect condition.

## Boundaries

- Do not fix defects during an audit unless a later request explicitly authorizes a correction phase.
- Do not touch canonical runtime data, projections, backups, `Site.txt`, credentials, or live providers.
- Do not weaken existing tests or infer expectations from current output.
- Do not archive OpenSpec changes, stage, commit, push, or open PRs unless explicitly authorized in a separate phase.
- Do not run source specialists from the original checkout. A clean snapshot is required but is not a complete OS security sandbox.
