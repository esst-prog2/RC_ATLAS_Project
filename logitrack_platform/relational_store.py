from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS store_meta (
        meta_key TEXT PRIMARY KEY,
        meta_value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sync_history (
        sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
        synced_at TEXT NOT NULL,
        source_backend TEXT NOT NULL,
        source_path TEXT,
        counts_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS projects (
        project_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        objective TEXT,
        indicator_count INTEGER NOT NULL DEFAULT 0,
        synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS indicators (
        indicator_id TEXT PRIMARY KEY,
        organization_id TEXT NOT NULL DEFAULT '',
        project_id TEXT NOT NULL,
        name TEXT NOT NULL,
        unit TEXT,
        frequency TEXT,
        direction TEXT,
        level TEXT,
        target REAL,
        baseline REAL,
        location_count INTEGER NOT NULL DEFAULT 0,
        synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS logical_framework_results (
        result_id TEXT PRIMARY KEY,
        organization_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        result_type TEXT NOT NULL CHECK (result_type IN ('goal', 'outcome', 'output')),
        parent_result_id TEXT,
        title TEXT NOT NULL,
        description TEXT,
        display_order INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL,
        created_at TEXT,
        updated_at TEXT,
        synced_at TEXT NOT NULL,
        FOREIGN KEY (parent_result_id) REFERENCES logical_framework_results(result_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS indicator_result_links (
        link_id TEXT PRIMARY KEY,
        organization_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        indicator_id TEXT NOT NULL UNIQUE,
        result_id TEXT NOT NULL,
        result_type TEXT NOT NULL CHECK (result_type IN ('outcome', 'output')),
        created_at TEXT,
        updated_at TEXT,
        synced_at TEXT NOT NULL,
        FOREIGN KEY (indicator_id) REFERENCES indicators(indicator_id) ON DELETE CASCADE,
        FOREIGN KEY (result_id) REFERENCES logical_framework_results(result_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS indicator_locations (
        location_key TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        indicator_id TEXT NOT NULL,
        country TEXT,
        province TEXT,
        district TEXT,
        latitude REAL,
        longitude REAL,
        target_local REAL,
        actual_local REAL,
        budget_local REAL,
        currency TEXT,
        synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS operational_activities (
        activity_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        name TEXT NOT NULL,
        owner TEXT,
        start_date TEXT,
        due_date TEXT,
        status TEXT,
        linked_indicator_count INTEGER NOT NULL DEFAULT 0,
        task_count INTEGER NOT NULL DEFAULT 0,
        linked_indicator_ids_json TEXT NOT NULL,
        synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        activity_id TEXT NOT NULL,
        name TEXT NOT NULL,
        owner TEXT,
        due_date TEXT,
        status TEXT,
        notes TEXT,
        synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tidy_datasets (
        dataset_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        source_type TEXT,
        created_at TEXT,
        updated_at TEXT,
        row_count INTEGER NOT NULL DEFAULT 0,
        synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS semantic_mappings (
        mapping_id TEXT PRIMARY KEY,
        dataset_id TEXT NOT NULL,
        name TEXT,
        status TEXT,
        confidence REAL,
        notes TEXT,
        fields_json TEXT NOT NULL,
        created_at TEXT,
        updated_at TEXT,
        synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dashboard_templates (
        template_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        dashboard_type TEXT,
        scope TEXT,
        filters_json TEXT NOT NULL,
        visuals_json TEXT NOT NULL,
        layout_json TEXT NOT NULL,
        narrative_sections_json TEXT NOT NULL,
        theme TEXT,
        created_at TEXT,
        updated_at TEXT,
        synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notification_rules (
        rule_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        is_active INTEGER NOT NULL,
        schedule TEXT,
        channel TEXT,
        provider TEXT,
        min_severity TEXT,
        condition_type TEXT,
        threshold REAL,
        project_id TEXT,
        indicator_id TEXT,
        dataset_id TEXT,
        recipients_json TEXT NOT NULL,
        webhook_url TEXT,
        notes TEXT,
        last_run_at TEXT,
        created_at TEXT,
        updated_at TEXT,
        synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reporting_records (
        record_id TEXT PRIMARY KEY,
        reporting_period TEXT NOT NULL,
        project_id TEXT,
        project_name TEXT,
        indicator_id TEXT,
        indicator_name TEXT,
        country TEXT,
        province TEXT,
        district TEXT,
        actual_value REAL,
        target_value REAL,
        progress_value REAL,
        budget_value REAL,
        currency TEXT,
        status TEXT,
        owner TEXT,
        notes TEXT,
        source_dataset_id TEXT,
        created_at TEXT,
        updated_at TEXT,
        synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        organization_id TEXT,
        team_id TEXT,
        username TEXT NOT NULL UNIQUE,
        full_name TEXT,
        email TEXT,
        role TEXT,
        status TEXT,
        permissions_json TEXT,
        password_salt TEXT,
        password_hash TEXT,
        api_token_hash TEXT,
        is_active INTEGER NOT NULL,
        created_at TEXT,
        updated_at TEXT,
        last_login_at TEXT,
        synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_events (
        audit_id TEXT PRIMARY KEY,
        occurred_at TEXT NOT NULL,
        actor_id TEXT,
        actor_username TEXT,
        actor_role TEXT,
        action TEXT,
        target_type TEXT,
        target_id TEXT,
        endpoint TEXT,
        outcome TEXT,
        details_json TEXT NOT NULL,
        synced_at TEXT NOT NULL
    )
    """,
]

CONTENT_TABLES = [
    "indicator_result_links",
    "logical_framework_results",
    "indicator_locations",
    "indicators",
    "projects",
    "operational_activities",
    "tasks",
    "tidy_datasets",
    "semantic_mappings",
    "dashboard_templates",
    "notification_rules",
    "reporting_records",
    "users",
    "audit_events",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_text(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def _int_flag(value: Any) -> int:
    return 1 if bool(value) else 0


def get_relational_store_path(snapshot_path: Optional[str] = None) -> str:
    configured = (os.getenv("LOGITRACK_RELATIONAL_STORE_PATH", "") or "").strip()
    if configured:
        return configured
    base_source = snapshot_path or (os.getenv("LOGITRACK_SQLITE_PATH", "") or "").strip() or (os.getenv("LOGITRACK_DATA_PATH", "") or "").strip()
    if not base_source:
        base_source = str(Path.cwd() / "logitrack_data.json")
    base_path = Path(base_source)
    if str(base_path).endswith(".warehouse.sqlite3") or str(base_path).endswith(".relational.sqlite3"):
        return str(base_path)
    if base_path.suffix:
        return str(base_path.with_suffix(".warehouse.sqlite3"))
    return str(base_path) + ".warehouse.sqlite3"


def _connect(path: str) -> sqlite3.Connection:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    for statement in DDL_STATEMENTS:
        conn.execute(statement)
    existing_user_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    for column_name in ("organization_id", "team_id", "status", "permissions_json", "password_salt", "password_hash", "api_token_hash"):
        if column_name not in existing_user_columns:
            conn.execute(f"ALTER TABLE users ADD COLUMN {column_name} TEXT")
    existing_indicator_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(indicators)").fetchall()
    }
    if "organization_id" not in existing_indicator_columns:
        conn.execute("ALTER TABLE indicators ADD COLUMN organization_id TEXT NOT NULL DEFAULT ''")


def _delete_existing_content(conn: sqlite3.Connection) -> None:
    for table in CONTENT_TABLES:
        conn.execute(f"DELETE FROM {table}")


def _iter_projects(snapshot: Dict[str, Any]) -> Iterable[Tuple[Dict[str, Any], Dict[str, Any]]]:
    for project in snapshot.get("projects", []) or []:
        if not isinstance(project, dict):
            continue
        for indicator in project.get("indicators", []) or []:
            if isinstance(indicator, dict):
                yield project, indicator


def sync_snapshot_to_relational_store(
    snapshot: Dict[str, Any],
    *,
    db_path: Optional[str] = None,
    source_backend: str = "snapshot",
    source_path: str = "",
) -> Dict[str, Any]:
    path = db_path or get_relational_store_path(source_path)
    synced_at = _utc_now_iso()
    conn = _connect(path)
    try:
        ensure_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        _delete_existing_content(conn)

        project_rows = 0
        indicator_rows = 0
        location_rows = 0
        activity_rows = 0
        task_rows = 0
        result_rows = 0
        indicator_result_link_rows = 0
        dataset_rows = 0
        reporting_rows = 0
        mapping_rows = 0
        template_rows = 0
        rule_rows = 0
        user_rows = 0
        audit_rows = 0

        for project in snapshot.get("projects", []) or []:
            if not isinstance(project, dict):
                continue
            indicators = [item for item in (project.get("indicators") or []) if isinstance(item, dict)]
            conn.execute(
                "INSERT INTO projects (project_id, name, objective, indicator_count, synced_at) VALUES (?, ?, ?, ?, ?)",
                (
                    str(project.get("id", "")),
                    str(project.get("name", "")),
                    str(project.get("objective", "")),
                    len(indicators),
                    synced_at,
                ),
            )
            project_rows += 1
            for indicator in indicators:
                locations = [item for item in (indicator.get("locations") or []) if isinstance(item, dict)]
                conn.execute(
                    """
                    INSERT INTO indicators
                    (indicator_id, organization_id, project_id, name, unit, frequency, direction, level, target, baseline, location_count, synced_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(indicator.get("id", "")),
                        str(indicator.get("organization_id") or project.get("organization_id", "")),
                        str(project.get("id", "")),
                        str(indicator.get("name", "")),
                        str(indicator.get("unit", "")),
                        str(indicator.get("frequency", "")),
                        str(indicator.get("direction", "")),
                        str(indicator.get("level", "")),
                        indicator.get("target"),
                        indicator.get("baseline"),
                        len(locations),
                        synced_at,
                    ),
                )
                indicator_rows += 1
                for location in locations:
                    location_key = "|".join([
                        str(project.get("id", "")),
                        str(indicator.get("id", "")),
                        str(location.get("country", "")),
                        str(location.get("province", "")),
                        str(location.get("district", "")),
                    ])
                    conn.execute(
                        """
                        INSERT INTO indicator_locations
                        (location_key, project_id, indicator_id, country, province, district, latitude, longitude, target_local, actual_local, budget_local, currency, synced_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            location_key,
                            str(project.get("id", "")),
                            str(indicator.get("id", "")),
                            str(location.get("country", "")),
                            str(location.get("province", "")),
                            str(location.get("district", "")),
                            location.get("latitude"),
                            location.get("longitude"),
                            location.get("target_local"),
                            location.get("actual_local"),
                            location.get("budget_local"),
                            str(location.get("currency", "")),
                            synced_at,
                        ),
                    )
                    location_rows += 1

        result_type_order = {"goal": 0, "outcome": 1, "output": 2}
        result_items = [
            item for item in (snapshot.get("logical_framework_results") or [])
            if isinstance(item, dict)
        ]
        result_items.sort(key=lambda item: (
            result_type_order.get(str(item.get("result_type", "")).lower(), 99),
            int(item.get("display_order", 0) or 0),
            str(item.get("id", "")),
        ))
        for result in result_items:
            conn.execute(
                """
                INSERT INTO logical_framework_results
                (result_id, organization_id, project_id, result_type, parent_result_id, title, description, display_order, status, created_at, updated_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(result.get("id", "")),
                    str(result.get("organization_id", "")),
                    str(result.get("project_id", "")),
                    str(result.get("result_type", "")),
                    str(result.get("parent_id", "")) or None,
                    str(result.get("title", "")),
                    str(result.get("description", "")),
                    int(result.get("display_order", 0) or 0),
                    str(result.get("status", "active") or "active"),
                    str(result.get("created_at", "")),
                    str(result.get("updated_at", "")),
                    synced_at,
                ),
            )
            result_rows += 1

        for link in snapshot.get("indicator_result_links", []) or []:
            if not isinstance(link, dict):
                continue
            conn.execute(
                """
                INSERT INTO indicator_result_links
                (link_id, organization_id, project_id, indicator_id, result_id, result_type, created_at, updated_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(link.get("id", "")),
                    str(link.get("organization_id", "")),
                    str(link.get("project_id", "")),
                    str(link.get("indicator_id", "")),
                    str(link.get("result_id", "")),
                    str(link.get("result_type", "")),
                    str(link.get("created_at", "")),
                    str(link.get("updated_at", "")),
                    synced_at,
                ),
            )
            indicator_result_link_rows += 1

        for project_id, ops in (snapshot.get("ops_by_project", {}) or {}).items():
            if not isinstance(ops, dict):
                continue
            for activity in ops.get("activities", []) or []:
                if not isinstance(activity, dict):
                    continue
                tasks = [item for item in (activity.get("tasks") or []) if isinstance(item, dict)]
                linked_indicator_ids = [str(item) for item in (activity.get("linked_indicator_ids") or [])]
                conn.execute(
                    """
                    INSERT INTO operational_activities
                    (activity_id, project_id, name, owner, start_date, due_date, status, linked_indicator_count, task_count, linked_indicator_ids_json, synced_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(activity.get("id", "")),
                        str(project_id),
                        str(activity.get("name", "")),
                        str(activity.get("owner", "")),
                        str(activity.get("start_date") or ""),
                        str(activity.get("due_date") or ""),
                        str(activity.get("status", "")),
                        len(linked_indicator_ids),
                        len(tasks),
                        _json_text(linked_indicator_ids),
                        synced_at,
                    ),
                )
                activity_rows += 1
                for task in tasks:
                    conn.execute(
                        """
                        INSERT INTO tasks
                        (task_id, project_id, activity_id, name, owner, due_date, status, notes, synced_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(task.get("id", "")),
                            str(project_id),
                            str(activity.get("id", "")),
                            str(task.get("name", "")),
                            str(task.get("owner", "")),
                            str(task.get("due_date") or ""),
                            str(task.get("status", "")),
                            str(task.get("notes", "")),
                            synced_at,
                        ),
                    )
                    task_rows += 1

        for dataset in snapshot.get("tidy_datasets", []) or []:
            if not isinstance(dataset, dict):
                continue
            row_count = len(dataset.get("rows") or []) if isinstance(dataset.get("rows"), list) else 0
            conn.execute(
                """
                INSERT INTO tidy_datasets
                (dataset_id, name, description, source_type, created_at, updated_at, row_count, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(dataset.get("id", "")),
                    str(dataset.get("name", "")),
                    str(dataset.get("description", "")),
                    str(dataset.get("source_type", "")),
                    str(dataset.get("created_at", "")),
                    str(dataset.get("updated_at", "")),
                    row_count,
                    synced_at,
                ),
            )
            dataset_rows += 1

        for mapping in snapshot.get("semantic_mappings", []) or []:
            if not isinstance(mapping, dict):
                continue
            conn.execute(
                """
                INSERT INTO semantic_mappings
                (mapping_id, dataset_id, name, status, confidence, notes, fields_json, created_at, updated_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(mapping.get("id", "")),
                    str(mapping.get("dataset_id", "")),
                    str(mapping.get("name", "")),
                    str(mapping.get("status", "")),
                    mapping.get("confidence"),
                    str(mapping.get("notes", "")),
                    _json_text(mapping.get("fields") or {}),
                    str(mapping.get("created_at", "")),
                    str(mapping.get("updated_at", "")),
                    synced_at,
                ),
            )
            mapping_rows += 1

        for template in snapshot.get("dashboard_templates", []) or []:
            if not isinstance(template, dict):
                continue
            conn.execute(
                """
                INSERT INTO dashboard_templates
                (template_id, name, description, dashboard_type, scope, filters_json, visuals_json, layout_json, narrative_sections_json, theme, created_at, updated_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(template.get("id", "")),
                    str(template.get("name", "")),
                    str(template.get("description", "")),
                    str(template.get("dashboard_type", "")),
                    str(template.get("scope", "")),
                    _json_text(template.get("filters") or []),
                    _json_text(template.get("visuals") or []),
                    _json_text(template.get("layout") or []),
                    _json_text(template.get("narrative_sections") or []),
                    str(template.get("theme", "")),
                    str(template.get("created_at", "")),
                    str(template.get("updated_at", "")),
                    synced_at,
                ),
            )
            template_rows += 1

        for rule in snapshot.get("notification_rules", []) or []:
            if not isinstance(rule, dict):
                continue
            conn.execute(
                """
                INSERT INTO notification_rules
                (rule_id, name, is_active, schedule, channel, provider, min_severity, condition_type, threshold, project_id, indicator_id, dataset_id, recipients_json, webhook_url, notes, last_run_at, created_at, updated_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(rule.get("id", "")),
                    str(rule.get("name", "")),
                    _int_flag(rule.get("is_active", True)),
                    str(rule.get("schedule", "")),
                    str(rule.get("channel", "")),
                    str(rule.get("provider", "")),
                    str(rule.get("min_severity", "")),
                    str(rule.get("condition_type", "")),
                    rule.get("threshold"),
                    str(rule.get("project_id", "")),
                    str(rule.get("indicator_id", "")),
                    str(rule.get("dataset_id", "")),
                    _json_text(rule.get("recipients") or []),
                    str(rule.get("webhook_url", "")),
                    str(rule.get("notes", "")),
                    str(rule.get("last_run_at", "")),
                    str(rule.get("created_at", "")),
                    str(rule.get("updated_at", "")),
                    synced_at,
                ),
            )
            rule_rows += 1

        for record in snapshot.get("reporting_records", []) or []:
            if not isinstance(record, dict):
                continue
            conn.execute(
                """
                INSERT INTO reporting_records
                (record_id, reporting_period, project_id, project_name, indicator_id, indicator_name, country, province, district, actual_value, target_value, progress_value, budget_value, currency, status, owner, notes, source_dataset_id, created_at, updated_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(record.get("id", "")),
                    str(record.get("reporting_period", "")),
                    str(record.get("project_id", "")),
                    str(record.get("project_name", "")),
                    str(record.get("indicator_id", "")),
                    str(record.get("indicator_name", "")),
                    str(record.get("country", "")),
                    str(record.get("province", "")),
                    str(record.get("district", "")),
                    record.get("actual_value"),
                    record.get("target_value"),
                    record.get("progress_value"),
                    record.get("budget_value"),
                    str(record.get("currency", "")),
                    str(record.get("status", "")),
                    str(record.get("owner", "")),
                    str(record.get("notes", "")),
                    str(record.get("source_dataset_id", "")),
                    str(record.get("created_at", "")),
                    str(record.get("updated_at", "")),
                    synced_at,
                ),
            )
            reporting_rows += 1

        for user in snapshot.get("users", []) or []:
            if not isinstance(user, dict):
                continue
            conn.execute(
                """
                INSERT INTO users
                (user_id, organization_id, team_id, username, full_name, email, role, status, permissions_json, password_salt, password_hash, api_token_hash, is_active, created_at, updated_at, last_login_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(user.get("id", "")),
                    str(user.get("organization_id", "")),
                    str(user.get("team_id", "")),
                    str(user.get("username", "")),
                    str(user.get("full_name", "")),
                    str(user.get("email", "")),
                    str(user.get("role", "")),
                    str(user.get("status", "active")),
                    _json_text(user.get("permissions") or []),
                    str(user.get("password_salt", "")),
                    str(user.get("password_hash", "")),
                    str(user.get("api_token_hash", "")),
                    _int_flag(user.get("is_active", True)),
                    str(user.get("created_at", "")),
                    str(user.get("updated_at", "")),
                    str(user.get("last_login_at", "")),
                    synced_at,
                ),
            )
            user_rows += 1

        for event in snapshot.get("audit_events", []) or []:
            if not isinstance(event, dict):
                continue
            conn.execute(
                """
                INSERT INTO audit_events
                (audit_id, occurred_at, actor_id, actor_username, actor_role, action, target_type, target_id, endpoint, outcome, details_json, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.get("id", "")),
                    str(event.get("occurred_at", "")),
                    str(event.get("actor_id", "")),
                    str(event.get("actor_username", "")),
                    str(event.get("actor_role", "")),
                    str(event.get("action", "")),
                    str(event.get("target_type", "")),
                    str(event.get("target_id", "")),
                    str(event.get("endpoint", "")),
                    str(event.get("outcome", "")),
                    _json_text(event.get("details") or {}),
                    synced_at,
                ),
            )
            audit_rows += 1

        counts = {
            "projects": project_rows,
            "indicators": indicator_rows,
            "indicator_locations": location_rows,
            "logical_framework_results": result_rows,
            "indicator_result_links": indicator_result_link_rows,
            "activities": activity_rows,
            "tasks": task_rows,
            "tidy_datasets": dataset_rows,
            "semantic_mappings": mapping_rows,
            "dashboard_templates": template_rows,
            "notification_rules": rule_rows,
            "reporting_records": reporting_rows,
            "users": user_rows,
            "audit_events": audit_rows,
        }
        conn.execute(
            "INSERT INTO sync_history (synced_at, source_backend, source_path, counts_json) VALUES (?, ?, ?, ?)",
            (synced_at, source_backend, source_path, json.dumps(counts, ensure_ascii=False)),
        )
        for key, value in {
            "last_synced_at": synced_at,
            "source_backend": source_backend,
            "source_path": source_path,
            "counts_json": json.dumps(counts, ensure_ascii=False),
        }.items():
            conn.execute(
                """
                INSERT INTO store_meta (meta_key, meta_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(meta_key) DO UPDATE SET
                    meta_value = excluded.meta_value,
                    updated_at = excluded.updated_at
                """,
                (key, str(value), synced_at),
            )
        conn.execute("COMMIT")
        return {
            "ok": True,
            "db_path": path,
            "synced_at": synced_at,
            "source_backend": source_backend,
            "source_path": source_path,
            "counts": counts,
        }
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def _read_meta_map(conn: sqlite3.Connection) -> Dict[str, str]:
    rows = conn.execute("SELECT meta_key, meta_value FROM store_meta").fetchall()
    return {str(row["meta_key"]): str(row["meta_value"]) for row in rows}


def _table_count(conn: sqlite3.Connection, table_name: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def get_relational_store_status(db_path: Optional[str] = None) -> Dict[str, Any]:
    path = db_path or get_relational_store_path()
    exists = os.path.exists(path)
    status = {
        "path": path,
        "exists": exists,
        "size_bytes": os.path.getsize(path) if exists else 0,
        "counts": {},
        "meta": {},
    }
    if not exists:
        return status
    conn = _connect(path)
    try:
        ensure_schema(conn)
        status["counts"] = {table: _table_count(conn, table) for table in CONTENT_TABLES}
        status["meta"] = _read_meta_map(conn)
        latest_sync = conn.execute(
            "SELECT synced_at, source_backend, source_path, counts_json FROM sync_history ORDER BY sync_id DESC LIMIT 1"
        ).fetchone()
        if latest_sync is not None:
            status["last_sync"] = {
                "synced_at": str(latest_sync["synced_at"]),
                "source_backend": str(latest_sync["source_backend"]),
                "source_path": str(latest_sync["source_path"] or ""),
                "counts": json.loads(str(latest_sync["counts_json"] or "{}")),
            }
        else:
            status["last_sync"] = None
        return status
    finally:
        conn.close()
