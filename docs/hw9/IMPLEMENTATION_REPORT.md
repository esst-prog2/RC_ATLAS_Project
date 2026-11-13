# HW9 approved refinement

Date: 2026-11-13 (Europe/Budapest). Canonical checkout: `hw9-promo-page`, based on `origin/main` commit `5d487f8ff2fff3a864bc5405a90d2555ee3b5218`.

## Owner decisions applied

The owner accepted the disclosed sequential critique fallback, prohibited sub-agent retries, and approved all four P2 improvements and P3 typography refinement. Independent reviews could not complete because both delegated agents hit the account usage limit; this disclosure remains in CRITIQUE_REPORT.md and PROCESS.md.

Institutional Overview remains selected. `promo/` contains the refined public candidate; the three original previews and their source generator remain unchanged as design history.

## Implementation

- Retained the approved headline, navy-and-teal colors, system font identity, and prominent five-capability directory and explanations.
- Added the local-setup/no-public-live-demo notice immediately beside the opening GitHub action.
- Increased navigation, brand, secondary action, setup, and footer links to at least 44px high; primary buttons remain 50px high.
- Replaced the lower explanatory section with “Work you can trace. Evidence you can explain.” immediately after the workflow.
- Used semantic explanatory text for review checkpoints and an explicitly illustrative indicator calculation. Kept task delivery, indicator achievement, and reporting distinct.
- Simplified the governed-export caveat without claiming finalized exports are ready. Used balanced headings and pretty paragraph wrapping instead of adding manual line breaks to ordinary prose.
- Removed preview-comparison controls from the final candidate. Kept a logical workflow location for a future captioned video/transcript, with no empty player or HW10 media work.
- Improved landmark structure: header and footer outside main, a focusable main target for the skip link, labelled navigation, and ordered headings. No JavaScript, analytics, external fonts, tracking, API calls, or third-party embeds.

## Screenshot decision and provenance

The owner approved two genuine screenshots only from a verified isolated synthetic runtime, and explicitly approved honest text alternatives if safe verification was unavailable. Source inspection found the supported PostgreSQL fixture/capture route, but its prerequisites were unavailable in the checked environment: no configured `RCATLAS_PG_TEST_BIN`, no `initdb` or `pg_ctl` on PATH, no standard `C:\Program Files\PostgreSQL` installation, and no `psycopg` in active Python. This is a bounded environment check, not a claim that PostgreSQL cannot exist elsewhere on the computer.

No runtime was started, database installed, institutional data/backup/credential opened, or live provider contacted. No product screenshot is included. The visible examples are deliberately text explanations, not interface facsimiles or purported live results. The only graphic is the same RC Atlas mark used in the selected preview.

The example baseline 20, reported value 60, target 100 and `(60-20)/(100-20)*100 = 50%` are supported by `methodology_fixtures.py` and the expected explanation in `methodology_browser_acceptance.js`. The two-stage review boundary is supported by `assignment_aware_task_workflow_tests.py`. These sources were inspected, not executed in this step. No fresh application acceptance-pass claim is made.

## Preliminary validation

Actual Chromium renders inspected at desktop and mobile sizes. Initial checks passed for headline, anchor destinations, overflow, and computed text contrast. Keyboard skip navigation moved focus into main, and subsequent Tab presses reached the primary and secondary hero actions. External repository and setup-guide pages loaded in the browser; the guide returned HTTP 200. The final validation report and publication manifest record the completed checks and precise public file boundary.

## Publication boundary

Only the four files under `promo/` are candidates for the website: `index.html`, `styles.css`, `favicon.svg`, `.nojekyll`. Reports, manifests, browser captures, source, previews, runtime evidence, and PROCESS.md are outside that boundary. A later push of the HW9 topic branch will make its tracked homework records accessible through the existing public GitHub repository; that is separate from serving them as website files.

No push, Pages configuration change, publication, new worktree, or application/backend/security modification occurred. Final owner approval is required before pushing or publishing.
