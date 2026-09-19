# RC Atlas Studio Demo Startup

The portable installation, startup, and test instructions are maintained in
[`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

Start the browser application from the repository root with:

```powershell
py -m uvicorn logitrack_rc_v4_4_api:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000/studio`.

For a fresh local workspace, use the Studio bootstrap or
`Seed Demo Workspace` control.
Demo credentials are intentionally not published in this document. Optional API,
notification, email, and WhatsApp credentials must be supplied through local
environment configuration and must not be committed.
