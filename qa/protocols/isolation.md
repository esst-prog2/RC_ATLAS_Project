# Isolation Protocol

## Before Stateful Work

1. Record the audit ID and immutable full baseline SHA.
2. Create a fresh disposable clone, worktree, or repository-supported temporary fixture for exactly one stateful specialist.
3. Resolve and record absolute paths for the clone, canonical snapshot, relational projection, logs, uploads, and generated exports.
4. Prove all writable paths remain inside the disposable root. If any path is ambiguous, stop with `BLOCKED`.
5. Assign a unique localhost port and runtime ID. Confirm the process command and working directory.
6. Remove or override outbound provider configuration in the disposable environment. Never copy production credentials.
7. Record hashes of protected canonical files in the source checkout without mutating them.
8. Seed only through a supported application path and only after isolation is proven. Account for `KNOWN-BOOTSTRAP-001`: do not attempt login before initialization of a fresh demo workspace.

## Agent Boundaries

- Read-only source specialists may share only a QA Lead-verified `git archive` snapshot. They must not receive or search the original checkout path.
- Each specialist that mutates application state receives a separate runtime and data store.
- Specialists must not reuse another agent's cookies, sessions, generated files, ports, or databases.
- Test fixtures may use temporary directories managed by the test process.
- Disposable runtime changes are never copied back to canonical data.
- Prompt restrictions, ignore files, and search-glob exclusions are secondary controls and never replace the snapshot boundary.

Source-only setup and residual host risks are defined in `source_snapshot.md`. A clean archive excludes untracked and rejected tracked paths, but it does not prevent a process from escaping through host filesystem, network, environment, or child-process capabilities. Stateful and browser phases remain unauthorized until those controls are independently proven.

## Browser Lease

The QA Lead grants the shared browser to one specialist at a time. At handoff, record the tab, URL, runtime ID, authenticated actor, and scenario. Logout and verify actor refresh; clear browser state only when the scenario protocol requires it. The next specialist confirms the runtime and actor before interaction.

## External Providers

SMTP, SendGrid, Twilio, Meta/WhatsApp, generic webhooks, and any future provider remain disabled by default. `external_provider` scenarios are `BLOCKED` until the project owner separately authorizes a sandbox, approved recipient or endpoint, credentials handling, and side effects.

## Stop Conditions

Stop the affected work immediately when:

- an application process points to source/canonical runtime data;
- a source canonical hash changes;
- a protected file, credential, or unrelated tenant is accessed unexpectedly;
- a live notification or provider call could occur without authorization;
- data corruption, cross-tenant mutation, or runaway process risks further damage;
- runtime, actor, baseline, or browser ownership cannot be established.

Preserve evidence, terminate only the identified disposable process when safe, and report `BLOCKED` or `INCONCLUSIVE`. Do not improvise repair or rollback against protected data.

## After Stateful Work

Record disposable data mutations, stop owned processes, recheck source hashes and Git status, and state whether the disposable runtime was retained for evidence or safely removed under separate authorization. Never remove an ambiguous path.
