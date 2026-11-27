# HW11 final acceptance and publication

Product Owner accepted the Reveal.js deck and authorized publication on 27 November 2026.

- Public presentation: https://esst-prog2.github.io/RC_ATLAS_Project/slides/
- Publication branch: `gh-pages`, root `/`.
- Publication commit: `e87f654a2e3fc290e0d7c81d2accb7eda39e038c`.
- Deployment: **success**, [Pages run 46075858152](https://github.com/esst-prog2/RC_ATLAS_Project/actions/runs/46075858152).
- Published scope: **only `slides/index.html`**. Images, notes and Reveal.js dependencies are embedded.
- Existing promotional site: all **9 existing files** retain their original Git blob IDs and modes, including the video and logo.
- Public HTML SHA-256: `93032a0c4f4ef856a9d25fbe41b669571dee85b333d2038e4bb02761f00878eb`, identical to the Product Owner-approved local HTML.

## Public validation

HTTP 200. Chrome checks passed at 1920?1080: six slides, six progressive workflow stages confined to slide 2, six readable public note panels, decoded images, ArrowRight/ArrowLeft/Space navigation and N notes control. Escape closing was checked separately. No JavaScript errors, failed requests or external asset requests. Notes can also be opened and closed with their visible buttons. The test restores document focus between note panels for presentation shortcuts.

See [browser record](evidence/public-browser-validation.json), [deployment record](evidence/deployment.json) and [published screenshots](evidence/published-preview/). No application regression suite was run for publication.

## Source preservation

The approved HTML, original assets, editable presentation, source builders, speaker scripts, compliance record and bounded validation evidence are preserved on the existing `hw10-promo-video` academic branch. No application development branches were merged. The former pending-publication statements in the preparation records describe their earlier checkpoint; this acceptance record supersedes that delivery status.

All seven worktrees and unrelated untracked material remain in place. Only the canonical academic branch advances for the authorized source checkpoint. UI-01 remains paused. Local raw-reference downloads, server logs, intermediate builds and workspace-preservation snapshots are excluded from the source commit and remain on disk.
