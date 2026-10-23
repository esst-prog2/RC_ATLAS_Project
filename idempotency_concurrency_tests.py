import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from logical_framework_api_tests import MODULE
from services.demo_seed import build_demo_seed_bundle


class IdempotencyConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / "idempotency.json")
        self.previous_env = {
            name: os.environ.get(name)
            for name in (
                "LOGITRACK_STORAGE_BACKEND",
                "LOGITRACK_DATA_PATH",
                "LOGITRACK_SQLITE_PATH",
                "LOGITRACK_ENABLE_RELATIONAL_MIRROR",
                "LOGITRACK_ENABLE_REPOSITORY_DOMAINS",
                "LOGITRACK_IDEMPOTENCY_RETENTION_HOURS",
            )
        }
        os.environ["LOGITRACK_STORAGE_BACKEND"] = "json"
        os.environ["LOGITRACK_DATA_PATH"] = self.data_path
        os.environ.pop("LOGITRACK_SQLITE_PATH", None)
        os.environ["LOGITRACK_ENABLE_RELATIONAL_MIRROR"] = "false"
        os.environ["LOGITRACK_ENABLE_REPOSITORY_DOMAINS"] = "false"
        os.environ["LOGITRACK_IDEMPOTENCY_RETENTION_HOURS"] = "72"
        data = MODULE.from_serializable(build_demo_seed_bundle(MODULE.build_password_hash).payload)
        user = MODULE.find_user_by_username(data, "org.admin")
        self.actor_id = user.id
        self.token = "idempotency-admin-token"
        MODULE.register_session_for_token(data, user, self.token)
        MODULE.save_data_to_path(data)
        self.client = TestClient(MODULE.app)

    def tearDown(self):
        self.client.close()
        for name, value in self.previous_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.temp_dir.cleanup()

    def payload(self, name="Idempotent Project"):
        return {
            "project_name": name,
            "programme": "Synthetic Programme",
            "donor": "Synthetic Donor",
            "implementing_partner": "Synthetic Partner",
            "sector": "Education",
            "description": "Synthetic idempotency fixture",
            "country": "Testland",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        }

    def headers(self, key, version=None):
        headers = {"X-Auth-Token": self.token, "X-Idempotency-Key": key}
        if version is not None:
            headers["X-Workspace-Version"] = str(version)
        return headers

    def current_version(self):
        response = self.client.get("/v1/admin/projects", headers={"X-Auth-Token": self.token})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["workspace_version"]

    def test_exact_replay_returns_one_resource_and_changed_payload_conflicts(self):
        version = self.current_version()
        first = self.client.post(
            "/v1/admin/projects",
            headers=self.headers("project-create-001", version),
            json=self.payload(),
        )
        replay = self.client.post(
            "/v1/admin/projects",
            headers=self.headers("project-create-001", version),
            json=self.payload(),
        )
        conflict = self.client.post(
            "/v1/admin/projects",
            headers=self.headers("project-create-001", version),
            json=self.payload("Changed Intent"),
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json(), first.json())
        self.assertEqual(conflict.status_code, 409, conflict.text)
        data = MODULE.load_data_from_path()
        created_id = first.json()["project"]["id"]
        self.assertEqual(sum(1 for item in data.projects if item.id == created_id), 1)
        self.assertEqual(sum(1 for item in data.audit_events if item.target_id == created_id and item.action == "project.created"), 1)
        self.assertEqual(sum(1 for item in data.idempotency_records if item.resource_id == created_id), 1)

    def test_stale_workspace_version_rejects_without_mutation(self):
        version = self.current_version()
        first = self.client.post(
            "/v1/admin/projects",
            headers=self.headers("project-create-version-a", version),
            json=self.payload("Version A"),
        )
        self.assertEqual(first.status_code, 200, first.text)
        before = MODULE.to_serializable(MODULE.load_data_from_path())
        stale = self.client.post(
            "/v1/admin/projects",
            headers=self.headers("project-create-version-b", version),
            json=self.payload("Version B"),
        )
        self.assertEqual(stale.status_code, 409, stale.text)
        self.assertEqual(MODULE.to_serializable(MODULE.load_data_from_path()), before)

    def test_concurrent_same_intent_commits_once_and_replays(self):
        version = self.current_version()

        def create_once():
            with TestClient(MODULE.app) as client:
                return client.post(
                    "/v1/admin/projects",
                    headers=self.headers("project-create-concurrent", version),
                    json=self.payload("Concurrent Intent"),
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: create_once(), range(2)))
        self.assertEqual([item.status_code for item in responses], [200, 200], [item.text for item in responses])
        self.assertEqual(responses[0].json(), responses[1].json())
        created_id = responses[0].json()["project"]["id"]
        data = MODULE.load_data_from_path()
        self.assertEqual(sum(1 for item in data.projects if item.id == created_id), 1)
        self.assertEqual(sum(1 for item in data.audit_events if item.target_id == created_id and item.action == "project.created"), 1)

    def test_replay_survives_restart(self):
        version = self.current_version()
        first = self.client.post(
            "/v1/admin/projects",
            headers=self.headers("project-create-restart", version),
            json=self.payload("Restart Replay"),
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.client.close()
        self.client = TestClient(MODULE.app)
        replay = self.client.post(
            "/v1/admin/projects",
            headers=self.headers("project-create-restart", version),
            json=self.payload("Restart Replay"),
        )
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json(), first.json())

    def test_idempotency_key_is_scoped_by_actor_and_tenant(self):
        data = MODULE.load_data_from_path()
        data.organizations.append(MODULE.OrganizationAccount(
            id="org_idempotency_other",
            organization_name="Other Synthetic Tenant",
            status="active",
        ))
        same_tenant_actor = MODULE.UserAccount(
            id="user_idempotency_peer",
            organization_id="org_blue_delta",
            username="idempotency.peer",
            email="idempotency.peer@example.test",
            full_name="Idempotency Peer",
            role="organization_admin",
            status="active",
            is_active=True,
        )
        foreign_actor = MODULE.UserAccount(
            id="user_idempotency_foreign",
            organization_id="org_idempotency_other",
            username="idempotency.foreign",
            email="idempotency.foreign@example.test",
            full_name="Idempotency Foreign",
            role="organization_admin",
            status="active",
            is_active=True,
        )
        data.users.extend([same_tenant_actor, foreign_actor])
        peer_token = "idempotency-peer-token"
        foreign_token = "idempotency-foreign-token"
        MODULE.register_session_for_token(data, same_tenant_actor, peer_token)
        MODULE.register_session_for_token(data, foreign_actor, foreign_token)
        MODULE.save_data_to_path(data)

        key = "shared-client-key"
        responses = []
        for token, name in (
            (self.token, "Primary Actor Intent"),
            (peer_token, "Peer Actor Intent"),
            (foreign_token, "Foreign Tenant Intent"),
        ):
            response = self.client.post(
                "/v1/admin/projects",
                headers={"X-Auth-Token": token, "X-Idempotency-Key": key},
                json=self.payload(name),
            )
            self.assertEqual(response.status_code, 200, response.text)
            responses.append(response.json())

        self.assertEqual(len({item["project"]["id"] for item in responses}), 3)
        persisted = MODULE.load_data_from_path()
        scoped_records = [record for record in persisted.idempotency_records if record.key_hash == MODULE.hash_with_sha256(key)]
        self.assertEqual(len(scoped_records), 3)
        self.assertEqual(
            {(record.organization_id, record.actor_user_id) for record in scoped_records},
            {
                ("org_blue_delta", self.actor_id),
                ("org_blue_delta", "user_idempotency_peer"),
                ("org_idempotency_other", "user_idempotency_foreign"),
            },
        )

    def test_pre_commit_save_failure_persists_neither_project_nor_ledger(self):
        before = MODULE.to_serializable(MODULE.load_data_from_path())
        with patch.object(MODULE, "save_data_to_path", side_effect=OSError("synthetic pre-commit failure")):
            failed = self.client.post(
                "/v1/admin/projects",
                headers=self.headers("project-create-save-failure"),
                json=self.payload("Pre-commit Failure"),
            )
        self.assertEqual(failed.status_code, 500, failed.text)
        self.assertEqual(MODULE.to_serializable(MODULE.load_data_from_path()), before)

    def test_projection_failure_preserves_canonical_idempotency_for_truthful_retry(self):
        def commit_then_fail_projection(data, path=None):
            MODULE.save_canonical_data_to_path(data, path)
            raise RuntimeError("synthetic projection refresh failure")

        with patch.object(MODULE, "save_data_to_path", side_effect=commit_then_fail_projection):
            first = self.client.post(
                "/v1/admin/projects",
                headers=self.headers("project-create-projection-failure"),
                json=self.payload("Projection Failure Intent"),
            )
        self.assertEqual(first.status_code, 500, first.text)
        self.assertIn("canonical data was committed", first.text.lower())

        retry = self.client.post(
            "/v1/admin/projects",
            headers=self.headers("project-create-projection-failure"),
            json=self.payload("Projection Failure Intent"),
        )
        self.assertEqual(retry.status_code, 200, retry.text)
        persisted = MODULE.load_data_from_path()
        created = [item for item in persisted.projects if item.name == "Projection Failure Intent"]
        self.assertEqual(len(created), 1)
        self.assertEqual(
            sum(1 for record in persisted.idempotency_records if record.resource_id == created[0].id),
            1,
        )


if __name__ == "__main__":
    unittest.main()
