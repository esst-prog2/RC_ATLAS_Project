# Full-System Coverage Matrix

The QA Lead retains every row in the final audit. A row without execution must still receive `BLOCKED`, `NOT_TESTED`, or `INCONCLUSIVE` plus a reason. Scenario IDs refer to the catalogs under `qa/scenarios/`.

| Product area | Implemented surfaces | Primary owner | Secondary | Required modes | Scenario families |
| --- | --- | --- | --- | --- | --- |
| Bootstrap and authentication | pristine seed, login, logout, session, health | Security & Access | Functional, Reliability | source, automated, browser | SEC-AUTH, FUN-AUTH, REL-BOOT |
| Organization administration | users, roles, teams, activation, membership | Security & Access | Functional | source, automated, browser | SEC-ADMIN, FUN-ADMIN |
| Project lifecycle/configuration | create/configure projects, membership, ownership | Functional | Security & Access, UI/UX | automated, browser | FUN-PROJ, SEC-SCOPE, UI-PROJ |
| Portfolio/executive | overview, executive summaries, cross-project navigation | Data & Analytics | Functional, UI/UX | automated, browser | DAT-PORT, UI-NAV |
| Workplan and activities | activities, nesting, coordination, assignment | Functional | Integration, UI/UX | source, automated, browser | FUN-WORK, INT-API, UI-WORK |
| Assignment-aware tasks | execution, evidence, validation, approval, return, escalation | Functional | Security & Access, Reliability, UI/UX | automated, browser | FUN-TASK, SEC-TASK, REL-TASK, UI-TASK |
| Logical Framework | hierarchy, indicators, links, scoped persistence | Functional | Data & Analytics, Reliability, Security & Access | source, automated, browser | FUN-LF, DAT-LF, REL-LF, SEC-SCOPE |
| Dataset import and semantic mapping | uploads/import, mapping, validation, rejection | Integration | Data & Analytics, Security & Access, UI/UX | source, automated, browser | INT-DATA, DAT-QUAL, SEC-UPLOAD, UI-DATA |
| Data quality | completeness, validity, issue presentation | Data & Analytics | Functional, UI/UX | automated, browser | DAT-QUAL, UI-DATA |
| KPIs and trends | calculations, filters, trends, rounding, missing data | Data & Analytics | Reliability, UI/UX | source, automated, browser | DAT-KPI, REL-CALC, UI-ANL |
| Indicator intelligence/narratives | generated insights, provenance, empty/error states | Data & Analytics | Integration, UI/UX | automated, browser | DAT-INTEL, INT-NARR, UI-ANL |
| Dashboards | summaries, saved templates, filters, tenant scope | Data & Analytics | Security & Access, UI/UX | automated, browser | DAT-DASH, SEC-SCOPE, UI-DASH |
| Reports and exports | preview, template, export content and boundaries | Data & Analytics | Integration, UI/UX, Security & Access | automated, browser | DAT-REPORT, INT-EXPORT, UI-REPORT, SEC-EXPORT |
| Risks | risk views, state changes, project scope | Functional | Data & Analytics, UI/UX | automated, browser | FUN-RISK, DAT-RISK, UI-RISK |
| Studio Lab | implemented experimental/lab view and its enabled controls | UI/UX | Functional, Security & Access | source, browser | UI-LAB |
| Notifications | in-app rules/history and recipient scope | Integration | Security & Access, Functional | source, automated, browser | INT-NOTIFY, SEC-NOTIFY, FUN-NOTIFY |
| External delivery | SMTP, SendGrid, webhook, WhatsApp/Twilio/Meta | Integration | Security & Access, Reliability | source, external provider | INT-PROVIDER, SEC-PROVIDER, REL-PROVIDER |
| Audit/history | event accuracy, actor/scope, failure side effects | Security & Access | Reliability, Functional | source, automated | SEC-AUDIT, REL-ATOMIC |
| Canonical persistence | JSON/SQLite snapshot, atomic saves, recovery | Reliability | Data & Analytics, Security & Access | source, automated | REL-PERSIST, SEC-DATA |
| Derived projection | rebuild, precedence, consistency, duplicates | Reliability | Data & Analytics | automated | REL-PROJ, DAT-CONSIST |
| Migration/backfill | dry run, backup, idempotence, unresolved records | Reliability | Security & Access | source, automated | REL-MIG, SEC-MIG |
| Localization | EN/PT/FR content, labels, formatting, fallback | UI/UX | Functional | source, browser | UI-I18N, FUN-I18N |
| Accessibility/usability | keyboard, focus, labels, errors, responsive layouts | UI/UX | Functional | real browser | UI-A11Y, UI-RESP, UI-ERROR |
| API contract compatibility | status codes, schemas, legacy routes, error detail | Integration | Security & Access, Functional | source, automated | INT-API, SEC-ERROR |
| Operational reliability | restart, refresh, concurrent requests, degraded dependencies | Reliability | Integration, UI/UX | automated, browser | REL-OPS, INT-FAIL, UI-STALE |

Mode names in scenario YAML use `source_inspection`, `automated_test`, `real_browser`, and `external_provider`.
