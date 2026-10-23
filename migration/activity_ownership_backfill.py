from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


SAFE_TO_BACKFILL = "SAFE_TO_BACKFILL"
ALREADY_CORRECT = "ALREADY_CORRECT"
AMBIGUOUS_PROJECT = "AMBIGUOUS_PROJECT"
ORPHAN_PROJECT = "ORPHAN_PROJECT"
CONFLICTING_OWNERSHIP = "CONFLICTING_OWNERSHIP"
INVALID_ACTIVITY = "INVALID_ACTIVITY"

CLASSIFICATIONS = (
    SAFE_TO_BACKFILL,
    ALREADY_CORRECT,
    AMBIGUOUS_PROJECT,
    ORPHAN_PROJECT,
    CONFLICTING_OWNERSHIP,
    INVALID_ACTIVITY,
)


class ActivityOwnershipBackfillError(RuntimeError):
    pass


@dataclass(frozen=True)
class ActivityOwnershipBackfillPlan:
    source_snapshot: Dict[str, Any]
    proposed_snapshot: Dict[str, Any]
    report: Dict[str, Any]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ActivityOwnershipBackfillError(message)


def build_activity_ownership_backfill_plan(snapshot: Dict[str, Any]) -> ActivityOwnershipBackfillPlan:
    source = copy.deepcopy(snapshot)
    proposed = copy.deepcopy(snapshot)
    organizations = {
        _text(item.get("id"))
        for item in (source.get("organizations") or [])
        if isinstance(item, dict) and _text(item.get("id"))
    }
    projects_by_id: Dict[str, List[Dict[str, Any]]] = {}
    for project in source.get("projects") or []:
        if not isinstance(project, dict):
            continue
        project_id = _text(project.get("id"))
        if project_id:
            projects_by_id.setdefault(project_id, []).append(project)

    results: List[Dict[str, Any]] = []
    proposed_locations: Dict[tuple[str, int], Dict[str, Any]] = {}
    for project_id, ops in (source.get("ops_by_project") or {}).items():
        normalized_project_id = _text(project_id)
        activities = (ops or {}).get("activities") if isinstance(ops, dict) else None
        if not isinstance(activities, list):
            continue
        project_matches = projects_by_id.get(normalized_project_id, [])
        for index, activity in enumerate(activities):
            activity_id = _text(activity.get("id")) if isinstance(activity, dict) else ""
            result = {
                "project_id": normalized_project_id,
                "activity_id": activity_id,
                "activity_index": index,
                "classification": "",
                "reasons": [],
                "current_organization_id": "",
                "proposed_organization_id": "",
            }
            if not isinstance(activity, dict):
                result["classification"] = INVALID_ACTIVITY
                result["reasons"] = ["ACTIVITY_IS_NOT_AN_OBJECT"]
            elif not project_matches:
                result["classification"] = ORPHAN_PROJECT
                result["reasons"] = ["OPS_PROJECT_NOT_FOUND"]
            elif len(project_matches) != 1:
                result["classification"] = AMBIGUOUS_PROJECT
                result["reasons"] = ["PROJECT_ID_NOT_UNIQUE"]
            else:
                project_organization_id = _text(project_matches[0].get("organization_id"))
                current_organization_id = _text(activity.get("organization_id"))
                result["current_organization_id"] = current_organization_id
                if not project_organization_id:
                    result["classification"] = ORPHAN_PROJECT
                    result["reasons"] = ["PROJECT_ORGANIZATION_MISSING"]
                elif project_organization_id not in organizations:
                    result["classification"] = ORPHAN_PROJECT
                    result["reasons"] = ["PROJECT_ORGANIZATION_NOT_FOUND"]
                elif not current_organization_id:
                    result["classification"] = SAFE_TO_BACKFILL
                    result["reasons"] = ["OWNERSHIP_DERIVED_FROM_UNIQUE_PROJECT"]
                    result["proposed_organization_id"] = project_organization_id
                    proposed_locations[(normalized_project_id, index)] = result
                elif current_organization_id == project_organization_id:
                    result["classification"] = ALREADY_CORRECT
                    result["reasons"] = ["OWNERSHIP_MATCHES_PROJECT"]
                else:
                    result["classification"] = CONFLICTING_OWNERSHIP
                    result["reasons"] = ["ACTIVITY_PROJECT_OWNERSHIP_CONFLICT"]
                    result["proposed_organization_id"] = project_organization_id
            results.append(result)

    for project_id, ops in (proposed.get("ops_by_project") or {}).items():
        activities = (ops or {}).get("activities") if isinstance(ops, dict) else None
        if not isinstance(activities, list):
            continue
        for index, activity in enumerate(activities):
            result = proposed_locations.get((_text(project_id), index))
            if result is not None and isinstance(activity, dict):
                activity["organization_id"] = result["proposed_organization_id"]

    counts = {
        classification: sum(1 for item in results if item["classification"] == classification)
        for classification in CLASSIFICATIONS
    }
    report = {
        "mode": "dry-run",
        "total_activities": len(results),
        "counts": counts,
        "safe_activity_ids": [
            item["activity_id"] for item in results if item["classification"] == SAFE_TO_BACKFILL
        ],
        "activities": results,
        "canonical_mutated": False,
        "projection_mutated": False,
    }
    return ActivityOwnershipBackfillPlan(source, proposed, report)


def run_activity_ownership_backfill(
    load_source_bytes: Callable[[], bytes],
    apply: bool = False,
    expected_source_sha256: str = "",
    approval_reference: str = "",
    server_stopped_confirmed: bool = False,
    backup_path: str = "",
    write_backup: Optional[Callable[[str, bytes], None]] = None,
    read_backup: Optional[Callable[[str], bytes]] = None,
    save_snapshot: Optional[Callable[[Dict[str, Any]], None]] = None,
    rebuild_projection: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    source_bytes = load_source_bytes()
    source_sha256 = _sha256(source_bytes)
    try:
        snapshot = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ActivityOwnershipBackfillError("Canonical snapshot is not valid UTF-8 JSON.") from exc

    plan = build_activity_ownership_backfill_plan(snapshot)
    result = copy.deepcopy(plan.report)
    result["source_sha256"] = source_sha256
    if not apply:
        return result

    _require(bool(approval_reference.strip()), "Apply requires an approved migration reference.")
    _require(server_stopped_confirmed, "Apply requires explicit confirmation that the server is stopped.")
    _require(bool(expected_source_sha256), "Apply requires the SHA-256 from a reviewed dry-run.")
    _require(source_sha256 == expected_source_sha256, "Canonical snapshot changed since the reviewed dry-run.")
    _require(bool(backup_path), "Apply requires an explicit timestamped backup path.")
    _require(write_backup is not None and read_backup is not None, "Apply requires verified backup callbacks.")
    _require(save_snapshot is not None, "Apply requires an atomic canonical save callback.")
    _require(rebuild_projection is not None, "Apply requires a derived projection rebuild callback.")

    safe_ids = result["safe_activity_ids"]
    if not safe_ids:
        result.update({
            "mode": "apply",
            "approval_reference": approval_reference,
            "changed_activity_ids": [],
            "backup_created": False,
        })
        return result

    write_backup(backup_path, source_bytes)
    backup_bytes = read_backup(backup_path)
    _require(backup_bytes == source_bytes, "Canonical backup is not byte-for-byte identical.")
    _require(_sha256(backup_bytes) == source_sha256, "Canonical backup SHA-256 verification failed.")

    save_snapshot(copy.deepcopy(plan.proposed_snapshot))
    result.update({
        "mode": "apply",
        "approval_reference": approval_reference,
        "backup_created": True,
        "backup_path": backup_path,
        "backup_sha256": source_sha256,
        "changed_activity_ids": safe_ids,
        "canonical_mutated": True,
    })
    try:
        result["projection"] = rebuild_projection(copy.deepcopy(plan.proposed_snapshot))
        result["projection_mutated"] = True
        result["projection_error"] = ""
    except Exception as exc:
        result["projection_mutated"] = False
        result["projection_error"] = str(exc)
    return result
