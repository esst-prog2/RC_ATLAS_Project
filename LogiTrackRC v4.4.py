# ============================================================
# LOGITRACK_RC v4.4 — Reporting + Ops Lite + BI Ready + API v1 (Render-ready)
# BASE: v4.3 (NO FEATURES REMOVED)
# Added:
#   - Official BI bridge: activity_indicator_links (CSV + API)
#   - KPI datasets: project/indicator/district/workplan (CSV + API)
#   - API v1 + /health + CORS
#   - Render-ready: global `app` for uvicorn import
# Persistence: JSON (lightweight)
# ============================================================

from dataclasses import dataclass, field, asdict
from typing import Any, List, Optional, Dict, Tuple
from statistics import mean
from datetime import datetime, date, timedelta, timezone
import json
import os
import csv
import base64
import hashlib
import logging
import secrets
import sqlite3
import smtplib
import tempfile
import threading
import time
from io import StringIO
from pathlib import Path
from email.message import EmailMessage
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest
from api import (
    LogicalFrameworkRouteDependencies,
    register_dashboard_template_routes,
    register_demo_routes,
    register_logical_framework_routes,
    register_notification_routes,
    register_reporting_routes,
)
from logitrack_platform import (
    RepeatingRuntimeWorker,
    get_relational_store_path,
    get_relational_store_status,
    sync_snapshot_to_relational_store,
)
from migration.sync_helpers import (
    hydrate_snapshot_with_repository_domains,
    repository_domains_enabled,
    safe_get_repository_sync_status,
    sync_repository_backed_domains_from_snapshot,
)
from repositories.logical_framework_repository import LogicalFrameworkScope
from repositories.logical_framework_snapshot import (
    SnapshotLogicalFrameworkRepository,
    SnapshotLogicalFrameworkUnitOfWork,
    validate_snapshot_logical_framework,
)
from services import (
    DashboardTemplateService,
    DashboardTemplateServiceDependencies,
    DemoWorkspaceService,
    DemoWorkspaceServiceDependencies,
    NotificationService,
    NotificationServiceDependencies,
    LogicalFrameworkActorContext,
    LogicalFrameworkApplication,
    LogicalFrameworkAuditRequest,
    LogicalFrameworkService,
    LogicalFrameworkValidationError,
    ReportingService,
    ReportingServiceDependencies,
)
try:
    from shared import (
        AuditEvent,
        DashboardTemplate,
        IndicatorResultLink,
        NotificationRule,
        OrganizationAccount,
        ReportingPeriodRecord,
        ResultNode,
        SemanticMapping,
        TeamAccount,
        TidyDataset,
        UserAccount,
    )
except ImportError:
    from shared import (
        AuditEvent,
        DashboardTemplate,
        IndicatorResultLink,
        NotificationRule,
        OrganizationAccount,
        ReportingPeriodRecord,
        ResultNode,
        SemanticMapping,
        TidyDataset,
        UserAccount,
    )
    try:
        from shared.domain_models import TeamAccount
    except ImportError:
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

# ----------------------------
# OPTIONAL API IMPORTS
# ----------------------------
try:
    from fastapi import FastAPI, Header, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, Response
except Exception:
    FastAPI = None
    Header = None
    HTTPException = None
    CORSMiddleware = None
    HTMLResponse = None
    Response = None

# ----------------------------
# CONFIG / BRAND
# ----------------------------
CONFIG = {
    "system_name": "LogiTrack_RC",
    "version": "v4.4",
    "status_thresholds": {"superou": 100, "verde": 80, "amarelo": 50},
}

# Default JSON path (local + Render)
DEFAULT_DATA_PATH = os.getenv("LOGITRACK_DATA_PATH", os.path.join(os.getcwd(), "logitrack_data.json"))
DATA_STORE_LOCK = threading.RLock()
RELATIONAL_SYNC_STATE = {
    "enabled": False,
    "last_synced_at": "",
    "last_error": "",
    "last_result": {},
}
REPOSITORY_SYNC_STATE = {
    "enabled": False,
    "last_synced_at": "",
    "last_error": "",
    "last_result": {},
}
LOGGER = logging.getLogger("logitrack")

# ----------------------------
# I18N (PT/EN/FR)
# Canonical status stays PT internally; only translate at presentation layer.
# ----------------------------
LANG_PACK = {
    "PT": {
        "select_lang_title": "Selecione o idioma do relatório/sistema:",
        "opt_pt": "1) Português",
        "opt_en": "2) English",
        "choice": "Escolha",
        "invalid_option": "Opção inválida.",
        "no_projects": "Ainda não há projetos. Cria um primeiro.",
        "projects": "Projetos",
        "pick_project": "Escolha o número do projeto",
        "project_created": "✅ Projeto criado.",
        "saved_to": "✅ Guardado em",
        "loaded_from": "✅ Carregado de",
        "menu_title": "{name} {version}",
        "menu_1": "1) Criar projeto (Reporting)",
        "menu_2": "2) Ops Lite (Workplan + Tasks)",
        "menu_3": "3) Relatório (inclui Workplan snapshot)",
        "menu_4": "4) Guardar (JSON)",
        "menu_5": "5) Carregar (JSON)",
        "menu_6": "6) Exportar (BI: CSV)",
        "menu_7": "7) Servir API (BI Online)",
        "menu_0": "0) Sair",
        "path_save": "Path para guardar (Enter = {path})",
        "path_load": "Path para carregar (Enter = {path})",
        "export_dir": "Pasta de export (Enter = {path})",
        "export_done": "✅ Export BI concluído em",
        "api_missing": "⚠️ FastAPI/uvicorn não instalado. Instale: pip install fastapi uvicorn",
        "api_start": "✅ API a correr em http://127.0.0.1:8000 (CTRL+C para parar)",
        "ops_title": "Ops Lite — {project}",
        "ops_1": "1) Listar atividades operacionais",
        "ops_2": "2) Criar atividade operacional (Workplan)",
        "ops_3": "3) Adicionar task a uma atividade",
        "ops_4": "4) Atualizar status de task",
        "ops_0": "0) Voltar",
        "new_op_act": "--- Nova Atividade Operacional (Workplan) ---",
        "op_act_name": "Nome da atividade operacional",
        "owner": "Responsável",
        "start_date": "Data início (YYYY-MM-DD) (opcional)",
        "due_date": "Data fim/prazo (YYYY-MM-DD) (opcional)",
        "status_op": "Status (planned/ongoing/done)",
        "indicators_for_link": "Indicadores (para linkar no Workplan)",
        "linked_ids": "IDs dos indicadores ligados (separar por vírgula)",
        "logframe_required": "⚠️ Para respeitar o quadro lógico, a atividade operacional deve estar ligada a pelo menos 1 indicador.",
        "op_cancelled": "Operação cancelada (crie novamente e faça o link).",
        "op_created": "✅ Atividade operacional criada e ligada ao(s) indicador(es).",
        "no_ops_acts": "Sem atividades operacionais.",
        "ops_list": "Atividades operacionais",
        "links": "links",
        "task_tag": "[Task]",
        "pick_activity": "Escolha o número da atividade",
        "new_task": "--- Nova Task ---",
        "task_name": "Nome da task",
        "task_owner": "Responsável da task",
        "task_status": "Status (todo/doing/done)",
        "notes": "Notas (opcional)",
        "task_added": "✅ Task adicionada.",
        "no_tasks": "Sem tasks nesta atividade.",
        "tasks": "Tasks",
        "pick_task": "Escolha o número da task",
        "new_status": "Novo status (todo/doing/done)",
        "status_updated": "✅ Status atualizado.",
        "report_title": "{name} {version} — RELATÓRIO EXECUTIVO (com Ops Lite)",
        "project": "Projeto",
        "objective": "Objetivo",
        "indicator": "Indicador",
        "level": "level",
        "direction": "dir",
        "progress_avg_district": "Progresso (média distritos)",
        "progress_na": "Progresso",
        "state": "Estado",
        "workplan_none": "Workplan ligado: 0 (⚠️ considerar ligar atividades operacionais)",
        "workplan_some": "Workplan ligado: {n} atividade(s)",
        "exec_summary_avg": "Resumo Executivo (média)",
        "workplan_snapshot": "--- WORKPLAN SNAPSHOT (Ops Lite) ---",
        "no_ops_registered": "Sem atividades operacionais registradas.",
        "overdue_tasks": "Tarefas atrasadas",
        "upcoming_tasks": "Tarefas próximos 7 dias",
        "ind_no_ops_warning": "⚠️ Indicadores sem atividades operacionais ligadas (pode afetar explicabilidade):",
        "selection_invalid": "Seleção inválida.",
        "create_project_inputs_name": "Nome do projeto",
        "create_project_inputs_objective": "Objetivo",
        "add_indicator": "Adicionar indicador? (s/n)",
        "add_location": "Adicionar distrito/localização para este indicador? (s/n)",
        "indicator_name": "Nome do indicador",
        "unit": "Unidade (%/#/USD/EUR/ha/outro)",
        "unit_spec": "Especifique a unidade",
        "frequency": "Periodicidade",
        "direction_updown": "Direção (up/down)",
        "level_oi": "Nível (output/outcome/impact)",
        "target_general": "Meta geral (opcional)",
        "baseline_optional": "Baseline (opcional)",
        "country": "País",
        "province": "Província",
        "district": "Distrito",
        "lat": "Latitude",
        "lon": "Longitude",
        "target_district": "Meta do distrito",
        "actual_district": "Real do distrito",
        "budget_district": "Budget do distrito",
        "currency": "Moeda (MZN/USD/EUR/GBP/ZAR/outro)",
        "currency_spec": "Especifique a moeda",
        "latlon_invalid": "Latitude/Longitude inválidas.",
        "data_file_missing": "⚠️ Ficheiro de dados não encontrado: {path}",
    },
    "EN": {
        "select_lang_title": "Select report/system language:",
        "opt_pt": "1) Português",
        "opt_en": "2) English",
        "choice": "Choice",
        "invalid_option": "Invalid option.",
        "no_projects": "No projects yet. Create one first.",
        "projects": "Projects",
        "pick_project": "Choose the project number",
        "project_created": "✅ Project created.",
        "saved_to": "✅ Saved to",
        "loaded_from": "✅ Loaded from",
        "menu_title": "{name} {version}",
        "menu_1": "1) Create project (Reporting)",
        "menu_2": "2) Ops Lite (Workplan + Tasks)",
        "menu_3": "3) Report (includes Workplan snapshot)",
        "menu_4": "4) Save (JSON)",
        "menu_5": "5) Load (JSON)",
        "menu_6": "6) Export (BI: CSV)",
        "menu_7": "7) Serve API (BI Online)",
        "menu_0": "0) Exit",
        "path_save": "Save path (Enter = {path})",
        "path_load": "Load path (Enter = {path})",
        "export_dir": "Export folder (Enter = {path})",
        "export_done": "✅ BI export completed in",
        "api_missing": "⚠️ FastAPI/uvicorn not installed. Install: pip install fastapi uvicorn",
        "api_start": "✅ API running at http://127.0.0.1:8000 (CTRL+C to stop)",
        "ops_title": "Ops Lite — {project}",
        "ops_1": "1) List operational activities",
        "ops_2": "2) Create operational activity (Workplan)",
        "ops_3": "3) Add task to an activity",
        "ops_4": "4) Update task status",
        "ops_0": "0) Back",
        "new_op_act": "--- New Operational Activity (Workplan) ---",
        "op_act_name": "Operational activity name",
        "owner": "Owner",
        "start_date": "Start date (YYYY-MM-DD) (optional)",
        "due_date": "Due date (YYYY-MM-DD) (optional)",
        "status_op": "Status (planned/ongoing/done)",
        "indicators_for_link": "Indicators (to link in Workplan)",
        "linked_ids": "Linked indicator IDs (comma-separated)",
        "logframe_required": "⚠️ To respect the logframe, an operational activity must be linked to at least 1 indicator.",
        "op_cancelled": "Operation cancelled (create again and link it).",
        "op_created": "✅ Operational activity created and linked to indicator(s).",
        "no_ops_acts": "No operational activities.",
        "ops_list": "Operational activities",
        "links": "links",
        "task_tag": "[Task]",
        "pick_activity": "Choose the activity number",
        "new_task": "--- New Task ---",
        "task_name": "Task name",
        "task_owner": "Task owner",
        "task_status": "Status (todo/doing/done)",
        "notes": "Notes (optional)",
        "task_added": "✅ Task added.",
        "no_tasks": "No tasks in this activity.",
        "tasks": "Tasks",
        "pick_task": "Choose the task number",
        "new_status": "New status (todo/doing/done)",
        "status_updated": "✅ Status updated.",
        "report_title": "{name} {version} — EXECUTIVE REPORT (with Ops Lite)",
        "project": "Project",
        "objective": "Objective",
        "indicator": "Indicator",
        "level": "level",
        "direction": "dir",
        "progress_avg_district": "Progress (district average)",
        "progress_na": "Progress",
        "state": "Status",
        "workplan_none": "Linked workplan: 0 (⚠️ consider linking operational activities)",
        "workplan_some": "Linked workplan: {n} activity(ies)",
        "exec_summary_avg": "Executive summary (average)",
        "workplan_snapshot": "--- WORKPLAN SNAPSHOT (Ops Lite) ---",
        "no_ops_registered": "No operational activities registered.",
        "overdue_tasks": "Overdue tasks",
        "upcoming_tasks": "Tasks due in next 7 days",
        "ind_no_ops_warning": "⚠️ Indicators with no linked operational activities (may reduce explainability):",
        "selection_invalid": "Invalid selection.",
        "create_project_inputs_name": "Project name",
        "create_project_inputs_objective": "Objective",
        "add_indicator": "Add indicator? (y/n)",
        "add_location": "Add district/location for this indicator? (y/n)",
        "indicator_name": "Indicator name",
        "unit": "Unit (%/#/USD/EUR/ha/other)",
        "unit_spec": "Specify the unit",
        "frequency": "Frequency",
        "direction_updown": "Direction (up/down)",
        "level_oi": "Level (output/outcome/impact)",
        "target_general": "Overall target (optional)",
        "baseline_optional": "Baseline (optional)",
        "country": "Country",
        "province": "Province",
        "district": "District",
        "lat": "Latitude",
        "lon": "Longitude",
        "target_district": "District target",
        "actual_district": "District actual",
        "budget_district": "District budget",
        "currency": "Currency (MZN/USD/EUR/GBP/ZAR/other)",
        "currency_spec": "Specify the currency",
        "latlon_invalid": "Invalid latitude/longitude.",
        "data_file_missing": "⚠️ Data file not found: {path}",
    }
}

LANG_PACK["PT"]["opt_fr"] = "3) Français"
LANG_PACK["EN"]["opt_fr"] = "3) Français"

LANG_PACK["FR"] = {
    **LANG_PACK["EN"],
    "select_lang_title": "Choisissez la langue du système et du rapport :",
    "opt_pt": "1) Português",
    "opt_en": "2) English",
    "opt_fr": "3) Français",
    "choice": "Choix",
    "invalid_option": "Option invalide.",
    "no_projects": "Aucun projet pour le moment. Créez-en un d'abord.",
    "projects": "Projets",
    "pick_project": "Choisissez le numéro du projet",
    "project_created": "Projet créé.",
    "saved_to": "Enregistré dans",
    "loaded_from": "Chargé depuis",
    "menu_1": "1) Créer un projet (Reporting)",
    "menu_2": "2) Ops Lite (Plan de travail + tâches)",
    "menu_3": "3) Rapport (inclut le snapshot du plan de travail)",
    "menu_4": "4) Enregistrer (JSON)",
    "menu_5": "5) Charger (JSON)",
    "menu_6": "6) Exporter (BI : CSV)",
    "menu_7": "7) Exposer l'API (BI en ligne)",
    "menu_0": "0) Quitter",
    "path_save": "Chemin d'enregistrement (Entrée = {path})",
    "path_load": "Chemin de chargement (Entrée = {path})",
    "export_dir": "Dossier d'export (Entrée = {path})",
    "export_done": "Export BI terminé dans",
    "api_missing": "FastAPI/uvicorn non installé. Installez : pip install fastapi uvicorn",
    "api_start": "API active sur http://127.0.0.1:8000 (CTRL+C pour arrêter)",
    "ops_title": "Ops Lite — {project}",
    "ops_1": "1) Lister les activités opérationnelles",
    "ops_2": "2) Créer une activité opérationnelle (plan de travail)",
    "ops_3": "3) Ajouter une tâche à une activité",
    "ops_4": "4) Mettre à jour le statut d'une tâche",
    "ops_0": "0) Retour",
    "new_op_act": "--- Nouvelle activité opérationnelle (plan de travail) ---",
    "op_act_name": "Nom de l'activité opérationnelle",
    "owner": "Responsable",
    "start_date": "Date de début (YYYY-MM-DD) (optionnel)",
    "due_date": "Date limite (YYYY-MM-DD) (optionnel)",
    "status_op": "Statut (planned/ongoing/done)",
    "indicators_for_link": "Indicateurs (à lier au plan de travail)",
    "linked_ids": "IDs des indicateurs liés (séparés par des virgules)",
    "logframe_required": "Pour respecter le cadre logique, une activité opérationnelle doit être liée à au moins 1 indicateur.",
    "op_cancelled": "Opération annulée (recréez-la et ajoutez le lien).",
    "op_created": "Activité opérationnelle créée et liée aux indicateurs.",
    "no_ops_acts": "Aucune activité opérationnelle.",
    "ops_list": "Activités opérationnelles",
    "pick_activity": "Choisissez le numéro de l'activité",
    "new_task": "--- Nouvelle tâche ---",
    "task_name": "Nom de la tâche",
    "task_owner": "Responsable de la tâche",
    "task_added": "Tâche ajoutée.",
    "no_tasks": "Aucune tâche dans cette activité.",
    "pick_task": "Choisissez le numéro de la tâche",
    "new_status": "Nouveau statut (todo/doing/done)",
    "status_updated": "Statut mis à jour.",
    "report_title": "{name} {version} — RAPPORT EXÉCUTIF (avec Ops Lite)",
    "project": "Projet",
    "objective": "Objectif",
    "indicator": "Indicateur",
    "progress_avg_district": "Progrès (moyenne des districts)",
    "progress_na": "Progrès",
    "state": "Statut",
    "workplan_none": "Plan de travail lié : 0 (envisager de lier des activités opérationnelles)",
    "workplan_some": "Plan de travail lié : {n} activité(s)",
    "exec_summary_avg": "Résumé exécutif (moyenne)",
    "workplan_snapshot": "--- SNAPSHOT DU PLAN DE TRAVAIL (Ops Lite) ---",
    "no_ops_registered": "Aucune activité opérationnelle enregistrée.",
    "overdue_tasks": "Tâches en retard",
    "upcoming_tasks": "Tâches dues dans les 7 prochains jours",
    "ind_no_ops_warning": "Indicateurs sans activités opérationnelles liées (peut réduire l'explicabilité) :",
    "selection_invalid": "Sélection invalide.",
    "create_project_inputs_name": "Nom du projet",
    "create_project_inputs_objective": "Objectif",
    "add_indicator": "Ajouter un indicateur ? (o/n)",
    "add_location": "Ajouter un district/lieu pour cet indicateur ? (o/n)",
    "indicator_name": "Nom de l'indicateur",
    "unit": "Unité (%/#/USD/EUR/ha/autre)",
    "unit_spec": "Précisez l'unité",
    "frequency": "Fréquence",
    "direction_updown": "Direction (up/down)",
    "level_oi": "Niveau (output/outcome/impact)",
    "target_general": "Cible globale (optionnel)",
    "baseline_optional": "Baseline (optionnel)",
    "country": "Pays",
    "province": "Province",
    "district": "District",
    "lat": "Latitude",
    "lon": "Longitude",
    "target_district": "Cible du district",
    "actual_district": "Réel du district",
    "budget_district": "Budget du district",
    "currency": "Devise (MZN/USD/EUR/GBP/ZAR/autre)",
    "currency_spec": "Précisez la devise",
    "latlon_invalid": "Latitude/longitude invalides.",
    "data_file_missing": "Fichier de données introuvable : {path}",
}

REPORT_LANG = "PT"

def tr(key: str, **kwargs) -> str:
    pack = LANG_PACK.get(REPORT_LANG, LANG_PACK["PT"])
    text = pack.get(key, LANG_PACK["PT"].get(key, key))
    try:
        return text.format(**kwargs)
    except Exception:
        return text

def select_language() -> str:
    print("\n" + tr("select_lang_title"))
    print(tr("opt_pt"))
    print(tr("opt_en"))
    print(tr("opt_fr"))
    c = input(f"{tr('choice')}: ").strip()
    if c == "3" or c.upper() == "FR":
        return "FR"
    if c == "2" or c.upper() == "EN":
        return "EN"
    if c.upper() == "PT":
        return "PT"
    return "PT"

def yes(x: str) -> bool:
    x = (x or "").strip().lower()
    return x.startswith(("s", "y", "o"))

def num(x) -> Optional[float]:
    try:
        s = str(x).strip()
        if s == "":
            return None
        return float(s.replace(",", "").replace(" ", ""))
    except Exception:
        return None

def parse_date(s: str) -> Optional[date]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def fmt_date(d: Optional[date]) -> str:
    return d.isoformat() if d else "-"

def display_status(canon_pt: str) -> str:
    if REPORT_LANG == "PT":
        return canon_pt
    if REPORT_LANG == "FR":
        mapping = {
            "SUPEROU": "DÉPASSÉ",
            "VERDE": "VERT",
            "AMARELO": "JAUNE",
            "VERMELHO": "ROUGE",
            "SEM DADOS": "SANS DONNÉES",
        }
        return mapping.get(canon_pt, canon_pt)
    mapping = {
        "SUPEROU": "EXCEEDED",
        "VERDE": "GREEN",
        "AMARELO": "YELLOW",
        "VERMELHO": "RED",
        "SEM DADOS": "NO DATA",
    }
    return mapping.get(canon_pt, canon_pt)

# ----------------------------
# DOMAIN MODELS (Reporting)
# ----------------------------
@dataclass
class LocationEntry:
    country: str
    province: str
    district: str
    latitude: float
    longitude: float
    target_local: Optional[float]
    actual_local: Optional[float]
    budget_local: Optional[float]
    currency: str

@dataclass
class Indicator:
    id: str
    name: str
    unit: str
    frequency: str
    direction: str            # up/down
    level: str                # Legacy metadata only; canonical hierarchy uses IndicatorResultLink.
    target: Optional[float]
    baseline: Optional[float]
    locations: List[LocationEntry] = field(default_factory=list)
    organization_id: str = ""
    project_id: str = ""

    def progress_for(self, actual: Optional[float], target: Optional[float]) -> Optional[float]:
        if actual is None or target is None:
            return None
        d = (self.direction or "up").lower()

        if d == "down":
            if self.baseline is None:
                if target == 0:
                    return None
                return ((target - actual) / target) * 100
            denom = (self.baseline - target)
            if denom == 0:
                return None
            return ((self.baseline - actual) / denom) * 100

        # up
        if self.baseline is None:
            if target == 0:
                return None
            return (actual / target) * 100
        denom = (target - self.baseline)
        if denom == 0:
            return None
        return ((actual - self.baseline) / denom) * 100

    def status_canon_for(self, progress: Optional[float]) -> str:
        if progress is None:
            return "SEM DADOS"
        t = CONFIG["status_thresholds"]
        if progress >= t["superou"]:
            return "SUPEROU"
        if progress >= t["verde"]:
            return "VERDE"
        if progress >= t["amarelo"]:
            return "AMARELO"
        return "VERMELHO"

@dataclass
class ProjectTeamAssignment:
    id: str
    project_id: str
    organization_id: str
    user_id: str
    role: str
    team_id: str = ""
    assigned_at: str = ""
    assigned_by_user_id: str = ""
    assigned_by_name: str = ""
    status: str = "active"

@dataclass
class Project:
    id: str
    name: str
    objective: str
    organization_id: str = ""
    project_code: str = ""
    programme: str = ""
    donor: str = ""
    implementing_partner: str = ""
    sector: str = ""
    description: str = ""
    country: str = ""
    province_coverage: List[str] = field(default_factory=list)
    district_coverage: List[str] = field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = "active"
    created_by_user_id: str = ""
    created_by_name: str = ""
    created_at: str = ""
    updated_at: str = ""
    published_at: str = ""
    status_before_archive: str = ""
    team_assignments: List[ProjectTeamAssignment] = field(default_factory=list)
    workspace_shell: Dict[str, Any] = field(default_factory=dict)
    cloned_from_project_id: str = ""
    indicators: List[Indicator] = field(default_factory=list)

# ----------------------------
# DOMAIN MODELS (Ops Lite)
# ----------------------------
@dataclass
class Task:
    id: str
    name: str
    owner: str
    due_date: Optional[date]
    status: str
    organization_id: str = ""
    notes: str = ""
    assignee_username: str = ""
    assignee_name: str = ""
    priority: str = "medium"
    progress_pct: float = 0.0
    category: str = "implementation"
    linked_indicator_id: str = ""
    evidence_placeholders: List[str] = field(default_factory=list)
    activity_log: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    submitted_at: str = ""
    validated_at: str = ""
    approved_at: str = ""

@dataclass
class OperationalActivity:
    id: str
    name: str
    owner: str
    start_date: Optional[date]
    due_date: Optional[date]
    status: str               # planned/ongoing/done
    organization_id: str = ""
    linked_indicator_ids: List[str] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)

@dataclass
class OpsLite:
    activities: List[OperationalActivity] = field(default_factory=list)

# ----------------------------
# DATASTORE (JSON)
# ----------------------------
@dataclass
class LogiTrackData:
    organizations: List[OrganizationAccount] = field(default_factory=list)
    teams: List[TeamAccount] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    logical_framework_results: List[ResultNode] = field(default_factory=list)
    indicator_result_links: List[IndicatorResultLink] = field(default_factory=list)
    ops_by_project: Dict[str, OpsLite] = field(default_factory=dict)
    tidy_datasets: List[TidyDataset] = field(default_factory=list)
    reporting_records: List[ReportingPeriodRecord] = field(default_factory=list)
    semantic_mappings: List[SemanticMapping] = field(default_factory=list)
    dashboard_templates: List[DashboardTemplate] = field(default_factory=list)
    notification_rules: List[NotificationRule] = field(default_factory=list)
    users: List[UserAccount] = field(default_factory=list)
    audit_events: List[AuditEvent] = field(default_factory=list)

def new_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

def to_serializable(data: LogiTrackData) -> dict:
    def convert(obj):
        if isinstance(obj, date):
            return obj.isoformat()
        if hasattr(obj, "__dict__") and not isinstance(obj, dict):
            d = asdict(obj)
            return {k: convert(v) for k, v in d.items()}
        if isinstance(obj, list):
            return [convert(x) for x in obj]
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        return obj
    return convert(data)

def construct_compat_model(model_cls: Any, **kwargs: Any) -> Any:
    allowed = getattr(model_cls, "__dataclass_fields__", None)
    if isinstance(allowed, dict) and allowed:
        filtered = {key: value for key, value in kwargs.items() if key in allowed}
        instance = model_cls(**filtered)
        for key, value in kwargs.items():
            if key in filtered or hasattr(instance, key):
                continue
            try:
                setattr(instance, key, value)
            except Exception:
                pass
        return instance
    return model_cls(**kwargs)

def from_serializable(d: dict) -> LogiTrackData:
    organizations: List[OrganizationAccount] = []
    for org in d.get("organizations", []):
        organizations.append(construct_compat_model(OrganizationAccount,
            id=str(org["id"]),
            organization_name=str(org.get("organization_name", "")),
            status=str(org.get("status", "active") or "active"),
            subscription_plan=str(org.get("subscription_plan", "foundation") or "foundation"),
            country=str(org.get("country", "")),
            timezone=str(org.get("timezone", "")),
            default_language=str(org.get("default_language", "EN") or "EN"),
            contact_email=str(org.get("contact_email", "")),
            contact_person=str(org.get("contact_person", "")),
            logo_placeholder=str(org.get("logo_placeholder", "")),
            created_at=str(org.get("created_at", "")),
            updated_at=str(org.get("updated_at", "")),
        ))

    teams: List[TeamAccount] = []
    for item in d.get("teams", []):
        teams.append(construct_compat_model(TeamAccount,
            id=str(item["id"]),
            organization_id=str(item.get("organization_id", "")),
            team_name=str(item.get("team_name", "")),
            description=str(item.get("description", "")),
            team_lead_user_id=str(item.get("team_lead_user_id", "")),
            status=str(item.get("status", "active") or "active"),
            created_at=str(item.get("created_at", "")),
            updated_at=str(item.get("updated_at", "")),
        ))

    projects: List[Project] = []
    for p in d.get("projects", []):
        inds: List[Indicator] = []
        for i in p.get("indicators", []):
            declared_organization_id = str(i.get("organization_id", "") or "")
            declared_project_id = str(i.get("project_id", "") or "")
            project_organization_id = str(p.get("organization_id", "") or "")
            project_id = str(p.get("id", "") or "")
            if declared_organization_id and project_organization_id and declared_organization_id != project_organization_id:
                raise ValueError(f"Indicator '{i.get('id', '')}' organization ownership conflicts with its project.")
            if declared_project_id and declared_project_id != project_id:
                raise ValueError(f"Indicator '{i.get('id', '')}' project ownership conflicts with its containing project.")
            locs: List[LocationEntry] = []
            for loc in i.get("locations", []):
                locs.append(LocationEntry(
                    country=loc["country"],
                    province=loc["province"],
                    district=loc["district"],
                    latitude=float(loc["latitude"]),
                    longitude=float(loc["longitude"]),
                    target_local=loc.get("target_local"),
                    actual_local=loc.get("actual_local"),
                    budget_local=loc.get("budget_local"),
                    currency=loc.get("currency", "")
                ))
            inds.append(Indicator(
                id=i["id"],
                name=i["name"],
                unit=i["unit"],
                frequency=i["frequency"],
                direction=i["direction"],
                level=i.get("level", "output"),
                target=i.get("target"),
                baseline=i.get("baseline"),
                locations=locs,
                organization_id=declared_organization_id or project_organization_id,
                project_id=declared_project_id or project_id,
            ))
        assignments: List[ProjectTeamAssignment] = []
        for assignment in p.get("team_assignments", []) or []:
            if not isinstance(assignment, dict):
                continue
            assignments.append(ProjectTeamAssignment(
                id=str(assignment.get("id") or new_id("projteam")),
                project_id=str(assignment.get("project_id") or p.get("id") or ""),
                organization_id=str(assignment.get("organization_id") or p.get("organization_id", "") or ""),
                user_id=str(assignment.get("user_id") or ""),
                role=normalize_role(str(assignment.get("role") or "executive_viewer")),
                team_id=str(assignment.get("team_id") or ""),
                assigned_at=str(assignment.get("assigned_at") or ""),
                assigned_by_user_id=str(assignment.get("assigned_by_user_id") or ""),
                assigned_by_name=str(assignment.get("assigned_by_name") or ""),
                status=str(assignment.get("status") or "active"),
            ))
        projects.append(Project(
            id=p["id"],
            name=p["name"],
            objective=p["objective"],
            organization_id=str(p.get("organization_id", "")),
            project_code=str(p.get("project_code", "")),
            programme=str(p.get("programme", "")),
            donor=str(p.get("donor", "")),
            implementing_partner=str(p.get("implementing_partner", p.get("partner", ""))),
            sector=str(p.get("sector", "")),
            description=str(p.get("description", p.get("objective", ""))),
            country=str(p.get("country", "")),
            province_coverage=[str(item) for item in p.get("province_coverage", []) if str(item).strip()],
            district_coverage=[str(item) for item in p.get("district_coverage", []) if str(item).strip()],
            start_date=parse_date(str(p.get("start_date", "") or "")),
            end_date=parse_date(str(p.get("end_date", "") or "")),
            status=normalize_project_status(str(p.get("status", "active") or "active")),
            created_by_user_id=str(p.get("created_by_user_id", "")),
            created_by_name=str(p.get("created_by_name", "")),
            created_at=str(p.get("created_at", "")),
            updated_at=str(p.get("updated_at", "")),
            published_at=str(p.get("published_at", "")),
            status_before_archive=str(p.get("status_before_archive", "")),
            team_assignments=assignments,
            workspace_shell=p.get("workspace_shell", {}) if isinstance(p.get("workspace_shell", {}), dict) else {},
            cloned_from_project_id=str(p.get("cloned_from_project_id", "")),
            indicators=inds
        ))

    logical_framework_results: List[ResultNode] = []
    for item in d.get("logical_framework_results", []) or []:
        if not isinstance(item, dict):
            continue
        logical_framework_results.append(ResultNode(
            id=str(item.get("id", "")),
            organization_id=str(item.get("organization_id", "")),
            project_id=str(item.get("project_id", "")),
            result_type=str(item.get("result_type", "")),
            title=str(item.get("title", "")),
            description=str(item.get("description", "")),
            parent_id=str(item.get("parent_id", "")),
            display_order=int(item.get("display_order", 0) or 0),
            status=str(item.get("status", "active") or "active"),
            created_at=str(item.get("created_at", "")),
            updated_at=str(item.get("updated_at", "")),
        ))

    indicator_result_links: List[IndicatorResultLink] = []
    for item in d.get("indicator_result_links", []) or []:
        if not isinstance(item, dict):
            continue
        indicator_result_links.append(IndicatorResultLink(
            id=str(item.get("id", "")),
            organization_id=str(item.get("organization_id", "")),
            project_id=str(item.get("project_id", "")),
            indicator_id=str(item.get("indicator_id", "")),
            result_id=str(item.get("result_id", "")),
            result_type=str(item.get("result_type", "")),
            created_at=str(item.get("created_at", "")),
            updated_at=str(item.get("updated_at", "")),
        ))

    ops_by_project: Dict[str, OpsLite] = {}
    for pid, ops in d.get("ops_by_project", {}).items():
        acts: List[OperationalActivity] = []
        for a in ops.get("activities", []):
            tasks: List[Task] = []
            for t in a.get("tasks", []):
                task_status = normalize_task_status(t.get("status", "todo"))
                tasks.append(Task(
                    id=t["id"],
                    name=t["name"],
                    owner=t.get("owner", ""),
                    due_date=parse_date(t.get("due_date", "")),
                    status=task_status,
                    organization_id=str(t.get("organization_id", "") or a.get("organization_id", "")),
                    notes=t.get("notes", ""),
                    assignee_username=t.get("assignee_username", ""),
                    assignee_name=t.get("assignee_name", ""),
                    priority=str(t.get("priority", "medium") or "medium"),
                    progress_pct=float(num(t.get("progress_pct")) or task_progress_default(task_status)),
                    category=str(t.get("category", "implementation") or "implementation"),
                    linked_indicator_id=str(t.get("linked_indicator_id", "") or ""),
                    evidence_placeholders=[str(item) for item in t.get("evidence_placeholders", []) if str(item).strip()],
                    activity_log=[item for item in t.get("activity_log", []) if isinstance(item, dict)],
                    created_at=str(t.get("created_at", "")),
                    updated_at=str(t.get("updated_at", "")),
                    submitted_at=str(t.get("submitted_at", "")),
                    validated_at=str(t.get("validated_at", "")),
                    approved_at=str(t.get("approved_at", "")),
                ))
            acts.append(OperationalActivity(
                id=a["id"],
                name=a["name"],
                owner=a.get("owner", ""),
                start_date=parse_date(a.get("start_date", "")),
                due_date=parse_date(a.get("due_date", "")),
                status=a.get("status", "planned"),
                organization_id=str(a.get("organization_id", "")),
                linked_indicator_ids=a.get("linked_indicator_ids", []),
                tasks=tasks
            ))
        ops_by_project[pid] = OpsLite(activities=acts)

    tidy_datasets: List[TidyDataset] = []
    for ds in d.get("tidy_datasets", []):
        rows = ds.get("rows", [])
        if not isinstance(rows, list):
            rows = []
        tidy_datasets.append(TidyDataset(
            id=ds["id"],
            name=ds["name"],
            description=ds.get("description", ""),
            source_type=ds.get("source_type", "rows"),
            organization_id=str(ds.get("organization_id", "")),
            created_at=ds.get("created_at", ""),
            updated_at=ds.get("updated_at", ""),
            rows=[row for row in rows if isinstance(row, dict)]
        ))

    reporting_records: List[ReportingPeriodRecord] = []
    for record in d.get("reporting_records", []):
        reporting_records.append(ReportingPeriodRecord(
            id=record["id"],
            reporting_period=str(record.get("reporting_period", "")),
            project_id=str(record.get("project_id", "")),
            project_name=str(record.get("project_name", "")),
            organization_id=str(record.get("organization_id", "")),
            indicator_id=str(record.get("indicator_id", "")),
            indicator_name=str(record.get("indicator_name", "")),
            country=str(record.get("country", "")),
            province=str(record.get("province", "")),
            district=str(record.get("district", "")),
            actual_value=num(record.get("actual_value")),
            target_value=num(record.get("target_value")),
            progress_value=num(record.get("progress_value")),
            budget_value=num(record.get("budget_value")),
            currency=str(record.get("currency", "")),
            status=str(record.get("status", "")),
            owner=str(record.get("owner", "")),
            notes=str(record.get("notes", "")),
            source_dataset_id=str(record.get("source_dataset_id", "")),
            created_at=str(record.get("created_at", "")),
            updated_at=str(record.get("updated_at", "")),
        ))

    semantic_mappings: List[SemanticMapping] = []
    for item in d.get("semantic_mappings", []):
        fields = item.get("fields", {})
        semantic_mappings.append(SemanticMapping(
            id=str(item["id"]),
            dataset_id=str(item.get("dataset_id", "")),
            name=str(item.get("name", "default")),
            organization_id=str(item.get("organization_id", "")),
            fields={str(k): str(v) for k, v in fields.items()} if isinstance(fields, dict) else {},
            status=str(item.get("status", "suggested")),
            confidence=float(item.get("confidence", 0.0) or 0.0),
            notes=str(item.get("notes", "")),
            created_at=str(item.get("created_at", "")),
            updated_at=str(item.get("updated_at", "")),
        ))

    dashboard_templates: List[DashboardTemplate] = []
    for item in d.get("dashboard_templates", []):
        visuals = item.get("visuals", [])
        layout = item.get("layout", [])
        narrative_sections = item.get("narrative_sections", [])
        filters = item.get("filters", [])
        dashboard_templates.append(DashboardTemplate(
            id=str(item["id"]),
            name=str(item.get("name", "")),
            description=str(item.get("description", "")),
            dashboard_type=str(item.get("dashboard_type", "")),
            organization_id=str(item.get("organization_id", "")),
            scope=str(item.get("scope", "custom")),
            filters=[str(x) for x in filters] if isinstance(filters, list) else [],
            visuals=[x for x in visuals if isinstance(x, dict)] if isinstance(visuals, list) else [],
            layout=[x for x in layout if isinstance(x, dict)] if isinstance(layout, list) else [],
            narrative_sections=[str(x) for x in narrative_sections] if isinstance(narrative_sections, list) else [],
            theme=str(item.get("theme", "studio_default")),
            created_at=str(item.get("created_at", "")),
            updated_at=str(item.get("updated_at", "")),
        ))

    notification_rules: List[NotificationRule] = []
    for item in d.get("notification_rules", []):
        recipients = item.get("recipients", [])
        notification_rules.append(NotificationRule(
            id=str(item["id"]),
            name=str(item.get("name", "")),
            is_active=bool(item.get("is_active", True)),
            organization_id=str(item.get("organization_id", "")),
            schedule=str(item.get("schedule", "manual")),
            channel=str(item.get("channel", "webhook")),
            provider=str(item.get("provider", "")),
            min_severity=str(item.get("min_severity", "medium")),
            condition_type=str(item.get("condition_type", "")),
            threshold=num(item.get("threshold")),
            project_id=str(item.get("project_id", "")),
            indicator_id=str(item.get("indicator_id", "")),
            dataset_id=str(item.get("dataset_id", "")),
            recipients=[str(x) for x in recipients] if isinstance(recipients, list) else [],
            webhook_url=str(item.get("webhook_url", "")),
            notes=str(item.get("notes", "")),
            last_run_at=str(item.get("last_run_at", "")),
            created_at=str(item.get("created_at", "")),
            updated_at=str(item.get("updated_at", "")),
        ))

    users: List[UserAccount] = []
    for item in d.get("users", []):
        users.append(construct_compat_model(UserAccount,
            id=str(item["id"]),
            username=str(item.get("username", "")),
            organization_id=str(item.get("organization_id", "")),
            team_id=str(item.get("team_id", "")),
            full_name=str(item.get("full_name", "")),
            email=str(item.get("email", "")),
            role=str(item.get("role", "viewer")),
            status=str(item.get("status", "active") or "active"),
            permissions=normalize_permission_ids(item.get("permissions", [])),
            password_salt=str(item.get("password_salt", "")),
            password_hash=str(item.get("password_hash", "")),
            api_token_hash=str(item.get("api_token_hash", "")),
            is_active=bool(item.get("is_active", True)),
            created_at=str(item.get("created_at", "")),
            updated_at=str(item.get("updated_at", "")),
            last_login_at=str(item.get("last_login_at", "")),
        ))

    audit_events: List[AuditEvent] = []
    for item in d.get("audit_events", []):
        details = item.get("details", {})
        audit_events.append(AuditEvent(
            id=str(item["id"]),
            occurred_at=str(item.get("occurred_at", "")),
            organization_id=str(item.get("organization_id", "")),
            actor_id=str(item.get("actor_id", "")),
            actor_username=str(item.get("actor_username", "")),
            actor_role=str(item.get("actor_role", "")),
            action=str(item.get("action", "")),
            target_type=str(item.get("target_type", "")),
            target_id=str(item.get("target_id", "")),
            endpoint=str(item.get("endpoint", "")),
            outcome=str(item.get("outcome", "success")),
            details=details if isinstance(details, dict) else {},
        ))

    loaded = LogiTrackData(
        organizations=organizations,
        teams=teams,
        projects=projects,
        logical_framework_results=logical_framework_results,
        indicator_result_links=indicator_result_links,
        ops_by_project=ops_by_project,
        tidy_datasets=tidy_datasets,
        reporting_records=reporting_records,
        semantic_mappings=semantic_mappings,
        dashboard_templates=dashboard_templates,
        notification_rules=notification_rules,
        users=users,
        audit_events=audit_events,
    )
    if loaded.logical_framework_results or loaded.indicator_result_links:
        validate_snapshot_logical_framework(loaded)
    return loaded

def get_storage_backend() -> str:
    raw = (os.getenv("LOGITRACK_STORAGE_BACKEND", "") or "").strip().lower()
    if raw in {"json", "sqlite"}:
        return raw
    if (os.getenv("LOGITRACK_SQLITE_PATH", "") or "").strip():
        return "sqlite"
    return "json"

def get_json_data_path(path: Optional[str] = None) -> str:
    return path or os.getenv("LOGITRACK_DATA_PATH", DEFAULT_DATA_PATH)

def get_sqlite_data_path(path: Optional[str] = None) -> str:
    if path:
        return path
    configured = (os.getenv("LOGITRACK_SQLITE_PATH", "") or "").strip()
    if configured:
        return configured
    json_path = get_json_data_path()
    base, _ = os.path.splitext(json_path)
    return base + ".sqlite3"

def get_data_path(path: Optional[str] = None) -> str:
    return get_storage_target_path(path)

def get_storage_target_path(path: Optional[str] = None, backend: Optional[str] = None) -> str:
    selected_backend = backend or get_storage_backend()
    if selected_backend == "sqlite":
        return get_sqlite_data_path(path)
    return get_json_data_path(path)

def _json_backup_path(path: str) -> str:
    return f"{path}.bak"

def _atomic_write_text(path: str, text: str) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(target.parent), delete=False) as handle:
            tmp_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if os.path.exists(target):
            backup_path = _json_backup_path(str(target))
            try:
                with open(target, "r", encoding="utf-8") as source_file:
                    previous = source_file.read()
                with open(backup_path, "w", encoding="utf-8") as backup_file:
                    backup_file.write(previous)
            except Exception:
                pass
        os.replace(tmp_name, target)
    except Exception:
        if tmp_name and os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except Exception:
                pass
        raise

def save_json(data: LogiTrackData, path: str) -> None:
    serialized = json.dumps(to_serializable(data), ensure_ascii=False, indent=2)
    with DATA_STORE_LOCK:
        _atomic_write_text(path, serialized)

def load_json(path: str) -> LogiTrackData:
    with DATA_STORE_LOCK:
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return from_serializable(d)
        except json.JSONDecodeError:
            backup_path = _json_backup_path(path)
            if not os.path.exists(backup_path):
                raise
            with open(backup_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return from_serializable(d)

def _sqlite_connect(path: str) -> sqlite3.Connection:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=30, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def _ensure_sqlite_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_state (
            state_key TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS state_revisions (
            revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
            updated_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
    """)

def _sqlite_revision_limit() -> int:
    raw = (os.getenv("LOGITRACK_SQLITE_REVISION_LIMIT", "25") or "25").strip()
    try:
        return max(5, min(500, int(raw)))
    except Exception:
        return 25

def save_sqlite(data: LogiTrackData, path: str) -> None:
    payload_json = json.dumps(to_serializable(data), ensure_ascii=False)
    updated_at = now_iso_utc()
    with DATA_STORE_LOCK:
        conn = _sqlite_connect(path)
        try:
            _ensure_sqlite_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO app_state (state_key, payload_json, updated_at)
                VALUES ('primary', ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (payload_json, updated_at),
            )
            conn.execute(
                "INSERT INTO state_revisions (updated_at, payload_json) VALUES (?, ?)",
                (updated_at, payload_json),
            )
            limit = _sqlite_revision_limit()
            conn.execute(
                """
                DELETE FROM state_revisions
                WHERE revision_id NOT IN (
                    SELECT revision_id FROM state_revisions
                    ORDER BY revision_id DESC
                    LIMIT ?
                )
                """,
                (limit,),
            )
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            conn.close()

def load_sqlite(path: str) -> LogiTrackData:
    if not os.path.exists(path):
        return LogiTrackData()
    with DATA_STORE_LOCK:
        conn = _sqlite_connect(path)
        try:
            _ensure_sqlite_schema(conn)
            row = conn.execute(
                "SELECT payload_json FROM app_state WHERE state_key = 'primary'"
            ).fetchone()
            if row is None or not row["payload_json"]:
                return LogiTrackData()
            return from_serializable(json.loads(str(row["payload_json"])))
        finally:
            conn.close()

def load_data_from_path(path: Optional[str] = None) -> LogiTrackData:
    backend = get_storage_backend()
    target = get_storage_target_path(path, backend=backend)
    if backend == "sqlite":
        if not os.path.exists(target):
            legacy_json_path = get_json_data_path(None)
            if legacy_json_path != target and os.path.exists(legacy_json_path):
                data = load_json(legacy_json_path)
                save_sqlite(data, target)
                loaded = data
            else:
                loaded = load_sqlite(target)
        else:
            loaded = load_sqlite(target)
    else:
        if not os.path.exists(target):
            loaded = LogiTrackData()
        else:
            loaded = load_json(target)
    if repository_domains_enabled():
        try:
            hydrated_snapshot = hydrate_snapshot_with_repository_domains(
                to_serializable(loaded),
                db_path=get_relational_store_path(target),
            )
            loaded = from_serializable(hydrated_snapshot)
        except Exception as exc:
            LOGGER.warning("Repository domain hydration failed; falling back to snapshot state. %s", exc)
    return loaded

def get_cors_origins() -> List[str]:
    raw = (os.getenv("LOGITRACK_API_ALLOW_ORIGINS", "*") or "").strip()
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["*"]

def save_canonical_data_to_path(data: LogiTrackData, path: Optional[str] = None) -> str:
    backend = get_storage_backend()
    target = get_storage_target_path(path, backend=backend)
    if backend == "sqlite":
        save_sqlite(data, target)
    else:
        save_json(data, target)
    return target

def save_data_to_path(data: LogiTrackData, path: Optional[str] = None) -> str:
    target = save_canonical_data_to_path(data, path)
    update_relational_store_from_data(data, source_path=target)
    return target

def get_storage_status(path: Optional[str] = None) -> Dict[str, Any]:
    backend = get_storage_backend()
    target = get_storage_target_path(path, backend=backend)
    exists = os.path.exists(target)
    size_bytes = os.path.getsize(target) if exists else 0
    status = {
        "backend": backend,
        "target_path": target,
        "exists": exists,
        "size_bytes": size_bytes,
    }
    if backend == "json":
        backup_path = _json_backup_path(target)
        status["backup_path"] = backup_path
        status["backup_exists"] = os.path.exists(backup_path)
    else:
        revision_count = 0
        if exists:
            conn = _sqlite_connect(target)
            try:
                _ensure_sqlite_schema(conn)
                revision_count = int(conn.execute("SELECT COUNT(*) FROM state_revisions").fetchone()[0])
            finally:
                conn.close()
        status["revision_limit"] = _sqlite_revision_limit()
        status["revisions"] = revision_count
    return status

def safe_get_storage_status(path: Optional[str] = None) -> Dict[str, Any]:
    try:
        return get_storage_status(path)
    except Exception as exc:
        target = get_storage_target_path(path)
        return {
            "backend": get_storage_backend(),
            "target_path": target,
            "exists": os.path.exists(target),
            "size_bytes": os.path.getsize(target) if os.path.exists(target) else 0,
            "error": str(exc),
        }

def update_relational_store_from_data(data: LogiTrackData, source_path: str = "") -> Optional[Dict[str, Any]]:
    RELATIONAL_SYNC_STATE["enabled"] = relational_mirror_enabled_setting()
    REPOSITORY_SYNC_STATE["enabled"] = repository_domains_enabled()
    if not RELATIONAL_SYNC_STATE["enabled"]:
        RELATIONAL_SYNC_STATE["last_result"] = {}
        RELATIONAL_SYNC_STATE["last_error"] = ""
        REPOSITORY_SYNC_STATE["last_result"] = {}
        REPOSITORY_SYNC_STATE["last_error"] = ""
        return None
    try:
        result = sync_snapshot_to_relational_store(
            to_serializable(data),
            db_path=get_relational_store_path(source_path or get_storage_target_path()),
            source_backend=get_storage_backend(),
            source_path=source_path or get_storage_target_path(),
        )
        RELATIONAL_SYNC_STATE["last_synced_at"] = str(result.get("synced_at", ""))
        RELATIONAL_SYNC_STATE["last_error"] = ""
        RELATIONAL_SYNC_STATE["last_result"] = result
        LOGGER.info("Relational mirror synchronized", extra={"relational_sync": result})
        if REPOSITORY_SYNC_STATE["enabled"]:
            repository_result = sync_repository_backed_domains_from_snapshot(
                to_serializable(data),
                db_path=get_relational_store_path(source_path or get_storage_target_path()),
            )
            REPOSITORY_SYNC_STATE["last_synced_at"] = str(result.get("synced_at", ""))
            REPOSITORY_SYNC_STATE["last_error"] = ""
            REPOSITORY_SYNC_STATE["last_result"] = repository_result
        else:
            REPOSITORY_SYNC_STATE["last_result"] = {}
            REPOSITORY_SYNC_STATE["last_error"] = ""
        return result
    except Exception as exc:
        RELATIONAL_SYNC_STATE["last_error"] = str(exc)
        RELATIONAL_SYNC_STATE["last_result"] = {}
        REPOSITORY_SYNC_STATE["last_error"] = str(exc)
        REPOSITORY_SYNC_STATE["last_result"] = {}
        LOGGER.exception("Relational mirror synchronization failed")
        if relational_sync_strict_setting():
            raise
        return None

def safe_get_relational_store_status(source_path: str = "") -> Dict[str, Any]:
    try:
        status = get_relational_store_status(get_relational_store_path(source_path or get_storage_target_path()))
        status["mirror_enabled"] = relational_mirror_enabled_setting()
        status["last_sync_state"] = dict(RELATIONAL_SYNC_STATE)
        return status
    except Exception as exc:
        return {
            "path": get_relational_store_path(source_path or get_storage_target_path()),
            "exists": os.path.exists(get_relational_store_path(source_path or get_storage_target_path())),
            "mirror_enabled": relational_mirror_enabled_setting(),
            "error": str(exc),
            "last_sync_state": dict(RELATIONAL_SYNC_STATE),
        }

def safe_get_repository_domain_status(source_path: str = "") -> Dict[str, Any]:
    status = safe_get_repository_sync_status(
        db_path=get_relational_store_path(source_path or get_storage_target_path()),
    )
    status["last_sync_state"] = dict(REPOSITORY_SYNC_STATE)
    return status

def normalize_choice(value: Optional[str], allowed: Tuple[str, ...], default: str) -> str:
    normalized = (value or default).strip().lower()
    if normalized in allowed:
        return normalized
    return default

def normalize_direction(value: Optional[str]) -> str:
    return normalize_choice(value, ("up", "down"), "up")

def normalize_level(value: Optional[str]) -> str:
    return normalize_choice(value, ("output", "outcome", "impact"), "output")

def normalize_activity_status(value: Optional[str]) -> str:
    return normalize_choice(value, ("planned", "ongoing", "done"), "planned")

def normalize_project_status(value: Optional[str], default: str = "draft") -> str:
    raw = str(value or default).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "draft": "draft",
        "published": "published",
        "publish": "published",
        "active": "active",
        "activated": "active",
        "paused": "paused",
        "pause": "paused",
        "deactivated": "paused",
        "inactive": "paused",
        "completed": "completed",
        "complete": "completed",
        "done": "completed",
        "archived": "archived",
        "archive": "archived",
    }
    normalized = aliases.get(raw, raw)
    allowed = {"draft", "published", "active", "paused", "completed", "archived"}
    return normalized if normalized in allowed else default

def normalize_project_assignment_role(value: Optional[str]) -> str:
    normalized = normalize_role(value)
    allowed = {"programme_manager", "meal_officer", "field_coordinator", "executive_viewer"}
    return normalized if normalized in allowed else "executive_viewer"

def normalize_task_status(value: Optional[str]) -> str:
    raw = str(value or "not_started").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "todo": "not_started",
        "not_started": "not_started",
        "new": "not_started",
        "doing": "in_progress",
        "inprogress": "in_progress",
        "in_progress": "in_progress",
        "ongoing": "in_progress",
        "pending_validation": "pending_validation",
        "awaiting_validation": "pending_validation",
        "validation_pending": "pending_validation",
        "done": "completed",
        "complete": "completed",
        "completed": "completed",
        "approved": "completed",
        "closed": "completed",
        "resolved": "completed",
        "overdue": "overdue",
        "escalated": "escalated",
    }
    normalized = aliases.get(raw, raw)
    allowed = {"not_started", "in_progress", "pending_validation", "completed", "overdue", "escalated"}
    return normalized if normalized in allowed else "not_started"

def task_progress_default(status: Optional[str]) -> float:
    key = normalize_task_status(status)
    if key == "completed":
        return 100.0
    if key == "pending_validation":
        return 90.0
    if key == "in_progress":
        return 55.0
    if key == "escalated":
        return 38.0
    if key == "overdue":
        return 25.0
    return 0.0

def task_status_is_complete(value: Any) -> bool:
    return normalize_task_status(value) == "completed"

def task_status_is_open(value: Any) -> bool:
    return not task_status_is_complete(value)

def task_status_display_label(value: Any) -> str:
    mapping = {
        "not_started": "Not Started",
        "in_progress": "In Progress",
        "pending_validation": "Pending Validation",
        "completed": "Completed",
        "overdue": "Overdue",
        "escalated": "Escalated",
    }
    return mapping.get(normalize_task_status(value), "Not Started")

def parse_optional_date_value(value: Any, field_name: str) -> Optional[date]:
    if value in (None, ""):
        return None
    parsed = parse_date(str(value))
    if parsed is None:
        raise ValueError(f"Invalid date for '{field_name}'. Use YYYY-MM-DD.")
    return parsed

def normalize_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, list):
        raw_items = value
    else:
        raise ValueError("Expected a list or comma-separated string.")

    seen = set()
    result = []
    for item in raw_items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result

def now_iso_utc() -> str:
    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


UTC_DATETIME_MIN = datetime.min.replace(tzinfo=timezone.utc)
UTC_DATETIME_MAX = datetime.max.replace(tzinfo=timezone.utc)

def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}

def scheduler_enabled_setting() -> bool:
    return env_flag("LOGITRACK_RUN_SCHEDULER", False)

def scheduler_interval_seconds_setting() -> int:
    raw = (os.getenv("LOGITRACK_SCHEDULER_INTERVAL_SECONDS", "300") or "300").strip()
    try:
        return max(30, min(86400, int(raw)))
    except Exception:
        return 300

def relational_mirror_enabled_setting() -> bool:
    return env_flag("LOGITRACK_ENABLE_RELATIONAL_MIRROR", True)

def relational_sync_strict_setting() -> bool:
    return env_flag("LOGITRACK_RELATIONAL_SYNC_STRICT", False)

PERMISSION_CATALOG = {
    "WORKSPACE_VIEW": {
        "label": "Workspace visibility",
        "scope": "workspace",
    },
    "WORKSPACE_ADMIN": {
        "label": "Workspace administration",
        "scope": "workspace",
    },
    "VIEW_PORTFOLIO": {
        "label": "Portfolio overview",
        "scope": "dashboard",
    },
    "VIEW_EXECUTIVE_SNAPSHOT": {
        "label": "Project executive snapshot",
        "scope": "dashboard",
    },
    "VIEW_INDICATORS": {
        "label": "Indicator intelligence",
        "scope": "analytics",
    },
    "EDIT_INDICATORS": {
        "label": "Edit indicator intelligence",
        "scope": "analytics",
    },
    "VIEW_LOGICAL_FRAMEWORK": {
        "label": "View Logical Framework",
        "scope": "results",
    },
    "MANAGE_LOGICAL_FRAMEWORK": {
        "label": "Manage Logical Framework structure",
        "scope": "results",
    },
    "LINK_RESULT_INDICATORS": {
        "label": "Link indicators to results",
        "scope": "results",
    },
    "VIEW_DATA_QUALITY": {
        "label": "Data quality review",
        "scope": "analytics",
    },
    "VALIDATE_EVIDENCE": {
        "label": "Validate evidence",
        "scope": "workflow",
    },
    "VIEW_WORKPLAN": {
        "label": "Workplan visibility",
        "scope": "workflow",
    },
    "MANAGE_WORKPLAN": {
        "label": "Manage workplan",
        "scope": "workflow",
    },
    "MANAGE_PROJECTS": {
        "label": "Manage projects",
        "scope": "workflow",
    },
    "ASSIGN_TASKS": {
        "label": "Assign tasks",
        "scope": "workflow",
    },
    "UPDATE_TASK_PROGRESS": {
        "label": "Update task progress",
        "scope": "workflow",
    },
    "SUBMIT_EVIDENCE": {
        "label": "Submit evidence",
        "scope": "workflow",
    },
    "APPROVE_TASKS": {
        "label": "Approve tasks",
        "scope": "workflow",
    },
    "VIEW_REPORTS": {
        "label": "View reports",
        "scope": "reporting",
    },
    "GENERATE_REPORTS": {
        "label": "Generate reports",
        "scope": "reporting",
    },
    "VIEW_NOTIFICATIONS": {
        "label": "View notifications",
        "scope": "notifications",
    },
    "MANAGE_NOTIFICATIONS": {
        "label": "Manage notifications",
        "scope": "notifications",
    },
    "VIEW_RISKS": {
        "label": "View risks",
        "scope": "risk",
    },
    "MANAGE_USERS": {
        "label": "Manage users",
        "scope": "administration",
    },
    "MANAGE_ORGANIZATION": {
        "label": "Manage organization",
        "scope": "administration",
    },
    "VIEW_AUDIT_LOG": {
        "label": "View audit log",
        "scope": "administration",
    },
}

PERMISSION_ALIAS_MAP = {
    "workspace.view": "WORKSPACE_VIEW",
    "workspace.admin": "WORKSPACE_ADMIN",
    "organization.manage": "MANAGE_ORGANIZATION",
    "users.manage": "MANAGE_USERS",
    "portfolio.view": "VIEW_PORTFOLIO",
    "projects.view": "VIEW_EXECUTIVE_SNAPSHOT",
    "projects.manage": "MANAGE_WORKPLAN",
    "indicators.view": "VIEW_INDICATORS",
    "logical_framework.view": "VIEW_LOGICAL_FRAMEWORK",
    "logical_framework.manage": "MANAGE_LOGICAL_FRAMEWORK",
    "logical_framework.link_indicators": "LINK_RESULT_INDICATORS",
    "reporting.view": "VIEW_REPORTS",
    "data_quality.view": "VIEW_DATA_QUALITY",
    "tasks.view_assigned": "VIEW_WORKPLAN",
    "tasks.manage": "ASSIGN_TASKS",
    "tasks.update": "UPDATE_TASK_PROGRESS",
    "tasks.validate": "VALIDATE_EVIDENCE",
    "tasks.approve": "APPROVE_TASKS",
    "evidence.submit": "SUBMIT_EVIDENCE",
    "notifications.view": "VIEW_NOTIFICATIONS",
    "notifications.manage": "MANAGE_NOTIFICATIONS",
    "reports.view": "VIEW_REPORTS",
    "reports.manage": "GENERATE_REPORTS",
    "approvals.view": "VALIDATE_EVIDENCE",
    "risks.view": "VIEW_RISKS",
    "workplan.view": "VIEW_WORKPLAN",
    "audit.view": "VIEW_AUDIT_LOG",
}

ROLE_ALIAS_MAP = {
    "viewer": "executive_viewer",
    "executive": "executive_viewer",
    "executive_viewer": "executive_viewer",
    "analyst": "meal_officer",
    "meal": "meal_officer",
    "meal_officer": "meal_officer",
    "field": "field_coordinator",
    "field_coordinator": "field_coordinator",
    "manager": "programme_manager",
    "programme_manager": "programme_manager",
    "program_manager": "programme_manager",
    "admin": "organization_admin",
    "organization_admin": "organization_admin",
}

ROLE_ORDER = {
    "executive_viewer": 1,
    "field_coordinator": 2,
    "meal_officer": 3,
    "programme_manager": 4,
    "organization_admin": 5,
}

ROLE_LABELS = {
    "organization_admin": "Organization Admin",
    "programme_manager": "Programme Manager",
    "meal_officer": "MEAL Officer",
    "field_coordinator": "Field Coordinator",
    "executive_viewer": "Executive Viewer",
}

ROLE_PERMISSION_TEMPLATES = {
    "organization_admin": [
        *PERMISSION_CATALOG.keys(),
    ],
    "programme_manager": [
        "WORKSPACE_VIEW",
        "VIEW_PORTFOLIO",
        "VIEW_EXECUTIVE_SNAPSHOT",
        "VIEW_LOGICAL_FRAMEWORK",
        "MANAGE_LOGICAL_FRAMEWORK",
        "LINK_RESULT_INDICATORS",
        "VIEW_WORKPLAN",
        "MANAGE_WORKPLAN",
        "MANAGE_PROJECTS",
        "ASSIGN_TASKS",
        "APPROVE_TASKS",
        "VIEW_NOTIFICATIONS",
        "VIEW_RISKS",
        "VIEW_REPORTS",
        "GENERATE_REPORTS",
    ],
    "meal_officer": [
        "WORKSPACE_VIEW",
        "VIEW_PORTFOLIO",
        "VIEW_EXECUTIVE_SNAPSHOT",
        "VIEW_INDICATORS",
        "EDIT_INDICATORS",
        "VIEW_LOGICAL_FRAMEWORK",
        "LINK_RESULT_INDICATORS",
        "VIEW_DATA_QUALITY",
        "VIEW_WORKPLAN",
        "UPDATE_TASK_PROGRESS",
        "VALIDATE_EVIDENCE",
        "VIEW_NOTIFICATIONS",
        "VIEW_REPORTS",
    ],
    "field_coordinator": [
        "WORKSPACE_VIEW",
        "VIEW_PORTFOLIO",
        "VIEW_EXECUTIVE_SNAPSHOT",
        "VIEW_LOGICAL_FRAMEWORK",
        "VIEW_WORKPLAN",
        "UPDATE_TASK_PROGRESS",
        "SUBMIT_EVIDENCE",
        "VIEW_NOTIFICATIONS",
    ],
    "executive_viewer": [
        "WORKSPACE_VIEW",
        "VIEW_PORTFOLIO",
        "VIEW_EXECUTIVE_SNAPSHOT",
        "VIEW_LOGICAL_FRAMEWORK",
        "VIEW_NOTIFICATIONS",
        "VIEW_RISKS",
        "VIEW_REPORTS",
    ],
}

ADMIN_PERMISSION_GROUPS = {
    "Portfolio": ["WORKSPACE_VIEW", "VIEW_PORTFOLIO"],
    "Projects": ["VIEW_EXECUTIVE_SNAPSHOT", "MANAGE_PROJECTS", "VIEW_RISKS"],
    "Indicators": ["VIEW_INDICATORS", "EDIT_INDICATORS"],
    "Logical Framework": ["VIEW_LOGICAL_FRAMEWORK", "MANAGE_LOGICAL_FRAMEWORK", "LINK_RESULT_INDICATORS"],
    "Workplan": ["VIEW_WORKPLAN", "MANAGE_WORKPLAN"],
    "Tasks": ["ASSIGN_TASKS", "UPDATE_TASK_PROGRESS", "SUBMIT_EVIDENCE", "APPROVE_TASKS", "VALIDATE_EVIDENCE"],
    "Reporting": ["VIEW_REPORTS", "GENERATE_REPORTS"],
    "Data Quality": ["VIEW_DATA_QUALITY"],
    "Administration": ["MANAGE_USERS", "MANAGE_ORGANIZATION", "WORKSPACE_ADMIN"],
    "Notifications": ["VIEW_NOTIFICATIONS", "MANAGE_NOTIFICATIONS"],
    "Audit": ["VIEW_AUDIT_LOG"],
}

PROJECT_WORKSPACE_RESERVED_CONTAINERS = [
    ("indicators", "Indicators"),
    ("logical_framework", "Logical Framework"),
    ("workplan", "Workplan"),
    ("reporting", "Reporting"),
    ("budget", "Budget"),
    ("documents", "Documents"),
]

PROJECT_LIFECYCLE_TRANSITIONS = {
    "draft": {"published", "archived"},
    "published": {"active", "paused", "archived"},
    "active": {"paused", "completed", "archived"},
    "paused": {"active", "completed", "archived"},
    "completed": {"archived"},
    "archived": set(),
}

def normalize_role(value: Optional[str]) -> str:
    role = (value or "executive_viewer").strip().lower()
    return ROLE_ALIAS_MAP.get(role, "executive_viewer")

def role_allows(current_role: str, required_role: str) -> bool:
    return ROLE_ORDER.get(normalize_role(current_role), 0) >= ROLE_ORDER.get(normalize_role(required_role), 0)

def normalize_permission_id(value: Optional[str]) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw in PERMISSION_CATALOG:
        return raw
    upper = raw.upper()
    if upper in PERMISSION_CATALOG:
        return upper
    alias = PERMISSION_ALIAS_MAP.get(raw.lower())
    if alias:
        return alias
    return upper

def normalize_permission_ids(values: Optional[List[str]]) -> List[str]:
    seen: set[str] = set()
    normalized: List[str] = []
    for value in values or []:
        permission_id = normalize_permission_id(value)
        if permission_id and permission_id in PERMISSION_CATALOG and permission_id not in seen:
            seen.add(permission_id)
            normalized.append(permission_id)
    return normalized

def role_permissions(role: Optional[str]) -> List[str]:
    return list(ROLE_PERMISSION_TEMPLATES.get(normalize_role(role), []))

def effective_permissions(user: Optional[UserAccount]) -> List[str]:
    if user is None:
        return []
    explicit = normalize_permission_ids(getattr(user, "permissions", []) or [])
    return explicit or role_permissions(user.role)

def user_has_permission(user: Optional[UserAccount], permission_id: str) -> bool:
    normalized = normalize_permission_id(permission_id)
    return normalized in effective_permissions(user)

def user_has_any_permission(user: Optional[UserAccount], permission_ids: Optional[List[str]]) -> bool:
    required = normalize_permission_ids(permission_ids or [])
    if not required:
        return True
    granted = set(effective_permissions(user))
    return any(permission_id in granted for permission_id in required)

def user_has_all_permissions(user: Optional[UserAccount], permission_ids: Optional[List[str]]) -> bool:
    required = normalize_permission_ids(permission_ids or [])
    if not required:
        return True
    granted = set(effective_permissions(user))
    return all(permission_id in granted for permission_id in required)

def role_label(role: Optional[str]) -> str:
    return ROLE_LABELS.get(normalize_role(role), "Executive Viewer")

def permission_groups_payload() -> List[Dict[str, Any]]:
    grouped: List[Dict[str, Any]] = []
    for group_name, permission_ids in ADMIN_PERMISSION_GROUPS.items():
        grouped.append({
            "group_name": group_name,
            "permissions": [
                {
                    "id": permission_id,
                    "label": PERMISSION_CATALOG.get(permission_id, {}).get("label", permission_id.replace("_", " ").title()),
                    "scope": PERMISSION_CATALOG.get(permission_id, {}).get("scope", ""),
                }
                for permission_id in permission_ids
                if permission_id in PERMISSION_CATALOG
            ],
        })
    return grouped

def hash_with_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def build_password_hash(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_value.encode("utf-8"), 120000)
    return salt_value, base64.b64encode(digest).decode("ascii")

def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    _, computed = build_password_hash(password, salt=salt)
    return secrets.compare_digest(computed, expected_hash)

def new_api_token() -> str:
    return "lt_" + secrets.token_urlsafe(32)

def sanitize_user(user: UserAccount) -> Dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "organization_id": user.organization_id,
        "team_id": user.team_id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "role_label": role_label(user.role),
        "status": user.status,
        "permissions": effective_permissions(user),
        "role_template_permissions": role_permissions(user.role),
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login_at": user.last_login_at,
    }

def sanitize_organization(organization: OrganizationAccount) -> Dict[str, Any]:
    return {
        "id": organization.id,
        "organization_id": organization.id,
        "organization_name": organization.organization_name,
        "status": organization.status,
        "subscription_plan": organization.subscription_plan,
        "country": organization.country,
        "timezone": organization.timezone,
        "default_language": organization.default_language,
        "contact_email": organization.contact_email,
        "contact_person": organization.contact_person,
        "logo_placeholder": organization.logo_placeholder,
        "created_at": organization.created_at,
        "updated_at": organization.updated_at,
    }

def sanitize_team(data: LogiTrackData, team: TeamAccount) -> Dict[str, Any]:
    lead = find_user_by_id(data, team.team_lead_user_id) if team.team_lead_user_id else None
    member_count = len([
        user for user in data.users
        if user.organization_id == team.organization_id and user.team_id == team.id and user.status != "archived"
    ])
    return {
        "id": team.id,
        "team_id": team.id,
        "organization_id": team.organization_id,
        "team_name": team.team_name,
        "description": team.description,
        "team_lead_user_id": team.team_lead_user_id,
        "team_lead_name": lead.full_name if lead else "",
        "status": team.status,
        "member_count": member_count,
        "created_at": team.created_at,
        "updated_at": team.updated_at,
    }

def projects_for_organization(data: LogiTrackData, organization_id: str) -> List[Project]:
    target = str(organization_id or "").strip()
    if not target:
        return []
    return [project for project in data.projects if str(getattr(project, "organization_id", "") or "").strip() == target]

def ensure_project_scope(actor: Optional[UserAccount], project: Optional[Project]) -> None:
    if actor is None or project is None:
        return
    ensure_organization_scope(actor, getattr(project, "organization_id", ""), detail="Access denied for this project.")

def find_project_by_code(data: LogiTrackData, organization_id: str, project_code: str) -> Optional[Project]:
    target_org = str(organization_id or "").strip()
    target_code = str(project_code or "").strip().lower()
    if not target_org or not target_code:
        return None
    for project in data.projects:
        if project.organization_id == target_org and str(getattr(project, "project_code", "") or "").strip().lower() == target_code:
            return project
    return None

def slugify_project_code(value: str) -> str:
    base = "".join(ch.upper() if ch.isalnum() else "-" for ch in str(value or "")).strip("-")
    while "--" in base:
        base = base.replace("--", "-")
    return base[:48]

def generate_unique_project_code(data: LogiTrackData, organization_id: str, preferred: str) -> str:
    root = slugify_project_code(preferred) or slugify_project_code(new_id("project")) or "PROJECT"
    candidate = root
    index = 2
    while True:
        existing = find_project_by_code(data, organization_id, candidate)
        if existing is None:
            return candidate
        candidate = f"{root}-{index}"
        index += 1

def project_team_role_options() -> List[Dict[str, str]]:
    return [
        {"role_id": "programme_manager", "role_label": role_label("programme_manager")},
        {"role_id": "meal_officer", "role_label": role_label("meal_officer")},
        {"role_id": "field_coordinator", "role_label": role_label("field_coordinator")},
        {"role_id": "executive_viewer", "role_label": role_label("executive_viewer")},
    ]

def build_project_workspace_shell(project: Project, actor: Optional[UserAccount] = None) -> Dict[str, Any]:
    generated_at = now_iso_utc()
    return {
        "project_id": project.id,
        "organization_id": project.organization_id,
        "status": "published",
        "generated_at": generated_at,
        "generated_by_user_id": actor.id if actor else "",
        "generated_by_name": actor.full_name if actor else "",
        "containers": [
            {
                "key": key,
                "label": label,
                "status": "reserved",
                "ready": False,
                "created_at": generated_at,
            }
            for key, label in PROJECT_WORKSPACE_RESERVED_CONTAINERS
        ],
    }

def project_lifecycle_actions(status: str) -> List[str]:
    normalized = normalize_project_status(status, default="draft")
    actions = ["edit", "clone"]
    if normalized == "draft":
        actions.extend(["publish", "archive"])
    elif normalized == "published":
        actions.extend(["activate", "deactivate", "archive"])
    elif normalized == "active":
        actions.extend(["deactivate", "complete", "archive"])
    elif normalized == "paused":
        actions.extend(["activate", "complete", "archive"])
    elif normalized == "completed":
        actions.extend(["archive"])
    elif normalized == "archived":
        actions.extend(["restore", "clone"])
    return actions

def sanitize_project_team_assignment(data: LogiTrackData, assignment: ProjectTeamAssignment) -> Dict[str, Any]:
    user = find_user_by_id(data, assignment.user_id)
    team = find_team_by_id(data, assignment.team_id) if assignment.team_id else None
    return {
        "id": assignment.id,
        "project_id": assignment.project_id,
        "organization_id": assignment.organization_id,
        "user_id": assignment.user_id,
        "user_name": user.full_name if user else "",
        "email": user.email if user else "",
        "role": assignment.role,
        "role_label": role_label(assignment.role),
        "team_id": assignment.team_id,
        "team_name": team.team_name if team else "",
        "assigned_at": assignment.assigned_at,
        "assigned_by_user_id": assignment.assigned_by_user_id,
        "assigned_by_name": assignment.assigned_by_name,
        "status": assignment.status,
    }

def sanitize_project(data: LogiTrackData, project: Project) -> Dict[str, Any]:
    assignments = [sanitize_project_team_assignment(data, item) for item in getattr(project, "team_assignments", [])]
    assigned_user_ids = {item["user_id"] for item in assignments if item.get("user_id")}
    assigned_role_labels = [item["role_label"] for item in assignments if item.get("role_label")]
    return {
        "id": project.id,
        "project_id": project.id,
        "project_name": project.name,
        "project_code": getattr(project, "project_code", ""),
        "programme": getattr(project, "programme", ""),
        "donor": getattr(project, "donor", ""),
        "implementing_partner": getattr(project, "implementing_partner", ""),
        "sector": getattr(project, "sector", ""),
        "description": getattr(project, "description", "") or project.objective,
        "objective": project.objective,
        "country": getattr(project, "country", ""),
        "province_coverage": list(getattr(project, "province_coverage", []) or []),
        "district_coverage": list(getattr(project, "district_coverage", []) or []),
        "start_date": fmt_date(getattr(project, "start_date", None)) if getattr(project, "start_date", None) else "",
        "end_date": fmt_date(getattr(project, "end_date", None)) if getattr(project, "end_date", None) else "",
        "status": normalize_project_status(getattr(project, "status", "draft"), default="draft"),
        "created_by_user_id": getattr(project, "created_by_user_id", ""),
        "created_by_name": getattr(project, "created_by_name", ""),
        "created_at": getattr(project, "created_at", ""),
        "updated_at": getattr(project, "updated_at", ""),
        "published_at": getattr(project, "published_at", ""),
        "status_before_archive": getattr(project, "status_before_archive", ""),
        "organization_id": getattr(project, "organization_id", ""),
        "team_assignments": assignments,
        "assigned_users_total": len(assigned_user_ids),
        "assigned_roles": assigned_role_labels,
        "workspace_shell": getattr(project, "workspace_shell", {}) or {},
        "workspace_ready": bool((getattr(project, "workspace_shell", {}) or {}).get("containers")),
        "cloned_from_project_id": getattr(project, "cloned_from_project_id", ""),
        "available_actions": project_lifecycle_actions(getattr(project, "status", "draft")),
    }

def project_registry_summary(items: List[Project]) -> Dict[str, Any]:
    normalized = [normalize_project_status(getattr(project, "status", "draft"), default="draft") for project in items]
    return {
        "total": len(items),
        "draft": normalized.count("draft"),
        "published": normalized.count("published"),
        "active": normalized.count("active"),
        "paused": normalized.count("paused"),
        "completed": normalized.count("completed"),
        "archived": normalized.count("archived"),
    }

def eligible_project_team_users(data: LogiTrackData, organization_id: str) -> List[UserAccount]:
    allowed_roles = {item["role_id"] for item in project_team_role_options()}
    return [
        user
        for user in organization_users(data, organization_id)
        if user.status != "archived" and normalize_role(user.role) in allowed_roles
    ]

def find_organization_by_id(data: LogiTrackData, organization_id: str) -> Optional[OrganizationAccount]:
    target = str(organization_id or "").strip()
    if not target:
        return None
    for organization in data.organizations:
        if organization.id == target:
            return organization
    return None

def find_team_by_id(data: LogiTrackData, team_id: str) -> Optional[TeamAccount]:
    target = str(team_id or "").strip()
    if not target:
        return None
    for team in data.teams:
        if team.id == target:
            return team
    return None

def teams_for_organization(data: LogiTrackData, organization_id: str) -> List[TeamAccount]:
    target = str(organization_id or "").strip()
    if not target:
        return []
    return [team for team in data.teams if team.organization_id == target]

def organization_for_user(data: LogiTrackData, user: Optional[UserAccount]) -> Optional[OrganizationAccount]:
    if user is None:
        return None
    if user.organization_id:
        match = find_organization_by_id(data, user.organization_id)
        if match is not None:
            return match
    return data.organizations[0] if data.organizations else None

def build_user_session_payload(data: LogiTrackData, user: UserAccount) -> Dict[str, Any]:
    organization = organization_for_user(data, user)
    team = find_team_by_id(data, user.team_id)
    payload = sanitize_user(user)
    payload["organization"] = sanitize_organization(organization) if organization else None
    payload["organization_name"] = organization.organization_name if organization else ""
    payload["team"] = sanitize_team(data, team) if team else None
    payload["team_name"] = team.team_name if team else ""
    payload["role_label"] = role_label(user.role)
    payload["permissions"] = effective_permissions(user)
    payload["role_template_permissions"] = role_permissions(user.role)
    return payload

def find_user_by_username(data: LogiTrackData, username: str) -> Optional[UserAccount]:
    target = str(username or "").strip().lower()
    if not target:
        return None
    for user in data.users:
        if user.username.strip().lower() == target:
            return user
    return None

def find_user_by_id(data: LogiTrackData, user_id: str) -> Optional[UserAccount]:
    for user in data.users:
        if user.id == user_id:
            return user
    return None

def find_user_by_email(data: LogiTrackData, email: str) -> Optional[UserAccount]:
    target = str(email or "").strip().lower()
    if not target:
        return None
    for user in data.users:
        if user.email.strip().lower() == target:
            return user
    return None

def organization_users(data: LogiTrackData, organization_id: str) -> List[UserAccount]:
    target = str(organization_id or "").strip()
    if not target:
        return []
    return [user for user in data.users if user.organization_id == target]

def user_belongs_to_organization(user: Optional[UserAccount], organization_id: str) -> bool:
    if user is None:
        return False
    target = str(organization_id or "").strip()
    if not target:
        return False
    return str(user.organization_id or "").strip() == target

def ensure_organization_scope(actor: Optional[UserAccount], organization_id: str, detail: str = "Access denied for this organization.") -> None:
    if actor is None:
        return
    if actor.organization_id and actor.organization_id != str(organization_id or "").strip():
        raise HTTPException(status_code=403, detail=detail)

def ensure_user_scope(actor: Optional[UserAccount], user: Optional[UserAccount]) -> None:
    if actor is None or user is None:
        return
    ensure_organization_scope(actor, user.organization_id, detail="Access denied for this user.")

def ensure_team_scope(actor: Optional[UserAccount], team: Optional[TeamAccount]) -> None:
    if actor is None or team is None:
        return
    ensure_organization_scope(actor, team.organization_id, detail="Access denied for this team.")

def find_audit_actor(data: LogiTrackData, item: AuditEvent) -> Optional[UserAccount]:
    if item.actor_id:
        match = find_user_by_id(data, item.actor_id)
        if match is not None:
            return match
    if item.actor_username:
        return find_user_by_username(data, item.actor_username)
    return None

def build_team_account_from_payload(payload: Dict[str, Any], existing: Optional[TeamAccount] = None) -> TeamAccount:
    team_name = optional_text_field(payload, "team_name", existing.team_name if existing else "")
    if not team_name:
        raise ValueError("Missing required field: 'team_name'.")
    return TeamAccount(
        id=str(payload.get("id") or (existing.id if existing else new_id("team"))),
        organization_id=optional_text_field(payload, "organization_id", existing.organization_id if existing else ""),
        team_name=team_name,
        description=optional_text_field(payload, "description", existing.description if existing else ""),
        team_lead_user_id=optional_text_field(payload, "team_lead_user_id", existing.team_lead_user_id if existing else ""),
        status=optional_text_field(payload, "status", existing.status if existing else "active") or "active",
        created_at=(existing.created_at if existing and existing.created_at else now_iso_utc()),
        updated_at=now_iso_utc(),
    )

def upsert_team_account(data: LogiTrackData, team: TeamAccount) -> str:
    for idx, existing in enumerate(data.teams):
        if existing.id == team.id:
            data.teams[idx] = team
            return "updated"
    data.teams.append(team)
    return "created"

def assign_team_members(data: LogiTrackData, organization_id: str, team_id: str, member_user_ids: List[str]) -> None:
    target_users = {str(user_id).strip() for user_id in member_user_ids if str(user_id).strip()}
    for user in data.users:
        if user.organization_id != organization_id or user.status == "archived":
            continue
        if user.id in target_users:
            user.team_id = team_id
            user.updated_at = now_iso_utc()
        elif user.team_id == team_id:
            user.team_id = ""
            user.updated_at = now_iso_utc()

def find_user_by_token(data: LogiTrackData, token: str) -> Optional[UserAccount]:
    token_hash = hash_with_sha256(token)
    for user in data.users:
        if user.api_token_hash and secrets.compare_digest(user.api_token_hash, token_hash):
            return user
    return None

def append_audit_event(
    data: LogiTrackData,
    action: str,
    target_type: str = "",
    target_id: str = "",
    endpoint: str = "",
    actor: Optional[UserAccount] = None,
    outcome: str = "success",
    details: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    event = AuditEvent(
        id=new_id("audit"),
        occurred_at=now_iso_utc(),
        organization_id=getattr(actor, "organization_id", "") if actor else "",
        actor_id=actor.id if actor else "",
        actor_username=actor.username if actor else "",
        actor_role=actor.role if actor else "",
        action=action,
        target_type=target_type,
        target_id=target_id,
        endpoint=endpoint,
        outcome=outcome,
        details=details or {},
    )
    data.audit_events.append(event)
    if len(data.audit_events) > 5000:
        data.audit_events = data.audit_events[-5000:]
    return event

def build_dashboard_layout_from_visuals(visuals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    layout = []
    wide_charts = {"line_trend", "area_trend", "geo_map", "heatmap", "correlation_matrix", "sorted_table"}
    tall_charts = {"heatmap", "sorted_table", "treemap"}
    for idx, visual in enumerate(visuals):
        chart_type = str(visual.get("chart_type", "data_table"))
        visual_id = str(visual.get("id") or visual.get("visual_id") or f"visual_{idx + 1}")
        layout.append({
            "widget_id": visual_id,
            "visual_index": idx,
            "chart_type": chart_type,
            "title": str(visual.get("title") or chart_type.replace("_", " ").title()),
            "column_span": 2 if chart_type in wide_charts else 1,
            "row_span": 2 if chart_type in tall_charts else 1,
            "section": "main" if idx > 1 else "summary",
        })
    return layout

def sanitize_dashboard_layout(layout: Any, visuals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    default_layout = build_dashboard_layout_from_visuals(visuals)
    if not isinstance(layout, list):
        return default_layout

    def safe_span(value: Any, default: int = 1) -> int:
        try:
            return max(1, min(3, int(value or default)))
        except Exception:
            return default

    sanitized = []
    max_index = max(len(visuals) - 1, 0)
    for idx, item in enumerate(layout):
        if not isinstance(item, dict):
            continue
        visual_index_raw = item.get("visual_index", idx)
        try:
            visual_index = max(0, min(int(visual_index_raw), max_index))
        except Exception:
            visual_index = min(idx, max_index)
        visual = visuals[visual_index] if visuals else {}
        chart_type = str(item.get("chart_type") or visual.get("chart_type") or "data_table")
        sanitized.append({
            "widget_id": str(item.get("widget_id") or visual.get("id") or f"visual_{visual_index + 1}"),
            "visual_index": visual_index,
            "chart_type": chart_type,
            "title": str(item.get("title") or visual.get("title") or chart_type.replace("_", " ").title()),
            "column_span": safe_span(item.get("column_span", 1), default=1),
            "row_span": safe_span(item.get("row_span", 1), default=1),
            "section": str(item.get("section") or ("main" if visual_index > 1 else "summary")),
        })

    return sanitized or default_layout

def build_user_account_from_payload(payload: Dict[str, Any], existing: Optional[UserAccount] = None) -> UserAccount:
    username = derive_username(payload, existing=existing)
    password = payload.get("password")
    if existing is None and (password is None or str(password) == ""):
        raise ValueError("Missing required field: 'password'.")

    salt = existing.password_salt if existing else ""
    password_hash = existing.password_hash if existing else ""
    if password not in (None, ""):
        salt, password_hash = build_password_hash(str(password))

    is_active_raw = payload.get("is_active", existing.is_active if existing else True)
    if isinstance(is_active_raw, str):
        is_active = is_active_raw.strip().lower() not in {"0", "false", "no"}
    else:
        is_active = bool(is_active_raw)

    return UserAccount(
        id=str(payload.get("id") or (existing.id if existing else new_id("user"))),
        username=username,
        organization_id=optional_text_field(payload, "organization_id", existing.organization_id if existing else ""),
        team_id=optional_text_field(payload, "team_id", existing.team_id if existing else ""),
        full_name=optional_text_field(payload, "full_name", existing.full_name if existing else ""),
        email=optional_text_field(payload, "email", existing.email if existing else ""),
        role=normalize_role(optional_text_field(payload, "role", existing.role if existing else "executive_viewer")),
        status=optional_text_field(payload, "status", existing.status if existing else ("active" if is_active else "inactive")) or ("active" if is_active else "inactive"),
        permissions=normalize_permission_ids(payload.get("permissions", existing.permissions if existing else [])),
        password_salt=salt,
        password_hash=password_hash,
        api_token_hash=existing.api_token_hash if existing else "",
        is_active=is_active,
        created_at=(existing.created_at if existing and existing.created_at else now_iso_utc()),
        updated_at=now_iso_utc(),
        last_login_at=existing.last_login_at if existing else "",
    )

def upsert_user_account(data: LogiTrackData, user: UserAccount) -> str:
    for idx, existing in enumerate(data.users):
        if existing.id == user.id:
            data.users[idx] = user
            return "updated"
    data.users.append(user)
    return "created"

def normalize_column_name(name: str) -> str:
    return str(name or "").strip().lower().replace(" ", "_")

def looks_like_identifier(name: str) -> bool:
    tokens = ("id", "code", "ref", "reference", "uuid")
    normalized = normalize_column_name(name)
    return any(token in normalized for token in tokens)

def normalize_datetime_utc(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, datetime.min.time()).replace(tzinfo=timezone.utc)
    else:
        text = str(value).strip()
        if not text:
            return None

        parsed = None
        candidates = [
            text,
            text.replace("Z", "+00:00"),
        ]
        for candidate in candidates:
            try:
                parsed = datetime.fromisoformat(candidate)
                break
            except Exception:
                pass

        if parsed is None:
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m", "%Y/%m"):
                try:
                    parsed = datetime.strptime(text, fmt)
                    break
                except Exception:
                    pass
        if parsed is None:
            return None

    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def parse_date_like_value(value: Any) -> Optional[datetime]:
    return normalize_datetime_utc(value)

def normalize_utc_datetime(value: Any) -> Optional[datetime]:
    return normalize_datetime_utc(value)

def scalar_type_of(value: Any) -> str:
    if value is None:
        return "empty"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"

    text = str(value).strip()
    if text == "":
        return "empty"
    if text.lower() in {"true", "false", "yes", "no", "y", "n", "sim", "nao", "não"}:
        return "boolean"
    if parse_date_like_value(text) is not None:
        return "date"
    if num(text) is not None:
        return "number"
    return "text"

def clean_row_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in row.items():
        col = str(key or "").strip()
        if not col:
            continue
        cleaned[col] = value.strip() if isinstance(value, str) else value
    return cleaned

def normalize_rows_payload(rows_payload: Any) -> List[Dict[str, Any]]:
    if not isinstance(rows_payload, list):
        raise ValueError("'rows' must be a list of JSON objects.")

    rows: List[Dict[str, Any]] = []
    for row in rows_payload:
        if not isinstance(row, dict):
            raise ValueError("Each row in 'rows' must be a JSON object.")
        cleaned = clean_row_dict(row)
        if cleaned:
            rows.append(cleaned)
    return rows

def rows_from_csv_text(csv_text: str) -> List[Dict[str, Any]]:
    content = (csv_text or "").strip()
    if not content:
        raise ValueError("CSV text is empty.")

    reader = csv.DictReader(StringIO(content.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise ValueError("CSV text must include a header row.")

    rows: List[Dict[str, Any]] = []
    for row in reader:
        cleaned = clean_row_dict(row)
        if cleaned and any(str(value).strip() != "" for value in cleaned.values()):
            rows.append(cleaned)
    return rows

def tidy_dataset_columns(rows: List[Dict[str, Any]]) -> List[str]:
    columns: List[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                columns.append(key)
    return columns

def find_tidy_dataset(data: LogiTrackData, dataset_id: str) -> Optional[TidyDataset]:
    for dataset in data.tidy_datasets:
        if dataset.id == dataset_id:
            return dataset
    return None

def infer_column_profile(rows: List[Dict[str, Any]], column_name: str) -> Dict[str, Any]:
    values = [row.get(column_name) for row in rows]
    non_empty = [value for value in values if value not in (None, "")]
    type_counts = {"number": 0, "date": 0, "boolean": 0, "text": 0}
    unique_values = set()

    for value in non_empty:
        scalar_type = scalar_type_of(value)
        if scalar_type in type_counts:
            type_counts[scalar_type] += 1
        unique_values.add(str(value).strip())

    non_empty_count = len(non_empty)
    numeric_ratio = (type_counts["number"] / non_empty_count) if non_empty_count else 0.0
    date_ratio = (type_counts["date"] / non_empty_count) if non_empty_count else 0.0
    bool_ratio = (type_counts["boolean"] / non_empty_count) if non_empty_count else 0.0

    normalized = normalize_column_name(column_name)
    is_latitude = normalized in {"lat", "latitude"}
    is_longitude = normalized in {"lon", "lng", "longitude"}
    has_time_keyword = any(token in normalized for token in ("date", "month", "year", "period", "quarter", "week"))
    has_status_keyword = any(token in normalized for token in ("status", "state", "risk"))
    has_geo_keyword = any(token in normalized for token in ("country", "province", "district", "region", "location", "site", "area"))
    has_owner_keyword = any(token in normalized for token in ("owner", "manager", "assignee", "team"))
    has_target_keyword = "target" in normalized or "meta" in normalized
    has_actual_keyword = any(token in normalized for token in ("actual", "value", "result", "achieved"))
    has_budget_keyword = any(token in normalized for token in ("budget", "cost", "amount", "expense"))
    has_progress_keyword = any(token in normalized for token in ("progress", "rate", "score", "pct", "percent"))

    role = "dimension"
    semantic = "text"
    aggregation = "count"

    if is_latitude:
        role = "latitude"
        semantic = "geo"
        aggregation = "none"
    elif is_longitude:
        role = "longitude"
        semantic = "geo"
        aggregation = "none"
    elif has_status_keyword:
        role = "status"
        semantic = "status"
        aggregation = "count"
    elif has_time_keyword or date_ratio >= 0.6:
        role = "time"
        semantic = "date"
        aggregation = "none"
    elif numeric_ratio >= 0.8 and not looks_like_identifier(column_name):
        role = "measure"
        semantic = "number"
        if has_progress_keyword or "%" in normalized or "percent" in normalized:
            aggregation = "avg"
        elif has_target_keyword or has_actual_keyword or has_budget_keyword:
            aggregation = "sum"
        else:
            aggregation = "sum"
    elif bool_ratio >= 0.8:
        role = "flag"
        semantic = "boolean"
        aggregation = "count_true"
    elif has_geo_keyword:
        role = "geo_dimension"
        semantic = "geo"
        aggregation = "count"
    elif has_owner_keyword:
        role = "owner"
        semantic = "text"
        aggregation = "count"
    elif looks_like_identifier(column_name):
        role = "identifier"
        semantic = "text"
        aggregation = "count"

    return {
        "name": column_name,
        "normalized_name": normalized,
        "role": role,
        "semantic_type": semantic,
        "aggregation": aggregation,
        "non_empty_count": non_empty_count,
        "empty_count": len(values) - non_empty_count,
        "unique_count": len(unique_values),
        "numeric_ratio": round(numeric_ratio, 3),
        "date_ratio": round(date_ratio, 3),
        "boolean_ratio": round(bool_ratio, 3),
        "sample_values": [str(value) for value in non_empty[:5]],
        "has_target_keyword": has_target_keyword,
        "has_actual_keyword": has_actual_keyword,
        "has_budget_keyword": has_budget_keyword,
        "has_progress_keyword": has_progress_keyword,
    }

def classify_dashboard_type(column_profiles: List[Dict[str, Any]]) -> str:
    normalized_names = {profile["normalized_name"] for profile in column_profiles}
    roles = [profile["role"] for profile in column_profiles]
    has_project = any(token in name for name in normalized_names for token in ("project", "program", "initiative"))
    has_indicator = any(token in name for name in normalized_names for token in ("indicator", "kpi", "metric"))
    has_due = any(token in name for name in normalized_names for token in ("due", "deadline"))

    if has_project and has_indicator:
        return "project_performance"
    if "latitude" in roles and "longitude" in roles:
        return "geospatial_monitoring"
    if "status" in roles and has_due:
        return "operations_management"
    return "general_analytics"

def build_dataset_schema(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    columns = tidy_dataset_columns(rows)
    column_profiles = [infer_column_profile(rows, column_name) for column_name in columns]

    return {
        "row_count": len(rows),
        "column_count": len(columns),
        "columns": column_profiles,
        "roles": {
            "time": [profile["name"] for profile in column_profiles if profile["role"] == "time"],
            "measures": [profile["name"] for profile in column_profiles if profile["role"] == "measure"],
            "status": [profile["name"] for profile in column_profiles if profile["role"] == "status"],
            "dimensions": [profile["name"] for profile in column_profiles if profile["role"] in {"dimension", "geo_dimension", "owner"}],
            "latitude": [profile["name"] for profile in column_profiles if profile["role"] == "latitude"],
            "longitude": [profile["name"] for profile in column_profiles if profile["role"] == "longitude"],
        },
        "dashboard_type": classify_dashboard_type(column_profiles),
    }

def choose_best_dimension(column_profiles: List[Dict[str, Any]]) -> Optional[str]:
    candidates = [
        profile for profile in column_profiles
        if profile["role"] in {"dimension", "geo_dimension", "owner", "status"}
        and profile["unique_count"] > 1
        and profile["unique_count"] <= 50
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda profile: (profile["unique_count"], profile["name"]))
    return candidates[0]["name"]

def choose_top_measures(column_profiles: List[Dict[str, Any]], limit: int = 4) -> List[str]:
    candidates = [profile for profile in column_profiles if profile["role"] == "measure"]
    candidates.sort(
        key=lambda profile: (
            0 if profile["has_progress_keyword"] else 1,
            0 if profile["has_actual_keyword"] else 1,
            0 if profile["has_target_keyword"] else 1,
            profile["name"],
        )
    )
    return [profile["name"] for profile in candidates[:limit]]

def choose_top_dimensions(column_profiles: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    candidates = [
        profile for profile in column_profiles
        if profile["role"] in {"dimension", "geo_dimension", "owner", "status"}
        and profile["unique_count"] > 1
        and profile["unique_count"] <= 60
    ]
    candidates.sort(key=lambda profile: (profile["unique_count"], profile["name"]))
    return [profile["name"] for profile in candidates[:limit]]

def add_visual(
    visuals: List[Dict[str, Any]],
    seen_chart_types: set,
    chart_type: str,
    payload: Dict[str, Any],
) -> None:
    if chart_type in seen_chart_types:
        return
    visuals.append({"chart_type": chart_type, **payload})
    seen_chart_types.add(chart_type)

def find_profile_by_keyword(column_profiles: List[Dict[str, Any]], keywords: Tuple[str, ...], role: Optional[str] = None) -> Optional[Dict[str, Any]]:
    for profile in column_profiles:
        if role is not None and profile["role"] != role:
            continue
        if any(keyword in profile["normalized_name"] for keyword in keywords):
            return profile
    return None

def build_visual_suggestions_from_schema(schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    column_profiles = schema["columns"]
    measures = choose_top_measures(column_profiles)
    dimensions = choose_top_dimensions(column_profiles)
    time_col = schema["roles"]["time"][0] if schema["roles"]["time"] else None
    status_col = schema["roles"]["status"][0] if schema["roles"]["status"] else None
    best_dimension = choose_best_dimension(column_profiles)
    latitude_col = schema["roles"]["latitude"][0] if schema["roles"]["latitude"] else None
    longitude_col = schema["roles"]["longitude"][0] if schema["roles"]["longitude"] else None
    row_count = int(schema.get("row_count") or 0)

    visuals: List[Dict[str, Any]] = []
    seen_chart_types = set()

    if measures:
        add_visual(visuals, seen_chart_types, "kpi_cards", {
            "title": "Executive KPI cards",
            "measures": measures,
            "confidence": 0.95,
            "reason": "The dataset contains numeric measures suitable for headline cards.",
        })

    if time_col and measures:
        add_visual(visuals, seen_chart_types, "line_trend", {
            "title": f"Trend over {time_col}",
            "x": time_col,
            "y": measures[:2],
            "confidence": 0.92,
            "reason": "A time column plus measures supports trend analysis.",
        })
        if len(measures) >= 1:
            add_visual(visuals, seen_chart_types, "area_trend", {
                "title": f"Cumulative pattern over {time_col}",
                "x": time_col,
                "y": [measures[0]],
                "confidence": 0.82,
                "reason": "Area charts help show volume or cumulative change over time.",
            })

    if best_dimension and measures:
        add_visual(visuals, seen_chart_types, "bar_comparison", {
            "title": f"Compare {measures[0]} by {best_dimension}",
            "dimension": best_dimension,
            "measure": measures[0],
            "confidence": 0.89,
            "reason": "A categorical dimension and numeric measure are ideal for comparison bars.",
        })
        add_visual(visuals, seen_chart_types, "sorted_table", {
            "title": f"Ranked table of {measures[0]} by {best_dimension}",
            "dimension": best_dimension,
            "measure": measures[0],
            "confidence": 0.78,
            "reason": "A ranked table complements charts for exact values and drill-down.",
        })

    if status_col:
        add_visual(visuals, seen_chart_types, "status_donut", {
            "title": f"Status distribution by {status_col}",
            "dimension": status_col,
            "measure": "row_count",
            "confidence": 0.87,
            "reason": "A status field supports quick operational distribution views.",
        })
        if best_dimension and best_dimension != status_col:
            add_visual(visuals, seen_chart_types, "stacked_bar", {
                "title": f"Status composition by {best_dimension}",
                "dimension": best_dimension,
                "stack": status_col,
                "measure": "row_count",
                "confidence": 0.84,
                "reason": "Stacked bars help compare category composition across statuses.",
            })

    if latitude_col and longitude_col and measures:
        add_visual(visuals, seen_chart_types, "geo_map", {
            "title": "Map view of performance",
            "latitude": latitude_col,
            "longitude": longitude_col,
            "measure": measures[0],
            "confidence": 0.91,
            "reason": "Latitude and longitude columns enable a geographic monitoring dashboard.",
        })

    actual_profile = find_profile_by_keyword(column_profiles, ("actual", "achieved", "result"), role="measure")
    target_profile = find_profile_by_keyword(column_profiles, ("target", "meta"), role="measure")
    if actual_profile and target_profile:
        add_visual(visuals, seen_chart_types, "bullet_or_gauge", {
            "title": f"Actual vs target: {actual_profile['name']} against {target_profile['name']}",
            "actual_measure": actual_profile["name"],
            "target_measure": target_profile["name"],
            "confidence": 0.94,
            "reason": "Actual and target fields support KPI attainment visuals.",
        })
        if best_dimension:
            add_visual(visuals, seen_chart_types, "variance_bar", {
                "title": f"Variance to target by {best_dimension}",
                "dimension": best_dimension,
                "actual_measure": actual_profile["name"],
                "target_measure": target_profile["name"],
                "confidence": 0.88,
                "reason": "Variance bars make underperformance and overperformance easy to scan.",
            })

    if measures and row_count >= 20:
        add_visual(visuals, seen_chart_types, "histogram", {
            "title": f"Distribution of {measures[0]}",
            "measure": measures[0],
            "confidence": 0.83,
            "reason": "Histograms are useful when a numeric field has enough observations to show distribution.",
        })

    if measures and best_dimension:
        add_visual(visuals, seen_chart_types, "box_plot", {
            "title": f"Spread of {measures[0]} by {best_dimension}",
            "dimension": best_dimension,
            "measure": measures[0],
            "confidence": 0.82,
            "reason": "Box plots are strong when you want to compare spread, median, and outliers across groups.",
        })

    if len(measures) >= 2 and row_count >= 15:
        add_visual(visuals, seen_chart_types, "scatter_plot", {
            "title": f"Relationship between {measures[0]} and {measures[1]}",
            "x": measures[0],
            "y": measures[1],
            "confidence": 0.86,
            "reason": "Two numeric measures are good candidates for correlation or clustering analysis.",
        })
        if len(measures) >= 3:
            add_visual(visuals, seen_chart_types, "bubble_chart", {
                "title": f"Multimetric relationship: {measures[0]}, {measures[1]}, and {measures[2]}",
                "x": measures[0],
                "y": measures[1],
                "size": measures[2],
                "confidence": 0.8,
                "reason": "Bubble charts help compare three numeric measures at once.",
            })

    if len(dimensions) >= 2 and measures:
        add_visual(visuals, seen_chart_types, "heatmap", {
            "title": f"Heatmap of {measures[0]} across {dimensions[0]} and {dimensions[1]}",
            "x": dimensions[0],
            "y": dimensions[1],
            "measure": measures[0],
            "confidence": 0.81,
            "reason": "Two dimensions plus a measure can reveal concentration patterns in a heatmap.",
        })

    if best_dimension and measures and row_count >= 10:
        add_visual(visuals, seen_chart_types, "treemap", {
            "title": f"Proportional contribution of {best_dimension}",
            "dimension": best_dimension,
            "measure": measures[0],
            "confidence": 0.76,
            "reason": "Treemaps are useful for proportional contribution across many categories.",
        })

    if len(measures) >= 3:
        add_visual(visuals, seen_chart_types, "correlation_matrix", {
            "title": "Correlation view of numeric measures",
            "measures": measures,
            "confidence": 0.74,
            "reason": "Several numeric columns support correlation analysis and multivariate exploration.",
        })

    if not visuals:
        add_visual(visuals, seen_chart_types, "data_table", {
            "title": "Detailed data explorer",
            "confidence": 0.7,
            "reason": "The dataset is better explored as a table before charting.",
        })

    return visuals

def build_dashboard_recommendation_for_rows(rows: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
    schema = build_dataset_schema(rows)
    column_profiles = schema["columns"]
    recommended_filters = []
    visuals = build_visual_suggestions_from_schema(schema)

    for profile in column_profiles:
        if profile["role"] in {"dimension", "geo_dimension", "owner", "status", "time"} and profile["unique_count"] > 1:
            recommended_filters.append(profile["name"])

    return {
        "dataset_name": dataset_name,
        "dashboard_type": schema["dashboard_type"],
        "summary": f"{dataset_name} has {schema['row_count']} rows and {schema['column_count']} columns.",
        "recommended_filters": recommended_filters[:6],
        "recommended_visuals": visuals,
        "visualization_scope": sorted({item["chart_type"] for item in visuals}),
        "schema": schema,
    }

def build_tidy_dataset_from_payload(payload: Dict[str, Any], existing: Optional[TidyDataset] = None) -> TidyDataset:
    name = require_text_field(payload, "name")
    description = optional_text_field(payload, "description")
    rows_payload = payload.get("rows")
    csv_text = payload.get("csv_text")

    if rows_payload is None and csv_text is None:
        raise ValueError("Provide either 'rows' or 'csv_text' to import a tidy dataset.")
    if rows_payload is not None and csv_text is not None:
        raise ValueError("Provide only one of 'rows' or 'csv_text', not both.")

    rows = normalize_rows_payload(rows_payload) if rows_payload is not None else rows_from_csv_text(str(csv_text))
    if not rows:
        raise ValueError("The tidy dataset has no data rows.")

    dataset_id = str(payload.get("id") or (existing.id if existing else new_id("tidy")))
    source_type = "rows" if rows_payload is not None else "csv_text"
    created_at = existing.created_at if existing and existing.created_at else now_iso_utc()

    return TidyDataset(
        id=dataset_id,
        name=name,
        description=description,
        source_type=source_type,
        created_at=created_at,
        updated_at=now_iso_utc(),
        rows=rows,
    )

def upsert_tidy_dataset(data: LogiTrackData, dataset: TidyDataset) -> str:
    for idx, existing in enumerate(data.tidy_datasets):
        if existing.id == dataset.id:
            data.tidy_datasets[idx] = dataset
            return "updated"
    data.tidy_datasets.append(dataset)
    return "created"

def find_semantic_mapping(data: LogiTrackData, dataset_id: str) -> Optional[SemanticMapping]:
    candidates = [item for item in data.semantic_mappings if item.dataset_id == dataset_id]
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item.status == "confirmed", item.updated_at or ""))

def build_semantic_mapping_suggestion(dataset: TidyDataset) -> SemanticMapping:
    base_mapping = infer_reporting_history_mapping(dataset.rows)
    fields = dict(base_mapping.get("mappings", {}))
    schema = base_mapping.get("schema", {})
    column_profiles = schema.get("columns", [])

    extra_candidates = {
        "gender": ("gender", "sex"),
        "age_group": ("age", "youth", "adult"),
        "beneficiary_group": ("beneficiary", "group", "cohort"),
        "partner": ("partner", "implementer", "organization"),
        "site": ("site", "facility", "school", "hospital"),
        "latitude": ("lat", "latitude"),
        "longitude": ("lon", "lng", "longitude"),
    }
    for field_name, keywords in extra_candidates.items():
        profile = find_profile_by_keyword(column_profiles, keywords)
        if profile is not None:
            fields[field_name] = profile["name"]

    status = "suggested"
    confidence = float(base_mapping.get("confidence", 0.0) or 0.0)
    return SemanticMapping(
        id=new_id("map"),
        dataset_id=dataset.id,
        name=f"{dataset.name} mapping",
        fields={k: v for k, v in fields.items() if v},
        status=status,
        confidence=confidence,
        notes=base_mapping.get("reason", ""),
        created_at=now_iso_utc(),
        updated_at=now_iso_utc(),
    )

def build_semantic_mapping_from_payload(payload: Dict[str, Any], dataset_id: str, existing: Optional[SemanticMapping] = None) -> SemanticMapping:
    fields_payload = payload.get("fields", {})
    if not isinstance(fields_payload, dict):
        raise ValueError("'fields' must be a JSON object.")

    fields = {str(key): str(value) for key, value in fields_payload.items() if str(value).strip()}
    return SemanticMapping(
        id=str(payload.get("id") or (existing.id if existing else new_id("map"))),
        dataset_id=dataset_id,
        name=optional_text_field(payload, "name", existing.name if existing else f"dataset-{dataset_id}-mapping"),
        fields=fields,
        status=optional_text_field(payload, "status", "confirmed") or "confirmed",
        confidence=float(payload.get("confidence", existing.confidence if existing else 1.0) or 0.0),
        notes=optional_text_field(payload, "notes", existing.notes if existing else ""),
        created_at=(existing.created_at if existing and existing.created_at else now_iso_utc()),
        updated_at=now_iso_utc(),
    )

def upsert_semantic_mapping(data: LogiTrackData, mapping: SemanticMapping) -> str:
    for idx, existing in enumerate(data.semantic_mappings):
        if existing.id == mapping.id or (existing.dataset_id == mapping.dataset_id and existing.name == mapping.name):
            data.semantic_mappings[idx] = mapping
            return "updated"
    data.semantic_mappings.append(mapping)
    return "created"

def effective_semantic_mapping(data: LogiTrackData, dataset: TidyDataset) -> SemanticMapping:
    existing = find_semantic_mapping(data, dataset.id)
    if existing is not None:
        suggestion = build_semantic_mapping_suggestion(dataset)
        merged_fields = dict(suggestion.fields)
        merged_fields.update(existing.fields)
        existing.fields = merged_fields
        return existing
    return build_semantic_mapping_suggestion(dataset)

def safe_sorted_numeric(values: List[Any]) -> List[float]:
    nums = [float(v) for v in values if v is not None]
    nums.sort()
    return nums

def percentile(values: List[float], q: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    idx = (len(values) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(values) - 1)
    frac = idx - lo
    return values[lo] * (1 - frac) + values[hi] * frac

def build_tidy_dataset_quality_report(data: LogiTrackData, dataset: TidyDataset) -> Dict[str, Any]:
    rows = dataset.rows
    schema = build_dataset_schema(rows)
    mapping = effective_semantic_mapping(data, dataset)
    row_count = len(rows)
    columns = tidy_dataset_columns(rows)
    cell_total = row_count * len(columns) if row_count and columns else 0
    missing_cells = 0
    empty_columns = []
    duplicate_rows = 0
    issues: List[Dict[str, Any]] = []
    completeness_by_column = []

    seen_rows = {}
    for row in rows:
        row_key = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
        seen_rows[row_key] = seen_rows.get(row_key, 0) + 1
    duplicate_rows = sum(count - 1 for count in seen_rows.values() if count > 1)

    for column in columns:
        non_empty = sum(1 for row in rows if row.get(column) not in (None, ""))
        empty = row_count - non_empty
        missing_cells += empty
        if non_empty == 0:
            empty_columns.append(column)
        completeness_by_column.append({
            "column": column,
            "non_empty_count": non_empty,
            "missing_count": empty,
            "completeness_pct": round((non_empty / row_count) * 100, 2) if row_count else None,
        })

    data_freshness_days = None
    time_field = mapping.fields.get("reporting_period")
    invalid_time_rows = 0
    if time_field:
        parsed_dates = []
        for row in rows:
            value = row.get(time_field)
            if value in (None, ""):
                continue
            parsed = normalize_utc_datetime(value)
            if parsed is None:
                invalid_time_rows += 1
            else:
                parsed_dates.append(parsed)
        if parsed_dates:
            latest = max(parsed_dates)
            data_freshness_days = (utc_now() - latest).days

    measure_outliers = []
    for measure in choose_top_measures(schema["columns"], limit=6):
        values = safe_sorted_numeric([num(row.get(measure)) for row in rows])
        if len(values) < 5:
            continue
        q1 = percentile(values, 0.25)
        q3 = percentile(values, 0.75)
        if q1 is None or q3 is None:
            continue
        iqr = q3 - q1
        low = q1 - (1.5 * iqr)
        high = q3 + (1.5 * iqr)
        outlier_count = sum(1 for value in values if value < low or value > high)
        if outlier_count > 0:
            measure_outliers.append({
                "measure": measure,
                "outlier_count": outlier_count,
                "lower_bound": round(low, 3),
                "upper_bound": round(high, 3),
            })

    completeness_score = 100.0 if cell_total == 0 else max(0.0, 100.0 - ((missing_cells / cell_total) * 100.0))
    duplicates_score = 100.0 if row_count == 0 else max(0.0, 100.0 - ((duplicate_rows / max(row_count, 1)) * 100.0))
    freshness_score = 100.0
    if data_freshness_days is not None:
        freshness_score = max(0.0, 100.0 - max(0, data_freshness_days - 30))
    validity_penalty = min(100.0, (invalid_time_rows * 5.0) + sum(item["outlier_count"] for item in measure_outliers) * 2.0 + len(empty_columns) * 5.0)
    validity_score = max(0.0, 100.0 - validity_penalty)
    overall_score = round((completeness_score + duplicates_score + freshness_score + validity_score) / 4.0, 2)

    if duplicate_rows > 0:
        issues.append({"severity": "medium", "type": "duplicates", "message": f"{duplicate_rows} duplicate row(s) detected."})
    if empty_columns:
        issues.append({"severity": "low", "type": "empty_columns", "message": f"Empty columns: {', '.join(empty_columns[:10])}"})
    if invalid_time_rows > 0:
        issues.append({"severity": "medium", "type": "invalid_dates", "message": f"{invalid_time_rows} row(s) have invalid reporting period values."})
    if data_freshness_days is not None and data_freshness_days > 30:
        issues.append({"severity": "medium", "type": "stale_data", "message": f"The latest reporting period is {data_freshness_days} days old."})
    for item in measure_outliers[:3]:
        issues.append({"severity": "low", "type": "outliers", "message": f"{item['measure']} has {item['outlier_count']} possible outlier(s)."})

    return {
        "dataset_id": dataset.id,
        "row_count": row_count,
        "column_count": len(columns),
        "overall_score": overall_score,
        "scores": {
            "completeness": round(completeness_score, 2),
            "duplicates": round(duplicates_score, 2),
            "freshness": round(freshness_score, 2),
            "validity": round(validity_score, 2),
        },
        "data_freshness_days": data_freshness_days,
        "duplicate_rows": duplicate_rows,
        "invalid_time_rows": invalid_time_rows,
        "empty_columns": empty_columns,
        "measure_outliers": measure_outliers,
        "issues": issues,
        "column_completeness": completeness_by_column,
        "mapping": {
            "status": mapping.status,
            "confidence": mapping.confidence,
            "fields": mapping.fields,
        },
    }

def build_dataset_narrative_summary(data: LogiTrackData, dataset: TidyDataset) -> Dict[str, Any]:
    recommendation = build_dashboard_recommendation_for_rows(dataset.rows, dataset.name)
    quality = build_tidy_dataset_quality_report(data, dataset)
    notifications = build_tidy_dataset_notifications(dataset)
    top_visuals = [item["chart_type"] for item in recommendation["recommended_visuals"][:4]]

    summary = f"{dataset.name} contains {len(dataset.rows)} rows. The recommended dashboard type is {recommendation['dashboard_type']}."
    insights = [
        f"Overall data quality score: {quality['overall_score']}.",
        f"Suggested visuals: {', '.join(top_visuals) if top_visuals else 'data_table'}.",
    ]
    if quality["data_freshness_days"] is not None:
        insights.append(f"Latest reporting data is {quality['data_freshness_days']} day(s) old.")
    if notifications:
        insights.append(f"{len(notifications)} dataset-specific notification(s) were generated.")
    if quality["issues"]:
        insights.append(f"Most urgent quality issue: {quality['issues'][0]['message']}")

    return {
        "dataset_id": dataset.id,
        "summary": summary,
        "insights": insights,
        "quality": quality,
        "recommendation": recommendation,
    }

def build_project_narrative_summary(data: LogiTrackData, project_id: str) -> Dict[str, Any]:
    project = find_project(data, project_id)
    if project is None:
        raise ValueError(f"Project '{project_id}' not found.")
    project_trend = build_project_trend_series(data, project_id)
    notifications = [
        item for item in build_current_notifications(data)
        if item.get("context", {}).get("project_id") == project_id or item.get("source_id") == project_id
    ]
    latest = project_trend[-1] if project_trend else {}
    summary = f"{project.name} is being tracked across {len(project.indicators)} indicator(s)."
    insights = []
    if latest.get("progress_weighted_pct") is not None:
        insights.append(f"Latest weighted progress is {latest['progress_weighted_pct']}% for period {latest['reporting_period']}.")
    if len(project_trend) >= 2:
        prev = project_trend[-2].get("progress_weighted_pct")
        curr = project_trend[-1].get("progress_weighted_pct")
        if prev is not None and curr is not None:
            delta = round(float(curr) - float(prev), 2)
            direction = "improved" if delta >= 0 else "declined"
            insights.append(f"Progress has {direction} by {abs(delta)} percentage points versus the previous period.")
    if notifications:
        insights.append(f"There are {len(notifications)} active notification(s) for this project.")

    return {
        "project_id": project.id,
        "project_name": project.name,
        "summary": summary,
        "insights": insights,
        "trend": project_trend,
        "notifications": notifications[:10],
    }

def build_portfolio_narrative_summary(data: LogiTrackData) -> Dict[str, Any]:
    trend = build_portfolio_trend_series(data)
    notifications = build_current_notifications(data)
    summary = f"The portfolio currently covers {len(data.projects)} project(s), {len(data.reporting_records)} reporting records, and {len(data.tidy_datasets)} tidy dataset(s)."
    insights = []
    if trend:
        latest = trend[-1]
        if latest.get("progress_weighted_pct") is not None:
            insights.append(f"The latest portfolio weighted progress is {latest['progress_weighted_pct']}% in {latest['reporting_period']}.")
    if notifications:
        high_count = sum(1 for item in notifications if item.get("severity") in {"critical", "high"})
        insights.append(f"There are {high_count} high-priority portfolio notifications.")
    return {
        "summary": summary,
        "insights": insights,
        "trend": trend[-12:],
        "notifications": notifications[:10],
    }

def find_dashboard_template(data: LogiTrackData, template_id: str) -> Optional[DashboardTemplate]:
    for template in data.dashboard_templates:
        if template.id == template_id:
            return template
    return None

def build_builtin_dashboard_templates(dataset: TidyDataset, recommendation: Dict[str, Any]) -> List[DashboardTemplate]:
    filters = recommendation.get("recommended_filters", [])[:6]
    visuals = recommendation.get("recommended_visuals", [])
    dashboard_type = recommendation.get("dashboard_type", "general_analytics")
    now = now_iso_utc()

    def template(template_id: str, name: str, description: str, chart_types: Tuple[str, ...], narrative_sections: List[str]) -> DashboardTemplate:
        selected = [item for item in visuals if item.get("chart_type") in chart_types]
        if not selected:
            selected = visuals[:4]
        return DashboardTemplate(
            id=template_id,
            name=name,
            description=description,
            dashboard_type=dashboard_type,
            scope="builtin",
            filters=filters,
            visuals=selected,
            layout=build_dashboard_layout_from_visuals(selected),
            narrative_sections=narrative_sections,
            theme="studio_default",
            created_at=now,
            updated_at=now,
        )

    templates = [
        template("builtin_executive", "Executive Dashboard", "High-level KPIs and management alerts.", ("kpi_cards", "line_trend", "bar_comparison", "status_donut", "bullet_or_gauge"), ["summary", "risks", "actions"]),
        template("builtin_me", "M&E Dashboard", "Indicator tracking, targets, and trend analysis.", ("line_trend", "variance_bar", "bullet_or_gauge", "heatmap", "box_plot"), ["progress", "data_quality", "next_steps"]),
        template("builtin_ops", "Operations Dashboard", "Tasks, statuses, and operational bottlenecks.", ("status_donut", "stacked_bar", "bar_comparison", "sorted_table"), ["delivery", "bottlenecks", "follow_up"]),
        template("builtin_geo", "Geographic Dashboard", "Spatial view of performance across locations.", ("geo_map", "heatmap", "treemap", "bar_comparison"), ["geography", "coverage", "gaps"]),
        template("builtin_budget", "Budget vs Results Dashboard", "Financial effort against achieved results.", ("bubble_chart", "scatter_plot", "variance_bar", "line_trend"), ["budget", "value_for_money", "exceptions"]),
    ]
    return templates

def build_dashboard_template_from_payload(payload: Dict[str, Any], existing: Optional[DashboardTemplate] = None) -> DashboardTemplate:
    visuals = payload.get("visuals", existing.visuals if existing else [])
    layout = payload.get("layout", existing.layout if existing else [])
    filters = payload.get("filters", existing.filters if existing else [])
    narrative_sections = payload.get("narrative_sections", existing.narrative_sections if existing else [])
    if not isinstance(visuals, list) or not all(isinstance(item, dict) for item in visuals):
        raise ValueError("'visuals' must be a list of objects.")
    if not isinstance(filters, list):
        raise ValueError("'filters' must be a list.")
    if not isinstance(narrative_sections, list):
        raise ValueError("'narrative_sections' must be a list.")

    return DashboardTemplate(
        id=str(payload.get("id") or (existing.id if existing else new_id("tpl"))),
        name=require_text_field(payload, "name"),
        description=optional_text_field(payload, "description", existing.description if existing else ""),
        dashboard_type=optional_text_field(payload, "dashboard_type", existing.dashboard_type if existing else ""),
        scope=optional_text_field(payload, "scope", existing.scope if existing else "custom"),
        filters=[str(item) for item in filters],
        visuals=visuals,
        layout=sanitize_dashboard_layout(layout, visuals),
        narrative_sections=[str(item) for item in narrative_sections],
        theme=optional_text_field(payload, "theme", existing.theme if existing else "studio_default") or "studio_default",
        created_at=(existing.created_at if existing and existing.created_at else now_iso_utc()),
        updated_at=now_iso_utc(),
    )

def upsert_dashboard_template(data: LogiTrackData, template: DashboardTemplate) -> str:
    for idx, existing in enumerate(data.dashboard_templates):
        if existing.id == template.id:
            data.dashboard_templates[idx] = template
            return "updated"
    data.dashboard_templates.append(template)
    return "created"

def build_dashboard_blueprint(data: LogiTrackData, dataset: TidyDataset, template_id: Optional[str] = None) -> Dict[str, Any]:
    recommendation = build_dashboard_recommendation_for_rows(dataset.rows, dataset.name)
    quality = build_tidy_dataset_quality_report(data, dataset)
    narrative = build_dataset_narrative_summary(data, dataset)
    builtin_templates = build_builtin_dashboard_templates(dataset, recommendation)
    custom_templates = [item for item in data.dashboard_templates if item.scope != "builtin"]
    template_lookup = {item.id: item for item in builtin_templates + custom_templates}
    selected = template_lookup.get(template_id) if template_id else builtin_templates[0]
    if selected is None:
        selected = builtin_templates[0]

    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "selected_template": asdict(selected),
        "available_templates": [asdict(item) for item in builtin_templates + custom_templates],
        "filters": selected.filters or recommendation.get("recommended_filters", []),
        "visuals": selected.visuals or recommendation.get("recommended_visuals", []),
        "layout": sanitize_dashboard_layout(selected.layout, selected.visuals or recommendation.get("recommended_visuals", [])),
        "narrative": narrative,
        "quality": quality,
        "mapping": asdict(effective_semantic_mapping(data, dataset)),
    }

def find_notification_rule(data: LogiTrackData, rule_id: str) -> Optional[NotificationRule]:
    for rule in data.notification_rules:
        if rule.id == rule_id:
            return rule
    return None

def build_notification_rule_from_payload(payload: Dict[str, Any], existing: Optional[NotificationRule] = None) -> NotificationRule:
    recipients = payload.get("recipients", existing.recipients if existing else [])
    if not isinstance(recipients, list):
        raise ValueError("'recipients' must be a list.")
    is_active_raw = payload.get("is_active", existing.is_active if existing else True)
    if isinstance(is_active_raw, str):
        is_active = is_active_raw.strip().lower() not in {"0", "false", "no"}
    else:
        is_active = bool(is_active_raw)

    return NotificationRule(
        id=str(payload.get("id") or (existing.id if existing else new_id("rule"))),
        name=require_text_field(payload, "name"),
        is_active=is_active,
        schedule=optional_text_field(payload, "schedule", existing.schedule if existing else "manual") or "manual",
        channel=optional_text_field(payload, "channel", existing.channel if existing else "webhook") or "webhook",
        provider=optional_text_field(payload, "provider", existing.provider if existing else ""),
        min_severity=optional_text_field(payload, "min_severity", existing.min_severity if existing else "medium") or "medium",
        condition_type=optional_text_field(payload, "condition_type", existing.condition_type if existing else ""),
        threshold=num(payload.get("threshold")) if payload.get("threshold") not in (None, "") else (existing.threshold if existing else None),
        project_id=optional_text_field(payload, "project_id", existing.project_id if existing else ""),
        indicator_id=optional_text_field(payload, "indicator_id", existing.indicator_id if existing else ""),
        dataset_id=optional_text_field(payload, "dataset_id", existing.dataset_id if existing else ""),
        recipients=[str(item) for item in recipients],
        webhook_url=optional_text_field(payload, "webhook_url", existing.webhook_url if existing else ""),
        notes=optional_text_field(payload, "notes", existing.notes if existing else ""),
        last_run_at=existing.last_run_at if existing else "",
        created_at=(existing.created_at if existing and existing.created_at else now_iso_utc()),
        updated_at=now_iso_utc(),
    )

def upsert_notification_rule(data: LogiTrackData, rule: NotificationRule) -> str:
    for idx, existing in enumerate(data.notification_rules):
        if existing.id == rule.id:
            data.notification_rules[idx] = rule
            return "updated"
    data.notification_rules.append(rule)
    return "created"

def is_notification_rule_due(rule: NotificationRule, now_dt: Optional[datetime] = None) -> bool:
    if not rule.is_active:
        return False
    now_dt = now_dt or utc_now()
    schedule = (rule.schedule or "manual").strip().lower()
    if schedule == "manual":
        return False
    if not rule.last_run_at:
        return True
    last_run = normalize_utc_datetime(rule.last_run_at)
    if last_run is None:
        return True
    if schedule == "daily":
        return (now_dt - last_run) >= timedelta(days=1)
    if schedule == "weekly":
        return (now_dt - last_run) >= timedelta(days=7)
    if schedule == "hourly":
        return (now_dt - last_run) >= timedelta(hours=1)
    return False

def evaluate_notification_rule(data: LogiTrackData, rule: NotificationRule) -> List[Dict[str, Any]]:
    notifications = build_current_notifications(data)

    if rule.project_id:
        notifications = [
            item for item in notifications
            if item.get("context", {}).get("project_id") == rule.project_id or item.get("source_id") == rule.project_id
        ]
    if rule.indicator_id:
        notifications = [
            item for item in notifications
            if item.get("context", {}).get("indicator_id") == rule.indicator_id or item.get("source_id") == rule.indicator_id
        ]
    if rule.dataset_id:
        notifications = [
            item for item in notifications
            if item.get("context", {}).get("dataset_id") == rule.dataset_id or item.get("source_id") == rule.dataset_id
        ]

    condition = (rule.condition_type or "").strip().lower()
    threshold = rule.threshold

    if condition == "progress_below" and threshold is not None:
        scoped = []
        if rule.indicator_id and rule.project_id:
            series = build_indicator_trend_series(data, rule.project_id, rule.indicator_id)
            if series and series[-1].get("progress_weighted_pct") is not None and float(series[-1]["progress_weighted_pct"]) < float(threshold):
                scoped.append(make_notification(
                    "high",
                    "rule_progress_below",
                    "indicator",
                    rule.indicator_id,
                    f"Rule '{rule.name}' triggered",
                    f"Indicator progress is below {threshold}%.",
                    "Review the indicator and its recovery actions.",
                    {"project_id": rule.project_id, "indicator_id": rule.indicator_id},
                ))
        elif rule.project_id:
            series = build_project_trend_series(data, rule.project_id)
            if series and series[-1].get("progress_weighted_pct") is not None and float(series[-1]["progress_weighted_pct"]) < float(threshold):
                scoped.append(make_notification(
                    "high",
                    "rule_progress_below",
                    "project",
                    rule.project_id,
                    f"Rule '{rule.name}' triggered",
                    f"Project progress is below {threshold}%.",
                    "Escalate the project review.",
                    {"project_id": rule.project_id},
                ))
        notifications.extend(scoped)

    if condition == "trend_drop" and threshold is not None and rule.project_id:
        series = build_project_trend_series(data, rule.project_id)
        if len(series) >= 2:
            latest = series[-1].get("progress_weighted_pct")
            previous = series[-2].get("progress_weighted_pct")
            if latest is not None and previous is not None and (float(previous) - float(latest)) >= float(threshold):
                notifications.append(make_notification(
                    "high",
                    "rule_trend_drop",
                    "project",
                    rule.project_id,
                    f"Rule '{rule.name}' triggered",
                    f"Project trend dropped by at least {threshold} percentage points.",
                    "Investigate the cause of the drop immediately.",
                    {"project_id": rule.project_id},
                ))

    if condition == "stale_reporting" and threshold is not None and rule.project_id:
        series = build_project_trend_series(data, rule.project_id)
        if series:
            latest_period = normalize_utc_datetime(series[-1]["reporting_period"])
            if latest_period is not None and (utc_now() - latest_period).days >= float(threshold):
                notifications.append(make_notification(
                    "medium",
                    "rule_stale_reporting",
                    "project",
                    rule.project_id,
                    f"Rule '{rule.name}' triggered",
                    f"The latest reporting period is older than {threshold} days.",
                    "Request a fresh reporting update.",
                    {"project_id": rule.project_id},
                ))

    return filter_notifications(notifications, min_severity=rule.min_severity)

def normalize_reporting_period_text(value: Any) -> str:
    parsed = parse_date_like_value(value)
    if parsed is None:
        raise ValueError("Reporting period must be a valid date or month value.")
    return parsed.date().isoformat()

def normalize_progress_number(value: Any, column_name: str = "") -> Optional[float]:
    progress = num(value)
    if progress is None:
        return None
    normalized_name = normalize_column_name(column_name)
    if -1.0 <= progress <= 1.0 and any(token in normalized_name for token in ("progress", "percent", "pct", "rate")):
        return float(progress * 100.0)
    return float(progress)

def find_project_by_name(data: LogiTrackData, project_name: str) -> Optional[Project]:
    target = str(project_name or "").strip().lower()
    if not target:
        return None
    for project in data.projects:
        if project.name.strip().lower() == target:
            return project
    return None

def find_indicator_global_by_name(data: LogiTrackData, indicator_name: str) -> Optional[Tuple[Project, Indicator]]:
    target = str(indicator_name or "").strip().lower()
    if not target:
        return None
    for project in data.projects:
        for indicator in project.indicators:
            if indicator.name.strip().lower() == target:
                return project, indicator
    return None

def resolve_project_from_reference(data: LogiTrackData, project_id: str = "", project_name: str = "") -> Optional[Project]:
    if project_id:
        project = find_project(data, project_id)
        if project is not None:
            return project
    if project_name:
        return find_project_by_name(data, project_name)
    return None

def resolve_indicator_from_reference(
    data: LogiTrackData,
    project: Optional[Project] = None,
    indicator_id: str = "",
    indicator_name: str = "",
) -> Optional[Tuple[Optional[Project], Indicator]]:
    if project is not None:
        if indicator_id:
            indicator = find_indicator(project, indicator_id)
            if indicator is not None:
                return project, indicator
        if indicator_name:
            target = indicator_name.strip().lower()
            for indicator in project.indicators:
                if indicator.name.strip().lower() == target:
                    return project, indicator

    if indicator_name:
        global_match = find_indicator_global_by_name(data, indicator_name)
        if global_match is not None:
            return global_match
    return None

def pick_unique_profile(
    column_profiles: List[Dict[str, Any]],
    used_columns: set,
    keywords: Tuple[str, ...] = (),
    role: Optional[str] = None,
    preferred_names: Tuple[str, ...] = (),
) -> Optional[Dict[str, Any]]:
    candidates = []
    for profile in column_profiles:
        if profile["name"] in used_columns:
            continue
        if role is not None and profile["role"] != role:
            continue
        if keywords and not any(keyword in profile["normalized_name"] for keyword in keywords):
            continue
        candidates.append(profile)

    if preferred_names:
        preferred = [profile for profile in candidates if profile["normalized_name"] in preferred_names]
        if preferred:
            preferred.sort(key=lambda profile: profile["name"])
            return preferred[0]

    if candidates:
        candidates.sort(key=lambda profile: profile["name"])
        return candidates[0]
    return None

def infer_reporting_history_mapping(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    schema = build_dataset_schema(rows)
    column_profiles = schema["columns"]
    used_columns: set = set()

    def assign(field_name: str, keywords: Tuple[str, ...] = (), role: Optional[str] = None, preferred_names: Tuple[str, ...] = ()) -> Optional[str]:
        profile = pick_unique_profile(column_profiles, used_columns, keywords=keywords, role=role, preferred_names=preferred_names)
        if profile is not None:
            used_columns.add(profile["name"])
            return profile["name"]
        return None

    reporting_period = assign("reporting_period", role="time") or assign("reporting_period", keywords=("date", "month", "period", "quarter", "year"))
    project_id_col = assign("project_id", keywords=("project_id", "program_id", "initiative_id"), role="identifier")
    project_name_col = assign("project_name", keywords=("project", "program", "initiative"))
    indicator_id_col = assign("indicator_id", keywords=("indicator_id", "kpi_id", "metric_id"), role="identifier")
    indicator_name_col = assign("indicator_name", keywords=("indicator", "kpi", "metric"))
    actual_col = assign("actual_value", keywords=("actual", "achieved", "result"), role="measure")
    target_col = assign("target_value", keywords=("target", "meta"), role="measure")
    progress_col = assign("progress_value", keywords=("progress", "percent", "pct", "rate", "score"), role="measure")
    budget_col = assign("budget_value", keywords=("budget", "cost", "expense", "amount"), role="measure")
    country_col = assign("country", keywords=("country",), role="geo_dimension")
    province_col = assign("province", keywords=("province", "state"), role="geo_dimension")
    district_col = assign("district", keywords=("district", "region", "location", "site", "area"), role="geo_dimension")
    status_col = assign("status", keywords=("status", "state", "risk"))
    owner_col = assign("owner", keywords=("owner", "manager", "assignee", "team"))
    currency_col = assign("currency", keywords=("currency", "moeda"))
    notes_col = assign("notes", keywords=("notes", "comment", "remark", "observation"))

    mappings = {
        "reporting_period": reporting_period,
        "project_id": project_id_col,
        "project_name": project_name_col,
        "indicator_id": indicator_id_col,
        "indicator_name": indicator_name_col,
        "actual_value": actual_col,
        "target_value": target_col,
        "progress_value": progress_col,
        "budget_value": budget_col,
        "country": country_col,
        "province": province_col,
        "district": district_col,
        "status": status_col,
        "owner": owner_col,
        "currency": currency_col,
        "notes": notes_col,
    }

    completed = sum(1 for value in mappings.values() if value)
    required_ready = bool(reporting_period and (progress_col or (actual_col and target_col)))
    confidence = round(completed / max(len(mappings), 1), 3)

    return {
        "schema": schema,
        "mappings": mappings,
        "can_materialize": required_ready,
        "confidence": confidence,
        "reason": (
            "The dataset contains a time field and either progress values or actual/target pairs."
            if required_ready
            else "The dataset is missing a reliable time field or KPI value fields for normalized history."
        ),
    }

def get_mapped_row_value(row: Dict[str, Any], mapping: Dict[str, Any], field_name: str) -> Any:
    column_name = mapping.get(field_name)
    if not column_name:
        return None
    return row.get(column_name)

def calculate_reporting_record_progress(record: ReportingPeriodRecord, indicator: Optional[Indicator] = None) -> Optional[float]:
    if record.progress_value is not None:
        return float(record.progress_value)
    if record.actual_value is None or record.target_value is None:
        return None
    if indicator is not None:
        return indicator.progress_for(record.actual_value, record.target_value)
    if record.target_value == 0:
        return None
    return (record.actual_value / record.target_value) * 100.0

def reporting_record_to_dict(record: ReportingPeriodRecord, data: Optional[LogiTrackData] = None) -> Dict[str, Any]:
    indicator = None
    if data is not None:
        project = resolve_project_from_reference(data, record.project_id, record.project_name)
        indicator_match = resolve_indicator_from_reference(data, project, record.indicator_id, record.indicator_name)
        if indicator_match is not None:
            _, indicator = indicator_match

    progress = calculate_reporting_record_progress(record, indicator=indicator)
    return {
        "record_id": record.id,
        "reporting_period": record.reporting_period,
        "project_id": record.project_id,
        "project_name": record.project_name,
        "indicator_id": record.indicator_id,
        "indicator_name": record.indicator_name,
        "country": record.country,
        "province": record.province,
        "district": record.district,
        "actual_value": record.actual_value,
        "target_value": record.target_value,
        "progress_value": (round(progress, 3) if progress is not None else None),
        "budget_value": record.budget_value,
        "currency": record.currency,
        "status": record.status,
        "owner": record.owner,
        "notes": record.notes,
        "source_dataset_id": record.source_dataset_id,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }

def reporting_record_natural_key(record: ReportingPeriodRecord) -> str:
    return "|".join([
        normalize_column_name(record.reporting_period),
        normalize_column_name(record.project_id or record.project_name),
        normalize_column_name(record.indicator_id or record.indicator_name),
        normalize_column_name(record.country),
        normalize_column_name(record.province),
        normalize_column_name(record.district),
        normalize_column_name(record.source_dataset_id),
    ])

def build_reporting_record_from_payload(
    payload: Dict[str, Any],
    data: LogiTrackData,
    source_dataset_id: str = "",
    existing: Optional[ReportingPeriodRecord] = None,
) -> ReportingPeriodRecord:
    reporting_period = normalize_reporting_period_text(payload.get("reporting_period"))
    project_id = optional_text_field(payload, "project_id")
    project_name = optional_text_field(payload, "project_name")
    indicator_id = optional_text_field(payload, "indicator_id")
    indicator_name = optional_text_field(payload, "indicator_name")

    project = resolve_project_from_reference(data, project_id, project_name)
    if project is not None:
        project_id = project.id
        if not project_name:
            project_name = project.name

    indicator = None
    indicator_match = resolve_indicator_from_reference(data, project, indicator_id, indicator_name)
    if indicator_match is not None:
        resolved_project, resolved_indicator = indicator_match
        indicator = resolved_indicator
        if resolved_project is not None:
            project = resolved_project
            project_id = project.id
            if not project_name:
                project_name = project.name
        indicator_id = resolved_indicator.id
        if not indicator_name:
            indicator_name = resolved_indicator.name

    if not project_id and not project_name:
        raise ValueError("Reporting record requires project_id or project_name.")
    if not indicator_id and not indicator_name:
        raise ValueError("Reporting record requires indicator_id or indicator_name.")

    actual_value = num(payload.get("actual_value"))
    target_value = num(payload.get("target_value"))
    progress_value = normalize_progress_number(payload.get("progress_value"), "progress_value")
    budget_value = num(payload.get("budget_value"))

    record = ReportingPeriodRecord(
        id=str(payload.get("id") or (existing.id if existing else new_id("rpt"))),
        reporting_period=reporting_period,
        project_id=project_id,
        project_name=project_name,
        indicator_id=indicator_id,
        indicator_name=indicator_name,
        country=optional_text_field(payload, "country"),
        province=optional_text_field(payload, "province"),
        district=optional_text_field(payload, "district"),
        actual_value=actual_value,
        target_value=target_value,
        progress_value=progress_value,
        budget_value=budget_value,
        currency=optional_text_field(payload, "currency").upper(),
        status=optional_text_field(payload, "status"),
        owner=optional_text_field(payload, "owner"),
        notes=optional_text_field(payload, "notes"),
        source_dataset_id=source_dataset_id or optional_text_field(payload, "source_dataset_id"),
        created_at=(existing.created_at if existing and existing.created_at else now_iso_utc()),
        updated_at=now_iso_utc(),
    )

    if record.progress_value is None:
        derived_progress = calculate_reporting_record_progress(record, indicator=indicator)
        record.progress_value = round(derived_progress, 6) if derived_progress is not None else None
    return record

def build_reporting_record_from_dataset_row(
    row: Dict[str, Any],
    mapping_info: Dict[str, Any],
    data: LogiTrackData,
    source_dataset_id: str,
    existing: Optional[ReportingPeriodRecord] = None,
) -> ReportingPeriodRecord:
    mappings = mapping_info["mappings"]
    payload = {
        "reporting_period": get_mapped_row_value(row, mappings, "reporting_period"),
        "project_id": get_mapped_row_value(row, mappings, "project_id"),
        "project_name": get_mapped_row_value(row, mappings, "project_name"),
        "indicator_id": get_mapped_row_value(row, mappings, "indicator_id"),
        "indicator_name": get_mapped_row_value(row, mappings, "indicator_name"),
        "actual_value": get_mapped_row_value(row, mappings, "actual_value"),
        "target_value": get_mapped_row_value(row, mappings, "target_value"),
        "progress_value": get_mapped_row_value(row, mappings, "progress_value"),
        "budget_value": get_mapped_row_value(row, mappings, "budget_value"),
        "country": get_mapped_row_value(row, mappings, "country"),
        "province": get_mapped_row_value(row, mappings, "province"),
        "district": get_mapped_row_value(row, mappings, "district"),
        "status": get_mapped_row_value(row, mappings, "status"),
        "owner": get_mapped_row_value(row, mappings, "owner"),
        "currency": get_mapped_row_value(row, mappings, "currency"),
        "notes": get_mapped_row_value(row, mappings, "notes"),
        "source_dataset_id": source_dataset_id,
    }
    if mappings.get("progress_value"):
        payload["progress_value"] = normalize_progress_number(
            get_mapped_row_value(row, mappings, "progress_value"),
            mappings["progress_value"],
        )
    return build_reporting_record_from_payload(payload, data, source_dataset_id=source_dataset_id, existing=existing)

def find_reporting_record_by_key(data: LogiTrackData, key: str) -> Optional[ReportingPeriodRecord]:
    for record in data.reporting_records:
        if reporting_record_natural_key(record) == key:
            return record
    return None

def upsert_reporting_records(data: LogiTrackData, records: List[ReportingPeriodRecord]) -> Dict[str, int]:
    created = 0
    updated = 0
    existing_by_key = {reporting_record_natural_key(record): idx for idx, record in enumerate(data.reporting_records)}

    for record in records:
        key = reporting_record_natural_key(record)
        if key in existing_by_key:
            idx = existing_by_key[key]
            record.id = data.reporting_records[idx].id
            record.created_at = data.reporting_records[idx].created_at or record.created_at
            data.reporting_records[idx] = record
            updated += 1
        else:
            data.reporting_records.append(record)
            existing_by_key[key] = len(data.reporting_records) - 1
            created += 1

    return {"created": created, "updated": updated, "total": len(records)}

def materialize_reporting_records_from_tidy_dataset(
    data: LogiTrackData,
    dataset: TidyDataset,
) -> Dict[str, Any]:
    mapping_info = infer_reporting_history_mapping(dataset.rows)
    semantic_mapping = find_semantic_mapping(data, dataset.id)
    if semantic_mapping is not None and semantic_mapping.fields:
        merged = dict(mapping_info.get("mappings", {}))
        merged.update(semantic_mapping.fields)
        mapping_info["mappings"] = merged
        mapping_info["can_materialize"] = bool(
            merged.get("reporting_period") and (merged.get("progress_value") or (merged.get("actual_value") and merged.get("target_value")))
        )
    if not mapping_info["can_materialize"]:
        raise ValueError(mapping_info["reason"])

    records: List[ReportingPeriodRecord] = []
    skipped = 0
    for row in dataset.rows:
        try:
            existing = find_reporting_record_by_key(
                data,
                "|".join([
                    normalize_column_name(normalize_reporting_period_text(get_mapped_row_value(row, mapping_info["mappings"], "reporting_period"))),
                    normalize_column_name(str(get_mapped_row_value(row, mapping_info["mappings"], "project_id") or get_mapped_row_value(row, mapping_info["mappings"], "project_name") or "")),
                    normalize_column_name(str(get_mapped_row_value(row, mapping_info["mappings"], "indicator_id") or get_mapped_row_value(row, mapping_info["mappings"], "indicator_name") or "")),
                    normalize_column_name(str(get_mapped_row_value(row, mapping_info["mappings"], "country") or "")),
                    normalize_column_name(str(get_mapped_row_value(row, mapping_info["mappings"], "province") or "")),
                    normalize_column_name(str(get_mapped_row_value(row, mapping_info["mappings"], "district") or "")),
                    normalize_column_name(dataset.id),
                ]),
            )
            record = build_reporting_record_from_dataset_row(row, mapping_info, data, dataset.id, existing=existing)
            records.append(record)
        except Exception:
            skipped += 1

    summary = upsert_reporting_records(data, records)
    summary["skipped"] = skipped
    summary["dataset_id"] = dataset.id
    summary["mapping"] = mapping_info
    return summary

def group_reporting_records_by_period(records: List[ReportingPeriodRecord]) -> List[Tuple[str, List[ReportingPeriodRecord]]]:
    grouped: Dict[str, List[ReportingPeriodRecord]] = {}
    for record in records:
        grouped.setdefault(record.reporting_period, []).append(record)

    periods = sorted(grouped.keys(), key=lambda value: normalize_utc_datetime(value) or UTC_DATETIME_MIN)
    return [(period, grouped[period]) for period in periods]

def build_reporting_trend_series(data: LogiTrackData, records: List[ReportingPeriodRecord]) -> List[Dict[str, Any]]:
    series: List[Dict[str, Any]] = []
    for period, rows in group_reporting_records_by_period(records):
        progress_list: List[float] = []
        progress_pairs: List[Tuple[Optional[float], Optional[float]]] = []
        actual_total = 0.0
        target_total = 0.0
        budget_total = 0.0
        actual_present = False
        target_present = False
        dimensions = set()

        for record in rows:
            indicator_match = resolve_indicator_from_reference(
                data,
                resolve_project_from_reference(data, record.project_id, record.project_name),
                record.indicator_id,
                record.indicator_name,
            )
            indicator = indicator_match[1] if indicator_match is not None else None
            progress = calculate_reporting_record_progress(record, indicator=indicator)
            if progress is not None:
                progress_list.append(float(progress))
                progress_pairs.append((float(progress), record.target_value))

            if record.actual_value is not None:
                actual_total += float(record.actual_value)
                actual_present = True
            if record.target_value is not None:
                target_total += float(record.target_value)
                target_present = True
            if record.budget_value is not None:
                budget_total += float(record.budget_value)

            dimension_label = " | ".join(part for part in [record.country, record.province, record.district] if part)
            if dimension_label:
                dimensions.add(dimension_label)

        mean_progress = safe_mean(progress_list)
        weighted_progress = weighted_mean(progress_pairs)
        series.append({
            "reporting_period": period,
            "records_count": len(rows),
            "actual_total": (round(actual_total, 3) if actual_present else None),
            "target_total": (round(target_total, 3) if target_present else None),
            "budget_total": round(budget_total, 3),
            "progress_mean_pct": (round(mean_progress, 3) if mean_progress is not None else None),
            "progress_weighted_pct": (round(weighted_progress, 3) if weighted_progress is not None else None),
            "status_mean_canon": canon_status_from_progress(mean_progress),
            "status_weighted_canon": canon_status_from_progress(weighted_progress),
            "dimensions_count": len(dimensions),
        })
    return series

def latest_reporting_period(records: List[ReportingPeriodRecord]) -> Optional[str]:
    periods = [record.reporting_period for record in records if record.reporting_period]
    if not periods:
        return None
    periods.sort(key=lambda value: normalize_utc_datetime(value) or UTC_DATETIME_MIN)
    return periods[-1]

def build_project_trend_series(data: LogiTrackData, project_id: str) -> List[Dict[str, Any]]:
    records = [record for record in data.reporting_records if record.project_id == project_id]
    return build_reporting_trend_series(data, records)

def build_indicator_trend_series(data: LogiTrackData, project_id: str, indicator_id: str) -> List[Dict[str, Any]]:
    records = [
        record for record in data.reporting_records
        if record.project_id == project_id and record.indicator_id == indicator_id
    ]
    return build_reporting_trend_series(data, records)

def build_portfolio_trend_series(data: LogiTrackData) -> List[Dict[str, Any]]:
    return build_reporting_trend_series(data, data.reporting_records)

# ----------------------------
# INPUT: Reporting creation
# ----------------------------
def create_location() -> LocationEntry:
    country = input(f"{tr('country')}: ").strip()
    province = input(f"{tr('province')}: ").strip()
    district = input(f"{tr('district')}: ").strip()
    lat = num(input(f"{tr('lat')}: "))
    lon = num(input(f"{tr('lon')}: "))
    target_local = num(input(f"{tr('target_district')}: "))
    actual_local = num(input(f"{tr('actual_district')}: "))
    budget_local = num(input(f"{tr('budget_district')}: "))
    currency = input(f"{tr('currency')}: ").strip().upper()
    if currency.lower() == "outro" or currency.lower() == "other":
        currency = input(f"{tr('currency_spec')}: ").strip().upper()
    if lat is None or lon is None:
        raise ValueError(tr("latlon_invalid"))
    return LocationEntry(
        country=country, province=province, district=district,
        latitude=float(lat), longitude=float(lon),
        target_local=target_local, actual_local=actual_local,
        budget_local=budget_local, currency=currency
    )

def create_indicator() -> Indicator:
    ind_id = new_id("ind")
    name = input(f"{tr('indicator_name')}: ").strip()
    unit = input(f"{tr('unit')}: ").strip()
    if unit.lower() == "outro" or unit.lower() == "other":
        unit = input(f"{tr('unit_spec')}: ").strip()
    frequency = input(f"{tr('frequency')}: ").strip()
    direction = (input(f"{tr('direction_updown')}: ").strip().lower() or "up")
    level = (input(f"{tr('level_oi')}: ").strip().lower() or "output")
    target = num(input(f"{tr('target_general')}: "))
    baseline = num(input(f"{tr('baseline_optional')}: "))
    ind = Indicator(
        id=ind_id, name=name, unit=unit, frequency=frequency,
        direction=direction, level=level, target=target, baseline=baseline
    )
    while yes(input(f"{tr('add_location')}: ")):
        ind.locations.append(create_location())
    return ind

def create_project() -> Project:
    pid = new_id("proj")
    name = input(f"{tr('create_project_inputs_name')}: ").strip()
    objective = input(f"{tr('create_project_inputs_objective')}: ").strip()
    p = Project(id=pid, name=name, objective=objective)
    while yes(input(f"{tr('add_indicator')}: ")):
        p.indicators.append(create_indicator())
    return p

# ----------------------------
# Ops Lite menus
# ----------------------------
def pick_project(data: LogiTrackData) -> Optional[Project]:
    if not data.projects:
        print(tr("no_projects"))
        return None
    print(f"\n{tr('projects')}:")
    for idx, p in enumerate(data.projects, start=1):
        print(f"  {idx}) {p.name} ({p.id})")
    sel = input(f"{tr('pick_project')}: ").strip()
    try:
        i = int(sel)
        if 1 <= i <= len(data.projects):
            return data.projects[i-1]
    except Exception:
        pass
    print(tr("selection_invalid"))
    return None

def list_indicators(p: Project) -> None:
    if not p.indicators:
        print("—")
        return
    print(f"\n{tr('indicators_for_link')}:")
    for idx, ind in enumerate(p.indicators, start=1):
        print(f"  {idx}) {ind.name} | {tr('level')}={ind.level} | id={ind.id}")

def ensure_ops(data: LogiTrackData, project_id: str) -> OpsLite:
    if project_id not in data.ops_by_project:
        data.ops_by_project[project_id] = OpsLite()
    return data.ops_by_project[project_id]

def create_operational_activity(p: Project, ops: OpsLite) -> None:
    print("\n" + tr("new_op_act"))
    act_id = new_id("act")
    name = input(f"{tr('op_act_name')}: ").strip()
    owner = input(f"{tr('owner')}: ").strip()
    start = parse_date(input(f"{tr('start_date')}: "))
    due = parse_date(input(f"{tr('due_date')}: "))
    status = (input(f"{tr('status_op')}: ").strip().lower() or "planned")

    list_indicators(p)
    linked = input(f"{tr('linked_ids')}: ").strip()
    linked_ids = [x.strip() for x in linked.split(",") if x.strip()]
    existing_ids = {i.id for i in p.indicators}
    linked_ids = [x for x in linked_ids if x in existing_ids]
    if not linked_ids:
        print(tr("logframe_required"))
        print(tr("op_cancelled"))
        return

    ops.activities.append(OperationalActivity(
        id=act_id, name=name, owner=owner,
        start_date=start, due_date=due,
        status=status, linked_indicator_ids=linked_ids
    ))
    print(tr("op_created"))

def list_operational_activities(ops: OpsLite) -> None:
    if not ops.activities:
        print(tr("no_ops_acts"))
        return
    print(f"\n{tr('ops_list')}:")
    for idx, a in enumerate(ops.activities, start=1):
        print(f"  {idx}) {a.name} | owner={a.owner} | status={a.status} | due={fmt_date(a.due_date)} | id={a.id}")
        print(f"     {tr('links')}: {', '.join(a.linked_indicator_ids)}")
        if a.tasks:
            for t in a.tasks:
                print(f"       - {tr('task_tag')} {t.name} | {t.status} | due={fmt_date(t.due_date)} | owner={t.owner}")

def pick_activity(ops: OpsLite) -> Optional[OperationalActivity]:
    if not ops.activities:
        print(tr("no_ops_acts"))
        return None
    list_operational_activities(ops)
    sel = input(f"{tr('pick_activity')}: ").strip()
    try:
        i = int(sel)
        if 1 <= i <= len(ops.activities):
            return ops.activities[i-1]
    except Exception:
        pass
    print(tr("selection_invalid"))
    return None

def add_task_to_activity(act: OperationalActivity) -> None:
    print("\n" + tr("new_task"))
    tid = new_id("task")
    name = input(f"{tr('task_name')}: ").strip()
    owner = input(f"{tr('task_owner')}: ").strip()
    due = parse_date(input(f"{tr('due_date')}: "))
    status = (input(f"{tr('task_status')}: ").strip().lower() or "todo")
    notes = input(f"{tr('notes')}: ").strip()
    act.tasks.append(Task(id=tid, name=name, owner=owner, due_date=due, status=status, notes=notes))
    print(tr("task_added"))

def update_task_status(act: OperationalActivity) -> None:
    if not act.tasks:
        print(tr("no_tasks"))
        return
    print(f"\n{tr('tasks')}:")
    for idx, t in enumerate(act.tasks, start=1):
        print(f"  {idx}) {t.name} | {t.status} | due={fmt_date(t.due_date)} | owner={t.owner}")
    sel = input(f"{tr('pick_task')}: ").strip()
    try:
        i = int(sel)
        if 1 <= i <= len(act.tasks):
            new_status = input(f"{tr('new_status')}: ").strip().lower()
            if new_status in ("todo", "doing", "done"):
                act.tasks[i-1].status = new_status
                print(tr("status_updated"))
                return
    except Exception:
        pass
    print(tr("selection_invalid"))

# ----------------------------
# REPORT (includes Workplan Snapshot)
# ----------------------------
def workplan_snapshot(p: Project, ops: OpsLite) -> None:
    print("\n" + tr("workplan_snapshot"))
    if not ops.activities:
        print(tr("no_ops_registered"))
        return

    today = date.today()
    next_7 = today + timedelta(days=7)

    overdue_tasks = []
    upcoming_tasks = []

    for a in ops.activities:
        for t in a.tasks:
            if t.due_date is None:
                continue
            if t.status != "done" and t.due_date < today:
                overdue_tasks.append((a, t))
            elif t.status != "done" and today <= t.due_date <= next_7:
                upcoming_tasks.append((a, t))

    print(f"{tr('overdue_tasks')}: {len(overdue_tasks)}")
    for a, t in overdue_tasks[:10]:
        print(f"  - {t.name} (owner={t.owner}) | due={fmt_date(t.due_date)} | activity={a.name}")

    print(f"{tr('upcoming_tasks')}: {len(upcoming_tasks)}")
    for a, t in upcoming_tasks[:10]:
        print(f"  - {t.name} (owner={t.owner}) | due={fmt_date(t.due_date)} | activity={a.name}")

    ind_ids = {i.id: i.name for i in p.indicators}
    linked_map = {iid: 0 for iid in ind_ids.keys()}
    for a in ops.activities:
        for iid in a.linked_indicator_ids:
            if iid in linked_map:
                linked_map[iid] += 1
    no_ops = [ind_ids[iid] for iid, c in linked_map.items() if c == 0]
    if no_ops:
        print("\n" + tr("ind_no_ops_warning"))
        for name in no_ops[:15]:
            print(f"  - {name}")

def report_project_basic(p: Project, ops: OpsLite) -> None:
    print("\n" + "=" * 80)
    print(tr("report_title", name=CONFIG["system_name"], version=CONFIG["version"]))
    print("=" * 80)
    print(f"{tr('project')}: {p.name}")
    print(f"{tr('objective')}: {p.objective}")
    print("-" * 80)

    all_prog = []
    for ind in p.indicators:
        vals = []
        for loc in ind.locations:
            prog = ind.progress_for(loc.actual_local, loc.target_local)
            if prog is not None:
                vals.append(prog)

        avg_loc_prog = mean(vals) if vals else None
        canon = ind.status_canon_for(avg_loc_prog)

        print(f"{tr('indicator')}: {ind.name} | {tr('level')}={ind.level} | {tr('direction')}={ind.direction}")
        if avg_loc_prog is not None:
            print(f"  {tr('progress_avg_district')}: {avg_loc_prog:.1f}%")
        else:
            print(f"  {tr('progress_na')}: -")

        print(f"  {tr('state')}: {display_status(canon)}")

        linked_acts = [a for a in ops.activities if ind.id in a.linked_indicator_ids]
        if linked_acts:
            print("  " + tr("workplan_some", n=len(linked_acts)))
        else:
            print("  " + tr("workplan_none"))

        print("-" * 40)
        if avg_loc_prog is not None:
            all_prog.append(avg_loc_prog)

    if all_prog:
        print(f"{tr('exec_summary_avg')}: {mean(all_prog):.1f}%")
    else:
        print(f"{tr('exec_summary_avg')}: -")

    workplan_snapshot(p, ops)
    print("=" * 80)

# ----------------------------
# KPI rules (standardized)
# ----------------------------
def safe_mean(values: List[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return mean(vals) if vals else None

def weighted_mean(pairs: List[Tuple[Optional[float], Optional[float]]]) -> Optional[float]:
    # Weighted by target_local (common M&E/BI practice)
    nume = 0.0
    deno = 0.0
    for prog, w in pairs:
        if prog is None or w is None:
            continue
        if w <= 0:
            continue
        nume += prog * w
        deno += w
    if deno == 0:
        return None
    return nume / deno

def canon_status_from_progress(progress: Optional[float]) -> str:
    if progress is None:
        return "SEM DADOS"
    t = CONFIG["status_thresholds"]
    if progress >= t["superou"]:
        return "SUPEROU"
    if progress >= t["verde"]:
        return "VERDE"
    if progress >= t["amarelo"]:
        return "AMARELO"
    return "VERMELHO"

# ----------------------------
# BI Flattening (tables + bridge + KPIs)
# ----------------------------
def build_bi_tables(data: LogiTrackData):
    projects = []
    indicators = []
    indicator_locations = []
    activities = []
    tasks = []
    activity_indicator_links = []

    kpi_project = []
    kpi_indicator = []
    kpi_district = []
    kpi_workplan = []

    for p in data.projects:
        projects.append({"project_id": p.id, "project_name": p.name, "objective": p.objective})

        ops = data.ops_by_project.get(p.id, OpsLite())
        for a in ops.activities:
            activities.append({
                "activity_id": a.id, "project_id": p.id,
                "activity_name": a.name, "owner": a.owner,
                "start_date": (a.start_date.isoformat() if a.start_date else None),
                "due_date": (a.due_date.isoformat() if a.due_date else None),
                "status": a.status,
                "linked_indicator_ids": ",".join(a.linked_indicator_ids),
            })

            for iid in a.linked_indicator_ids:
                activity_indicator_links.append({
                    "project_id": p.id,
                    "activity_id": a.id,
                    "indicator_id": iid
                })

            for tsk in a.tasks:
                tasks.append({
                    "task_id": tsk.id, "project_id": p.id, "activity_id": a.id,
                    "task_name": tsk.name, "owner": tsk.owner,
                    "due_date": (tsk.due_date.isoformat() if tsk.due_date else None),
                    "status": normalize_task_status(tsk.status),
                    "status_label": task_status_display_label(tsk.status),
                    "notes": tsk.notes,
                    "assignee_username": tsk.assignee_username,
                    "assignee_name": tsk.assignee_name or tsk.owner,
                    "priority": tsk.priority,
                    "progress_pct": round(float(tsk.progress_pct or 0.0), 2),
                    "category": tsk.category,
                    "linked_indicator_id": tsk.linked_indicator_id,
                    "evidence_count": len(tsk.evidence_placeholders or []),
                    "comment_count": len(tsk.activity_log or []),
                    "created_at": tsk.created_at,
                    "updated_at": tsk.updated_at,
                    "submitted_at": tsk.submitted_at,
                    "validated_at": tsk.validated_at,
                    "approved_at": tsk.approved_at,
                })

        for ind in p.indicators:
            indicators.append({
                "indicator_id": ind.id,
                "project_id": p.id,
                "indicator_name": ind.name,
                "unit": ind.unit,
                "frequency": ind.frequency,
                "direction": ind.direction,
                "level": ind.level,
                "target": ind.target,
                "baseline": ind.baseline
            })

            prog_list = []
            prog_weight_pairs = []
            missing_count = 0
            valid_count = 0
            budget_sum = 0.0

            for loc in ind.locations:
                prog = ind.progress_for(loc.actual_local, loc.target_local)
                canon = ind.status_canon_for(prog)

                has_target = loc.target_local is not None and loc.target_local != 0
                has_actual = loc.actual_local is not None
                is_valid = (prog is not None)

                if is_valid:
                    valid_count += 1
                    prog_list.append(float(prog))
                    prog_weight_pairs.append((float(prog), loc.target_local))
                else:
                    missing_count += 1

                if loc.budget_local is not None:
                    budget_sum += float(loc.budget_local)

                indicator_locations.append({
                    "indicator_id": ind.id,
                    "project_id": p.id,
                    "country": loc.country,
                    "province": loc.province,
                    "district": loc.district,
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "target_local": loc.target_local,
                    "actual_local": loc.actual_local,
                    "budget_local": loc.budget_local,
                    "currency": loc.currency,
                    "progress_pct": (round(prog, 3) if prog is not None else None),
                    "status_canon": canon,
                    "has_target": bool(has_target),
                    "has_actual": bool(has_actual),
                    "is_valid_progress": bool(is_valid),
                })

            avg_prog = safe_mean(prog_list)
            wavg_prog = weighted_mean(prog_weight_pairs)

            kpi_indicator.append({
                "project_id": p.id,
                "indicator_id": ind.id,
                "indicator_name": ind.name,
                "level": ind.level,
                "direction": ind.direction,
                "progress_mean_pct": (round(avg_prog, 3) if avg_prog is not None else None),
                "progress_weighted_pct": (round(wavg_prog, 3) if wavg_prog is not None else None),
                "status_mean_canon": canon_status_from_progress(avg_prog),
                "status_weighted_canon": canon_status_from_progress(wavg_prog),
                "district_valid_count": valid_count,
                "district_missing_count": missing_count,
                "budget_total": round(budget_sum, 3),
            })

        # Project KPI from base fact
        proj_prog = []
        proj_pairs = []
        proj_budget = 0.0
        proj_loc_valid = 0
        proj_loc_missing = 0

        for row in indicator_locations:
            if row["project_id"] != p.id:
                continue
            if row["budget_local"] is not None:
                proj_budget += float(row["budget_local"])
            if row["progress_pct"] is None:
                proj_loc_missing += 1
                continue
            proj_loc_valid += 1
            proj_prog.append(float(row["progress_pct"]))
            proj_pairs.append((float(row["progress_pct"]), row["target_local"]))

        proj_mean = safe_mean(proj_prog)
        proj_wavg = weighted_mean(proj_pairs)

        # Workplan KPIs
        today_ = date.today()
        next7_ = today_ + timedelta(days=7)

        tasks_total = 0
        tasks_done = 0
        tasks_overdue = 0
        tasks_next7 = 0
        acts_total = 0
        acts_open = 0

        for a in data.ops_by_project.get(p.id, OpsLite()).activities:
            acts_total += 1
            if (a.status or "").lower() != "done":
                acts_open += 1
            for t in a.tasks:
                tasks_total += 1
                if task_status_is_complete(t.status):
                    tasks_done += 1
                if t.due_date and task_status_is_open(t.status):
                    if t.due_date < today_:
                        tasks_overdue += 1
                    elif today_ <= t.due_date <= next7_:
                        tasks_next7 += 1

        ind_ids = {i.id for i in p.indicators}
        linked_ind_ids = {link["indicator_id"] for link in activity_indicator_links if link["project_id"] == p.id}
        linked_count = len(ind_ids.intersection(linked_ind_ids))
        ind_total = len(ind_ids)
        ind_without = max(ind_total - linked_count, 0)
        coverage = (linked_count / ind_total) if ind_total else None

        kpi_project.append({
            "project_id": p.id,
            "project_name": p.name,
            "progress_mean_pct": (round(proj_mean, 3) if proj_mean is not None else None),
            "progress_weighted_pct": (round(proj_wavg, 3) if proj_wavg is not None else None),
            "status_mean_canon": canon_status_from_progress(proj_mean),
            "status_weighted_canon": canon_status_from_progress(proj_wavg),
            "budget_total": round(proj_budget, 3),
            "locations_valid_count": proj_loc_valid,
            "locations_missing_count": proj_loc_missing,
            "indicators_total": ind_total,
            "indicators_linked_to_workplan": linked_count,
            "indicators_without_workplan": ind_without,
            "workplan_coverage_pct": (round(coverage * 100, 3) if coverage is not None else None),
            "activities_total": acts_total,
            "activities_open": acts_open,
            "tasks_total": tasks_total,
            "tasks_done": tasks_done,
            "tasks_overdue": tasks_overdue,
            "tasks_next_7_days": tasks_next7
        })

        # District KPI
        district_map: Dict[str, Dict] = {}
        for row in indicator_locations:
            if row["project_id"] != p.id:
                continue
            key = f"{row['country']}|{row['province']}|{row['district']}"
            if key not in district_map:
                district_map[key] = {
                    "project_id": p.id,
                    "country": row["country"],
                    "province": row["province"],
                    "district": row["district"],
                    "progress_list": [],
                    "pairs": [],
                    "budget_sum": 0.0,
                    "valid": 0,
                    "missing": 0,
                }
            dct = district_map[key]
            if row["budget_local"] is not None:
                dct["budget_sum"] += float(row["budget_local"])
            if row["progress_pct"] is None:
                dct["missing"] += 1
            else:
                dct["valid"] += 1
                dct["progress_list"].append(float(row["progress_pct"]))
                dct["pairs"].append((float(row["progress_pct"]), row["target_local"]))

        for _, dct in district_map.items():
            m = safe_mean(dct["progress_list"])
            w = weighted_mean(dct["pairs"])
            kpi_district.append({
                "project_id": dct["project_id"],
                "country": dct["country"],
                "province": dct["province"],
                "district": dct["district"],
                "progress_mean_pct": (round(m, 3) if m is not None else None),
                "progress_weighted_pct": (round(w, 3) if w is not None else None),
                "status_mean_canon": canon_status_from_progress(m),
                "status_weighted_canon": canon_status_from_progress(w),
                "budget_total": round(dct["budget_sum"], 3),
                "rows_valid_count": dct["valid"],
                "rows_missing_count": dct["missing"],
            })

        kpi_workplan.append({
            "project_id": p.id,
            "project_name": p.name,
            "activities_total": acts_total,
            "activities_open": acts_open,
            "tasks_total": tasks_total,
            "tasks_done": tasks_done,
            "tasks_overdue": tasks_overdue,
            "tasks_next_7_days": tasks_next7,
            "indicators_total": ind_total,
            "indicators_linked_to_workplan": linked_count,
            "indicators_without_workplan": ind_without,
            "workplan_coverage_pct": (round(coverage * 100, 3) if coverage is not None else None),
        })

    return (
        projects, indicators, indicator_locations, activities, tasks,
        activity_indicator_links,
        kpi_project, kpi_indicator, kpi_district, kpi_workplan
    )

def build_bi_payload(data: LogiTrackData) -> Dict[str, List[dict]]:
    (
        projects,
        indicators,
        indicator_locations,
        activities,
        tasks,
        activity_indicator_links,
        kpi_project,
        kpi_indicator,
        kpi_district,
        kpi_workplan,
    ) = build_bi_tables(data)

    return {
        "projects": projects,
        "indicators": indicators,
        "indicator_locations": indicator_locations,
        "activities": activities,
        "tasks": tasks,
        "activity_indicator_links": activity_indicator_links,
        "kpi_project": kpi_project,
        "kpi_indicator": kpi_indicator,
        "kpi_district": kpi_district,
        "kpi_workplan": kpi_workplan,
    }

def count_statuses(rows: List[dict], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "SEM DADOS")
        counts[value] = counts.get(value, 0) + 1
    return counts

def build_dashboard_summary(data: LogiTrackData) -> Dict[str, Any]:
    payload = build_bi_payload(data)
    project_kpis = payload["kpi_project"]
    indicator_kpis = payload["kpi_indicator"]
    district_kpis = payload["kpi_district"]
    workplan_kpis = payload["kpi_workplan"]
    notifications = build_current_notifications(data)
    portfolio_trend = build_portfolio_trend_series(data)

    project_mean_values = [row["progress_mean_pct"] for row in project_kpis if row["progress_mean_pct"] is not None]
    project_weighted_values = [row["progress_weighted_pct"] for row in project_kpis if row["progress_weighted_pct"] is not None]

    return {
        "generated_at": now_iso_utc(),
        "counts": {
            "projects": len(payload["projects"]),
            "indicators": len(payload["indicators"]),
            "indicator_locations": len(payload["indicator_locations"]),
            "activities": len(payload["activities"]),
            "tasks": len(payload["tasks"]),
            "tidy_datasets": len(data.tidy_datasets),
            "reporting_records": len(data.reporting_records),
            "notifications": len(notifications),
            "users": len(data.users),
            "audit_events": len(data.audit_events),
        },
        "portfolio": {
            "progress_mean_pct": safe_mean(project_mean_values),
            "progress_weighted_pct": safe_mean(project_weighted_values),
            "budget_total": round(sum(float(row.get("budget_total") or 0.0) for row in project_kpis), 3),
            "tasks_total": sum(int(row.get("tasks_total") or 0) for row in workplan_kpis),
            "tasks_overdue": sum(int(row.get("tasks_overdue") or 0) for row in workplan_kpis),
            "tasks_next_7_days": sum(int(row.get("tasks_next_7_days") or 0) for row in workplan_kpis),
            "project_status_counts": count_statuses(project_kpis, "status_mean_canon"),
            "indicator_status_counts": count_statuses(indicator_kpis, "status_mean_canon"),
            "latest_reporting_period": latest_reporting_period(data.reporting_records),
        },
        "projects": project_kpis,
        "indicators": indicator_kpis,
        "districts": district_kpis,
        "workplan": workplan_kpis,
        "portfolio_trend": portfolio_trend[-12:],
        "notifications_preview": notifications[:10],
        "security": {
            "users_total": len(data.users),
            "active_users": sum(1 for user in data.users if user.is_active),
            "audit_events_total": len(data.audit_events),
        },
        "tidy_datasets": [
            {
                "dataset_id": dataset.id,
                "name": dataset.name,
                "row_count": len(dataset.rows),
                "updated_at": dataset.updated_at,
            }
            for dataset in data.tidy_datasets
        ],
    }

def make_notification(
    severity: str,
    category: str,
    source_type: str,
    source_id: str,
    title: str,
    message: str,
    suggested_action: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "id": new_id("notif"),
        "severity": severity,
        "category": category,
        "source_type": source_type,
        "source_id": source_id,
        "title": title,
        "message": message,
        "suggested_action": suggested_action,
        "context": context or {},
        "generated_at": now_iso_utc(),
    }

def severity_rank(value: str) -> int:
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    return order.get((value or "").lower(), 0)

def filter_notifications(notifications: List[Dict[str, Any]], min_severity: str = "info", max_items: Optional[int] = None) -> List[Dict[str, Any]]:
    threshold = severity_rank(min_severity)
    filtered = [item for item in notifications if severity_rank(item.get("severity", "info")) >= threshold]
    filtered.sort(key=lambda item: (-severity_rank(item.get("severity", "info")), item.get("title", "")))
    if max_items is not None:
        return filtered[:max_items]
    return filtered

def find_latest_date_in_column(rows: List[Dict[str, Any]], column_name: str) -> Optional[datetime]:
    values = []
    for row in rows:
        parsed = normalize_utc_datetime(row.get(column_name))
        if parsed is not None:
            values.append(parsed)
    return max(values) if values else None

def status_is_open(value: Any) -> bool:
    return task_status_is_open(value)

def build_project_notifications(data: LogiTrackData) -> List[Dict[str, Any]]:
    payload = build_bi_payload(data)
    notifications: List[Dict[str, Any]] = []

    for project_row in payload["kpi_project"]:
        project_id = project_row["project_id"]
        project_name = project_row["project_name"]
        progress = project_row.get("progress_weighted_pct")
        tasks_overdue = int(project_row.get("tasks_overdue") or 0)
        coverage = project_row.get("workplan_coverage_pct")
        missing_locations = int(project_row.get("locations_missing_count") or 0)

        if tasks_overdue > 0:
            notifications.append(make_notification(
                "high",
                "delivery_risk",
                "project",
                project_id,
                f"{project_name}: overdue tasks detected",
                f"{tasks_overdue} task(s) are overdue in the workplan.",
                "Review overdue tasks, assign owners, and update the delivery plan.",
                {"project_id": project_id, "tasks_overdue": tasks_overdue},
            ))

        if progress is None:
            notifications.append(make_notification(
                "medium",
                "missing_data",
                "project",
                project_id,
                f"{project_name}: progress cannot be calculated",
                "The project does not yet have enough valid KPI values to compute overall progress.",
                "Upload actual and target values for indicator locations.",
                {"project_id": project_id},
            ))
        elif progress < 50:
            notifications.append(make_notification(
                "high",
                "kpi_underperformance",
                "project",
                project_id,
                f"{project_name}: KPI performance is off track",
                f"Weighted project progress is {round(progress, 2)}%, below the red threshold.",
                "Escalate the KPI review and trigger a management checkpoint.",
                {"project_id": project_id, "progress_weighted_pct": round(progress, 3)},
            ))
        elif progress < 80:
            notifications.append(make_notification(
                "medium",
                "kpi_watch",
                "project",
                project_id,
                f"{project_name}: KPI progress needs attention",
                f"Weighted project progress is {round(progress, 2)}%, below the green threshold.",
                "Investigate blockers and refresh the action plan for weak indicators.",
                {"project_id": project_id, "progress_weighted_pct": round(progress, 3)},
            ))

        if coverage is not None and coverage < 60:
            notifications.append(make_notification(
                "medium",
                "workplan_gap",
                "project",
                project_id,
                f"{project_name}: low KPI-to-workplan coverage",
                f"Only {round(float(coverage), 2)}% of indicators are linked to operational activities.",
                "Link missing indicators to operational activities so the dashboard can explain performance.",
                {"project_id": project_id, "workplan_coverage_pct": round(float(coverage), 3)},
            ))

        if missing_locations > 0:
            notifications.append(make_notification(
                "low",
                "data_quality",
                "project",
                project_id,
                f"{project_name}: some KPI rows are missing values",
                f"{missing_locations} location row(s) are missing progress inputs.",
                "Complete the missing actual or target values to improve KPI accuracy.",
                {"project_id": project_id, "locations_missing_count": missing_locations},
            ))

    for indicator_row in payload["kpi_indicator"]:
        progress = indicator_row.get("progress_weighted_pct")
        if progress is not None and progress < 50:
            notifications.append(make_notification(
                "high",
                "indicator_underperformance",
                "indicator",
                indicator_row["indicator_id"],
                f"{indicator_row['indicator_name']}: indicator is under target",
                f"Weighted indicator progress is {round(progress, 2)}%.",
                "Review the implementation activities linked to this indicator and update the mitigation plan.",
                {
                    "project_id": indicator_row["project_id"],
                    "indicator_id": indicator_row["indicator_id"],
                    "progress_weighted_pct": round(progress, 3),
                },
            ))

    for task_row in payload["tasks"]:
        due_value = parse_optional_date_value(task_row.get("due_date"), "due_date") if task_row.get("due_date") else None
        if due_value and status_is_open(task_row.get("status")):
            days_left = (due_value - date.today()).days
            if 0 <= days_left <= 3:
                notifications.append(make_notification(
                    "low",
                    "upcoming_deadline",
                    "task",
                    task_row["task_id"],
                    f"{task_row['task_name']}: deadline approaching",
                    f"The task is due on {task_row['due_date']} and is still marked as open.",
                    "Check progress with the task owner and confirm the next action.",
                    {
                        "project_id": task_row["project_id"],
                        "activity_id": task_row["activity_id"],
                        "task_id": task_row["task_id"],
                        "due_date": task_row["due_date"],
                    },
                ))

    return notifications

def build_tidy_dataset_notifications(dataset: TidyDataset) -> List[Dict[str, Any]]:
    notifications: List[Dict[str, Any]] = []
    schema = build_dataset_schema(dataset.rows)
    column_profiles = schema["columns"]

    time_col = schema["roles"]["time"][0] if schema["roles"]["time"] else None
    if time_col:
        latest = find_latest_date_in_column(dataset.rows, time_col)
        if latest is not None:
            age_days = (utc_now() - latest).days
            if age_days > 30:
                notifications.append(make_notification(
                    "medium",
                    "stale_dataset",
                    "tidy_dataset",
                    dataset.id,
                    f"{dataset.name}: dataset may be stale",
                    f"The latest value in '{time_col}' is {latest.date().isoformat()}, which is {age_days} days old.",
                    "Refresh the source file or confirm whether the reporting period is still current.",
                    {"dataset_id": dataset.id, "time_column": time_col, "latest_date": latest.date().isoformat()},
                ))

    status_profile = find_profile_by_keyword(column_profiles, ("status", "state", "risk"))
    if status_profile is not None:
        status_col = status_profile["name"]
        risky_terms = {"delayed", "late", "risk", "at risk", "critical", "blocked", "overdue", "red"}
        risky_rows = 0
        for row in dataset.rows:
            status_text = str(row.get(status_col, "")).strip().lower()
            if status_text in risky_terms:
                risky_rows += 1
        if risky_rows > 0:
            notifications.append(make_notification(
                "high" if risky_rows >= 3 else "medium",
                "status_alert",
                "tidy_dataset",
                dataset.id,
                f"{dataset.name}: risky status values found",
                f"{risky_rows} row(s) in '{status_col}' indicate risk, delay, or blockage.",
                "Open the dashboard drill-down and review the affected rows immediately.",
                {"dataset_id": dataset.id, "status_column": status_col, "risky_rows": risky_rows},
            ))

    actual_profile = find_profile_by_keyword(column_profiles, ("actual", "achieved", "result"), role="measure")
    target_profile = find_profile_by_keyword(column_profiles, ("target", "meta"), role="measure")
    label_col = choose_best_dimension(column_profiles)
    if actual_profile and target_profile:
        weak_rows = []
        for row in dataset.rows:
            actual_value = num(row.get(actual_profile["name"]))
            target_value = num(row.get(target_profile["name"]))
            if actual_value is None or target_value in (None, 0):
                continue
            progress = (actual_value / target_value) * 100
            if progress < 50:
                weak_rows.append({
                    "label": str(row.get(label_col)) if label_col else None,
                    "progress_pct": round(progress, 2),
                })
        if weak_rows:
            label_text = weak_rows[0]["label"] or "One row"
            notifications.append(make_notification(
                "high",
                "dataset_underperformance",
                "tidy_dataset",
                dataset.id,
                f"{dataset.name}: low actual-vs-target rows found",
                f"{len(weak_rows)} row(s) are below 50% attainment. Example: {label_text}.",
                "Prioritize a KPI review for the low-performing rows and confirm the target assumptions.",
                {
                    "dataset_id": dataset.id,
                    "actual_column": actual_profile["name"],
                    "target_column": target_profile["name"],
                    "sample_rows": weak_rows[:5],
                },
            ))

    return notifications

def build_reporting_trend_notifications(data: LogiTrackData) -> List[Dict[str, Any]]:
    notifications: List[Dict[str, Any]] = []
    today_utc = utc_now()

    for project in data.projects:
        series = build_project_trend_series(data, project.id)
        if not series:
            continue

        latest = series[-1]
        latest_period_dt = normalize_utc_datetime(latest["reporting_period"])
        if latest_period_dt is not None:
            age_days = (today_utc - latest_period_dt).days
            if age_days > 45:
                notifications.append(make_notification(
                    "medium",
                    "stale_reporting",
                    "project",
                    project.id,
                    f"{project.name}: reporting history is stale",
                    f"The latest reporting period is {latest['reporting_period']}, which is {age_days} days old.",
                    "Request a fresh reporting update from the project team.",
                    {"project_id": project.id, "latest_reporting_period": latest["reporting_period"]},
                ))

        if len(series) >= 2:
            previous = series[-2]
            latest_progress = latest.get("progress_weighted_pct")
            previous_progress = previous.get("progress_weighted_pct")
            if latest_progress is not None and previous_progress is not None:
                delta = float(latest_progress) - float(previous_progress)
                if delta <= -10:
                    notifications.append(make_notification(
                        "high",
                        "negative_trend",
                        "project",
                        project.id,
                        f"{project.name}: progress dropped between reporting periods",
                        f"Weighted progress moved from {round(previous_progress, 2)}% to {round(latest_progress, 2)}% between {previous['reporting_period']} and {latest['reporting_period']}.",
                        "Run a management review on the deteriorating KPIs and recovery actions.",
                        {
                            "project_id": project.id,
                            "previous_period": previous["reporting_period"],
                            "latest_period": latest["reporting_period"],
                            "delta_pct": round(delta, 3),
                        },
                    ))

        for indicator in project.indicators:
            indicator_series = build_indicator_trend_series(data, project.id, indicator.id)
            if len(indicator_series) < 2:
                continue
            latest_indicator = indicator_series[-1]
            previous_indicator = indicator_series[-2]
            latest_progress = latest_indicator.get("progress_weighted_pct")
            previous_progress = previous_indicator.get("progress_weighted_pct")
            if latest_progress is None or previous_progress is None:
                continue
            delta = float(latest_progress) - float(previous_progress)
            if delta <= -15:
                notifications.append(make_notification(
                    "high",
                    "indicator_negative_trend",
                    "indicator",
                    indicator.id,
                    f"{indicator.name}: indicator trend is deteriorating",
                    f"Weighted progress dropped from {round(previous_progress, 2)}% to {round(latest_progress, 2)}%.",
                    "Inspect the driver activities and validate whether targets or field data changed.",
                    {
                        "project_id": project.id,
                        "indicator_id": indicator.id,
                        "previous_period": previous_indicator["reporting_period"],
                        "latest_period": latest_indicator["reporting_period"],
                        "delta_pct": round(delta, 3),
                    },
                ))

    return notifications

def build_current_notifications(data: LogiTrackData) -> List[Dict[str, Any]]:
    notifications = build_project_notifications(data)
    notifications.extend(build_reporting_trend_notifications(data))
    for dataset in data.tidy_datasets:
        notifications.extend(build_tidy_dataset_notifications(dataset))
    return filter_notifications(notifications, min_severity="info")

def format_notifications_as_text(notifications: List[Dict[str, Any]]) -> str:
    lines = [
        f"{CONFIG['system_name']} notifications",
        f"Generated at: {now_iso_utc()}",
        "",
    ]
    for idx, notification in enumerate(notifications, start=1):
        lines.append(f"{idx}. [{notification.get('severity', 'info').upper()}] {notification.get('title', '')}")
        lines.append(f"   {notification.get('message', '')}")
        suggestion = notification.get("suggested_action")
        if suggestion:
            lines.append(f"   Suggested action: {suggestion}")
        lines.append("")
    return "\n".join(lines).strip()

def dispatch_notifications_to_webhook(notifications: List[Dict[str, Any]], webhook_url: str) -> Dict[str, Any]:
    body = json.dumps({
        "system": CONFIG["system_name"],
        "version": CONFIG["version"],
        "sent_at": now_iso_utc(),
        "notifications": notifications,
    }).encode("utf-8")

    req = urlrequest.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=15) as response:
        response_body = response.read().decode("utf-8", errors="replace")
        return {
            "ok": True,
            "status_code": getattr(response, "status", None),
            "response_body": response_body[:500],
        }

def dispatch_notifications_to_email(
    notifications: List[Dict[str, Any]],
    smtp_host: str,
    smtp_port: int,
    smtp_from: str,
    recipients: List[str],
    smtp_username: str = "",
    smtp_password: str = "",
    use_tls: bool = True,
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    if not recipients:
        raise ValueError("Email dispatch requires at least one recipient.")

    message = EmailMessage()
    message["From"] = smtp_from
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject or f"{CONFIG['system_name']} notifications ({len(notifications)})"
    message.set_content(format_notifications_as_text(notifications))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        if use_tls:
            server.starttls()
        if smtp_username:
            server.login(smtp_username, smtp_password)
        server.send_message(message)

    return {
        "ok": True,
        "channel": "email",
        "recipients": recipients,
        "subject": message["Subject"],
    }

def dispatch_notifications_to_sendgrid_email(
    notifications: List[Dict[str, Any]],
    api_key: str,
    sender_email: str,
    recipients: List[str],
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    if not recipients:
        raise ValueError("SendGrid email dispatch requires at least one recipient.")
    if not api_key or not sender_email:
        raise ValueError("SendGrid email dispatch requires api_key and sender_email.")

    payload = {
        "personalizations": [{"to": [{"email": email} for email in recipients]}],
        "from": {"email": sender_email},
        "subject": subject or f"{CONFIG['system_name']} notifications ({len(notifications)})",
        "content": [{"type": "text/plain", "value": format_notifications_as_text(notifications)}],
    }
    req = urlrequest.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=20) as response:
        return {
            "ok": True,
            "channel": "email",
            "provider": "sendgrid",
            "status_code": getattr(response, "status", None),
            "recipients": recipients,
        }

def dispatch_notifications_to_whatsapp_webhook(
    notifications: List[Dict[str, Any]],
    webhook_url: str,
    recipients: List[str],
) -> Dict[str, Any]:
    if not recipients:
        raise ValueError("WhatsApp dispatch requires at least one recipient.")

    body = json.dumps({
        "channel": "whatsapp",
        "system": CONFIG["system_name"],
        "version": CONFIG["version"],
        "sent_at": now_iso_utc(),
        "recipients": recipients,
        "message_text": format_notifications_as_text(notifications),
        "notifications": notifications,
    }).encode("utf-8")

    req = urlrequest.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=15) as response:
        response_body = response.read().decode("utf-8", errors="replace")
        return {
            "ok": True,
            "channel": "whatsapp_webhook",
            "status_code": getattr(response, "status", None),
            "response_body": response_body[:500],
            "recipients": recipients,
        }

def dispatch_notifications_to_twilio_whatsapp(
    notifications: List[Dict[str, Any]],
    account_sid: str,
    auth_token: str,
    from_number: str,
    recipients: List[str],
) -> Dict[str, Any]:
    if not recipients:
        raise ValueError("Twilio WhatsApp dispatch requires at least one recipient.")
    if not account_sid or not auth_token or not from_number:
        raise ValueError("Twilio WhatsApp dispatch requires account_sid, auth_token, and from_number.")

    message_text = format_notifications_as_text(notifications)
    auth_header = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
    sent = []
    for recipient in recipients:
        form = urlparse.urlencode({
            "From": from_number,
            "To": recipient,
            "Body": message_text,
        }).encode("utf-8")
        req = urlrequest.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
            data=form,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=20) as response:
            sent.append({"recipient": recipient, "status_code": getattr(response, "status", None)})

    return {
        "ok": True,
        "channel": "whatsapp",
        "provider": "twilio",
        "results": sent,
    }

def dispatch_notifications_to_meta_whatsapp(
    notifications: List[Dict[str, Any]],
    access_token: str,
    phone_number_id: str,
    recipients: List[str],
) -> Dict[str, Any]:
    if not recipients:
        raise ValueError("Meta WhatsApp dispatch requires at least one recipient.")
    if not access_token or not phone_number_id:
        raise ValueError("Meta WhatsApp dispatch requires access_token and phone_number_id.")

    message_text = format_notifications_as_text(notifications)
    sent = []
    for recipient in recipients:
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message_text[:4096]},
        }
        req = urlrequest.Request(
            f"https://graph.facebook.com/v19.0/{phone_number_id}/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=20) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            sent.append({
                "recipient": recipient,
                "status_code": getattr(response, "status", None),
                "response_body": response_body[:300],
            })

    return {
        "ok": True,
        "channel": "whatsapp",
        "provider": "meta_cloud",
        "results": sent,
    }

def notification_channels_status() -> Dict[str, Any]:
    smtp_host = (os.getenv("LOGITRACK_SMTP_HOST", "") or "").strip()
    smtp_from = (os.getenv("LOGITRACK_SMTP_FROM", "") or "").strip()
    whatsapp_webhook = (os.getenv("LOGITRACK_WHATSAPP_WEBHOOK_URL", "") or "").strip()
    generic_webhook = (os.getenv("LOGITRACK_NOTIFY_WEBHOOK_URL", "") or "").strip()
    sendgrid_key = (os.getenv("LOGITRACK_SENDGRID_API_KEY", "") or "").strip()
    sendgrid_from = (os.getenv("LOGITRACK_SENDGRID_FROM", "") or "").strip()
    twilio_sid = (os.getenv("LOGITRACK_TWILIO_ACCOUNT_SID", "") or "").strip()
    twilio_token = (os.getenv("LOGITRACK_TWILIO_AUTH_TOKEN", "") or "").strip()
    twilio_from = (os.getenv("LOGITRACK_TWILIO_WHATSAPP_FROM", "") or "").strip()
    meta_token = (os.getenv("LOGITRACK_META_WHATSAPP_TOKEN", "") or "").strip()
    meta_phone_id = (os.getenv("LOGITRACK_META_WHATSAPP_PHONE_NUMBER_ID", "") or "").strip()
    return {
        "webhook": {"configured": bool(generic_webhook), "provider": "generic_webhook"},
        "email": {
            "configured": bool(smtp_host and smtp_from) or bool(sendgrid_key and sendgrid_from),
            "default_provider": "smtp" if (smtp_host and smtp_from) else ("sendgrid" if (sendgrid_key and sendgrid_from) else ""),
            "providers": {
                "smtp": bool(smtp_host and smtp_from),
                "sendgrid": bool(sendgrid_key and sendgrid_from),
            },
        },
        "whatsapp": {
            "configured": bool(whatsapp_webhook) or bool(twilio_sid and twilio_token and twilio_from) or bool(meta_token and meta_phone_id),
            "default_provider": "webhook" if whatsapp_webhook else ("twilio" if (twilio_sid and twilio_token and twilio_from) else ("meta_cloud" if (meta_token and meta_phone_id) else "")),
            "providers": {
                "webhook": bool(whatsapp_webhook),
                "twilio": bool(twilio_sid and twilio_token and twilio_from),
                "meta_cloud": bool(meta_token and meta_phone_id),
            },
        },
    }

def parse_recipients(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = str(value).split(",")
    return [str(item).strip() for item in items if str(item).strip()]

def require_text_field(payload: Dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Missing required field: '{field_name}'.")
    return str(value).strip()

def optional_text_field(payload: Dict[str, Any], field_name: str, default: str = "") -> str:
    value = payload.get(field_name, default)
    if value is None:
        return default
    return str(value).strip()

def build_project_team_assignments_from_payload(
    data: LogiTrackData,
    project_id: str,
    organization_id: str,
    payload: Any,
    actor: Optional[UserAccount],
) -> List[ProjectTeamAssignment]:
    if payload in (None, ""):
        return []
    if not isinstance(payload, list):
        raise ValueError("'team_assignments' must be a list.")
    assignments: List[ProjectTeamAssignment] = []
    seen: set[tuple[str, str]] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Each project team assignment must be a JSON object.")
        user_id = optional_text_field(item, "user_id")
        if not user_id:
            raise ValueError("Project team assignment requires 'user_id'.")
        user = find_user_by_id(data, user_id)
        if user is None or user.status == "archived":
            raise ValueError(f"Selected project team user '{user_id}' does not exist.")
        if user.organization_id != organization_id:
            raise ValueError("Project team assignments must stay inside the same organization.")
        role_id = normalize_project_assignment_role(optional_text_field(item, "role", user.role or "executive_viewer"))
        team_id = optional_text_field(item, "team_id", user.team_id)
        if team_id:
            team = find_team_by_id(data, team_id)
            if team is None:
                raise ValueError(f"Selected project team '{team_id}' does not exist.")
            if team.organization_id != organization_id:
                raise ValueError("Project team assignments must stay inside the same organization.")
        key = (user_id, role_id)
        if key in seen:
            continue
        seen.add(key)
        assignments.append(ProjectTeamAssignment(
            id=str(item.get("id") or new_id("projteam")),
            project_id=project_id,
            organization_id=organization_id,
            user_id=user_id,
            role=role_id,
            team_id=team_id,
            assigned_at=optional_text_field(item, "assigned_at", now_iso_utc()),
            assigned_by_user_id=optional_text_field(item, "assigned_by_user_id", actor.id if actor else ""),
            assigned_by_name=optional_text_field(item, "assigned_by_name", actor.full_name if actor else ""),
            status=optional_text_field(item, "status", "active") or "active",
        ))
    return assignments

def build_project_from_payload(
    data: LogiTrackData,
    payload: Dict[str, Any],
    actor: Optional[UserAccount],
    organization_id: str,
    existing: Optional[Project] = None,
) -> Project:
    project_name = require_text_field(payload, "project_name" if "project_name" in payload else "name")
    programme = optional_text_field(payload, "programme", getattr(existing, "programme", ""))
    donor = optional_text_field(payload, "donor", getattr(existing, "donor", ""))
    implementing_partner = optional_text_field(payload, "implementing_partner", optional_text_field(payload, "partner", getattr(existing, "implementing_partner", "")))
    sector = optional_text_field(payload, "sector", getattr(existing, "sector", ""))
    project_code_input = optional_text_field(payload, "project_code", getattr(existing, "project_code", ""))
    if project_code_input:
        project_code = slugify_project_code(project_code_input)
    elif existing is not None and getattr(existing, "project_code", ""):
        project_code = slugify_project_code(existing.project_code)
    else:
        project_code = generate_unique_project_code(data, organization_id, project_name)
    if not project_code:
        project_code = generate_unique_project_code(data, organization_id, project_name)
    duplicate = find_project_by_code(data, organization_id, project_code)
    if duplicate is not None and (existing is None or duplicate.id != existing.id):
        raise ValueError(f"Project code '{project_code}' already exists in this organization.")
    description = optional_text_field(payload, "description", getattr(existing, "description", "") or getattr(existing, "objective", ""))
    country = optional_text_field(payload, "country", getattr(existing, "country", ""))
    province_coverage = normalize_string_list(payload.get("province_coverage")) if "province_coverage" in payload else list(getattr(existing, "province_coverage", []) or [])
    district_coverage = normalize_string_list(payload.get("district_coverage")) if "district_coverage" in payload else list(getattr(existing, "district_coverage", []) or [])
    start_date = parse_optional_date_value(payload.get("start_date"), "start_date") if "start_date" in payload else getattr(existing, "start_date", None)
    end_date = parse_optional_date_value(payload.get("end_date"), "end_date") if "end_date" in payload else getattr(existing, "end_date", None)
    required_text_fields = {
        "programme": programme,
        "donor": donor,
        "implementing_partner": implementing_partner,
        "sector": sector,
        "description": description,
        "country": country,
    }
    for field_name, field_value in required_text_fields.items():
        if not str(field_value or "").strip():
            raise ValueError(f"Missing required field: '{field_name}'.")
    if start_date is None:
        raise ValueError("Missing required field: 'start_date'.")
    if end_date is None:
        raise ValueError("Missing required field: 'end_date'.")
    if end_date < start_date:
        raise ValueError("Project end date must be on or after the start date.")
    project_id = str(payload.get("project_id") or payload.get("id") or (existing.id if existing else new_id("proj")))
    if existing is None and find_project(data, project_id) is not None:
        raise ValueError(f"Project id '{project_id}' already exists.")
    created_at = getattr(existing, "created_at", "") or now_iso_utc()
    current_status = normalize_project_status(getattr(existing, "status", "draft") if existing is not None else "draft", default="draft")
    requested_status = normalize_project_status(optional_text_field(payload, "status", current_status), default=current_status)
    if existing is None and requested_status != "draft":
        raise ValueError("New projects must start in Draft status and move through lifecycle actions afterward.")
    if existing is not None and requested_status != current_status:
        raise ValueError("Project lifecycle changes must be completed through publish, activate, pause, complete, archive, or restore actions.")
    status = current_status if existing is not None else "draft"
    project = Project(
        id=project_id,
        name=project_name,
        objective=optional_text_field(payload, "objective", description),
        organization_id=organization_id,
        project_code=project_code,
        programme=programme,
        donor=donor,
        implementing_partner=implementing_partner,
        sector=sector,
        description=description,
        country=country,
        province_coverage=province_coverage,
        district_coverage=district_coverage,
        start_date=start_date,
        end_date=end_date,
        status=status,
        created_by_user_id=getattr(existing, "created_by_user_id", "") or (actor.id if actor else ""),
        created_by_name=getattr(existing, "created_by_name", "") or (actor.full_name if actor else ""),
        created_at=created_at,
        updated_at=now_iso_utc(),
        published_at=getattr(existing, "published_at", ""),
        status_before_archive=getattr(existing, "status_before_archive", ""),
        team_assignments=list(getattr(existing, "team_assignments", []) or []),
        workspace_shell=dict(getattr(existing, "workspace_shell", {}) or {}),
        cloned_from_project_id=getattr(existing, "cloned_from_project_id", ""),
        indicators=list(getattr(existing, "indicators", []) or []),
    )
    assignments_payload = payload.get("team_assignments")
    if assignments_payload is not None:
        project.team_assignments = build_project_team_assignments_from_payload(
            data,
            project.id,
            organization_id,
            assignments_payload,
            actor,
        )
    return project

def validate_project_publish_readiness(project: Project) -> None:
    if not list(getattr(project, "province_coverage", []) or []):
        raise ValueError("Project publication requires at least one province in geographic coverage.")
    if not list(getattr(project, "district_coverage", []) or []):
        raise ValueError("Project publication requires at least one district in geographic coverage.")
    if not list(getattr(project, "team_assignments", []) or []):
        raise ValueError("Project publication requires at least one assigned project team member.")

def apply_project_lifecycle_transition(
    project: Project,
    target_status: str,
    actor: Optional[UserAccount],
) -> Dict[str, Any]:
    current_status = normalize_project_status(getattr(project, "status", "draft"), default="draft")
    next_status = normalize_project_status(target_status, default=current_status)
    if current_status == "archived" and next_status != "archived":
        raise ValueError("Archived projects must be restored instead of transitioned directly.")
    allowed = PROJECT_LIFECYCLE_TRANSITIONS.get(current_status, set())
    if next_status != current_status and next_status not in allowed:
        raise ValueError(f"Project cannot move from '{current_status}' to '{next_status}'.")
    changes = {"from": current_status, "to": next_status}
    project.status = next_status
    project.updated_at = now_iso_utc()
    if actor is not None and not getattr(project, "created_by_name", ""):
        project.created_by_name = actor.full_name
        project.created_by_user_id = actor.id
    if next_status == "published" and not getattr(project, "published_at", ""):
        project.published_at = now_iso_utc()
    return changes

def derive_username(payload: Dict[str, Any], existing: Optional[UserAccount] = None) -> str:
    username_raw = payload.get("username", existing.username if existing else "")
    if username_raw is not None and str(username_raw).strip():
        return str(username_raw).strip().lower()
    email_value = optional_text_field(payload, "email", existing.email if existing else "").lower()
    if email_value and "@" in email_value:
        return email_value.split("@", 1)[0].strip().lower()
    full_name_value = optional_text_field(payload, "full_name", existing.full_name if existing else "").lower()
    if full_name_value:
        normalized = "".join(ch if ch.isalnum() else "." for ch in full_name_value)
        normalized = ".".join(part for part in normalized.split(".") if part)
        if normalized:
            return normalized
    raise ValueError("Missing required field: 'username' or a valid 'email'.")

def build_location_from_payload(payload: Dict[str, Any]) -> LocationEntry:
    latitude = num(payload.get("latitude"))
    longitude = num(payload.get("longitude"))
    if latitude is None or longitude is None:
        raise ValueError("Location requires valid 'latitude' and 'longitude'.")

    return LocationEntry(
        country=require_text_field(payload, "country"),
        province=require_text_field(payload, "province"),
        district=require_text_field(payload, "district"),
        latitude=float(latitude),
        longitude=float(longitude),
        target_local=num(payload.get("target_local")),
        actual_local=num(payload.get("actual_local")),
        budget_local=num(payload.get("budget_local")),
        currency=optional_text_field(payload, "currency").upper(),
    )

def build_task_from_payload(payload: Dict[str, Any]) -> Task:
    status = normalize_task_status(optional_text_field(payload, "status", "not_started"))
    return Task(
        id=str(payload.get("id") or new_id("task")),
        name=require_text_field(payload, "name"),
        owner=optional_text_field(payload, "owner"),
        due_date=parse_optional_date_value(payload.get("due_date"), "due_date"),
        status=status,
        notes=optional_text_field(payload, "notes"),
        assignee_username=optional_text_field(payload, "assignee_username"),
        assignee_name=optional_text_field(payload, "assignee_name"),
        priority=normalize_choice(optional_text_field(payload, "priority", "medium"), ("low", "medium", "high", "critical"), "medium"),
        progress_pct=float(num(payload.get("progress_pct")) or task_progress_default(status)),
        category=optional_text_field(payload, "category", "implementation").lower() or "implementation",
        linked_indicator_id=optional_text_field(payload, "linked_indicator_id"),
        evidence_placeholders=normalize_string_list(payload.get("evidence_placeholders")),
        activity_log=[item for item in payload.get("activity_log", []) if isinstance(item, dict)] if isinstance(payload.get("activity_log"), list) else [],
        created_at=optional_text_field(payload, "created_at"),
        updated_at=optional_text_field(payload, "updated_at"),
        submitted_at=optional_text_field(payload, "submitted_at"),
        validated_at=optional_text_field(payload, "validated_at"),
        approved_at=optional_text_field(payload, "approved_at"),
    )

def build_indicator_from_payload(
    payload: Dict[str, Any],
    organization_id: str = "",
    project_id: str = "",
) -> Indicator:
    locations_payload = payload.get("locations") or []
    if not isinstance(locations_payload, list):
        raise ValueError("'locations' must be a list.")

    indicator = Indicator(
        id=str(payload.get("id") or new_id("ind")),
        name=require_text_field(payload, "name"),
        unit=optional_text_field(payload, "unit"),
        frequency=optional_text_field(payload, "frequency"),
        direction=normalize_direction(optional_text_field(payload, "direction", "up")),
        level=normalize_level(optional_text_field(payload, "level", "output")),
        target=num(payload.get("target")),
        baseline=num(payload.get("baseline")),
        organization_id=organization_id or optional_text_field(payload, "organization_id"),
        project_id=project_id or optional_text_field(payload, "project_id"),
    )
    for location_payload in locations_payload:
        if not isinstance(location_payload, dict):
            raise ValueError("Each location must be a JSON object.")
        indicator.locations.append(build_location_from_payload(location_payload))
    return indicator

def build_activity_from_payload(payload: Dict[str, Any], project: Project) -> OperationalActivity:
    tasks_payload = payload.get("tasks") or []
    if not isinstance(tasks_payload, list):
        raise ValueError("'tasks' must be a list.")

    linked_ids = normalize_string_list(payload.get("linked_indicator_ids"))
    if not linked_ids:
        raise ValueError("Operational activity must link at least one indicator.")

    project_indicator_ids = {indicator.id for indicator in project.indicators}
    invalid_ids = [indicator_id for indicator_id in linked_ids if indicator_id not in project_indicator_ids]
    if invalid_ids:
        raise ValueError(f"Unknown linked indicator id(s): {', '.join(invalid_ids)}.")

    activity = OperationalActivity(
        id=str(payload.get("id") or new_id("act")),
        name=require_text_field(payload, "name"),
        owner=optional_text_field(payload, "owner"),
        start_date=parse_optional_date_value(payload.get("start_date"), "start_date"),
        due_date=parse_optional_date_value(payload.get("due_date"), "due_date"),
        status=normalize_activity_status(optional_text_field(payload, "status", "planned")),
        linked_indicator_ids=linked_ids,
    )

    for task_payload in tasks_payload:
        if not isinstance(task_payload, dict):
            raise ValueError("Each task must be a JSON object.")
        activity.tasks.append(build_task_from_payload(task_payload))
    return activity

def find_project(data: LogiTrackData, project_id: str) -> Optional[Project]:
    for project in data.projects:
        if project.id == project_id:
            return project
    return None

def find_indicator(project: Project, indicator_id: str) -> Optional[Indicator]:
    for indicator in project.indicators:
        if indicator.id == indicator_id:
            return indicator
    return None

def find_activity(ops: OpsLite, activity_id: str) -> Optional[OperationalActivity]:
    for activity in ops.activities:
        if activity.id == activity_id:
            return activity
    return None

def upsert_indicator_location(indicator: Indicator, location: LocationEntry) -> str:
    location_key = (
        location.country.strip().lower(),
        location.province.strip().lower(),
        location.district.strip().lower(),
    )

    for idx, existing in enumerate(indicator.locations):
        existing_key = (
            existing.country.strip().lower(),
            existing.province.strip().lower(),
            existing.district.strip().lower(),
        )
        if existing_key == location_key:
            indicator.locations[idx] = location
            return "updated"

    indicator.locations.append(location)
    return "created"

def build_api_template() -> Dict[str, Any]:
    # Credential-shaped values in this discovery payload are fictional request
    # examples for disposable local demos, not live account credentials.
    return {
        "project": {
            "name": "Water Access Program",
            "objective": "Improve access to safe water in rural districts.",
            "indicators": [
                {
                    "name": "Households with access to safe water",
                    "unit": "%",
                    "frequency": "monthly",
                    "direction": "up",
                    "level": "outcome",
                    "target": 80,
                    "baseline": 35,
                    "locations": [
                        {
                            "country": "Mozambique",
                            "province": "Nampula",
                            "district": "Mecuburi",
                            "latitude": -14.65,
                            "longitude": 39.32,
                            "target_local": 80,
                            "actual_local": 52,
                            "budget_local": 150000,
                            "currency": "MZN",
                        }
                    ],
                }
            ],
            "activities": [
                {
                    "name": "Install new boreholes",
                    "owner": "Field Team",
                    "start_date": "2026-05-01",
                    "due_date": "2026-06-15",
                    "status": "ongoing",
                    "linked_indicator_ids": ["ind_..."],
                    "tasks": [
                        {
                            "name": "Validate district shortlist",
                            "owner": "M&E Officer",
                            "due_date": "2026-05-20",
                            "status": "doing",
                            "notes": "Need sign-off from PM.",
                        }
                    ],
                }
            ],
        },
        "bulk_import_shape": {
            "projects": [],
            "ops_by_project": {},
            "reporting_records": [],
        },
        "tidy_dataset": {
            "name": "Monthly KPI tidy data",
            "description": "One row per project, KPI, district, and reporting month.",
            "rows": [
                {
                    "project_name": "Water Access Program",
                    "indicator_name": "Households with access to safe water",
                    "reporting_month": "2026-05-01",
                    "province": "Nampula",
                    "district": "Mecuburi",
                    "actual_value": 52,
                    "target_value": 80,
                    "budget_spent": 150000,
                    "status": "ongoing",
                }
            ],
        },
        "reporting_record": {
            "project_name": "Water Access Program",
            "indicator_name": "Households with access to safe water",
            "reporting_period": "2026-05-01",
            "country": "Mozambique",
            "province": "Nampula",
            "district": "Mecuburi",
            "actual_value": 52,
            "target_value": 80,
            "budget_value": 150000,
            "currency": "MZN",
            "status": "ongoing",
            "owner": "M&E Officer",
            "notes": "Monthly submission",
        },
        "semantic_mapping": {
            "name": "Confirmed mapping",
            "status": "confirmed",
            "fields": {
                "project_name": "project_name",
                "indicator_name": "indicator_name",
                "reporting_period": "reporting_month",
                "actual_value": "actual_value",
                "target_value": "target_value",
                "budget_value": "budget_spent",
                "status": "status",
                "province": "province",
                "district": "district",
            },
        },
        "dashboard_template": {
            "name": "Custom Executive Template",
            "description": "Template for management review meetings.",
            "dashboard_type": "project_performance",
            "scope": "custom",
            "filters": ["project_name", "reporting_month", "province"],
            "visuals": [
                {"chart_type": "kpi_cards", "title": "Executive KPIs"},
                {"chart_type": "line_trend", "title": "Trend over reporting month"},
            ],
            "layout": [
                {"widget_id": "visual_1", "visual_index": 0, "chart_type": "kpi_cards", "title": "Executive KPIs", "column_span": 2, "row_span": 1, "section": "summary"},
                {"widget_id": "visual_2", "visual_index": 1, "chart_type": "line_trend", "title": "Trend over reporting month", "column_span": 2, "row_span": 2, "section": "main"},
            ],
            "narrative_sections": ["summary", "risks", "actions"],
            "theme": "studio_default",
        },
        "notification_rule": {
            "name": "Weekly low KPI alert",
            "is_active": True,
            "schedule": "weekly",
            "channel": "email",
            "provider": "sendgrid",
            "min_severity": "high",
            "condition_type": "progress_below",
            "threshold": 60,
            "project_id": "proj_...",
            "recipients": ["pm@example.org"],
        },
        "user_bootstrap": {
            "username": "admin",
            "password": "ChangeMe123!",
            "full_name": "System Administrator",
            "email": "admin@example.org",
            "role": "admin",
        },
        "user_create": {
            "username": "analyst.one",
            "password": "StrongPassword123!",
            "full_name": "Portfolio Analyst",
            "email": "analyst@example.org",
            "role": "analyst",
            "is_active": True,
        },
        "notification_dispatch": {
            "channel": "email | whatsapp | webhook",
            "provider": "smtp | sendgrid | twilio | meta_cloud | webhook",
            "min_severity": "medium",
            "max_items": 20,
            "webhook_url": "https://example.com/webhook",
            "email_to": ["pm@example.org"],
            "whatsapp_to": ["+258840000000"],
        },
    }

# ----------------------------
# BI Export (CSV + KPIs + Bridge)
# ----------------------------
def export_bi_csv(data: LogiTrackData, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    (projects, indicators, indicator_locations, activities, tasks,
     activity_indicator_links,
     kpi_project, kpi_indicator, kpi_district, kpi_workplan) = build_bi_tables(data)

    def write_csv(name: str, rows: List[dict], fieldnames: List[str]):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)

    write_csv("projects.csv", projects, ["project_id", "project_name", "objective"])

    write_csv("indicators.csv", indicators, [
        "indicator_id", "project_id", "indicator_name", "unit", "frequency",
        "direction", "level", "target", "baseline"
    ])

    write_csv("indicator_locations.csv", indicator_locations, [
        "indicator_id", "project_id", "country", "province", "district",
        "latitude", "longitude", "target_local", "actual_local",
        "budget_local", "currency", "progress_pct", "status_canon",
        "has_target", "has_actual", "is_valid_progress"
    ])

    write_csv("activities.csv", activities, [
        "activity_id", "project_id", "activity_name", "owner",
        "start_date", "due_date", "status", "linked_indicator_ids"
    ])

    write_csv("tasks.csv", tasks, [
        "task_id", "project_id", "activity_id", "task_name", "owner",
        "due_date", "status", "notes"
    ])

    write_csv("activity_indicator_links.csv", activity_indicator_links, [
        "project_id", "activity_id", "indicator_id"
    ])

    write_csv("kpi_project.csv", kpi_project, [
        "project_id", "project_name",
        "progress_mean_pct", "progress_weighted_pct",
        "status_mean_canon", "status_weighted_canon",
        "budget_total", "locations_valid_count", "locations_missing_count",
        "indicators_total", "indicators_linked_to_workplan", "indicators_without_workplan",
        "workplan_coverage_pct",
        "activities_total", "activities_open",
        "tasks_total", "tasks_done", "tasks_overdue", "tasks_next_7_days"
    ])

    write_csv("kpi_indicator.csv", kpi_indicator, [
        "project_id", "indicator_id", "indicator_name", "level", "direction",
        "progress_mean_pct", "progress_weighted_pct",
        "status_mean_canon", "status_weighted_canon",
        "district_valid_count", "district_missing_count",
        "budget_total"
    ])

    write_csv("kpi_district.csv", kpi_district, [
        "project_id", "country", "province", "district",
        "progress_mean_pct", "progress_weighted_pct",
        "status_mean_canon", "status_weighted_canon",
        "budget_total", "rows_valid_count", "rows_missing_count"
    ])

    write_csv("kpi_workplan.csv", kpi_workplan, [
        "project_id", "project_name",
        "activities_total", "activities_open",
        "tasks_total", "tasks_done", "tasks_overdue", "tasks_next_7_days",
        "indicators_total", "indicators_linked_to_workplan", "indicators_without_workplan",
        "workplan_coverage_pct"
    ])


def build_health_payload(
    storage: Dict[str, Any],
    runtime_status: Dict[str, Any],
    cors_origins: List[str],
    allow_credentials: bool,
    loaded_data: Optional[LogiTrackData],
    data_error: Optional[str],
) -> Dict[str, Any]:
    channels = notification_channels_status()
    return {
        "ok": data_error is None,
        "system": CONFIG["system_name"],
        "version": CONFIG["version"],
        "data_path": storage["target_path"],
        "data_file_exists": storage["exists"],
        "data_file_valid": data_error is None if storage["exists"] else True,
        "data_error": data_error,
        "storage": storage,
        "cors_origins": cors_origins,
        "cors_allow_credentials": allow_credentials,
        "write_auth_enabled": bool((os.getenv("LOGITRACK_API_KEY", "") or "").strip()),
        "token_auth_enabled": bool(loaded_data.users) if loaded_data else False,
        "auth_bootstrap_required": bool(loaded_data is not None and not loaded_data.users),
        "scheduler_enabled": runtime_status["scheduler"]["enabled"],
        "scheduler_thread_alive": runtime_status["scheduler"]["thread_alive"],
        "scheduler_last_run_at": runtime_status["scheduler"]["last_run_at"],
        "scheduler_last_error": runtime_status["scheduler"]["last_error"],
        "relational_store": runtime_status["relational_store"],
        "repository_domains": runtime_status["repository_domains"],
        "notify_webhook_configured": bool((os.getenv("LOGITRACK_NOTIFY_WEBHOOK_URL", "") or "").strip()),
        "smtp_email_configured": channels["email"]["configured"],
        "whatsapp_configured": channels["whatsapp"]["configured"],
        "tidy_dataset_count": len(loaded_data.tidy_datasets) if loaded_data else 0,
        "reporting_record_count": len(loaded_data.reporting_records) if loaded_data else 0,
        "semantic_mapping_count": len(loaded_data.semantic_mappings) if loaded_data else 0,
        "dashboard_template_count": len(loaded_data.dashboard_templates) if loaded_data else 0,
        "notification_rule_count": len(loaded_data.notification_rules) if loaded_data else 0,
        "user_count": len(loaded_data.users) if loaded_data else 0,
        "audit_event_count": len(loaded_data.audit_events) if loaded_data else 0,
    }

# ----------------------------
# FASTAPI APP (Render-ready)
# ----------------------------
app = None
if FastAPI is not None:
    cors_origins = get_cors_origins()
    allow_credentials = "*" not in cors_origins

    app = FastAPI(
        title=f"{CONFIG['system_name']} API",
        version=CONFIG["version"],
        description="Operational reporting and dashboard API for project, indicator, workplan, and KPI data.",
    )

    if CORSMiddleware is not None:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=allow_credentials,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    app_start_monotonic = time.monotonic()
    runtime_state = {
        "app_started_at": now_iso_utc(),
        "storage_backend": get_storage_backend(),
        "relational_mirror_enabled": relational_mirror_enabled_setting(),
        "repository_domains_enabled": repository_domains_enabled(),
    }
    scheduler_runtime = {"worker": None}

    def _build_runtime_status() -> Dict[str, Any]:
        scheduler_worker = scheduler_runtime["worker"]
        scheduler_status = scheduler_worker.status() if scheduler_worker is not None else {
            "enabled": scheduler_enabled_setting(),
            "interval_seconds": scheduler_interval_seconds_setting(),
            "thread_alive": False,
            "last_run_at": "",
            "last_completed_at": "",
            "last_result": {},
            "last_error": "",
        }
        return {
            **runtime_state,
            "uptime_seconds": max(0, int(time.monotonic() - app_start_monotonic)),
            "storage": safe_get_storage_status(),
            "relational_store": safe_get_relational_store_status(),
            "repository_domains": safe_get_repository_domain_status(),
            "scheduler": scheduler_status,
        }

    def _load_for_api() -> LogiTrackData:
        path = get_data_path()
        try:
            return load_data_from_path(path)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail=f"Invalid JSON in data file '{path}': {exc}") from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to load data from '{path}': {exc}") from exc

    def _save_for_api(data: LogiTrackData) -> str:
        try:
            return save_data_to_path(data)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to save data: {exc}") from exc

    def _resolve_authenticated_user(data: LogiTrackData, x_auth_token: Optional[str]) -> Optional[UserAccount]:
        token = (x_auth_token or "").strip()
        if not token:
            return None
        user = find_user_by_token(data, token)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid or inactive X-Auth-Token.")
        return user

    def _authorize_request(
        data: LogiTrackData,
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
        required_role: str = "analyst",
        required_permission: Optional[str] = None,
        required_permissions: Optional[List[str]] = None,
        require_all_permissions: bool = False,
    ) -> Optional[UserAccount]:
        expected_key = (os.getenv("LOGITRACK_API_KEY", "") or "").strip()
        if expected_key and (x_api_key or "").strip() == expected_key:
            return None

        user = _resolve_authenticated_user(data, x_auth_token)
        if user is not None:
            requested_permissions = normalize_permission_ids(required_permissions or [])
            if required_permission:
                normalized_permission = normalize_permission_id(required_permission)
                if normalized_permission:
                    requested_permissions.append(normalized_permission)
            requested_permissions = normalize_permission_ids(requested_permissions)
            if requested_permissions:
                allowed = (
                    user_has_all_permissions(user, requested_permissions)
                    if require_all_permissions
                    else user_has_any_permission(user, requested_permissions)
                )
                if not allowed:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Missing required permission: {', '.join(requested_permissions)}.",
                    )
            elif not role_allows(user.role, required_role):
                raise HTTPException(status_code=403, detail=f"Role '{user.role}' is not allowed to perform this action.")
            return user

        if expected_key:
            raise HTTPException(status_code=401, detail="Provide a valid X-API-Key or X-Auth-Token.")
        if data.users:
            raise HTTPException(status_code=401, detail="Provide a valid X-Auth-Token.")
        return None

    def _authorize_logical_framework_scope(
        *,
        project_id: str,
        permission: str,
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> LogicalFrameworkActorContext:
        data = _load_for_api()
        actor = _authorize_request(
            data,
            x_api_key,
            x_auth_token,
            required_permission=permission,
        )
        if actor is None:
            raise HTTPException(
                status_code=401,
                detail="Logical Framework endpoints require an authenticated user.",
            )
        project = find_project(data, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        ensure_project_scope(actor, project)
        return LogicalFrameworkActorContext(
            id=actor.id,
            username=actor.username,
            role=actor.role,
            organization_id=actor.organization_id,
        )

    def _append_logical_framework_audit(
        data: LogiTrackData,
        request: LogicalFrameworkAuditRequest,
    ) -> AuditEvent:
        return append_audit_event(
            data,
            action=request.action,
            target_type=request.target_type,
            target_id=request.target_id,
            actor=request.actor,
            endpoint=request.endpoint,
            details=request.details,
        )

    def _logical_framework_unit_of_work() -> SnapshotLogicalFrameworkUnitOfWork:
        return SnapshotLogicalFrameworkUnitOfWork(
            load_snapshot=_load_for_api,
            save_canonical=save_canonical_data_to_path,
            synchronize_projection=lambda data, path: update_relational_store_from_data(
                data, source_path=path
            ),
            append_audit=_append_logical_framework_audit,
        )

    logical_framework_application = LogicalFrameworkApplication(
        _logical_framework_unit_of_work,
        normalize_project_status=normalize_project_status,
    )

    # Notification execution and dispatch orchestration now live in services/notifications.py.

    def _scheduler_job() -> Dict[str, Any]:
        data = load_data_from_path()
        batch_result = notification_service.run_due_rules_batch(
            data=data,
            payload={},
            actor=None,
            endpoint="/scheduler/notification_rules/run_due",
        )
        append_audit_event(
            data,
            action="notification_rule.run_due",
            target_type="notification_rule",
            target_id="scheduler",
            endpoint="/scheduler/notification_rules/run_due",
            details={"checked_rules": batch_result["checked_rules"], "ran_rules": batch_result["ran_rules"]},
        )
        save_data_to_path(data)
        return batch_result

    @app.on_event("startup")
    def on_startup() -> None:
        runtime_state["storage_backend"] = get_storage_backend()
        runtime_state["relational_mirror_enabled"] = relational_mirror_enabled_setting()
        runtime_state["repository_domains_enabled"] = repository_domains_enabled()
        scheduler_worker = scheduler_runtime["worker"]
        if scheduler_worker is None:
            scheduler_runtime["worker"] = RepeatingRuntimeWorker(
                name="LogiTrackScheduler",
                handler=_scheduler_job,
                interval_seconds=scheduler_interval_seconds_setting(),
                enabled=scheduler_enabled_setting(),
            )
            scheduler_worker = scheduler_runtime["worker"]
        else:
            scheduler_worker.configure(
                interval_seconds=scheduler_interval_seconds_setting(),
                enabled=scheduler_enabled_setting(),
            )
        scheduler_worker.start()
        try:
            data = load_data_from_path()
            update_relational_store_from_data(data, source_path=get_storage_target_path())
        except Exception:
            pass

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        scheduler_worker = scheduler_runtime["worker"]
        if scheduler_worker is not None:
            scheduler_worker.stop(timeout=3)

    def _build_payload_for_api() -> Tuple[LogiTrackData, Dict[str, List[dict]]]:
        data = _load_for_api()
        return data, build_bi_payload(data)

    def _build_dataset_payload(data: LogiTrackData, dataset: TidyDataset) -> Dict[str, Any]:
        recommendation = build_dashboard_recommendation_for_rows(dataset.rows, dataset.name)
        history_mapping = infer_reporting_history_mapping(dataset.rows)
        quality = build_tidy_dataset_quality_report(data, dataset)
        return {
            "dataset_id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "source_type": dataset.source_type,
            "created_at": dataset.created_at,
            "updated_at": dataset.updated_at,
            "row_count": len(dataset.rows),
            "columns": tidy_dataset_columns(dataset.rows),
            "dashboard_recommendation": recommendation,
            "history_mapping": history_mapping,
            "quality_overall_score": quality["overall_score"],
        }

    reporting_service = ReportingService(
        ReportingServiceDependencies(
            load_data=_load_for_api,
            save_data=_save_for_api,
            authorize_request=_authorize_request,
            append_audit_event=append_audit_event,
            now_iso_utc=now_iso_utc,
            parse_date_like_value=parse_date_like_value,
            find_project=find_project,
            find_indicator=find_indicator,
            find_tidy_dataset=find_tidy_dataset,
            build_dataset_payload=_build_dataset_payload,
            build_tidy_dataset_notifications=build_tidy_dataset_notifications,
            effective_semantic_mapping=effective_semantic_mapping,
            find_semantic_mapping=find_semantic_mapping,
            build_semantic_mapping_from_payload=build_semantic_mapping_from_payload,
            upsert_semantic_mapping=upsert_semantic_mapping,
            build_tidy_dataset_quality_report=build_tidy_dataset_quality_report,
            build_dataset_narrative_summary=build_dataset_narrative_summary,
            build_dashboard_blueprint=build_dashboard_blueprint,
            infer_reporting_history_mapping=infer_reporting_history_mapping,
            build_dashboard_recommendation_for_rows=build_dashboard_recommendation_for_rows,
            build_tidy_dataset_from_payload=build_tidy_dataset_from_payload,
            upsert_tidy_dataset=upsert_tidy_dataset,
            materialize_reporting_records_from_tidy_dataset=materialize_reporting_records_from_tidy_dataset,
            build_reporting_record_from_payload=build_reporting_record_from_payload,
            upsert_reporting_records=upsert_reporting_records,
            latest_reporting_period=latest_reporting_period,
            reporting_record_to_dict=reporting_record_to_dict,
            build_portfolio_trend_series=build_portfolio_trend_series,
            build_portfolio_narrative_summary=build_portfolio_narrative_summary,
            build_project_trend_series=build_project_trend_series,
            build_project_narrative_summary=build_project_narrative_summary,
            build_indicator_trend_series=build_indicator_trend_series,
            optional_text_field=optional_text_field,
        )
    )

    dashboard_template_service = DashboardTemplateService(
        DashboardTemplateServiceDependencies(
            load_data=_load_for_api,
            save_data=_save_for_api,
            authorize_request=_authorize_request,
            append_audit_event=append_audit_event,
            build_dashboard_recommendation_for_rows=build_dashboard_recommendation_for_rows,
            build_builtin_dashboard_templates=build_builtin_dashboard_templates,
            find_tidy_dataset=find_tidy_dataset,
            find_dashboard_template=find_dashboard_template,
            build_dashboard_template_from_payload=build_dashboard_template_from_payload,
            upsert_dashboard_template=upsert_dashboard_template,
        )
    )

    notification_service = NotificationService(
        NotificationServiceDependencies(
            load_data=_load_for_api,
            save_data=_save_for_api,
            authorize_request=_authorize_request,
            append_audit_event=append_audit_event,
            find_notification_rule=find_notification_rule,
            build_notification_rule_from_payload=build_notification_rule_from_payload,
            upsert_notification_rule=upsert_notification_rule,
            is_notification_rule_due=is_notification_rule_due,
            evaluate_notification_rule=evaluate_notification_rule,
            build_current_notifications=build_current_notifications,
            filter_notifications=filter_notifications,
            optional_text_field=optional_text_field,
            parse_recipients=parse_recipients,
            now_iso_utc=now_iso_utc,
            utc_now=utc_now,
            dispatch_notifications_to_webhook=dispatch_notifications_to_webhook,
            dispatch_notifications_to_email=dispatch_notifications_to_email,
            dispatch_notifications_to_sendgrid_email=dispatch_notifications_to_sendgrid_email,
            dispatch_notifications_to_whatsapp_webhook=dispatch_notifications_to_whatsapp_webhook,
            dispatch_notifications_to_twilio_whatsapp=dispatch_notifications_to_twilio_whatsapp,
            dispatch_notifications_to_meta_whatsapp=dispatch_notifications_to_meta_whatsapp,
            notification_channels_status=notification_channels_status,
        )
    )

    demo_workspace_service = DemoWorkspaceService(
        DemoWorkspaceServiceDependencies(
            load_data=_load_for_api,
            save_data=_save_for_api,
            authorize_request=_authorize_request,
            append_audit_event=append_audit_event,
            from_serializable=from_serializable,
            find_user_by_username=find_user_by_username,
            sanitize_user=sanitize_user,
            build_password_hash=build_password_hash,
            hash_with_sha256=hash_with_sha256,
            new_api_token=new_api_token,
            now_iso_utc=now_iso_utc,
            build_dashboard_summary=build_dashboard_summary,
            build_bi_payload=build_bi_payload,
            build_portfolio_narrative_summary=build_portfolio_narrative_summary,
            build_project_narrative_summary=build_project_narrative_summary,
            build_current_notifications=build_current_notifications,
            filter_notifications=filter_notifications,
            build_tidy_dataset_quality_report=build_tidy_dataset_quality_report,
            build_project_trend_series=build_project_trend_series,
            find_project=find_project,
            find_tidy_dataset=find_tidy_dataset,
            find_dashboard_template=find_dashboard_template,
            parse_date_like_value=parse_date_like_value,
        )
    )

    @app.get("/", include_in_schema=False)
    def home():
        return Response(status_code=307, headers={"Location": "/studio"})

    @app.get("/health")
    def health():
        storage = safe_get_storage_status()
        runtime_status = _build_runtime_status()
        data_error = None
        loaded_data = None
        if storage["exists"]:
            try:
                loaded_data = load_data_from_path(storage["target_path"])
            except Exception as exc:
                data_error = str(exc)
        return build_health_payload(
            storage=storage,
            runtime_status=runtime_status,
            cors_origins=cors_origins,
            allow_credentials=allow_credentials,
            loaded_data=loaded_data,
            data_error=data_error,
        )

    @app.get("/v1/system/runtime")
    def v1_system_runtime():
        return _build_runtime_status()

    @app.get("/v1/system/relational_store")
    def v1_system_relational_store():
        return safe_get_relational_store_status()

    @app.get("/v1/system/repositories")
    def v1_system_repositories():
        return safe_get_repository_domain_status()

    @app.post("/v1/system/relational_sync")
    def v1_system_relational_sync(
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="WORKSPACE_ADMIN")
        result = update_relational_store_from_data(data, source_path=get_storage_target_path())
        append_audit_event(
            data,
            action="system.relational_sync",
            target_type="relational_store",
            target_id=get_relational_store_path(get_storage_target_path()),
            actor=actor,
            endpoint="/v1/system/relational_sync",
            details={"synced": bool(result), "path": get_relational_store_path(get_storage_target_path())},
        )
        _save_for_api(data)
        return {
            "ok": True,
            "sync_result": result,
            "status": safe_get_relational_store_status(),
        }

    @app.get("/v1/data/template")
    def v1_data_template():
        return build_api_template()

    @app.get("/v1/dashboard/summary")
    def v1_dashboard_summary():
        data = _load_for_api()
        return build_dashboard_summary(data)

    @app.post("/v1/auth/bootstrap")
    def v1_auth_bootstrap(payload: Dict[str, Any]):
        data = _load_for_api()
        if data.users:
            raise HTTPException(status_code=409, detail="Bootstrap is only allowed when no users exist.")
        organization_name = optional_text_field(payload, "organization_name", "Blue Delta Consortium") or "Blue Delta Consortium"
        if not data.organizations:
            data.organizations.append(OrganizationAccount(
                id=str(payload.get("organization_id") or "org_blue_delta"),
                organization_name=organization_name,
                status="active",
                subscription_plan=str(payload.get("subscription_plan") or "foundation"),
                created_at=now_iso_utc(),
            ))
        organization_id = str(payload.get("organization_id") or data.organizations[0].id)
        bootstrap_payload = dict(payload)
        bootstrap_payload["organization_id"] = organization_id
        bootstrap_payload["role"] = payload.get("role") or "organization_admin"
        bootstrap_payload["is_active"] = True
        bootstrap_payload["status"] = payload.get("status") or "active"
        if not str(bootstrap_payload.get("username") or "").strip():
            email_value = str(bootstrap_payload.get("email") or "").strip().lower()
            bootstrap_payload["username"] = email_value.split("@", 1)[0] if "@" in email_value else "organization.admin"
        user = build_user_account_from_payload({
            **bootstrap_payload,
        })
        if find_user_by_username(data, user.username) is not None:
            raise HTTPException(status_code=409, detail=f"Username '{user.username}' already exists.")
        if user.email and find_user_by_email(data, user.email) is not None:
            raise HTTPException(status_code=409, detail=f"Email '{user.email}' already exists.")
        token = new_api_token()
        user.api_token_hash = hash_with_sha256(token)
        user.last_login_at = now_iso_utc()
        user.updated_at = now_iso_utc()
        data.users.append(user)
        append_audit_event(
            data,
            action="auth.bootstrap",
            target_type="user",
            target_id=user.id,
            actor=user,
            endpoint="/v1/auth/bootstrap",
            details={"username": user.username, "role": user.role},
        )
        saved_path = _save_for_api(data)
        return {
            "ok": True,
            "saved_to": saved_path,
            "token": token,
            "user": build_user_session_payload(data, user),
        }

    @app.post("/v1/auth/login")
    def v1_auth_login(payload: Dict[str, Any]):
        data = _load_for_api()
        login_email = str(payload.get("email") or "").strip().lower()
        login_username = str(payload.get("username") or "").strip().lower()
        password = require_text_field(payload, "password")
        if not login_email and not login_username:
            raise HTTPException(status_code=400, detail="Provide 'email' and 'password' to sign in.")
        user = find_user_by_email(data, login_email) if login_email else None
        if user is None and login_username:
            user = find_user_by_username(data, login_username)
        if user is None or not user.is_active or not verify_password(password, user.password_salt, user.password_hash):
            append_audit_event(
                data,
                action="auth.login",
                target_type="user",
                target_id=user.id if user else "",
                actor=user if user and user.is_active else None,
                endpoint="/v1/auth/login",
                outcome="failure",
                details={"email": login_email, "username": login_username},
            )
            _save_for_api(data)
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        token = new_api_token()
        user.api_token_hash = hash_with_sha256(token)
        user.last_login_at = now_iso_utc()
        user.updated_at = now_iso_utc()
        append_audit_event(
            data,
            action="auth.login",
            target_type="user",
            target_id=user.id,
            actor=user,
            endpoint="/v1/auth/login",
            details={"username": user.username, "email": user.email, "organization_id": user.organization_id},
        )
        saved_path = _save_for_api(data)
        return {
            "ok": True,
            "saved_to": saved_path,
            "token": token,
            "user": build_user_session_payload(data, user),
        }

    @app.get("/v1/auth/me")
    def v1_auth_me(x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        user = _resolve_authenticated_user(data, x_auth_token)
        if user is None:
            raise HTTPException(status_code=401, detail="Missing X-Auth-Token.")
        organization = organization_for_user(data, user)
        return {
            "ok": True,
            "user": build_user_session_payload(data, user),
            "organization": sanitize_organization(organization) if organization else None,
            "role": normalize_role(user.role),
            "permissions": effective_permissions(user),
        }

    @app.get("/v1/admin/organization")
    def v1_admin_organization(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_ORGANIZATION")
        organization = organization_for_user(data, actor) if actor is not None else (data.organizations[0] if data.organizations else None)
        if organization is None:
            raise HTTPException(status_code=404, detail="Organization not found.")
        return {"ok": True, "organization": sanitize_organization(organization)}

    @app.patch("/v1/admin/organization")
    def v1_admin_update_organization(payload: Dict[str, Any], x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_ORGANIZATION")
        organization = organization_for_user(data, actor) if actor is not None else (data.organizations[0] if data.organizations else None)
        if organization is None:
            raise HTTPException(status_code=404, detail="Organization not found.")
        changes = {}
        for field_name in ("organization_name", "country", "timezone", "default_language", "subscription_plan", "contact_email", "contact_person", "logo_placeholder", "status"):
            if field_name in payload:
                new_value = optional_text_field(payload, field_name, getattr(organization, field_name))
                if getattr(organization, field_name) != new_value:
                    changes[field_name] = {"from": getattr(organization, field_name), "to": new_value}
                    setattr(organization, field_name, new_value)
        organization.updated_at = now_iso_utc()
        append_audit_event(
            data,
            action="organization.updated",
            target_type="organization",
            target_id=organization.id,
            actor=actor,
            endpoint="/v1/admin/organization",
            details={"fields": changes},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "organization": sanitize_organization(organization)}

    @app.get("/v1/admin/users")
    def v1_admin_users(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_USERS")
        users = data.users if actor is None or not actor.organization_id else organization_users(data, actor.organization_id)
        return {"ok": True, "count": len(users), "items": [build_user_session_payload(data, user) for user in users if user.status != "archived"]}

    @app.post("/v1/admin/users")
    def v1_admin_create_user(payload: Dict[str, Any], x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_USERS")
        user_payload = dict(payload or {})
        if actor is not None:
            user_payload["organization_id"] = actor.organization_id
        organization_id = optional_text_field(user_payload, "organization_id", "")
        if actor is not None:
            ensure_organization_scope(actor, organization_id)
        team_id = optional_text_field(user_payload, "team_id", "")
        if team_id:
            team = find_team_by_id(data, team_id)
            if team is None:
                raise HTTPException(status_code=400, detail="Selected team does not exist.")
            ensure_team_scope(actor, team)
        username_value = derive_username(user_payload)
        if find_user_by_username(data, username_value) is not None:
            raise HTTPException(status_code=409, detail=f"Username '{username_value}' already exists.")
        email_value = optional_text_field(user_payload, "email", "").lower()
        email_duplicate = find_user_by_email(data, email_value) if email_value else None
        if email_duplicate is not None:
            raise HTTPException(status_code=409, detail=f"Email '{email_value}' already exists.")
        try:
            user = build_user_account_from_payload(user_payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        action = upsert_user_account(data, user)
        append_audit_event(
            data,
            action="user.created",
            target_type="user",
            target_id=user.id,
            actor=actor,
            endpoint="/v1/admin/users",
            details={"username": user.username, "role": user.role, "team_id": user.team_id, "status": user.status},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "action": action, "saved_to": saved_path, "user": build_user_session_payload(data, user)}

    @app.patch("/v1/admin/users/{user_id}")
    def v1_admin_update_user(user_id: str, payload: Dict[str, Any], x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_USERS")
        existing = find_user_by_id(data, user_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="User not found.")
        ensure_user_scope(actor, existing)
        user_payload = dict(payload or {})
        user_payload["id"] = existing.id
        user_payload["organization_id"] = existing.organization_id
        if "team_id" in user_payload and user_payload.get("team_id"):
            team = find_team_by_id(data, str(user_payload.get("team_id")))
            if team is None:
                raise HTTPException(status_code=400, detail="Selected team does not exist.")
            ensure_team_scope(actor, team)
        username_value = derive_username(user_payload, existing=existing)
        duplicate = find_user_by_username(data, username_value)
        if duplicate is not None and duplicate.id != existing.id:
            raise HTTPException(status_code=409, detail=f"Username '{username_value}' already exists.")
        email_value = optional_text_field(user_payload, "email", existing.email).lower()
        email_duplicate = find_user_by_email(data, email_value) if email_value else None
        if email_duplicate is not None and email_duplicate.id != existing.id:
            raise HTTPException(status_code=409, detail=f"Email '{email_value}' already exists.")
        try:
            user = build_user_account_from_payload(user_payload, existing=existing)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        upsert_user_account(data, user)
        append_audit_event(
            data,
            action="user.updated",
            target_type="user",
            target_id=user.id,
            actor=actor,
            endpoint=f"/v1/admin/users/{user.id}",
            details={"username": user.username, "role": user.role, "team_id": user.team_id, "status": user.status},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "user": build_user_session_payload(data, user)}

    @app.post("/v1/admin/users/{user_id}/suspend")
    def v1_admin_suspend_user(user_id: str, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_USERS")
        user = find_user_by_id(data, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        ensure_user_scope(actor, user)
        user.status = "suspended"
        user.is_active = False
        user.updated_at = now_iso_utc()
        append_audit_event(data, action="user.suspended", target_type="user", target_id=user.id, actor=actor, endpoint=f"/v1/admin/users/{user.id}/suspend", details={"username": user.username})
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "user": build_user_session_payload(data, user)}

    @app.post("/v1/admin/users/{user_id}/reactivate")
    def v1_admin_reactivate_user(user_id: str, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_USERS")
        user = find_user_by_id(data, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        ensure_user_scope(actor, user)
        user.status = "active"
        user.is_active = True
        user.updated_at = now_iso_utc()
        append_audit_event(data, action="user.reactivated", target_type="user", target_id=user.id, actor=actor, endpoint=f"/v1/admin/users/{user.id}/reactivate", details={"username": user.username})
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "user": build_user_session_payload(data, user)}

    @app.post("/v1/admin/users/{user_id}/archive")
    def v1_admin_archive_user(user_id: str, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_USERS")
        user = find_user_by_id(data, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        ensure_user_scope(actor, user)
        user.status = "archived"
        user.is_active = False
        user.updated_at = now_iso_utc()
        append_audit_event(data, action="user.archived", target_type="user", target_id=user.id, actor=actor, endpoint=f"/v1/admin/users/{user.id}/archive", details={"username": user.username})
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "user": build_user_session_payload(data, user)}

    @app.get("/v1/admin/teams")
    def v1_admin_teams(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permissions=["MANAGE_ORGANIZATION", "MANAGE_USERS"])
        teams = data.teams if actor is None or not actor.organization_id else teams_for_organization(data, actor.organization_id)
        return {"ok": True, "count": len(teams), "items": [sanitize_team(data, team) for team in teams if team.status != "archived"]}

    @app.post("/v1/admin/teams")
    def v1_admin_create_team(payload: Dict[str, Any], x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_ORGANIZATION")
        team_payload = dict(payload or {})
        if actor is not None:
            team_payload["organization_id"] = actor.organization_id
        organization_id = optional_text_field(team_payload, "organization_id", "")
        if actor is not None:
            ensure_organization_scope(actor, organization_id)
        team_lead_user_id = optional_text_field(team_payload, "team_lead_user_id", "")
        if team_lead_user_id:
            lead = find_user_by_id(data, team_lead_user_id)
            if lead is None:
                raise HTTPException(status_code=400, detail="Selected team lead does not exist.")
            ensure_user_scope(actor, lead)
        try:
            team = build_team_account_from_payload(team_payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        action = upsert_team_account(data, team)
        member_user_ids = [str(item) for item in payload.get("member_user_ids", [])] if isinstance(payload.get("member_user_ids"), list) else []
        if member_user_ids:
            assign_team_members(data, team.organization_id, team.id, member_user_ids)
        append_audit_event(
            data,
            action="team.created",
            target_type="team",
            target_id=team.id,
            actor=actor,
            endpoint="/v1/admin/teams",
            details={"team_name": team.team_name, "status": team.status, "member_user_ids": member_user_ids},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "action": action, "saved_to": saved_path, "team": sanitize_team(data, team)}

    @app.patch("/v1/admin/teams/{team_id}")
    def v1_admin_update_team(team_id: str, payload: Dict[str, Any], x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_ORGANIZATION")
        existing = find_team_by_id(data, team_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Team not found.")
        ensure_team_scope(actor, existing)
        team_payload = dict(payload or {})
        team_payload["id"] = existing.id
        team_payload["organization_id"] = existing.organization_id
        team_lead_user_id = optional_text_field(team_payload, "team_lead_user_id", existing.team_lead_user_id)
        if team_lead_user_id:
            lead = find_user_by_id(data, team_lead_user_id)
            if lead is None:
                raise HTTPException(status_code=400, detail="Selected team lead does not exist.")
            ensure_user_scope(actor, lead)
        try:
            team = build_team_account_from_payload(team_payload, existing=existing)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        upsert_team_account(data, team)
        member_user_ids = payload.get("member_user_ids")
        if isinstance(member_user_ids, list):
            assign_team_members(data, team.organization_id, team.id, [str(item) for item in member_user_ids])
        append_audit_event(
            data,
            action="team.updated",
            target_type="team",
            target_id=team.id,
            actor=actor,
            endpoint=f"/v1/admin/teams/{team.id}",
            details={"team_name": team.team_name, "status": team.status},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "team": sanitize_team(data, team)}

    @app.post("/v1/admin/teams/{team_id}/archive")
    def v1_admin_archive_team(team_id: str, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_ORGANIZATION")
        team = find_team_by_id(data, team_id)
        if team is None:
            raise HTTPException(status_code=404, detail="Team not found.")
        ensure_team_scope(actor, team)
        team.status = "archived"
        team.updated_at = now_iso_utc()
        append_audit_event(data, action="team.archived", target_type="team", target_id=team.id, actor=actor, endpoint=f"/v1/admin/teams/{team.id}/archive", details={"team_name": team.team_name})
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "team": sanitize_team(data, team)}

    @app.get("/v1/admin/projects")
    def v1_admin_projects(
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_PROJECTS")
        organization_id = actor.organization_id if actor is not None else ""
        projects = projects_for_organization(data, organization_id) if organization_id else list(data.projects)
        assignable_users = eligible_project_team_users(data, organization_id) if organization_id else list(data.users)
        visible_teams = teams_for_organization(data, organization_id) if organization_id else list(data.teams)
        items = [sanitize_project(data, project) for project in projects]
        items.sort(key=lambda item: ((item.get("status") or ""), (item.get("project_name") or "").lower()))
        return {
            "ok": True,
            "count": len(items),
            "summary": project_registry_summary(projects),
            "items": items,
            "assignable_users": [build_user_session_payload(data, user) for user in assignable_users],
            "teams": [sanitize_team(data, team) for team in visible_teams if team.status != "archived"],
            "role_options": project_team_role_options(),
            "status_options": ["draft", "published", "active", "paused", "completed", "archived"],
        }

    @app.post("/v1/admin/projects")
    def v1_admin_create_project(
        payload: Dict[str, Any],
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_PROJECTS")
        organization_id = actor.organization_id if actor is not None else optional_text_field(payload, "organization_id", "")
        if actor is not None:
            ensure_organization_scope(actor, organization_id)
        try:
            project = build_project_from_payload(data, payload or {}, actor, organization_id, existing=None)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        data.projects.append(project)
        append_audit_event(
            data,
            action="project.created",
            target_type="project",
            target_id=project.id,
            actor=actor,
            endpoint="/v1/admin/projects",
            details={"project_code": project.project_code, "status": project.status, "team_assignments": len(project.team_assignments)},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "project": sanitize_project(data, project)}

    @app.patch("/v1/admin/projects/{project_id}")
    def v1_admin_update_project(
        project_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_PROJECTS")
        existing = find_project(data, project_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        ensure_project_scope(actor, existing)
        try:
            project = build_project_from_payload(data, {**(payload or {}), "id": existing.id}, actor, existing.organization_id, existing=existing)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        for idx, candidate in enumerate(data.projects):
            if candidate.id == existing.id:
                data.projects[idx] = project
                break
        append_audit_event(
            data,
            action="project.updated",
            target_type="project",
            target_id=project.id,
            actor=actor,
            endpoint=f"/v1/admin/projects/{project.id}",
            details={"project_code": project.project_code, "fields": sorted((payload or {}).keys())},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "project": sanitize_project(data, project)}

    @app.post("/v1/admin/projects/{project_id}/publish")
    def v1_admin_publish_project(
        project_id: str,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_PROJECTS")
        project = find_project(data, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        ensure_project_scope(actor, project)
        try:
            validate_project_publish_readiness(project)
            apply_project_lifecycle_transition(project, "published", actor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        project.workspace_shell = build_project_workspace_shell(project, actor)
        append_audit_event(
            data,
            action="project.published",
            target_type="project",
            target_id=project.id,
            actor=actor,
            endpoint=f"/v1/admin/projects/{project.id}/publish",
            details={"project_code": project.project_code, "workspace_containers": len(project.workspace_shell.get("containers", []))},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "project": sanitize_project(data, project)}

    @app.post("/v1/admin/projects/{project_id}/activate")
    def v1_admin_activate_project(
        project_id: str,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_PROJECTS")
        project = find_project(data, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        ensure_project_scope(actor, project)
        try:
            apply_project_lifecycle_transition(project, "active", actor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not project.workspace_shell:
            project.workspace_shell = build_project_workspace_shell(project, actor)
        append_audit_event(
            data,
            action="project.activated",
            target_type="project",
            target_id=project.id,
            actor=actor,
            endpoint=f"/v1/admin/projects/{project.id}/activate",
            details={"project_code": project.project_code},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "project": sanitize_project(data, project)}

    @app.post("/v1/admin/projects/{project_id}/deactivate")
    def v1_admin_deactivate_project(
        project_id: str,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_PROJECTS")
        project = find_project(data, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        ensure_project_scope(actor, project)
        try:
            apply_project_lifecycle_transition(project, "paused", actor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        append_audit_event(
            data,
            action="project.paused",
            target_type="project",
            target_id=project.id,
            actor=actor,
            endpoint=f"/v1/admin/projects/{project.id}/deactivate",
            details={"project_code": project.project_code},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "project": sanitize_project(data, project)}

    @app.post("/v1/admin/projects/{project_id}/complete")
    def v1_admin_complete_project(
        project_id: str,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_PROJECTS")
        project = find_project(data, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        ensure_project_scope(actor, project)
        try:
            apply_project_lifecycle_transition(project, "completed", actor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        append_audit_event(
            data,
            action="project.completed",
            target_type="project",
            target_id=project.id,
            actor=actor,
            endpoint=f"/v1/admin/projects/{project.id}/complete",
            details={"project_code": project.project_code},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "project": sanitize_project(data, project)}

    @app.post("/v1/admin/projects/{project_id}/archive")
    def v1_admin_archive_project(
        project_id: str,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_PROJECTS")
        project = find_project(data, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        ensure_project_scope(actor, project)
        current_status = normalize_project_status(project.status, default="draft")
        if current_status == "archived":
            raise HTTPException(status_code=400, detail="Project is already archived.")
        project.status_before_archive = current_status
        project.status = "archived"
        project.updated_at = now_iso_utc()
        append_audit_event(
            data,
            action="project.archived",
            target_type="project",
            target_id=project.id,
            actor=actor,
            endpoint=f"/v1/admin/projects/{project.id}/archive",
            details={"project_code": project.project_code, "restorable_status": project.status_before_archive},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "project": sanitize_project(data, project)}

    @app.post("/v1/admin/projects/{project_id}/restore")
    def v1_admin_restore_project(
        project_id: str,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_PROJECTS")
        project = find_project(data, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        ensure_project_scope(actor, project)
        if normalize_project_status(project.status, default="draft") != "archived":
            raise HTTPException(status_code=400, detail="Project is not archived.")
        restored_status = normalize_project_status(project.status_before_archive or "draft", default="draft")
        project.status = restored_status
        project.status_before_archive = ""
        project.updated_at = now_iso_utc()
        append_audit_event(
            data,
            action="project.restored",
            target_type="project",
            target_id=project.id,
            actor=actor,
            endpoint=f"/v1/admin/projects/{project.id}/restore",
            details={"project_code": project.project_code, "restored_to": restored_status},
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "project": sanitize_project(data, project)}

    @app.post("/v1/admin/projects/{project_id}/clone")
    def v1_admin_clone_project(
        project_id: str,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_PROJECTS")
        source = find_project(data, project_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        ensure_project_scope(actor, source)
        cloned_id = new_id("proj")
        cloned_code = generate_unique_project_code(data, source.organization_id, f"{source.project_code or source.name}-COPY")
        cloned = Project(
            id=cloned_id,
            name=f"{source.name} Copy",
            objective=source.objective,
            organization_id=source.organization_id,
            project_code=cloned_code,
            programme=source.programme,
            donor=source.donor,
            implementing_partner=source.implementing_partner,
            sector=source.sector,
            description=source.description,
            country=source.country,
            province_coverage=list(source.province_coverage or []),
            district_coverage=list(source.district_coverage or []),
            start_date=source.start_date,
            end_date=source.end_date,
            status="draft",
            created_by_user_id=actor.id if actor else "",
            created_by_name=actor.full_name if actor else "",
            created_at=now_iso_utc(),
            updated_at=now_iso_utc(),
            published_at="",
            status_before_archive="",
            team_assignments=[
                ProjectTeamAssignment(
                    id=new_id("projteam"),
                    project_id=cloned_id,
                    organization_id=source.organization_id,
                    user_id=item.user_id,
                    role=item.role,
                    team_id=item.team_id,
                    assigned_at=now_iso_utc(),
                    assigned_by_user_id=actor.id if actor else "",
                    assigned_by_name=actor.full_name if actor else "",
                    status=item.status or "active",
                )
                for item in source.team_assignments
            ],
            workspace_shell={},
            cloned_from_project_id=source.id,
            indicators=[],
        )
        data.projects.append(cloned)
        try:
            source_repository = SnapshotLogicalFrameworkRepository(
                data,
                LogicalFrameworkScope(source.organization_id, source.id),
            )
            destination_repository = SnapshotLogicalFrameworkRepository(
                data,
                LogicalFrameworkScope(cloned.organization_id, cloned.id),
            )
            logical_framework_clone = LogicalFrameworkService(
                destination_repository
            ).clone_hierarchy(source_repository)
        except LogicalFrameworkValidationError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Project clone could not copy the Logical Framework: {exc}",
            ) from exc
        append_audit_event(
            data,
            action="project.cloned",
            target_type="project",
            target_id=cloned.id,
            actor=actor,
            endpoint=f"/v1/admin/projects/{source.id}/clone",
            details={
                "source_project_id": source.id,
                "project_code": cloned.project_code,
                "logical_framework_results_cloned": len(logical_framework_clone["results"]),
                "logical_framework_indicator_links_cloned": logical_framework_clone["indicator_links_cloned"],
            },
        )
        saved_path = _save_for_api(data)
        return {"ok": True, "saved_to": saved_path, "project": sanitize_project(data, cloned)}

    @app.get("/v1/admin/permissions")
    def v1_admin_permissions(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        _authorize_request(data, x_api_key, x_auth_token, required_permissions=["MANAGE_ORGANIZATION", "MANAGE_USERS", "VIEW_AUDIT_LOG"])
        role_cards = []
        for role_id, permissions in ROLE_PERMISSION_TEMPLATES.items():
            role_cards.append({
                "role_id": role_id,
                "role_label": role_label(role_id),
                "permissions": normalize_permission_ids(permissions),
            })
        return {
            "ok": True,
            "groups": permission_groups_payload(),
            "roles": role_cards,
            "catalog": [
                {
                    "id": permission_id,
                    "label": metadata.get("label", permission_id.replace("_", " ").title()),
                    "scope": metadata.get("scope", ""),
                }
                for permission_id, metadata in PERMISSION_CATALOG.items()
            ],
        }

    @app.get("/v1/admin/audit")
    def v1_admin_audit(
        limit: int = 200,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_username: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search: Optional[str] = None,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="VIEW_AUDIT_LOG")
        events = list(reversed(data.audit_events))
        if actor is not None and actor.organization_id:
            events = [item for item in events if not item.organization_id or item.organization_id == actor.organization_id]
        if action:
            events = [item for item in events if item.action == action]
        if actor_id:
            events = [item for item in events if item.actor_id == actor_id]
        if actor_username:
            target_username = str(actor_username).strip().lower()
            events = [item for item in events if str(item.actor_username or "").strip().lower() == target_username]
        from_bound = normalize_datetime_utc(date_from) if date_from else None
        to_bound = normalize_datetime_utc(date_to) if date_to else None
        if from_bound is not None:
            events = [item for item in events if (normalize_datetime_utc(item.occurred_at) or UTC_DATETIME_MIN) >= from_bound]
        if to_bound is not None:
            events = [item for item in events if (normalize_datetime_utc(item.occurred_at) or UTC_DATETIME_MAX) <= to_bound]
        if search:
            search_text = str(search).strip().lower()
            events = [
                item
                for item in events
                if search_text in str(item.action or "").lower()
                or search_text in str(item.actor_username or "").lower()
                or search_text in str(item.target_type or "").lower()
                or search_text in str(item.target_id or "").lower()
                or search_text in json.dumps(item.details or {}, ensure_ascii=False).lower()
            ]
        items = []
        for item in events[:max(1, min(limit, 1000))]:
            audit_actor = find_audit_actor(data, item)
            items.append({
                **asdict(item),
                "actor_full_name": audit_actor.full_name if audit_actor else item.actor_username,
            })
        return {"ok": True, "count": len(events), "items": items}

    @app.get("/v1/users")
    def v1_users(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_USERS")
        users = data.users if actor is None or not actor.organization_id else organization_users(data, actor.organization_id)
        return [
            build_user_session_payload(data, user)
            for user in users
        ]

    @app.post("/v1/users")
    def v1_save_user(payload: Dict[str, Any], x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_USERS")
        existing = find_user_by_id(data, str(payload.get("id"))) if payload.get("id") else None
        user_payload = dict(payload)
        if actor is not None:
            if existing is not None:
                ensure_user_scope(actor, existing)
                user_payload["organization_id"] = existing.organization_id
            else:
                user_payload["organization_id"] = actor.organization_id
        username_value = derive_username(user_payload, existing=existing)
        if existing is None and find_user_by_username(data, username_value) is not None:
            raise HTTPException(status_code=409, detail=f"Username '{username_value}' already exists.")
        if existing is not None:
            duplicate = find_user_by_username(data, username_value)
            if duplicate is not None and duplicate.id != existing.id:
                raise HTTPException(status_code=409, detail=f"Username '{username_value}' already exists.")
        email_value = str(user_payload.get("email", existing.email if existing else "")).strip().lower()
        email_duplicate = find_user_by_email(data, email_value) if email_value else None
        if email_duplicate is not None and (existing is None or email_duplicate.id != existing.id):
            raise HTTPException(status_code=409, detail=f"Email '{email_value}' already exists.")
        team_id = optional_text_field(user_payload, "team_id", existing.team_id if existing else "")
        if team_id:
            team = find_team_by_id(data, team_id)
            if team is None:
                raise HTTPException(status_code=400, detail="Selected team does not exist.")
            ensure_team_scope(actor, team)
        try:
            user = build_user_account_from_payload(user_payload, existing=existing)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        action = upsert_user_account(data, user)
        append_audit_event(
            data,
            action=f"user.{action}",
            target_type="user",
            target_id=user.id,
            actor=actor,
            endpoint="/v1/users",
            details={"username": user.username, "role": user.role, "team_id": user.team_id, "is_active": user.is_active},
        )
        saved_path = _save_for_api(data)
        return {
            "ok": True,
            "action": action,
            "saved_to": saved_path,
            "user": build_user_session_payload(data, user),
        }

    @app.get("/v1/audit_events")
    def v1_audit_events(
        limit: int = 200,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        outcome: Optional[str] = None,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="VIEW_AUDIT_LOG")
        events = list(reversed(data.audit_events))
        if actor is not None and actor.organization_id:
            events = [item for item in events if not item.organization_id or item.organization_id == actor.organization_id]
        if action:
            events = [item for item in events if item.action == action]
        if target_type:
            events = [item for item in events if item.target_type == target_type]
        if outcome:
            events = [item for item in events if item.outcome == outcome]
        return {
            "count": len(events),
            "items": [
                {
                    **asdict(item),
                    "actor_full_name": (find_audit_actor(data, item).full_name if find_audit_actor(data, item) else item.actor_username),
                }
                for item in events[:max(1, min(limit, 1000))]]
        }

    @app.get("/studio", response_class=HTMLResponse)
    def studio():
        studio_path = Path(__file__).with_name("logitrack_studio.html")
        if not studio_path.exists():
            raise HTTPException(status_code=404, detail="Studio UI file not found.")
        return studio_path.read_text(encoding="utf-8")

    @app.get("/favicon.ico")
    def favicon():
        icon_svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
            "<rect width='64' height='64' rx='16' fill='#0f766e'/>"
            "<path d='M18 46V18h8v20h20v8H18z' fill='white'/>"
            "</svg>"
        )
        return Response(content=icon_svg, media_type="image/svg+xml")

    register_reporting_routes(
        app,
        reporting_service,
        header_factory=Header,
        http_exception_cls=HTTPException,
    )
    register_logical_framework_routes(
        app,
        LogicalFrameworkRouteDependencies(
            authorize_scope=_authorize_logical_framework_scope,
            application=logical_framework_application,
        ),
        header_factory=Header,
        http_exception_cls=HTTPException,
    )
    register_dashboard_template_routes(
        app,
        dashboard_template_service,
        header_factory=Header,
        http_exception_cls=HTTPException,
    )
    register_notification_routes(
        app,
        notification_service,
        header_factory=Header,
        http_exception_cls=HTTPException,
    )
    register_demo_routes(
        app,
        demo_workspace_service,
        header_factory=Header,
        http_exception_cls=HTTPException,
    )

    @app.get("/v1/projects")
    def v1_projects():
        _, payload = _build_payload_for_api()
        return payload["projects"]

    @app.get("/v1/indicators")
    def v1_indicators():
        _, payload = _build_payload_for_api()
        return payload["indicators"]

    @app.get("/v1/indicator_locations")
    def v1_indicator_locations():
        _, payload = _build_payload_for_api()
        return payload["indicator_locations"]

    @app.get("/v1/activities")
    def v1_activities():
        _, payload = _build_payload_for_api()
        return payload["activities"]

    @app.get("/v1/tasks")
    def v1_tasks():
        _, payload = _build_payload_for_api()
        return payload["tasks"]

    @app.get("/v1/activity_indicator_links")
    def v1_links():
        _, payload = _build_payload_for_api()
        return payload["activity_indicator_links"]

    @app.get("/v1/kpi/project")
    def v1_kpi_project():
        _, payload = _build_payload_for_api()
        return payload["kpi_project"]

    @app.get("/v1/kpi/indicator")
    def v1_kpi_indicator():
        _, payload = _build_payload_for_api()
        return payload["kpi_indicator"]

    @app.get("/v1/kpi/district")
    def v1_kpi_district():
        _, payload = _build_payload_for_api()
        return payload["kpi_district"]

    @app.get("/v1/kpi/workplan")
    def v1_kpi_workplan():
        _, payload = _build_payload_for_api()
        return payload["kpi_workplan"]

    @app.get("/v1/projects/{project_id}/dashboard")
    def v1_project_dashboard(project_id: str):
        data, payload = _build_payload_for_api()
        project = find_project(data, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

        project_row = next((row for row in payload["projects"] if row["project_id"] == project_id), None)
        project_kpi = next((row for row in payload["kpi_project"] if row["project_id"] == project_id), None)
        workplan_kpi = next((row for row in payload["kpi_workplan"] if row["project_id"] == project_id), None)

        return {
            "project": project_row,
            "kpi_project": project_kpi,
            "kpi_indicator": [row for row in payload["kpi_indicator"] if row["project_id"] == project_id],
            "kpi_district": [row for row in payload["kpi_district"] if row["project_id"] == project_id],
            "kpi_workplan": workplan_kpi,
            "activities": [row for row in payload["activities"] if row["project_id"] == project_id],
            "tasks": [row for row in payload["tasks"] if row["project_id"] == project_id],
            "trend_series": build_project_trend_series(data, project_id),
            "narrative": build_project_narrative_summary(data, project_id),
            "reporting_records": [
                reporting_record_to_dict(record, data)
                for record in sorted(
                    [record for record in data.reporting_records if record.project_id == project_id],
                    key=lambda record: normalize_utc_datetime(record.reporting_period) or UTC_DATETIME_MIN,
                    reverse=True,
                )[:20]
            ],
            "notifications": [
                item for item in build_current_notifications(data)
                if item.get("context", {}).get("project_id") == project_id or item.get("source_id") == project_id
            ],
        }

    @app.post("/v1/data/import")
    def v1_data_import(
        payload: Dict[str, Any],
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        current_data = _load_for_api()
        actor = _authorize_request(current_data, x_api_key, x_auth_token, required_permission="WORKSPACE_ADMIN")
        try:
            data = from_serializable(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid import payload: {exc}") from exc

        append_audit_event(
            data,
            action="data.import",
            target_type="workspace_data",
            target_id="full_import",
            actor=actor,
            endpoint="/v1/data/import",
            details={"projects": len(data.projects), "datasets": len(data.tidy_datasets), "users": len(data.users)},
        )
        saved_path = _save_for_api(data)
        summary = build_dashboard_summary(data)
        return {
            "ok": True,
            "saved_to": saved_path,
            "counts": summary["counts"],
        }

    @app.post("/v1/projects")
    def v1_create_project(
        payload: Dict[str, Any],
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_PROJECTS")
        indicators_payload = payload.get("indicators") or []
        activities_payload = payload.get("activities") or []

        if not isinstance(indicators_payload, list):
            raise HTTPException(status_code=400, detail="'indicators' must be a list.")
        if not isinstance(activities_payload, list):
            raise HTTPException(status_code=400, detail="'activities' must be a list.")

        project = Project(
            id=str(payload.get("id") or new_id("proj")),
            name=require_text_field(payload, "name"),
            objective=optional_text_field(payload, "objective"),
            organization_id=getattr(actor, "organization_id", "") if actor else "",
            project_code=generate_unique_project_code(data, getattr(actor, "organization_id", "") if actor else "", optional_text_field(payload, "project_code", require_text_field(payload, "name"))),
            programme=optional_text_field(payload, "programme"),
            donor=optional_text_field(payload, "donor"),
            implementing_partner=optional_text_field(payload, "implementing_partner", optional_text_field(payload, "partner")),
            sector=optional_text_field(payload, "sector"),
            description=optional_text_field(payload, "description", optional_text_field(payload, "objective")),
            country=optional_text_field(payload, "country"),
            province_coverage=normalize_string_list(payload.get("province_coverage")) if "province_coverage" in payload else [],
            district_coverage=normalize_string_list(payload.get("district_coverage")) if "district_coverage" in payload else [],
            start_date=parse_optional_date_value(payload.get("start_date"), "start_date") if "start_date" in payload else None,
            end_date=parse_optional_date_value(payload.get("end_date"), "end_date") if "end_date" in payload else None,
            status=normalize_project_status(optional_text_field(payload, "status", "active"), default="active"),
            created_by_user_id=actor.id if actor else "",
            created_by_name=actor.full_name if actor else "",
            created_at=now_iso_utc(),
            updated_at=now_iso_utc(),
        )

        if find_project(data, project.id) is not None:
            raise HTTPException(status_code=409, detail=f"Project id '{project.id}' already exists.")

        try:
            for indicator_payload in indicators_payload:
                if not isinstance(indicator_payload, dict):
                    raise ValueError("Each indicator must be a JSON object.")
                indicator = build_indicator_from_payload(
                    indicator_payload,
                    organization_id=project.organization_id,
                    project_id=project.id,
                )
                if find_indicator(project, indicator.id) is not None:
                    raise ValueError(f"Indicator id '{indicator.id}' is duplicated in the project payload.")
                project.indicators.append(indicator)

            data.projects.append(project)
            if activities_payload:
                ops = ensure_ops(data, project.id)
                for activity_payload in activities_payload:
                    if not isinstance(activity_payload, dict):
                        raise ValueError("Each activity must be a JSON object.")
                    activity = build_activity_from_payload(activity_payload, project)
                    if find_activity(ops, activity.id) is not None:
                        raise ValueError(f"Activity id '{activity.id}' is duplicated in the project payload.")
                    ops.activities.append(activity)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        append_audit_event(
            data,
            action="project.created",
            target_type="project",
            target_id=project.id,
            actor=actor,
            endpoint="/v1/projects",
            details={"name": project.name, "indicators_total": len(project.indicators), "activities_total": len(data.ops_by_project.get(project.id, OpsLite()).activities)},
        )
        saved_path = _save_for_api(data)
        return {
            "ok": True,
            "saved_to": saved_path,
            "project_id": project.id,
            "indicator_ids": [indicator.id for indicator in project.indicators],
            "activities_total": len(data.ops_by_project.get(project.id, OpsLite()).activities),
        }

    @app.post("/v1/projects/{project_id}/indicators")
    def v1_add_indicator(
        project_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="EDIT_INDICATORS")
        project = find_project(data, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

        try:
            indicator = build_indicator_from_payload(
                payload,
                organization_id=project.organization_id,
                project_id=project.id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if find_indicator(project, indicator.id) is not None:
            raise HTTPException(status_code=409, detail=f"Indicator id '{indicator.id}' already exists in project '{project_id}'.")

        project.indicators.append(indicator)
        append_audit_event(
            data,
            action="indicator.created",
            target_type="indicator",
            target_id=indicator.id,
            actor=actor,
            endpoint=f"/v1/projects/{project_id}/indicators",
            details={"project_id": project_id, "name": indicator.name},
        )
        saved_path = _save_for_api(data)
        return {
            "ok": True,
            "saved_to": saved_path,
            "project_id": project_id,
            "indicator_id": indicator.id,
            "locations_total": len(indicator.locations),
        }

    @app.post("/v1/projects/{project_id}/indicators/{indicator_id}/locations")
    def v1_upsert_indicator_location(
        project_id: str,
        indicator_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="EDIT_INDICATORS")
        project = find_project(data, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

        indicator = find_indicator(project, indicator_id)
        if indicator is None:
            raise HTTPException(status_code=404, detail=f"Indicator '{indicator_id}' not found in project '{project_id}'.")

        try:
            location = build_location_from_payload(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        action = upsert_indicator_location(indicator, location)
        append_audit_event(
            data,
            action=f"indicator_location.{action}",
            target_type="indicator_location",
            target_id=f"{project_id}:{indicator_id}:{location.district}",
            actor=actor,
            endpoint=f"/v1/projects/{project_id}/indicators/{indicator_id}/locations",
            details={"country": location.country, "province": location.province, "district": location.district},
        )
        saved_path = _save_for_api(data)
        return {
            "ok": True,
            "action": action,
            "saved_to": saved_path,
            "project_id": project_id,
            "indicator_id": indicator_id,
            "district": location.district,
        }

    @app.post("/v1/projects/{project_id}/activities")
    def v1_add_activity(
        project_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_WORKPLAN")
        project = find_project(data, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

        try:
            activity = build_activity_from_payload(payload, project)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        ops = ensure_ops(data, project_id)
        if find_activity(ops, activity.id) is not None:
            raise HTTPException(status_code=409, detail=f"Activity id '{activity.id}' already exists in project '{project_id}'.")

        ops.activities.append(activity)
        append_audit_event(
            data,
            action="activity.created",
            target_type="activity",
            target_id=activity.id,
            actor=actor,
            endpoint=f"/v1/projects/{project_id}/activities",
            details={"project_id": project_id, "name": activity.name, "tasks_total": len(activity.tasks)},
        )
        saved_path = _save_for_api(data)
        return {
            "ok": True,
            "saved_to": saved_path,
            "project_id": project_id,
            "activity_id": activity.id,
            "tasks_total": len(activity.tasks),
        }

    @app.post("/v1/projects/{project_id}/activities/{activity_id}/tasks")
    def v1_add_task(
        project_id: str,
        activity_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    ):
        data = _load_for_api()
        actor = _authorize_request(data, x_api_key, x_auth_token, required_permission="ASSIGN_TASKS")
        project = find_project(data, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

        ops = ensure_ops(data, project_id)
        activity = find_activity(ops, activity_id)
        if activity is None:
            raise HTTPException(status_code=404, detail=f"Activity '{activity_id}' not found in project '{project_id}'.")

        try:
            task = build_task_from_payload(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if any(existing.id == task.id for existing in activity.tasks):
            raise HTTPException(status_code=409, detail=f"Task id '{task.id}' already exists in activity '{activity_id}'.")

        activity.tasks.append(task)
        append_audit_event(
            data,
            action="task.created",
            target_type="task",
            target_id=task.id,
            actor=actor,
            endpoint=f"/v1/projects/{project_id}/activities/{activity_id}/tasks",
            details={"project_id": project_id, "activity_id": activity_id, "name": task.name, "status": task.status},
        )
        saved_path = _save_for_api(data)
        return {
            "ok": True,
            "saved_to": saved_path,
            "project_id": project_id,
            "activity_id": activity_id,
            "task_id": task.id,
        }

# ----------------------------
# LOCAL CLI MAIN APP (NO FEATURES REMOVED)
# ----------------------------
def main():
    global REPORT_LANG
    REPORT_LANG = select_language()

    data = LogiTrackData()
    default_path = get_storage_target_path()

    while True:
        print(f"\n{tr('menu_title', name=CONFIG['system_name'], version=CONFIG['version'])}")
        print(tr("menu_1"))
        print(tr("menu_2"))
        print(tr("menu_3"))
        print(tr("menu_4"))
        print(tr("menu_5"))
        print(tr("menu_6"))
        print(tr("menu_7"))
        print(tr("menu_0"))

        choice = input(f"{tr('choice')}: ").strip()

        if choice == "1":
            p = create_project()
            data.projects.append(p)
            print(tr("project_created"))

        elif choice == "2":
            p = pick_project(data)
            if not p:
                continue
            ops = ensure_ops(data, p.id)

            while True:
                print(f"\n{tr('ops_title', project=p.name)}")
                print(tr("ops_1"))
                print(tr("ops_2"))
                print(tr("ops_3"))
                print(tr("ops_4"))
                print(tr("ops_0"))

                c2 = input(f"{tr('choice')}: ").strip()

                if c2 == "1":
                    list_operational_activities(ops)
                elif c2 == "2":
                    create_operational_activity(p, ops)
                elif c2 == "3":
                    act = pick_activity(ops)
                    if act:
                        add_task_to_activity(act)
                elif c2 == "4":
                    act = pick_activity(ops)
                    if act:
                        update_task_status(act)
                elif c2 == "0":
                    break
                else:
                    print(tr("invalid_option"))

        elif choice == "3":
            p = pick_project(data)
            if not p:
                continue
            ops = ensure_ops(data, p.id)
            report_project_basic(p, ops)

        elif choice == "4":
            path = input(f"{tr('path_save', path=default_path)}: ").strip() or default_path
            save_data_to_path(data, path)
            print(f"{tr('saved_to')}: {path}")

        elif choice == "5":
            path = input(f"{tr('path_load', path=default_path)}: ").strip() or default_path
            if get_storage_backend() == "json" and not os.path.exists(path):
                print(tr("data_file_missing", path=path))
                continue
            data = load_data_from_path(path)
            print(f"{tr('loaded_from')}: {path}")

        elif choice == "6":
            default_export = os.path.join(os.getcwd(), "logitrack_bi_export")
            out_dir = input(f"{tr('export_dir', path=default_export)}: ").strip() or default_export
            export_bi_csv(data, out_dir)
            print(f"{tr('export_done')}: {out_dir}")

        elif choice == "7":
            # Local usage only: run uvicorn manually if you want.
            # Render will start the app via uvicorn command.
            print("Para cloud (Render), use o Start Command do Render com uvicorn (ver instruções).")
            print("Para teste local da API, corre no terminal:")
            print("  pip install fastapi uvicorn")
            print("  uvicorn logitrack_rc_v4_4_api:app --host 127.0.0.1 --port 8000")

        elif choice == "0":
            break

        else:
            print(tr("invalid_option"))

if __name__ == "__main__":
    main()
