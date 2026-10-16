# Source-Only Snapshot Protocol

## Primary Boundary

Source-only specialists must work from a clean archive of one verified committed Git tree. The QA Lead creates that snapshot with `qa/tools/New-SourceAuditSnapshot.ps1`, verifies its metadata, and gives specialists only the snapshot path. The original checkout path must not appear in a specialist handoff, command, working directory, search root, or evidence reference.

`git archive` is the primary content boundary because it includes committed tree entries only. Prompt instructions, search globs, ignore files, and promises not to open protected files are secondary controls and are not sufficient isolation by themselves.

The snapshot tool rejects a committed tree containing protected runtime names or common local-secret paths. It also refuses an existing destination, a destination inside the source checkout, a non-commit baseline, or a baseline that lacks the QA framework files required for controlled execution.

## Lead-Owned Metadata

The QA Lead owns and validates:

- unique audit ID and immutable 40-character baseline SHA;
- snapshot identity and generated metadata;
- authorized verification mode and scenario IDs;
- specialist role and actual lifecycle agent ID, when available;
- process policy, port allocation, runtime ID, and writable paths;
- result, finding, hypothesis, and reconciliation artifact locations.

Specialists may report observed metadata but must not replace Lead-issued values. A mismatch is `BLOCKED`, never silently corrected.

## Source-Only Restrictions

A source-only plan has no runtime data path, application process, browser lease, provider access, or allocated port. It permits reads only under the verified snapshot root and writes only to a separately declared evidence directory when explicitly authorized. No audit process may resolve relative paths against the original checkout.

Before delegation, the Lead validates the execution plan against `qa/schemas/audit-execution-plan.schema.json` and runs `qa/tools/Test-AuditExecutionPlan.ps1`. Each specialist receives a fresh process context whose working directory is the snapshot root.

## Stateful Guard Design

Later stateful phases require separate authorization and additional verified metadata: a disposable runtime root outside the source checkout, dedicated canonical and projection paths within that root, an owned process ID and exact command, a unique approved localhost port, disabled outbound providers, and before/after integrity evidence. Source snapshots do not authorize stateful execution.

## Residual Risk

A clean Git snapshot is a content boundary, not a complete security sandbox. A process running inside it may still traverse the host filesystem, inherit environment variables, access the network, or launch child processes if the host allows those actions. Stronger phases must add OS-level filesystem and network isolation, process ownership controls, least-privilege environment construction, and explicit browser/runtime leases. Until those controls are proven, the framework authorizes source inspection only.

## Pilot Safety Incident

During `RCATLAS-QA-PILOT-20261009-001`, a malformed source search reached protected local backup files in the original checkout. No mutation or secret disclosure was reported, but the access violated the audit boundary. The pilot's product observations remain preliminary where runtime reproduction is required. Future source agents must use verified committed snapshots and never receive the original checkout path.
