## Context

See proposal.md for motivation. The current Studio task drawer routes non-manager users to Workplan through a generic view switch, so the drawer remains open over controls that are already authorized correctly by the Workplan renderer. DemoWorkspaceService.create_task derives a stable coordination activity ID but appends a new activity whenever activity_id is omitted. Canonical data is saved before derived synchronization, but migration/sync_helpers.py currently replaces repository-backed canonical collections during hydration, and the composition-root synchronization path skips repository-domain synchronization when the broad relational projection fails.

The current JSON or SQLite snapshot remains authoritative. The relational tables and repository-backed domain tables remain derived compatibility infrastructure. The existing task routes, authentication model, workflow transitions, schemas, and frontend architecture are constraints.

## Goals / Non-Goals

**Goals:**
- Restore the browser Golden Journey by handing a selected drawer task to the existing Workplan controls.
- Prevent new duplicate default coordination activities and reject corrupted or cross-scope activity identity safely.
- Ensure present canonical collections cannot be replaced by stale derived repository state.
- Attempt independent derived synchronization phases and retain truthful diagnostics after canonical commit.
- Provide a guarded, testable, dry-run-first repair for the known local duplicate without losing tasks.

**Non-Goals:**
- Redesign task workflow, Workplan, authentication, sessions, tokens, snapshot or relational schemas, tenant security, or Logical Framework.
- Fix the Project Configuration persistent-view defect or alter Portfolio, Executive Snapshot, Risks, Reports, or visual design.
- Introduce PostgreSQL, queues, React, TypeScript, RC Atlas Next, or new infrastructure.

## Decisions

### 1. Use a one-shot drawer-to-Workplan target instead of duplicating controls

Add a focused navigation function conceptually named openTaskWorkflowControls(taskId). It stores the selected ID in transient Studio state, closes the drawer, then activates Workplan. After the existing hydration and render sequence completes, a small targeting function locates the matching task card, opens its existing details element, scrolls it into view, and focuses the progress input or first enabled workflow action. The target is cleared after success and also cleared with a non-authorizing warning when targeting fails.

The Workplan task filter and taskWorkflowActionButtons remain the only frontend workflow eligibility implementation. The drawer does not render a second Field form or reproduce permission and state rules.

Alternative considered: render Field mutation controls directly in the drawer. Rejected because it would duplicate workflow authorization, input collection, transition availability, and event handling.

### 2. Resolve activity identity before mutating the request-local aggregate

Task creation will derive the default ID from the canonical project ID when activity_id is absent. A focused resolver will inspect activity occurrences by ID across project operation containers, then accept only exactly one compatible match in the requested organization and project. Compatibility requires the activity to be in the expected project container, carry matching organization ownership, expose the expected activity/task structure, and be usable as a coordination container. The title is descriptive and is not identity.

Zero compatible matches create one staged default activity. More than one scoped match, any foreign or cross-project occurrence of the same stable ID, or a malformed scoped match produces a conflict before data is mutated. Explicit activity IDs use the same scoped resolution principle. The activity and task are appended only after project, assignee, activity, task ID, and payload validation succeeds; audit staging and canonical save retain the existing operation order.

Alternative considered: choose the first matching activity or deduplicate during every task creation. Rejected because silent selection hides corrupted state and online repair would mix migration with a business request.

### 3. Determine hydration authority from serialized key presence

Repository-domain hydration will decide independently for users, notification_rules, and reporting_records whether the original serialized snapshot contains the domain key. If present, its value is preserved even when empty. Only a missing key can invoke the existing legacy backfill from a ready repository projection. This decision occurs before domain-model defaults can collapse absent and present-empty into the same value.

Alternative considered: compare timestamps or row counts between snapshot and projection. Rejected because the current derived stores do not provide a reliable cross-domain version contract and such comparison could make projection data authoritative.

### 4. Separate broad projection and repository-domain synchronization phases

After the canonical save, the composition root will attempt broad relational projection synchronization and repository-backed domain synchronization as separate phases. A broad projection exception is captured and diagnosed without preventing the repository phase from running. A repository-phase exception is recorded independently. After both attempts, the existing strict/non-strict policy determines whether a synchronization error is returned or raised; diagnostics must identify which phase failed and must never describe the canonical save as rolled back.

This order specifically allows a freshly persisted user token to reach the repository-backed users table even when an unrelated activity projection fails. Hydration precedence remains the primary safety rule, so stale repository data still cannot replace present canonical users if repository synchronization also fails.

Alternative considered: only catch the duplicate activity projection error. Rejected because any future broad projection failure could recreate the stale-authentication condition.

### 5. Implement repair as an explicit offline operation with rehearsal

Create a focused migration/repair utility rather than running normalization during startup or ordinary task creation. Dry-run is the default. It loads canonical state without repository overlay, verifies the expected organization, project, duplicate stable ID, 11 activity and 20 task counts, duplicate ownership, task IDs, and both named browser-created tasks, then builds a corrected copy in memory.

The corrected copy retains one valid coordination activity, appends the second container's task objects without reconstructing them, stable-deduplicates linked indicator IDs, removes only the redundant container, and validates unique activity and task IDs plus ownership. Before canonical mutation, apply mode requires server-stop confirmation, creates a timestamped byte-for-byte canonical backup, and rehearses serialization and relational projection rebuilding against a temporary projection database. Only then does it perform one atomic canonical save and rebuild the configured derived projection from the corrected snapshot.

If a precondition, staged postcondition, or rehearsal fails, canonical state is untouched. If the production projection rebuild fails unexpectedly after canonical save, the command reports the canonical commit and failed reconciliation separately, preserves the backup, and exits unsuccessfully without claiming rollback. The fixed hydration rule prevents that stale projection from overriding corrected canonical state.

Alternative considered: reseed or manually edit the snapshot. Rejected because either could discard operational data and would not provide repeatable validation or rollback evidence.

### 6. Protect behavior at three testing levels

Service/API tests will cover idempotent activity creation, collisions, atomic denial, token survival, hydration presence semantics, and repair dry-run/apply behavior using isolated temporary stores. Studio structural tests will verify the one-shot navigation sequence, drawer closure, authoritative action reuse, and targeting/focus hooks without pretending to be browser proof. Existing Course MVP, Logical Framework, and tenant-security suites remain regression gates. Final acceptance requires a real browser Golden Journey and one MEAL return/resubmission branch.

## Risks / Trade-offs

- [Risk] Splitting synchronization phases could obscure which strict-mode exception should be surfaced when both fail. -> Mitigation: retain separate phase diagnostics, attempt both, and apply a deterministic error-priority rule documented in tests without changing canonical commit truth.
- [Risk] DOM targeting may race asynchronous Workplan hydration. -> Mitigation: invoke targeting only after the existing Workplan render completes, use one-shot state, and clear it on both success and terminal failure.
- [Risk] Stable activity IDs can collide across project containers in malformed legacy data. -> Mitigation: scan by ID across containers and fail closed instead of reusing a match based only on the current dictionary key.
- [Risk] A repair utility can damage local data if assumptions drift. -> Mitigation: exact identity/count guards, dry-run default, mandatory backup, staged copy validation, projection rehearsal, one canonical save, and explicit postcondition checks.
- [Trade-off] Repository backfill remains available for truly absent legacy keys. This preserves compatibility but keeps a transitional path that must eventually be retired when repository migration policy is formalized.

## Migration Plan

1. Implement and verify hydration precedence and synchronization isolation against temporary stores before touching local runtime data.
2. Implement and verify idempotent activity resolution and all workflow regressions.
3. Implement the repair utility and prove dry-run and apply behavior against an isolated fixture matching the known 11-activity and 20-task state.
4. Stop the local server, run dry-run against the real canonical workspace, review the report, create the required timestamped backup, and run apply only under separate explicit authorization.
5. Verify the corrected 10-activity and 20-task canonical state, rebuild the derived projection, and confirm authentication for existing users without changing passwords or accounts.
6. Apply the minimal drawer navigation patch and run automated regressions.
7. Run the manual Golden Journey and return branch, including refresh/re-login persistence checks.

Rollback for application code is the pre-change Git checkpoint. Rollback for the one-time data repair is the timestamped canonical backup; it is used only with the server stopped and followed by projection reconciliation. No automatic rollback may substitute stale projection state for canonical state.
