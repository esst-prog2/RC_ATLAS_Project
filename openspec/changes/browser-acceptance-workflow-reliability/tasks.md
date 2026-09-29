## 1. Baseline and Characterization

- [x] 1.1 Run py -m unittest discover -v -p *tests.py before source edits and verify the 180-test security checkpoint baseline passes with zero failures, errors, or skips.
- [x] 1.2 Add focused Studio characterization assertions for the current task-drawer view switch, drawer visibility, Workplan render timing, task-card details controls, and action-generation authority; verify the tests reproduce the blocked Field navigation before implementation.
- [x] 1.3 Add API/service characterization tests for two implicit task creations, project-local defaults, explicit activity lookup, duplicate stable IDs, foreign collisions, and no-save failure behavior; verify the duplicate default activity defect is reproduced.
- [x] 1.4 Add persistence characterization tests for present canonical collections, present-empty collections, absent legacy keys, broad projection failure, repository synchronization ordering, and login token survival; verify the stale projected user can reproduce the pre-fix identity failure.
- [x] 1.5 Build an isolated repair fixture matching org_blue_delta, proj_resilience, duplicate act_proj_resilience_coordination, 11 activities, 20 tasks, and both named browser-created tasks; verify the fixture preserves all task fields needed for lossless comparison.

## 2. Canonical Hydration Precedence

- [x] 2.1 Change repository-domain hydration to test serialized key presence independently for each supported domain and verify present values are returned unchanged.
- [x] 2.2 Protect canonical users from stale repository rows, including present-empty users, and verify a newer canonical token remains valid through the authenticated identity endpoint.
- [x] 2.3 Apply the same present-versus-absent rule to notification_rules and reporting_records and verify projected rows cannot repopulate explicitly empty canonical collections.
- [x] 2.4 Preserve the explicit legacy backfill path only for genuinely absent supported keys and verify mixed present/absent domains are handled independently.

## 3. Projection Failure Isolation

- [x] 3.1 Separate broad relational projection synchronization from repository-backed domain synchronization after canonical save and verify each phase is attempted independently.
- [x] 3.2 Record broad-projection and repository-domain outcomes and errors separately and verify diagnostics never claim canonical rollback after a successful canonical save.
- [x] 3.3 Add failure injection proving an unrelated activity projection failure does not skip user repository synchronization and does not invalidate the newly issued login token.
- [x] 3.4 Add repository-sync failure and combined-failure tests that preserve the current strict/non-strict policy, deterministic surfaced error behavior, canonical authority, and reconciliation diagnostics.

## 4. Idempotent Coordination Activity Resolution

- [x] 4.1 Introduce a focused resolver for implicit and explicit activity identifiers that searches occurrences by ID and verifies organization, project container, and structural compatibility; verify no title comparison determines identity.
- [x] 4.2 Make implicit creation reuse exactly one compatible scoped default, create only when no occurrence exists, and reject duplicate, foreign, cross-project, or incompatible stable-ID states before mutation.
- [x] 4.3 Stage the operations container, optional activity, task, and audit changes until all project, assignee, activity, task-ID, and payload validation succeeds; verify failed requests call no canonical save.
- [x] 4.4 Add tests proving two implicit tasks in one project share one activity while tasks in different projects receive distinct project-local activities.
- [x] 4.5 Add same-ID collision tests for duplicate scoped activities, foreign activities, cross-project activities, malformed activities, and explicit activity_id resolution; verify every invalid case fails closed.
- [x] 4.6 Assert failed task creation leaves activity, task, audit, notification, canonical snapshot, and attributable projection state unchanged.

## 5. Guarded Local Data Repair

- [x] 5.1 Add a focused offline repair utility with dry-run as the default and explicit organization, project, activity, expected-count, and apply inputs; verify ordinary application startup never runs it.
- [x] 5.2 Implement precondition checks for stopped-server confirmation, exact organization/project ownership, two matching default activities, 11 activities, 20 tasks, expected named tasks, and unique task IDs; verify any mismatch aborts without mutation.
- [x] 5.3 Build the repair on a copied aggregate by retaining one valid activity, moving the second container's original task objects, stable-deduplicating linked indicator IDs, and removing only the redundant container; verify every preserved task field and history matches its pre-repair value.
- [x] 5.4 Validate staged postconditions for 10 activities, 20 tasks, one stable coordination activity, unique activity and task IDs, correct ownership, and both browser-created tasks before any canonical write.
- [x] 5.5 Require a timestamped byte-for-byte canonical backup and rehearse serialization plus relational rebuild against a temporary projection database before apply; verify rehearsal failure leaves the canonical target untouched.
- [x] 5.6 Apply the validated repair with one atomic canonical save, rebuild the configured derived projection, and report canonical commit and projection outcome separately; verify unexpected rebuild failure retains the backup and never claims rollback.
- [x] 5.7 Add isolated dry-run, successful apply, precondition failure, postcondition failure, rehearsal failure, and post-commit projection failure tests; verify dry-run is byte-for-byte non-mutating.
- [x] 5.8 Under explicit data-repair authorization with the local server stopped, run and review the real dry-run, preserve its report and timestamped backup, apply once, and verify 11 to 10 activities, 20 retained tasks, successful projection rebuild, and unchanged users, passwords, roles, projects, indicators, reporting, and Logical Framework data.

## 6. Field Drawer Navigation

- [x] 6.1 Add one-shot pending task targeting state and a focused drawer-to-Workplan navigation function that stores the task ID, closes the drawer, and then activates Workplan; verify closure occurs before view activation.
- [x] 6.2 After existing Workplan hydration and rendering, locate the matching task card, expand its existing details controls, scroll it into view, focus the progress input or first enabled action, and clear the pending target; verify the correct assigned task is targeted.
- [x] 6.3 Wire only the existing Open workflow controls drawer action to the focused navigation path and implement graceful target failure that clears state without exposing controls or duplicating permission logic.
- [x] 6.4 Extend Studio UI tests to protect one-shot state, drawer closure, post-hydration targeting, focus behavior, failure cleanup, and continued use of the existing taskWorkflowActionButtons path; verify no visual, Portfolio, Workplan-layout, or unrelated navigation changes.

## 7. Regression and Acceptance Gates

- [x] 7.1 Run focused API and workflow tests proving assigned Field update and submission succeed, another Field user's task remains protected, and failed creation has zero side effects.
- [x] 7.2 Run the Course MVP workflow tests through MEAL validate, Programme Manager approval, MEAL return, Field correction/resubmission, and final completion; verify no validated task status is introduced.
- [x] 7.3 Run the tenant-security and Logical Framework persistence-boundary suites and verify their authentication, isolation, UoW, canonical commit, and projection reconciliation contracts remain unchanged.
- [x] 7.4 Run py -m unittest discover -v -p *tests.py and verify all original 180 tests plus the new reliability tests pass with zero failures, errors, or skips.
- [x] 7.5 Run OpenSpec strict validation, git diff --check, final scope inspection, and status inspection; verify security-tenant-stabilization remains active and untouched, Site.txt remains untouched/untracked, and no out-of-scope module or schema changed.
- [x] 7.6 With the repaired local workspace and server running, manually execute the browser Golden Journey from Programme Manager assignment through Field drawer handoff/update/submission, MEAL validation, Programme Manager approval, Completed persistence after refresh/re-login, then execute one MEAL return and Field correction/resubmission branch; verify no unexpected 401 or 403 occurs.
