# HW9 content evidence and proposed direction

Status: source review complete; product-owner approval of content direction pending. This is a planning artifact, not public page content or an approved Impeccable shape brief.

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

## Content direction awaiting approval

Recommendation: emphasize the concrete handoff from assigned work to approved results. The original tagline, From institutional data to coordinated action, remains an owner suggestion rather than approved final copy.

Proposed primary audience: programme managers, field coordinators, and monitoring/evaluation teams coordinating institutional project work. Organization categories and adoption claims remain unconfirmed; name no real institution as a customer.

Proposed headline: **RC Atlas - From assigned work to approved results.**

Draft supporting copy: **Keep responsibilities, progress, and review checkpoints together. RC Atlas helps project teams assign tasks, track delivery, and follow work through validation and approval.**

Draft problem statement: **A task is not finished just because someone has submitted it. Teams also need to know who owns the work, what is due, and which review comes next. RC Atlas makes those handoffs visible in a shared project workflow.**

Draft capability labels:

- Assign responsibility: give each task an owner and a deadline.
- Track progress: follow assigned work as it moves forward.
- Review submissions: validate work before its final approval in the featured workflow.
- See the outcome: follow the task through to its completed state.

Draft workflow: **Assign -> Work -> Submit -> Validate -> Approve.** Explain that the featured example uses both validation and approval. Use generic role names rather than reproducing fictional people that could be mistaken for real endorsements.

Draft exploration section: **Explore RC Atlas. This course project runs locally. Visit the GitHub repository to read the workflow and find setup instructions.** Proposed primary action: **Explore on GitHub**. A secondary action can link directly to the documented local setup.

Not approved for ready-to-use marketing claims: donor reports, AI narratives, budgeting, predictive analytics, mapping, external notification providers, data-collection integrations, mobile apps, subscription management, and production cloud hosting. README.md explicitly excludes these from the assessed workflow, even where supporting code exists.

## Existing visual identity evidence

logitrack_studio.html defines navy #123b5d, teal #11828a, dark text #0f172a, light blue-gray #dde6ef, and white surfaces. Existing font stacks use Segoe UI for interface text and Aptos Display for display text. These are incumbent evidence, not newly selected promo styling. Preserve the identity without redesigning the application. No reference material from UI-01 was modified or used as a new baseline.

## Remaining owner gates and next steps

1. Confirm the content focus and headline, then complete the office-hours content decisions.
2. Capture confirmed product truth in PRODUCT.md through Impeccable init; no product record has been invented.
3. Produce and confirm the shape brief without page code.
4. Generate visual variants in the browser and wait for the owner's selection.
5. Critique the selected variant as a classmate, professor, and unfamiliar visitor; apply substantive revisions only after approval.
6. Implement, inspect the exact public file set, obtain publication approval, publish through GitHub Pages, and verify the public URL.

Screenshot evidence has not been selected or captured. Only genuine UI with verified synthetic data is allowed. No canonical runtime data, backups, Site.txt, or credentials were read. The future video section must have useful content without an empty or broken player; no video generation is part of HW9.
