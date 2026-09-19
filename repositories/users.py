from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .common import begin_write, connect_repository_db, safe_rollback


LOGGER = logging.getLogger("logitrack.repositories.users")


def _row_to_user_dict(row: Any) -> Dict[str, Any]:
    permissions_raw = row["permissions_json"] if "permissions_json" in row.keys() else "[]"
    try:
        permissions = json.loads(str(permissions_raw or "[]"))
    except Exception:
        permissions = []
    return {
        "id": str(row["user_id"]),
        "organization_id": str(row["organization_id"] or ""),
        "team_id": str(row["team_id"] or ""),
        "username": str(row["username"]),
        "full_name": str(row["full_name"] or ""),
        "email": str(row["email"] or ""),
        "role": str(row["role"] or "viewer"),
        "status": str(row["status"] or "active"),
        "permissions": permissions if isinstance(permissions, list) else [],
        "password_salt": str(row["password_salt"] or ""),
        "password_hash": str(row["password_hash"] or ""),
        "api_token_hash": str(row["api_token_hash"] or ""),
        "is_active": bool(row["is_active"]),
        "created_at": str(row["created_at"] or ""),
        "updated_at": str(row["updated_at"] or ""),
        "last_login_at": str(row["last_login_at"] or ""),
    }


def list_users(db_path: Optional[str] = None, only_active: Optional[bool] = None) -> List[Dict[str, Any]]:
    conn = connect_repository_db(db_path)
    try:
        sql = "SELECT * FROM users"
        params: List[Any] = []
        if only_active is not None:
            sql += " WHERE is_active = ?"
            params.append(1 if only_active else 0)
        sql += " ORDER BY username"
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_user_dict(row) for row in rows]
    finally:
        conn.close()


def get_user_by_id(user_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = connect_repository_db(db_path)
    try:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return _row_to_user_dict(row) if row else None
    finally:
        conn.close()


def get_user_by_username(username: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = connect_repository_db(db_path)
    try:
        row = conn.execute("SELECT * FROM users WHERE lower(username) = lower(?)", (username,)).fetchone()
        return _row_to_user_dict(row) if row else None
    finally:
        conn.close()


def get_user_by_token_hash(token_hash: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = connect_repository_db(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE api_token_hash = ?",
            (token_hash,),
        ).fetchone()
        return _row_to_user_dict(row) if row else None
    finally:
        conn.close()


def upsert_user(user: Dict[str, Any], db_path: Optional[str] = None) -> str:
    conn = connect_repository_db(db_path)
    try:
        begin_write(conn)
        existing = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (str(user.get("id", "")),)).fetchone()
        conn.execute(
            """
            INSERT INTO users
            (user_id, organization_id, team_id, username, full_name, email, role, status, permissions_json, password_salt, password_hash, api_token_hash, is_active, created_at, updated_at, last_login_at, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                organization_id = excluded.organization_id,
                team_id = excluded.team_id,
                username = excluded.username,
                full_name = excluded.full_name,
                email = excluded.email,
                role = excluded.role,
                status = excluded.status,
                permissions_json = excluded.permissions_json,
                password_salt = excluded.password_salt,
                password_hash = excluded.password_hash,
                api_token_hash = excluded.api_token_hash,
                is_active = excluded.is_active,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                last_login_at = excluded.last_login_at,
                synced_at = excluded.synced_at
            """,
            (
                str(user.get("id", "")),
                str(user.get("organization_id", "")),
                str(user.get("team_id", "")),
                str(user.get("username", "")),
                str(user.get("full_name", "")),
                str(user.get("email", "")),
                str(user.get("role", "viewer")),
                str(user.get("status", "active")),
                json.dumps(user.get("permissions", []) or [], ensure_ascii=False),
                str(user.get("password_salt", "")),
                str(user.get("password_hash", "")),
                str(user.get("api_token_hash", "")),
                1 if bool(user.get("is_active", True)) else 0,
                str(user.get("created_at", "")),
                str(user.get("updated_at", "")),
                str(user.get("last_login_at", "")),
                str(user.get("updated_at", "")) or str(user.get("created_at", "")),
            ),
        )
        conn.execute("COMMIT")
        return "updated" if existing else "created"
    except Exception:
        safe_rollback(conn)
        LOGGER.exception("Failed to upsert user into relational repository")
        raise
    finally:
        conn.close()


def replace_all_users(users: List[Dict[str, Any]], db_path: Optional[str] = None) -> Dict[str, Any]:
    conn = connect_repository_db(db_path)
    try:
        begin_write(conn)
        conn.execute("DELETE FROM users")
        for user in users:
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
                    str(user.get("role", "viewer")),
                    str(user.get("status", "active")),
                    json.dumps(user.get("permissions", []) or [], ensure_ascii=False),
                    str(user.get("password_salt", "")),
                    str(user.get("password_hash", "")),
                    str(user.get("api_token_hash", "")),
                    1 if bool(user.get("is_active", True)) else 0,
                    str(user.get("created_at", "")),
                    str(user.get("updated_at", "")),
                    str(user.get("last_login_at", "")),
                    str(user.get("updated_at", "")) or str(user.get("created_at", "")),
                ),
            )
        conn.execute("COMMIT")
        return {"ok": True, "count": len(users)}
    except Exception:
        safe_rollback(conn)
        LOGGER.exception("Failed to replace users in relational repository")
        raise
    finally:
        conn.close()
