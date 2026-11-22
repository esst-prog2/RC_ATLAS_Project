# HW10 — authentic RC Atlas application recording

Completed locally on 22 November 2026. **Approved by the Product Owner and published on 22 November 2026.** UI-01 remains paused.

## Deliverable

- MP4: [output/rc-atlas-authentic-demo.mp4](output/rc-atlas-authentic-demo.mp4)
- Review player and descriptive transcript: [output/review.html](output/review.html)
- Optional local review: run `python docs/hw10/authentic-demo/serve_review.py` from the canonical checkout, then open `http://127.0.0.1:8788/review.html`. The helper serves only the review HTML, poster and MP4 over loopback.
- Duration **29.800 seconds**, **1920×1080**, **30 fps**, H.264/yuv420p, **894 frames**, **3,594,834 bytes**. Silent, with burned-in explanatory captions.
- SHA-256: `cc8dbe3276a7c4ca8dc580e683b0a85852a99342f95327cb4b85a67452efc574`.

## What actually ran

The real RC Atlas application ran through its documented Uvicorn entrypoint, `logitrack_rc_v4_4_api:app`, with JSON storage. The procedure was recovered from `docs/DEVELOPMENT.md`; startup/environment settings are explicit in `runtime.py`.

The source was a 205-file committed-source copy inside this canonical workspace's ignored `.runtime/app` directory, sourced from canonical commit `640bcb2827c0d328069a0bb52defa9e7fec9f92e` on `hw10-promo-video`. File selection used the established application baseline `5d487f8ff2fff3a864bc5405a90d2555ee3b5218`; the recorded file bytes came from the canonical committed tree. No application source was edited. The paused UI-01 worktree and its uncommitted visual revisions were not incorporated or changed.

The repository's demo seed builder created fictional projects and users. New `example.test` demo accounts operated the workflow. Application JSON writes were confined to `.runtime/synthetic.json`; no canonical data, backups, credentials, `Site.txt`, or live providers were read or used. The runtime used a scrubbed environment, disabled scheduler/providers, loopback binding, and independently exercised Python audit guards that reject writes outside the disposable runtime, protected data paths and external connections. This is a bounded application-level isolation measure, **not an OS sandbox**. See `.runtime/isolation.json` locally and `runtime_guard.py` for the exact checks.

## Actual workflow

The workflow was exercised end to end before recording, including approval and a fresh login, using a separate rehearsal task. `evidence/preflight-verification.json` records that successful sequence. The disposable fixture was then reseeded for the recorded task; the rehearsal state was retained separately.

Recorded task: **Review Buzi field report**, ID `task_proj_resilience_review_buzi_field_report`. Assigned to **Aline Duarte (Demo)**, validated by **Raimundo Cumba (Demo)** and approved by **Teresa Mbanze (Demo)**. Due 1 December 2026; validation-plus-approval route; evidence required; no linked KPI.

| Real user action | Verified application result |
| --- | --- |
| Programme Manager navigates from Portfolio to Workplan and creates the task with its assignee/reviewers | Task exists in the operational workplan, `not_started`, stage `execution`, progress 0% |
| Field Coordinator uses **Start Work** | `in_progress`, stage `execution`, progress 25% |
| Field Coordinator enters 100%, an evidence note and a comment, then uses **Submit for Validation** | `pending_validation`, stage `validation`, progress 100%, one evidence item |
| MEAL Officer uses **Validate** | `pending_validation`, stage `approval`; displayed as **Pending Approval** |
| Programme Manager uses **Approve** | `completed`, stage `complete`, progress 100%, evidence retained |
| Programme Manager filters the workplan to Completed | The same task appears in the actual results table |
| Separate fresh Programme Manager login, checked after recording the approval | Completed status and evidence persist |

The evidence item is the actual application **text note** “Synthetic Buzi field report reviewed”; it is not an uploaded report or a claim that real field evidence was assessed. The comment is “Ready for independent validation.” Completion of this operational task does not establish indicator measurements or outcomes. The closing caption states that distinction explicitly.

## Footage provenance and editing

Chromium rendered the real running application at 1920×1080. Playwright performed genuine browser navigation, input and clicks using the application controls; `recordVideo` captured actual browser screencasts. Mutation requests were emitted by the application, not fabricated by an editing tool. Read-only checks of actual persisted state independently confirmed the results.

The final film uses these real WebM sources, retained under ignored `raw/`:

| Source | Content |
| --- | --- |
| `page@48aa891aa09d34c1fb8ea0b6ecfbe476.webm` | Programme Manager navigation, filled creation form, creation and resulting workplan |
| `page@1e3daa7cdf08848ed3b59d7a666a92c5.webm` | Field Coordinator start and submission |
| `page@fd06d8d6809abc0bb34a268096d86e36.webm` | MEAL Officer validation |
| `page@abaf245d339b558aeab4599e58be2a52.webm` | Programme Manager approval and completed workplan |

Creation and later actions were captured across sessions, including a resumed session on 22 November. They concern the same persisted task. This is an edited demonstration, not a claim of uninterrupted 30-second execution. Logins, role changes and waiting time are cut. Source intervals run at their original speed; static crops/zooms improve readability. No app screen was generated, redrawn, reconstructed, composited from separate UI elements, or simulated. No artificial cursor or fabricated action was added. The authentic UI's differences between roles remain visible.

Portable FFmpeg 9.0.2 made the cuts, proportional crops/scaling and navy/teal caption footer, then encoded H.264 with fast-start metadata. The official `promo/logo.png` was proportionally scaled without redesign; its source hash remains `5f01ae7a53df9d72f18b9d096babf473be39c240f625105cb5ab6d33c19644ee`. The poster is decoded from this final MP4. HyperFrames and image generation were not used for this authentic revision.

`edit_video.py` is reproducible against the retained raw clips. `evidence/edit-decision-list.json` records every source hash, source interval, output interval, crop, caption and final hash. `evidence/record4/workflow.json` records the successful real actions, HTTP 200 responses, persisted state readbacks and zero page errors.

Earlier harness attempts are retained accurately: the preflight used an incorrect Portfolio selector for a Workplan button, then a selector that matched both row and button; both were corrected in recording automation only. During recording, a delayed real application refresh closed expanded task controls while the harness held for a shot. The harness now reopens the actual summary control and refills real inputs before clicking. No application code was changed to resolve this. Failed attempts were not represented as successful footage.

## Validation and preservation

- FFprobe verified duration, resolution, frame rate, H.264 format and all 894 frames. FFmpeg decoded the complete output without error.
- Decoded source frames were inspected to select real action/result intervals; the wall-clock capture markers were not assumed to be exact video timestamps. All ten final shots were reviewed through decoded frames/contact sheet, with detailed inspection of submission and completion views.
- Chromium played the review MP4 through **29.8 seconds**, with no media error. Seeking to 17.5 seconds, keyboard Space play/pause and HTTP 206 byte ranges passed.
- Review layouts at 1440, 390 and 320 pixels had no horizontal overflow; the mobile screenshot was inspected. Small application text is best reviewed in desktop/full-screen or mobile landscape. The separate descriptive transcript remains readable in portrait. This is not a claim that every original application label is readable at phone thumbnail size.
- `evidence/final-preservation.json` verifies all 205 copied source hashes, all nine published website asset hashes, unchanged canonical HEAD, unchanged seven worktree registrations/HEADs, empty Git index and continued existence of the three original untracked paths. The contents of forbidden untracked files were not read for hashing. No other worktree was edited.
- The temporary application's verified PID 23444 was stopped after recording. Synthetic fixture and raw evidence are retained locally; no destructive cleanup was performed.
- Changes are local in `docs/hw10/authentic-demo/`, plus appended `PROCESS.md` and `PLANNING_LOG.md` entries. No commit, push, merge, branch change, application edit or website publication was performed for this revision. The current public HW10 video remains unchanged.

Evidence: `evidence/final-media.json`, `evidence/review-browser-validation.json`, `evidence/final-contact.jpg`, `evidence/final-preservation.json`, `evidence/preflight-verification.json`, `evidence/record4/workflow.json`.

**Owner decision pending:** review this revised MP4 before any replacement of the published HW10 video. UI-01 remains paused; no consolidation or mapping work was resumed.

## Publication approval ? 22 November 2026

The owner visually reviewed and approved this exact 29.8-second film and authorized replacing the existing public promotional video. Publication and verification are recorded separately under `publication/`; the local-delivery history above is retained. UI-01 remains paused.

## Publication completed ? 22 November 2026

The approved exact MP4 is now live at https://esst-prog2.github.io/RC_ATLAS_Project/#video. GitHub Pages run 45037722255 succeeded for cb18155c7e4239ff636f711ff9da42376f02c990. Public byte hashes, complete playback, seeking, keyboard controls and desktop/mobile checks passed. See [publication/PUBLICATION_REPORT.md](publication/PUBLICATION_REPORT.md). Earlier local-only statements above describe the pre-approval delivery checkpoint. UI-01 remains paused.
