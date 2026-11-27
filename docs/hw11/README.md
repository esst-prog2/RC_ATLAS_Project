# RC Atlas final academic presentation

Completed 27 November 2026. Exactly five English slides in widescreen 16:9, designed for a presentation without a live demonstration.

- [Editable PowerPoint](RC_Atlas_Presentation.pptx)
- [Presentation-ready PDF](RC_Atlas_Presentation.pdf)
- [Speaking script](SPEAKER_NOTES.md), also embedded in the PowerPoint notes
- [Rendered slide previews](preview/index.html), 1920 × 1080

## Slide sequence and provenance

| Slide | Content | Original assets |
|---|---|---|
| 1 | Institutional cover, author and ELTE course | Official `rc-atlas-logo@2x.png`, unchanged from `promo/logo@2x.png` |
| 2 | Six capability areas, implementation limits and current Portfolio Overview | `01-portfolio-overview.png`, accepted UI-01 commit `bbeed8433905e044c7df8f9c7a8ed2364aa1d37f` |
| 3 | Programme Manager assignment and Field Coordinator execution | `02-task-creation-assignment.png`, `03-task-in-progress.png` |
| 4 | Evidence submission, MEAL validation and Programme Manager approval | `04-task-submission.png`, `05-task-validation.png`, `06-final-approval.png` |
| 5 | Completed Workplan, institutional benefits and promotional URL | `07-completed-workplan.png` |

All originals remain under [assets/](assets/INVENTORY.md). The six task images come from retained authentic HW10 evidence for **Review Buzi field report** in the **Coastal Resilience and Livelihoods Programme**. All seven screenshots and the official logo are embedded byte-for-byte in the PowerPoint. Cropping is reversible PowerPoint framing; no application content was changed. Crop coordinates and editable text are recorded in `build.mjs`.

The current Portfolio Overview uses a separate synthetic UI-01 fixture. The task sequence uses the historical HW10 scenario. The deck does not imply identical sessions or that the current overview contains the historical completed task. The source inventory records capture details and SHA-256 hashes.

The creation and submission images show filled forms before their actions. Validation shows Pending Validation before Validate; approval shows Completed and Approved after the final action. The workflow record confirms the intervening transitions. Evidence is a synthetic text note, not a real report attachment. Task completion does not establish programme outcomes. Report export/delivery limitations and the unresolved missing-versus-zero analytical presentation are explicitly qualified.

The promotional URL comes from the existing HW10 publication record: https://esst-prog2.github.io/RC_ATLAS_Project/. The deck follows the promotional navy/teal institutional identity, using the exact requested colours `#0C2038` and `#168B87` with Segoe UI, white and neutral grey.

## Quality control

All five slides were rendered through installed Microsoft PowerPoint and visually inspected individually. The final PDF was exported from the validated deck through PowerPoint, rendered with Poppler and inspected page by page. Text, crops, chronology, spacing and slide numbering are consistent between formats. The PPTX package, heading geometry, font policy and five-slide count checks passed. Both files are 16:9. Full-screen use at 1920 × 1080 or higher is recommended for application details.

The original screenshot hashes, application source hashes and all seven worktree paths/branches/HEADs were verified unchanged. No application regression tests, application edits, UI-01 continuation, commits, merges, pushes or deployments occurred.

`build.mjs` is presentation-only source. Ignored `.build/` contains intermediate exports and validation receipts; these are not delivery files. The PowerPoint is directly editable without running the builder.
