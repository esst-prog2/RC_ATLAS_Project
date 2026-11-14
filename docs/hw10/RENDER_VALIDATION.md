# HW10 local render: ready for owner review

14 November 2026. Actual HyperFrames 0.9.42 through Codex, with the owner's explicit host-substitution approval. No fallback was needed.

## Review artifacts

- `output/rc-atlas-promo.mp4`: complete silent, text-led film.
- `output/review.html`: local review player with the complete on-screen transcript; it is separate from the promotional website.
- Review URL while the local server runs: http://127.0.0.1:8787/review.html. Restart from canonical workspace with `python docs/hw10/video/serve_review.py`.
- Editable HyperFrames preview: `python docs/hw10/video/hf.py preview --port 8785`, then http://localhost:8785/#project/video. HyperFrames also offers its desktop app for continued editing (`hyperframes open .` from the video project); no desktop app installation was performed.

## Encoded-file verification

FFprobe counted **900 frames**, exactly **30.000 seconds**, **1920x1080**, **30fps**, H.264/yuv420p. Exactly one video stream and no audio streams, matching the silent format. Full FFmpeg decode returned no errors. The MP4 streaming index precedes media data (faststart).

Size: **1,056,009 bytes**. SHA-256: `970f44467d8a7f58e483869c275b186aee5f0c92adcea4f0f4c4ad84ce963bd0`.

The official logo asset remains byte-identical to the approved source: `479835cff8a75eabb4e8f62e1d51093a374e775344628a77db1b2d2c10459cc7`. No generated product screenshots, institutional data, credentials or backend runtime were used. All five capability names, four example workflow stages, the owner's revised evidence message and local-setup/no-demo notice are visible in the decoded output. Text and logo stay within the approved canvas, without stretching or cropping the logo.

## Visual and playback verification

HyperFrames check passed with zero errors; runtime/layout checks and all 23 sampled contrast checks passed. Rendered scene, seam and 360px phone sheets were inspected. A real read-only HW10 sub-agent reviewed earlier sheets; its two small-type concerns were addressed. See video/REVIEW.md for the exact scope and retained warnings.

Viewed decoded frames at the opening, each scene and final frame. gstack Chromium loaded the actual encoded MP4 and played to currentTime=30, ended=true, error=null. Desktop (1440px) and phone (390px/360px) review layouts had no horizontal overflow. Browser console showed no errors. The constrained local machine recorded three cumulative dropped playback frames across review playback/replays; FFmpeg decoded all 900 frames, so this is a playback-performance observation, not missing encoded frames.

The initial standard-library preview server did not support reliable seeking. The review-only replacement binds to loopback and serves only output/ with MP4 byte ranges: HTTP 206 verified, and browser seeking to 15.5 seconds succeeded. This helper is not application code and is not intended for publication.

The workflow is the densest scene, and small portrait inline playback remains less readable than full-screen landscape. No claim of physical-device or user usability testing. Installed Segoe UI is needed to reproduce the source render on another machine; the MP4 itself needs no fonts. Silence and reading holds are intentional. No sound was heard or synthesized.

## Git and publication boundary

Current topic branch: hw10-promo-video, based on 07f80e3. Setup and implementation commits: 415abe1, d01fb3f, 2eea01a, 872fe83; this delivery is recorded in the following render commit. All seven registered worktrees remain; other worktree HEADs and existing untracked artifacts are preserved. No application source or promo/ change. gh-pages remains 23de743274a68e1a0863ca733e13c1a5ce94a348. No push, merge, website integration or deployment occurred.

Awaiting owner review of the MP4 before preparing website integration. HW10 is not yet complete because embedding and publication remain unapproved and undone. UI-01 consolidation and Mozambique mapping remain deferred.
