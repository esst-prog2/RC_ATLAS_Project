import argparse
import http.cookiejar
import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


PASSWORD = "SyntheticRestartPassword!123"


def load_module():
    spec = importlib.util.spec_from_file_location("rcatlas_restart_fixture", "LogiTrackRC v4.4.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_fixture(module):
    data = module.LogiTrackData()
    for organization_id, name in (
        ("org_restart_a", "Restart Tenant A"),
        ("org_restart_b", "Restart Tenant B"),
    ):
        data.organizations.append(module.OrganizationAccount(
            id=organization_id,
            organization_name=name,
            status="active",
            subscription_plan="synthetic",
            created_at=module.now_iso_utc(),
        ))
    for user_id, organization_id, username in (
        ("user_restart_a", "org_restart_a", "restart.admin.a"),
        ("user_restart_b", "org_restart_b", "restart.admin.b"),
    ):
        data.users.append(module.build_user_account_from_payload({
            "id": user_id,
            "organization_id": organization_id,
            "username": username,
            "email": f"{username}@example.test",
            "full_name": f"Synthetic {username}",
            "role": "organization_admin",
            "status": "active",
            "is_active": True,
            "password": PASSWORD,
        }))
    module.save_data_to_path(data)


class BrowserSession:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def cookie(self, name):
        return next((item.value for item in self.jar if item.name == name), "")

    def request(self, method, path, payload=None, headers=None, expected=200):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request_headers = {"Accept": "application/json", **(headers or {})}
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        if method in {"POST", "PUT", "PATCH", "DELETE"} and self.cookie("rcatlas_csrf_dev"):
            request_headers.setdefault("X-CSRF-Token", self.cookie("rcatlas_csrf_dev"))
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            with self.opener.open(request, timeout=15) as response:
                raw = response.read().decode("utf-8")
                status = response.status
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            status = exc.code
        parsed = json.loads(raw) if raw else {}
        if status != expected:
            raise AssertionError(f"{method} {path}: expected {expected}, received {status}: {parsed}")
        return parsed


def start_server(port, environment, workdir):
    command = (
        "import importlib.util,uvicorn; "
        "s=importlib.util.spec_from_file_location('rcatlas_runtime',r'LogiTrackRC v4.4.py'); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        f"uvicorn.run(m.app,host='127.0.0.1',port={port},log_level='warning')"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", command],
        cwd=workdir,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    health = BrowserSession(f"http://127.0.0.1:{port}")
    for _ in range(80):
        if process.poll() is not None:
            raise RuntimeError("Disposable server exited before readiness.")
        try:
            health.request("GET", "/health")
            return process
        except Exception:
            time.sleep(0.25)
    process.terminate()
    raise RuntimeError("Disposable server did not become ready.")


def stop_server(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_acceptance(workdir, runtime_dir, port):
    runtime_dir.mkdir(parents=True, exist_ok=False)
    db_path = runtime_dir / "restart.sqlite3"
    evidence_path = runtime_dir / "restart-session-results.json"
    base_url = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    environment.update({
        "LOGITRACK_STORAGE_BACKEND": "sqlite",
        "LOGITRACK_SQLITE_PATH": str(db_path),
        "LOGITRACK_ENABLE_RELATIONAL_MIRROR": "false",
        "LOGITRACK_ENABLE_REPOSITORY_DOMAINS": "false",
        "LOGITRACK_ENVIRONMENT": "development",
        "LOGITRACK_SESSION_COOKIE_SECURE": "false",
        "LOGITRACK_API_ALLOW_ORIGINS": base_url,
        "LOGITRACK_PUBLIC_ORIGIN": base_url,
        "LOGITRACK_SETUP_ENABLED": "false",
    })
    os.environ.update({key: value for key, value in environment.items() if key.startswith("LOGITRACK_")})
    module = load_module()
    seed_fixture(module)

    process = None
    try:
        process = start_server(port, environment, workdir)
        tenant_a = BrowserSession(base_url)
        login = tenant_a.request("POST", "/v1/auth/login", {
            "username": "restart.admin.a",
            "password": PASSWORD,
        })
        if "token" in login:
            raise AssertionError("Browser login exposed a bearer token.")
        copied_cookie = tenant_a.cookie("rcatlas_session_dev")
        if not copied_cookie or not tenant_a.cookie("rcatlas_csrf_dev"):
            raise AssertionError("Browser session cookies were not established.")
        initial = tenant_a.request("GET", "/v1/admin/projects")
        project_payload = {
            "project_name": "Cookie Restart Persistence Project",
            "programme": "Synthetic Programme",
            "donor": "Synthetic Donor",
            "implementing_partner": "Synthetic Partner",
            "sector": "Education",
            "description": "Disposable cookie restart fixture.",
            "country": "Testland",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        }
        created = tenant_a.request(
            "POST",
            "/v1/admin/projects",
            project_payload,
            headers={
                "X-Idempotency-Key": "cookie-restart-project-001",
                "X-Workspace-Version": str(initial["workspace_version"]),
            },
        )
        project_id = created["project"]["id"]
        stop_server(process)
        process = start_server(port, environment, workdir)

        identity = tenant_a.request("GET", "/v1/auth/me")
        after = tenant_a.request("GET", "/v1/admin/projects")
        if identity["user"]["username"] != "restart.admin.a":
            raise AssertionError("Session identity changed after restart.")
        if [item["id"] for item in after["items"]] != [project_id]:
            raise AssertionError("Project state did not survive restart.")
        tenant_b = BrowserSession(base_url)
        tenant_b.request("POST", "/v1/auth/login", {
            "username": "restart.admin.b",
            "password": PASSWORD,
        })
        foreign = tenant_b.request("GET", "/v1/admin/projects")
        if any(item["id"] == project_id for item in foreign["items"]):
            raise AssertionError("Tenant B could read Tenant A project.")
        tenant_a.request("POST", "/v1/auth/logout")
        stop_server(process)
        process = start_server(port, environment, workdir)

        replay = BrowserSession(base_url)
        replay.request(
            "GET",
            "/v1/auth/me",
            headers={"Cookie": f"rcatlas_session_dev={copied_cookie}"},
            expected=401,
        )
        result = {
            "status": "PASS",
            "synthetic_only": True,
            "backend": "sqlite",
            "session_survived_restart": True,
            "project_survived_restart": True,
            "tenant_isolation_after_restart": True,
            "revocation_survived_second_restart": True,
            "revoked_cookie_status": 401,
            "workspace_version": after["workspace_version"],
            "project_id": project_id,
            "secrets_written_to_evidence": False,
        }
        evidence_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result, evidence_path
    finally:
        stop_server(process)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--port", type=int, default=8877)
    args = parser.parse_args()
    workdir = Path(__file__).resolve().parent
    result, evidence_path = run_acceptance(workdir, Path(args.runtime_dir), args.port)
    print(json.dumps({**result, "evidence": str(evidence_path)}))


if __name__ == "__main__":
    main()
