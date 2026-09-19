from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Tuple


@dataclass(frozen=True)
class DemoSeedCredential:
    username: str
    password: str
    role: str
    full_name: str
    email: str


@dataclass(frozen=True)
class DemoSeedBundle:
    payload: Dict[str, Any]
    credentials: List[DemoSeedCredential]
    default_project_id: str
    default_dataset_id: str
    finance_dataset_id: str
    default_username: str
    default_email: str

    def to_summary(self) -> Dict[str, Any]:
        return {
            "projects": len(self.payload.get("projects", [])),
            "datasets": len(self.payload.get("tidy_datasets", [])),
            "reporting_records": len(self.payload.get("reporting_records", [])),
            "templates": len(self.payload.get("dashboard_templates", [])),
            "notification_rules": len(self.payload.get("notification_rules", [])),
            "users": len(self.payload.get("users", [])),
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _month_start(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _shift_months(dt: datetime, offset: int) -> datetime:
    year = dt.year
    month = dt.month + offset
    while month > 12:
        month -= 12
        year += 1
    while month < 1:
        month += 12
        year -= 1
    return dt.replace(year=year, month=month, day=1)


def _slug(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text or "")).strip("_")


def _project_row(
    project_id: str,
    project_name: str,
    donor: str,
    manager: str,
    implementing_partner: str,
    sector: str,
    country: str,
    province: str,
    district: str,
    latitude: float,
    longitude: float,
    indicator_id: str,
    indicator_name: str,
    indicator_level: str,
    reporting_period: str,
    actual_value: float,
    target_value: float,
    progress_value: float,
    budget_value: float,
    status: str,
    owner: str,
    risk_level: str,
    beneficiary_group: str,
    budget_variance_pct: float,
) -> Dict[str, Any]:
    return {
        "portfolio": "Mozambique Country Portfolio",
        "donor": donor,
        "project_id": project_id,
        "project_name": project_name,
        "project_manager": manager,
        "implementing_partner": implementing_partner,
        "sector": sector,
        "country": country,
        "province": province,
        "district": district,
        "latitude": latitude,
        "longitude": longitude,
        "indicator_id": indicator_id,
        "indicator_name": indicator_name,
        "indicator_level": indicator_level,
        "reporting_month": reporting_period,
        "actual_value": round(actual_value, 3),
        "target_value": round(target_value, 3),
        "progress_value": round(progress_value, 3),
        "budget_value": round(budget_value, 3),
        "currency": "USD",
        "status": status,
        "owner": owner,
        "risk_level": risk_level,
        "beneficiary_group": beneficiary_group,
        "budget_variance_pct": round(budget_variance_pct, 2),
    }


def build_demo_seed_bundle(
    build_password_hash: Callable[[str], Tuple[str, str]],
) -> DemoSeedBundle:
    now = _utc_now()
    created_at = _iso(now - timedelta(days=2))
    updated_at = _iso(now)
    organization_id = "org_blue_delta"
    organization_name = "Blue Delta Consortium"
    organization_country = "Mozambique"
    organization_timezone = "Africa/Maputo"
    organization_language = "EN"
    organization_contact_email = "operations@bluedelta.org"
    organization_contact_person = "Amina Duarte"
    organization_logo_placeholder = "blue-delta-consortium-mark"
    periods = [
        _iso(_shift_months(_month_start(now), -3)),
        _iso(_shift_months(_month_start(now), -2)),
        _iso(_shift_months(_month_start(now), -1)),
        _iso(_month_start(now)),
    ]

    # Fictional local-demo identities and credentials. Never use these values in
    # production or for accounts outside the disposable RC Atlas demo workspace.
    credentials = [
        DemoSeedCredential("org.admin", "AtlasAdmin!2026", "organization_admin", "Amina Duarte", "amina.duarte@bluedelta.org"),
        DemoSeedCredential("teresa.mbanze", "TeresaPM!2026", "programme_manager", "Teresa Mbanze", "teresa.mbanze@bluedelta.org"),
        DemoSeedCredential("raimundo.cumba", "RaimundoMEAL!2026", "meal_officer", "Raimundo Cumba", "raimundo.cumba@bluedelta.org"),
        DemoSeedCredential("aline.duarte", "AlineField!2026", "field_coordinator", "Aline Duarte", "aline.duarte@bluedelta.org"),
        DemoSeedCredential("executive.director", "ExecutiveView!2026", "executive_viewer", "Executive Director", "executive.director@bluedelta.org"),
    ]
    default_teams = [
        {
            "id": "team_management",
            "organization_id": organization_id,
            "team_name": "Management",
            "description": "Executive and programme oversight for the portfolio.",
            "team_lead_user_id": "user_demo_1",
            "status": "active",
            "created_at": created_at,
            "updated_at": updated_at,
        },
        {
            "id": "team_meal",
            "organization_id": organization_id,
            "team_name": "MEAL",
            "description": "Monitoring, evaluation, accountability, and learning coordination.",
            "team_lead_user_id": "user_demo_3",
            "status": "active",
            "created_at": created_at,
            "updated_at": updated_at,
        },
        {
            "id": "team_field_ops",
            "organization_id": organization_id,
            "team_name": "Field Operations",
            "description": "District implementation and field execution follow-up.",
            "team_lead_user_id": "user_demo_4",
            "status": "active",
            "created_at": created_at,
            "updated_at": updated_at,
        },
        {
            "id": "team_programme_ops",
            "organization_id": organization_id,
            "team_name": "Programme Operations",
            "description": "Cross-project coordination, workplan management, and delivery assurance.",
            "team_lead_user_id": "user_demo_2",
            "status": "active",
            "created_at": created_at,
            "updated_at": updated_at,
        },
    ]
    user_team_map = {
        "organization_admin": "team_management",
        "programme_manager": "team_programme_ops",
        "meal_officer": "team_meal",
        "field_coordinator": "team_field_ops",
        "executive_viewer": "team_management",
    }

    users = []
    for index, item in enumerate(credentials, start=1):
        salt, password_hash = build_password_hash(item.password)
        users.append({
            "id": f"user_demo_{index}",
            "username": item.username,
            "organization_id": organization_id,
            "team_id": user_team_map.get(item.role, ""),
            "full_name": item.full_name,
            "email": item.email,
            "role": item.role,
            "status": "active",
            "password_salt": salt,
            "password_hash": password_hash,
            "api_token_hash": "",
            "is_active": True,
            "created_at": created_at,
            "updated_at": updated_at,
            "last_login_at": "",
        })

    project_specs = [
        {
            "id": "proj_resilience",
            "project_code": "CRLP-001",
            "programme": "Coastal Resilience Portfolio",
            "name": "Coastal Resilience and Livelihoods Programme",
            "objective": "Protect climate-vulnerable households through early warning systems, resilient agriculture, and local response capacity.",
            "donor": "ECHO",
            "manager": "Teresa Mbanze",
            "partner": "Blue Delta Consortium",
            "sector": "Climate Resilience",
            "country": "Mozambique",
            "start_date": "2026-01-15",
            "end_date": "2027-12-31",
            "owner": "Field Coordination Unit",
            "districts": [
                {"province": "Sofala", "district": "Buzi", "latitude": -19.886, "longitude": 34.844},
                {"province": "Sofala", "district": "Dondo", "latitude": -19.609, "longitude": 34.743},
                {"province": "Sofala", "district": "Nhamatanda", "latitude": -19.118, "longitude": 34.281},
            ],
            "indicators": [
                {
                    "id": "ind_res_households",
                    "name": "Households receiving resilience support",
                    "unit": "households",
                    "frequency": "monthly",
                    "direction": "up",
                    "level": "outcome",
                    "baseline": 3200,
                    "target": 12000,
                    "beneficiary_group": "Crisis-affected households",
                    "locations": [
                        {"target": 4200, "budget": 225000, "monthly_actuals": [2100, 2600, 3200, 3560]},
                        {"target": 3800, "budget": 205000, "monthly_actuals": [1850, 2330, 2740, 3040]},
                        {"target": 4000, "budget": 215000, "monthly_actuals": [1900, 2450, 2890, 3320]},
                    ],
                },
                {
                    "id": "ind_res_committees",
                    "name": "Functional community preparedness committees",
                    "unit": "committees",
                    "frequency": "monthly",
                    "direction": "up",
                    "level": "output",
                    "baseline": 12,
                    "target": 45,
                    "beneficiary_group": "Community leaders",
                    "locations": [
                        {"target": 15, "budget": 60000, "monthly_actuals": [9, 11, 13, 14]},
                        {"target": 15, "budget": 59000, "monthly_actuals": [8, 9, 10, 11]},
                        {"target": 15, "budget": 61000, "monthly_actuals": [9, 10, 11, 12]},
                    ],
                },
                {
                    "id": "ind_res_agriculture",
                    "name": "Hectares under climate-smart agriculture",
                    "unit": "hectares",
                    "frequency": "monthly",
                    "direction": "up",
                    "level": "outcome",
                    "baseline": 640,
                    "target": 2500,
                    "beneficiary_group": "Farmer groups",
                    "locations": [
                        {"target": 900, "budget": 112000, "monthly_actuals": [430, 510, 620, 720]},
                        {"target": 800, "budget": 101000, "monthly_actuals": [360, 430, 520, 580]},
                        {"target": 800, "budget": 103000, "monthly_actuals": [380, 470, 550, 640]},
                    ],
                },
            ],
            "activities": [
                {
                    "id": "act_res_assessments",
                    "name": "Village preparedness reviews completed",
                    "owner": "District Resilience Officer",
                    "start_offset_days": -85,
                    "due_offset_days": -5,
                    "status": "ongoing",
                    "linked_indicator_ids": ["ind_res_committees"],
                    "tasks": [
                        {"id": "task_res_1", "name": "Finalize Nhamatanda review memo", "owner": "Aline", "due_offset_days": -12, "status": "doing"},
                        {"id": "task_res_2", "name": "Share action tracker with partner", "owner": "Joao", "due_offset_days": -3, "status": "todo"},
                    ],
                },
                {
                    "id": "act_res_training",
                    "name": "Household targeting and referral refresh",
                    "owner": "Programme Manager",
                    "start_offset_days": -44,
                    "due_offset_days": 11,
                    "status": "ongoing",
                    "linked_indicator_ids": ["ind_res_households"],
                    "tasks": [
                        {"id": "task_res_3", "name": "Approve participant list", "owner": "Teresa", "due_offset_days": 2, "status": "doing"},
                        {"id": "task_res_4", "name": "Close training venue contract", "owner": "Marta", "due_offset_days": 8, "status": "todo"},
                    ],
                },
                {
                    "id": "act_res_demo",
                    "name": "Climate-smart agriculture plots monitored",
                    "owner": "Agriculture Specialist",
                    "start_offset_days": -60,
                    "due_offset_days": 14,
                    "status": "ongoing",
                    "linked_indicator_ids": ["ind_res_agriculture"],
                    "tasks": [
                        {"id": "task_res_5", "name": "Field supervision visit", "owner": "Antonio", "due_offset_days": -1, "status": "todo"},
                        {"id": "task_res_6", "name": "Compile yield snapshots", "owner": "Bruna", "due_offset_days": 6, "status": "doing"},
                    ],
                },
            ],
        },
        {
            "id": "proj_health",
            "project_code": "CHAI-002",
            "programme": "Primary Health Access Portfolio",
            "name": "Community Health Access Initiative",
            "objective": "Improve primary health service delivery and reduce stock-outs in underserved districts.",
            "donor": "USAID",
            "manager": "Helena Cuamba",
            "partner": "Vida Rural Alliance",
            "sector": "Primary Health",
            "country": "Mozambique",
            "start_date": "2026-02-01",
            "end_date": "2027-11-30",
            "owner": "Health Programme Unit",
            "districts": [
                {"province": "Nampula", "district": "Angoche", "latitude": -16.233, "longitude": 39.91},
                {"province": "Nampula", "district": "Monapo", "latitude": -15.237, "longitude": 39.105},
                {"province": "Cabo Delgado", "district": "Mueda", "latitude": -11.672, "longitude": 39.563},
            ],
            "indicators": [
                {
                    "id": "ind_health_coverage",
                    "name": "Children fully immunized before age one",
                    "unit": "%",
                    "frequency": "monthly",
                    "direction": "up",
                    "level": "outcome",
                    "baseline": 58,
                    "target": 90,
                    "beneficiary_group": "Children under one",
                    "locations": [
                        {"target": 90, "budget": 165000, "monthly_actuals": [64, 68, 72, 76]},
                        {"target": 90, "budget": 158000, "monthly_actuals": [61, 65, 69, 72]},
                        {"target": 90, "budget": 172000, "monthly_actuals": [55, 58, 61, 67]},
                    ],
                },
                {
                    "id": "ind_health_chw",
                    "name": "Community health workers supervised on schedule",
                    "unit": "workers",
                    "frequency": "monthly",
                    "direction": "up",
                    "level": "output",
                    "baseline": 90,
                    "target": 240,
                    "beneficiary_group": "Community health workers",
                    "locations": [
                        {"target": 80, "budget": 72000, "monthly_actuals": [48, 56, 63, 70]},
                        {"target": 80, "budget": 68000, "monthly_actuals": [45, 51, 58, 64]},
                        {"target": 80, "budget": 74000, "monthly_actuals": [38, 46, 54, 61]},
                    ],
                },
                {
                    "id": "ind_health_stockout",
                    "name": "Essential medicine stock-out rate",
                    "unit": "%",
                    "frequency": "monthly",
                    "direction": "down",
                    "level": "outcome",
                    "baseline": 28,
                    "target": 5,
                    "beneficiary_group": "Primary health facilities",
                    "locations": [
                        {"target": 5, "budget": 95000, "monthly_actuals": [20, 16, 13, 11]},
                        {"target": 5, "budget": 91000, "monthly_actuals": [24, 20, 18, 16]},
                        {"target": 5, "budget": 99000, "monthly_actuals": [26, 23, 21, 19]},
                    ],
                },
            ],
            "activities": [
                {
                    "id": "act_health_supervision",
                    "name": "Quarterly supervision wave completed",
                    "owner": "Regional MEAL Lead",
                    "start_offset_days": -52,
                    "due_offset_days": -9,
                    "status": "ongoing",
                    "linked_indicator_ids": ["ind_health_chw"],
                    "tasks": [
                        {"id": "task_health_1", "name": "Resolve missing Mueda supervision forms", "owner": "Helena", "due_offset_days": -14, "status": "todo"},
                        {"id": "task_health_2", "name": "Upload supervision dashboard pack", "owner": "Paulo", "due_offset_days": -2, "status": "doing"},
                    ],
                },
                {
                    "id": "act_health_supply",
                    "name": "Stock-out root cause action plan",
                    "owner": "Supply Chain Advisor",
                    "start_offset_days": -39,
                    "due_offset_days": 4,
                    "status": "ongoing",
                    "linked_indicator_ids": ["ind_health_stockout"],
                    "tasks": [
                        {"id": "task_health_3", "name": "Verify Angoche redistribution", "owner": "Rita", "due_offset_days": 1, "status": "doing"},
                        {"id": "task_health_4", "name": "Review transport framework", "owner": "Edson", "due_offset_days": 6, "status": "todo"},
                    ],
                },
                {
                    "id": "act_health_outreach",
                    "name": "Catch-up outreach sessions",
                    "owner": "District Health Promoter",
                    "start_offset_days": -28,
                    "due_offset_days": 18,
                    "status": "ongoing",
                    "linked_indicator_ids": ["ind_health_coverage"],
                    "tasks": [
                        {"id": "task_health_5", "name": "Confirm vaccine stock buffer", "owner": "Sergio", "due_offset_days": 2, "status": "todo"},
                        {"id": "task_health_6", "name": "Approve outreach mobilization budget", "owner": "Lina", "due_offset_days": -1, "status": "doing"},
                    ],
                },
            ],
        },
        {
            "id": "proj_education",
            "project_code": "GLPA-003",
            "programme": "Girls Learning Portfolio",
            "name": "Girls Learning and Protection Accelerator",
            "objective": "Improve girls' retention, safeguarding, and transition outcomes in fragile education districts.",
            "donor": "FCDO",
            "manager": "Madalena Cumbe",
            "partner": "Educa Mais Network",
            "sector": "Education and Protection",
            "country": "Mozambique",
            "start_date": "2026-03-01",
            "end_date": "2027-09-30",
            "owner": "Education Programme Unit",
            "districts": [
                {"province": "Manica", "district": "Macate", "latitude": -19.882, "longitude": 33.338},
                {"province": "Tete", "district": "Tsangano", "latitude": -15.543, "longitude": 34.624},
                {"province": "Tete", "district": "Moatize", "latitude": -16.104, "longitude": 33.742},
            ],
            "indicators": [
                {
                    "id": "ind_edu_retention",
                    "name": "Girls retained through transition cycle",
                    "unit": "%",
                    "frequency": "monthly",
                    "direction": "up",
                    "level": "outcome",
                    "baseline": 63,
                    "target": 88,
                    "beneficiary_group": "Adolescent girls",
                    "locations": [
                        {"target": 88, "budget": 138000, "monthly_actuals": [70, 73, 76, 79]},
                        {"target": 88, "budget": 129000, "monthly_actuals": [67, 69, 71, 74]},
                        {"target": 88, "budget": 134000, "monthly_actuals": [65, 67, 69, 72]},
                    ],
                },
                {
                    "id": "ind_edu_safeguarding",
                    "name": "Schools with safeguarding clubs active",
                    "unit": "schools",
                    "frequency": "monthly",
                    "direction": "up",
                    "level": "output",
                    "baseline": 18,
                    "target": 54,
                    "beneficiary_group": "School leadership",
                    "locations": [
                        {"target": 18, "budget": 52000, "monthly_actuals": [10, 11, 13, 15]},
                        {"target": 18, "budget": 50000, "monthly_actuals": [9, 10, 11, 13]},
                        {"target": 18, "budget": 53000, "monthly_actuals": [8, 9, 11, 12]},
                    ],
                },
                {
                    "id": "ind_edu_coaching",
                    "name": "Teacher coaching visits completed",
                    "unit": "visits",
                    "frequency": "monthly",
                    "direction": "up",
                    "level": "output",
                    "baseline": 24,
                    "target": 96,
                    "beneficiary_group": "Teachers",
                    "locations": [
                        {"target": 32, "budget": 47000, "monthly_actuals": [16, 19, 22, 26]},
                        {"target": 32, "budget": 45000, "monthly_actuals": [14, 17, 20, 24]},
                        {"target": 32, "budget": 45500, "monthly_actuals": [12, 16, 18, 21]},
                    ],
                },
            ],
            "activities": [
                {
                    "id": "act_edu_safeguarding",
                    "name": "School safeguarding club refresh",
                    "owner": "Protection Coordinator",
                    "start_offset_days": -33,
                    "due_offset_days": -6,
                    "status": "ongoing",
                    "linked_indicator_ids": ["ind_edu_safeguarding"],
                    "tasks": [
                        {"id": "task_edu_1", "name": "Confirm Tsangano facilitator roster", "owner": "Madalena", "due_offset_days": -7, "status": "doing"},
                        {"id": "task_edu_2", "name": "Print reporting forms", "owner": "Zelia", "due_offset_days": -2, "status": "todo"},
                    ],
                },
                {
                    "id": "act_edu_coaching",
                    "name": "Instructional coaching sprint",
                    "owner": "Education Specialist",
                    "start_offset_days": -48,
                    "due_offset_days": 9,
                    "status": "ongoing",
                    "linked_indicator_ids": ["ind_edu_coaching"],
                    "tasks": [
                        {"id": "task_edu_3", "name": "Approve coach travel advances", "owner": "Ramos", "due_offset_days": 1, "status": "doing"},
                        {"id": "task_edu_4", "name": "Close observation feedback loop", "owner": "Vania", "due_offset_days": 5, "status": "todo"},
                    ],
                },
                {
                    "id": "act_edu_retention",
                    "name": "Transition support package rollout",
                    "owner": "Girls Education Lead",
                    "start_offset_days": -61,
                    "due_offset_days": 16,
                    "status": "ongoing",
                    "linked_indicator_ids": ["ind_edu_retention"],
                    "tasks": [
                        {"id": "task_edu_5", "name": "Finalize bursary shortlist", "owner": "Lourdes", "due_offset_days": 3, "status": "todo"},
                        {"id": "task_edu_6", "name": "Escalate attendance dip in Moatize", "owner": "Silvia", "due_offset_days": -4, "status": "doing"},
                    ],
                },
            ],
        },
    ]

    projects = []
    ops_by_project: Dict[str, Any] = {}
    reporting_records = []
    main_rows: List[Dict[str, Any]] = []
    finance_rows: List[Dict[str, Any]] = []

    status_labels = ["verde", "amarelo", "vermelho"]
    risk_labels = ["low", "medium", "high"]
    task_assignees = {item.role: item for item in credentials}
    task_assignment_roles = {
        "task_res_1": "field_coordinator",
        "task_res_2": "programme_manager",
        "task_res_3": "programme_manager",
        "task_res_4": "programme_manager",
        "task_res_5": "field_coordinator",
        "task_res_6": "meal_officer",
        "task_health_1": "meal_officer",
        "task_health_2": "meal_officer",
        "task_health_3": "field_coordinator",
        "task_health_4": "programme_manager",
        "task_health_5": "field_coordinator",
        "task_health_6": "programme_manager",
        "task_edu_1": "field_coordinator",
        "task_edu_2": "meal_officer",
        "task_edu_3": "programme_manager",
        "task_edu_4": "meal_officer",
        "task_edu_5": "field_coordinator",
        "task_edu_6": "programme_manager",
    }
    task_workflow_states = {
        "task_res_1": "pending_validation",
        "task_res_2": "overdue",
        "task_res_3": "in_progress",
        "task_res_4": "not_started",
        "task_res_5": "in_progress",
        "task_res_6": "in_progress",
        "task_health_1": "overdue",
        "task_health_2": "completed",
        "task_health_3": "in_progress",
        "task_health_4": "not_started",
        "task_health_5": "not_started",
        "task_health_6": "overdue",
        "task_edu_1": "overdue",
        "task_edu_2": "not_started",
        "task_edu_3": "in_progress",
        "task_edu_4": "not_started",
        "task_edu_5": "not_started",
        "task_edu_6": "escalated",
    }
    task_progress_by_status = {
        "not_started": 0.0,
        "in_progress": 52.0,
        "pending_validation": 90.0,
        "overdue": 35.0,
        "escalated": 40.0,
        "completed": 100.0,
    }
    task_evidence = {
        "task_res_1": ["Fictional Nhamatanda review memo evidence package"],
        "task_health_2": ["Fictional supervision dashboard evidence pack"],
    }

    for project_index, project in enumerate(project_specs):
        indicator_entries = []
        project_budget_total = 0.0

        for indicator_index, indicator in enumerate(project["indicators"]):
            location_entries = []
            for district_index, district in enumerate(project["districts"]):
                location_spec = indicator["locations"][district_index]
                latest_actual = float(location_spec["monthly_actuals"][-1])
                location_entries.append({
                    "country": project["country"],
                    "province": district["province"],
                    "district": district["district"],
                    "latitude": district["latitude"],
                    "longitude": district["longitude"],
                    "target_local": location_spec["target"],
                    "actual_local": latest_actual,
                    "budget_local": location_spec["budget"],
                    "currency": "USD",
                })
                project_budget_total += float(location_spec["budget"])

                for period_index, period in enumerate(periods):
                    actual_value = float(location_spec["monthly_actuals"][period_index])
                    target_value = float(location_spec["target"])
                    if indicator["direction"] == "down":
                        baseline = float(indicator["baseline"])
                        denominator = baseline - target_value
                        progress_value = ((baseline - actual_value) / denominator) * 100 if denominator else 0.0
                    else:
                        baseline = float(indicator["baseline"])
                        denominator = target_value - baseline
                        progress_value = ((actual_value - baseline) / denominator) * 100 if denominator else 0.0
                    budget_value = float(location_spec["budget"]) * ((period_index + 1) / len(periods))
                    budget_variance_pct = ((period_index - 1) * 4.5) + (project_index * 1.8) - (district_index * 1.7)
                    row_status = status_labels[min(len(status_labels) - 1, max(0, int(progress_value < 80) + int(progress_value < 55)))]
                    risk_level = risk_labels[min(len(risk_labels) - 1, max(0, int(progress_value < 78) + int(progress_value < 52)))]

                    main_rows.append(_project_row(
                        project_id=project["id"],
                        project_name=project["name"],
                        donor=project["donor"],
                        manager=project["manager"],
                        implementing_partner=project["partner"],
                        sector=project["sector"],
                        country=project["country"],
                        province=district["province"],
                        district=district["district"],
                        latitude=district["latitude"],
                        longitude=district["longitude"],
                        indicator_id=indicator["id"],
                        indicator_name=indicator["name"],
                        indicator_level=indicator["level"],
                        reporting_period=period,
                        actual_value=actual_value,
                        target_value=target_value,
                        progress_value=progress_value,
                        budget_value=budget_value,
                        status=row_status,
                        owner=project["owner"],
                        risk_level=risk_level,
                        beneficiary_group=indicator["beneficiary_group"],
                        budget_variance_pct=budget_variance_pct,
                    ))

                    reporting_records.append({
                        "id": f"rep_{project['id']}_{indicator['id']}_{district_index + 1}_{period_index + 1}",
                        "reporting_period": period,
                        "project_id": project["id"],
                        "project_name": project["name"],
                        "indicator_id": indicator["id"],
                        "indicator_name": indicator["name"],
                        "country": project["country"],
                        "province": district["province"],
                        "district": district["district"],
                        "actual_value": round(actual_value, 3),
                        "target_value": round(target_value, 3),
                        "progress_value": round(progress_value, 3),
                        "budget_value": round(budget_value, 3),
                        "currency": "USD",
                        "status": row_status,
                        "owner": project["owner"],
                        "notes": "",
                        "source_dataset_id": "ds_demo_portfolio",
                        "created_at": created_at,
                        "updated_at": updated_at,
                    })

            indicator_entries.append({
                "id": indicator["id"],
                "name": indicator["name"],
                "unit": indicator["unit"],
                "frequency": indicator["frequency"],
                "direction": indicator["direction"],
                "level": indicator["level"],
                "target": indicator["target"],
                "baseline": indicator["baseline"],
                "locations": location_entries,
            })

        projects.append({
            "id": project["id"],
            "name": project["name"],
            "objective": project["objective"],
            "project_code": project["project_code"],
            "programme": project["programme"],
            "donor": project["donor"],
            "implementing_partner": project["partner"],
            "partner": project["partner"],
            "sector": project["sector"],
            "description": project["objective"],
            "country": project["country"],
            "province_coverage": list(dict.fromkeys([district["province"] for district in project["districts"]])),
            "district_coverage": [district["district"] for district in project["districts"]],
            "start_date": project["start_date"],
            "end_date": project["end_date"],
            "status": "active",
            "created_by_user_id": "user_demo_1",
            "created_by_name": "Amina Duarte",
            "created_at": created_at,
            "updated_at": updated_at,
            "published_at": created_at,
            "organization_id": organization_id,
            "team_assignments": [
                {
                    "id": f"projteam_{project['id']}_pm",
                    "project_id": project["id"],
                    "organization_id": organization_id,
                    "user_id": "user_demo_2",
                    "role": "programme_manager",
                    "team_id": "team_programme_ops",
                    "assigned_at": created_at,
                    "assigned_by_user_id": "user_demo_1",
                    "assigned_by_name": "Amina Duarte",
                    "status": "active",
                },
                {
                    "id": f"projteam_{project['id']}_meal",
                    "project_id": project["id"],
                    "organization_id": organization_id,
                    "user_id": "user_demo_3",
                    "role": "meal_officer",
                    "team_id": "team_meal",
                    "assigned_at": created_at,
                    "assigned_by_user_id": "user_demo_1",
                    "assigned_by_name": "Amina Duarte",
                    "status": "active",
                },
                {
                    "id": f"projteam_{project['id']}_field",
                    "project_id": project["id"],
                    "organization_id": organization_id,
                    "user_id": "user_demo_4",
                    "role": "field_coordinator",
                    "team_id": "team_field_ops",
                    "assigned_at": created_at,
                    "assigned_by_user_id": "user_demo_1",
                    "assigned_by_name": "Amina Duarte",
                    "status": "active",
                },
                {
                    "id": f"projteam_{project['id']}_exec",
                    "project_id": project["id"],
                    "organization_id": organization_id,
                    "user_id": "user_demo_5",
                    "role": "executive_viewer",
                    "team_id": "team_management",
                    "assigned_at": created_at,
                    "assigned_by_user_id": "user_demo_1",
                    "assigned_by_name": "Amina Duarte",
                    "status": "active",
                },
            ],
            "workspace_shell": {
                "project_id": project["id"],
                "organization_id": organization_id,
                "status": "published",
                "generated_at": created_at,
                "generated_by_user_id": "user_demo_1",
                "generated_by_name": "Amina Duarte",
                "containers": [
                    {"key": "indicators", "label": "Indicators", "status": "reserved", "ready": False, "created_at": created_at},
                    {"key": "logical_framework", "label": "Logical Framework", "status": "reserved", "ready": False, "created_at": created_at},
                    {"key": "workplan", "label": "Workplan", "status": "reserved", "ready": False, "created_at": created_at},
                    {"key": "reporting", "label": "Reporting", "status": "reserved", "ready": False, "created_at": created_at},
                    {"key": "budget", "label": "Budget", "status": "reserved", "ready": False, "created_at": created_at},
                    {"key": "documents", "label": "Documents", "status": "reserved", "ready": False, "created_at": created_at},
                ],
            },
            "indicators": indicator_entries,
        })

        activity_entries = []
        for activity in project["activities"]:
            tasks = []
            for task in activity["tasks"]:
                task_status = task_workflow_states[task["id"]]
                assignee = task_assignees[task_assignment_roles[task["id"]]]
                progress_pct = task_progress_by_status[task_status]
                priority = "critical" if task_status in {"overdue", "escalated"} else "high" if task_status == "pending_validation" else "medium"
                evidence_placeholders = task_evidence.get(task["id"], [])
                submitted_at = updated_at if task_status in {"pending_validation", "completed"} else ""
                validated_at = updated_at if task_status == "completed" else ""
                approved_at = updated_at if task_status == "completed" else ""
                tasks.append({
                    "id": task["id"],
                    "name": task["name"],
                    "owner": assignee.full_name,
                    "assignee_username": assignee.username,
                    "assignee_name": assignee.full_name,
                    "due_date": _iso(now + timedelta(days=task["due_offset_days"]))[:10],
                    "status": task_status,
                    "organization_id": organization_id,
                    "notes": "Fictional demo workflow item." if evidence_placeholders else "",
                    "priority": priority,
                    "progress_pct": progress_pct,
                    "category": "implementation",
                    "linked_indicator_id": activity["linked_indicator_ids"][0] if activity["linked_indicator_ids"] else "",
                    "evidence_placeholders": evidence_placeholders,
                    "activity_log": [
                        {
                            "id": f"log_{task['id']}_seed",
                            "occurred_at": updated_at,
                            "actor_username": "org.admin",
                            "actor_role": "organization_admin",
                            "event_type": "seeded",
                            "message": f"{task['name']} was seeded for {assignee.full_name} with {task_status.replace('_', ' ')} status.",
                            "details": {"source": "demo_seed"},
                        }
                    ],
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "submitted_at": submitted_at,
                    "validated_at": validated_at,
                    "approved_at": approved_at,
                })
            activity_entries.append({
                "id": activity["id"],
                "name": activity["name"],
                "owner": activity["owner"],
                "start_date": _iso(now + timedelta(days=activity["start_offset_days"]))[:10],
                "due_date": _iso(now + timedelta(days=activity["due_offset_days"]))[:10],
                "status": activity["status"],
                "organization_id": organization_id,
                "linked_indicator_ids": activity["linked_indicator_ids"],
                "tasks": tasks,
            })
        ops_by_project[project["id"]] = {"activities": activity_entries}

        for period_index, period in enumerate(periods):
            implementation_ratio = 0.52 + (period_index * 0.11) - (project_index * 0.03)
            budget_spent = project_budget_total * implementation_ratio
            budget_committed = project_budget_total * (0.63 + (period_index * 0.08))
            disbursement_pct = min(100, round(58 + period_index * 11 - project_index * 4, 2))
            burn_rate_pct = round((budget_spent / project_budget_total) * 100, 2) if project_budget_total else 0.0
            variance_to_plan_pct = round((budget_spent - budget_committed) / project_budget_total * 100, 2) if project_budget_total else 0.0
            finance_rows.append({
                "portfolio": "Mozambique Country Portfolio",
                "donor": project["donor"],
                "project_id": project["id"],
                "project_name": project["name"],
                "project_manager": project["manager"],
                "grant_window": f"{project['donor']} FY26 Window",
                "reporting_month": period,
                "country": project["country"],
                "budget_total": round(project_budget_total, 3),
                "budget_committed": round(budget_committed, 3),
                "budget_spent": round(budget_spent, 3),
                "burn_rate_pct": burn_rate_pct,
                "disbursement_pct": disbursement_pct,
                "variance_to_plan_pct": variance_to_plan_pct,
                "deliverable_due_count": 2 + project_index + period_index,
                "risk_level": risk_labels[min(2, max(0, int(disbursement_pct < 70) + int(abs(variance_to_plan_pct) > 8)))],
                "status": "verde" if variance_to_plan_pct >= -4 else "amarelo" if variance_to_plan_pct >= -9 else "vermelho",
            })

    semantic_mappings = [
        {
            "id": "map_demo_portfolio",
            "dataset_id": "ds_demo_portfolio",
            "name": "Demo portfolio mapping",
            "fields": {
                "project_id": "project_id",
                "project_name": "project_name",
                "indicator_id": "indicator_id",
                "indicator_name": "indicator_name",
                "reporting_period": "reporting_month",
                "actual_value": "actual_value",
                "target_value": "target_value",
                "progress_value": "progress_value",
                "budget_value": "budget_value",
                "country": "country",
                "province": "province",
                "district": "district",
                "status": "status",
                "owner": "project_manager",
                "latitude": "latitude",
                "longitude": "longitude",
            },
            "status": "confirmed",
            "confidence": 0.98,
            "notes": "Seeded semantic mapping for the portfolio KPI dataset.",
            "created_at": created_at,
            "updated_at": updated_at,
        },
        {
            "id": "map_demo_grants",
            "dataset_id": "ds_demo_grants",
            "name": "Demo grants mapping",
            "fields": {
                "project_id": "project_id",
                "project_name": "project_name",
                "reporting_period": "reporting_month",
                "actual_value": "budget_spent",
                "target_value": "budget_committed",
                "budget_value": "budget_total",
                "status": "status",
                "owner": "project_manager",
            },
            "status": "confirmed",
            "confidence": 0.93,
            "notes": "Seeded semantic mapping for donor financial monitoring.",
            "created_at": created_at,
            "updated_at": updated_at,
        },
    ]

    dashboard_templates = [
        {
            "id": "demo_tpl_portfolio_board",
            "name": "Portfolio Executive Board",
            "description": "Portfolio-wide executive review with delivery, risks, budget, and notifications.",
            "dashboard_type": "portfolio_executive",
            "scope": "custom",
            "filters": ["project_name", "donor", "province", "reporting_month"],
            "visuals": [
                {"id": "demo_exec_kpis", "chart_type": "kpi_cards", "title": "Portfolio KPIs", "reason": "Board-level headline measures."},
                {"id": "demo_exec_trend", "chart_type": "line_trend", "title": "Weighted Progress Trend", "reason": "Shows whether the portfolio is improving across reporting periods."},
                {"id": "demo_exec_status", "chart_type": "status_donut", "title": "Status Mix", "reason": "Summarizes delivery health by status."},
                {"id": "demo_exec_budget", "chart_type": "budget_vs_actual", "title": "Budget vs Delivery", "reason": "Compares portfolio burn against results."},
                {"id": "demo_exec_alerts", "chart_type": "notification_summary", "title": "Management Alerts", "reason": "Pulls current priority issues for action."},
                {"id": "demo_exec_map", "chart_type": "map_placeholder", "title": "Coverage Footprint", "reason": "Highlights the current district coverage footprint."},
                {"id": "demo_exec_narrative", "chart_type": "narrative_panel", "title": "Executive Narrative", "reason": "Provides a management-ready written interpretation."},
            ],
            "layout": [
                {"widget_id": "demo_exec_kpis", "visual_index": 0, "chart_type": "kpi_cards", "title": "Portfolio KPIs", "column_span": 3, "row_span": 1, "section": "summary"},
                {"widget_id": "demo_exec_trend", "visual_index": 1, "chart_type": "line_trend", "title": "Weighted Progress Trend", "column_span": 2, "row_span": 2, "section": "main"},
                {"widget_id": "demo_exec_status", "visual_index": 2, "chart_type": "status_donut", "title": "Status Mix", "column_span": 1, "row_span": 1, "section": "summary"},
                {"widget_id": "demo_exec_budget", "visual_index": 3, "chart_type": "budget_vs_actual", "title": "Budget vs Delivery", "column_span": 1, "row_span": 2, "section": "main"},
                {"widget_id": "demo_exec_alerts", "visual_index": 4, "chart_type": "notification_summary", "title": "Management Alerts", "column_span": 2, "row_span": 2, "section": "main"},
                {"widget_id": "demo_exec_map", "visual_index": 5, "chart_type": "map_placeholder", "title": "Coverage Footprint", "column_span": 1, "row_span": 2, "section": "main"},
                {"widget_id": "demo_exec_narrative", "visual_index": 6, "chart_type": "narrative_panel", "title": "Executive Narrative", "column_span": 3, "row_span": 1, "section": "main"},
            ],
            "narrative_sections": ["summary", "risks", "actions", "donor_talking_points"],
            "theme": "executive",
            "created_at": created_at,
            "updated_at": updated_at,
        },
        {
            "id": "demo_tpl_project_snapshot",
            "name": "Project Executive Snapshot",
            "description": "Project-level view for delivery, workplan execution, and donor readiness.",
            "dashboard_type": "project_snapshot",
            "scope": "custom",
            "filters": ["project_name", "district", "indicator_name", "reporting_month"],
            "visuals": [
                {"id": "demo_proj_status", "chart_type": "project_status_summary", "title": "Delivery Posture", "reason": "Summarizes project health and implementation context."},
                {"id": "demo_proj_gauge", "chart_type": "bullet_or_gauge", "title": "Progress vs Target", "reason": "Highlights delivery confidence against target."},
                {"id": "demo_proj_districts", "chart_type": "bar_comparison", "title": "District Performance", "reason": "Compares district-level progress."},
                {"id": "demo_proj_budget", "chart_type": "variance_bar", "title": "Budget Variance", "reason": "Shows financial deviation from plan."},
                {"id": "demo_proj_workplan", "chart_type": "activity_progress", "title": "Workplan Delivery", "reason": "Tracks activity and task completion."},
                {"id": "demo_proj_alerts", "chart_type": "notification_summary", "title": "Project Alerts", "reason": "Keeps the project manager focused on current risks."},
                {"id": "demo_proj_map", "chart_type": "map_placeholder", "title": "District Coverage", "reason": "Displays delivery footprint by district."},
                {"id": "demo_proj_narrative", "chart_type": "narrative_panel", "title": "Narrative Summary", "reason": "Summarizes the story behind the numbers."},
            ],
            "layout": [
                {"widget_id": "demo_proj_status", "visual_index": 0, "chart_type": "project_status_summary", "title": "Delivery Posture", "column_span": 2, "row_span": 1, "section": "summary"},
                {"widget_id": "demo_proj_gauge", "visual_index": 1, "chart_type": "bullet_or_gauge", "title": "Progress vs Target", "column_span": 1, "row_span": 1, "section": "summary"},
                {"widget_id": "demo_proj_districts", "visual_index": 2, "chart_type": "bar_comparison", "title": "District Performance", "column_span": 2, "row_span": 2, "section": "main"},
                {"widget_id": "demo_proj_budget", "visual_index": 3, "chart_type": "variance_bar", "title": "Budget Variance", "column_span": 1, "row_span": 2, "section": "main"},
                {"widget_id": "demo_proj_workplan", "visual_index": 4, "chart_type": "activity_progress", "title": "Workplan Delivery", "column_span": 2, "row_span": 2, "section": "main"},
                {"widget_id": "demo_proj_alerts", "visual_index": 5, "chart_type": "notification_summary", "title": "Project Alerts", "column_span": 1, "row_span": 2, "section": "main"},
                {"widget_id": "demo_proj_map", "visual_index": 6, "chart_type": "map_placeholder", "title": "District Coverage", "column_span": 1, "row_span": 2, "section": "main"},
                {"widget_id": "demo_proj_narrative", "visual_index": 7, "chart_type": "narrative_panel", "title": "Narrative Summary", "column_span": 2, "row_span": 1, "section": "main"},
            ],
            "narrative_sections": ["summary", "exceptions", "actions"],
            "theme": "operations",
            "created_at": created_at,
            "updated_at": updated_at,
        },
        {
            "id": "demo_tpl_donor_pack",
            "name": "Donor Reporting Snapshot",
            "description": "Funding, delivery, and accountability lens for donor conversations.",
            "dashboard_type": "donor_reporting",
            "scope": "custom",
            "filters": ["donor", "project_name", "reporting_month"],
            "visuals": [
                {"id": "demo_donor_kpis", "chart_type": "kpi_cards", "title": "Donor Review KPIs", "reason": "Focuses on burn rate, progress, and compliance."},
                {"id": "demo_donor_trend", "chart_type": "area_trend", "title": "Budget Burn Trend", "reason": "Shows expenditure and delivery trajectory."},
                {"id": "demo_donor_variance", "chart_type": "budget_vs_actual", "title": "Budget Commitments vs Spend", "reason": "Provides budget governance perspective."},
                {"id": "demo_donor_risks", "chart_type": "notification_summary", "title": "Reporting Risks", "reason": "Highlights issues that may affect donor confidence."},
                {"id": "demo_donor_narrative", "chart_type": "narrative_panel", "title": "Donor Narrative", "reason": "Packages delivery into donor-ready language."},
            ],
            "layout": [
                {"widget_id": "demo_donor_kpis", "visual_index": 0, "chart_type": "kpi_cards", "title": "Donor Review KPIs", "column_span": 3, "row_span": 1, "section": "summary"},
                {"widget_id": "demo_donor_trend", "visual_index": 1, "chart_type": "area_trend", "title": "Budget Burn Trend", "column_span": 2, "row_span": 2, "section": "main"},
                {"widget_id": "demo_donor_variance", "visual_index": 2, "chart_type": "budget_vs_actual", "title": "Budget Commitments vs Spend", "column_span": 1, "row_span": 2, "section": "main"},
                {"widget_id": "demo_donor_risks", "visual_index": 3, "chart_type": "notification_summary", "title": "Reporting Risks", "column_span": 1, "row_span": 2, "section": "main"},
                {"widget_id": "demo_donor_narrative", "visual_index": 4, "chart_type": "narrative_panel", "title": "Donor Narrative", "column_span": 2, "row_span": 1, "section": "main"},
            ],
            "narrative_sections": ["executive_summary", "budget", "risk_and_mitigation", "next_commitments"],
            "theme": "geo_focus",
            "created_at": created_at,
            "updated_at": updated_at,
        },
    ]

    notification_rules = [
        {
            "id": "rule_demo_portfolio_delivery",
            "name": "Weekly portfolio delivery dip",
            "is_active": True,
            "schedule": "weekly",
            "channel": "email",
            "provider": "smtp",
            "min_severity": "high",
            "condition_type": "progress_below",
            "threshold": 75,
            "project_id": "proj_health",
            "indicator_id": "",
            "dataset_id": "",
            "recipients": ["executive.director@bluedelta.org", "raimundo.cumba@bluedelta.org"],
            "webhook_url": "",
            "notes": "Escalate if project performance remains below threshold for two consecutive cycles.",
            "last_run_at": "",
            "created_at": created_at,
            "updated_at": updated_at,
        },
        {
            "id": "rule_demo_trend_drop",
            "name": "Donor watchlist trend drop",
            "is_active": True,
            "schedule": "daily",
            "channel": "whatsapp",
            "provider": "webhook",
            "min_severity": "medium",
            "condition_type": "trend_drop",
            "threshold": 5,
            "project_id": "proj_education",
            "indicator_id": "",
            "dataset_id": "",
            "recipients": ["+258840001111", "+258840002222"],
            "webhook_url": "",
            "notes": "Used during internal stand-up for rapid follow-up.",
            "last_run_at": "",
            "created_at": created_at,
            "updated_at": updated_at,
        },
        {
            "id": "rule_demo_stale_reporting",
            "name": "Stale reporting escalation",
            "is_active": True,
            "schedule": "weekly",
            "channel": "webhook",
            "provider": "generic_webhook",
            "min_severity": "medium",
            "condition_type": "stale_reporting",
            "threshold": 40,
            "project_id": "proj_resilience",
            "indicator_id": "",
            "dataset_id": "",
            "recipients": [],
            "webhook_url": "https://example.org/demo-webhook",
            "notes": "Flags late reporting submissions ahead of portfolio review.",
            "last_run_at": "",
            "created_at": created_at,
            "updated_at": updated_at,
        },
    ]

    audit_events = [
        {
            "id": "audit_demo_1",
            "occurred_at": periods[-2],
            "actor_id": "user_demo_2",
            "actor_username": "teresa.mbanze",
            "actor_role": "programme_manager",
            "action": "reporting_records.imported",
            "target_type": "reporting_records",
            "target_id": "ds_demo_portfolio",
            "endpoint": "/v1/reporting_records/import",
            "outcome": "success",
            "details": {"count": len(reporting_records), "source": "demo_seed"},
        },
        {
            "id": "audit_demo_2",
            "occurred_at": periods[-1],
            "actor_id": "user_demo_3",
            "actor_username": "raimundo.cumba",
            "actor_role": "meal_officer",
            "action": "dashboard_template.created",
            "target_type": "dashboard_template",
            "target_id": "demo_tpl_project_snapshot",
            "endpoint": "/v1/dashboard_templates",
            "outcome": "success",
            "details": {"theme": "operations"},
        },
        {
            "id": "audit_demo_3",
            "occurred_at": updated_at,
            "actor_id": "user_demo_1",
            "actor_username": "org.admin",
            "actor_role": "organization_admin",
            "action": "notification_rule.run_due",
            "target_type": "notification_rule",
            "target_id": "batch",
            "endpoint": "/scheduler/notification_rules/run_due",
            "outcome": "success",
            "details": {"checked_rules": 3, "ran_rules": 2},
        },
    ]

    tidy_datasets = [
        {
            "id": "ds_demo_portfolio",
            "name": "Portfolio KPI Reporting Feed",
            "description": "One row per project, indicator, district, and reporting month for the NGO portfolio demo.",
            "source_type": "demo_seed",
            "created_at": created_at,
            "updated_at": updated_at,
            "rows": main_rows,
        },
        {
            "id": "ds_demo_grants",
            "name": "Donor Grant Performance Feed",
            "description": "Monthly budget, disbursement, and grant delivery tracking for donor-facing reviews.",
            "source_type": "demo_seed",
            "created_at": created_at,
            "updated_at": updated_at,
            "rows": finance_rows,
        },
    ]

    organizations = [
        {
            "id": organization_id,
            "organization_name": organization_name,
            "status": "active",
            "subscription_plan": "foundation",
            "country": organization_country,
            "timezone": organization_timezone,
            "default_language": organization_language,
            "contact_email": organization_contact_email,
            "contact_person": organization_contact_person,
            "logo_placeholder": organization_logo_placeholder,
            "created_at": created_at,
            "updated_at": updated_at,
        }
    ]

    for project in projects:
        project["organization_id"] = organization_id
    for record in reporting_records:
        record["organization_id"] = organization_id
    for dataset in tidy_datasets:
        dataset["organization_id"] = organization_id
        dataset["rows"] = [
            {
                **row,
                "organization_id": organization_id,
            }
            for row in dataset.get("rows", [])
        ]
    for mapping in semantic_mappings:
        mapping["organization_id"] = organization_id
    for template in dashboard_templates:
        template["organization_id"] = organization_id
    for rule in notification_rules:
        rule["organization_id"] = organization_id
    for event in audit_events:
        event["organization_id"] = organization_id
    for ops in ops_by_project.values():
        for activity in ops.get("activities", []):
            activity["organization_id"] = organization_id
            for task in activity.get("tasks", []):
                task["organization_id"] = organization_id

    payload = {
        "organizations": organizations,
        "teams": default_teams,
        "projects": projects,
        "ops_by_project": ops_by_project,
        "tidy_datasets": tidy_datasets,
        "reporting_records": reporting_records,
        "semantic_mappings": semantic_mappings,
        "dashboard_templates": dashboard_templates,
        "notification_rules": notification_rules,
        "users": users,
        "audit_events": audit_events,
    }

    return DemoSeedBundle(
        payload=payload,
        credentials=credentials,
        default_project_id="proj_resilience",
        default_dataset_id="ds_demo_portfolio",
        finance_dataset_id="ds_demo_grants",
        default_username="org.admin",
        default_email="amina.duarte@bluedelta.org",
    )
