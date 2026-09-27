## Context

See `proposal.md` for motivation and the capability specification for observable behavior. RC Atlas currently has one authoritative serialized `LogiTrackData` snapshot, FastAPI routes split between `LogiTrackRC v4.4.py` and focused `api/` modules, and callback-based services around reporting, notifications, demo workflows, dashboard templates, and Logical Framework.

The shared authorization helper currently accepts the configured API key before resolving a user and returns `None` as the actor. Several legacy and extracted GET routes do not invoke authentication at all. Other mutations check a permission but look up project or child identifiers from whole-state collections without consistently verifying organization and project ownership. Logical Framework is the strongest existing exception: it requires a real actor, creates an immutable actor context, verifies project scope, and reaches storage through its application/UoW boundary.

This change secures the request boundary while snapshots remain authoritative. It does not migrate persistence, redesign sessions, or generalize the Logical Framework repository to unrelated domains.

## Goals / Non-Goals

**Goals:**

- Establish one fail-closed authenticated tenant context for current tenant-owned `/v1` operations.
- Make actor identity, organization ID, and effective permissions explicit before tenant-owned data is resolved.
- Apply organization and project ownership checks to both reads and writes without changing successful domain behavior.
- Remove the global API key's ability to act as an actorless tenant bypass while preserving header compatibility.
- Protect hostile identifiers, including cross-tenant same-ID collisions, before existing mutations run.
- Preserve the current Studio through authentication-header-only compatibility edits where required.
- Provide reusable black-box tests that verify HTTP results and canonical non-mutation after denials.

**Non-Goals:**

- Session entities, concurrent sessions, expiration, backend logout, password change/reset, lockout, or rate limiting.
- Browser token-storage redesign, XSS/CSP work, broad CORS or security-header architecture, or SSRF remediation.
- PostgreSQL, schema migration, a generic repository layer, or changes to snapshot authority.
- Changes to role names, permission bundles, workflows, Logical Framework architecture, API v2, or successful response DTOs.
- UI redesign, frontend modularization, React, TypeScript, or RC Atlas Next.
- A production/demo deployment-mode architecture or service-account credential model.

## Decisions

### 1. Add an immutable authenticated tenant context at the HTTP boundary

Introduce a focused value object, conceptually:

```text
AuthenticatedTenantContext
  actor_id
  username
  organization_id
  role
  effective_permissions
```

The context is produced only from a valid, active `X-Auth-Token`. It contains identifiers and immutable authorization facts, not `LogiTrackData`, mutable collections, repositories, or persistence callbacks. Project context is resolved separately for routes that target a project so the requested project is revalidated against the actor's organization.

The request path becomes:

```text
HTTP request
  -> authenticate X-Auth-Token
  -> AuthenticatedTenantContext
  -> existing capability check
  -> organization/project-scoped resource resolution
  -> existing service/domain behavior
  -> existing audit/notification/persistence behavior
```

The composition root may use the current loaded snapshot to resolve the token and build the context, and existing services may continue to use snapshot-backed dependencies. The context itself never exposes whole application state.

**Alternative considered:** Extend the optional `UserAccount` return from `_authorize_request` and rely on each route to remember scope checks. Rejected because the current defect is inconsistent caller discipline and actorless success.

**Alternative considered:** Introduce a global tenant repository/UoW for all domains. Rejected as a persistence rewrite outside this security slice.

### 2. Separate user authentication from API-key verification

Tenant-owned routes use a helper that always requires a real active user. If both headers are present, user-token resolution is authoritative; the API key neither bypasses an invalid token nor expands permissions. An API-key-only call to tenant data returns 401.

If a current endpoint is proven to be purely technical and non-tenant, it can use an explicitly named technical-key check. That helper must not return tenant context and cannot be reused by data-bearing routes. The current exploration identified no API-key-only requirement that justifies access to tenant-owned application state, so the default is fail closed.

**Alternative considered:** Bind the existing global key to a synthetic super-admin. Rejected because it would preserve the unauditable universal bypass and invent a service-account model.

### 3. Preserve existing permissions and add ownership as an independent gate

Authorization is conjunctive:

```text
valid actor AND required existing capability AND in-scope target/references
```

Routes that already require a named permission keep it. Previously public reads become authenticated and scoped; they use an existing read permission where one is already part of that module's contract, otherwise they require an active in-tenant actor without inventing a new permission bundle. Existing task assignment and workflow role rules continue to run after tenant resolution.

Status behavior is:

- 401 for absent, invalid, or inactive actor, including API-key-only calls.
- 403 for an authenticated actor who lacks an existing required capability.
- 404 for identifiers not found within a scoped lookup, including foreign objects on newly protected legacy routes, to avoid confirming foreign resource existence.
- Existing Logical Framework and other already-tested routes retain established 403/404 distinctions where changing them would break their public contract.
- Existing same-tenant validation failures retain their established 400 semantics, and same-tenant lifecycle, dependency, and conflict failures retain their established 409 semantics.

### 4. Use domain-specific scoped resolvers, not a generic repository

Small resolver functions or focused service dependencies will express the ownership path for each domain. Representative rules are:

- Project: `project.organization_id == context.organization_id`.
- Project child (indicator, activity, task, project report): resolve the scoped project first, then resolve the child within that project.
- User/team: match stable IDs together with `organization_id`; username and email checks remain global because the current login flow has no organization selector.
- Dataset/custom template/notification rule: use explicit organization ownership when present, otherwise derive only through one unambiguous owned parent. Persisted custom templates with blank ownership fail closed.
- Generated builtin template: create and return it only from an already authenticated and tenant-scoped dataset request; treat it as a read-only transient output, never as a persisted custom-template target.
- Audit event: explicit organization ownership, or deterministic derivation from one owned project/resource. Actor display enrichment uses the event's established organization together with actor ID or username.

Every referenced ID in a mutation is scoped, not just its primary target. Destructive operations filter or locate by scope and ID together, so same-ID collisions cannot affect foreign records.

**Alternative considered:** Fetch globally and filter response payloads afterward. Rejected because it still exposes foreign objects to business logic and does not secure writes.

### 5. Close reads at their actual route boundary

Monolithic project/BI endpoints, including `GET /v1/dashboard/summary`, and extracted reporting, notification, dashboard-template, and demo routes will accept the existing auth headers and resolve context before service calls. Services receive context or focused scope inputs where necessary so collection filtering happens before response construction.

The successful route method, path, payload, status, and response shape remain unchanged. Collections may contain fewer records because foreign and ambiguous records are removed; that is the intended security correction.

### 6. Validate all scope before mutation and reuse existing persistence

For each write, authentication, capability checks, project ownership, target ownership, and referenced-object ownership occur before the existing object mutation, audit append, notification creation, outbound webhook/email/WhatsApp/provider call, or save call. Denials therefore perform zero canonical saves, invoke no external dispatcher, and create no success-side effects.

This change does not add a global transaction manager. Once checks pass, the existing domain-specific mutation and persistence sequence remains responsible for successful atomicity. The Logical Framework application/UoW path is not bypassed or rewritten.

### 7. Make admin user/team lookups scope-qualified

Create, update, suspend, reactivate, archive, and team membership operations must locate record targets with `(organization_id, id)` semantics. Caller-supplied IDs never select or replace a foreign organization record. Username and email availability checks remain global to preserve the current organization-agnostic login mechanism; duplicate identity attempts return the existing 409 envelope without foreign-tenant details. Organization Admin retains current in-tenant governance permissions.

### 8. Fail closed on global destructive workspace operations

`/v1/data/import` and any reset path that replaces or globally affects the authoritative snapshot are not representable as ordinary tenant-admin operations. They reject tenant actors with 403 and API-key-only calls with 401 rather than treating Organization Admin as a platform operator.

`POST /v1/system/relational_sync` is likewise a global data-bearing operation. Because no current actor represents platform-global authority, its external HTTP path rejects anonymous and API-key-only callers with 401 and every authenticated tenant actor, including Organization Admin, with 403. The rejection happens before synchronization, audit, canonical save, or projection mutation. Existing internal startup and canonical-save projection synchronization remains unchanged.

`POST /v1/auth/bootstrap` remains the one narrow unauthenticated first-run exception. It succeeds only when all persisted tenant-bearing collections are empty: organizations, users, teams, projects, project operations, Logical Framework results/links, datasets, reporting records, semantic mappings, custom templates, notification rules, and audit events. Existing users or any tenant/organization/operational state produce the compatible 409 response before mutation or success audit.

The existing local demo bootstrap may remain only under a deterministic empty-workspace precondition: no organizations, users, or tenant-owned records. Once populated, a normal request cannot reseed the whole workspace. This preserves course/local initialization without defining a production operator architecture.

**Alternative considered:** Scope global import to the caller during this change. Rejected because it would require a new import ownership/migration design.

### 9. Apply a fail-closed legacy ownership policy

No compatibility path assigns missing ownership from the current caller. A legacy record is accessible only when it has explicit ownership or one deterministic parent relationship that resolves to the actor's organization and applicable project. Conflicting, orphaned, or otherwise ambiguous records are omitted from collections and unavailable to mutation.

No snapshot format migration is required. This is runtime access-control derivation; intentional data backfill belongs to a separate migration change.

Generated builtin dashboard templates are not legacy persisted records. They may be returned only as transient, read-only output after their source dataset has passed tenant scoping. This exception cannot authorize blank-owner persisted custom templates or make builtins writable.

### 10. Restrict organization audit views without redesigning audit storage

Audit reads filter to explicitly owned events plus events whose ownership can be derived unambiguously from an owned project/resource. Empty-organization events are not automatically shared with every organization. Actor display enrichment resolves a user only inside the event's established organization, preventing a colliding foreign user ID or username from supplying display data. Existing operational audit creation remains unchanged except where route scoping ensures the actor and resource ownership are correct.

### 11. Keep anonymous health output to minimal liveness

`GET /health` remains available for local/runtime liveness checks, but its anonymous response contains only `ok`, `system`, and `version`. Storage paths, aggregate record counts, repository/projection state, tenant data, and internal configuration are not returned anonymously. This is a narrow response hardening, not a new observability system.

### 12. Limit Studio work to existing auth-header plumbing

Calls that already use the shared Studio API helper continue unchanged. Any protected call currently made without auth headers is switched to the existing authenticated request helper or supplied the existing token header. There are no component, CSS, navigation, localization, Portfolio, or Workplan presentation changes.

### 13. Prove the boundary with reusable black-box contracts

A security contract fixture creates two organizations, representative roles, multiple projects, and colliding IDs where allowed. Tests call the FastAPI application rather than invoking only helpers and verify both response status/payload and persisted state.

The matrix covers anonymous, invalid-token, API-key-only, token-plus-key, authorized, insufficient-permission, foreign-project, foreign-object, and same-ID requests across representative GET collection/detail, POST, PATCH/PUT, DELETE, and task workflow operations. It also covers first-run bootstrap, the disabled external relational-sync path, tenant-scoped dashboard summary, minimal anonymous health, global username/email conflicts, generated builtin templates, organization-scoped audit enrichment, existing 400/409 business errors, and notification denials with controllable dispatch fakes. Snapshot fingerprints or focused before/after state assertions prove that denied operations did not alter canonical data, audit, notifications, projections, or external dispatch counters.

Existing route compatibility tests remain, and the authoritative `py -m unittest discover -v -p "*tests.py"` suite is the final regression gate.

## Risks / Trade-offs

- **[Intentional compatibility break for anonymous/API-key clients]** -> Update the current Studio's few unauthenticated data calls in the same release and document that tenant APIs require `X-Auth-Token`; preserve successful authenticated payloads.
- **[Large route inventory can leave a gap]** -> Start with a route/auth characterization table and require every data-bearing `/v1` route to be classified as tenant-owned, explicitly non-tenant technical, or out of scope with rationale.
- **[Legacy records disappear from scoped reads]** -> Permit only deterministic parent-based derivation, add fixtures for known legacy shapes, and report ambiguous records diagnostically without granting access.
- **[Monolithic and modular routes may drift]** -> Use the same context constructor and error policy from both registration styles, then enforce behavior through shared black-box tests.
- **[Snapshot concurrency remains last-write-wins]** -> Keep this limitation explicit; this change prevents unauthorized mutations but does not claim concurrent update safety.
- **[Global demo seed becomes less convenient]** -> Preserve only empty-workspace bootstrap and require separate future operator/demo-mode architecture for destructive reseeding.
- **[Security checks could alter role workflows]** -> Keep current permission and workflow tests as mandatory gates and add tenant scope before, not instead of, existing business rules.

## Migration Plan

1. Record the current route inventory, response contracts, role behavior, and baseline tests before implementation.
2. Add the tenant-context type and authentication/error-policy helpers without changing route behavior.
3. Add black-box failure cases for anonymous, API-key-only, foreign-scope, and same-ID requests; initially confirm they expose the characterized gaps.
4. Migrate read and write surfaces in small domain groups, keeping each group's successful contract and existing tests green.
5. Apply admin collision, global destructive-operation, audit visibility, and legacy ownership policies.
6. Add only required Studio auth-header compatibility changes and verify approved views remain unchanged.
7. Run focused security contracts, domain/workflow tests, the full unittest suite, and final scope review.

Rollback is a source rollback of this bounded change. No schema or snapshot-format migration is introduced, so stored data remains readable by the previous version. Deploy backend and any minimal Studio header adjustment together because newly protected calls intentionally reject unauthenticated clients.

## Open Questions

None. Any future service-account/API-key model, production demo-mode separation, ownership backfill migration, session lifecycle, or browser hardening requires a separate approved change.
