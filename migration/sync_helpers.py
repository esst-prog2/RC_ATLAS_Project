from __future__ import annotations

import copy
import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from logitrack_platform.relational_store import get_relational_store_path, get_relational_store_status
from repositories.notification_rules import list_notification_rules, replace_all_notification_rules
from repositories.reporting_records import list_reporting_records, replace_all_reporting_records
from repositories.users import list_users, replace_all_users


LOGGER = logging.getLogger("logitrack.migration.sync")
SUPPORTED_REPOSITORY_DOMAINS = ("users", "notification_rules", "reporting_records")


def repository_domains_enabled() -> bool:
    raw = os.getenv("LOGITRACK_ENABLE_REPOSITORY_DOMAINS")
    if raw is None:
        return True
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def selected_repository_domains(domains: Optional[Sequence[str]] = None) -> List[str]:
    if domains is not None:
        requested = [str(item).strip().lower() for item in domains if str(item).strip()]
    else:
        raw = (os.getenv("LOGITRACK_REPOSITORY_DOMAINS", ",".join(SUPPORTED_REPOSITORY_DOMAINS)) or "").strip()
        requested = [item.strip().lower() for item in raw.split(",") if item.strip()]
    result = []
    seen: Set[str] = set()
    for item in requested:
        if item in SUPPORTED_REPOSITORY_DOMAINS and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def sync_repository_backed_domains_from_snapshot(
    snapshot: Dict[str, Any],
    db_path: Optional[str] = None,
    domains: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    active_domains = selected_repository_domains(domains)
    target_path = db_path or get_relational_store_path()
    summary: Dict[str, Any] = {
        "enabled": repository_domains_enabled(),
        "db_path": target_path,
        "domains": active_domains,
        "results": {},
    }
    if not summary["enabled"]:
        return summary

    if "users" in active_domains:
        result = replace_all_users(snapshot.get("users", []) or [], db_path=target_path)
        summary["results"]["users"] = result
    if "notification_rules" in active_domains:
        result = replace_all_notification_rules(snapshot.get("notification_rules", []) or [], db_path=target_path)
        summary["results"]["notification_rules"] = result
    if "reporting_records" in active_domains:
        result = replace_all_reporting_records(snapshot.get("reporting_records", []) or [], db_path=target_path)
        summary["results"]["reporting_records"] = result
    LOGGER.info("Synchronized repository-backed domains", extra={"summary": summary})
    return summary


def hydrate_snapshot_with_repository_domains(
    snapshot: Dict[str, Any],
    db_path: Optional[str] = None,
    domains: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    active_domains = selected_repository_domains(domains)
    target_path = db_path or get_relational_store_path()
    if not repository_domains_enabled():
        return snapshot

    store_status = get_relational_store_status(target_path)
    domain_counts = store_status.get("counts", {})
    repo_ready = bool(store_status.get("last_sync")) or any(
        int(domain_counts.get(domain, 0) or 0) > 0 for domain in active_domains
    )
    if not store_status.get("exists") or not repo_ready:
        return snapshot

    hydrated = copy.deepcopy(snapshot)
    if "users" in active_domains:
        hydrated["users"] = list_users(db_path=target_path)
    if "notification_rules" in active_domains:
        hydrated["notification_rules"] = list_notification_rules(db_path=target_path)
    if "reporting_records" in active_domains:
        hydrated["reporting_records"] = list_reporting_records(db_path=target_path)
    return hydrated


def safe_get_repository_sync_status(db_path: Optional[str] = None, domains: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    target_path = db_path or get_relational_store_path()
    active_domains = selected_repository_domains(domains)
    try:
        store_status = get_relational_store_status(target_path)
        return {
            "enabled": repository_domains_enabled(),
            "db_path": target_path,
            "domains": active_domains,
            "store_exists": store_status.get("exists", False),
            "store_last_sync": (store_status.get("last_sync") or {}).get("synced_at", ""),
            "counts": {
                "users": store_status.get("counts", {}).get("users", 0),
                "notification_rules": store_status.get("counts", {}).get("notification_rules", 0),
                "reporting_records": store_status.get("counts", {}).get("reporting_records", 0),
            },
        }
    except Exception as exc:
        LOGGER.exception("Failed to inspect repository sync status")
        return {
            "enabled": repository_domains_enabled(),
            "db_path": target_path,
            "domains": active_domains,
            "error": str(exc),
        }
