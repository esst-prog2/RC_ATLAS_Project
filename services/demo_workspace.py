from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from .demo_seed import DemoSeedBundle, build_demo_seed_bundle
from .errors import ServiceError


UTC_DATETIME_MIN = datetime.min.replace(tzinfo=timezone.utc)
UTC_DATETIME_MAX = datetime.max.replace(tzinfo=timezone.utc)

TASK_STATUS_ORDER = {
    "not_started": 1,
    "in_progress": 2,
    "pending_validation": 3,
    "overdue": 4,
    "escalated": 5,
    "completed": 6,
}

TASK_STATUS_LABELS = {
    "not_started": "Not Started",
    "in_progress": "In Progress",
    "pending_validation": "Pending Validation",
    "completed": "Completed",
    "overdue": "Overdue",
    "escalated": "Escalated",
}

PRIORITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}

FIELD_TASK_UPDATE_FIELDS = frozenset({
    "comment",
    "evidence_note",
    "progress_pct",
    "status",
    "submit_for_validation",
})
FIELD_MUTABLE_TASK_STATUSES = frozenset({"not_started", "in_progress", "overdue", "escalated"})
FIELD_SUBMITTABLE_TASK_STATUSES = frozenset({"in_progress", "overdue", "escalated"})

ROLE_EXPERIENCE = {
    "organization_admin": {
        "title": "Organization Admin",
        "focus": "Organization-wide access control, workspace administration, and operational governance.",
    },
    "programme_manager": {
        "title": "Programme Manager",
        "focus": "Operational overview, backlog reduction, escalation control, and deadline recovery.",
    },
    "meal_officer": {
        "title": "MEAL Officer",
        "focus": "Validation backlog, reporting confidence, evidence quality, and indicator-linked follow-up.",
    },
    "field_coordinator": {
        "title": "Field Coordinator",
        "focus": "Assigned tasks, upcoming deadlines, field comments, and implementation progress updates.",
    },
    "executive_viewer": {
        "title": "Executive Viewer",
        "focus": "Delivery posture, donor readiness, risk exposure, and management actions needing oversight.",
    },
}


def _normalize_task_status(value: Any) -> str:
    raw = str(value or "not_started").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "todo": "not_started",
        "new": "not_started",
        "doing": "in_progress",
        "ongoing": "in_progress",
        "pending_validation": "pending_validation",
        "validation_pending": "pending_validation",
        "awaiting_validation": "pending_validation",
        "done": "completed",
        "complete": "completed",
        "approved": "completed",
        "resolved": "completed",
        "closed": "completed",
    }
    normalized = aliases.get(raw, raw)
    return normalized if normalized in TASK_STATUS_ORDER else "not_started"


def _task_status_label(value: Any) -> str:
    return TASK_STATUS_LABELS.get(_normalize_task_status(value), "Not Started")


def _task_is_complete(value: Any) -> bool:
    return _normalize_task_status(value) == "completed"


def _task_progress_default(status: Any) -> float:
    mapping = {
        "not_started": 0.0,
        "in_progress": 52.0,
        "pending_validation": 90.0,
        "completed": 100.0,
        "overdue": 24.0,
        "escalated": 32.0,
    }
    return mapping[_normalize_task_status(status)]


def _normalize_priority(value: Any) -> str:
    text = str(value or "medium").strip().lower()
    return text if text in PRIORITY_ORDER else "medium"


def _clamp_number(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class DemoWorkspaceServiceDependencies:
    load_data: Callable[[], Any]
    save_data: Callable[[Any], str]
    authorize_request: Callable[[Any, Optional[str], Optional[str], str], Any]
    append_audit_event: Callable[..., None]
    from_serializable: Callable[[Dict[str, Any]], Any]
    find_user_by_username: Callable[[Any, str], Any]
    sanitize_user: Callable[[Any], Dict[str, Any]]
    build_password_hash: Callable[[str], tuple[str, str]]
    hash_with_sha256: Callable[[str], str]
    new_api_token: Callable[[], str]
    now_iso_utc: Callable[[], str]
    build_dashboard_summary: Callable[[Any], Dict[str, Any]]
    build_bi_payload: Callable[[Any], Dict[str, List[Dict[str, Any]]]]
    build_portfolio_narrative_summary: Callable[[Any], Dict[str, Any]]
    build_project_narrative_summary: Callable[[Any, str], Dict[str, Any]]
    build_current_notifications: Callable[[Any], List[Dict[str, Any]]]
    filter_notifications: Callable[[List[Dict[str, Any]], str, Optional[int]], List[Dict[str, Any]]]
    build_tidy_dataset_quality_report: Callable[[Any, Any], Dict[str, Any]]
    build_project_trend_series: Callable[[Any, str], List[Dict[str, Any]]]
    find_project: Callable[[Any, str], Any]
    find_tidy_dataset: Callable[[Any, str], Any]
    find_dashboard_template: Callable[[Any, str], Any]
    parse_date_like_value: Callable[[Any], Any]


class DemoWorkspaceService:
    def __init__(self, deps: DemoWorkspaceServiceDependencies):
        self.deps = deps

    def _seed_bundle(self) -> DemoSeedBundle:
        return build_demo_seed_bundle(self.deps.build_password_hash)

    def _role_profile_for_user(self, actor: Any) -> Dict[str, str]:
        username = str(getattr(actor, "username", "") or "").strip().lower()
        role = str(getattr(actor, "role", "") or "").strip().lower()
        if role == "organization_admin":
            return {"id": "organization_admin", **ROLE_EXPERIENCE["organization_admin"]}
        if "field" in username or "coord" in username:
            return {"id": "field_coordinator", **ROLE_EXPERIENCE["field_coordinator"]}
        if role == "field_coordinator":
            return {"id": "field_coordinator", **ROLE_EXPERIENCE["field_coordinator"]}
        if role == "meal_officer" or "analyst" in role or "analyst" in username:
            return {"id": "meal_officer", **ROLE_EXPERIENCE["meal_officer"]}
        if role in {"programme_manager", "organization_admin", "admin", "manager"}:
            return {"id": "programme_manager", **ROLE_EXPERIENCE["programme_manager"]}
        return {"id": "executive_viewer", **ROLE_EXPERIENCE["executive_viewer"]}

    def _enforce_task_update_scope(self, actor: Any, task: Any) -> None:
        if actor is None:
            return
        role = str(getattr(actor, "role", "") or "").strip().lower()
        if role != "field_coordinator":
            return
        actor_username = str(getattr(actor, "username", "") or "").strip().lower()
        assignee_username = str(getattr(task, "assignee_username", "") or "").strip().lower()
        if not actor_username or actor_username != assignee_username:
            raise ServiceError(403, "Field coordinators may update only tasks assigned to their authenticated account.")

    def _actor_role(self, actor: Any) -> str:
        return str(getattr(actor, "role", "") or "").strip().lower()

    def _ensure_actor_project_scope(self, actor: Any, project: Any) -> None:
        if actor is None:
            return
        actor_organization_id = str(getattr(actor, "organization_id", "") or "").strip()
        project_organization_id = str(getattr(project, "organization_id", "") or "").strip()
        if actor_organization_id and project_organization_id and actor_organization_id != project_organization_id:
            raise ServiceError(403, "Access denied for this project's organization.")

    def _eligible_project_assignees(self, data: Any, project: Any) -> List[Dict[str, Any]]:
        project_id = str(getattr(project, "id", "") or "").strip()
        organization_id = str(getattr(project, "organization_id", "") or "").strip()
        assignments_by_user_id: Dict[str, Any] = {}
        for assignment in getattr(project, "team_assignments", []) or []:
            if str(getattr(assignment, "project_id", "") or "").strip() != project_id:
                continue
            if str(getattr(assignment, "organization_id", "") or "").strip() != organization_id:
                continue
            if str(getattr(assignment, "status", "active") or "active").strip().lower() != "active":
                continue
            user_id = str(getattr(assignment, "user_id", "") or "").strip()
            if user_id and user_id not in assignments_by_user_id:
                assignments_by_user_id[user_id] = assignment

        eligible: List[Dict[str, Any]] = []
        for user in getattr(data, "users", []) or []:
            assignment = assignments_by_user_id.get(str(getattr(user, "id", "") or "").strip())
            if assignment is None:
                continue
            if str(getattr(user, "organization_id", "") or "").strip() != organization_id:
                continue
            if not bool(getattr(user, "is_active", False)):
                continue
            if str(getattr(user, "status", "active") or "active").strip().lower() != "active":
                continue
            sanitized = self.deps.sanitize_user(user)
            eligible.append({
                "user_id": str(getattr(user, "id", "") or ""),
                "username": str(getattr(user, "username", "") or ""),
                "full_name": str(getattr(user, "full_name", "") or getattr(user, "username", "") or ""),
                "role": str(getattr(user, "role", "") or ""),
                "role_label": str(sanitized.get("role_label") or getattr(user, "role", "") or ""),
                "project_role": str(getattr(assignment, "role", "") or ""),
                "team_id": str(getattr(assignment, "team_id", "") or getattr(user, "team_id", "") or ""),
            })
        return sorted(eligible, key=lambda item: (item["full_name"].lower(), item["username"].lower()))

    def _resolve_task_assignee(self, data: Any, project: Any, username: Any) -> Any:
        canonical_username = str(username or "").strip()
        if not canonical_username:
            raise ServiceError(400, "Task creation requires an eligible project assignee.")
        user = self.deps.find_user_by_username(data, canonical_username)
        if user is None:
            raise ServiceError(400, "The selected task assignee is not eligible for this project.")
        eligible_user_ids = {item["user_id"] for item in self._eligible_project_assignees(data, project)}
        if str(getattr(user, "id", "") or "") not in eligible_user_ids:
            raise ServiceError(400, "The selected task assignee is not eligible for this project.")
        return user

    def _validate_task_update_request(self, actor: Any, task: Any, payload: Dict[str, Any]) -> None:
        role = self._actor_role(actor)
        current_status = _normalize_task_status(getattr(task, "status", "not_started"))
        submit_for_validation = bool(payload.get("submit_for_validation"))

        if role == "field_coordinator":
            self._enforce_task_update_scope(actor, task)
            unsupported_fields = sorted(set(payload) - FIELD_TASK_UPDATE_FIELDS)
            if unsupported_fields:
                raise ServiceError(403, "Field coordinators may update only progress, evidence, comments, and submission state.")
            if current_status not in FIELD_MUTABLE_TASK_STATUSES:
                raise ServiceError(409, "This task is not currently open for Field execution updates.")
            if "status" in payload:
                requested_status = _normalize_task_status(payload.get("status"))
                if requested_status != "in_progress":
                    raise ServiceError(403, "Field coordinators cannot set arbitrary task status values.")
                if current_status != "not_started" or submit_for_validation:
                    raise ServiceError(409, "Only a Not Started task can be started through this action.")
            if submit_for_validation and current_status not in FIELD_SUBMITTABLE_TASK_STATUSES:
                raise ServiceError(409, "Only active Field work can be submitted for MEAL validation.")
        elif submit_for_validation:
            raise ServiceError(403, "Only the assigned Field Coordinator may submit this task for validation.")

        if "status" in payload:
            requested_status = _normalize_task_status(payload.get("status"))
            if requested_status in {"pending_validation", "completed"}:
                raise ServiceError(409, "Use the supported submission and approval actions for this workflow transition.")

    def _organization_id_for_actor(self, data: Any, actor: Any) -> str:
        if actor is not None and getattr(actor, "organization_id", ""):
            return str(getattr(actor, "organization_id", "") or "")
        first_org = next(iter(getattr(data, "organizations", []) or []), None)
        return str(getattr(first_org, "id", "") or "")

    def _scope_data_for_actor(self, data: Any, actor: Any) -> Any:
        organization_id = self._organization_id_for_actor(data, actor)
        if not organization_id:
            return data
        scoped = deepcopy(data)
        scoped.organizations = [org for org in getattr(scoped, "organizations", []) if getattr(org, "id", "") == organization_id]
        scoped.projects = [
            project for project in getattr(scoped, "projects", [])
            if (
                (not getattr(project, "organization_id", "") or getattr(project, "organization_id", "") == organization_id)
                and str(getattr(project, "status", "active") or "active").strip().lower() not in {"draft", "archived"}
            )
        ]
        allowed_project_ids = {project.id for project in scoped.projects}
        scoped.ops_by_project = {
            project_id: ops
            for project_id, ops in getattr(scoped, "ops_by_project", {}).items()
            if project_id in allowed_project_ids
        }
        scoped.tidy_datasets = [
            dataset for dataset in getattr(scoped, "tidy_datasets", [])
            if not getattr(dataset, "organization_id", "") or getattr(dataset, "organization_id", "") == organization_id
        ]
        allowed_dataset_ids = {dataset.id for dataset in scoped.tidy_datasets}
        scoped.reporting_records = [
            record for record in getattr(scoped, "reporting_records", [])
            if (
                (not getattr(record, "organization_id", "") or getattr(record, "organization_id", "") == organization_id)
                and (not getattr(record, "project_id", "") or getattr(record, "project_id", "") in allowed_project_ids)
            )
        ]
        scoped.semantic_mappings = [
            item for item in getattr(scoped, "semantic_mappings", [])
            if (
                (not getattr(item, "organization_id", "") or getattr(item, "organization_id", "") == organization_id)
                and (not getattr(item, "dataset_id", "") or getattr(item, "dataset_id", "") in allowed_dataset_ids)
            )
        ]
        scoped.dashboard_templates = [
            item for item in getattr(scoped, "dashboard_templates", [])
            if not getattr(item, "organization_id", "") or getattr(item, "organization_id", "") == organization_id
        ]
        scoped.notification_rules = [
            item for item in getattr(scoped, "notification_rules", [])
            if (
                (not getattr(item, "organization_id", "") or getattr(item, "organization_id", "") == organization_id)
                and (not getattr(item, "project_id", "") or getattr(item, "project_id", "") in allowed_project_ids)
            )
        ]
        scoped.users = [
            user for user in getattr(scoped, "users", [])
            if not getattr(user, "organization_id", "") or getattr(user, "organization_id", "") == organization_id
        ]
        scoped.audit_events = [
            item for item in getattr(scoped, "audit_events", [])
            if not getattr(item, "organization_id", "") or getattr(item, "organization_id", "") == organization_id
        ]
        return scoped

    def _canonical_status_from_score(self, score: Optional[float]) -> str:
        if score is None:
            return "SEM DADOS"
        numeric = float(score)
        if numeric >= 100:
            return "SUPEROU"
        if numeric >= 80:
            return "VERDE"
        if numeric >= 55:
            return "AMARELO"
        return "VERMELHO"

    def _task_due_datetime(self, value: Any) -> Optional[datetime]:
        return self.deps.parse_date_like_value(value)

    def _coerce_datetime(self, value: Any) -> Optional[datetime]:
        if value in (None, ""):
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            value = value.isoformat()
        return self.deps.parse_date_like_value(value)

    def _coerce_date(self, value: Any) -> Optional[date]:
        parsed = self._coerce_datetime(value)
        return parsed.date() if parsed is not None else None

    def _task_is_overdue(self, value: Dict[str, Any]) -> bool:
        due_at = self._task_due_datetime(value.get("due_date"))
        if due_at is None or _task_is_complete(value.get("status")):
            return False
        reference = self.deps.parse_date_like_value(self.deps.now_iso_utc()) or UTC_DATETIME_MIN
        return due_at < reference

    def _task_sort_key(self, value: Dict[str, Any], default: datetime = UTC_DATETIME_MAX) -> datetime:
        return self._task_due_datetime(value.get("due_date")) or default

    def _find_task_context(self, data: Any, task_id: str) -> Dict[str, Any]:
        for project in data.projects:
            ops = data.ops_by_project.get(project.id)
            if not ops:
                continue
            for activity in ops.activities:
                for task in activity.tasks:
                    if task.id == task_id:
                        return {
                            "project": project,
                            "ops": ops,
                            "activity": activity,
                            "task": task,
                        }
        raise ServiceError(404, f"Task '{task_id}' not found.")

    def _task_class(self, data: Any) -> Any:
        for ops in data.ops_by_project.values():
            for activity in getattr(ops, "activities", []) or []:
                for task in getattr(activity, "tasks", []) or []:
                    return type(task)
        raise ServiceError(500, "No task class could be inferred from the workspace.")

    def _activity_class(self, data: Any) -> Any:
        for ops in data.ops_by_project.values():
            for activity in getattr(ops, "activities", []) or []:
                return type(activity)
        raise ServiceError(500, "No activity class could be inferred from the workspace.")

    def _opslite_class(self, data: Any) -> Any:
        for ops in data.ops_by_project.values():
            return type(ops)
        raise ServiceError(500, "No workplan container class could be inferred from the workspace.")

    def _task_to_row(self, project_id: str, activity: Any, task: Any) -> Dict[str, Any]:
        status = _normalize_task_status(getattr(task, "status", "not_started"))
        due_date = task.due_date.isoformat() if getattr(task, "due_date", None) else None
        return {
            "task_id": task.id,
            "project_id": project_id,
            "activity_id": activity.id,
            "activity_name": getattr(activity, "name", ""),
            "task_name": task.name,
            "owner": task.owner,
            "assignee_username": getattr(task, "assignee_username", ""),
            "assignee_name": getattr(task, "assignee_name", "") or task.owner,
            "due_date": due_date,
            "status": status,
            "status_label": _task_status_label(status),
            "notes": getattr(task, "notes", ""),
            "priority": getattr(task, "priority", "medium"),
            "progress_pct": round(float(getattr(task, "progress_pct", 0.0) or 0.0), 2),
            "category": getattr(task, "category", "implementation"),
            "linked_indicator_id": getattr(task, "linked_indicator_id", ""),
            "evidence_count": len(getattr(task, "evidence_placeholders", []) or []),
            "comment_count": len(getattr(task, "activity_log", []) or []),
            "created_at": getattr(task, "created_at", ""),
            "updated_at": getattr(task, "updated_at", ""),
            "submitted_at": getattr(task, "submitted_at", ""),
            "validated_at": getattr(task, "validated_at", ""),
            "approved_at": getattr(task, "approved_at", ""),
            "evidence_placeholders": list(getattr(task, "evidence_placeholders", []) or []),
            "activity_log": list(getattr(task, "activity_log", []) or []),
        }

    def _append_task_log_entry(
        self,
        task: Any,
        actor: Any,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not hasattr(task, "activity_log") or task.activity_log is None:
            task.activity_log = []
        task.activity_log.append({
            "id": _safe_slug(f"{task.id}_{event_type}_{self.deps.now_iso_utc()}"),
            "occurred_at": self.deps.now_iso_utc(),
            "actor_username": getattr(actor, "username", "") if actor else "",
            "actor_role": getattr(actor, "role", "") if actor else "",
            "event_type": event_type,
            "message": message,
            "details": details or {},
        })
        task.updated_at = self.deps.now_iso_utc()

    def _project_task_rows(self, data: Any, project_id: str) -> List[Dict[str, Any]]:
        ops = data.ops_by_project.get(project_id)
        if not ops:
            return []
        rows: List[Dict[str, Any]] = []
        for activity in ops.activities:
            for task in activity.tasks:
                rows.append(self._task_to_row(project_id, activity, task))
        return rows

    def _workflow_rollup(self, task_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        counts = {key: 0 for key in TASK_STATUS_ORDER}
        overdue = 0
        upcoming = 0
        active_assignees = set()
        categories: Dict[str, int] = {}
        linked_indicators = set()
        evidence_count = 0
        comments_count = 0
        progress_samples: List[float] = []
        today_dt = self.deps.parse_date_like_value(self.deps.now_iso_utc()) or UTC_DATETIME_MIN
        next_week = today_dt + timedelta(days=7)
        for row in task_rows:
            status = _normalize_task_status(row.get("status"))
            counts[status] = counts.get(status, 0) + 1
            due_at = self._task_due_datetime(row.get("due_date"))
            if due_at and not _task_is_complete(status):
                if due_at < today_dt:
                    overdue += 1
                elif today_dt <= due_at <= next_week:
                    upcoming += 1
            assignee = str(row.get("assignee_name") or row.get("owner") or "").strip()
            if assignee:
                active_assignees.add(assignee)
            category = str(row.get("category") or "implementation").strip().lower()
            categories[category] = categories.get(category, 0) + 1
            linked_indicator = str(row.get("linked_indicator_id") or "").strip()
            if linked_indicator:
                linked_indicators.add(linked_indicator)
            evidence_count += int(row.get("evidence_count") or 0)
            comments_count += int(row.get("comment_count") or 0)
            progress = row.get("progress_pct")
            if progress not in (None, ""):
                try:
                    progress_samples.append(float(progress))
                except Exception:
                    pass
        total = len(task_rows)
        completed = counts.get("completed", 0)
        open_count = max(total - completed, 0)
        pending_validation = counts.get("pending_validation", 0)
        escalated = counts.get("escalated", 0)
        in_progress = counts.get("in_progress", 0)
        avg_progress = round(sum(progress_samples) / len(progress_samples), 2) if progress_samples else 0.0
        return {
            "total": total,
            "completed": completed,
            "open": open_count,
            "in_progress": in_progress,
            "pending_validation": pending_validation,
            "escalated": escalated,
            "overdue": overdue,
            "upcoming": upcoming,
            "active_assignees": len(active_assignees),
            "categories": categories,
            "linked_indicators": len(linked_indicators),
            "evidence_count": evidence_count,
            "comments_count": comments_count,
            "progress_avg_pct": avg_progress,
            "completion_pct": round((completed / total) * 100, 2) if total else 0.0,
            "status_counts": counts,
        }

    def _operational_notifications(
        self,
        project: Dict[str, Any],
        executive: Dict[str, Any],
        workflow: Dict[str, Any],
        base_notifications: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        items = list(base_notifications)
        project_id = project.get("project_id", "")
        project_name = project.get("project_name", "Project")
        overdue = int(workflow.get("overdue") or 0)
        pending = int(workflow.get("pending_validation") or 0)
        escalated = int(workflow.get("escalated") or 0)
        open_tasks = int(workflow.get("open") or 0)
        if overdue:
            items.append(self._sim_notification(
                "critical" if overdue >= 4 else "high",
                f"{project_name}: overdue coordination pressure",
                f"{overdue} operational task(s) are overdue and currently lowering delivery flexibility.",
                "Reassign recovery owners, confirm near-term deadlines, and unblock delayed actions.",
            ) | {"context": {"project_id": project_id, "area": "workplan", "overdue_tasks": overdue}})
        if pending:
            items.append(self._sim_notification(
                "high" if pending >= 3 else "medium",
                f"{project_name}: validation backlog requires follow-up",
                f"{pending} completion update(s) are waiting for validation or sign-off.",
                "Clear the validation queue before the next reporting checkpoint.",
            ) | {"context": {"project_id": project_id, "area": "validation", "pending_validation": pending}})
        if escalated:
            items.append(self._sim_notification(
                "critical",
                f"{project_name}: escalation workflow is active",
                f"{escalated} task(s) have been escalated and require immediate management attention.",
                "Open the coordination view and confirm corrective actions with named owners today.",
            ) | {"context": {"project_id": project_id, "area": "escalation", "escalated_tasks": escalated}})
        if open_tasks and not overdue and not pending:
            items.append(self._sim_notification(
                "low",
                f"{project_name}: active implementation coordination",
                f"{open_tasks} task(s) are open and currently shaping implementation follow-up.",
                "Use the workplan workspace to update progress and close completed actions.",
            ) | {"context": {"project_id": project_id, "area": "coordination", "open_tasks": open_tasks}})
        deduped: Dict[str, Dict[str, Any]] = {}
        for item in items:
            dedupe_key = f"{item.get('severity')}|{item.get('title')}|{item.get('message')}"
            deduped.setdefault(dedupe_key, item)
        return sorted(deduped.values(), key=lambda item: self._severity_rank(item.get("severity", "info")), reverse=True)

    def _operational_state(
        self,
        project: Dict[str, Any],
        executive: Dict[str, Any],
        workflow: Dict[str, Any],
        notifications: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        base_progress = float(executive.get("progress_weighted_pct") or 0.0)
        coverage = float(executive.get("workplan_coverage_pct") or 0.0)
        high_alerts = sum(1 for item in notifications if self._severity_rank(item.get("severity", "info")) >= 3)
        overdue = int(workflow.get("overdue") or 0)
        pending = int(workflow.get("pending_validation") or 0)
        escalated = int(workflow.get("escalated") or 0)
        completion_pct = float(workflow.get("completion_pct") or 0.0)
        reporting_age_penalty = max(0.0, (self._days_since(executive.get("latest_reporting_period")) or 0) - 31)

        delivery_health = _clamp_number(base_progress - (overdue * 5.0) - (escalated * 8.0) - (pending * 2.0) + (completion_pct * 0.08))
        reporting_confidence = _clamp_number(coverage - (pending * 8.0) - (overdue * 2.0) - reporting_age_penalty + min(14.0, completion_pct * 0.04))
        operational_load = _clamp_number(100.0 - (workflow.get("open", 0) * 4.0) - (overdue * 7.0) - (pending * 5.0))
        escalation_pressure = _clamp_number(100.0 - (high_alerts * 14.0) - (overdue * 5.0) - (escalated * 10.0))

        if overdue >= 4 or escalated >= 2:
            posture = "high_pressure"
        elif overdue > 0 or pending > 0 or high_alerts > 0:
            posture = "managed_pressure"
        else:
            posture = "stable"

        return {
            "delivery_health_score": round(delivery_health, 2),
            "reporting_confidence_score": round(reporting_confidence, 2),
            "operational_load_score": round(operational_load, 2),
            "escalation_pressure_score": round(escalation_pressure, 2),
            "status_mean_canon": self._canonical_status_from_score(delivery_health),
            "status_weighted_canon": self._canonical_status_from_score(delivery_health),
            "coordination_posture": posture,
            "approval_backlog": int(workflow.get("pending_validation") or 0),
            "open_tasks": int(workflow.get("open") or 0),
            "task_progress_avg_pct": round(float(workflow.get("progress_avg_pct") or 0.0), 2),
        }

    def _days_since(self, value: Any) -> Optional[int]:
        parsed = self.deps.parse_date_like_value(value)
        now_dt = self.deps.parse_date_like_value(self.deps.now_iso_utc())
        if parsed is None or now_dt is None:
            return None
        return max(0, (now_dt - parsed).days)

    def _activity_feed(self, data: Any, project_id: str, workflow: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for event in reversed(data.audit_events):
            details = event.details or {}
            event_project_id = str(details.get("project_id") or "").strip()
            target_id = str(getattr(event, "target_id", "") or "").strip()
            task_id = str(details.get("task_id") or "").strip()
            if event_project_id == project_id or target_id == project_id or (task_id and task_id.startswith(f"task_{project_id}_")):
                title, message = self._activity_event_copy(event)
                events.append({
                    "id": event.id,
                    "occurred_at": event.occurred_at,
                    "actor": event.actor_username or "system",
                    "actor_role": event.actor_role or "",
                    "title": title,
                    "message": message,
                    "action": event.action,
                    "tone": self._activity_tone(event.action, details),
                })
        if workflow:
            if int(workflow.get("pending_validation") or 0):
                events.insert(0, {
                    "id": f"{project_id}-pending-validation",
                    "occurred_at": self.deps.now_iso_utc(),
                    "actor": "workflow",
                    "actor_role": "system",
                    "title": "Validation backlog remains open",
                    "message": f"{workflow['pending_validation']} update(s) still require validation before the reporting posture can improve.",
                    "action": "workflow.validation_backlog",
                    "tone": "warn",
                })
            if int(workflow.get("overdue") or 0):
                events.insert(0, {
                    "id": f"{project_id}-overdue-pressure",
                    "occurred_at": self.deps.now_iso_utc(),
                    "actor": "workflow",
                    "actor_role": "system",
                    "title": "Overdue implementation pressure detected",
                    "message": f"{workflow['overdue']} task(s) are overdue and currently shaping delivery pressure.",
                    "action": "workflow.overdue",
                    "tone": "bad",
                })
        return events[:15]

    def _activity_event_copy(self, event: Any) -> tuple[str, str]:
        details = event.details or {}
        action = str(event.action or "").strip().lower()
        if action == "demo.task.created":
            return "Task assigned", f"{details.get('task_name', 'A task')} was assigned to {details.get('assignee_name') or details.get('owner') or 'the team'}."
        if action == "demo.task.updated":
            return "Task progress updated", details.get("message", "Operational task progress was updated.")
        if action == "demo.task.validated":
            return "Validation completed", details.get("message", "A task update was validated in the workflow.")
        if action == "demo.task.approved":
            return "Approval completed", details.get("message", "A task update was approved and the project posture was refreshed.")
        if action == "reporting_records.imported":
            return "Reporting cycle submitted", "Fresh reporting records were imported into the workspace."
        if action == "notification_rule.run_due":
            return "Scheduled alerts evaluated", "The notification engine checked due rules and updated the alert state."
        return event.action.replace(".", " ").replace("_", " ").title(), details.get("message", "Operational activity was recorded in the workspace.")

    def _activity_tone(self, action: str, details: Dict[str, Any]) -> str:
        action_key = str(action or "").lower()
        if "approved" in action_key or "validated" in action_key:
            return "good"
        if "overdue" in action_key or details.get("overdue_tasks"):
            return "bad"
        if "created" in action_key or "updated" in action_key:
            return "info"
        return "warn"

    def _augment_project_narrative(
        self,
        project: Dict[str, Any],
        executive: Dict[str, Any],
        workflow: Dict[str, Any],
        notifications: List[Dict[str, Any]],
        narrative: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = dict(narrative or {})
        delivery_score = executive.get("delivery_health_score", executive.get("progress_weighted_pct"))
        reporting_score = executive.get("reporting_confidence_score", executive.get("workplan_coverage_pct"))
        overdue = int(workflow.get("overdue") or 0)
        pending = int(workflow.get("pending_validation") or 0)
        high_alerts = sum(1 for item in notifications if self._severity_rank(item.get("severity", "info")) >= 3)
        summary = (
            f"{project.get('project_name', 'This project')} is operating at {round(float(delivery_score or 0.0), 1)}% delivery health "
            f"with {overdue} overdue task(s), {pending} validation checkpoint(s), and {high_alerts} high-severity alert(s) currently shaping management attention."
        )
        insights = list(payload.get("insights") or [])
        insights[:0] = [
            f"Delivery health is now partially driven by operational execution, not only KPI reporting.",
            f"Reporting confidence currently stands at {round(float(reporting_score or 0.0), 1)}% after validation and backlog penalties.",
            f"{workflow.get('open', 0)} open task(s) remain active in the implementation workspace.",
        ]
        payload["summary"] = summary
        payload["insights"] = insights[:8]
        payload["recommended_actions"] = [
            "Assign recovery owners for overdue actions.",
            "Clear pending validation checkpoints before the next reporting cycle.",
            "Escalate blocked or repeated slippage items in the next coordination call.",
        ]
        return payload

    def _augment_portfolio_narrative(
        self,
        workspace: Dict[str, Any],
        narrative: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = dict(narrative or {})
        cards = workspace.get("project_cards", [])
        overdue = sum(int(item.get("tasks_overdue") or 0) for item in cards)
        high_risk = sum(1 for item in cards if int(item.get("active_notifications") or 0) >= 2 or str(item.get("risk_level") or "").lower() == "high")
        payload["summary"] = (
            f"The active portfolio combines {workspace.get('counts', {}).get('projects', 0)} project(s), "
            f"{overdue} overdue operational action(s), and {high_risk} project(s) requiring closer management attention."
        )
        payload["insights"] = [
            "Operational posture now reacts to task completion, validation backlog, and escalation pressure.",
            f"{workspace.get('portfolio', {}).get('tasks_overdue', 0)} overdue tasks are currently visible across the portfolio workspace.",
            f"{workspace.get('counts', {}).get('notifications', 0)} live notification signal(s) remain available for follow-up.",
        ] + list(payload.get("insights") or [])[:5]
        return payload

    def seed_workspace(
        self,
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        current_data = self.deps.load_data()
        actor = self.deps.authorize_request(current_data, x_api_key, x_auth_token, required_permission="WORKSPACE_ADMIN")
        bundle = self._seed_bundle()
        data = self.deps.from_serializable(bundle.payload)
        default_user = self.deps.find_user_by_username(data, bundle.default_username)
        if default_user is None:
            raise ServiceError(500, "Demo seed bundle did not create the default admin user.")

        demo_token = self.deps.new_api_token()
        default_user.api_token_hash = self.deps.hash_with_sha256(demo_token)
        default_user.updated_at = self.deps.now_iso_utc()

        self.deps.append_audit_event(
            data,
            action="demo.workspace.seeded",
            target_type="workspace_data",
            target_id="demo_seed",
            actor=actor,
            endpoint="/v1/demo/seed",
            details=bundle.to_summary(),
        )
        saved_path = self.deps.save_data(data)
        summary = self.deps.build_dashboard_summary(data)
        return {
            "ok": True,
            "saved_to": saved_path,
            "counts": summary["counts"],
            "default_project_id": bundle.default_project_id,
            "default_dataset_id": bundle.default_dataset_id,
            "login": {
                "email": bundle.default_email,
                "username": bundle.default_username,
                "password": next(item.password for item in bundle.credentials if item.username == bundle.default_username),
                "token": demo_token,
            },
            "user": {
                **self.deps.sanitize_user(default_user),
                "organization_name": bundle.payload.get("organizations", [{}])[0].get("organization_name", ""),
            },
            "credentials": [asdict(item) for item in bundle.credentials],
        }

    def workspace_overview(
        self,
        x_api_key: Optional[str] = None,
        x_auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        raw_data = self.deps.load_data()
        actor = self.deps.authorize_request(raw_data, x_api_key, x_auth_token, required_permission="VIEW_PORTFOLIO")
        data = self._scope_data_for_actor(raw_data, actor)
        summary = self.deps.build_dashboard_summary(data)
        payload = self.deps.build_bi_payload(data)
        narrative = self.deps.build_portfolio_narrative_summary(data)
        notifications = self.deps.filter_notifications(
            self.deps.build_current_notifications(data),
            min_severity="info",
            max_items=20,
        )
        project_meta = self._project_metadata_map(data)
        default_project_id = data.projects[0].id if data.projects else ""

        project_cards = []
        for row in payload["kpi_project"]:
            project_id = row.get("project_id", "")
            metadata = project_meta.get(project_id, {})
            workplan = next((item for item in payload["kpi_workplan"] if item.get("project_id") == project_id), {})
            base_project_notifications = [
                item for item in notifications
                if item.get("context", {}).get("project_id") == project_id or item.get("source_id") == project_id
            ]
            task_rows = self._project_task_rows(data, project_id)
            workflow = self._workflow_rollup(task_rows)
            project_frame = {
                "project_id": project_id,
                "project_name": row.get("project_name", ""),
                "risk_level": metadata.get("risk_level", "medium"),
            }
            operational_notifications = self._operational_notifications(project_frame, row, workflow, base_project_notifications)
            operational_state = self._operational_state(project_frame, {**row, **workplan}, workflow, operational_notifications)
            project_cards.append({
                "project_id": project_id,
                "project_name": row.get("project_name", ""),
                "objective": metadata.get("objective", ""),
                "donor": metadata.get("donor", ""),
                "manager": metadata.get("manager", ""),
                "partner": metadata.get("partner", ""),
                "sector": metadata.get("sector", ""),
                "country": metadata.get("country", ""),
                "provinces": sorted(metadata.get("provinces", [])),
                "district_count": len(metadata.get("districts", [])),
                "progress_weighted_pct": operational_state.get("delivery_health_score", row.get("progress_weighted_pct")),
                "status_mean_canon": operational_state.get("status_mean_canon", row.get("status_mean_canon")),
                "budget_total": row.get("budget_total"),
                "tasks_overdue": workflow.get("overdue", workplan.get("tasks_overdue", 0)),
                "tasks_next_7_days": workplan.get("tasks_next_7_days", 0),
                "workplan_coverage_pct": workplan.get("workplan_coverage_pct"),
                "active_notifications": len(operational_notifications),
                "highest_notification_severity": self._highest_severity(operational_notifications),
                "latest_reporting_period": summary["portfolio"].get("latest_reporting_period"),
                "risk_level": metadata.get("risk_level", "medium"),
                "budget_variance_pct": metadata.get("budget_variance_pct"),
                "reporting_confidence_score": operational_state.get("reporting_confidence_score"),
                "operational_load_score": operational_state.get("operational_load_score"),
                "escalation_pressure_score": operational_state.get("escalation_pressure_score"),
                "open_tasks": workflow.get("open", 0),
                "pending_validation": workflow.get("pending_validation", 0),
                "escalated_tasks": workflow.get("escalated", 0),
                "task_progress_avg_pct": workflow.get("progress_avg_pct", 0.0),
            })

        datasets = []
        total_quality = 0.0
        total_issues = 0
        stale_datasets = 0
        for dataset in data.tidy_datasets:
            quality = self.deps.build_tidy_dataset_quality_report(data, dataset)
            total_quality += float(quality.get("overall_score") or 0.0)
            total_issues += len(quality.get("issues") or [])
            if quality.get("data_freshness_days") is not None and float(quality["data_freshness_days"]) > 45:
                stale_datasets += 1
            datasets.append({
                "dataset_id": dataset.id,
                "name": dataset.name,
                "description": dataset.description,
                "row_count": len(dataset.rows),
                "quality_score": quality.get("overall_score"),
                "issues_count": len(quality.get("issues") or []),
                "freshness_days": quality.get("data_freshness_days"),
                "updated_at": dataset.updated_at,
            })

        portfolio_delivery_scores = [float(card.get("progress_weighted_pct") or 0.0) for card in project_cards]
        portfolio_reporting_scores = [float(card.get("reporting_confidence_score") or 0.0) for card in project_cards if card.get("reporting_confidence_score") is not None]
        portfolio_load_scores = [float(card.get("operational_load_score") or 0.0) for card in project_cards if card.get("operational_load_score") is not None]
        risks = self._portfolio_risks(notifications, project_cards)

        workspace = {
            "generated_at": self.deps.now_iso_utc(),
            "demo_ready": bool(data.projects or data.tidy_datasets),
            "default_project_id": default_project_id,
            "counts": summary["counts"],
            "portfolio": {
                **summary["portfolio"],
                "delivery_health_avg_pct": round(sum(portfolio_delivery_scores) / len(portfolio_delivery_scores), 2) if portfolio_delivery_scores else 0.0,
                "reporting_confidence_avg_pct": round(sum(portfolio_reporting_scores) / len(portfolio_reporting_scores), 2) if portfolio_reporting_scores else 0.0,
                "operational_load_avg_pct": round(sum(portfolio_load_scores) / len(portfolio_load_scores), 2) if portfolio_load_scores else 0.0,
            },
            "executive_cards": [
                {"label": "Active projects", "value": summary["counts"]["projects"], "tone": "good"},
                {"label": "Delivery health", "value": round(sum(portfolio_delivery_scores) / len(portfolio_delivery_scores), 1) if portfolio_delivery_scores else 0.0, "tone": "info", "suffix": "%"},
                {"label": "Reporting confidence", "value": round(sum(portfolio_reporting_scores) / len(portfolio_reporting_scores), 1) if portfolio_reporting_scores else 0.0, "tone": "accent", "suffix": "%"},
                {"label": "Overdue tasks", "value": summary["portfolio"].get("tasks_overdue"), "tone": "bad"},
                {"label": "Operational load", "value": sum(int(card.get("open_tasks") or 0) for card in project_cards), "tone": "warn"},
                {"label": "Reporting month", "value": summary["portfolio"].get("latest_reporting_period") or "n/a", "tone": "muted"},
            ],
            "project_cards": project_cards,
            "portfolio_trend": summary.get("portfolio_trend", []),
            "narrative": {},
            "notifications": notifications,
            "risks": risks,
            "data_quality": {
                "average_score": round(total_quality / len(datasets), 2) if datasets else 0.0,
                "datasets": datasets,
                "issue_count": total_issues,
                "stale_datasets": stale_datasets,
            },
            "templates": [asdict(item) for item in data.dashboard_templates],
            "demo_accounts": [self.deps.sanitize_user(user) for user in data.users],
            "organization": {
                "organization_id": self._organization_id_for_actor(data, actor),
                "organization_name": getattr(next(iter(getattr(data, "organizations", []) or []), None), "organization_name", ""),
            },
        }
        workspace["narrative"] = self._augment_portfolio_narrative(workspace, narrative)

        return workspace

    def project_executive_snapshot(
        self,
        project_id: str,
        template_id: Optional[str] = None,
        x_api_key: Optional[str] = None,
        x_auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        raw_data = self.deps.load_data()
        actor = self.deps.authorize_request(raw_data, x_api_key, x_auth_token, required_permission="VIEW_EXECUTIVE_SNAPSHOT")
        data = self._scope_data_for_actor(raw_data, actor)
        project = self.deps.find_project(data, project_id)
        if project is None:
            raise ServiceError(404, f"Project '{project_id}' not found.")
        self._ensure_actor_project_scope(actor, project)

        payload = self.deps.build_bi_payload(data)
        metadata = self._project_metadata_map(data).get(project_id, {})
        project_row = next((row for row in payload["projects"] if row.get("project_id") == project_id), None)
        project_kpi = next((row for row in payload["kpi_project"] if row.get("project_id") == project_id), None)
        workplan_kpi = next((row for row in payload["kpi_workplan"] if row.get("project_id") == project_id), None)
        if project_row is None or project_kpi is None:
            raise ServiceError(500, f"Project dashboard inputs are incomplete for '{project_id}'.")

        trend = self.deps.build_project_trend_series(data, project_id)
        base_narrative = self.deps.build_project_narrative_summary(data, project_id)
        notifications = [
            item for item in self.deps.build_current_notifications(data)
            if item.get("context", {}).get("project_id") == project_id or item.get("source_id") == project_id
        ]
        district_rows = [row for row in payload["kpi_district"] if row.get("project_id") == project_id]
        indicator_rows = [row for row in payload["kpi_indicator"] if row.get("project_id") == project_id]
        activity_rows = [row for row in payload["activities"] if row.get("project_id") == project_id]
        task_rows = self._project_task_rows(data, project_id)
        workflow = self._workflow_rollup(task_rows)
        records = [
            row for row in data.reporting_records
            if row.project_id == project_id
        ]
        records = sorted(
            records,
            key=lambda item: self._datetime_sort_key(item.reporting_period),
            reverse=True,
        )[:24]

        project_payload = {
            "project_id": project.id,
            "project_name": project.name,
            "objective": project.objective,
            "organization_id": getattr(project, "organization_id", ""),
            "donor": metadata.get("donor", ""),
            "manager": metadata.get("manager", ""),
            "partner": metadata.get("partner", ""),
            "sector": metadata.get("sector", ""),
            "country": metadata.get("country", ""),
            "provinces": sorted(metadata.get("provinces", [])),
            "districts": sorted(metadata.get("districts", [])),
            "risk_level": metadata.get("risk_level", "medium"),
            "budget_variance_pct": metadata.get("budget_variance_pct"),
        }
        notifications = self._operational_notifications(project_payload, {**project_kpi, **(workplan_kpi or {})}, workflow, notifications)
        operational_state = self._operational_state(project_payload, {**project_kpi, **(workplan_kpi or {})}, workflow, notifications)
        narrative = self._augment_project_narrative(project_payload, {**project_kpi, **(workplan_kpi or {}), **operational_state}, workflow, notifications, base_narrative)

        templates = [asdict(item) for item in data.dashboard_templates]
        selected_template = self._select_template(data, template_id)
        rendered_widgets = self._render_dashboard_widgets(
            selected_template=selected_template,
            project_row=project_row,
            project_kpi=project_kpi,
            workplan_kpi=workplan_kpi or {},
            district_rows=district_rows,
            indicator_rows=indicator_rows,
            trend=trend,
            notifications=notifications,
            activity_rows=activity_rows,
            metadata=metadata,
            narrative=narrative,
        )

        overdue_tasks = [row for row in task_rows if self._task_is_overdue(row)]
        return {
            "generated_at": self.deps.now_iso_utc(),
            "project": project_payload,
            "executive": {
                "progress_weighted_pct": operational_state.get("delivery_health_score", project_kpi.get("progress_weighted_pct")),
                "progress_mean_pct": project_kpi.get("progress_mean_pct"),
                "status_mean_canon": operational_state.get("status_mean_canon", project_kpi.get("status_mean_canon")),
                "budget_total": project_kpi.get("budget_total"),
                "latest_reporting_period": trend[-1].get("reporting_period") if trend else "",
                "tasks_overdue": workflow.get("overdue", workplan_kpi.get("tasks_overdue", 0)),
                "tasks_total": workflow.get("total", workplan_kpi.get("tasks_total", 0)),
                "tasks_done": workflow.get("completed", workplan_kpi.get("tasks_done", 0)),
                "workplan_coverage_pct": workplan_kpi.get("workplan_coverage_pct"),
                "active_notifications": len(notifications),
                "pending_validation_count": workflow.get("pending_validation", 0),
                "escalated_tasks": workflow.get("escalated", 0),
                "open_tasks": workflow.get("open", 0),
                "task_progress_avg_pct": workflow.get("progress_avg_pct", 0.0),
                "delivery_health_score": operational_state.get("delivery_health_score"),
                "reporting_confidence_score": operational_state.get("reporting_confidence_score"),
                "operational_load_score": operational_state.get("operational_load_score"),
                "escalation_pressure_score": operational_state.get("escalation_pressure_score"),
                "coordination_posture": operational_state.get("coordination_posture"),
                "approval_backlog": operational_state.get("approval_backlog"),
                "latest_sync_at": self.deps.now_iso_utc(),
            },
            "dashboard": {
                "selected_template": asdict(selected_template),
                "available_templates": templates,
                "widgets": rendered_widgets,
            },
            "trend": trend,
            "districts": district_rows,
            "indicators": indicator_rows,
            "activities": activity_rows,
            "tasks": task_rows,
            "overdue_tasks": overdue_tasks,
            "notifications": notifications,
            "narrative": narrative,
            "activity_feed": self._activity_feed(data, project_id, workflow),
            "workflow": workflow,
            "role_views": ROLE_EXPERIENCE,
            "reporting_records": [asdict(item) for item in records],
        }

    def project_risks(
        self,
        project_id: str,
        x_api_key: Optional[str] = None,
        x_auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="VIEW_RISKS")
        snapshot = self.project_executive_snapshot(project_id, x_api_key=x_api_key, x_auth_token=x_auth_token)
        risks = []
        for item in snapshot["notifications"]:
            risks.append({
                "severity": item.get("severity", "info"),
                "title": item.get("title", ""),
                "message": item.get("message", ""),
                "suggested_action": item.get("suggested_action", ""),
            })
        variance = snapshot["project"].get("budget_variance_pct")
        if variance is not None and abs(float(variance)) >= 8:
            risks.append({
                "severity": "high" if abs(float(variance)) >= 12 else "medium",
                "title": "Budget variance requires attention",
                "message": f"Current variance to plan is {variance}%.",
                "suggested_action": "Review burn rate assumptions with finance and the project manager.",
            })
        risks.sort(key=lambda item: self._severity_rank(item["severity"]), reverse=True)
        return {
            "project_id": project_id,
            "count": len(risks),
            "items": risks,
        }

    def project_workplan_snapshot(
        self,
        project_id: str,
        x_api_key: Optional[str] = None,
        x_auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="VIEW_WORKPLAN")
        project = self.deps.find_project(data, project_id)
        if project is None:
            raise ServiceError(404, f"Project '{project_id}' not found.")
        self._ensure_actor_project_scope(actor, project)
        snapshot = self.project_executive_snapshot(project_id, x_api_key=x_api_key, x_auth_token=x_auth_token)
        tasks = snapshot["tasks"]
        upcoming = [row for row in tasks if not _task_is_complete(row.get("status")) and row.get("due_date") and not self._task_is_overdue(row)]
        workflow = snapshot.get("workflow", {})
        return {
            "project_id": project_id,
            "eligible_assignees": self._eligible_project_assignees(data, project),
            "summary": snapshot["executive"],
            "activities": snapshot["activities"],
            "tasks": tasks,
            "overdue_tasks": snapshot["overdue_tasks"],
            "upcoming_tasks": sorted(
                upcoming,
                key=lambda item: self._task_sort_key(item, default=UTC_DATETIME_MAX),
            )[:10],
            "task_board": {
                "status_counts": workflow.get("status_counts", {}),
                "open_tasks": workflow.get("open", 0),
                "progress_avg_pct": workflow.get("progress_avg_pct", 0.0),
                "pending_validation": workflow.get("pending_validation", 0),
                "escalated": workflow.get("escalated", 0),
            },
            "activity_feed": snapshot.get("activity_feed", []),
            "role_views": snapshot.get("role_views", ROLE_EXPERIENCE),
            "operational_summary": {
                "delivery_health_score": snapshot["executive"].get("delivery_health_score"),
                "reporting_confidence_score": snapshot["executive"].get("reporting_confidence_score"),
                "operational_load_score": snapshot["executive"].get("operational_load_score"),
                "escalation_pressure_score": snapshot["executive"].get("escalation_pressure_score"),
            },
        }

    def data_quality_overview(
        self,
        x_api_key: Optional[str] = None,
        x_auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        raw_data = self.deps.load_data()
        actor = self.deps.authorize_request(raw_data, x_api_key, x_auth_token, required_permission="VIEW_DATA_QUALITY")
        data = self._scope_data_for_actor(raw_data, actor)
        items = []
        for dataset in data.tidy_datasets:
            quality = self.deps.build_tidy_dataset_quality_report(data, dataset)
            items.append({
                "dataset_id": dataset.id,
                "name": dataset.name,
                "description": dataset.description,
                "row_count": len(dataset.rows),
                "overall_score": quality.get("overall_score"),
                "data_freshness_days": quality.get("data_freshness_days"),
                "issues": quality.get("issues", []),
            })
        average_score = round(sum(float(item["overall_score"] or 0.0) for item in items) / len(items), 2) if items else 0.0
        return {
            "generated_at": self.deps.now_iso_utc(),
            "average_score": average_score,
            "datasets": items,
            "issue_count": sum(len(item["issues"]) for item in items),
        }

    def narrative_summary(
        self,
        project_id: Optional[str] = None,
        x_api_key: Optional[str] = None,
        x_auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        self.deps.authorize_request(
            data,
            x_api_key,
            x_auth_token,
            required_permissions=["VIEW_REPORTS", "GENERATE_REPORTS"],
        )
        payload = {
            "portfolio": self.workspace_overview(x_api_key=x_api_key, x_auth_token=x_auth_token).get("narrative", {}),
        }
        if project_id:
            try:
                payload["project"] = self.project_executive_snapshot(
                    project_id,
                    x_api_key=x_api_key,
                    x_auth_token=x_auth_token,
                ).get("narrative", {})
            except ServiceError:
                raise
        return payload

    def simulate_notifications(
        self,
        payload: Dict[str, Any],
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_NOTIFICATIONS")
        scenario = str(payload.get("scenario") or "overdue_alerts").strip().lower()
        project_id = str(payload.get("project_id") or "").strip()
        snapshot = self.project_executive_snapshot(
            project_id or (data.projects[0].id if data.projects else ""),
            x_api_key=x_api_key,
            x_auth_token=x_auth_token,
        )
        generated = self._scenario_notifications(scenario, snapshot)
        self.deps.append_audit_event(
            data,
            action="demo.notifications.simulated",
            target_type="notification_batch",
            target_id=scenario,
            actor=actor,
            endpoint="/v1/demo/notifications/simulate",
            details={"scenario": scenario, "project_id": snapshot["project"]["project_id"], "count": len(generated)},
        )
        self.deps.save_data(data)
        return {
            "ok": True,
            "scenario": scenario,
            "project_id": snapshot["project"]["project_id"],
            "project_name": snapshot["project"]["project_name"],
            "count": len(generated),
            "items": generated,
        }

    def create_task(
        self,
        payload: Dict[str, Any],
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="ASSIGN_TASKS")
        project_id = str(payload.get("project_id") or "").strip()
        if not project_id:
            raise ServiceError(400, "Task creation requires 'project_id'.")
        project = self.deps.find_project(data, project_id)
        if project is None:
            raise ServiceError(404, f"Project '{project_id}' not found.")
        self._ensure_actor_project_scope(actor, project)
        task_name = str(payload.get("title") or payload.get("name") or "").strip()
        if not task_name:
            raise ServiceError(400, "Task creation requires 'title' or 'name'.")
        assignee = self._resolve_task_assignee(data, project, payload.get("assignee_username"))

        ops = data.ops_by_project.get(project_id)
        if ops is None:
            ops_cls = self._opslite_class(data)
            ops = ops_cls(activities=[])
            data.ops_by_project[project_id] = ops

        activity_id = str(payload.get("activity_id") or "").strip()
        activity = next((item for item in ops.activities if item.id == activity_id), None) if activity_id else None
        if activity is None:
            activity_cls = self._activity_class(data)
            linked_indicator_id = str(payload.get("linked_indicator_id") or "").strip()
            activity = activity_cls(
                id=str(payload.get("activity_id") or f"act_{project_id}_coordination"),
                name=str(payload.get("activity_name") or "Operational Coordination Queue").strip(),
                owner=str(payload.get("activity_owner") or getattr(actor, "full_name", "") or getattr(actor, "username", "")).strip(),
                start_date=date.today(),
                due_date=self._coerce_date(payload.get("due_date")),
                status="ongoing",
                organization_id=str(getattr(project, "organization_id", "") or getattr(actor, "organization_id", "")),
                linked_indicator_ids=[linked_indicator_id] if linked_indicator_id else [],
                tasks=[],
            )
            ops.activities.append(activity)

        task_cls = self._task_class(data)
        status = "not_started"
        assignee_name = str(getattr(assignee, "full_name", "") or getattr(assignee, "username", "") or "")
        assignee_username = str(getattr(assignee, "username", "") or "")
        task = task_cls(
            id=str(payload.get("id") or f"task_{project_id}_{_safe_slug(payload.get('title') or payload.get('name') or self.deps.now_iso_utc())}"),
            name=task_name,
            owner=assignee_name,
            due_date=self._coerce_date(payload.get("due_date")),
            status=status,
            organization_id=str(getattr(project, "organization_id", "") or getattr(actor, "organization_id", "")),
            notes=str(payload.get("description") or payload.get("notes") or "").strip(),
            assignee_username=assignee_username,
            assignee_name=assignee_name,
            priority=_normalize_priority(payload.get("priority")),
            progress_pct=_task_progress_default(status),
            category=str(payload.get("category") or "implementation").strip().lower() or "implementation",
            linked_indicator_id=str(payload.get("linked_indicator_id") or "").strip(),
            evidence_placeholders=[str(item).strip() for item in payload.get("evidence_placeholders", []) if str(item).strip()],
            activity_log=[],
            created_at=self.deps.now_iso_utc(),
            updated_at=self.deps.now_iso_utc(),
            submitted_at="",
            validated_at="",
            approved_at="",
        )
        self._append_task_log_entry(
            task,
            actor,
            "task_assigned",
            f"Task assigned to {task.assignee_name or task.owner or 'the team'} with {task.priority} priority.",
            {"project_id": project_id, "activity_id": activity.id, "task_id": task.id},
        )
        activity.tasks.append(task)

        details = {
            "project_id": project_id,
            "activity_id": activity.id,
            "task_id": task.id,
            "task_name": task.name,
            "assignee_username": task.assignee_username,
            "assignee_name": task.assignee_name or task.owner,
            "priority": task.priority,
            "message": f"{task.name} was assigned to {task.assignee_name or task.owner or 'the team'}.",
        }
        self.deps.append_audit_event(
            data,
            action="demo.task.created",
            target_type="task",
            target_id=task.id,
            actor=actor,
            endpoint="/v1/demo/tasks",
            details=details,
        )
        self.deps.save_data(data)
        return {
            "ok": True,
            "task": self._task_to_row(project_id, activity, task),
            "project_id": project_id,
            "workflow": self.project_workplan_snapshot(project_id, x_api_key=x_api_key, x_auth_token=x_auth_token),
        }

    def update_task(
        self,
        task_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(
            data,
            x_api_key,
            x_auth_token,
            required_permissions=["UPDATE_TASK_PROGRESS", "MANAGE_WORKPLAN", "ASSIGN_TASKS"],
        )
        context = self._find_task_context(data, task_id)
        task = context["task"]
        project = context["project"]
        activity = context["activity"]
        self._ensure_actor_project_scope(actor, project)
        self._validate_task_update_request(actor, task, payload)

        if "status" in payload:
            task.status = _normalize_task_status(payload.get("status"))
        if "progress_pct" in payload and payload.get("progress_pct") not in (None, ""):
            task.progress_pct = _clamp_number(float(payload.get("progress_pct") or 0.0))
        else:
            task.progress_pct = float(getattr(task, "progress_pct", _task_progress_default(task.status)) or 0.0)
        if "due_date" in payload:
            task.due_date = self._coerce_date(payload.get("due_date"))
        if "priority" in payload:
            task.priority = _normalize_priority(payload.get("priority"))
        if "category" in payload:
            task.category = str(payload.get("category") or "implementation").strip().lower() or "implementation"
        if "assignee_name" in payload:
            task.assignee_name = str(payload.get("assignee_name") or "").strip()
        if "assignee_username" in payload:
            task.assignee_username = str(payload.get("assignee_username") or "").strip()
        if "owner" in payload:
            task.owner = str(payload.get("owner") or "").strip()
        if "linked_indicator_id" in payload:
            task.linked_indicator_id = str(payload.get("linked_indicator_id") or "").strip()

        comment = str(payload.get("comment") or "").strip()
        evidence_note = str(payload.get("evidence_note") or "").strip()
        submit_for_validation = bool(payload.get("submit_for_validation"))
        escalate = bool(payload.get("escalate"))

        if comment:
            if task.notes:
                task.notes = f"{task.notes}\n\n{comment}"
            else:
                task.notes = comment
        if evidence_note:
            task.evidence_placeholders.append(evidence_note)
        if submit_for_validation:
            task.status = "pending_validation"
            task.submitted_at = self.deps.now_iso_utc()
            task.validated_at = ""
            task.approved_at = ""
            task.progress_pct = max(float(getattr(task, "progress_pct", 0.0) or 0.0), 90.0)
        if escalate:
            task.status = "escalated"
        if _task_is_complete(task.status):
            task.progress_pct = 100.0
        elif self._coerce_datetime(task.due_date) and self._coerce_datetime(task.due_date) < (self.deps.parse_date_like_value(self.deps.now_iso_utc()) or UTC_DATETIME_MIN) and task.status not in {"pending_validation", "escalated"}:
            task.status = "overdue"

        message_bits = []
        if comment:
            message_bits.append("comment added")
        if evidence_note:
            message_bits.append("evidence placeholder attached")
        if submit_for_validation:
            message_bits.append("submitted for validation")
        if escalate:
            message_bits.append("escalated")
        if "progress_pct" in payload:
            message_bits.append(f"progress updated to {round(float(task.progress_pct), 1)}%")
        if "status" in payload and not submit_for_validation and not escalate:
            message_bits.append(f"status changed to {_task_status_label(task.status)}")
        update_message = ", ".join(message_bits) or "task details updated"

        normalized_status = _normalize_task_status(getattr(task, "status", "not_started"))
        log_event_type = (
            "submitted_for_validation" if submit_for_validation
            else "task_started" if "status" in payload and normalized_status in {"in_progress", "overdue"}
            else "task_updated"
        )
        audit_action = (
            "demo.task.submitted" if submit_for_validation
            else "demo.task.started" if log_event_type == "task_started"
            else "demo.task.updated"
        )

        self._append_task_log_entry(
            task,
            actor,
            log_event_type,
            update_message,
            {"project_id": project.id, "activity_id": activity.id, "task_id": task.id},
        )
        self.deps.append_audit_event(
            data,
            action=audit_action,
            target_type="task",
            target_id=task.id,
            actor=actor,
            endpoint=f"/v1/demo/tasks/{task.id}/update",
            details={
                "project_id": project.id,
                "activity_id": activity.id,
                "task_id": task.id,
                "task_name": task.name,
                "status": task.status,
                "progress_pct": round(float(task.progress_pct), 2),
                "message": f"{task.name}: {update_message}.",
            },
        )
        self.deps.save_data(data)
        return {
            "ok": True,
            "task": self._task_to_row(project.id, activity, task),
            "project_id": project.id,
            "workflow": self.project_workplan_snapshot(project.id, x_api_key=x_api_key, x_auth_token=x_auth_token),
        }

    def validate_task(
        self,
        task_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        decision = str(payload.get("decision") or "validated").strip().lower()
        data = self.deps.load_data()
        actor = self.deps.authorize_request(
            data,
            x_api_key,
            x_auth_token,
            required_permission="APPROVE_TASKS" if decision in {"approve", "approved"} else "VALIDATE_EVIDENCE",
        )
        context = self._find_task_context(data, task_id)
        task = context["task"]
        project = context["project"]
        activity = context["activity"]
        self._ensure_actor_project_scope(actor, project)

        status = _normalize_task_status(getattr(task, "status", "not_started"))
        submitted_at = str(getattr(task, "submitted_at", "") or "").strip()
        validated_at = str(getattr(task, "validated_at", "") or "").strip()
        approved_at = str(getattr(task, "approved_at", "") or "").strip()

        if decision in {"validate", "validated"}:
            if status != "pending_validation" or not submitted_at or validated_at:
                raise ServiceError(409, "Only an unvalidated submitted task can complete MEAL validation.")
            task.validated_at = self.deps.now_iso_utc()
            event_type = "demo.task.validated"
            task_event_type = "validated"
            message = "Validation checkpoint completed."
        elif decision in {"approve", "approved"}:
            if status != "pending_validation" or not validated_at or approved_at:
                raise ServiceError(409, "Final approval requires a pending task already validated by MEAL.")
            task.approved_at = self.deps.now_iso_utc()
            task.status = "completed"
            task.progress_pct = 100.0
            event_type = "demo.task.approved"
            task_event_type = "approved"
            message = "Manager approval completed and task closed."
        elif decision in {"reject", "rejected", "changes_required"}:
            if status != "pending_validation" or not submitted_at or validated_at:
                raise ServiceError(409, "Only an unvalidated submitted task can be returned for rework.")
            task.status = "in_progress"
            task.validated_at = ""
            task.approved_at = ""
            event_type = "demo.task.returned"
            task_event_type = "returned_for_rework"
            message = "Validation requested further work before closure."
        else:
            raise ServiceError(400, "Unsupported validation decision. Use validated, approved, or rejected.")

        comment = str(payload.get("comment") or "").strip()
        if comment:
            if task.notes:
                task.notes = f"{task.notes}\n\n{comment}"
            else:
                task.notes = comment
        self._append_task_log_entry(
            task,
            actor,
            task_event_type,
            message,
            {"project_id": project.id, "activity_id": activity.id, "task_id": task.id},
        )
        self.deps.append_audit_event(
            data,
            action=event_type,
            target_type="task",
            target_id=task.id,
            actor=actor,
            endpoint=f"/v1/demo/tasks/{task.id}/validate",
            details={
                "project_id": project.id,
                "activity_id": activity.id,
                "task_id": task.id,
                "task_name": task.name,
                "status": task.status,
                "submitted_at": getattr(task, "submitted_at", ""),
                "validated_at": getattr(task, "validated_at", ""),
                "approved_at": getattr(task, "approved_at", ""),
                "message": f"{task.name}: {message}",
            },
        )
        self.deps.save_data(data)
        return {
            "ok": True,
            "task": self._task_to_row(project.id, activity, task),
            "project_id": project.id,
            "workflow": self.project_workplan_snapshot(project.id, x_api_key=x_api_key, x_auth_token=x_auth_token),
        }

    def report_preview(
        self,
        audience: str = "donor",
        project_id: Optional[str] = None,
        x_api_key: Optional[str] = None,
        x_auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        self.deps.authorize_request(
            data,
            x_api_key,
            x_auth_token,
            required_permissions=["VIEW_REPORTS", "GENERATE_REPORTS"],
        )
        audience = (audience or "donor").strip().lower()
        if audience not in {"donor", "management", "meal"}:
            raise ServiceError(400, "Unsupported audience. Use 'donor', 'management', or 'meal'.")

        if project_id:
            snapshot = self.project_executive_snapshot(project_id, x_api_key=x_api_key, x_auth_token=x_auth_token)
            narrative = snapshot["narrative"]
            title = f"{snapshot['project']['project_name']} {self._audience_title(audience)}"
            highlights = [
                f"Delivery health is {snapshot['executive'].get('delivery_health_score', snapshot['executive'].get('progress_weighted_pct'))}%.",
                f"{snapshot['executive'].get('tasks_overdue', 0)} tasks are overdue.",
                f"{len(snapshot['notifications'])} current alerts require follow-up.",
            ]
            sections = [
                {"title": "Executive summary", "body": narrative.get("summary", ""), "bullets": narrative.get("insights", [])[:4]},
                {"title": "Delivery and coverage", "body": f"The project is active in {len(snapshot['project'].get('districts', []))} districts with {len(snapshot['indicators'])} tracked indicator rows and {snapshot['executive'].get('open_tasks', 0)} open operational tasks.", "bullets": [item.get("title", "") for item in snapshot["dashboard"]["widgets"][:3]]},
                {"title": "Risks and mitigation", "body": "Current risks are summarized below for management action.", "bullets": [item.get("title", "") for item in snapshot["notifications"][:4]]},
            ]
        else:
            workspace = self.workspace_overview(x_api_key=x_api_key, x_auth_token=x_auth_token)
            narrative = {"portfolio": workspace.get("narrative", {})}
            title = f"Portfolio {self._audience_title(audience)}"
            highlights = [
                f"The portfolio covers {workspace['counts']['projects']} active projects.",
                f"Delivery health is {workspace['portfolio'].get('delivery_health_avg_pct', workspace['portfolio'].get('progress_weighted_pct'))}%.",
                f"{workspace['portfolio'].get('tasks_overdue', 0)} overdue tasks are currently visible.",
            ]
            sections = [
                {"title": "Executive summary", "body": narrative["portfolio"].get("summary", ""), "bullets": narrative["portfolio"].get("insights", [])[:4]},
                {"title": "Portfolio delivery", "body": "The demo workspace combines delivery, operational, and donor accountability signals.", "bullets": [item["project_name"] for item in workspace["project_cards"][:3]]},
                {"title": "Risk and accountability", "body": "Priority notifications and data quality issues are surfaced for rapid follow-up.", "bullets": [item.get("title", "") for item in workspace["notifications"][:4]]},
            ]

        audience_guidance = {
            "donor": ["Value for money", "Implementation risks", "Coverage and beneficiary reach"],
            "management": ["Delivery trend", "Escalations", "Management actions due this week"],
            "meal": ["Indicator quality", "Reporting freshness", "Evidence gaps by district"],
        }
        return {
            "generated_at": self.deps.now_iso_utc(),
            "audience": audience,
            "title": title,
            "highlights": highlights,
            "sections": sections,
            "talking_points": audience_guidance[audience],
            "export_options": ["PDF briefing", "PowerPoint board pack", "Email summary"],
        }

    def _select_template(self, data: Any, template_id: Optional[str]) -> Any:
        if template_id:
            template = self.deps.find_dashboard_template(data, template_id)
            if template is not None:
                return template
        if data.dashboard_templates:
            return data.dashboard_templates[0]
        raise ServiceError(500, "No dashboard templates are available in the workspace.")

    def _project_metadata_map(self, data: Any) -> Dict[str, Dict[str, Any]]:
        metadata: Dict[str, Dict[str, Any]] = {}
        for dataset in data.tidy_datasets:
            for row in dataset.rows:
                project_id = str(row.get("project_id") or "").strip()
                project_name = str(row.get("project_name") or "").strip()
                if not project_id:
                    continue
                item = metadata.setdefault(project_id, {
                    "project_id": project_id,
                    "project_name": project_name,
                    "objective": next((project.objective for project in data.projects if project.id == project_id), ""),
                    "donor": "",
                    "manager": "",
                    "partner": "",
                    "sector": "",
                    "country": "",
                    "provinces": set(),
                    "districts": set(),
                    "risk_level": "low",
                    "budget_variance_pct": None,
                })
                item["donor"] = item["donor"] or str(row.get("donor") or "")
                item["manager"] = item["manager"] or str(row.get("project_manager") or row.get("owner") or "")
                item["partner"] = item["partner"] or str(row.get("implementing_partner") or "")
                item["sector"] = item["sector"] or str(row.get("sector") or "")
                item["country"] = item["country"] or str(row.get("country") or "")
                province = str(row.get("province") or "").strip()
                district = str(row.get("district") or "").strip()
                if province:
                    item["provinces"].add(province)
                if district:
                    item["districts"].add(district)
                risk_level = str(row.get("risk_level") or "").strip().lower()
                if self._severity_rank(risk_level) > self._severity_rank(item["risk_level"]):
                    item["risk_level"] = risk_level
                variance = row.get("budget_variance_pct")
                if variance not in (None, ""):
                    try:
                        item["budget_variance_pct"] = round(float(variance), 2)
                    except Exception:
                        pass
        return metadata

    def _portfolio_risks(self, notifications: List[Dict[str, Any]], project_cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        risks = []
        for card in project_cards:
            if int(card.get("tasks_overdue") or 0) > 0:
                risks.append({
                    "severity": "high" if int(card["tasks_overdue"]) >= 3 else "medium",
                    "title": f"{card['project_name']}: overdue workplan actions",
                    "message": f"{card['tasks_overdue']} task(s) are overdue and need attention.",
                    "project_id": card["project_id"],
                })
            variance = card.get("budget_variance_pct")
            if variance is not None and abs(float(variance)) >= 8:
                risks.append({
                    "severity": "high" if abs(float(variance)) >= 12 else "medium",
                    "title": f"{card['project_name']}: budget variance",
                    "message": f"Budget variance is {variance}%.",
                    "project_id": card["project_id"],
                })
        for item in notifications:
            if item.get("severity") in {"high", "critical"}:
                risks.append({
                    "severity": item.get("severity", "high"),
                    "title": item.get("title", ""),
                    "message": item.get("message", ""),
                    "project_id": item.get("context", {}).get("project_id", ""),
                })
        risks.sort(key=lambda item: self._severity_rank(item["severity"]), reverse=True)
        return risks[:12]

    def _render_dashboard_widgets(
        self,
        selected_template: Any,
        project_row: Dict[str, Any],
        project_kpi: Dict[str, Any],
        workplan_kpi: Dict[str, Any],
        district_rows: List[Dict[str, Any]],
        indicator_rows: List[Dict[str, Any]],
        trend: List[Dict[str, Any]],
        notifications: List[Dict[str, Any]],
        activity_rows: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        narrative: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        visuals = selected_template.visuals or []
        layout = selected_template.layout or []
        widgets = []
        for index, entry in enumerate(layout):
            visual_index = int(entry.get("visual_index", index))
            visual = visuals[visual_index] if 0 <= visual_index < len(visuals) else {}
            chart_type = str(entry.get("chart_type") or visual.get("chart_type") or "data_table")
            widgets.append({
                "widget_id": entry.get("widget_id") or f"widget_{index + 1}",
                "title": entry.get("title") or visual.get("title") or chart_type.replace("_", " ").title(),
                "chart_type": chart_type,
                "column_span": entry.get("column_span", 1),
                "row_span": entry.get("row_span", 1),
                "section": entry.get("section", "main"),
                "content": self._widget_content(
                    chart_type=chart_type,
                    project_row=project_row,
                    project_kpi=project_kpi,
                    workplan_kpi=workplan_kpi,
                    district_rows=district_rows,
                    indicator_rows=indicator_rows,
                    trend=trend,
                    notifications=notifications,
                    activity_rows=activity_rows,
                    metadata=metadata,
                    narrative=narrative,
                ),
            })
        return widgets

    def _widget_content(
        self,
        chart_type: str,
        project_row: Dict[str, Any],
        project_kpi: Dict[str, Any],
        workplan_kpi: Dict[str, Any],
        district_rows: List[Dict[str, Any]],
        indicator_rows: List[Dict[str, Any]],
        trend: List[Dict[str, Any]],
        notifications: List[Dict[str, Any]],
        activity_rows: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        narrative: Dict[str, Any],
    ) -> Dict[str, Any]:
        if chart_type == "kpi_cards":
            return {
                "cards": [
                    {"label": "Weighted progress", "value": project_kpi.get("progress_weighted_pct"), "suffix": "%"},
                    {"label": "Budget tracked", "value": project_kpi.get("budget_total"), "prefix": "$"},
                    {"label": "Overdue tasks", "value": workplan_kpi.get("tasks_overdue", 0)},
                    {"label": "Active alerts", "value": len(notifications)},
                ],
            }
        if chart_type in {"line_trend", "area_trend"}:
            return {
                "series": [
                    {"label": item.get("reporting_period", ""), "value": item.get("progress_weighted_pct")}
                    for item in trend[-6:]
                ],
            }
        if chart_type in {"bar_comparison", "variance_bar"}:
            return {
                "bars": [
                    {
                        "label": item.get("district") or item.get("indicator_name") or f"Row {index + 1}",
                        "value": item.get("progress_weighted_pct") or item.get("budget_total") or 0,
                        "secondary_value": item.get("budget_total") if chart_type == "variance_bar" else item.get("progress_mean_pct"),
                    }
                    for index, item in enumerate((district_rows or indicator_rows)[:6])
                ],
            }
        if chart_type == "status_donut":
            counts = {}
            for item in indicator_rows:
                key = item.get("status_mean_canon") or "SEM DADOS"
                counts[key] = counts.get(key, 0) + 1
            return {"segments": [{"label": key, "value": value} for key, value in counts.items()]}
        if chart_type == "bullet_or_gauge":
            return {
                "value": project_kpi.get("progress_weighted_pct"),
                "target": 100,
                "label": "Overall progress",
            }
        if chart_type == "project_status_summary":
            return {
                "summary": [
                    {"label": "Project", "value": project_row.get("project_name", "")},
                    {"label": "Donor", "value": metadata.get("donor", "")},
                    {"label": "Manager", "value": metadata.get("manager", "")},
                    {"label": "Current status", "value": project_kpi.get("status_mean_canon", "")},
                ],
            }
        if chart_type == "budget_vs_actual":
            return {
                "cards": [
                    {"label": "Budget total", "value": project_kpi.get("budget_total"), "prefix": "$"},
                    {"label": "Variance to plan", "value": metadata.get("budget_variance_pct"), "suffix": "%"},
                    {"label": "Tasks next 7 days", "value": workplan_kpi.get("tasks_next_7_days", 0)},
                ],
            }
        if chart_type == "activity_progress":
            return {
                "items": [
                    {
                        "title": item.get("activity_name", item.get("name", "")),
                        "status": item.get("status", ""),
                        "owner": item.get("owner", ""),
                        "due_date": item.get("due_date", ""),
                    }
                    for item in activity_rows[:6]
                ],
            }
        if chart_type == "notification_summary":
            return {"items": notifications[:6]}
        if chart_type == "map_placeholder":
            return {
                "districts": [
                    {
                        "province": item.get("province", ""),
                        "district": item.get("district", ""),
                        "value": item.get("progress_weighted_pct"),
                        "status": item.get("status_weighted_canon") or item.get("status_mean_canon"),
                    }
                    for item in district_rows[:8]
                ],
            }
        if chart_type == "narrative_panel":
            return {
                "summary": narrative.get("summary", ""),
                "insights": narrative.get("insights", [])[:5],
            }
        return {
            "summary": "Renderable demo placeholder",
            "insights": [f"Widget type '{chart_type}' is available for the demo renderer."],
        }

    def _scenario_notifications(self, scenario: str, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        project = snapshot["project"]
        executive = snapshot["executive"]
        if scenario == "donor_reporting":
            return [
                self._sim_notification("high", f"{project['project_name']}: donor report deadline approaching", "Narrative sections and budget commentary are due within 72 hours.", "Finalize the donor report preview and validate financial variance explanations."),
                self._sim_notification("medium", f"{project['project_name']}: one district update missing", "At least one district has not yet submitted the latest reporting package.", "Escalate to district focal points and confirm expected submission time."),
                self._sim_notification("medium", f"{project['project_name']}: reporting pack flagged for quality review", "The donor-facing pack includes moderate-quality data issues that should be reviewed.", "Open the Data Quality view and resolve the top issues before export."),
            ]
        if scenario == "risk_spike":
            return [
                self._sim_notification("critical", f"{project['project_name']}: implementation risk spike", "Field delivery conditions deteriorated and progress is at risk of slipping next cycle.", "Escalate to the project board and activate contingency actions immediately."),
                self._sim_notification("high", f"{project['project_name']}: budget variance widened", "Variance to plan moved outside the normal tolerance for this project.", "Review commitments, procurement timing, and donor reforecast assumptions."),
                self._sim_notification("medium", f"{project['project_name']}: follow-up narrative required", "Management will require a short explanation for the variance in the next review call.", "Generate a narrative brief and add corrective actions."),
            ]
        overdue_count = executive.get("tasks_overdue", 0)
        return [
            self._sim_notification("critical" if overdue_count >= 3 else "high", f"{project['project_name']}: overdue implementation actions", f"{overdue_count} overdue tasks are affecting project execution.", "Open the workplan snapshot and assign immediate recovery owners."),
            self._sim_notification("high", f"{project['project_name']}: alert simulation triggered", "The demo workspace simulated an overdue-alert escalation for management review.", "Use this output during the demo to explain how proactive alerts support project governance."),
            self._sim_notification("medium", f"{project['project_name']}: next coordination call should focus on slippage", "Recent delays suggest a focused coordination call is needed this week.", "Prepare a short action tracker and confirm due dates with responsible staff."),
        ]

    def _sim_notification(self, severity: str, title: str, message: str, suggested_action: str) -> Dict[str, Any]:
        return {
            "severity": severity,
            "source_type": "demo_simulation",
            "source_id": _safe_slug(title),
            "title": title,
            "message": message,
            "suggested_action": suggested_action,
            "context": {},
        }

    def _highest_severity(self, notifications: List[Dict[str, Any]]) -> str:
        if not notifications:
            return "info"
        return sorted((item.get("severity", "info") for item in notifications), key=self._severity_rank, reverse=True)[0]

    def _severity_rank(self, severity: str) -> int:
        mapping = {"low": 1, "info": 1, "medium": 2, "warn": 2, "high": 3, "critical": 4}
        return mapping.get(str(severity or "").strip().lower(), 0)

    def _is_past(self, value: str) -> bool:
        parsed = self.deps.parse_date_like_value(value)
        reference = self.deps.parse_date_like_value(self.deps.now_iso_utc())
        if parsed is None or reference is None:
            return False
        return parsed < reference

    def _datetime_sort_key(self, value: Any, default: datetime = UTC_DATETIME_MIN) -> datetime:
        return self.deps.parse_date_like_value(value) or default

    def _audience_title(self, audience: str) -> str:
        return {
            "donor": "Donor Review Brief",
            "management": "Management Brief",
            "meal": "MEAL Learning Brief",
        }[audience]


def _safe_slug(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text or "")).strip("_")
