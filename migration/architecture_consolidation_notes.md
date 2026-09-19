# Architecture Consolidation Notes

This sprint extracts three monolith-heavy areas into explicit modules without changing the route contract:

- `shared/domain_models.py`
  - shared dataclasses for tidy datasets, reporting records, semantic mappings, dashboard templates, notification rules, users, and audit events
- `services/reporting.py`
  - reporting and tidy-dataset orchestration
- `services/notifications.py`
  - notification rule execution, dispatch routing, and scheduler-facing batch execution
- `services/dashboard_templates.py`
  - dashboard-template listing and persistence
- `api/reporting_routes.py`
  - preserves reporting, trends, narratives, tidy-dataset, and reporting import routes
- `api/notification_routes.py`
  - preserves notification channel, notification listing, rule, due-run, and dispatch routes
- `api/dashboard_template_routes.py`
  - preserves dashboard-template routes

## Compatibility strategy

- Existing route paths remain unchanged.
- Existing helper and domain logic inside `LogiTrackRC v4.4.py` is still used through injected dependencies.
- JSON persistence, repository sync, relational mirror, and scheduler behavior remain intact.
- The extraction is orchestration-first: it reduces monolith responsibilities before attempting deeper domain rewrites.

## Tradeoffs

- The service layer currently depends on injected legacy helpers from the monolith. This is intentional to preserve behavior while creating boundaries.
- Some business rules still live in the monolith and are called through those dependencies. A later sprint can move pure helpers out progressively.
- FastAPI is still optional at import time, so route compatibility is validated with registration tests rather than live app boot in this environment.
