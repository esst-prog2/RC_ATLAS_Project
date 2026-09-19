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
from typing import List, Optional, Dict, Tuple
from statistics import mean
from datetime import datetime, date, timedelta
import json
import os
import csv
from pathlib import Path

# ----------------------------
# OPTIONAL API IMPORTS
# ----------------------------
try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except Exception:
    FastAPI = None
    CORSMiddleware = None

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

# ----------------------------
# I18N (PT/EN)
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
    c = input(f"{tr('choice')}: ").strip()
    if c == "2":
        return "EN"
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
    level: str                # output/outcome/impact
    target: Optional[float]
    baseline: Optional[float]
    locations: List[LocationEntry] = field(default_factory=list)

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
class Project:
    id: str
    name: str
    objective: str
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
    status: str               # todo/doing/done
    notes: str = ""

@dataclass
class OperationalActivity:
    id: str
    name: str
    owner: str
    start_date: Optional[date]
    due_date: Optional[date]
    status: str               # planned/ongoing/done
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
    projects: List[Project] = field(default_factory=list)
    ops_by_project: Dict[str, OpsLite] = field(default_factory=dict)

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

def from_serializable(d: dict) -> LogiTrackData:
    projects: List[Project] = []
    for p in d.get("projects", []):
        inds: List[Indicator] = []
        for i in p.get("indicators", []):
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
                locations=locs
            ))
        projects.append(Project(
            id=p["id"],
            name=p["name"],
            objective=p["objective"],
            indicators=inds
        ))

    ops_by_project: Dict[str, OpsLite] = {}
    for pid, ops in d.get("ops_by_project", {}).items():
        acts: List[OperationalActivity] = []
        for a in ops.get("activities", []):
            tasks: List[Task] = []
            for t in a.get("tasks", []):
                tasks.append(Task(
                    id=t["id"],
                    name=t["name"],
                    owner=t.get("owner", ""),
                    due_date=parse_date(t.get("due_date", "")),
                    status=t.get("status", "todo"),
                    notes=t.get("notes", "")
                ))
            acts.append(OperationalActivity(
                id=a["id"],
                name=a["name"],
                owner=a.get("owner", ""),
                start_date=parse_date(a.get("start_date", "")),
                due_date=parse_date(a.get("due_date", "")),
                status=a.get("status", "planned"),
                linked_indicator_ids=a.get("linked_indicator_ids", []),
                tasks=tasks
            ))
        ops_by_project[pid] = OpsLite(activities=acts)

    return LogiTrackData(projects=projects, ops_by_project=ops_by_project)

def save_json(data: LogiTrackData, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_serializable(data), f, ensure_ascii=False, indent=2)

def load_json(path: str) -> LogiTrackData:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return from_serializable(d)

def load_data_from_path(path: str) -> LogiTrackData:
    if not os.path.exists(path):
        # For API use (Render): return empty dataset instead of crashing
        return LogiTrackData()
    return load_json(path)

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
                    "status": tsk.status, "notes": tsk.notes
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
                if (t.status or "").lower() == "done":
                    tasks_done += 1
                if t.due_date and (t.status or "").lower() != "done":
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

# ----------------------------
# FASTAPI APP (Render-ready)
# ----------------------------
app = None
if FastAPI is not None:
    app = FastAPI(title=f"{CONFIG['system_name']} API", version=CONFIG["version"])

    if CORSMiddleware is not None:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _load_for_api() -> LogiTrackData:
        # For Render: read from LOGITRACK_DATA_PATH or default
        path = os.getenv("LOGITRACK_DATA_PATH", DEFAULT_DATA_PATH)
        return load_data_from_path(path)

    @app.get("/")
    def home():
        return {
            "system": CONFIG["system_name"],
            "version": CONFIG["version"],
            "docs": "/docs",
            "health": "/health",
            "v1": {
                "projects": "/v1/projects",
                "indicators": "/v1/indicators",
                "indicator_locations": "/v1/indicator_locations",
                "activities": "/v1/activities",
                "tasks": "/v1/tasks",
                "activity_indicator_links": "/v1/activity_indicator_links",
                "kpi_project": "/v1/kpi/project",
                "kpi_indicator": "/v1/kpi/indicator",
                "kpi_district": "/v1/kpi/district",
                "kpi_workplan": "/v1/kpi/workplan",
            },
        }

    @app.get("/health")
    def health():
        path = os.getenv("LOGITRACK_DATA_PATH", DEFAULT_DATA_PATH)
        return {
            "ok": True,
            "system": CONFIG["system_name"],
            "version": CONFIG["version"],
            "data_path": path,
            "data_file_exists": os.path.exists(path),
        }

    @app.get("/v1/projects")
    def v1_projects():
        d = _load_for_api()
        return build_bi_tables(d)[0]

    @app.get("/v1/indicators")
    def v1_indicators():
        d = _load_for_api()
        return build_bi_tables(d)[1]

    @app.get("/v1/indicator_locations")
    def v1_indicator_locations():
        d = _load_for_api()
        return build_bi_tables(d)[2]

    @app.get("/v1/activities")
    def v1_activities():
        d = _load_for_api()
        return build_bi_tables(d)[3]

    @app.get("/v1/tasks")
    def v1_tasks():
        d = _load_for_api()
        return build_bi_tables(d)[4]

    @app.get("/v1/activity_indicator_links")
    def v1_links():
        d = _load_for_api()
        return build_bi_tables(d)[5]

    @app.get("/v1/kpi/project")
    def v1_kpi_project():
        d = _load_for_api()
        return build_bi_tables(d)[6]

    @app.get("/v1/kpi/indicator")
    def v1_kpi_indicator():
        d = _load_for_api()
        return build_bi_tables(d)[7]

    @app.get("/v1/kpi/district")
    def v1_kpi_district():
        d = _load_for_api()
        return build_bi_tables(d)[8]

    @app.get("/v1/kpi/workplan")
    def v1_kpi_workplan():
        d = _load_for_api()
        return build_bi_tables(d)[9]

# ----------------------------
# LOCAL CLI MAIN APP (NO FEATURES REMOVED)
# ----------------------------
def main():
    global REPORT_LANG
    REPORT_LANG = select_language()

    data = LogiTrackData()
    default_path = DEFAULT_DATA_PATH

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
            save_json(data, path)
            print(f"{tr('saved_to')}: {path}")

        elif choice == "5":
            path = input(f"{tr('path_load', path=default_path)}: ").strip() or default_path
            if not os.path.exists(path):
                print(tr("data_file_missing", path=path))
                continue
            data = load_json(path)
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
            print("  uvicorn logitrack_rc_v4_4:app --host 127.0.0.1 --port 8000")

        elif choice == "0":
            break

        else:
            print(tr("invalid_option"))

if __name__ == "__main__":
    main()
