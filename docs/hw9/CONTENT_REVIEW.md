# HW9 content evidence and proposed direction

Status: product owner approved the broader institutional positioning and original headline on 2026-11-12. Capability wording is grounded in the expanded source review below; visual selection and publication remain unapproved. This is a planning artifact, not public page content or an approved Impeccable shape brief.

## Tool availability

- gstack office-hours: installed skill and runtime available. Invoked gstack-skill-start --skill office-hours --model gpt-6-astra through Git Bash; returned protocol 1 and interactive session 1-1794469369-f5997c2e. Installed version reported as 1.91.216.0. Context recovery and prior-learning search also ran.
- Runtime limitation: gstack reported that a live process retained its lease directory and this session held no workflow lease. No upgrade, lease repair, external model review, or automatic shipping was attempted. Telemetry and artifact sync reported off.
- Impeccable: installed metadata and successful context command confirm version 4.7.0. Context identified an existing visual implementation, no PRODUCT.md, no DESIGN.md, and no active automatic design detector. Existing .impeccable/config.json was read and left untouched; it disables hooks.
- Both tools reported newer releases; none was installed. Required workflow is still in progress, not completed.

## Verified product evidence

Evidence below is static inspection of committed source and tests at baseline 5d487f8ff2fff3a864bc5405a90d2555ee3b5218. Tests were read, not executed. The application and canonical runtime were not started or inspected.

| Visitor-facing claim | Evidence | Limit |
|---|---|---|
| RC Atlas is a local browser workspace for managing project implementation. | README.md introduction and docs/DEVELOPMENT.md startup instructions | No public application deployment or commercial availability claim. |
| Assign tasks to project users and set deadlines. | README.md sections 1-3; assignment_aware_task_workflow_tests.py create_task; workplan_project_members_contract_tests.py | Do not claim unlimited organizations, custom roles, or onboarding. |
| Assigned staff can start work, update progress, and submit work for review. | README.md demo; assignment_aware_task_workflow_tests.py start and test_two_stage_golden_journey | Illustrate the configured workflow; avoid implying every task requires identical checkpoints. |
| Validation and approval can be separate checkpoints. | test_two_stage_golden_journey and test_hw5_two_stage_workflow_requires_approval_before_completion | Other configured modes exist; this is the featured course example. |
| Completed work appears in the workplan with its current state. | README.md sections 1-4; logitrack_studio.html | No promised performance numbers, institutional results, or operational certification. |
| Actions depend on assigned responsibilities. | README.md sections 3-4; test_non_assignee_is_rejected_without_mutation | Describe user behavior, not an absolute security guarantee. |
| Developers can explore the source and follow local setup instructions. | Public repository URL supplied by the owner; docs/DEVELOPMENT.md | Do not suggest visitors can sign up for a hosted app. A fresh setup requires initialization and contains no included runtime data. |

## Approved content direction

Owner decision, 2026-11-12: retain **RC Atlas — From institutional data to coordinated action.** Present the assignment-to-approval workflow as the practical demonstration, not the whole product. Highlight verified project management, monitoring, indicators, analytics, and reporting capabilities in support of institutional accountability and decision-making.

Primary audience: programme managers, field coordinators, and monitoring/evaluation teams coordinating institutional project work. Do not imply a real institution is a customer or that production adoption has been verified.

### Proposed publication copy

**RC Atlas — From institutional data to coordinated action.**

Bring project work, monitoring information, and indicator evidence into one workspace. RC Atlas helps institutional teams follow responsibilities, examine results, and prepare information for review and decisions.

**A clearer picture of the work and the evidence.**

Institutional decisions need more than a completed-task count. Teams need to see who is responsible, how delivery is progressing, what indicators measure, and what the available data can support. RC Atlas brings these perspectives together while keeping work completion distinct from measured results.

**Five connected capabilities**

- **Project management.** Organize project work, assign responsibility, set deadlines, and follow tasks through review.
- **Monitoring.** Follow operational progress and reporting records so teams can see what has been submitted and what still needs attention.
- **Indicators.** Examine indicator baselines, targets, and results. For configured indicators, inspect the selected calculation method and reporting period.
- **Analytics.** Understand how supported indicator results are calculated, with explanations, source context, and data-quality checks for the selected indicator. Missing configuration and unsupported calculations are identified explicitly.
- **Reporting.** Review recorded information and prepare report previews for discussion. Report previews are part of the current project; fully governed export snapshots remain future work.

**Accountability, demonstrated through one task.**

A manager assigns the work and its deadline. A coordinator updates progress and submits the result. A reviewer validates the submission. The manager approves completion. This example uses both validation and approval checkpoints; other configured task flows exist.

**Assign → Work → Submit → Validate → Approve.**

A completed task shows that the work passed its delivery checks. Indicator results provide a separate view of what the data shows. Keeping these distinct helps teams discuss both delivery and evidence without treating task completion as proof of impact.

**Explore the project.**

RC Atlas is a locally run course project. Explore its public repository to understand the workflow, inspect the source, and follow the local setup instructions. The promotional website does not host the application.

Primary action: **Explore on GitHub**. Secondary action: **Local setup guide**. Workflow anchor: **See the workflow**.

**Current scope.**

Indicator analysis requires configured methods and suitable data. Some wider analytical and reporting functions remain under development. This page describes supported capabilities and does not offer a production-hosted service.

### Expanded claim evidence and boundaries

Static inspection at baseline 5d487f8ff2fff3a864bc5405a90d2555ee3b5218; no fresh test-pass or live acceptance claim.

| Area | Supporting implementation and contract | Publication boundary |
|---|---|---|
| Project management | Assignment workflow tests; project member tests; api/logical_framework_routes.py includes result and indicator-link operations | Describe the verified operational journey; do not call the logical-framework builder complete. |
| Monitoring | services/reporting.py:list_reporting_records; workflow status/progress in README and tests; consumer matrix C19 and C41 | Reporting records and operational task progress are different from calculated indicator achievement. |
| Indicators | api/methodology_routes.py:get_methodology/get_calculation; Studio How is this calculated? panel; docs/WAVE_2_PACKAGE_1_CONTRACT.md | Approved method definitions and explicit source, period, and version are required. No automatic configuration or full authoring UI claim. |
| Analytics | services/analytical_consumers.py:calculate_indicator/indicator_kpi/quality_report; docs/WAVE_2_PACKAGE_2_CONTRACT.md; Studio renderMethodologyResult | Supported selected indicator calculations and explanations only. Quality is rule-specific and scoped; no overall fitness score, prediction, statistical trend, or cross-project aggregate claim. |
| Reporting | services/reporting.py:list_reporting_records and narrative/quality accessors; services/demo_workspace.py:report_preview; sec01_report_preview_tests.py; consumer matrix C28-C31 | Report previews and recorded information exist. Do not promise production donor reports, governed immutable exports, or certified PDF/PPTX output. |

The README's assessed course workflow is narrower than the integrated platform source. Exclusion from that homework demonstration does not prove a broader feature is absent; use the implementation contracts to determine its supported scope. Conversely, a route or visible menu alone does not prove readiness.

Keep out of ready-to-use claims: predictive analysis, statistical trends, portfolio progress aggregation, cross-currency totals, universal data-quality scoring, risk scoring, AI narratives, complete budgeting, mapping, external notification/data-collection integrations, subscription management, production cloud hosting, and fully governed report/export snapshots.

## Existing visual identity evidence

logitrack_studio.html defines navy #123b5d, teal #11828a, dark text #0f172a, light blue-gray #dde6ef, and white surfaces. Existing font stacks use Segoe UI for interface text and Aptos Display for display text. These are incumbent evidence, not newly selected promo styling. Preserve the identity without redesigning the application. No reference material from UI-01 was modified or used as a new baseline.

## Remaining owner gates and next steps

1. Content focus and headline confirmed by the owner; exact final copy and the completed office-hours design record remain reviewable.
2. Capture confirmed product truth in PRODUCT.md through Impeccable init, using the explicit owner answer and source evidence.
3. Produce and confirm the shape brief without page code.
4. Generate visual variants in the browser and wait for the owner's selection.
5. Critique the selected variant as a classmate, professor, and unfamiliar visitor; apply substantive revisions only after approval.
6. Implement, inspect the exact public file set, obtain publication approval, publish through GitHub Pages, and verify the public URL.

Screenshot evidence has not been selected or captured. Only genuine UI with verified synthetic data is allowed. No canonical runtime data, backups, Site.txt, or credentials were read. The future video section must have useful content without an empty or broken player; no video generation is part of HW9.
