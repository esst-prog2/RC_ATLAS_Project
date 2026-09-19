from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .common import begin_write, connect_repository_db, safe_rollback


LOGGER = logging.getLogger("logitrack.repositories.reporting_records")


def _row_to_record_dict(row: Any) -> Dict[str, Any]:
    return {
        "id": str(row["record_id"]),
        "reporting_period": str(row["reporting_period"]),
        "project_id": str(row["project_id"] or ""),
        "project_name": str(row["project_name"] or ""),
        "indicator_id": str(row["indicator_id"] or ""),
        "indicator_name": str(row["indicator_name"] or ""),
        "country": str(row["country"] or ""),
        "province": str(row["province"] or ""),
        "district": str(row["district"] or ""),
        "actual_value": row["actual_value"],
        "target_value": row["target_value"],
        "progress_value": row["progress_value"],
        "budget_value": row["budget_value"],
        "currency": str(row["currency"] or ""),
        "status": str(row["status"] or ""),
        "owner": str(row["owner"] or ""),
        "notes": str(row["notes"] or ""),
        "source_dataset_id": str(row["source_dataset_id"] or ""),
        "created_at": str(row["created_at"] or ""),
        "updated_at": str(row["updated_at"] or ""),
    }


def list_reporting_records(
    db_path: Optional[str] = None,
    project_id: Optional[str] = None,
    indicator_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    conn = connect_repository_db(db_path)
    try:
        sql = "SELECT * FROM reporting_records"
        clauses: List[str] = []
        params: List[Any] = []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if indicator_id:
            clauses.append("indicator_id = ?")
            params.append(indicator_id)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY reporting_period DESC, record_id DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_record_dict(row) for row in rows]
    finally:
        conn.close()


def upsert_reporting_records(records: List[Dict[str, Any]], db_path: Optional[str] = None) -> Dict[str, Any]:
    conn = connect_repository_db(db_path)
    try:
        begin_write(conn)
        for record in records:
            conn.execute(
                """
                INSERT INTO reporting_records
                (record_id, reporting_period, project_id, project_name, indicator_id, indicator_name, country, province, district, actual_value, target_value, progress_value, budget_value, currency, status, owner, notes, source_dataset_id, created_at, updated_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(record_id) DO UPDATE SET
                    reporting_period = excluded.reporting_period,
                    project_id = excluded.project_id,
                    project_name = excluded.project_name,
                    indicator_id = excluded.indicator_id,
                    indicator_name = excluded.indicator_name,
                    country = excluded.country,
                    province = excluded.province,
                    district = excluded.district,
                    actual_value = excluded.actual_value,
                    target_value = excluded.target_value,
                    progress_value = excluded.progress_value,
                    budget_value = excluded.budget_value,
                    currency = excluded.currency,
                    status = excluded.status,
                    owner = excluded.owner,
                    notes = excluded.notes,
                    source_dataset_id = excluded.source_dataset_id,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    synced_at = excluded.synced_at
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
                    str(record.get("updated_at", "")) or str(record.get("created_at", "")),
                ),
            )
        conn.execute("COMMIT")
        return {"ok": True, "count": len(records)}
    except Exception:
        safe_rollback(conn)
        LOGGER.exception("Failed to upsert reporting records into relational repository")
        raise
    finally:
        conn.close()


def replace_all_reporting_records(records: List[Dict[str, Any]], db_path: Optional[str] = None) -> Dict[str, Any]:
    conn = connect_repository_db(db_path)
    try:
        begin_write(conn)
        conn.execute("DELETE FROM reporting_records")
        for record in records:
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
                    str(record.get("updated_at", "")) or str(record.get("created_at", "")),
                ),
            )
        conn.execute("COMMIT")
        return {"ok": True, "count": len(records)}
    except Exception:
        safe_rollback(conn)
        LOGGER.exception("Failed to replace reporting records in relational repository")
        raise
    finally:
        conn.close()
