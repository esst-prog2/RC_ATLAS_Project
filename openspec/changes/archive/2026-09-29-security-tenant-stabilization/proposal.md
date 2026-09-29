## Why

RC Atlas does not yet enforce one authenticated tenant boundary across all tenant-owned APIs: some reads remain anonymous, some writes resolve identifiers globally after checking only a capability, and the global `X-API-Key` path can authorize requests without a user, organization, or auditable actor. This creates credible cross-organization disclosure and mutation risks that should be closed before additional clients, modules, or persistence backends expand the attack surface.

## What Changes

- Introduce an immutable authenticated tenant context containing actor identity, organization identity, and effective permissions, with project context resolved when an operation is project-scoped.
- **BREAKING**: require a valid authenticated actor for tenant-owned reads, writes, deletes, workflow transitions, imports, resets, and administrative operations that were previously anonymous or accessible with only the global `X-API-Key`.
- Make `X-Auth-Token` authoritative when both headers are supplied and make API-key-only requests fail closed on tenant-owned routes; no service-account model is introduced.
- Scope collection reads and object resolution to the actor's organization and, where applicable, project before invoking existing domain behavior.
- Require both capability authorization and tenant/resource ownership for mutations, with denied operations producing no canonical snapshot, audit, notification, or projection side effects.
- Protect administrative user/team operations from cross-tenant identifier collisions and prevent organization administrators from invoking globally destructive import, reset, or demo operations.
- Preserve globally unique usernames and email addresses under the current organization-agnostic login flow while making user and team record IDs tenant scoped.
- Restrict unauthenticated bootstrap to a genuinely uninitialized persisted workspace, fail closed on external relational synchronization, tenant-scope the dashboard summary, and reduce anonymous health output to minimal liveness data.
- Distinguish tenant-owned custom dashboard templates from read-only generated builtin templates, and require tenant scope before any notification dispatcher or audit actor enrichment runs.
- Apply an explicit legacy-ownership policy: derive ownership only from an existing unambiguous relationship; otherwise exclude the record from reads and deny mutation.
- Restrict audit visibility to events with ownership that is unambiguously attributable to the requesting organization.
- Add reusable black-box security contract tests covering anonymous, API-key-only, authenticated, cross-tenant, cross-project, same-ID collision, permission, and non-mutation behavior across representative API surfaces.
- Permit only the smallest Studio compatibility changes needed to attach the existing authentication token to newly protected calls; no user-interface or frontend-architecture redesign is included.

## Capabilities

### New Capabilities

- `security-tenant-stabilization`: Client-independent authenticated tenant context, API-key fail-closed behavior, tenant/project resource isolation, legacy ownership handling, and black-box security contract requirements for current tenant-owned APIs.

### Modified Capabilities

None.

## Impact

- Expected backend touch points include the shared authorization boundary in `LogiTrackRC v4.4.py`, focused API route modules, existing domain-specific services/helpers, and narrow tenant/object lookup paths. The Logical Framework persistence boundary remains intact and serves only as a scoping reference.
- Covered API domains include legacy project/BI reads and dashboard summary, indicators, activities, task/workplan operations, reporting, datasets, notifications, dashboard templates, administration, authentication bootstrap, imports/resets, demo operations that can affect tenant data, global relational synchronization, health diagnostics, and audit visibility.
- Existing authenticated success payloads, workflow transitions, roles, permission meanings, stable identifiers, snapshot authority, JSON/SQLite compatibility, and approved Portfolio/Workplan behavior remain compatible.
- A minimal `logitrack_studio.html` request-header adjustment is allowed only if a protected existing request omits `X-Auth-Token`; visual and information-architecture changes are excluded.
- No dependency is added. Multi-session authentication, token lifecycle redesign, browser-token/XSS hardening, CORS/security-header work, PostgreSQL, RC Atlas Next, broad repository refactoring, and unrelated domain changes are deferred.
