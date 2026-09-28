# Authenticated Tenant Boundary

RC Atlas tenant-owned HTTP APIs require an active user token and resolve an
immutable tenant context before reading or changing application data. The
context contains the actor ID, username, organization ID, role, and effective
permissions. It does not expose the application snapshot or persistence
callbacks.

The request boundary is:

```text
HTTP request
  -> X-Auth-Token authentication
  -> authenticated tenant context
  -> existing permission check
  -> organization/project-scoped resource resolution
  -> existing service or domain behavior
  -> existing snapshot persistence
```

## Authentication And Status Semantics

`X-API-Key` does not establish actor or tenant authority. API-key-only
requests to tenant data return HTTP 401. When both headers are present,
`X-Auth-Token` is authoritative and the API key does not expand or rescue
the actor's permissions.

The existing response envelope is retained:

- 401: missing, invalid, inactive, or organization-less actor.
- 403: authenticated actor lacks the existing capability, or a tenant actor
  attempts an externally unavailable global operation.
- 404: an object is unavailable inside the actor's scoped lookup, subject to
  established route-specific compatibility such as Logical Framework.
- 400: existing same-tenant validation failure.
- 409: existing same-tenant lifecycle, dependency, or identity conflict.

## Route Inventory

Anonymous non-tenant routes are limited to:

- `/`, `/studio`, and `/favicon.ico`: static application shell assets.
- `/health`: `ok`, `system`, and `version` only.
- `/v1/data/template`: fictional static request examples.
- `/v1/auth/login`: existing credential exchange.
- `/v1/auth/bootstrap`: first-run initialization only when every persisted
  tenant-owned collection is empty.
- `/v1/demo/seed`: local fictional demo initialization only for the same
  empty-workspace condition.

Authenticated tenant routes include project and BI reads, administration,
audit, indicators, activities, tasks and workplans, Logical Framework,
reporting, datasets, dashboard templates, notifications, and demo workspace
views and workflow actions. Collections are scoped before response
construction, and mutations scope both their target and referenced objects
before business behavior or side effects execute.

The following global HTTP operations fail closed because the current actor
model has no platform-global operator:

- `GET /v1/system/runtime`
- `GET /v1/system/relational_store`
- `GET /v1/system/repositories`
- `POST /v1/system/relational_sync`
- `POST /v1/data/import`

Anonymous and API-key-only calls receive 401. Authenticated tenant actors,
including Organization Admin, receive 403. Internal non-HTTP canonical-save
and projection synchronization remain available.

## Ownership Rules

Projects, users, teams, datasets, persisted custom dashboard templates, and
notification rules use explicit organization ownership. Project children are
resolved through an organization-scoped project. User and team record IDs are
tenant scoped, while usernames and email addresses remain globally unique
because login has no organization selector.

Legacy reporting records, semantic mappings, notification rules, and audit
events may use one deterministic owned parent when explicit ownership is
absent. Conflicting, orphaned, or otherwise ambiguous ownership fails closed;
the requesting actor is never used as an ownership backfill.

Generated builtin dashboard templates are transient read-only outputs. They
may be returned only after their source dataset has been authenticated and
tenant scoped. This does not permit blank ownership for persisted custom
templates.

Audit events are filtered by event organization before display enrichment.
Actor names are resolved within that event organization, preventing colliding
user IDs or usernames from leaking foreign-tenant identity data.

## Side Effects And Compatibility

Tenant, project, permission, and ownership checks occur before canonical
mutation, success audit, notification persistence, projection change, or
webhook/email/WhatsApp dispatch. Denied requests have no such side effects.

The operational task workflow and Logical Framework application/UoW boundary
remain unchanged. Authenticated same-tenant methods, payloads, successful
response shapes, workflow rules, snapshot authority, and projection behavior
remain compatible. Studio changes are limited to attaching its existing token
header to five previously unauthenticated dataset/template requests.

## Deferred Work

This boundary does not add multi-session storage, token expiry or revocation,
backend logout, password reset, rate limiting, XSS/CSP remediation, broad
CORS/security headers, SSRF remediation, a platform-operator or service-account
model, PostgreSQL, RC Atlas Next, or a persistence redesign.
