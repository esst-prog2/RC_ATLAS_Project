# HW10 composition review

14 November 2026. This is the owner-approved silent first cut, rendered locally with HyperFrames through Codex. The institutional overview storyboard was implemented; no alternative storyline, invented application screen, statistic, soundtrack or external media was added.

## Findings and refinements

- Initial check found two root compositions. Preserved the smoke source under tests/; the final root is index.html.
- Opening copy now appears fully at frame zero.
- Rendered seam sheets revealed doubled text during full-scene dissolves. Outgoing text now fades before each boundary; incoming text appears after the background transition has begun. Brief background-only intervals are deliberate, not dropped frames.
- A real Codex sub-agent, hw10_visual_review, independently viewed the storyboard and rendered beat/phone/two seam sheets. It reported no P0 and two P1 concerns: small workflow labels and closing instructions at phone width. Its review was of still samples, not complete playback. The prior HW9 failed critiques were not retried.
- Enlarged workflow labels from 62 to 74px and URL/setup text from 60/56 to 72px. Retained the four-stage horizontal sequence after the layout check found no overflow. The repository address remains two lines; the setup disclosure fits on one line.
- Final runtime, layout and contrast passes have zero errors/warnings; 23 sampled contrast checks pass. Static lint has only five local-font warnings. Craft retains silence plus two deliberate reading holds. Detailed evidence: ../evidence/final-check.json.

## Visual assessment

Beat frames identify the brand, audience and five capabilities, the example task-review sequence, the evidence/method requirement, then the GitHub next step. All objects are either approved branding, typography or explanatory lines/nodes. There is no fabricated UI or claim that approval establishes indicator outcomes. The evidence message is a separate scene without an arrow or counter connecting it to task approval.

Reviewed rendered beats, transitions and phone-width sheets. The workflow is the densest shot; the larger labels improve scanning, but full-screen landscape playback remains preferable to a tiny portrait inline player. The closing URL is relatively long, so a real clickable link outside the video will remain useful at the later integration stage. No website was edited.

Segoe UI is read from the installed Windows fonts; those font files are not redistributed. Re-rendering on a different machine requires the same fonts or a separately approved replacement. The output MP4 will contain pixels, so viewer font installation is irrelevant. Silence is intentional; there is no audio to assess by listening. The review is visual/sample-based and does not claim user usability testing.

Owner review of the final MP4 is required before preparing website integration. Render-file verification will be recorded separately in ../RENDER_VALIDATION.md.
