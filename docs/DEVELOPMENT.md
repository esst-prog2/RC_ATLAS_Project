# RC Atlas Development

## Prerequisites

- Python 3 with the `py` launcher available on Windows
- Git for version control

The current code and complete test suite have been exercised with Python 3.14.7.
The direct dependencies are constrained to the tested compatible release lines
in `requirements.txt`; this is not a fully resolved transitive lock file.

## Install Dependencies

From the repository root, create and activate a virtual environment, then install
the declared dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

`fastapi` and `uvicorn` are runtime dependencies. `httpx` is used by FastAPI's
test client during API integration tests. The validated direct versions are
FastAPI 0.141.1, Uvicorn 0.53.0, and HTTPX 0.28.1. Install into a dedicated virtual
environment so unrelated globally installed packages do not affect resolution.

## Start The Application

Run this command from the repository root:

```powershell
py -m uvicorn logitrack_rc_v4_4_api:app --host 127.0.0.1 --port 8000
```

Open the browser application at:

```text
http://127.0.0.1:8000/studio
```

The health endpoint is available at `http://127.0.0.1:8000/health`.

The wrapper `logitrack_rc_v4_4_api.py` loads the active application from
`LogiTrackRC v4.4.py`. Keep both files beside `logitrack_studio.html` when running
the application.

## Run Tests

```powershell
py -m unittest discover -v -p *tests.py
```

## Local Runtime Files

The following files are intentionally ignored and remain local to each machine:

- `.env` and machine-specific `.env.*` files
- Python virtual environments and caches
- `logitrack_data.json` and its backup
- SQLite databases, journals, WAL files, and shared-memory files
- application logs and generated `logitrack_bi_export/` output
- editor and operating-system metadata

Do not place passwords, API keys, access tokens, provider credentials, or real
client data in tracked files. Configure optional providers and API protection
through local environment variables.

The source and tests include clearly marked fictional identities and credentials
for disposable local demonstrations. They must never be reused for production,
real organizations, or external accounts.

## Reproducibility Notes

- Direct dependencies are constrained to their tested compatible release lines;
  a reproducible deployment still needs a separately generated and reviewed
  transitive lock for its target Python and operating system.
- The full test suite was exercised with FastAPI 0.141.1, Uvicorn 0.53.0, and
  HTTPX 0.28.1. This is test evidence, not a production deployment certification.
- Live FastAPI integration tests require every entry in `requirements.txt`.
- Legacy and compatibility source files are preserved for this checkpoint.
- Runtime data is not included. A fresh installation starts with an empty local
  datastore unless it is initialized or seeded through the application.

## System-Wide QA Framework

The governance-only system-wide audit framework lives under `qa/`. Start with
`qa/README.md`, instantiate `qa/audit_manifest.yaml` for one immutable commit,
and use the scenario catalogs and full-system coverage matrix to retain both
tested and untested product surfaces.

Stateful audit execution requires one verified disposable runtime per agent,
dedicated persistence paths and ports, disabled live providers, and source
runtime hashes before and after execution. Real-browser verification is
serialized through the QA Lead. External-provider verification requires a
separately authorized sandbox and is blocked by default.

The Codex coordination instructions are in
`.agents/skills/rc-atlas-qa-audit/SKILL.md`. They use actual subagent lifecycle
tools when those tools are available and authorized; otherwise the same role
briefs run sequentially. Written role files are governance, not proof that
autonomous agents executed.

Source-only specialists use `qa/tools/New-SourceAuditSnapshot.ps1` to plan or
create a committed-tree archive outside the checkout, then validate a Lead-owned
plan with `qa/tools/Test-AuditExecutionPlan.ps1`. Agents receive only the verified
snapshot path. See `qa/protocols/source_snapshot.md` and `qa/schemas/` for the
residual host risks and machine-readable contracts.
