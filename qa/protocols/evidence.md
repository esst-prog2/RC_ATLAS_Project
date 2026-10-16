# Evidence Protocol

## Scenario Record

Machine-readable scenario records must validate against `qa/schemas/scenario-result.schema.json`.

Every executed or unexecuted scenario record must contain:

- audit ID, scenario ID, specialist owner, baseline SHA, timestamp, and verification mode;
- runtime ID and isolated data path for stateful work;
- actor, organization, project, and relevant starting state using fictional or redacted identifiers;
- independent oracle and its source, fixed before execution;
- exact input/actions and reproducible command or browser procedure;
- expected and actual outcomes;
- one controlled status and any side effects;
- evidence references such as redacted output, response, log excerpt, screenshot, or data hash;
- protected-resource and cleanup confirmation.

For `BLOCKED`, record the blocker and unmet prerequisite. For `NOT_TESTED`, record why execution was intentionally omitted. For `INCONCLUSIVE`, record the ambiguity and what evidence would resolve it.

## Finding Record

Confirmed findings must validate against `qa/schemas/finding.schema.json`; observations lacking reproduction or causality use `qa/schemas/hypothesis.schema.json` instead.

A confirmed finding requires:

- unique finding ID and owning specialist;
- severity `P0`, `P1`, `P2`, or `P3` with impact rationale;
- affected module, route/view, baseline SHA, runtime, actor, and preconditions;
- minimal repeatable steps;
- independently defined expected behavior and observed behavior;
- evidence references and reproduction count;
- scope, tenant/data impact, workaround, and confidence;
- related scenario IDs, known-issue IDs, and possible duplicates.

If reproduction or causality is insufficient, label the observation `hypothesis`; do not assign confirmed-bug severity.

## Evidence Handling

- Redact passwords, tokens, session cookies, hashes, provider secrets, real personal data, and unnecessary payload content.
- Prefer stable IDs and minimal routing metadata over full records.
- Do not paste entire runtime databases or canonical snapshots into reports.
- Record commands and exit codes. Summaries without reproducible inputs are insufficient for a confirmed failure.
- For UI findings, capture viewport, browser, actor, visible state, and network/backend response when relevant.
- For analytics findings, retain source fixture, formula/oracle, rounding rules, filters, and expected aggregate.
- For persistence findings, retain before/after hashes and identify canonical versus derived state.

## Reconciliation

The QA Lead groups possible duplicates but preserves each original report. A reconciliation record lists all source IDs, explains whether they are duplicate, related, conflicting, or independent, and names the canonical finding if merged. Conflicts stay open until baseline, runtime, oracle, and evidence differences are resolved.

Reconciliation records validate against `qa/schemas/reconciliation.schema.json`. Only the QA Lead may issue or alter execution identity, baseline, agent assignment, or reconciliation metadata. A specialist self-report that conflicts with lifecycle records is preserved as evidence but does not override Lead-controlled metadata.

The Phase 2B pilot observations remain preliminary unless their declared verification mode is sufficient for the claim. Source evidence may establish a deterministic source-level defect, but behavior requiring process, persistence, browser, or provider evidence remains a hypothesis until safely reproduced.

No result may be deleted because it is inconvenient, untested, blocked, or contradicted by another specialist.
