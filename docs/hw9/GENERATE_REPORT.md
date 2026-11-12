# HW9 generate results

Date: 2026-11-12 (Europe/Budapest). Branch: hw9-promo-page. Baseline: 5d487f8ff2fff3a864bc5405a90d2555ee3b5218.

## Outcome

Three complete code-first promotional variants, at comparable content and fidelity:

| Variant | Working preview | Desktop capture | Mobile capture |
|---|---|---|---|
| Evidence-led editorial | http://127.0.0.1:8769/editorial.html | previews/screenshots/editorial-desktop.png | previews/screenshots/editorial-mobile.png |
| Institutional overview | http://127.0.0.1:8769/overview.html | previews/screenshots/overview-desktop.png | previews/screenshots/overview-mobile.png |
| Accountability journey | http://127.0.0.1:8769/journey.html | previews/screenshots/journey-desktop.png | previews/screenshots/journey-mobile.png |

Comparison: http://127.0.0.1:8769/index.html. Each variant also has desktop-full and mobile-full captures, linked from the comparison page. No variant was selected, accepted, or published. Critique and HW10 were not started.

## Actual tool execution

- Impeccable 4.7.0 live-generate initially reported config_missing. Created only the new local .impeccable/live/config.json, scoped to the newly created promotional target; original .impeccable/config.json remains untouched. detect-csp returned shape:null and no signals; no application security control was changed.
- Connected browser access returned host unavailable. Used the installed gstack browse.exe local Chromium driver; no substitute for Impeccable was needed.
- Impeccable live-generate --action impeccable --count 3 successfully produced browser session 3924587e and its real scaffold. Delivered all three variants in one target edit and sent live-poll --reply 3924587e done. live-status confirmed arrivedVariants:3, phase:cycling, generationPhase:all_variants_ready.
- Retained standalone copies of all three designs for durable comparison and screenshots. The user's explicit request for screenshots takes precedence over the live skill's ordinary wait-until-accept screenshot rule.
- Stopped the helper after delivery without calling accept or discard. The poll returned exit with a successful done acknowledgement. Removed generated session wrappers/injection from the served HTML; live.html now links to the comparison page. No winner is baked into source.
- No subagents, external model review, generated images, product runtime, or product screenshot capture were used.

## Identity and composition

Identity lock: inherited navy #123b5d, teal #11828a, pale blue-gray surfaces, Segoe UI/Aptos Display family, clear institutional wording, and restrained borders. Three primary axes: editorial proof composition; dark platform directory; a continuous conceptual journey and vertical task handoffs. Each retains the exact approved headline in its heading text and all five supported capabilities, limitations, workflow, repository action, and local setup link.

The Explore section is structurally ready for a future media block. It currently contains useful text, not a video player or a fake play control. No video was generated.

## Browser verification

Using the gstack Chromium driver, all three pages returned HTTP 200 and were inspected at 1440x1000, 390x844, and 320x900. verify_preview.js checked heading structure, anchor targets, horizontal overflow, visible text contrast against inherited solid backgrounds, and external resource loads.

| Check | Observed result |
|---|---|
| One main heading with the approved headline | All three passed |
| Horizontal overflow | None at the three tested widths |
| Broken in-page anchor targets | None |
| Text contrast under the script's solid-background calculation | No failures at tested widths |
| External page resources | None; fonts are local system stacks |
| Workflow navigation click | All three reached their correct workflow anchor |
| Keyboard skip link | Editorial Tab focused the skip link; Enter reached editorial-start |
| Public repository and setup-guide links | Both loaded in the browser; setup-guide navigation returned HTTP 200 |
| Screenshot inspection | Desktop and mobile first screens reviewed for all three; full-page captures also inspected |

The Impeccable mechanical detector reported warnings, including 11px preview-label text and suspected cramped padding. Increased the mobile preview label to 12px, permitted wrapping, and recaptured/rechecked all mobile previews. Padding warnings include section wrappers with nested inset containers and CSS logical padding; the observed renders have the intended insets. Warnings are not represented as a clean detector pass. A full accessibility certification and cross-browser/device test are outside this preview-selection step.

Initial browser CLI attempts using embedded double quotes in selectors/expressions failed because of Windows argument handling. File-based eval and a quote-free navigation selector succeeded. Earlier console output included Chromium GPU screenshot performance warnings; no product failure is inferred from those warnings.

## Image provenance and preview boundary

All PNGs are actual browser screenshots of the promotional HTML written in this step. There are no application screenshots or invented interface mockups. Diagrams are labelled as conceptual/workflow illustrations. No canonical runtime data, backups, Site.txt, provider credentials, or institutional records were opened.

PREVIEW_MANIFEST.json records every served file's SHA-256, size, and verified local HTTP status. The server exposes only docs/hw9/previews on 127.0.0.1, not the repository root. It includes only promotional HTML/CSS and their browser captures. This manifest is for local design review, not authorization to publish the preview bundle.

## Reopen and selection

From the canonical checkout, if the local server has stopped:

```powershell
python -m http.server 8769 --bind 127.0.0.1 --directory docs/hw9/previews
```

Open http://127.0.0.1:8769/index.html and choose in the chat. HTML files also work directly from disk. The owner must select the visual direction before critique/final implementation; publication remains a separate approval.
