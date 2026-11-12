⚠️ DEGRADED: single-context (both sub-agent runs failed with an account usage-limit error).

# Institutional Overview — HW9 critique

2026-11-13, Europe/Budapest. Target: `docs/hw9/previews/overview.html`, locally rendered at `http://127.0.0.1:8769/overview.html`. Assessed source commit: `8983498c4ae9ec60e2fb11b2b2e3532c814bd987`. Mode: Persuade. This is a design critique, not a system-wide application audit or a publication approval.

The owner selected Institutional Overview and authorized two independent rendered-page reviewers. The actual delegated agents, `/root/critique_design` and `/root/critique_evidence`, both failed before delivering assessments: “You've hit your usage limit.” The independent-review requirement remains unmet. Under Impeccable's failed-spawn fallback, the parent completed and recorded visual Assessment A before running detector/browser Assessment B. These are sequential assessments in one context, not independent reviewers or simulated sub-agents.

## Design specificity and overall impression

The institutional framing, five capability areas, and assignment-to-approval demonstration fit RC Atlas. The navy-and-teal identity and confident typography work together. However, the page still feels like a polished explanatory brochure: visitors cannot yet see the actual application. The strongest improvement is concrete, honest product proof within the selected structure.

Keep the approved headline, broader institutional positioning, palette, and all five capability areas: project management, monitoring, indicators, analytics, and reporting. The practical workflow should demonstrate their contribution to accountability and decision-making, without becoming the whole product story.

## Design health

Scores are reviewer judgments, not accessibility certification or measured conversion performance.

| # | Nielsen heuristic | Score / 4 | Finding |
|---|---|---|---|
| 1 | Visibility of status | 3 | Anchors respond; local-project availability is disclosed late. |
| 2 | Match to the real world | 2 | Clear opening, but methodology/export language needs explanation. |
| 3 | User control and freedom | 4 | Native links, skip navigation, ordinary scrolling, no trapping interaction. |
| 4 | Consistency and standards | 3 | Coherent identity; text links have smaller hit areas than the primary action. |
| 5 | Error prevention | 3 | Honest limitations; earlier availability context would prevent wrong expectations. |
| 6 | Recognition rather than recall | 3 | Capability directory and workflow are visible; actual interface proof is missing. |
| 7 | Flexibility and efficiency | n/a | No expert application task on this promotional surface. |
| 8 | Aesthetic and minimalist design | 3 | Strong hierarchy, but the lower narrative repeats concepts. |
| 9 | Error recovery | n/a | No form, submission, or stateful error flow. |
| 10 | Help and documentation | 2 | Repository/setup links exist; nontechnical exploration needs clearer framing. |
| | **Total** | **23/32** | **72%: Good foundation, improvements recommended.** |

## What works

- The hero communicates the broader platform; the five-capability directory avoids reducing RC Atlas to a task manager.
- Navy, teal, white, and restrained typography provide a consistent institutional identity on desktop and mobile.
- Copy distinguishes delivery progress from indicator evidence and acknowledges limits instead of claiming unsupported impact or public hosting.

## Consolidated priority findings

No P0 or P1 blocker was confirmed within this critique's scope. Priorities below are recommendations awaiting owner approval.

| Priority | Confirmed observation | Interpretation and proposed improvement | Impeccable follow-up |
|---|---|---|---|
| P2 | There are no genuine product screenshots on the page. | The design offers little tangible proof. Add up to two provenance-verified synthetic screenshots in a focused evidence section, with captions explaining what each demonstrates. Feasibility is conditional, not a claim that safe images already exist. | layout |
| P2 | The local-course-project explanation starts around y=3217px on desktop and y=4715px on mobile, after the initial GitHub action. | A first-time visitor may not understand the access model before leaving. Add a brief local-project/no-public-demo explanation beside the opening action; keep the workflow route for nontechnical visitors and label the setup link clearly. | clarify |
| P2 | Mobile navigation link boxes are about 22.4px high; the secondary hero link is about 25.6px, versus 50px for the primary action. | Increase these hit areas toward a comfortable 44px height. This is a usability recommendation, not a proven accessibility-standard failure: spacing exceptions were not exhaustively evaluated. | adapt |
| P2 | The workflow and lower “Know what the result can tell you” section revisit delivery/evidence ideas; terminology includes “fully governed export snapshots.” | Replace that lower section with “Work you can trace. Evidence you can explain.” rather than adding another long section. Use two concise proof narratives and plain-language limits, preserving factual caveats. Reading fatigue is a reviewer judgment, not user-test evidence. | distill / clarify |
| P3 | The live detector identified five short final lines at 1440px: “view.”, “review.”, “decisions.”, “happened.”, “initialization.” | Review text measures and final wording after content approval. Avoid forced line breaks that break mobile layout. | typeset |

## Three required perspectives

| Perspective | What succeeds | Weakest point and proposed response |
|---|---|---|
| Classmate | Can identify five capabilities and follow assignment, submission, validation, approval. | Cannot picture an actual screen or explain one concrete indicator result. Show a real task-review view and a real indicator explanation, each with a short synthetic example caption. |
| Professor | Broad scope, workflow boundaries, limitations, and repository access are represented honestly. | Promotional assertions need traceable product evidence and an accurate process record. Preserve the source capability mapping; record screenshot source, fixture, runtime verification, and image hash. Record the failed delegation honestly. |
| First-time visitor | Clear institutional headline and recognizable page navigation. | GitHub appears before the access model is clear; technical terminology increases effort. Explain local exploration near the CTA and keep a simple on-page workflow path. |

These are scenario-based expert reviews, not interviews with actual classmates, the professor, or prospective users. The mobile/accessibility lens also exposes small tap areas; no actual assistive-technology user testing was performed.

## Editorial-section integration proposal

Retain this order: institutional hero and capability directory → five capability explanations → assignment-to-approval workflow → **Work you can trace. Evidence you can explain.** → explore locally/repository → existing limitations and footer.

Replace the existing lower explanatory section, preserving its useful distinction between work completion and measured results. Pair “Work you can trace” with the genuine task review boundary, and “Evidence you can explain” with an indicator's method, period, baseline, target, and result. Keep screenshots readable in a stacked mobile layout. Do not move this block ahead of the five capabilities, duplicate a large narrative section, or suggest that task approval automatically proves institutional impact.

## Product screenshot feasibility and safety

**Conditional feasibility only. No product screenshot is currently approved or verified for inclusion.** The tracked-image inventory contains promotional-page captures, not established application proof. This critique did not start an application runtime or access canonical runtime data, credentials, backups, or Site.txt.

Source inspection found a plausible synthetic capture route:

- `methodology_runtime_acceptance.py` seeds a fresh disposable PostgreSQL runtime with synthetic names and `example.test` accounts.
- `postgresql_test_support.py` requires an explicit test root, creates fresh storage, binds loopback, and independently queries server data directory, port, and listen address. This is a useful mechanism, not evidence that a runtime has already been created or verified for HW9.
- `methodology_browser_acceptance.js` captures the actual `#methodologyPanel` through browser screenshot APIs. Its example checks actual=60, baseline=20, target=100 → 50% final-target achievement, separately from schedule attainment. These source expectations must be reproduced before any promotional claim/caption uses them.

Recommended captures, pending approval:

1. A Workplan/task-review screen illustrating the submission/review boundary. Its precise synthetic fixture and visible state still need verification.
2. An Indicator Intelligence explanation showing a verified method, period, baseline, target, and calculated result.

Capture only after independently verifying a disposable runtime rooted inside the canonical workspace, using fresh synthetic configuration with live providers disabled. Do not launch the default canonical runtime or copy its data. Record source commit, fixture provenance, runtime isolation evidence, capture steps, and SHA-256 hashes. Visually inspect every exported image for personal/institutional data, tokens, paths, emails, and browser chrome. Use genuine focused UI captures, descriptive alt text, and an explicit synthetic-demonstration caption; never manufacture interface content. If two readable images make mobile too long, use the indicator view alone. If isolation or provenance cannot be established, stop and report the blocker; do not substitute an unverified image.

## Rendered browser and detector evidence

Real Chromium inspection used separate fresh tabs for visual A and detector B, both operated sequentially by the parent. Desktop was 1440×1000; mobile 390×844; additional DOM checks used 320×844 and 720×500. Full-page and viewport captures are in `critique-evidence/`.

- Checked widths had no horizontal overflow or missing internal anchor targets. One main landmark and one h1 were present.
- Computed-color checks found no below-threshold text contrast in their tested solid-background model. This limited script is not a comprehensive accessibility audit.
- Keyboard Tab reached the skip link; Enter navigated to `#overview-start`. Clicking workflow navigation reached `#overview-workflow`. No console errors were observed before detector injection.
- No external resources were loaded by the page before temporary detector injection. External repository/setup destinations were inspected as hrefs here; this critique does not claim a fresh remote availability test.
- CLI detector returned six `cramped-padding` warnings in `overview.html` (line 0, wrapper selectors). Measured child insets were 120px desktop / 20px mobile; main sections had 90px / 58px vertical padding. Rendered inspection does not support those six flush-edge warnings; classify them as false positives for this target, without changing the global ignore list.
- Successful temporary browser injection ran the detector and produced five `straggler` findings, saved in the console transcript and overlay capture. This was headless browser evidence; no reliable user-visible live overlay is claimed.
- The 720px viewport is a narrow-layout check, not a true browser-zoom test. Screen-reader behavior, real-device touch, full keyboard traversal, and complete accessibility conformance remain untested.

## Cognitive load, emotional journey, and minor observations

The five-capability directory presents five simultaneous choices, but it is a useful scan aid and an approved requirement, not a reason to remove a capability. The primary CTA and secondary workflow link are distinguishable. The bigger cognitive costs are repeated explanations and unexplained domain language. The emotional sequence is a confident opening, a text-heavy middle, and an honest but technical GitHub ending. Concrete proof and an earlier access explanation would improve that sequence.

The preview comparison strip is appropriate for selection, but should be removed only when the owner approves the final implementation. Retain the future-video provision without an empty or broken player. Do not use detector warnings as a reason to alter the approved palette or brand.

## Decisions awaiting the owner

1. Approve the four P2 improvements together, or specify a narrower scope; include the P3 typography pass only after the substantive copy is approved.
2. Approve investigating and capturing two genuine synthetic-data views, one indicator view, or keep the page text-only. Capture approval is not publication approval.

No substantive page changes, product runtime execution, push, publication, or HW10 work were performed during this critique. The independent dual-review requirement is still outstanding because both delegated runs failed.
