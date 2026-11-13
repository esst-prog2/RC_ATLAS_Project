# HW10 assignment review and technical feasibility

Date: 14 November 2026, Europe/Budapest. Status: planning only, pending owner approval.

## Exact assignment instructions

Source: the product owner pasted the professor's instructions in this conversation on 14 November 2026. No assignment file or connected document session was available before that reply. The supplied text is recorded verbatim below; it has not been independently checked against a course portal.

> About 30 seconds about your program, for someone who has never heard of it. It goes on your page, not in your presentation.
> Steps
> 1. Make it with HyperFrames. Open Claude Code and say:
> Install HyperFrames from github.com/heygen-com/hyperframes. Then make a 30-second promo video from my promo page.
> It needs Node 22+ and FFmpeg. If it won’t start: record your screen, and add captions.
> 2. Put it on your page.
> 3. Push, and add the step to your PROCESS.md.

The assignment requires a novice-facing video of about 30 seconds, a HyperFrames attempt first, website embedding (not presentation insertion), a push and process documentation. Screen recording plus captions is explicitly permitted if HyperFrames will not start. The supplied text does not specify a HW10 deadline, resolution, frame rate, soundtrack, narration, file-size limit, or separate submission portal; do not inherit HW9's deadline as HW10's.

The owner's current gate is stricter about timing: first present the storyboard, feasibility and implementation plan for approval; do not change or publish the website yet. No software was installed or video generated during this planning step.

## Existing website and source review

Opened the actual public site in gstack Chromium on 14 November and read its rendered text, then inspected a desktop screenshot. Compared its messaging with promo/index.html, promo/styles.css and docs/hw9/CONTENT_REVIEW.md. Public URL: https://esst-prog2.github.io/RC_ATLAS_Project/ . Current publication commit: 23de743; current planning checkout starts at eaa6ea4 on hw9-promo-page.

Retain the approved headline, Institutional Overview positioning, navy #123b5d, teal #11828a, light teal #9ddbd5 and white. Five capability names: project management, monitoring, indicators, analytics and reporting. Reporting covers records and previews, not completed governed exports. Indicator analysis depends on configured methods and suitable data. A task's approval confirms delivery, not measured outcomes or impact. The website requires local setup and offers no public application demo.

The video will use the approved source PNG at docs/hw9/branding/approved-source.png, SHA-256 479835cff8a75eabb4e8f62e1d51093a374e775344628a77db1b2d2c10459cc7. Preserve its 3:2 source ratio, alpha and artwork; never crop, trace, stretch or recreate it. It is a raster logo, not vector art. Use original resolution for the video, not the tiny favicon.

## Technical checks performed

| Item | Observed result | Consequence |
|---|---|---|
| Node.js | node --version: v24.19.0 | Meets upstream Node >=22 requirement. |
| npm | npm.cmd --version: 11.17.0 | Use the Windows .cmd entry point. Bare npm hits the existing PowerShell script policy; no policy changes needed. |
| HyperFrames | No command on PATH, no canonical root node_modules/.bin executable, no matching installed skill directories in the checked skill roots | Not verified locally installed or runnable. Upstream npm package metadata reports 0.9.42 with Node >=22; no CLI execution/install attempted. |
| FFmpeg / FFprobe | Neither command resolves on PATH; imageio_ffmpeg Python package absent | Need verified executable paths or a scoped installation before rendering. This is not proof that no copy exists anywhere on the machine. |
| Browser | Chrome and Edge executables exist; gstack Chromium rendered the public page | Browser rendering is available, but HyperFrames' own browser integration remains untested. |
| Claude Code | claude command not found on PATH | The assignment names Claude Code. Ask the owner to approve using HyperFrames from this Codex session, or provide a working Claude Code entry point. Do not claim Claude Code was used. |
| Git | Tracked tree clean at entry; seven worktrees; current branch hw9-promo-page | Planning commits can be made safely without switching. No original untracked file is included. |

Conclusion: HyperFrames is available upstream and appears feasible here after dependency setup. It is **not yet render-ready or smoke-tested**. Missing dependencies alone do not justify skipping the required HyperFrames attempt.

## Preferred setup after approval

Pin a reviewed HyperFrames release (0.9.42 was observed), read that version's bundled authoring/CLI instructions, and install only into a dedicated HW10 subfolder of the canonical project. Keep npm/browser caches, temporary files and any downloaded tools under that folder; do not install globally or change machine execution policies. Keep runtime dependencies and tool binaries ignored, with source/lockfile and provenance recorded.

The upstream doctor supports explicit HYPERFRAMES_FFMPEG_PATH and HYPERFRAMES_FFPROBE_PATH. Obtain a Windows build via the links on FFmpeg's official download page, verify its provenance/checksum, and point the process at those canonical-workspace executables. Validate doctor JSON (not exit code alone), then prove a short local render before building the full film. If downloads cannot stay within the permitted workspace, stop and report the exact issue.

Use local HTML/CSS and seekable animation, local approved assets, and the local rendering path. No HeyGen cloud account, paid provider, avatar, generated product imagery, live institutional runtime, or credential access is needed for the proposed film. FFmpeg/FFprobe will encode and inspect the MP4. Installed browsers still need explicit compatibility verification by HyperFrames.

## Permitted fallback assessment

If the installed HyperFrames route genuinely fails to start after a bounded diagnosis, record the failure and proposed remedy in PROCESS.md. The assignment permits recording the screen and adding captions in that situation. Record only the approved public promo page or a controlled local copy, then add the approved timed explanatory text/captions. Do not record a signed-in institution, desktop notifications, tabs, credentials or unverified application screens. A website recording must be labelled and presented as the promotional website, not as a working application demonstration.

Use the same 30-second narrative and output checks. Browser screen capture still needs a tested recording/encoding path; it is not a guarantee that the missing FFmpeg dependency can be ignored. No fallback recording or tool installation has been performed. Report any actual startup failure before switching routes rather than silently substituting another generator.

## Primary sources reviewed

- https://github.com/heygen-com/hyperframes — HTML-to-video model, local CLI, Node/FFmpeg prerequisites.
- https://raw.githubusercontent.com/heygen-com/hyperframes/main/packages/cli/package.json — observed package version and Node engine constraint.
- https://registry.npmjs.org/hyperframes/latest — read-only package metadata, version 0.9.42 at review time.
- https://hyperframes.heygen.com/quickstart — authoring and preview approaches.
- https://raw.githubusercontent.com/heygen-com/hyperframes/main/skills/hyperframes/SKILL.md — inspected as upstream documentation, not installed or invoked; seekable composition contract and review-before-render workflow.
- https://raw.githubusercontent.com/heygen-com/hyperframes/main/skills/hyperframes-cli/SKILL.md — CLI check/preview/render workflow.
- https://raw.githubusercontent.com/heygen-com/hyperframes/main/skills/hyperframes-cli/references/doctor-browser.md — FFmpeg/FFprobe configuration and diagnostic checks.
- https://ffmpeg.org/download.html — authoritative download entry point; Windows binaries are provided by linked build providers.

Mutable upstream sources must be pinned/rechecked during installation. Planning sources are not proof of a completed local render.
