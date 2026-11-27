# HW11 — Session 10 compliant Reveal.js presentation

Prepared for Product Owner review, 27 November 2026. **Not published.** The previously approved PowerPoint, PDF, notes, previews and authentic assets are preserved unchanged.

## Open the presentation

- Running local preview: http://127.0.0.1:8871/RC_ATLAS_Project/slides/
- Standalone deliverable: [slides/index.html](slides/index.html). Copy this single file to a shared computer and open it in a current browser; no RC Atlas server, login, CDN or internet connection is required for the slides.
- [Five-minute speaker script](SPEAKER_NOTES.md). Public notes are embedded in the HTML; press **N** or select **Notes**. Escape closes notes. Arrow keys and Space advance slides and demo stages; left arrow reverses them. F enters fullscreen through Reveal.js.
- [Rendered review gallery](preview/index.html).

## Assignment compliance

Inspected the actual [Session 10 instructions](https://esst-prog2.github.io/10.html) and [professor’s six-slide example](https://esst-prog2.github.io/10-blindspot.html), including its rendered progressive demo, before implementation.

| Substantive slide | Time | Content |
|---|---:|---|
| 1. For whom, and why | 45 s | Institutional users, operational problem, broader capabilities and authentic current Portfolio Overview |
| 2. The demo | 120 s | Six authentic HW10 stages on one slide, using five Reveal.js fragments to replace the initial image progressively |
| 3. Why it works | 60 s | Existing designated-reviewer authorization test, exact assertions, recorded focused result and explicit limits |
| 4. What I learned | 45 s | Documented null-to-zero presentation fallback, exact source line, analytical consequence and unresolved status |
| 5. What's next | 30 s | Cross-role UI harmonization, analytical integrity/reporting and preparation for a Mozambique pilot; explicitly future work |
| Closing | Additional | Thank you, official logo, project link and synthetic-data/development disclosure |

There are exactly six top-level Reveal.js sections, with no nested substantive slides. Five speaking budgets total 300 seconds. The substantive script contains 602 words, approximately 120 words/minute; rehearse against the supplied time budgets. No actual five-minute human rehearsal is claimed.

## Verification and learning evidence

The existing test is `assignment_aware_task_workflow_tests.py:156–168`, `AssignmentAwareTaskWorkflowTests.test_capable_but_non_designated_reviewers_are_rejected`, in accepted UI-01 checkpoint `bbeed8433905e044c7df8f9c7a8ed2364aa1d37f`.

It gives users the relevant capabilities but verifies that non-designated reviewers still receive 403, while the designated validator receives 200. The agent ran **only this test**, in the existing independently guarded synthetic runtime: **1 passed, 0 failures, 0 errors, 0 skips**. Runtime test source matches the checkpoint worktree source. It demonstrates this routing restriction, not all permissions, tenant isolation, analytical correctness or production readiness. The deck does not invent a historical Product Owner test run.

Reproduce from the existing workspace with:

```powershell
python docs/hw11/reveal/evidence/run_focused_check.py
```

This wrapper verifies the retained UI-01 runtime, clears inherited provider settings, installs its guard and runs the one named test. The test seeds its own temporary test fixture; the manual-inspection synthetic dataset is not reseeded. See [recorded output](evidence/focused-check.txt), [runner](evidence/run_focused_check.py), [source record](evidence/source-record.json) and [exact excerpt](evidence/reviewer-test-excerpt.txt). A deprecation warning from the existing Starlette/httpx integration did not fail the test; no dependency changes were made.

The learning source is `logitrack_studio.html:14415`, where `portfolioHealth` uses `numericValue(...) ?? 0`. `docs/ui-01/BACKLOG.md:64` traces missing/NOT_ASSESSED aggregate health to this fallback under UI01-03. The accepted checkpoint still contains it. The slide explicitly reports the unresolved issue and does not claim a fix. A bounded excerpt and result are embedded in the public HTML, so understanding the evidence does not depend on a public URL to the local UI-01 checkpoint.

## Publication plan, pending authorization

An authenticated read of `GET /repos/esst-prog2/RC_ATLAS_Project/pages` confirmed the current configuration on 27 November: **legacy branch publishing, `gh-pages`, path `/`, status `built`**. See [sanitized configuration record](evidence/pages-config.json).

After explicit publication authorization, add only the reviewed HTML bytes as **`slides/index.html` at the root of `gh-pages`**, preserving every existing site file. Do not assume publication from main or docs and do not overwrite the promotional homepage. The intended URL is https://esst-prog2.github.io/RC_ATLAS_Project/slides/. Recheck the remote branch and Pages configuration before that future action. No commit, push or deployment has occurred in this task.

Reveal.js 5.2.1 CSS/JavaScript and all original PNGs are embedded in the approximately 4.3 MB HTML. Its MIT license is embedded too. There are no external runtime resource dependencies or root-relative asset URLs, so the repository subpath and offline delivery both work. The website link requires internet only if followed.

## Validation and preservation

- Chrome validation at 1920×1080 passed: six slides, timing attributes 45/120/60/45/30, six demo stages confined to slide 2, successful image decode, no page errors and no external resource requests.
- ArrowRight, ArrowLeft, Space, N and Escape were exercised. Direct `file://` loading and progressive navigation passed.
- Every slide and every demo stage was rendered and visually inspected. Screenshots retain authentic content; only reversible CSS cropping and scaling are used.
- The HTML includes public-safe English notes, synthetic screenshots, source excerpts and sanitized provenance. No credentials, canonical data, workstation paths or private runtime addresses are included in the public deliverable.
- Hash checks preserve the approved PPTX, PDF, speaker notes and every original asset. All seven worktree paths, branches and HEADs remain unchanged. No application source edits, UI-01 continuation, broad regression suite, commit, push or deployment.

Only `slides/index.html` is the publication payload. Build scripts, preview images, raw professor-reference downloads, local runner and server logs are review/build material, not site content. The original HW11 deliverables remain independently available in the parent directory.

## Final acceptance and publication ? 27 November 2026

The Product Owner accepted this deck and authorized publication. It is now live at https://esst-prog2.github.io/RC_ATLAS_Project/slides/. The Pages deployment succeeded and public validation passed. See [PUBLICATION_REPORT.md](PUBLICATION_REPORT.md). Earlier pending-publication statements above are retained as preparation history.
