from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from logitrack_platform.relational_store import ensure_schema, get_relational_store_path


LOGGER = logging.getLogger("logitrack.repositories")


def connect_repository_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or get_relational_store_path()
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    ensure_schema(conn)
    return conn


def json_loads_or_default(raw: Any, default: Any) -> Any:
    if raw in (None, ""):
        return default
    try:
        return json.loads(str(raw))
    except Exception:
        return default


def begin_write(conn: sqlite3.Connection) -> None:
    conn.execute("BEGIN IMMEDIATE")


def safe_rollback(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("ROLLBACK")
    except Exception:
        pass


def scalar_count(conn: sqlite3.Connection, table_name: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
