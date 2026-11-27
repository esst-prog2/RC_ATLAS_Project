# HW11 authentic presentation assets

Prepared 2026-11-26. Seven untouched application screenshots, each **1920 x 1080**. No slides have been created.

| Screenshot | Role | Stage and source |
|---|---|---|
| [01-portfolio-overview.png](01-portfolio-overview.png) | Programme Manager | Current accepted UI-01, Coastal Resilience and Livelihoods Programme selected. Portfolio-wide overview; existing UI-01 synthetic fixture, not the historical HW10 task session. Source: http://127.0.0.1:8769/studio (guarded UI-01 runtime) |
| [02-task-creation-assignment.png](02-task-creation-assignment.png) | Programme Manager | Filled creation form before Save: Review Buzi field report; Aline Duarte (Demo) assignee, Raimundo Cumba (Demo) validator, Teresa Mbanze (Demo) approver; validation plus approval, evidence required, deadline 2026-12-01. Source: [docs/hw10/authentic-demo/evidence/record/programme_manager-create_before.png](../../../docs/hw10/authentic-demo/evidence/record/programme_manager-create_before.png) |
| [03-task-in-progress.png](03-task-in-progress.png) | Field Coordinator | The same Buzi task is in progress at 25%, viewed by Aline Duarte (Demo). Source: [docs/hw10/authentic-demo/evidence/record4/field_coordinator-started.png](../../../docs/hw10/authentic-demo/evidence/record4/field_coordinator-started.png) |
| [04-task-submission.png](04-task-submission.png) | Field Coordinator | Filled form immediately before Submit for Validation: progress 100%, evidence note Synthetic Buzi field report reviewed, comment Ready for independent validation. Header still shows pre-submission state; this image does not claim submission has already completed. Source: [docs/hw10/authentic-demo/evidence/record4/field_coordinator-submit_before.png](../../../docs/hw10/authentic-demo/evidence/record4/field_coordinator-submit_before.png) |
| [05-task-validation.png](05-task-validation.png) | MEAL Officer | Raimundo Cumba (Demo) views the submitted Buzi task, pending validation at 100%, with evidence and Validate / Request Rework controls. Captured immediately before validation. Source: [docs/hw10/authentic-demo/evidence/record4/meal_officer-validate_before.png](../../../docs/hw10/authentic-demo/evidence/record4/meal_officer-validate_before.png) |
| [06-final-approval.png](06-final-approval.png) | Programme Manager | Teresa Mbanze (Demo) views the same task after approval: Completed, stage Complete, Approved, with evidence and approval history. Source: [docs/hw10/authentic-demo/evidence/record4/programme_manager-approved.png](../../../docs/hw10/authentic-demo/evidence/record4/programme_manager-approved.png) |
| [07-completed-workplan.png](07-completed-workplan.png) | Programme Manager | Completed-filter Workplan shows Review Buzi field report at 100%, owned by Aline Duarte (Demo), with one evidence entry. Source: [docs/hw10/authentic-demo/evidence/record4/programme_manager-completed_table.png](../../../docs/hw10/authentic-demo/evidence/record4/programme_manager-completed_table.png) |

## Context and authenticity

Images 02-07 are byte-for-byte copies of retained native HW10 screenshots from the authentic application recording sessions, chosen for clear controls and readable text. The original screenshots and raw recordings remain in their existing HW10 locations. No image was generated, reconstructed, cropped, rescaled, retouched or relabelled.

Workflow: **Review Buzi field report**, task `task_proj_resilience_review_buzi_field_report`, project **Coastal Resilience and Livelihoods Programme** (`proj_resilience`). Aline Duarte (Demo) executes, Raimundo Cumba (Demo) validates, and Teresa Mbanze (Demo) approves. The deadline is 1 December 2026 (the creation form displays 12/01/2026 in its native locale). Evidence is a synthetic text note, not a real field-report attachment. Completion demonstrates task workflow, not verified programme outcomes.

Image 01 was captured from the actual accepted UI-01 runtime at commit `bbeed8433905e044c7df8f9c7a8ed2364aa1d37f`, using the existing synthetic Programme Manager account and the same project selection. It intentionally uses the current accepted UI rather than the historical HW10 version. Its account display name, date-sensitive counts and fixture differ from the historical task demonstration. It must not be presented as the same session or as an overview containing the completed HW10 task.

The current overview authentically displays Portfolio Health as 0%. The existing missing/NOT_ASSESSED-versus-zero concern remains unresolved; this image is visual evidence of the current interface, not certification of analytical correctness.

See [HW10 workflow record](../../hw10/authentic-demo/WORKFLOW_RECORD.md) and [persisted workflow evidence](../../hw10/authentic-demo/evidence/record4/workflow.json). Native source paths, resolutions and SHA-256 hashes are in [assets-manifest.json](assets-manifest.json).

## Official logo

- [rc-atlas-logo.png](rc-atlas-logo.png): unchanged copy of `promo/logo.png`, 192 x 128. Prefer the @2x original where appropriate.
- [rc-atlas-logo@2x.png](rc-atlas-logo@2x.png): unchanged copy of `promo/logo@2x.png`, 384 x 256. Prefer the @2x original where appropriate.

## Review and preservation

[Open the image review gallery](index.html). Each image links to the original full-resolution asset. The gallery is an asset index, not a presentation.

All seven registered worktrees and their HEADs were preserved. Product source hashes and all six original workflow image hashes match the initial record. No application changes, reseeding, regression tests, commits, merges, pushes or UI-01 implementation were performed. The existing guarded inspection server remains available at http://127.0.0.1:8769/studio.
