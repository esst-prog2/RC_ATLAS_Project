from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .common import begin_write, connect_repository_db, json_loads_or_default, safe_rollback


LOGGER = logging.getLogger("logitrack.repositories.notification_rules")


def _row_to_rule_dict(row: Any) -> Dict[str, Any]:
    return {
        "id": str(row["rule_id"]),
        "name": str(row["name"]),
        "is_active": bool(row["is_active"]),
        "schedule": str(row["schedule"] or "manual"),
        "channel": str(row["channel"] or "webhook"),
        "provider": str(row["provider"] or ""),
        "min_severity": str(row["min_severity"] or "medium"),
        "condition_type": str(row["condition_type"] or ""),
        "threshold": row["threshold"],
        "project_id": str(row["project_id"] or ""),
        "indicator_id": str(row["indicator_id"] or ""),
        "dataset_id": str(row["dataset_id"] or ""),
        "recipients": json_loads_or_default(row["recipients_json"], []),
        "webhook_url": str(row["webhook_url"] or ""),
        "notes": str(row["notes"] or ""),
        "last_run_at": str(row["last_run_at"] or ""),
        "created_at": str(row["created_at"] or ""),
        "updated_at": str(row["updated_at"] or ""),
    }


def list_notification_rules(db_path: Optional[str] = None, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
    conn = connect_repository_db(db_path)
    try:
        sql = "SELECT * FROM notification_rules"
        params: List[Any] = []
        if is_active is not None:
            sql += " WHERE is_active = ?"
            params.append(1 if is_active else 0)
        sql += " ORDER BY name"
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_rule_dict(row) for row in rows]
    finally:
        conn.close()


def get_notification_rule(rule_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = connect_repository_db(db_path)
    try:
        row = conn.execute("SELECT * FROM notification_rules WHERE rule_id = ?", (rule_id,)).fetchone()
        return _row_to_rule_dict(row) if row else None
    finally:
        conn.close()


def upsert_notification_rule(rule: Dict[str, Any], db_path: Optional[str] = None) -> str:
    conn = connect_repository_db(db_path)
    try:
        begin_write(conn)
        existing = conn.execute("SELECT 1 FROM notification_rules WHERE rule_id = ?", (str(rule.get("id", "")),)).fetchone()
        conn.execute(
            """
            INSERT INTO notification_rules
            (rule_id, name, is_active, schedule, channel, provider, min_severity, condition_type, threshold, project_id, indicator_id, dataset_id, recipients_json, webhook_url, notes, last_run_at, created_at, updated_at, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(rule_id) DO UPDATE SET
                name = excluded.name,
                is_active = excluded.is_active,
                schedule = excluded.schedule,
                channel = excluded.channel,
                provider = excluded.provider,
                min_severity = excluded.min_severity,
                condition_type = excluded.condition_type,
                threshold = excluded.threshold,
                project_id = excluded.project_id,
                indicator_id = excluded.indicator_id,
                dataset_id = excluded.dataset_id,
                recipients_json = excluded.recipients_json,
                webhook_url = excluded.webhook_url,
                notes = excluded.notes,
                last_run_at = excluded.last_run_at,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                synced_at = excluded.synced_at
            """,
            (
                str(rule.get("id", "")),
                str(rule.get("name", "")),
                1 if bool(rule.get("is_active", True)) else 0,
                str(rule.get("schedule", "manual")),
                str(rule.get("channel", "webhook")),
                str(rule.get("provider", "")),
                str(rule.get("min_severity", "medium")),
                str(rule.get("condition_type", "")),
                rule.get("threshold"),
                str(rule.get("project_id", "")),
                str(rule.get("indicator_id", "")),
                str(rule.get("dataset_id", "")),
                json.dumps(rule.get("recipients", []) or [], ensure_ascii=False),
                str(rule.get("webhook_url", "")),
                str(rule.get("notes", "")),
                str(rule.get("last_run_at", "")),
                str(rule.get("created_at", "")),
                str(rule.get("updated_at", "")),
                str(rule.get("updated_at", "")) or str(rule.get("created_at", "")),
            ),
        )
        conn.execute("COMMIT")
        return "updated" if existing else "created"
    except Exception:
        safe_rollback(conn)
        LOGGER.exception("Failed to upsert notification rule into relational repository")
        raise
    finally:
        conn.close()


def update_notification_rule_run_state(rule_id: str, last_run_at: str, updated_at: str, db_path: Optional[str] = None) -> bool:
    conn = connect_repository_db(db_path)
    try:
        begin_write(conn)
        result = conn.execute(
            "UPDATE notification_rules SET last_run_at = ?, updated_at = ?, synced_at = ? WHERE rule_id = ?",
            (last_run_at, updated_at, updated_at, rule_id),
        )
        conn.execute("COMMIT")
        return result.rowcount > 0
    except Exception:
        safe_rollback(conn)
        LOGGER.exception("Failed to update notification rule run state")
        raise
    finally:
        conn.close()


def replace_all_notification_rules(rules: List[Dict[str, Any]], db_path: Optional[str] = None) -> Dict[str, Any]:
    conn = connect_repository_db(db_path)
    try:
        begin_write(conn)
        conn.execute("DELETE FROM notification_rules")
        for rule in rules:
            conn.execute(
                """
                INSERT INTO notification_rules
                (rule_id, name, is_active, schedule, channel, provider, min_severity, condition_type, threshold, project_id, indicator_id, dataset_id, recipients_json, webhook_url, notes, last_run_at, created_at, updated_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(rule.get("id", "")),
                    str(rule.get("name", "")),
                    1 if bool(rule.get("is_active", True)) else 0,
                    str(rule.get("schedule", "manual")),
                    str(rule.get("channel", "webhook")),
                    str(rule.get("provider", "")),
                    str(rule.get("min_severity", "medium")),
                    str(rule.get("condition_type", "")),
                    rule.get("threshold"),
                    str(rule.get("project_id", "")),
                    str(rule.get("indicator_id", "")),
                    str(rule.get("dataset_id", "")),
                    json.dumps(rule.get("recipients", []) or [], ensure_ascii=False),
                    str(rule.get("webhook_url", "")),
                    str(rule.get("notes", "")),
                    str(rule.get("last_run_at", "")),
                    str(rule.get("created_at", "")),
                    str(rule.get("updated_at", "")),
                    str(rule.get("updated_at", "")) or str(rule.get("created_at", "")),
                ),
            )
        conn.execute("COMMIT")
        return {"ok": True, "count": len(rules)}
    except Exception:
        safe_rollback(conn)
        LOGGER.exception("Failed to replace notification rules in relational repository")
        raise
    finally:
        conn.close()
