## Context

See `proposal.md` for motivation. RC Atlas combines a large FastAPI/domain module, modular API and service layers, a monolithic Studio client, canonical JSON or SQLite snapshot persistence, a derived relational projection, external notification adapters, and four canonical OpenSpec capabilities. Existing unittest coverage is strong around backend workflows, tenant isolation, persistence, and static Studio contracts, but there is no common audit manifest, complete coverage ledger, evidence schema, or specialist handoff protocol.

The Codex environment can expose real subagent lifecycle tools, but availability is session-specific. Browser control uses shared state and therefore cannot be treated as safely parallel by default.

## Goals / Non-Goals

**Goals:**
- Make the audit plan machine-readable and the evidence contract reviewable.
- Assign all implemented product surfaces to one primary specialist and relevant secondary specialists.
- Support real subagent coordination when available without making it a prerequisite.
- Keep stateful execution isolated from canonical runtime and external providers.
- Preserve missing, blocked, and inconclusive coverage as first-class records.

**Non-Goals:**
- Run the audit, create disposable runtimes, seed data, or exercise a browser in this phase.
- Change product behavior, production tests, dependencies, CI, or provider configuration.
- Replace OpenSpec, application authorization, or existing test suites.
- Promise autonomous behavior from documentation alone.

## Decisions

### 1. Use one lead-owned manifest and immutable scenario catalogs

`qa/audit_manifest.yaml` is the per-audit control plane. It records audit identity, baseline, runtime assignments, role status, known issues, and artifact locations. Domain catalogs under `qa/scenarios/` define stable scenario IDs and independent oracles; execution results are future audit artifacts rather than edits to expected values.

Alternative considered: free-form specialist reports. Rejected because omissions, status drift, and duplicate IDs would be difficult to detect.

### 2. Assign primary ownership and allow explicit secondary review

Each coverage area and scenario has exactly one primary specialist. Cross-cutting areas list secondary specialists. The QA Lead owns assignment, boundary questions, conflict reconciliation, and final coverage accounting but does not silently rewrite specialist evidence.

Alternative considered: allow every specialist to test every area. Rejected because it encourages duplicated work and unclear accountability.

### 3. Separate verification modes

Scenarios declare one or more of `source_inspection`, `automated_test`, `real_browser`, and `external_provider`. Passing one mode does not imply that another passed. Provider verification remains blocked until a safe sandbox and explicit authorization exist.

Alternative considered: a single pass/fail per feature. Rejected because static, API, rendered-browser, and live-provider behavior have different evidence strength and risk.

### 4. Isolate by agent and serialize the browser

Stateful specialists receive separate disposable clones or equivalent verified runtime roots, dedicated data and projection files, unique ports, and disabled outbound providers. Read-only source agents may share the repository. Shared browser control is leased by the QA Lead to one specialist at a time, with actor and runtime reset checks at handoff.

Alternative considered: one shared seeded runtime for all specialists. Rejected because state contamination makes failures hard to reproduce and increases protected-data risk.

### 5. Keep orchestration capability honest

The Codex skill instructs the lead to inspect available tools. If spawn/send/wait/close lifecycle tools exist, the lead may create real specialist subagents and must provide explicit handoffs. Otherwise, the lead runs the same role briefs sequentially and records `execution_mode: sequential_roles`. Instructions alone never constitute proof that agents ran.

Alternative considered: require subagents. Rejected because tool availability varies by environment.

### 6. Treat safety stops as audit outcomes

Isolation ambiguity, protected-resource access, canonical hash drift, unexpected provider calls, data corruption, or credential exposure stop the affected work immediately. The result remains visible as `BLOCKED` or `INCONCLUSIVE`, and only the QA Lead decides whether independent unaffected work may continue.

### 7. Register the bootstrap issue before execution

The empty-workspace login-audit/demo-seed defect is listed in the manifest as a known issue with provenance. Specialists may test it only under an approved isolated scenario and must distinguish confirmation from novel scope or impact.

### 8. Use committed-tree snapshots for source specialists

The QA Lead creates source-only workspaces from a verified baseline with `git archive`. The tooling rejects protected tracked names, untracked content is absent by construction, the destination must be outside the original checkout, and agents receive only the snapshot path. Prompt restrictions and search globs remain defense in depth rather than the primary content boundary.

A snapshot is not an OS security sandbox. Processes may still traverse the host filesystem, inherit environment variables, reach networks, or launch child processes. Stateful, browser, and provider work therefore remain separately authorized and require stronger runtime and process controls.

### 9. Separate owner-approved and repository-derived oracles

The readiness register classifies all scenarios as `APPROVED_EXISTING`, `APPROVED_OWNER`, or `UNDEFINED`. Owner decisions use stable IDs and dates. Undefined scenarios remain visible and non-executable; observed program output cannot promote them.

### 10. Make execution metadata Lead-controlled and machine-readable

JSON schemas define source-only execution plans, scenario results, confirmed findings, hypotheses, and reconciliation. The QA Lead owns audit identity, baseline, actual lifecycle agent IDs, process and port allocation, runtime identity, and reconciliation. Specialist self-description cannot override lifecycle evidence.

## Risks / Trade-offs

- [Large scenario inventory becomes stale] -> Require stable IDs, named owners, source references, and coverage reconciliation before each audit.
- [Parallel specialists contaminate shared state] -> Use per-agent runtimes and serialize all shared-browser access.
- [Static checks overstate usability] -> Track verification modes separately and require real-browser evidence for rendered interaction claims.
- [Provider checks cause external effects] -> Default provider scenarios to blocked until sandbox credentials and explicit authorization are present.
- [Subagent outputs conflict or omit context] -> Use a fixed report contract and lead reconciliation log.
- [YAML remains syntactically valid but semantically incomplete] -> Validate required keys and scenario/coverage IDs before the first real audit.
- [A source process escapes its clean snapshot] -> Document residual host risk and require stronger OS-level controls before stateful or externally connected work.

## Migration Plan

1. Land the governance, scenario, skill, and OpenSpec artifacts without running an audit.
2. Review scenario ownership and oracle completeness with the project owner.
3. Complete stateful-runtime verification tooling in a separately authorized phase; source-only snapshot and schema validation are provided by Phase 2C.
4. Freeze an audit baseline SHA, instantiate a manifest, and execute source and automated phases.
5. Run serialized browser and explicitly authorized provider phases, then reconcile and publish the audit report.

Rollback consists of removing only the new QA framework artifacts before adoption; no product or runtime migration is involved.
