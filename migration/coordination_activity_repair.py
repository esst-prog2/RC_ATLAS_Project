from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence


class CoordinationActivityRepairError(RuntimeError):
    pass


@dataclass(frozen=True)
class CoordinationActivityRepairConfig:
    organization_id: str
    project_id: str
    activity_id: str
    expected_activity_count: int
    expected_task_count: int
    expected_task_ids: Sequence[str]


@dataclass(frozen=True)
class CoordinationActivityRepairPlan:
    repaired_snapshot: Dict[str, Any]
    report: Dict[str, Any]


def _activities(snapshot: Dict[str, Any]):
    for project_id, ops in (snapshot.get("ops_by_project") or {}).items():
        for index, activity in enumerate((ops or {}).get("activities") or []):
            yield project_id, index, activity


def _tasks(snapshot: Dict[str, Any]):
    for project_id, _, activity in _activities(snapshot):
        for task in activity.get("tasks") or []:
            yield project_id, activity, task


def _stable_unique(values: Sequence[Any]) -> List[Any]:
    result: List[Any] = []
    seen = set()
    for value in values:
        marker = json.dumps(value, sort_keys=True, default=str)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(copy.deepcopy(value))
    return result


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CoordinationActivityRepairError(message)


def _inventory(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    activities = list(_activities(snapshot))
    tasks = list(_tasks(snapshot))
    return {
        "activity_count": len(activities),
        "task_count": len(tasks),
        "activity_ids": [str(activity.get("id") or "") for _, _, activity in activities],
        "task_ids": [str(task.get("id") or "") for _, _, task in tasks],
    }


def build_coordination_activity_repair_plan(
    snapshot: Dict[str, Any],
    config: CoordinationActivityRepairConfig,
) -> CoordinationActivityRepairPlan:
    source = copy.deepcopy(snapshot)
    staged = copy.deepcopy(snapshot)
    before = _inventory(source)
    _require(before["activity_count"] == config.expected_activity_count, "Unexpected pre-repair activity count.")
    _require(before["task_count"] == config.expected_task_count, "Unexpected pre-repair task count.")
    _require(len(before["task_ids"]) == len(set(before["task_ids"])), "Task IDs are not unique before repair.")

    projects = [item for item in staged.get("projects", []) if str(item.get("id") or "") == config.project_id]
    _require(len(projects) == 1, "The target project was not found exactly once.")
    _require(
        str(projects[0].get("organization_id") or "") == config.organization_id,
        "The target project does not belong to the expected organization.",
    )
    target_ops = (staged.get("ops_by_project") or {}).get(config.project_id)
    _require(isinstance(target_ops, dict), "The target project has no operations container.")
    target_activities = target_ops.get("activities")
    _require(isinstance(target_activities, list), "The target operations container is malformed.")

    occurrences = [
        (project_id, index, activity)
        for project_id, index, activity in _activities(staged)
        if str(activity.get("id") or "") == config.activity_id
    ]
    _require(len(occurrences) == 2, "The expected duplicate coordination activity was not found exactly twice.")
    _require(
        all(project_id == config.project_id for project_id, _, _ in occurrences),
        "The duplicate activity ID occurs outside the expected project.",
    )
    for _, _, activity in occurrences:
        _require(
            str(activity.get("organization_id") or "") == config.organization_id,
            "A duplicate activity has unexpected organization ownership.",
        )
        _require(isinstance(activity.get("tasks"), list), "A duplicate activity has malformed tasks.")
        _require(
            isinstance(activity.get("linked_indicator_ids"), list),
            "A duplicate activity has malformed indicator links.",
        )

    expected_task_ids = {str(item) for item in config.expected_task_ids}
    duplicate_task_ids = {
        str(task.get("id") or "")
        for _, _, activity in occurrences
        for task in activity.get("tasks") or []
    }
    _require(expected_task_ids.issubset(duplicate_task_ids), "Expected browser-created tasks are not in the duplicate activities.")

    retained_index = occurrences[0][1]
    redundant_index = occurrences[1][1]
    retained = target_activities[retained_index]
    redundant = target_activities[redundant_index]
    moved_task_ids = [str(task.get("id") or "") for task in redundant.get("tasks") or []]
    retained["tasks"] = list(retained.get("tasks") or []) + list(redundant.get("tasks") or [])
    retained["linked_indicator_ids"] = _stable_unique(
        list(retained.get("linked_indicator_ids") or []) + list(redundant.get("linked_indicator_ids") or [])
    )
    target_activities.pop(redundant_index)

    after = _inventory(staged)
    _require(after["activity_count"] == config.expected_activity_count - 1, "Unexpected post-repair activity count.")
    _require(after["task_count"] == config.expected_task_count, "Task count changed during repair planning.")
    _require(len(after["activity_ids"]) == len(set(after["activity_ids"])), "Activity IDs remain duplicated after repair planning.")
    _require(len(after["task_ids"]) == len(set(after["task_ids"])), "Task IDs are not unique after repair planning.")
    _require(after["activity_ids"].count(config.activity_id) == 1, "The coordination activity is not unique after repair planning.")
    _require(expected_task_ids.issubset(set(after["task_ids"])), "Expected browser-created tasks were not preserved.")

    source_tasks = {str(task.get("id") or ""): task for _, _, task in _tasks(source)}
    repaired_tasks = {str(task.get("id") or ""): task for _, _, task in _tasks(staged)}
    _require(source_tasks == repaired_tasks, "One or more task fields changed during repair planning.")

    report = {
        "mode": "dry-run",
        "organization_id": config.organization_id,
        "project_id": config.project_id,
        "activity_id": config.activity_id,
        "activities_before": before["activity_count"],
        "activities_after": after["activity_count"],
        "tasks_before": before["task_count"],
        "tasks_after": after["task_count"],
        "retained_activity_index": retained_index,
        "removed_activity_index": redundant_index,
        "moved_task_ids": moved_task_ids,
        "preserved_task_ids": sorted(expected_task_ids),
        "linked_indicator_ids_after": list(retained.get("linked_indicator_ids") or []),
        "canonical_mutated": False,
        "projection_mutated": False,
    }
    return CoordinationActivityRepairPlan(repaired_snapshot=staged, report=report)


def run_coordination_activity_repair(
    config: CoordinationActivityRepairConfig,
    load_snapshot: Callable[[], Dict[str, Any]],
    rehearse_projection: Callable[[Dict[str, Any]], Dict[str, Any]],
    backup_path: str,
    apply: bool = False,
    server_stopped_confirmed: bool = False,
    write_backup: Optional[Callable[[str], None]] = None,
    save_canonical: Optional[Callable[[Dict[str, Any]], None]] = None,
    rebuild_projection: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    source = load_snapshot()
    plan = build_coordination_activity_repair_plan(source, config)
    result = copy.deepcopy(plan.report)
    result["backup_path"] = backup_path
    if not apply:
        result["rehearsal"] = rehearse_projection(copy.deepcopy(plan.repaired_snapshot))
        return result

    _require(server_stopped_confirmed, "Apply requires explicit confirmation that the local server is stopped.")
    _require(bool(backup_path), "Apply requires an explicit timestamped backup path.")
    _require(write_backup is not None, "Apply requires a canonical backup writer.")
    _require(save_canonical is not None, "Apply requires a canonical save callback.")
    _require(rebuild_projection is not None, "Apply requires a projection rebuild callback.")
    write_backup(backup_path)
    result["backup_created"] = True
    result["rehearsal"] = rehearse_projection(copy.deepcopy(plan.repaired_snapshot))
    save_canonical(copy.deepcopy(plan.repaired_snapshot))
    result["canonical_mutated"] = True
    result["mode"] = "apply"
    try:
        result["projection"] = rebuild_projection(copy.deepcopy(plan.repaired_snapshot))
        result["projection_mutated"] = True
        result["projection_error"] = ""
    except Exception as exc:
        result["projection_mutated"] = False
        result["projection_error"] = str(exc)
    return result


def _load_application_module():
    module_path = Path(__file__).resolve().parents[1] / "LogiTrackRC v4.4.py"
    spec = importlib.util.spec_from_file_location("logitrack_coordination_activity_repair", module_path)
    if spec is None or spec.loader is None:
        raise CoordinationActivityRepairError(f"Unable to load application module from {module_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _timestamped_backup_path(target: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return target.with_name(f"{target.name}.{stamp}.browser-reliability.bak")


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair the approved duplicate coordination activity in an offline workspace.")
    parser.add_argument("--data-path")
    parser.add_argument("--organization-id", default="org_blue_delta")
    parser.add_argument("--project-id", default="proj_resilience")
    parser.add_argument("--activity-id", default="act_proj_resilience_coordination")
    parser.add_argument("--expected-activities", type=int, default=11)
    parser.add_argument("--expected-tasks", type=int, default=20)
    parser.add_argument(
        "--expected-task-id",
        action="append",
        default=["task_proj_resilience_test", "task_proj_resilience_test2"],
    )
    parser.add_argument("--backup-path")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-server-stopped", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    module = _load_application_module()
    backend = module.get_storage_backend()
    target = Path(module.get_storage_target_path(args.data_path, backend=backend)).resolve()
    backup_path = Path(args.backup_path).resolve() if args.backup_path else _timestamped_backup_path(target)
    config = CoordinationActivityRepairConfig(
        organization_id=args.organization_id,
        project_id=args.project_id,
        activity_id=args.activity_id,
        expected_activity_count=args.expected_activities,
        expected_task_count=args.expected_tasks,
        expected_task_ids=tuple(args.expected_task_id),
    )

    def load_snapshot() -> Dict[str, Any]:
        data = module.load_sqlite(str(target)) if backend == "sqlite" else module.load_json(str(target))
        return module.to_serializable(data)

    def rehearse_projection(snapshot: Dict[str, Any]) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            rehearsal_path = str(Path(tmp_dir) / "projection.sqlite3")
            return module.sync_snapshot_to_relational_store(
                snapshot,
                db_path=rehearsal_path,
                source_backend=backend,
                source_path=str(target),
            )

    def write_backup(destination: str) -> None:
        destination_path = Path(destination)
        _require(not destination_path.exists(), "The requested backup path already exists.")
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, destination_path)
        _require(target.read_bytes() == destination_path.read_bytes(), "The canonical backup is not byte-for-byte identical.")

    def save_canonical(snapshot: Dict[str, Any]) -> None:
        module.save_canonical_data_to_path(module.from_serializable(snapshot), str(target))

    def rebuild_projection(snapshot: Dict[str, Any]) -> Dict[str, Any]:
        projection = module.sync_snapshot_to_relational_store(
            snapshot,
            db_path=module.get_relational_store_path(str(target)),
            source_backend=backend,
            source_path=str(target),
        )
        repository = module.sync_repository_backed_domains_from_snapshot(
            snapshot,
            db_path=module.get_relational_store_path(str(target)),
        )
        return {"relational": projection, "repository": repository}

    result = run_coordination_activity_repair(
        config=config,
        load_snapshot=load_snapshot,
        rehearse_projection=rehearse_projection,
        backup_path=str(backup_path),
        apply=args.apply,
        server_stopped_confirmed=args.confirm_server_stopped,
        write_backup=write_backup,
        save_canonical=save_canonical,
        rebuild_projection=rebuild_projection,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
