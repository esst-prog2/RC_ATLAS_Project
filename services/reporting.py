from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .errors import ServiceError


UTC_DATETIME_MIN = datetime.min.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class ReportingServiceDependencies:
    load_data: Callable[[], Any]
    save_data: Callable[[Any], str]
    authorize_request: Callable[[Any, Optional[str], Optional[str], str], Any]
    append_audit_event: Callable[..., None]
    now_iso_utc: Callable[[], str]
    parse_date_like_value: Callable[[Any], Any]
    find_project: Callable[[Any, str], Any]
    find_indicator: Callable[[Any, str], Any]
    find_tidy_dataset: Callable[[Any, str], Any]
    build_dataset_payload: Callable[[Any, Any], Dict[str, Any]]
    build_tidy_dataset_notifications: Callable[[Any], List[Dict[str, Any]]]
    effective_semantic_mapping: Callable[[Any, Any], Any]
    find_semantic_mapping: Callable[[Any, str], Any]
    build_semantic_mapping_from_payload: Callable[[Dict[str, Any], str, Optional[Any]], Any]
    upsert_semantic_mapping: Callable[[Any, Any], str]
    build_tidy_dataset_quality_report: Callable[[Any, Any], Dict[str, Any]]
    build_dataset_narrative_summary: Callable[[Any, Any], Dict[str, Any]]
    build_dashboard_blueprint: Callable[[Any, Any, Optional[str]], Dict[str, Any]]
    infer_reporting_history_mapping: Callable[[List[Dict[str, Any]]], Dict[str, Any]]
    build_dashboard_recommendation_for_rows: Callable[[List[Dict[str, Any]], str], Dict[str, Any]]
    build_tidy_dataset_from_payload: Callable[[Dict[str, Any], Optional[Any]], Any]
    upsert_tidy_dataset: Callable[[Any, Any], str]
    materialize_reporting_records_from_tidy_dataset: Callable[[Any, Any], Dict[str, Any]]
    build_reporting_record_from_payload: Callable[[Dict[str, Any], Any, str], Any]
    upsert_reporting_records: Callable[[Any, List[Any]], Dict[str, Any]]
    latest_reporting_period: Callable[[List[Any]], Optional[str]]
    reporting_record_to_dict: Callable[[Any, Any], Dict[str, Any]]
    build_portfolio_trend_series: Callable[[Any], List[Dict[str, Any]]]
    build_portfolio_narrative_summary: Callable[[Any], Dict[str, Any]]
    build_project_trend_series: Callable[[Any, str], List[Dict[str, Any]]]
    build_project_narrative_summary: Callable[[Any, str], Dict[str, Any]]
    build_indicator_trend_series: Callable[[Any, str, str], List[Dict[str, Any]]]
    optional_text_field: Callable[[Dict[str, Any], str, str], str]


class ReportingService:
    def __init__(self, deps: ReportingServiceDependencies):
        self.deps = deps

    def _require_project(self, data: Any, project_id: str) -> Any:
        project = self.deps.find_project(data, project_id)
        if project is None:
            raise ServiceError(404, f"Project '{project_id}' not found.")
        return project

    def _require_indicator(self, project: Any, project_id: str, indicator_id: str) -> Any:
        indicator = self.deps.find_indicator(project, indicator_id)
        if indicator is None:
            raise ServiceError(404, f"Indicator '{indicator_id}' not found in project '{project_id}'.")
        return indicator

    def _require_dataset(self, data: Any, dataset_id: str) -> Any:
        dataset = self.deps.find_tidy_dataset(data, dataset_id)
        if dataset is None:
            raise ServiceError(404, f"Tidy dataset '{dataset_id}' not found.")
        return dataset

    def list_reporting_records(
        self,
        project_id: Optional[str] = None,
        indicator_id: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        data = self.deps.load_data()
        records = data.reporting_records
        if project_id:
            records = [record for record in records if record.project_id == project_id]
        if indicator_id:
            records = [record for record in records if record.indicator_id == indicator_id]
        records = sorted(
            records,
            key=lambda record: self.deps.parse_date_like_value(record.reporting_period) or UTC_DATETIME_MIN,
            reverse=True,
        )
        return [self.deps.reporting_record_to_dict(record, data) for record in records[:limit]]

    def portfolio_trends(self) -> Dict[str, Any]:
        data = self.deps.load_data()
        return {
            "generated_at": self.deps.now_iso_utc(),
            "series": self.deps.build_portfolio_trend_series(data),
        }

    def portfolio_narrative(self) -> Dict[str, Any]:
        data = self.deps.load_data()
        return self.deps.build_portfolio_narrative_summary(data)

    def project_trends(self, project_id: str) -> Dict[str, Any]:
        data = self.deps.load_data()
        project = self._require_project(data, project_id)
        return {
            "project_id": project.id,
            "project_name": project.name,
            "series": self.deps.build_project_trend_series(data, project_id),
        }

    def project_narrative(self, project_id: str) -> Dict[str, Any]:
        data = self.deps.load_data()
        try:
            return self.deps.build_project_narrative_summary(data, project_id)
        except ValueError as exc:
            raise ServiceError(404, str(exc)) from exc

    def indicator_trends(self, project_id: str, indicator_id: str) -> Dict[str, Any]:
        data = self.deps.load_data()
        project = self._require_project(data, project_id)
        indicator = self._require_indicator(project, project_id, indicator_id)
        return {
            "project_id": project.id,
            "project_name": project.name,
            "indicator_id": indicator.id,
            "indicator_name": indicator.name,
            "series": self.deps.build_indicator_trend_series(data, project_id, indicator_id),
        }

    def list_tidy_datasets(self) -> List[Dict[str, Any]]:
        data = self.deps.load_data()
        return [self.deps.build_dataset_payload(data, dataset) for dataset in data.tidy_datasets]

    def get_tidy_dataset_detail(self, dataset_id: str) -> Dict[str, Any]:
        data = self.deps.load_data()
        dataset = self._require_dataset(data, dataset_id)
        payload = self.deps.build_dataset_payload(data, dataset)
        payload["preview_rows"] = dataset.rows[:20]
        payload["notifications"] = self.deps.build_tidy_dataset_notifications(dataset)
        return payload

    def get_tidy_dataset_semantic_mapping(self, dataset_id: str) -> Dict[str, Any]:
        data = self.deps.load_data()
        dataset = self._require_dataset(data, dataset_id)
        return asdict(self.deps.effective_semantic_mapping(data, dataset))

    def save_tidy_dataset_semantic_mapping(
        self,
        dataset_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="EDIT_INDICATORS")
        self._require_dataset(data, dataset_id)
        existing = self.deps.find_semantic_mapping(data, dataset_id)
        try:
            mapping = self.deps.build_semantic_mapping_from_payload(payload, dataset_id, existing=existing)
        except ValueError as exc:
            raise ServiceError(400, str(exc)) from exc
        action = self.deps.upsert_semantic_mapping(data, mapping)
        self.deps.append_audit_event(
            data,
            action=f"semantic_mapping.{action}",
            target_type="semantic_mapping",
            target_id=mapping.id,
            actor=actor,
            endpoint=f"/v1/tidy_datasets/{dataset_id}/semantic_mapping",
            details={"dataset_id": dataset_id, "status": mapping.status},
        )
        saved_path = self.deps.save_data(data)
        return {
            "ok": True,
            "action": action,
            "saved_to": saved_path,
            "mapping": asdict(mapping),
        }

    def get_tidy_dataset_quality(self, dataset_id: str) -> Dict[str, Any]:
        data = self.deps.load_data()
        dataset = self._require_dataset(data, dataset_id)
        return self.deps.build_tidy_dataset_quality_report(data, dataset)

    def get_tidy_dataset_narrative(self, dataset_id: str) -> Dict[str, Any]:
        data = self.deps.load_data()
        dataset = self._require_dataset(data, dataset_id)
        return self.deps.build_dataset_narrative_summary(data, dataset)

    def get_tidy_dataset_dashboard_blueprint(
        self,
        dataset_id: str,
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        dataset = self._require_dataset(data, dataset_id)
        return self.deps.build_dashboard_blueprint(data, dataset, template_id=template_id)

    def get_tidy_dataset_history_mapping(self, dataset_id: str) -> Dict[str, Any]:
        data = self.deps.load_data()
        dataset = self._require_dataset(data, dataset_id)
        return self.deps.infer_reporting_history_mapping(dataset.rows)

    def get_tidy_dataset_dashboard_suggestions(self, dataset_id: str) -> Dict[str, Any]:
        data = self.deps.load_data()
        dataset = self._require_dataset(data, dataset_id)
        return self.deps.build_dashboard_recommendation_for_rows(dataset.rows, dataset.name)

    def import_tidy_dataset(
        self,
        payload: Dict[str, Any],
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="EDIT_INDICATORS")
        existing = self.deps.find_tidy_dataset(data, str(payload.get("id"))) if payload.get("id") else None
        try:
            dataset = self.deps.build_tidy_dataset_from_payload(payload, existing=existing)
        except ValueError as exc:
            raise ServiceError(400, str(exc)) from exc

        action = self.deps.upsert_tidy_dataset(data, dataset)
        self.deps.append_audit_event(
            data,
            action=f"tidy_dataset.{action}",
            target_type="tidy_dataset",
            target_id=dataset.id,
            actor=actor,
            endpoint="/v1/tidy_datasets/import",
            details={"name": dataset.name, "row_count": len(dataset.rows), "source_type": dataset.source_type},
        )
        saved_path = self.deps.save_data(data)
        recommendation = self.deps.build_dashboard_recommendation_for_rows(dataset.rows, dataset.name)
        return {
            "ok": True,
            "action": action,
            "saved_to": saved_path,
            "dataset_id": dataset.id,
            "row_count": len(dataset.rows),
            "dashboard_type": recommendation["dashboard_type"],
            "recommended_visuals": recommendation["recommended_visuals"],
        }

    def materialize_history(
        self,
        dataset_id: str,
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="EDIT_INDICATORS")
        dataset = self._require_dataset(data, dataset_id)
        try:
            summary = self.deps.materialize_reporting_records_from_tidy_dataset(data, dataset)
        except ValueError as exc:
            raise ServiceError(400, str(exc)) from exc
        self.deps.append_audit_event(
            data,
            action="reporting_history.materialized",
            target_type="tidy_dataset",
            target_id=dataset.id,
            actor=actor,
            endpoint=f"/v1/tidy_datasets/{dataset_id}/materialize_history",
            details=summary,
        )
        saved_path = self.deps.save_data(data)
        return {
            "ok": True,
            "saved_to": saved_path,
            "summary": summary,
        }

    def import_reporting_records(
        self,
        payload: Dict[str, Any],
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="EDIT_INDICATORS")
        records_payload = payload.get("records")
        if not isinstance(records_payload, list):
            raise ServiceError(400, "'records' must be a list of reporting record objects.")

        source_dataset_id = self.deps.optional_text_field(payload, "source_dataset_id")
        records: List[Any] = []
        try:
            for record_payload in records_payload:
                if not isinstance(record_payload, dict):
                    raise ValueError("Each reporting record must be a JSON object.")
                records.append(
                    self.deps.build_reporting_record_from_payload(
                        record_payload,
                        data,
                        source_dataset_id=source_dataset_id,
                    )
                )
        except ValueError as exc:
            raise ServiceError(400, str(exc)) from exc

        summary = self.deps.upsert_reporting_records(data, records)
        self.deps.append_audit_event(
            data,
            action="reporting_records.imported",
            target_type="reporting_records",
            target_id=source_dataset_id or "batch",
            actor=actor,
            endpoint="/v1/reporting_records/import",
            details={"count": len(records), **summary},
        )
        saved_path = self.deps.save_data(data)
        return {
            "ok": True,
            "saved_to": saved_path,
            "summary": summary,
            "latest_reporting_period": self.deps.latest_reporting_period(data.reporting_records),
        }
