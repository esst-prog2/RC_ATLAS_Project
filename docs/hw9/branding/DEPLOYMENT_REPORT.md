# Approved RC Atlas branding update: published

Published and publicly verified on 13 November 2026.

- Website: https://esst-prog2.github.io/RC_ATLAS_Project/
- Successful deployment: https://github.com/esst-prog2/RC_ATLAS_Project/actions/runs/43476713822
- Published commit: `23de743274a68e1a0863ca733e13c1a5ce94a348`.
- Published tree: `3a6e92000e6437f754a1b70f2f7174a39bd02e33`.
- Existing Pages source retained: `gh-pages`, `/(root)`.

The owner explicitly approved the previously reviewed seven-file version and directed that the small 16px favicon should not delay publication. No logo, copy or layout changes were made during publication. This report supersedes the earlier candidate-only status in VALIDATION_REPORT.md and its historical review manifest.

## Exact published root inventory

| File | Bytes |
|---|---:|
| .nojekyll | 0 |
| favicon.ico | 3,170 |
| favicon.png | 1,635 |
| index.html | 10,526 |
| logo.png | 11,925 |
| logo@2x.png | 37,965 |
| styles.css | 10,240 |
| Total | 75,461 |

GitHub's remote tree contains exactly these seven regular files, with no directories or additional files. All seven served files and the site root returned HTTP 200 and matched approved SHA-256 hashes. The removed favicon.svg and tested report/application paths returned 404. Original source artwork, reuse assets, process records, application files and verification artifacts are not part of Pages.

## Public verification

GitHub Actions build, report-build-status and deploy jobs succeeded for the exact published commit. `verify_live.py` checked that run, the remote branch/commit/tree, blob identities, public response hashes, and excluded URLs. Results and content types are recorded in public-evidence/deployment.json.

The actual public site was opened in gstack Chromium and visually inspected at 1440x1000 and 390x844. Automated DOM checks also covered 320px width and 2x density. The logo decoded, retained its 3:2 ratio, and selected logo@2x.png at 2x density. No horizontal overflow or missing internal anchors occurred. Header navigation hit areas remained at least 44px tall; the accessible brand name remained RC Atlas. Network records showed successful CSS and logo loads; no page console errors were observed.

Actual clicks reached #capabilities, #workflow, #explore and #main. Keyboard Tab focused Skip to content and Enter moved focus to main. The approved page bytes preserve Institutional Overview, its content and all five capability areas. Favicon files were verified over HTTP; native browser tab chrome was not visually captured. These are Chromium responsive checks, not a real-device or cross-browser certification.

## History and preservation

- `3c279b4`: preserve exact approved logo and application reuse plan.
- `28a6706`: integrate the logo and raster favicon assets.
- `fb846c0`: validate preview and proposed inventory.
- `90c348a`: record explicit publication approval and preparation of publication commit `23de743`.
- Atomic push advanced only HW9 and gh-pages; `1e03d8d` records the successful push and deployment start.
- This report's commit records final successful deployment and browser checks, then is pushed to HW9.

Canonical checkout remains on hw9-promo-page. Main remains `5d487f8ff2fff3a864bc5405a90d2555ee3b5218`. All seven registered worktrees and other worktree HEADs remain intact. Existing untracked .impeccable, Site.txt and the supplied root logo remain unstaged. Application source and backend are unchanged and were not deployed. No worktree, reset, stash, force-push or main merge was used.

## Remaining limitation and next-work boundary

The complete approved image retains generous transparent margins, so the 16px favicon remains small and loses fine detail. This is accepted for this publication and documented for a later, separately approved refinement; no crop, redraw or substitute was introduced.

HW10 has not started. Application UI integration remains planned only. Consolidation and Mozambique mapping remain deferred until after HW9/HW10 as directed.
