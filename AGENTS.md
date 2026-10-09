## Planning log

Whenever we decide something about this project — a requirement,
a number, a name, a tool — append one line to PLANNING_LOG.md:
the date, what was decided, and whether I decided it or you did.
Never rewrite an earlier line.

## System-wide QA audits

Use `qa/README.md`, `qa/audit_manifest.yaml`, and the protocols under
`qa/protocols/` for authorized RC Atlas audits. Preserve every coverage record,
including blocked and untested features. Stateful work requires an independently
verified disposable runtime; never use canonical runtime JSON, SQLite data,
backups, `Site.txt`, credentials, or live providers.

Source-only QA agents must work from a QA Lead-verified committed-tree snapshot
created under `qa/protocols/source_snapshot.md`. Never give a specialist the
original checkout path. Prompt restrictions and search exclusions are not the
primary isolation boundary, and a clean snapshot is not a complete OS sandbox.

When a user explicitly authorizes multi-agent audit execution, use the
`rc-atlas-qa-audit` skill. Claim actual subagent delegation only when Codex
subagent lifecycle tools were called. Otherwise record sequential role-based
execution. Shared browser access must be serialized by the QA Lead.
