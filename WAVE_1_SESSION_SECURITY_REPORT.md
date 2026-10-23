# Wave 1 Session Security Report

## Identity And Determination

- Audit: `QA-SOURCE-AUDIT-20261009-140211-353A22C3`
- Worktree: `D:\RC_ATLAS_REMEDIATION_W1_20261014`
- Branch: `remediation/wave-1-security-integrity`
- Baseline HEAD: `6ee278af46abe37968c03b256252d7824c75ecf5`
- Evidence date: 2026-10-22
- Session-security determination: **PASS**
- Overall Wave 1 determination: **CONDITIONAL**
- Internet release determination: **NO-GO**

The browser bearer-token blocker recorded in `WAVE_1_ACCEPTANCE_CLOSURE_REPORT.md` is closed by implementation plus automated, real-browser, and process-restart evidence. Wave 1 remains conditional because historical activity ownership migration still requires its separate reviewed-data approval gate. This report does not authorize public deployment.

## Implemented Design

### Browser session transport

- Interactive login now creates a random server-side session and returns no bearer token. The raw session identifier exists only in a host-only session cookie; the canonical store retains only its SHA-256 hash (`LogiTrackRC v4.4.py:6924-7027`).
- Production cookies default to `__Host-rcatlas_session`, `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`, no `Domain`, and an absolute-lifetime `Max-Age` (`LogiTrackRC v4.4.py:1701-1759`). Server-side idle timeout, absolute timeout, tenant binding, revocation, and persisted session versions remain authoritative.
- Explicit local HTTP mode uses `rcatlas_session_dev` only when `LOGITRACK_ENVIRONMENT=development`, `LOGITRACK_SESSION_COOKIE_SECURE=false`, and the request host is loopback/test-only. The same setting fails closed with 503 outside that combination.
- Login while an existing browser session is present revokes the prior identifier with `login_rotation` before issuing a new session. Logout revokes the canonical session and expires both browser cookies (`LogiTrackRC v4.4.py:7059-7087`).
- Every response passing through the session middleware receives `Cache-Control: no-store`.

### CSRF and origin defense

- Each browser session receives an independent random CSRF nonce. Only its hash is stored in `ApiSession.csrf_token_hash` (`shared/domain_models.py:211-223`; generation at `LogiTrackRC v4.4.py:2549-2553`).
- The nonce is held in a separate host-only, `SameSite` CSRF cookie that is intentionally readable by same-origin JavaScript. It is not a session credential.
- Cookie-authenticated `POST`, `PUT`, `PATCH`, and `DELETE` requests require all three to match: CSRF cookie, `X-CSRF-Token` header, and the server-side hash. Missing, invalid, mismatched, and stale evidence returns 403 (`LogiTrackRC v4.4.py:6442-6487`).
- Unsafe requests with a cross-site fetch marker or an unapproved `Origin` return 403. Login, bootstrap, and demo setup do not require an existing CSRF token, but remain covered by origin validation; SameSite is defense in depth rather than the sole control.
- `GET /v1/auth/csrf` is a same-session recovery endpoint. Normal Studio reloads reuse the existing CSRF cookie; recovery rotates the nonce only when that cookie is absent (`LogiTrackRC v4.4.py:7029-7057`).

### Studio integration

- Studio no longer contains bearer-token input controls and no longer adds `X-Auth-Token` to browser requests.
- `fetch` uses `credentials="same-origin"`; unsafe calls attach the in-memory CSRF header (`logitrack_studio.html:11572-11602`).
- Reload restores identity through `/v1/auth/me`, reads the independent CSRF cookie, and refreshes the workspace without exposing the HttpOnly session identifier (`logitrack_studio.html:26190-26231`).
- Legacy `rcatlas.authToken` and `rcatlas.sessionUser` values are removed on startup and are never written. Only a non-secret `rcatlas.sessionSignal` logout marker is written for cross-tab synchronization (`logitrack_studio.html:10016-10018`, `:11650-11655`, `:25346-25354`).
- EN/PT/FR session-security copy was updated. Existing project, pending/error, duplicate-submit, language, and role workflows remain connected.

### Non-browser API compatibility

- Existing server-registered `X-Auth-Token` sessions remain supported for controlled non-browser clients and tests; they do not require CSRF because browsers cannot ambiently attach that header.
- Password-to-token issuance is disabled by default. It requires both `LOGITRACK_API_TOKEN_LOGIN_ENABLED=true` and `X-Auth-Transport: api-token`. Studio never requests this transport.
- If enabled later, clients must use TLS, non-browser secret storage, rotation, revocation, and redacted logging. It is not an insecure browser fallback.

## Changed Files

Session-security task changes:

- `LogiTrackRC v4.4.py`: cookie configuration, CSRF/origin middleware, login transport split, fixation rotation, CSRF recovery, logout cookie clearing.
- `shared/domain_models.py`: persisted CSRF hash on `ApiSession`.
- `logitrack_studio.html`: cookie session integration, CSRF header, reload restoration, cross-tab signal, removal of browser bearer controls/storage, localized copy.
- `session_security_tests.py`: ten focused positive, negative, boundary, restart, and configuration tests.
- `browser_acceptance_workflow_reliability_tests.py`: cookie-backed projection-failure regression.
- `studio_ui_tests.py`: no-persistent-token and CSRF Studio contract assertions.
- `wave1_browser_acceptance.js`: real Chrome cookie/storage/reload/logout/replay and project workflow evidence.
- `wave1_session_restart_acceptance.py`: redacted, in-memory-cookie, actual-process restart harness.
- `wave1-session-security-evidence/`: disposable synthetic runtime, screenshots, and machine-readable results.
- `WAVE_1_SESSION_SECURITY_REPORT.md`: this report.

All earlier Wave 1 source changes and acceptance artifacts were preserved. No commit, push, merge, rebase, deployment, provider call, PostgreSQL work, or production migration occurred.

## Test Matrix

| Control / journey | Mode | Result | Evidence |
| --- | --- | --- | --- |
| Cookie creation and flags | Unit/integration | PASS | Development host-only cookie is HttpOnly/Lax; production `__Host-` cookie is Secure/HttpOnly/Lax; no Domain. |
| No browser bearer response/storage | Unit + Chrome | PASS | Browser login JSON has no token; persisted state contains only hashes; Chrome found no auth token or actor record in local storage and could not see the session cookie through `document.cookie`. |
| Missing/invalid/rotated CSRF | Integration | PASS | Missing, invalid, mismatched, and stale CSRF returned 403; matched cookie/header/hash succeeded. |
| Cross-origin protection | Integration | PASS | Cross-site login and authenticated cross-origin mutation returned 403. |
| Session fixation | Integration | PASS | Re-login changed the identifier and revoked the old session as `login_rotation`; old identifier returned 401. |
| Idle, absolute, revoked, and tenant-mismatched session | Integration | PASS | Each state failed closed with 401. |
| Explicit API transport | Integration | PASS | Disabled by default; explicit enablement and transport required; no browser cookie or CSRF contract used. |
| Login, reload, logout, cross-tab, replay | Chrome 154.0.8037.98 | PASS | `wave1-session-security-evidence/browser-4/browser-results.json`; screenshots `01` through `07`. |
| Duplicate project submit and failure recovery | Chrome | PASS | One POST/one project under double activation; pending state, failed-save message, draft retention, and control recovery passed. |
| Process restart and recovery | Uvicorn + SQLite, three processes | PASS | `wave1-session-security-evidence/restart-20261022-1/restart-session-results.json`. Session, project, workspace version, and tenant boundary survived restart; logout survived another restart; copied cookie returned 401; no secret was written to evidence. |
| Focused regression | `unittest` | **12/12 PASS** | Session suite plus Studio and projection-failure checks, 7.157 seconds in the final focused run. |
| Complete repository regression | `unittest discover` | **299/299 PASS** | 209.766 seconds; zero failures/errors/skips. Expected failure-injection logging and FastAPI lifespan deprecation warnings remain non-failing. |
| Diff integrity | Git | PASS | `git diff --check` produced no whitespace errors; only existing line-ending warnings were reported. |

## Real-Browser Evidence

The accepted run used installed Google Chrome 154.0.8037.98 through Playwright against `127.0.0.1` with a new disposable JSON store. Nine recorded checks passed:

1. Unauthorized trusted setup rejected.
2. Authorized trusted setup succeeded without credential/token disclosure.
3. Invalid login produced visible feedback.
4. Valid login established an HttpOnly session with no persistent browser bearer token.
5. Page reload restored the authenticated workspace.
6. Logout propagated to a second tab and copied-cookie replay returned 401.
7. Duplicate project activation produced one request and one record.
8. Synthetic save failure preserved the draft and restored the control.
9. Browser console contained only expected negative-path resource errors.

The earlier `browser-2` run correctly exposed the cross-tab CSRF rotation defect. That design was replaced. `browser-4` is the final accepted run.

## Mapping To Wave 1 Gates

| Gate | Disposition after this work |
| --- | --- |
| `RCQA-015` session/logout/stale state | **FIXED and verified** for browser/API/restart modes. Server revocation, expiry, fixation rotation, reload, cross-tab propagation, actor clearing, and rejected replay are evidenced. |
| `RCQA-001` secure initialization | **No regression**; authorized and unauthorized setup passed in real Chrome. Public setup remains disabled unless explicitly configured. |
| `RCQA-003`, `RCQA-004` bootstrap/error disclosure | **No regression** in 299-test suite and browser setup/login paths. |
| `RCQA-006` duplicate operations | **No regression**; Chrome double activation produced one project, and full idempotency tests passed. |
| `RCQA-014` unsupported outbound channels | **No regression**; email remains disabled/unconfigured and deferred channels remain rejected by the full suite. |
| `RCQA-005` historical activity ownership | Implementation and synthetic dry-run tests remain present, but real-data apply remains **BLOCKED pending separate reviewed-data approval**. |

## Deployment Assumptions And Residual Risks

1. Internet deployment must terminate trusted HTTPS, preserve the effective public origin, set `LOGITRACK_PUBLIC_ORIGIN`, and use an explicit restrictive `LOGITRACK_API_ALLOW_ORIGINS`. Production must not set insecure-cookie development mode.
2. The CSRF nonce is intentionally JavaScript-readable; it is not a bearer credential. An XSS defect could still act as the current user, so CSP, dependency review, output encoding, and browser security headers remain release-hardening responsibilities.
3. Session and idempotency state still use the current canonical JSON/SQLite architecture and single-writer assumptions. The process restart test proves current behavior, not horizontal multi-process safety.
4. Explicit API-token login remains an optional disabled capability. Enabling it requires an approved operational client policy; no production enablement is authorized here.
5. Historical activity ownership apply remains blocked until the reviewed hash, backup, ambiguity report, tenant scope, and explicit approval gate are satisfied.
6. Full internet release still depends on later security, PostgreSQL, methodology, export, accessibility, localization, provider-sandbox, backup/restore, and deployment gates.

## Acceptance Recommendation

**Session security: PASS.** The previous JavaScript-accessible persistent bearer-token blocker is closed with implementation and independent evidence.

**Wave 1 overall: CONDITIONAL.** Keep the existing condition for historical activity ownership migration approval; do not infer approval to mutate real data.

**Internet release: NO-GO.** This work removes one major blocker but does not complete the full release-readiness programme.

## Immediate Next Controlled Package

The next package is **PostgreSQL Primary Persistence Migration and PostGIS Foundation**. It must begin only after review of this report and must precede Wave 2 methodology implementation. The package must assess and safely migrate canonical JSON/SQLite and projection behavior, then verify tenant isolation, transactions, schema migrations, sessions, CSRF/session persistence, idempotency, workspace versions, backup/restore, rollback, reconciliation, concurrent writes, and process restart recovery. PostGIS must be provisioned and tested before Wave 3 geographic functionality. No PostgreSQL or PostGIS implementation was performed here.
