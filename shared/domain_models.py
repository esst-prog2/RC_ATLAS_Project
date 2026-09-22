from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


RESULT_TYPES = ("goal", "outcome", "output")
INDICATOR_RESULT_TYPES = ("outcome", "output")


@dataclass
class OrganizationAccount:
    id: str
    organization_name: str
    status: str = "active"
    subscription_plan: str = "foundation"
    created_at: str = ""
    country: str = ""
    timezone: str = ""
    default_language: str = ""
    contact_email: str = ""
    contact_person: str = ""
    logo_placeholder: str = ""
    updated_at: str = ""


@dataclass
class TeamAccount:
    id: str
    organization_id: str = ""
    team_name: str = ""
    description: str = ""
    team_lead_user_id: str = ""
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""


@dataclass
class TidyDataset:
    id: str
    name: str
    description: str = ""
    source_type: str = "rows"
    organization_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    rows: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ReportingPeriodRecord:
    id: str
    reporting_period: str
    project_id: str = ""
    project_name: str = ""
    organization_id: str = ""
    indicator_id: str = ""
    indicator_name: str = ""
    country: str = ""
    province: str = ""
    district: str = ""
    actual_value: Optional[float] = None
    target_value: Optional[float] = None
    progress_value: Optional[float] = None
    budget_value: Optional[float] = None
    currency: str = ""
    status: str = ""
    owner: str = ""
    notes: str = ""
    source_dataset_id: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class SemanticMapping:
    id: str
    dataset_id: str
    name: str = "default"
    organization_id: str = ""
    fields: Dict[str, str] = field(default_factory=dict)
    status: str = "suggested"
    confidence: float = 0.0
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class DashboardTemplate:
    id: str
    name: str
    description: str = ""
    dashboard_type: str = ""
    organization_id: str = ""
    scope: str = "builtin"
    filters: List[str] = field(default_factory=list)
    visuals: List[Dict[str, Any]] = field(default_factory=list)
    layout: List[Dict[str, Any]] = field(default_factory=list)
    narrative_sections: List[str] = field(default_factory=list)
    theme: str = "studio_default"
    created_at: str = ""
    updated_at: str = ""


@dataclass
class NotificationRule:
    id: str
    name: str
    is_active: bool = True
    organization_id: str = ""
    schedule: str = "manual"
    channel: str = "webhook"
    provider: str = ""
    min_severity: str = "medium"
    condition_type: str = ""
    threshold: Optional[float] = None
    project_id: str = ""
    indicator_id: str = ""
    dataset_id: str = ""
    recipients: List[str] = field(default_factory=list)
    webhook_url: str = ""
    notes: str = ""
    last_run_at: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ResultNode:
    id: str
    organization_id: str
    project_id: str
    result_type: str
    title: str
    description: str = ""
    parent_id: str = ""
    display_order: int = 0
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        self.id = str(self.id or "").strip()
        self.organization_id = str(self.organization_id or "").strip()
        self.project_id = str(self.project_id or "").strip()
        self.result_type = str(self.result_type or "").strip().lower()
        self.title = str(self.title or "").strip()
        self.parent_id = str(self.parent_id or "").strip()
        self.status = str(self.status or "active").strip().lower() or "active"
        if not self.id or not self.organization_id or not self.project_id or not self.title:
            raise ValueError("Result nodes require id, organization_id, project_id, and title.")
        if self.result_type not in RESULT_TYPES:
            raise ValueError(f"Unsupported result type: '{self.result_type}'.")
        if self.result_type == "goal" and self.parent_id:
            raise ValueError("A Goal cannot have a parent result.")
        if self.result_type in {"outcome", "output"} and not self.parent_id:
            raise ValueError(f"A {self.result_type.title()} requires a parent result.")
        try:
            self.display_order = int(self.display_order)
        except (TypeError, ValueError) as exc:
            raise ValueError("Result display_order must be an integer.") from exc
        if self.display_order < 0:
            raise ValueError("Result display_order cannot be negative.")


@dataclass
class IndicatorResultLink:
    id: str
    organization_id: str
    project_id: str
    indicator_id: str
    result_id: str
    result_type: str
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        self.id = str(self.id or "").strip()
        self.organization_id = str(self.organization_id or "").strip()
        self.project_id = str(self.project_id or "").strip()
        self.indicator_id = str(self.indicator_id or "").strip()
        self.result_id = str(self.result_id or "").strip()
        self.result_type = str(self.result_type or "").strip().lower()
        if not all((self.id, self.organization_id, self.project_id, self.indicator_id, self.result_id)):
            raise ValueError("Indicator result links require stable ownership and relationship identifiers.")
        if self.result_type not in INDICATOR_RESULT_TYPES:
            raise ValueError("Indicators may link only to an Outcome or Output.")


@dataclass
class UserAccount:
    id: str
    username: str
    organization_id: str = ""
    full_name: str = ""
    email: str = ""
    role: str = "viewer"
    status: str = "active"
    permissions: List[str] = field(default_factory=list)
    password_salt: str = ""
    password_hash: str = ""
    api_token_hash: str = ""
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""
    last_login_at: str = ""
    team_id: str = ""


@dataclass
class AuditEvent:
    id: str
    occurred_at: str
    organization_id: str = ""
    actor_id: str = ""
    actor_username: str = ""
    actor_role: str = ""
    action: str = ""
    target_type: str = ""
    target_id: str = ""
    endpoint: str = ""
    outcome: str = "success"
    details: Dict[str, Any] = field(default_factory=dict)
