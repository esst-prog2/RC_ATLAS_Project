from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


SAFE_TO_BACKFILL = "SAFE_TO_BACKFILL"
AMBIGUOUS = "AMBIGUOUS"
UNRESOLVED = "UNRESOLVED"
ALREADY_CANONICAL = "ALREADY_CANONICAL"
INVALID_EXISTING_ROUTING = "INVALID_EXISTING_ROUTING"

CLASSIFICATIONS = (
    ALREADY_CANONICAL,
    SAFE_TO_BACKFILL,
    AMBIGUOUS,
    UNRESOLVED,
    INVALID_EXISTING_ROUTING,
)
REVIEW_MODES = {
    "direct_completion",
    "validation",
    "approval",
    "validation_and_approval",
}
REVIEW_STAGES = {"execution", "validation", "approval", "complete"}
OPEN_STATUSES = {"not_started", "in_progress", "overdue", "escalated"}
ROUTING_FIELDS = (
    "assignee_user_id",
    "review_mode",
    "validator_user_id",
    "approver_user_id",
    "evidence_required",
    "review_stage",
)


class TaskWorkflowBackfillError(RuntimeError):
    pass


@dataclass(frozen=True)
class TaskWorkflowBackfillPlan:
    source_snapshot: Dict[str, Any]
    proposed_snapshot: Dict[str, Any]
    report: Dict[str, Any]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _text(value).lower()


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TaskWorkflowBackfillError(message)


def _field_missing(record: Dict[str, Any], field: str) -> bool:
    if field not in record or record.get(field) is None:
        return True
    if field != "evidence_required" and not _text(record.get(field)):
        return True
    return False


def _active_project_members(snapshot: Dict[str, Any], project: Dict[str, Any]) -> List[Dict[str, Any]]:
    project_id = _text(project.get("id"))
    organization_id = _text(project.get("organization_id"))
    active_ids = {
        _text(assignment.get("user_id"))
        for assignment in (project.get("team_assignments") or [])
        if isinstance(assignment, dict)
        and _text(assignment.get("project_id")) == project_id
        and _text(assignment.get("organization_id")) == organization_id
        and _lower(assignment.get("status") or "active") == "active"
        and _text(assignment.get("user_id"))
    }
    return [
        user
        for user in (snapshot.get("users") or [])
        if isinstance(user, dict)
        and _text(user.get("id")) in active_ids
        and _text(user.get("organization_id")) == organization_id
        and bool(user.get("is_active", True))
        and _lower(user.get("status") or "active") == "active"
    ]


def _has_permission(
    user: Dict[str, Any],
    permission: str,
    permission_resolver: Callable[[Dict[str, Any]], Iterable[str]],
) -> bool:
    return permission in {_text(item) for item in permission_resolver(user) if _text(item)}


def _existing_member_by_id(
    members: Sequence[Dict[str, Any]],
    user_id: str,
) -> Optional[Dict[str, Any]]:
    matches = [user for user in members if _text(user.get("id")) == user_id]
    return matches[0] if len(matches) == 1 else None


def _result(
    task_id: str,
    project_id: str,
    activity_id: str,
    classification: str,
    reasons: Sequence[str],
    proposed_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "task_id": task_id,
        "project_id": project_id,
        "activity_id": activity_id,
        "classification": classification,
        "reason_codes": list(dict.fromkeys(reasons)),
        "proposed_fields": copy.deepcopy(proposed_fields or {}),
    }


def _derive_review_stage(task: Dict[str, Any], review_mode: str) -> Tuple[Optional[str], List[str]]:
    status = _lower(task.get("status") or "not_started").replace("-", "_").replace(" ", "_")
    submitted = bool(_text(task.get("submitted_at")))
    validated = bool(_text(task.get("validated_at")))
    approved = bool(_text(task.get("approved_at")))

    if status in OPEN_STATUSES:
        if submitted or validated or approved:
            return None, ["OPEN_STATUS_HAS_REVIEW_TIMESTAMPS"]
        stage = "execution"
    elif status == "pending_validation":
        if not submitted or approved:
            return None, ["PENDING_REVIEW_TIMESTAMPS_CONTRADICT_STATUS"]
        if review_mode == "direct_completion":
            return None, ["DIRECT_COMPLETION_CANNOT_BE_PENDING_REVIEW"]
        if review_mode == "approval":
            if validated:
                return None, ["APPROVAL_ONLY_HAS_VALIDATION_TIMESTAMP"]
            stage = "approval"
        elif review_mode == "validation":
            if validated:
                return None, ["VALIDATION_ONLY_SHOULD_COMPLETE_AFTER_VALIDATION"]
            stage = "validation"
        else:
            stage = "approval" if validated else "validation"
    elif status == "completed":
        expected = {
            "direct_completion": (False, False, False),
            "validation": (True, True, False),
            "approval": (True, False, True),
            "validation_and_approval": (True, True, True),
        }[review_mode]
        if (submitted, validated, approved) != expected:
            return None, ["COMPLETED_TIMESTAMPS_CONTRADICT_REVIEW_MODE"]
        stage = "complete"
    else:
        return None, ["UNSUPPORTED_TASK_STATUS"]

    raw_stage = _lower(task.get("review_stage"))
    if raw_stage and raw_stage not in REVIEW_STAGES:
        return None, ["UNKNOWN_REVIEW_STAGE"]
    if raw_stage and raw_stage != stage:
        return None, ["REVIEW_STAGE_CONTRADICTS_STATUS"]
    return stage, []


def _classify_task(
    snapshot: Dict[str, Any],
    project: Dict[str, Any],
    activity: Dict[str, Any],
    task: Dict[str, Any],
    permission_resolver: Callable[[Dict[str, Any]], Iterable[str]],
) -> Dict[str, Any]:
    task_id = _text(task.get("id"))
    project_id = _text(project.get("id"))
    activity_id = _text(activity.get("id"))
    members = _active_project_members(snapshot, project)
    proposed: Dict[str, Any] = {}

    raw_mode = _lower(task.get("review_mode"))
    review_mode = raw_mode or "validation_and_approval"
    if review_mode not in REVIEW_MODES:
        return _result(task_id, project_id, activity_id, INVALID_EXISTING_ROUTING, ["UNKNOWN_REVIEW_MODE"])
    if not raw_mode:
        proposed["review_mode"] = review_mode

    raw_evidence = task.get("evidence_required")
    if _field_missing(task, "evidence_required"):
        evidence_required = False
        proposed["evidence_required"] = False
    elif not isinstance(raw_evidence, bool):
        return _result(task_id, project_id, activity_id, INVALID_EXISTING_ROUTING, ["EVIDENCE_REQUIRED_NOT_BOOLEAN"])
    else:
        evidence_required = raw_evidence

    assignee_id = _text(task.get("assignee_user_id"))
    if assignee_id:
        assignee = _existing_member_by_id(members, assignee_id)
        if assignee is None:
            return _result(task_id, project_id, activity_id, INVALID_EXISTING_ROUTING, ["CANONICAL_ASSIGNEE_NOT_ACTIVE_PROJECT_MEMBER"])
    else:
        username = _lower(task.get("assignee_username"))
        matches = [user for user in members if username and _lower(user.get("username")) == username]
        if not matches:
            return _result(task_id, project_id, activity_id, UNRESOLVED, ["ASSIGNEE_USERNAME_NOT_RESOLVED"])
        if len(matches) > 1:
            return _result(task_id, project_id, activity_id, AMBIGUOUS, ["ASSIGNEE_USERNAME_AMBIGUOUS"])
        assignee = matches[0]
        assignee_id = _text(assignee.get("id"))
        proposed["assignee_user_id"] = assignee_id

    if not _has_permission(assignee, "UPDATE_TASK_PROGRESS", permission_resolver):
        reason = "CANONICAL_ASSIGNEE_LACKS_EXECUTION_CAPABILITY" if _text(task.get("assignee_user_id")) else "RESOLVED_ASSIGNEE_LACKS_EXECUTION_CAPABILITY"
        category = INVALID_EXISTING_ROUTING if _text(task.get("assignee_user_id")) else UNRESOLVED
        return _result(task_id, project_id, activity_id, category, [reason])
    if evidence_required and not _has_permission(assignee, "SUBMIT_EVIDENCE", permission_resolver):
        return _result(task_id, project_id, activity_id, INVALID_EXISTING_ROUTING, ["ASSIGNEE_LACKS_REQUIRED_EVIDENCE_CAPABILITY"])

    needs_validator = review_mode in {"validation", "validation_and_approval"}
    needs_approver = review_mode in {"approval", "validation_and_approval"}
    validator_id = _text(task.get("validator_user_id"))
    approver_id = _text(task.get("approver_user_id"))

    if not needs_validator and validator_id:
        return _result(task_id, project_id, activity_id, INVALID_EXISTING_ROUTING, ["INAPPLICABLE_VALIDATOR_PRESENT"])
    if not needs_approver and approver_id:
        return _result(task_id, project_id, activity_id, INVALID_EXISTING_ROUTING, ["INAPPLICABLE_APPROVER_PRESENT"])

    validator = None
    if validator_id:
        validator = _existing_member_by_id(members, validator_id)
        if validator is None or not _has_permission(validator, "VALIDATE_EVIDENCE", permission_resolver):
            return _result(task_id, project_id, activity_id, INVALID_EXISTING_ROUTING, ["CANONICAL_VALIDATOR_NOT_ELIGIBLE"])
        if validator_id == assignee_id:
            return _result(task_id, project_id, activity_id, INVALID_EXISTING_ROUTING, ["ASSIGNEE_IS_VALIDATOR"])

    approver = None
    if approver_id:
        approver = _existing_member_by_id(members, approver_id)
        if approver is None or not _has_permission(approver, "APPROVE_TASKS", permission_resolver):
            return _result(task_id, project_id, activity_id, INVALID_EXISTING_ROUTING, ["CANONICAL_APPROVER_NOT_ELIGIBLE"])
        if approver_id == assignee_id:
            return _result(task_id, project_id, activity_id, INVALID_EXISTING_ROUTING, ["ASSIGNEE_IS_APPROVER"])

    if validator_id and approver_id and validator_id == approver_id:
        return _result(task_id, project_id, activity_id, INVALID_EXISTING_ROUTING, ["VALIDATOR_EQUALS_APPROVER"])

    validator_candidates = [
        user for user in members
        if _text(user.get("id")) != assignee_id
        and _has_permission(user, "VALIDATE_EVIDENCE", permission_resolver)
    ]
    approver_candidates = [
        user for user in members
        if _text(user.get("id")) != assignee_id
        and _has_permission(user, "APPROVE_TASKS", permission_resolver)
    ]
    possible_validators = [validator] if validator is not None else validator_candidates if needs_validator else [None]
    possible_approvers = [approver] if approver is not None else approver_candidates if needs_approver else [None]
    pairs = [
        (candidate_validator, candidate_approver)
        for candidate_validator in possible_validators
        for candidate_approver in possible_approvers
        if candidate_validator is None
        or candidate_approver is None
        or _text(candidate_validator.get("id")) != _text(candidate_approver.get("id"))
    ]
    if (needs_validator and not possible_validators) or (needs_approver and not possible_approvers) or not pairs:
        reasons = []
        if needs_validator and not possible_validators:
            reasons.append("VALIDATOR_NOT_RESOLVED")
        if needs_approver and not possible_approvers:
            reasons.append("APPROVER_NOT_RESOLVED")
        if not pairs:
            reasons.append("NO_SEPARATED_REVIEWER_ROUTE")
        return _result(task_id, project_id, activity_id, UNRESOLVED, reasons)
    if len(pairs) > 1:
        reasons = []
        if needs_validator and not validator_id:
            reasons.append("VALIDATOR_AMBIGUOUS")
        if needs_approver and not approver_id:
            reasons.append("APPROVER_AMBIGUOUS")
        return _result(task_id, project_id, activity_id, AMBIGUOUS, reasons or ["REVIEW_ROUTE_AMBIGUOUS"])

    resolved_validator, resolved_approver = pairs[0]
    if needs_validator and not validator_id:
        validator_id = _text(resolved_validator.get("id"))
        proposed["validator_user_id"] = validator_id
    elif not needs_validator and "validator_user_id" not in task:
        proposed["validator_user_id"] = ""
    if needs_approver and not approver_id:
        approver_id = _text(resolved_approver.get("id"))
        proposed["approver_user_id"] = approver_id
    elif not needs_approver and "approver_user_id" not in task:
        proposed["approver_user_id"] = ""

    review_stage, stage_reasons = _derive_review_stage(task, review_mode)
    if stage_reasons:
        return _result(task_id, project_id, activity_id, INVALID_EXISTING_ROUTING, stage_reasons)
    if _field_missing(task, "review_stage"):
        proposed["review_stage"] = review_stage

    fields_complete = all(field in task and task.get(field) is not None for field in ROUTING_FIELDS)
    if fields_complete and not proposed:
        return _result(task_id, project_id, activity_id, ALREADY_CANONICAL, ["ROUTING_ALREADY_CANONICAL"])
    return _result(task_id, project_id, activity_id, SAFE_TO_BACKFILL, ["ROUTING_UNIQUELY_RESOLVED"], proposed)


def build_task_workflow_backfill_plan(
    snapshot: Dict[str, Any],
    permission_resolver: Callable[[Dict[str, Any]], Iterable[str]],
) -> TaskWorkflowBackfillPlan:
    source = copy.deepcopy(snapshot)
    proposed_snapshot = copy.deepcopy(snapshot)
    projects = {
        _text(project.get("id")): project
        for project in (source.get("projects") or [])
        if isinstance(project, dict) and _text(project.get("id"))
    }
    results: List[Dict[str, Any]] = []
    task_locations: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for project_id, ops in (source.get("ops_by_project") or {}).items():
        project = projects.get(_text(project_id))
        for activity in ((ops or {}).get("activities") or []):
            if not isinstance(activity, dict):
                continue
            for task in (activity.get("tasks") or []):
                if not isinstance(task, dict):
                    continue
                if project is None:
                    result = _result(
                        _text(task.get("id")),
                        _text(project_id),
                        _text(activity.get("id")),
                        UNRESOLVED,
                        ["PROJECT_NOT_RESOLVED"],
                    )
                else:
                    result = _classify_task(source, project, activity, task, permission_resolver)
                results.append(result)
                task_locations[(_text(project_id), _text(activity.get("id")), _text(task.get("id")))] = result

    for project_id, ops in (proposed_snapshot.get("ops_by_project") or {}).items():
        for activity in ((ops or {}).get("activities") or []):
            for task in (activity.get("tasks") or []):
                key = (_text(project_id), _text(activity.get("id")), _text(task.get("id")))
                result = task_locations.get(key)
                if result and result["classification"] == SAFE_TO_BACKFILL:
                    task.update(copy.deepcopy(result["proposed_fields"]))

    categories = {
        classification: [item for item in results if item["classification"] == classification]
        for classification in CLASSIFICATIONS
    }
    report = {
        "mode": "dry-run",
        "total_tasks": len(results),
        "counts": {classification: len(categories[classification]) for classification in CLASSIFICATIONS},
        "task_ids": {
            classification: [item["task_id"] for item in categories[classification]]
            for classification in CLASSIFICATIONS
        },
        "tasks": results,
        "canonical_mutated": False,
        "projection_mutated": False,
    }
    return TaskWorkflowBackfillPlan(source, proposed_snapshot, report)


def run_task_workflow_backfill(
    load_source_bytes: Callable[[], bytes],
    permission_resolver: Callable[[Dict[str, Any]], Iterable[str]],
    apply: bool = False,
    expected_source_sha256: str = "",
    backup_path: str = "",
    server_stopped_confirmed: bool = False,
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
        raise TaskWorkflowBackfillError("Canonical snapshot is not valid UTF-8 JSON.") from exc
    plan = build_task_workflow_backfill_plan(snapshot, permission_resolver)
    result = copy.deepcopy(plan.report)
    result["source_sha256"] = source_sha256

    if not apply:
        return result

    _require(server_stopped_confirmed, "Apply requires explicit confirmation that the server is stopped.")
    _require(bool(expected_source_sha256), "Apply requires the SHA-256 from a reviewed dry-run.")
    _require(source_sha256 == expected_source_sha256, "Canonical snapshot changed since the reviewed dry-run.")
    _require(bool(backup_path), "Apply requires a timestamped backup path.")
    _require(write_backup is not None and read_backup is not None, "Apply requires verified backup callbacks.")
    _require(save_snapshot is not None, "Apply requires an atomic canonical save callback.")
    _require(rebuild_projection is not None, "Apply requires a derived projection rebuild callback.")

    safe_tasks = result["task_ids"][SAFE_TO_BACKFILL]
    if not safe_tasks:
        result.update({"mode": "apply", "changed_task_ids": [], "backup_created": False})
        return result

    write_backup(backup_path, source_bytes)
    backup_bytes = read_backup(backup_path)
    backup_sha256 = _sha256(backup_bytes)
    _require(backup_bytes == source_bytes, "Canonical backup is not byte-for-byte identical.")
    _require(backup_sha256 == source_sha256, "Canonical backup SHA-256 verification failed.")

    save_snapshot(copy.deepcopy(plan.proposed_snapshot))
    result.update(
        {
            "mode": "apply",
            "backup_created": True,
            "backup_path": backup_path,
            "backup_sha256": backup_sha256,
            "changed_task_ids": safe_tasks,
            "canonical_mutated": True,
        }
    )
    try:
        result["projection"] = rebuild_projection(copy.deepcopy(plan.proposed_snapshot))
        result["projection_mutated"] = True
        result["projection_error"] = ""
    except Exception as exc:
        result["projection_mutated"] = False
        result["projection_error"] = str(exc)
    return result


def _load_application_module():
    module_path = Path(__file__).resolve().parents[1] / "LogiTrackRC v4.4.py"
    spec = importlib.util.spec_from_file_location("logitrack_task_workflow_backfill", module_path)
    if spec is None or spec.loader is None:
        raise TaskWorkflowBackfillError(f"Unable to load application module from {module_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _timestamped_backup_path(target: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return target.with_name(f"{target.name}.{stamp}.assignment-routing.bak")


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run or apply the guarded assignment-aware task routing backfill.")
    parser.add_argument("--data-path")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-source-sha256", default="")
    parser.add_argument("--backup-path")
    parser.add_argument("--confirm-server-stopped", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    module = _load_application_module()
    backend = module.get_storage_backend()
    _require(backend == "json", "Assignment routing backfill currently requires the canonical JSON backend.")
    target = Path(module.get_storage_target_path(args.data_path, backend=backend)).resolve()
    backup = Path(args.backup_path).resolve() if args.backup_path else _timestamped_backup_path(target)

    def permission_resolver(user: Dict[str, Any]) -> Iterable[str]:
        explicit = module.normalize_permission_ids(user.get("permissions", []) or [])
        return explicit or module.role_permissions(user.get("role"))

    def load_source_bytes() -> bytes:
        return target.read_bytes()

    def write_backup(destination: str, content: bytes) -> None:
        destination_path = Path(destination)
        _require(not destination_path.exists(), "The requested backup path already exists.")
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with open(destination_path, "xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

    def read_backup(source: str) -> bytes:
        return Path(source).read_bytes()

    def save_snapshot(snapshot: Dict[str, Any]) -> None:
        serialized = json.dumps(snapshot, ensure_ascii=False, indent=2)
        module._atomic_write_text(str(target), serialized)

    def rebuild_projection(snapshot: Dict[str, Any]) -> Dict[str, Any]:
        relational_path = module.get_relational_store_path(str(target))
        relational = module.sync_snapshot_to_relational_store(
            snapshot,
            db_path=relational_path,
            source_backend=backend,
            source_path=str(target),
        )
        repository = module.sync_repository_backed_domains_from_snapshot(snapshot, db_path=relational_path)
        return {"relational": relational, "repository": repository}

    result = run_task_workflow_backfill(
        load_source_bytes=load_source_bytes,
        permission_resolver=permission_resolver,
        apply=args.apply,
        expected_source_sha256=args.expected_source_sha256,
        backup_path=str(backup),
        server_stopped_confirmed=args.confirm_server_stopped,
        write_backup=write_backup,
        read_backup=read_backup,
        save_snapshot=save_snapshot,
        rebuild_projection=rebuild_projection,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
