import unittest
from pathlib import Path


class AssignmentAwareStudioUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path(__file__).with_name("logitrack_studio.html").read_text(encoding="utf-8")

    def block(self, start, end):
        return self.html.split(start, 1)[1].split(end, 1)[0]

    def test_project_members_drive_capability_filtered_canonical_selectors(self):
        selectors = self.block("function syncTaskRoutingControls", "function populateTaskAssigneePicker")
        self.assertIn("projectRoutingMembers(workplan)", selectors)
        self.assertIn('projectMemberHasPermission(member, "UPDATE_TASK_PROGRESS")', selectors)
        self.assertIn('projectMemberHasPermission(member, "VALIDATE_EVIDENCE")', selectors)
        self.assertIn('projectMemberHasPermission(member, "APPROVE_TASKS")', selectors)
        self.assertIn('option.value = textSafe(member.user_id', self.html)
        self.assertIn('option.textContent = textSafe(member.display_name', self.html)
        self.assertNotIn("eligible_assignees", selectors)
        self.assertNotIn("role_label", selectors)
        self.assertNotIn("field_coordinator", selectors)
        self.assertNotIn("meal_officer", selectors)
        self.assertNotIn("programme_manager", selectors)

    def test_review_modes_control_reviewer_visibility_and_clear_stale_values(self):
        selectors = self.block("function syncTaskRoutingControls", "function populateTaskAssigneePicker")
        for value in ("direct_completion", "validation", "approval", "validation_and_approval"):
            self.assertIn(f'value="{value}"', self.html)
        self.assertIn('const needsValidator = ["validation", "validation_and_approval"].includes(mode);', selectors)
        self.assertIn('const needsApprover = ["approval", "validation_and_approval"].includes(mode);', selectors)
        self.assertIn('validatorField?.classList.toggle("hidden", !needsValidator)', selectors)
        self.assertIn('approverField?.classList.toggle("hidden", !needsApprover)', selectors)
        self.assertIn('if (!needsValidator) validatorSelect.value = "";', selectors)
        self.assertIn('if (!needsApprover) approverSelect.value = "";', selectors)

    def test_separation_of_duties_updates_candidates_and_form_state(self):
        selectors = self.block("function syncTaskRoutingControls", "function populateTaskAssigneePicker")
        listeners = self.block('document.getElementById("createTaskBtn")', 'document.getElementById("myWorkInboxList")')
        self.assertIn('textSafe(member.user_id || "", "") !== assigneeId', selectors)
        self.assertIn('textSafe(member.user_id || "", "") !== previousApprover', selectors)
        self.assertIn('textSafe(member.user_id || "", "") !== validatorId', selectors)
        self.assertIn('if (validator?.value === selectedId) validator.value = "";', listeners)
        self.assertIn('if (approver?.value === selectedId) approver.value = "";', listeners)
        self.assertIn('if (approver?.value === event.target.value) approver.value = "";', listeners)
        self.assertIn('if (validator?.value === event.target.value) validator.value = "";', listeners)

    def test_evidence_policy_is_independent_and_filters_only_when_required(self):
        selectors = self.block("function syncTaskRoutingControls", "function populateTaskAssigneePicker")
        composer = self.block("async function createOperationalTaskFromForm", "function clearProtectedPanels")
        self.assertIn('id="taskEvidenceRequiredInput"', self.html)
        self.assertIn('value="false" selected', self.html)
        self.assertIn('value="true"', self.html)
        self.assertIn('const evidenceRequired = evidenceSelect.value === "true";', selectors)
        self.assertIn('(!evidenceRequired || projectMemberHasPermission(member, "SUBMIT_EVIDENCE"))', selectors)
        self.assertIn('evidence_required: document.getElementById("taskEvidenceRequiredInput")?.value === "true"', composer)

    def test_creation_payload_uses_canonical_ids_and_omits_irrelevant_reviewers(self):
        composer = self.block("async function createOperationalTaskFromForm", "function clearProtectedPanels")
        self.assertIn("assignee_user_id: assigneeUserId", composer)
        self.assertIn("review_mode: reviewMode", composer)
        self.assertIn("if (needsValidator) payload.validator_user_id = validatorUserId;", composer)
        self.assertIn("if (needsApprover) payload.approver_user_id = approverUserId;", composer)
        self.assertNotIn("assignee_username:", composer)
        self.assertIn("separation of duties", composer)

    def test_routing_summary_and_stage_labels_are_policy_aware(self):
        assignee_display = self.block("function taskAssigneeDisplayName", "function taskRoutingSummaryRows")
        summary = self.block("function taskRoutingSummaryRows", "function taskRoutingSummaryHtml")
        status = self.block("function taskWorkflowStatusLabel", "function taskRoutingResolved")
        timeline = self.block("function taskTimelineEntries", "function taskMetaLabel")
        self.assertIn("taskRoutingResolved(task)", assignee_display)
        self.assertIn("projectRoutingMemberName(assigneeId)", assignee_display)
        self.assertIn("Legacy routing", assignee_display)
        self.assertNotIn("assignee_username", assignee_display)
        self.assertNotIn("assignee_name", assignee_display)
        self.assertIn("Assigned to", summary)
        self.assertIn("Review path", summary)
        self.assertIn("Validator", summary)
        self.assertIn("Approver", summary)
        self.assertIn("Evidence", summary)
        self.assertIn("Current stage", summary)
        self.assertIn("Legacy routing", summary)
        self.assertIn("Review routing not yet configured", summary)
        self.assertIn('task?.review_stage || "", "").toLowerCase() === "approval"', status)
        self.assertIn("Pending Approval", status)
        self.assertIn("Pending Validation", self.html)
        self.assertNotIn("pending_approval", self.html)
        self.assertIn('taskReviewMode(task) === "approval"', timeline)
        self.assertIn("Submitted for approval", timeline)
        self.assertIn("Submitted for validation", timeline)

    def test_action_controls_use_actor_routing_policy_and_stage(self):
        actions = self.block("function taskWorkflowActionButtons", "function operationalTaskCardHtml")
        execution = self.block("function taskExecutionActionAllowed", "function taskWorkflowActionButtons")
        self.assertIn("currentActorUserId()", execution)
        self.assertIn("task.assignee_user_id", execution)
        self.assertIn('hasPermission("UPDATE_TASK_PROGRESS")', execution)
        self.assertIn('data-task-action="complete"', actions)
        self.assertIn("Complete Task", actions)
        self.assertIn("Submit for Validation", actions)
        self.assertIn("Submit for Approval", actions)
        self.assertIn('actorId === textSafe(task.validator_user_id', actions)
        self.assertIn('actorId === textSafe(task.approver_user_id', actions)
        self.assertIn('stage === "validation"', actions)
        self.assertIn('stage === "approval"', actions)
        self.assertNotIn("currentOperationalProfile", actions)
        self.assertNotIn("field_coordinator", actions)
        self.assertNotIn("meal_officer", actions)
        self.assertNotIn("programme_manager", actions)

    def test_escalation_legacy_handoff_and_backend_errors_remain_safe(self):
        actions = self.block("function taskWorkflowActionButtons", "function operationalTaskCardHtml")
        handler = self.block("async function handleTaskWorkflowAction", "async function createOperationalTaskFromForm")
        drawer = self.block("function renderTaskDrawer", "function currentOperationalProfile")
        self.assertIn('data-task-action="escalate"', actions)
        self.assertNotIn("assignee_user_id =", actions)
        self.assertNotIn("validator_user_id =", actions)
        self.assertNotIn("approver_user_id =", actions)
        self.assertIn("taskRoutingSummaryHtml(task)", drawer)
        self.assertIn("data-open-task-workflow", drawer)
        self.assertIn("openTaskWorkflowControls", self.html)
        self.assertIn("showMessage(error.message, \"bad\")", handler)
        self.assertIn("complete_execution: true", handler)

    def test_escalation_uses_canonical_execution_authorization(self):
        actions = self.block("function taskWorkflowActionButtons", "function operationalTaskCardHtml")
        execution = self.block("function taskExecutionActionAllowed", "function taskWorkflowActionButtons")

        self.assertIn("const canEscalate = taskExecutionActionAllowed(task);", actions)
        self.assertIn("if (canEscalate)", actions)
        self.assertNotIn('const canEscalate = hasAnyPermission(["ASSIGN_TASKS", "APPROVE_TASKS", "MANAGE_WORKPLAN"]);', actions)
        self.assertIn("taskRoutingResolved(task)", execution)
        self.assertIn("currentActorUserId()", execution)
        self.assertIn("task.assignee_user_id", execution)
        self.assertIn('hasPermission("UPDATE_TASK_PROGRESS")', execution)
        self.assertIn('["not_started", "in_progress", "overdue", "escalated"]', execution)
        self.assertNotIn("assignee_username", execution)
        self.assertNotIn("assignee_name", execution)
        self.assertNotIn("field_coordinator", actions)
        self.assertNotIn("meal_officer", actions)
        self.assertNotIn("programme_manager", actions)


if __name__ == "__main__":
    unittest.main()
