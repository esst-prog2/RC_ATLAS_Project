# HW10 completed: approved video published

Verified on 15 November 2026 (Europe/Budapest).

- Public website: https://esst-prog2.github.io/RC_ATLAS_Project/
- Direct video section: https://esst-prog2.github.io/RC_ATLAS_Project/#video
- Successful deployment: https://github.com/esst-prog2/RC_ATLAS_Project/actions/runs/43692941823
- Publication commit: `4be004c0adebb4fdb8de0b440d3e360a33cd9810`.
- Exact published tree: `b10c88e4b1ca927a5fc54361ddbdb4577a516d33`.
- Existing Pages strategy retained: `gh-pages`, `/(root)`. No hosting/settings strategy change.

## Approved integration

The owner officially approved the complete film and explicitly authorized integration, pushing HW10 and publication. The video is copied byte-for-byte, with SHA-256 `970f44467d8a7f58e483869c275b186aee5f0c92adcea4f0f4c4ad84ce963bd0`; it was not regenerated, re-encoded or edited. It remains 30 seconds, 1920x1080, 30fps, H.264, silent.

Native controls allow playback and seeking. The player uses playsinline, no autoplay/loop, preload none, an accessible name/description, proportional sizing and a poster decoded from the approved film at 2.5 seconds. A keyboard-operable inline transcript describes every scene, all text and the workflow sequence. A download link provides a fallback. The existing workflow/evidence sections and five capabilities remain intact; exact prior markup preservation was checked excluding the added video/link and stylesheet version query. All previous logo/favicon bytes are unchanged.

## Exact public file inventory

| File | Bytes |
|---|---:|
| .nojekyll | 0 |
| favicon.ico | 3,170 |
| favicon.png | 1,635 |
| index.html | 12,674 |
| logo.png | 11,925 |
| logo@2x.png | 37,965 |
| rc-atlas-promo.mp4 | 1,056,009 |
| styles.css | 11,294 |
| video-poster.jpg | 46,826 |
| Total | 1,181,498 |

Only these nine regular files are present in the published tree. No source dependencies, tools, technical reports, credentials, institutional data, application/backend code or preview server are in Pages. The transcript is part of index.html; no additional script or third-party player is required.

## Verification

GitHub connector confirmed the exact deployment completed successfully and its nine-file tree matched every manifest blob. The public root and all nine assets returned HTTP 200 with their exact approved SHA-256 hashes. MP4 byte-range requests returned HTTP 206 with matching bytes. Five excluded report/application/local-data paths returned 404. Public GitHub repository and setup-document links returned 200 and were followed successfully in the browser.

Fresh gstack Chromium verification played the public MP4 to currentTime=30, ended=true, error=null and zero dropped frames in the full playback pass. Seeking to 15.5 seconds succeeded; Space on the focused native player started and paused playback. An initial harness expectation that ArrowRight on the video element itself would seek was unsupported by the browser; it was corrected rather than claimed as a pass. Actual media seeking and server range support were separately verified. A browser session restart and Windows console encoding issue were recovered before the successful acceptance pass.

Desktop 1440px and mobile 390px/320px layouts showed no horizontal overflow, missing anchor target or limited computed-color contrast failure. Poster and logo decoded; transcript summary exceeded 44px height and opened using Enter; Tab/Enter activated Skip to content and focused main. Actual header/hero navigation and both external destinations worked. No public-site console errors. Screenshots and structured observations accompany this report. These are Chromium viewport checks, not physical-device or cross-browser certification. The silent landscape film is clearest full-screen on small phones; its complete transcript remains readable inline.

## Commits and preservation

- 0a4a194: owner approval and pre-publication baseline.
- 6bdfa38: accessible integration, poster and transcript.
- 7051245: exact committed publication boundary and assets-only commit preparation.
- 4be004c (gh-pages): publish approved film with the static site.
- 65da67b: record successful deployment.
- This report's commit: final public verification and completion record, pushed to hw10-promo-video.

The canonical checkout remains D:/MASTER SURVEY STATISTICS & DATA ANALYSIS/ADVANCED PROGRAMING/RC_Atlas_Project on hw10-promo-video. Main remains 5d487f8ff2fff3a864bc5405a90d2555ee3b5218. All seven registered worktrees and the other branch/worktree HEADs match the saved baseline. Existing untracked .impeccable, Site.txt and root logo remain untouched and unstaged. No worktree creation, force, stash, reset, main merge, backend deployment or application-code change occurred.

The completed HW10 work and process record are pushed on the HW10 branch. HW10 now includes the actual HyperFrames video, website embedding, successful deployment and public verification. No additional product development or consolidation/mapping work was started.
