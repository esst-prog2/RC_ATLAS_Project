# Approved authentic HW10 demonstration — published

Verified on 22 November 2026 (Europe/Budapest).

- Live page: https://esst-prog2.github.io/RC_ATLAS_Project/#video
- Successful GitHub Pages deployment: https://github.com/esst-prog2/RC_ATLAS_Project/actions/runs/45037722255
- Publication commit: `cb18155c7e4239ff636f711ff9da42376f02c990`.
- Publication tree: `0399f0733cef90174de01a614192b08a279c8ba1`.
- Existing configuration retained: **gh-pages, /(root)**.

## Approved replacement

The Product Owner visually reviewed and approved the authentic 29.8-second application demonstration, then authorized its publication. The exact approved MP4 was copied without editing or re-encoding. Its SHA-256 is:

`cc8dbe3276a7c4ca8dc580e683b0a85852a99342f95327cb4b85a67452efc574`

Only three website files changed: `index.html`, `rc-atlas-promo.mp4` and `video-poster.jpg`. The video-related heading, description, transcript, download size and hero-link wording now describe the actual recorded workflow. The poster is the already reviewed frame decoded from this MP4. Video and poster references use `?v=authentic-cc8dbe3276a7` to avoid stale cached assets. Native controls, inline playback, keyboard access and responsive styling remain intact.

The other six assets are byte-identical to the previous deployment. Markup outside the video block and its hero-link wording was compared and is unchanged. Institutional Overview, the five capabilities, branding, navigation, repository/setup links and all existing application limitations remain preserved.

## Published inventory

The remote Git tree contains exactly these nine regular files and no folders, application source, data, tools or technical reports:

| File | Bytes |
| --- | ---: |
| .nojekyll | 0 |
| favicon.ico | 3,170 |
| favicon.png | 1,635 |
| index.html | 13,675 |
| logo.png | 11,925 |
| logo@2x.png | 37,965 |
| rc-atlas-promo.mp4 | 3,594,834 |
| styles.css | 11,294 |
| video-poster.jpg | 261,479 |

Full hashes are in `manifest.json`; GitHub connector deployment/tree evidence is in `github-deployment.json`.

## Public verification

- GitHub Pages run **45037722255** completed successfully for the exact publication commit above.
- The public root and all nine files returned HTTP 200 with bytes matching the local committed publication assets.
- Both the versioned player URL and the unversioned `rc-atlas-promo.mp4` URL returned the approved new hash. The previous text-led MP4 hash (`970f4446…`) is not served at the current video path. The previous file remains in Git history, which was preserved.
- A fresh Chromium session loaded the public page and confirmed its `currentSrc` uses the new versioned MP4. It played to **29.8 seconds**, `ended=true`, `error=null`, at **1920×1080**. The approved file's 30fps encoding was unchanged.
- Seeking to 17.5 seconds, HTTP 206 byte ranges, keyboard Space play/pause, Enter on the transcript and the skip link all passed.
- Actual header navigation to Capabilities, Workflow and Explore, plus the hero video link, worked. Public GitHub repository and setup-guide URLs returned HTTP 200.
- CSS and logo loaded. Desktop 1440px and mobile 390px/320px viewports had no horizontal overflow; public desktop/mobile captures were inspected. No page JavaScript errors were observed.
- These are Chromium viewport checks, not physical-device or cross-browser certification. Fine application text is clearest full-screen/landscape on small phones; the full descriptive transcript is available inline.

Evidence: `public-http.json`, `public-browser.json`, `public-1440.png`, `public-390.png`, `github-deployment.json`, `preservation.json`.

## Git history and preservation

- `bd4c6d8`: preserve the approved authentic video, provenance and owner approval.
- `1857643`: integrate the exact MP4, decoded poster and accurate transcript; record local validation.
- `ed8bb39`: record the verified static publication commit.
- `cb18155`: publish the three-file replacement on gh-pages.
- This report's documentation commit records the completed deployment and public checks on hw10-promo-video.

An atomic push advanced only hw10-promo-video and gh-pages. The canonical checkout remains on hw10-promo-video. All seven worktree registrations are preserved; other worktree HEADs and all unrelated local branches, including main, match the publication baseline. Main's local baseline is `9093a3cb01b92a83d690e596ff95f0d4a5988053`; it was not modified or merged.

The application-source diff is empty. All 205 disposable source-copy hashes still match their original manifest. Existing untracked artifacts and local recording evidence remain in place and were not swept into the publication tree. No application/backend deployment, paused UI-01 edit, branch merge, new worktree or additional product development occurred.
