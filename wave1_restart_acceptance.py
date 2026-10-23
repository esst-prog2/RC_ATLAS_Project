import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


PASSWORD = "SyntheticRestartPassword!123"
PROJECT_PAYLOAD = {
    "project_name": "Restart Persistence Project",
    "programme": "Synthetic Programme",
    "donor": "Synthetic Donor",
    "implementing_partner": "Synthetic Partner",
    "sector": "Education",
    "description": "Disposable restart acceptance fixture.",
    "country": "Testland",
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
}
FOREIGN_PROJECT_PAYLOAD = {
    **PROJECT_PAYLOAD,
    "project_name": "Foreign Restart Project",
    "project_code": "FOREIGN-RESTART",
}


def fail(message):
    raise AssertionError(message)


def request(base_url, method, path, *, payload=None, token="", headers=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"Accept": "application/json"}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    if token:
        request_headers["X-Auth-Token"] = token
    request_headers.update(headers or {})
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"detail": "non-JSON error response"}
        return exc.code, parsed


def expect_status(actual, expected, label):
    status, body = actual
    if status != expected:
        fail(f"{label}: expected HTTP {expected}, received {status}: {body}")
    return body


def write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2), encoding="utf-8")


def seed_fixture(evidence_path):
    from logical_framework_api_tests import MODULE

    if Path(MODULE.get_sqlite_data_path()).exists():
        fail("Disposable SQLite fixture already exists; refusing to overwrite it.")
    data = MODULE.LogiTrackData()
    for organization_id, name in (
        ("org_restart_a", "Restart Tenant A"),
        ("org_restart_b", "Restart Tenant B"),
    ):
        data.organizations.append(MODULE.OrganizationAccount(
            id=organization_id,
            organization_name=name,
            status="active",
            subscription_plan="synthetic",
            created_at=MODULE.now_iso_utc(),
        ))
    for user_id, organization_id, username in (
        ("user_restart_a", "org_restart_a", "restart.admin.a"),
        ("user_restart_b", "org_restart_b", "restart.admin.b"),
    ):
        data.users.append(MODULE.build_user_account_from_payload({
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
    MODULE.save_data_to_path(data)
    write_json(evidence_path, {
        "phase": "seed",
        "status": "PASS",
        "backend": MODULE.get_storage_backend(),
        "organization_count": len(data.organizations),
        "user_count": len(data.users),
        "workspace_version": data.workspace_version,
        "synthetic_only": True,
    })


def login(base_url, username):
    body = expect_status(request(
        base_url,
        "POST",
        "/v1/auth/login",
        payload={"username": username, "password": PASSWORD},
    ), 200, f"login {username}")
    token = body.get("token", "")
    if not token:
        fail(f"login {username}: response did not contain a token")
    return token


def project_list(base_url, token):
    return expect_status(
        request(base_url, "GET", "/v1/admin/projects", token=token),
        200,
        "project list",
    )


def before_restart(base_url, state_path, evidence_path):
    token_a = login(base_url, "restart.admin.a")
    token_b = login(base_url, "restart.admin.b")
    initial_a = project_list(base_url, token_a)
    key_a = "restart-project-a-001"
    first_a = expect_status(request(
        base_url,
        "POST",
        "/v1/admin/projects",
        token=token_a,
        headers={
            "X-Idempotency-Key": key_a,
            "X-Workspace-Version": str(initial_a["workspace_version"]),
        },
        payload=PROJECT_PAYLOAD,
    ), 200, "tenant A project create")
    before_b = project_list(base_url, token_b)
    first_b = expect_status(request(
        base_url,
        "POST",
        "/v1/admin/projects",
        token=token_b,
        headers={
            "X-Idempotency-Key": "restart-project-b-001",
            "X-Workspace-Version": str(before_b["workspace_version"]),
        },
        payload=FOREIGN_PROJECT_PAYLOAD,
    ), 200, "tenant B project create")
    final_a = project_list(base_url, token_a)
    final_b = project_list(base_url, token_b)
    project_a_id = first_a["project"]["id"]
    project_b_id = first_b["project"]["id"]
    if {item["id"] for item in final_a["items"]} != {project_a_id}:
        fail("tenant A list was not isolated before restart")
    if {item["id"] for item in final_b["items"]} != {project_b_id}:
        fail("tenant B list was not isolated before restart")
    state = {
        "token_a": token_a,
        "token_b": token_b,
        "key_a": key_a,
        "stale_version_a": initial_a["workspace_version"],
        "project_a_id": project_a_id,
        "project_b_id": project_b_id,
        "first_a": first_a,
        "workspace_version": final_b["workspace_version"],
    }
    write_json(state_path, state)
    write_json(evidence_path, {
        "phase": "before_restart",
        "status": "PASS",
        "active_sessions": 2,
        "tenant_a_visible_project_ids": [project_a_id],
        "tenant_b_visible_project_ids": [project_b_id],
        "workspace_version": final_b["workspace_version"],
        "idempotency_key_recorded": True,
        "tokens_redacted": True,
    })


def after_restart(base_url, state_path, evidence_path):
    state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    token_a = state["token_a"]
    token_b = state["token_b"]
    expect_status(request(base_url, "GET", "/v1/auth/me", token=token_a), 200, "tenant A session after restart")
    expect_status(request(base_url, "GET", "/v1/auth/me", token=token_b), 200, "tenant B session after restart")
    list_a = project_list(base_url, token_a)
    list_b = project_list(base_url, token_b)
    if {item["id"] for item in list_a["items"]} != {state["project_a_id"]}:
        fail("tenant A project boundary did not survive restart")
    if {item["id"] for item in list_b["items"]} != {state["project_b_id"]}:
        fail("tenant B project boundary did not survive restart")
    replay = expect_status(request(
        base_url,
        "POST",
        "/v1/admin/projects",
        token=token_a,
        headers={
            "X-Idempotency-Key": state["key_a"],
            "X-Workspace-Version": str(state["stale_version_a"]),
        },
        payload=PROJECT_PAYLOAD,
    ), 200, "idempotent replay after restart")
    if replay != state["first_a"]:
        fail("idempotent replay did not return the original response")
    stale_status, _ = request(
        base_url,
        "POST",
        "/v1/admin/projects",
        token=token_a,
        headers={
            "X-Idempotency-Key": "restart-stale-version-002",
            "X-Workspace-Version": str(state["stale_version_a"]),
        },
        payload={**PROJECT_PAYLOAD, "project_name": "Stale Version Must Fail"},
    )
    if stale_status != 409:
        fail(f"stale workspace version returned {stale_status}, expected 409")
    post_replay = project_list(base_url, token_a)
    if post_replay["count"] != 1:
        fail("idempotent replay or stale write created an extra tenant A project")
    expect_status(request(base_url, "POST", "/v1/auth/logout", token=token_a), 200, "tenant A logout")
    write_json(evidence_path, {
        "phase": "after_restart",
        "status": "PASS",
        "active_session_survived": True,
        "project_data_survived": True,
        "tenant_boundaries_survived": True,
        "idempotent_replay_exact": True,
        "stale_version_status": 409,
        "tenant_a_project_count": post_replay["count"],
        "workspace_version": post_replay["workspace_version"],
        "logout_persisted_for_next_restart": True,
        "tokens_redacted": True,
    })


def after_revocation_restart(base_url, state_path, evidence_path):
    state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    revoked_status, _ = request(base_url, "GET", "/v1/auth/me", token=state["token_a"])
    active_status, _ = request(base_url, "GET", "/v1/auth/me", token=state["token_b"])
    if revoked_status != 401:
        fail(f"revoked session returned {revoked_status}, expected 401")
    if active_status != 200:
        fail(f"unrevoked tenant B session returned {active_status}, expected 200")
    final_a = project_list(base_url, state["token_b"])
    if {item["id"] for item in final_a["items"]} != {state["project_b_id"]}:
        fail("tenant B boundary changed after the second restart")
    write_json(evidence_path, {
        "phase": "after_revocation_restart",
        "status": "PASS",
        "revoked_session_status": revoked_status,
        "unrevoked_session_status": active_status,
        "tenant_boundary_preserved": True,
        "workspace_version": final_a["workspace_version"],
        "tokens_redacted": True,
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("seed", "before-restart", "after-restart", "after-revocation-restart"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8872")
    parser.add_argument("--state-path", required=True)
    parser.add_argument("--evidence-path", required=True)
    args = parser.parse_args()
    if args.phase == "seed":
        seed_fixture(args.evidence_path)
    elif args.phase == "before-restart":
        before_restart(args.base_url, args.state_path, args.evidence_path)
    elif args.phase == "after-restart":
        after_restart(args.base_url, args.state_path, args.evidence_path)
    else:
        after_revocation_restart(args.base_url, args.state_path, args.evidence_path)
    print(json.dumps({"phase": args.phase, "status": "PASS", "evidence": args.evidence_path}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        sys.exit(1)
