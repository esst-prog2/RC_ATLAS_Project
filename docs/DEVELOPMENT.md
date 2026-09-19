# RC Atlas Development

## Prerequisites

- Python 3 with the `py` launcher available on Windows
- Git for version control

The current code has been inspected with Python 3.14.7. The repository does not
yet define a supported Python version range or pinned dependency versions.

## Install Dependencies

From the repository root, create and activate a virtual environment, then install
the declared dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

`fastapi` and `uvicorn` are runtime dependencies. `httpx` is used by FastAPI's
test client during API integration tests. Versions are currently unpinned because
the active runtime dependencies were not installed in the inspected environment
and the repository contained no previous lockfile or version constraints.

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

- Dependency versions are not yet pinned.
- The inspected Python environment did not contain `fastapi` or `uvicorn`, so the
  web server could not be started during checkpoint preparation.
- Live FastAPI integration tests require every entry in `requirements.txt`.
- Legacy and compatibility source files are preserved for this checkpoint.
- Runtime data is not included. A fresh installation starts with an empty local
  datastore unless it is initialized or seeded through the application.
