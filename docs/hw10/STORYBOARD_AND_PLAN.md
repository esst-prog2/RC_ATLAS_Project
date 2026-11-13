# RC Atlas HW10: proposed 30-second film

14 November 2026, Europe/Budapest. **Proposal for owner approval; no video implementation or website changes yet.**

## Creative direction

Institutional Overview in motion: a clear, text-led introduction for someone unfamiliar with RC Atlas. Use the actual approved logo, navy/teal surfaces, white typography and simple explanatory workflow graphics. These graphics are editorial explanations, never imitation application screens. No institution/customer claims, numerical performance claims, invented data charts or promised functionality outside the reviewed website.

Recommend a 30.0-second, 1920x1080, 16:9 video at 30fps (900 frames), delivered as browser-compatible H.264 MP4 with yuv420p and fast-start metadata. These are agent proposals, not assignment-mandated specifications. File-size goal: at most 12 MB, subject to readable text and logo quality. No alternate aspect ratio is needed for this website assignment.

## Storyboard

Transition time is included within each row; rows total exactly 30 seconds. Key words remain visible while a brief transition settles. Final card holds through the last frame.

| Time | Visual and transition | Exact proposed on-screen text |
|---|---|---|
| 00:00-00:05 | Official logo and name on navy. Gentle 0.4s opacity reveal; no logo morph, crop or rotation. The headline is arranged in two or three readable lines. | **RC Atlas** / **From institutional data to coordinated action.** |
| 00:05-00:12 | 0.3s dissolve to the five capability names in a spacious two-row arrangement, matching the website hierarchy. All names appear within the first 0.8s and remain visible together; restrained teal emphasis moves once across them. | **For institutional project teams** / **Project management** / **Monitoring** / **Indicators** / **Analytics** / **Reporting** |
| 00:12-00:19 | 0.3s dissolve to a four-stage editorial flow. Highlight each handoff in sequence while keeping all labels visible. No fake app controls or implied live task updates. | **One example workflow** / **Assignment → Submission → Validation → Approval** / **Clear responsibility at each handoff.** |
| 00:19-00:25 | Clean dissolve to two contrasting lines on a light surface with navy text. Keep the operational fact and measurement caveat equally readable; no celebratory result chart. | **Completion is not proof of impact.** / **Indicator results need suitable data and configured methods.** |
| 00:25-00:30 | Return to navy and the official logo. 0.3s entrance, then a stable closing card with repository address. | **Explore RC Atlas on GitHub** / **github.com/esst-prog2/RC_ATLAS_Project** / **Local setup required · No public live demo** |

The workflow compresses the website's intermediate Work step into the period between assignment and submission; it does not remove execution or claim automatic submission. It describes the reviewed two-stage example, not a universal mandatory workflow. Approval concerns completion; the next scene explicitly distinguishes indicator evidence.

## Readability and motion specification

- Preserve navy #123b5d, teal #11828a, light teal #9ddbd5, white and existing restrained typography. Reuse Segoe UI/Aptos where renderable; verify actual font resolution. Do not distribute proprietary font binaries. Any necessary redistributable replacement is subject to visual review rather than silently changing the identity.
- Headlines about 80-100px, primary text at least 64px, supporting text about 54-60px at 1080p; use line breaks, never shrink critical copy to fit. Verify at a 390px-wide embedded preview; the long URL may use two lines and has a clickable adjacent website link after embedding.
- Keep text within the central 80% title-safe area. Use high-contrast text and adequate spacing; the five capability labels are a 3+2 grouping, never five tiny columns. At most three short lines on explanatory scenes.
- Dissolves 0.3-0.4s; any text translation limited to about 12px with smooth easing. No fast zoom, spin, flash, bouncing, parallax or decorative animation over the logo. No numerical counters that could imply real institutional results.
- Recommend an initially **silent, text-led version**: all meaning is readable without audio, with no unapproved voice or music provider. A soundtrack is optional, not required by the supplied brief; only add licensed music or narration if the owner requests/approves it. Provide an adjacent text transcript for the embedded video. If a narrated or screen-recorded fallback version is used, include timed captions as well.

## Implementation sequence after approval

1. **Confirm tool host and isolate source.** The assignment names Claude Code, but no claude executable is currently on PATH. Ask permission to run the same HyperFrames workflow from this Codex session, or use the owner's working Claude Code entry point. After the owner approves, recheck Git status and create a dedicated `hw10-promo-video` topic branch from the reviewed HW9 plus these planning commits in the same canonical checkout. No worktree or application folder replacement. Stop if branch creation encounters a conflict.
2. **Establish the local renderer.** Put the HyperFrames project under `docs/hw10/video/`, with dependencies/tooling/cache/output paths kept within the canonical project and ignored where appropriate. Pin the reviewed package version and lockfile, obtain verified FFmpeg/FFprobe binaries through the official download path, configure process-local paths, and run doctor plus a short render check. Record exact versions and results. No installation occurs during this planning turn.
3. **Build and preview.** Use the approved five-scene storyboard, seekable timelines and local source assets. No application runtime, screenshots or live providers are needed. Validate HyperFrames composition checks, inspect every scene midpoint and transition boundary, and show a local timed preview to the owner. Commit source and a truthful process entry.
4. **Render and verify after preview approval.** Render the MP4 locally; use FFprobe to verify about 30 seconds, dimensions, frame rate and codecs. Decode sample frames, watch the complete result, check final-card hold, text readability, correct logo ratio and lack of clipping/blank frames. Confirm sound/captions if any. Save a poster frame and transcript; keep source/tool files outside the publication tree. Show the MP4 for review.
5. **Prepare the website integration only when authorized.** Add a responsive native video element after the existing workflow, at the reserved HW10 location: controls, playsinline, preload=metadata, poster, no autoplay/loop, plus a transcript and adjacent GitHub link. Preserve every existing capability section, copy and page navigation. Proposed new public files are one MP4 and one poster, plus a VTT only if timed captions are needed; the exact inventory depends on the approved final cut. Review the complete inventory before any deployment.
6. **Publish and close the assignment after approval.** Reuse the existing gh-pages root strategy with an exact approved static tree. Push only the topic and publication branches, await successful Pages deployment and test public video loading/playback/seeking, poster, links and mobile layout. Record the actual output URL, duration, commit IDs, verification and any limitations in PROCESS.md. Never claim publication from a successful push alone.

Each meaningful completed step includes its own process entry and commit. No new authorization is inferred for application UI integration, backend/frontend consolidation, Mozambique mapping, paid/cloud rendering or machine-wide installation.

## Fallback decision

If HyperFrames cannot start after dependencies and a bounded diagnostic attempt, the professor permits a screen recording with captions. Record the approved promotional page (or its verified local copy) with controlled scrolling to the headline, five capabilities, workflow, evidence distinction and final CTA. Add timed explanatory captions, trim to approximately 30 seconds, and apply the same export and public verification gates. Do not fabricate app footage. Document the actual HyperFrames failure before proposing the switch; a fallback is not being selected now.

## Decisions awaiting the owner

1. Approve this five-scene storyboard, proposed 1080p/30fps format and initially silent text-led treatment, or specify changes.
2. Approve the canonical-workspace-only dependency setup and using HyperFrames from Codex despite the assignment's Claude Code example, or provide a working Claude Code entry point.

Website editing and publication remain separate later gates. This document records recommendations, not owner decisions already made.
