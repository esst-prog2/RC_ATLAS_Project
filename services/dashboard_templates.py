from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Optional

from .errors import ServiceError


@dataclass(frozen=True)
class DashboardTemplateServiceDependencies:
    load_data: Callable[[], Any]
    save_data: Callable[[Any], str]
    authorize_request: Callable[[Any, Optional[str], Optional[str], str], Any]
    append_audit_event: Callable[..., None]
    build_dashboard_recommendation_for_rows: Callable[[list[dict], str], Dict[str, Any]]
    build_builtin_dashboard_templates: Callable[[Any, Dict[str, Any]], list[Any]]
    find_tidy_dataset: Callable[[Any, str], Any]
    find_dashboard_template: Callable[[Any, str], Any]
    build_dashboard_template_from_payload: Callable[[Dict[str, Any], Optional[Any]], Any]
    upsert_dashboard_template: Callable[[Any, Any], str]


class DashboardTemplateService:
    def __init__(self, deps: DashboardTemplateServiceDependencies):
        self.deps = deps

    def list_templates(self, dataset_id: Optional[str] = None) -> Dict[str, Any]:
        data = self.deps.load_data()
        custom_templates = [asdict(item) for item in data.dashboard_templates]
        if not dataset_id:
            return {"builtin": [], "custom": custom_templates}

        dataset = self.deps.find_tidy_dataset(data, dataset_id)
        if dataset is None:
            raise ServiceError(404, f"Tidy dataset '{dataset_id}' not found.")
        recommendation = self.deps.build_dashboard_recommendation_for_rows(dataset.rows, dataset.name)
        builtins = [asdict(item) for item in self.deps.build_builtin_dashboard_templates(dataset, recommendation)]
        return {"builtin": builtins, "custom": custom_templates}

    def save_template(
        self,
        payload: Dict[str, Any],
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="WORKSPACE_ADMIN")
        existing = self.deps.find_dashboard_template(data, str(payload.get("id"))) if payload.get("id") else None
        try:
            template = self.deps.build_dashboard_template_from_payload(payload, existing=existing)
        except ValueError as exc:
            raise ServiceError(400, str(exc)) from exc

        action = self.deps.upsert_dashboard_template(data, template)
        self.deps.append_audit_event(
            data,
            action=f"dashboard_template.{action}",
            target_type="dashboard_template",
            target_id=template.id,
            actor=actor,
            endpoint="/v1/dashboard_templates",
            details={
                "name": template.name,
                "dashboard_type": template.dashboard_type,
                "layout_widgets": len(template.layout),
            },
        )
        saved_path = self.deps.save_data(data)
        return {
            "ok": True,
            "action": action,
            "saved_to": saved_path,
            "template": asdict(template),
        }
