## Purpose

Establishes a client-independent authenticated tenant boundary so RC Atlas tenant-owned API data can be read or changed only by an authorized actor within the actor's organization and applicable project scope.

## ADDED Requirements

### Requirement: Tenant-owned operations require an authenticated actor
Except for the explicitly bounded first-run authentication bootstrap and empty-workspace demo initialization defined below, every API operation that reads, creates, updates, deletes, transitions, imports, resets, or administrates tenant-owned data SHALL resolve an active authenticated user before reaching that data. The resolved request context SHALL contain the actor's stable user ID, organization ID, and effective permissions.

#### Scenario: Active token establishes tenant context
- **WHEN** an active user submits a valid `X-Auth-Token` to a tenant-owned endpoint
- **THEN** the system resolves that user's identity, organization, and effective permissions for the request

#### Scenario: Anonymous tenant-data request is rejected
- **WHEN** a request without a valid authenticated user targets tenant-owned data
- **THEN** the system returns HTTP 401 without reading or mutating tenant-owned records

#### Scenario: Inactive user is rejected
- **WHEN** a token resolves to a suspended, archived, or otherwise inactive user
- **THEN** the system returns HTTP 401 and does not establish tenant context

### Requirement: API keys do not establish tenant authority
Possession of the configured global `X-API-Key` SHALL NOT create an actor, organization, role, permission, or project context and SHALL NOT authorize access to tenant-owned API data.

#### Scenario: API-key-only tenant request fails closed
- **WHEN** a request supplies a valid `X-API-Key` but no valid `X-Auth-Token` to a tenant-owned endpoint
- **THEN** the system returns HTTP 401 without exposing or mutating tenant-owned data

#### Scenario: Authenticated token is authoritative when both headers are present
- **WHEN** a request supplies both `X-Auth-Token` and `X-API-Key`
- **THEN** the system derives tenant scope and permissions exclusively from the authenticated user represented by `X-Auth-Token`

#### Scenario: API key cannot rescue an invalid token
- **WHEN** a request supplies a valid `X-API-Key` and an invalid or inactive `X-Auth-Token` to a tenant-owned endpoint
- **THEN** the system returns HTTP 401

#### Scenario: Non-tenant technical endpoint remains explicitly isolated
- **WHEN** a technical endpoint is intentionally retained without a tenant actor
- **THEN** that endpoint cannot read, mutate, reset, import, or otherwise operate on tenant-owned application data

### Requirement: Authorization errors have stable security semantics
Tenant-owned API routes SHALL distinguish absent or invalid authentication, insufficient capability, and resources unavailable within the authenticated scope without disclosing foreign-tenant resource existence.

#### Scenario: Missing authentication returns 401
- **WHEN** tenant-owned data is requested without a valid actor
- **THEN** the response status is HTTP 401 with the existing API error envelope

#### Scenario: Missing capability returns 403
- **WHEN** an authenticated actor requests an in-scope operation but lacks its required permission
- **THEN** the response status is HTTP 403 with the existing API error envelope

#### Scenario: Foreign object is unavailable in scoped lookup
- **WHEN** an authenticated actor supplies an object identifier that does not resolve inside the actor's organization and applicable project scope
- **THEN** the system returns HTTP 404 unless an existing route contract intentionally uses HTTP 403 for project-scope denial

#### Scenario: Existing Logical Framework scope status remains compatible
- **WHEN** an authenticated actor is denied access by the existing Logical Framework project-scope contract
- **THEN** the route preserves its established HTTP status and error-envelope behavior

#### Scenario: Invalid same-tenant business input preserves 400 semantics
- **WHEN** an authenticated and authorized actor submits invalid business input for an in-scope resource
- **THEN** the route preserves its existing HTTP 400 semantics and error envelope

#### Scenario: Same-tenant lifecycle or dependency conflict preserves 409 semantics
- **WHEN** an authenticated and authorized actor attempts an invalid lifecycle transition or conflicting operation on an in-scope resource
- **THEN** the route preserves its existing HTTP 409 semantics and error envelope

### Requirement: Tenant-owned reads are organization scoped
Collection and detail reads SHALL return only records owned by the authenticated actor's organization or records whose ownership can be derived unambiguously from an in-scope parent relationship.

#### Scenario: Collection excludes foreign organization records
- **WHEN** an authenticated actor requests a tenant-owned collection containing records from multiple organizations
- **THEN** the response contains only records visible to the actor's organization

#### Scenario: Detail lookup cannot disclose foreign record
- **WHEN** an authenticated actor requests a foreign organization's record by identifier
- **THEN** the system returns the scoped not-found or established scope-denial response without returning record content

#### Scenario: Same identifier in two organizations resolves locally
- **WHEN** two organizations contain records with the same identifier and one organization's actor requests that identifier
- **THEN** the response resolves only the record owned by the actor's organization

### Requirement: Project-owned operations establish project scope
An operation on project-owned data SHALL confirm that the target project belongs to the authenticated actor's organization and that the requested resource belongs to that project before existing domain behavior executes.

#### Scenario: Foreign project identifier is rejected
- **WHEN** an authenticated actor supplies a project ID owned by another organization
- **THEN** the operation is rejected before project data or child resources are returned or changed

#### Scenario: Resource from another project is rejected
- **WHEN** an actor with access to Project A supplies a child-resource ID belonging to Project B
- **THEN** the operation is rejected unless the actor independently has access to Project B and the request explicitly targets Project B

#### Scenario: In-scope project behavior is preserved
- **WHEN** an authenticated actor has the required capability and the project and resource are in scope
- **THEN** the system invokes the existing domain behavior with the existing successful response shape

### Requirement: Mutations require capability and ownership authorization
Every tenant-owned mutation SHALL require both the existing operation permission and verified organization/project ownership of every target and referenced resource. Permission alone SHALL NOT authorize a foreign-tenant or foreign-project mutation.

#### Scenario: Capable actor cannot mutate foreign resource
- **WHEN** an actor has the required permission but supplies a resource owned by another organization
- **THEN** the system rejects the mutation before invoking existing domain behavior

#### Scenario: Referenced object is scoped
- **WHEN** a mutation references a related project, task, indicator, activity, user, team, report, dataset, notification rule, or dashboard template
- **THEN** each referenced object is resolved within the authenticated tenant and applicable project scope before mutation

#### Scenario: Denied mutation has no durable side effects
- **WHEN** authentication, permission, organization scope, project scope, or ownership validation rejects a mutation
- **THEN** the canonical snapshot, audit events, notifications, and relational projection remain unchanged by that request

#### Scenario: Existing successful workflow transition is preserved
- **WHEN** an authorized actor performs an in-scope task workflow transition
- **THEN** the existing workflow state, audit, notification, persistence, and response semantics remain unchanged

### Requirement: Current tenant-data API surfaces enforce the boundary
The authenticated tenant boundary SHALL cover current legacy project and BI reads, indicators, activities, tasks and workplans, reporting, datasets, notifications, dashboard templates, administration, tenant-visible audit data, and any import, reset, demo, or seed operation capable of affecting tenant-owned state.

#### Scenario: Legacy project and BI reads require tenant context
- **WHEN** a client requests project lists, project detail, indicators, locations, activities, tasks, links, KPIs, or project-dashboard data
- **THEN** the system authenticates the actor and restricts the response to the actor's organization and project access

#### Scenario: Indicator and activity writes are scoped
- **WHEN** an actor creates or updates an indicator or activity
- **THEN** the target project and all referenced tenant-owned objects are verified within the actor's scope

#### Scenario: Task and workplan operations are scoped
- **WHEN** an actor reads or mutates a task or performs a task workflow action
- **THEN** organization, project, permission, role-specific workflow, and canonical task-assignment rules all remain enforced

#### Scenario: Reporting and dataset operations are scoped
- **WHEN** an actor reads or changes reporting or dataset resources
- **THEN** only records with unambiguous ownership in the actor's organization and applicable project are accessible

#### Scenario: Notification and template operations are scoped
- **WHEN** an actor reads or changes notifications, notification rules, channels, or dashboard templates that contain tenant-owned data
- **THEN** the operation is restricted to records visible to the actor's organization

#### Scenario: Dashboard summary is tenant scoped
- **WHEN** an authenticated actor requests `GET /v1/dashboard/summary`
- **THEN** the response is computed only from data visible to that actor's organization and never from the unscoped aggregate

### Requirement: System and health endpoints have explicit data boundaries
Externally reachable technical endpoints SHALL NOT expose or operate on global tenant data without an actor model capable of representing that authority. Anonymous health checking MAY expose only minimal infrastructure liveness data.

#### Scenario: External relational synchronization fails closed for anonymous and API-key callers
- **WHEN** an anonymous or API-key-only caller invokes `POST /v1/system/relational_sync`
- **THEN** the route returns HTTP 401 without invoking synchronization, appending a success audit event, saving canonical state, or changing projection state

#### Scenario: External relational synchronization fails closed for tenant actors
- **WHEN** any authenticated tenant actor, including an Organization Admin, invokes `POST /v1/system/relational_sync`
- **THEN** the route returns HTTP 403 without invoking global synchronization or producing any persistence or success-audit side effect

#### Scenario: Internal projection synchronization remains available
- **WHEN** existing non-HTTP startup or canonical-save infrastructure performs projection synchronization
- **THEN** that internal behavior remains available and is not authorized through the external tenant request boundary

#### Scenario: Anonymous health response is minimal
- **WHEN** an anonymous caller requests `GET /health`
- **THEN** the response contains only the existing minimal liveness identity and status fields `ok`, `system`, and `version`, without storage paths, tenant record counts, repository state, tenant data, or internal configuration

### Requirement: Administrative identifiers are collision safe
Organization administration SHALL resolve and mutate users and teams by both identifier and organization scope so a hostile or colliding identifier cannot overwrite, archive, suspend, reactivate, or otherwise modify another organization's record.

#### Scenario: User ID collision cannot overwrite foreign user
- **WHEN** an Organization Admin creates or updates a user using an ID also present in another organization
- **THEN** the foreign user remains unchanged and the local operation follows the existing local duplicate/conflict policy

#### Scenario: Team ID collision cannot overwrite foreign team
- **WHEN** an Organization Admin creates or updates a team using an ID also present in another organization
- **THEN** the foreign team remains unchanged and the local operation follows the existing local duplicate/conflict policy

#### Scenario: Organization Admin retains local governance
- **WHEN** an Organization Admin performs an allowed operation on a user or team in the admin's own organization
- **THEN** the existing governance capability and successful response behavior remain available

#### Scenario: Username remains globally unique
- **WHEN** an administrator attempts to create or update a user with a username already assigned in any organization
- **THEN** the request returns the existing HTTP 409 conflict envelope without disclosing the foreign user's organization or other tenant details

#### Scenario: Email remains globally unique
- **WHEN** an administrator attempts to create or update a user with an email address already assigned in any organization
- **THEN** the request returns the existing HTTP 409 conflict envelope without disclosing the foreign user's organization or other tenant details

### Requirement: First-run authentication bootstrap is bounded
The system SHALL permit unauthenticated `POST /v1/auth/bootstrap` only while the persisted workspace is genuinely uninitialized. A workspace is genuinely uninitialized only when its persisted organizations, users, teams, projects, project operations, Logical Framework results and links, datasets, reporting records, semantic mappings, custom dashboard templates, notification rules, and audit events are all empty.

#### Scenario: Genuinely uninitialized workspace permits bootstrap
- **WHEN** `POST /v1/auth/bootstrap` is invoked against a workspace satisfying the complete uninitialized-workspace condition
- **THEN** the existing first organization and Organization Admin initialization flow may succeed with its existing response contract

#### Scenario: Existing users deny bootstrap
- **WHEN** the workspace contains any user
- **THEN** bootstrap returns the existing compatible HTTP 409 conflict response and does not mutate canonical state or append a success audit event

#### Scenario: Tenant data without users denies bootstrap
- **WHEN** no users exist but any organization, team, project, operational record, Logical Framework record, reporting/dataset resource, custom template, notification rule, or audit event exists
- **THEN** bootstrap returns HTTP 409 without claiming, adopting, or modifying the existing workspace

#### Scenario: Denied bootstrap has no side effects
- **WHEN** either populated-workspace bootstrap denial applies
- **THEN** the canonical snapshot, audit events, and relational projection remain unchanged

### Requirement: Global destructive operations fail closed for tenant actors
An ordinary tenant actor, including an Organization Admin, SHALL NOT gain authority to replace, reset, reseed, or globally import the canonical multi-organization workspace. A global operation that cannot be represented safely by the current tenant actor model SHALL fail closed.

#### Scenario: Organization Admin cannot replace global workspace
- **WHEN** an Organization Admin invokes an import or reset operation that would replace or affect data outside that admin's organization
- **THEN** the operation returns HTTP 403 and the canonical workspace remains unchanged

#### Scenario: API key cannot authorize destructive operation
- **WHEN** a client invokes a global import, reset, demo, or seed operation with only `X-API-Key`
- **THEN** the operation returns HTTP 401 and does not change canonical state

#### Scenario: Empty-workspace local demo bootstrap remains bounded
- **WHEN** the existing local demo bootstrap is invoked in a canonical workspace with no organizations, users, or tenant-owned data
- **THEN** the system may initialize the existing fictional demo workspace without granting ongoing global authority to a tenant actor

#### Scenario: Demo reseed is unavailable in populated multi-tenant state
- **WHEN** any organization, user, or tenant-owned record already exists
- **THEN** an ordinary tenant request cannot use the demo seed path to replace the workspace

### Requirement: Audit visibility is tenant safe
Tenant-visible audit queries SHALL return only events whose organization ownership is explicitly the actor's organization or can be derived unambiguously from an owned project/resource relationship.

#### Scenario: Foreign audit event is excluded
- **WHEN** an Organization Admin requests audit events and the audit store contains events for multiple organizations
- **THEN** the response excludes events owned by other organizations

#### Scenario: Ambiguous audit event is excluded
- **WHEN** an audit event has no organization ID and ownership cannot be derived unambiguously
- **THEN** the event is not exposed through an organization-scoped audit response

#### Scenario: Local audit behavior is preserved
- **WHEN** an audit event is explicitly owned by the requesting actor's organization
- **THEN** existing permission and filtering behavior continues to make that event available

#### Scenario: Audit actor enrichment is organization scoped
- **WHEN** an in-scope audit event is enriched with actor display information and another organization contains a user with the same actor ID or username
- **THEN** actor enrichment resolves only within the event's established organization and never attaches the foreign user's display data

### Requirement: Legacy ownership is derived only when unambiguous
Records with absent or ambiguous organization ownership SHALL NOT be silently assigned to the requesting actor. Ownership MAY be derived only through an existing deterministic relationship to exactly one owned project or resource.

#### Scenario: Ownership derives from one scoped project
- **WHEN** a legacy record lacks `organization_id` but references exactly one project owned by the actor's organization
- **THEN** the system may treat the record as owned by that project's organization for access-control purposes without rewriting unrelated data

#### Scenario: Ambiguous legacy ownership fails closed
- **WHEN** a legacy record has no safe deterministic owner or has conflicting ownership relationships
- **THEN** the record is excluded from scoped reads and mutations against it are rejected

#### Scenario: Legacy compatibility does not assign ownership from caller
- **WHEN** an authenticated actor requests an ambiguously owned legacy record
- **THEN** the actor's organization is not used as an implicit ownership backfill

#### Scenario: Persisted custom template requires explicit ownership
- **WHEN** a persisted custom dashboard template has foreign, empty, or ambiguous organization ownership
- **THEN** it is unavailable to the requesting tenant and is not silently adopted or mutated

#### Scenario: Generated builtin template inherits scoped request context only
- **WHEN** builtin dashboard templates are generated from a dataset that has already been authenticated and resolved inside the actor's tenant scope
- **THEN** those read-only generated outputs may be returned for that request despite having no persisted `organization_id`, but they are not globally readable, persisted, adopted, or mutable as custom templates

### Requirement: Notification authorization precedes external side effects
Notification reads, rule execution, due-rule execution, and dispatch SHALL authenticate and validate tenant ownership of all relevant rules, datasets, projects, and generated notification inputs before invoking any outbound provider.

#### Scenario: Denied notification operation invokes no dispatcher
- **WHEN** a notification operation is denied because it is anonymous, API-key-only, foreign-tenant, ambiguously owned, or otherwise unauthorized
- **THEN** no webhook, SMTP/email, WhatsApp, or provider dispatcher is invoked and no notification, success audit, canonical snapshot, or projection state changes

#### Scenario: Authorized notification dispatch remains compatible
- **WHEN** an authenticated actor with the existing required permission executes an in-scope notification operation
- **THEN** existing rule evaluation, provider behavior, persistence, audit, and response semantics remain unchanged

### Requirement: Existing permissions and business rules remain authoritative
Tenant scoping SHALL complement, not replace or broaden, existing role permissions, project access, task ownership, workflow transitions, and Logical Framework hierarchy rules.

#### Scenario: Tenant membership does not grant missing permission
- **WHEN** an actor owns the tenant and project scope but lacks the required capability
- **THEN** the operation remains forbidden with HTTP 403

#### Scenario: Field assignment restriction remains enforced
- **WHEN** a Field Coordinator attempts to mutate an in-organization task not canonically assigned to that user
- **THEN** the existing task-ownership authorization rejects the mutation

#### Scenario: Logical Framework boundary remains unchanged
- **WHEN** an actor uses a Logical Framework endpoint
- **THEN** the existing application coordinator, unit of work, repository scoping, hierarchy behavior, permissions, persistence, and response contract remain authoritative

### Requirement: Successful API contracts remain client independent
For an authenticated, authorized, in-scope request, existing `/v1` methods, paths, request fields, successful status codes, response field names, and response shapes SHALL remain usable by the current Studio and any future authorized client.

#### Scenario: Existing Studio request succeeds with token
- **WHEN** the current Studio calls a newly protected endpoint using its authenticated user's token
- **THEN** the endpoint returns the same successful application data and behavior it provided before tenant-boundary enforcement

#### Scenario: Missing Studio token attachment is corrected without redesign
- **WHEN** an existing Studio request to tenant-owned data does not currently attach `X-Auth-Token`
- **THEN** the request is updated to use the existing authentication-header helper without changing the view's layout, information architecture, or business behavior

#### Scenario: Client implementation does not change authorization
- **WHEN** two clients submit equivalent authenticated requests with the same actor, payload, and resource scope
- **THEN** the backend produces equivalent authorization and business behavior regardless of client technology

### Requirement: Tenant isolation is protected by black-box security contracts
The change SHALL provide reusable HTTP-level security contract coverage that verifies both responses and persisted outcomes using at least two organizations and representative roles.

#### Scenario: Authentication matrix is exercised
- **WHEN** the security contract suite runs
- **THEN** it covers anonymous, invalid-token, API-key-only, token-plus-API-key, authorized-token, and insufficient-permission requests

#### Scenario: Operation matrix is exercised
- **WHEN** the security contract suite runs against representative tenant-owned routes
- **THEN** it covers collection and detail GET, POST, PATCH or PUT, DELETE, and a workflow transition

#### Scenario: Isolation matrix is exercised
- **WHEN** the security contract suite runs with two organizations and multiple projects
- **THEN** it covers foreign project IDs, foreign object IDs, and same-ID collisions where the data model permits them

#### Scenario: Denial non-mutation is verified
- **WHEN** a cross-tenant or unauthorized mutation is denied
- **THEN** the test verifies that canonical records, audit events, notifications, and projections affected by the operation did not change

#### Scenario: Full regression suite remains mandatory
- **WHEN** implementation verification is performed
- **THEN** all pre-existing RC Atlas tests and all new security contract tests pass without weakening, skipping, or deleting existing coverage

### Requirement: Deferred security architecture remains unchanged
This change SHALL NOT introduce session entities, multi-session support, token expiration, backend logout, password-reset flows, rate limiting, account lockout, browser token-storage redesign, XSS/CSP remediation, broad CORS or security-header redesign, SSRF remediation, PostgreSQL, Redis, queues, microservices, API v2, RC Atlas Next, a global repository rewrite, or domain/workflow redesign.

#### Scenario: Current token and persistence formats remain compatible
- **WHEN** the tenant boundary is implemented
- **THEN** the current token format and authoritative JSON/SQLite snapshot formats remain compatible

#### Scenario: Frontend and domain scope remain bounded
- **WHEN** the implementation diff is reviewed
- **THEN** it contains no UI redesign, frontend migration, task-workflow redesign, Logical Framework redesign, or unrelated feature work
