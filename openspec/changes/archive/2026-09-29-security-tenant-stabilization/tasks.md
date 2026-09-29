## 1. Baseline Characterization

- [x] 1.1 Run `py -m unittest discover -v -p "*tests.py"`, record the 151-test baseline, and stop implementation if any pre-existing test fails.
- [x] 1.2 Inventory every current `/v1` route as tenant-owned, explicitly non-tenant technical, or excluded with rationale; verify the inventory covers monolithic routes and every registrar in `api/`.
- [x] 1.3 Add black-box characterization tests for current authenticated success methods, paths, status codes, and response shapes across the covered domains; verify they pass before security behavior is changed.
- [x] 1.4 Add black-box characterization tests for current route-specific 401/403/404 behavior, existing same-tenant 400 validation and 409 conflict/lifecycle behavior, and existing permission requirements, including Logical Framework exceptions; verify the implementation plan does not flatten domain errors or invent or broaden permission bundles.

## 2. Authenticated Tenant Context

- [x] 2.1 Add a focused immutable authenticated-tenant-context value object containing actor ID, username, organization ID, role, and effective permissions; verify it exposes no `LogiTrackData`, mutable collections, or persistence access.
- [x] 2.2 Add one shared context-construction path from a valid active `X-Auth-Token`; verify active users resolve correctly and invalid, suspended, or archived users return 401.
- [x] 2.3 Separate tenant authentication from technical API-key verification; verify a valid `X-API-Key` alone cannot create tenant context or access tenant-owned data.
- [x] 2.4 Make `X-Auth-Token` authoritative when both headers are present; verify a valid token retains its own permissions and tenant scope while an invalid token is not rescued by a valid API key.
- [x] 2.5 Centralize compatible 401/403/scoped-404 handling for migrated routes; verify existing Logical Framework status/error contracts remain unchanged.

## 3. Reusable Security Contract Harness

- [x] 3.1 Build a reusable black-box fixture with two organizations, authenticated representative roles, multiple projects, and same-ID records where supported; verify each actor resolves only to its own tenant.
- [x] 3.2 Add reusable authentication and permission matrix assertions for anonymous, invalid-token, API-key-only, token-plus-key, allowed-token, and denied-permission cases; verify actual HTTP envelopes and statuses.
- [x] 3.3 Add reusable organization/project isolation assertions for collection GET, detail GET, POST, PATCH or PUT, DELETE, and workflow transition operations; verify foreign project/object identifiers fail closed.
- [x] 3.4 Add canonical before/after assertions for denied mutations; verify snapshot data, audit events, notifications, and relevant projection state do not change.

## 4. Tenant-Safe Reads

- [x] 4.1 Require tenant context and scoped project resolution for legacy project, indicator, location, activity, task, link, KPI, project-dashboard, and `GET /v1/dashboard/summary` reads; verify collections and dashboard aggregation exclude foreign records and successful shapes remain compatible.
- [x] 4.2 Scope reporting records, portfolio/project trends, narratives, and indicator trend reads; verify portfolio aggregation uses only projects visible to the authenticated organization.
- [x] 4.3 Scope tidy-dataset detail, quality, mapping, narrative, history, blueprint, and suggestion reads; verify foreign and ambiguously owned datasets are unavailable.
- [x] 4.4 Scope notification, notification-rule, channel-status, and dashboard-template reads according to explicit or deterministically derived ownership; verify persisted custom templates require explicit tenant ownership while read-only builtin templates are returned only from an already scoped dataset and cannot create a generic blank-owner bypass.
- [x] 4.5 Scope demo workspace, executive snapshot, risks, workplan, data-quality, narrative, and report-preview reads to the authenticated actor; verify current in-tenant Studio responses retain their successful shapes.

## 5. Tenant-Safe Writes and Workflow

- [x] 5.1 Scope indicator mutations by authenticated organization, target project, and referenced IDs before mutation; verify foreign-project indicator writes and same-ID collisions cannot change foreign data.
- [x] 5.2 Scope activity mutations and indicator references by authenticated organization and project; verify foreign activity/indicator combinations fail with zero persisted side effects.
- [x] 5.3 Scope the existing task creation, assignment, progress/evidence update, validation, return, approval, and escalation operations before existing workflow rules execute; verify Field ownership and the two-step MEAL/Programme Manager closure remain unchanged without creating a new task-delete endpoint.
- [x] 5.4 Scope reporting-record imports, dataset imports, semantic mappings, and history materialization by explicit or derived tenant/project ownership; verify foreign and ambiguous records cannot be changed.
- [x] 5.5 Scope notification-rule creation/run/due execution, dispatch, and dashboard-template writes; use controllable dispatcher fakes to verify denied, foreign, ambiguous, anonymous, and API-key-only operations invoke zero webhook/email/WhatsApp/provider calls and cause no audit, notification, snapshot, or projection side effects.
- [x] 5.6 Add destructive-operation collision tests for every migrated delete/unlink path; verify a local same-ID target can be changed without removing or rewriting the foreign-tenant record.

## 6. Administration, Global Operations, and Audit

- [x] 6.1 Qualify admin user create/update/suspend/reactivate/archive targets by organization plus ID while preserving global username and email uniqueness; verify hostile user-ID collisions preserve foreign users and duplicate login identities return compatible 409 responses without foreign-tenant detail.
- [x] 6.2 Qualify admin team create/update/archive/member operations and conflicts by organization plus ID; verify hostile team-ID and member-ID collisions preserve foreign tenant data.
- [x] 6.3 Make global import/reset operations unavailable to ordinary tenant actors and API-key-only callers; verify Organization Admin receives 403, API-key-only receives 401, and the canonical workspace is unchanged.
- [x] 6.4 Restrict demo seeding to the deterministic empty-workspace precondition; verify empty local demo initialization still succeeds and populated workspaces cannot be replaced through the route.
- [x] 6.5 Restrict `POST /v1/auth/bootstrap` to a workspace with empty persisted organizations, users, teams, projects, project operations, Logical Framework results/links, datasets, reporting records, semantic mappings, custom templates, notification rules, and audit events; verify an empty first run succeeds while users or tenant data cause a side-effect-free 409.
- [x] 6.6 Fail closed `POST /v1/system/relational_sync` for anonymous and API-key-only callers with 401 and all tenant actors with 403; verify the sync function is not invoked and internal startup/canonical-save synchronization remains operational.
- [x] 6.7 Reduce anonymous `GET /health` to `ok`, `system`, and `version`; verify storage paths, record counts, repository/projection state, tenant data, and internal configuration are absent without introducing new observability infrastructure.
- [x] 6.8 Restrict audit collection/detail visibility and actor enrichment to explicitly or deterministically owned event organizations; verify foreign and ambiguous events are excluded and colliding foreign actor IDs/usernames cannot supply display data.

## 7. Legacy Ownership and Studio Compatibility

- [x] 7.1 Implement focused ownership-resolution helpers for covered legacy records using explicit organization IDs or exactly one deterministic owned parent; verify no helper assigns ownership from the caller.
- [x] 7.2 Add legacy fixtures for explicit, derivable, orphaned, and conflicting ownership; verify derivable records remain usable, ambiguous records fail closed without snapshot migration, custom templates require ownership, and generated builtins remain read-only outputs of a scoped dataset.
- [x] 7.3 Audit Studio calls to newly protected APIs and add only missing existing-token headers through current request plumbing; verify no markup, CSS, navigation, localization, Portfolio, or Workplan presentation changes occur.

## 8. Compatibility, Documentation, and Final Gates

- [x] 8.1 Run focused authentication, authorization, admin, task-workflow, reporting, notification, demo, audit, and Logical Framework tests, including the characterized same-tenant 400/409 cases; verify all existing role and business-rule contracts remain green.
- [x] 8.2 Run the complete reusable black-box tenant-isolation matrix and verify two-tenant reads, writes, collisions, workflow transitions, and denial non-mutation pass.
- [x] 8.3 Document the authenticated tenant boundary, API-key fail-closed rule, status semantics, legacy ownership policy, protected route inventory, and deferred session/demo/operator work; verify the documentation matches implemented behavior.
- [x] 8.4 Run `py -m unittest discover -v -p "*tests.py"`, OpenSpec strict validation, `git diff --check`, and a final diff review; verify all original and new tests pass and no PostgreSQL, session redesign, frontend redesign, workflow redesign, or unrelated refactor entered the change.
- [x] 8.5 Confirm `Site.txt`, runtime databases, caches, credentials, and generated artifacts remain untouched/untracked as applicable, and report the final implementation footprint without staging, committing, or pushing.
