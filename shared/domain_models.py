from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
