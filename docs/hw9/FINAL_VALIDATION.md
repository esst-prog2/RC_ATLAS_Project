# HW9 pre-publication validation

Date: 2026-11-13 (Europe/Budapest). Candidate: `promo/`, implementation commit `6930cd6b88fcde6bd0a71e427282518810413b54`. Status: locally validated, pending owner approval; not pushed or published.

## Actual browser results

| Check | Observed result |
|---|---|
| Viewports | 320×844, 390×844, 768×1024, 1024×768, 1440×1000, 1920×1080 |
| Horizontal overflow | None in the six checked layouts; CSS does not hide overflow to mask defects |
| Approved headline | One h1 with the exact accessible headline |
| Five capabilities | All five retained as directory links and detailed headings |
| Section order | Evidence follows the workflow in the DOM and rendered page |
| Availability disclosure | Local setup and no public live demo appear beside the opening GitHub action |
| Keyboard skip flow | Tab focused skip link; Enter focused main; subsequent Tab presses reached primary GitHub and secondary workflow links |
| Keyboard action | Enter on the workflow link reached #workflow |
| Main navigation | Capabilities, workflow, and explore anchors resolved; capability targets exist |
| Touch areas | Measured navigation, brand, secondary/setup/footer links at least 44px high; primary buttons 50px |
| Semantics | Banner, main, contentinfo, labelled navigation, one h1, logical h2/h3 structure; decorative logo has empty alt next to the RC Atlas link name |
| Contrast basics | Computed text contrast scan found no failures in its solid-background model at all six sizes; explicit visible-focus styles present |
| Console | No console errors observed |
| Outbound links | Public repository and development guide loaded in Chromium; guide navigation returned HTTP 200 |
| Resource loading | No external resources; local favicon loaded; no scripts, embeds, forms, or broken/empty video player |
| Responsive inspection | Desktop/mobile full-page and viewport captures visually inspected; small-mobile and evidence-section captures also reviewed |

Evidence is retained in final-evidence. Browser DOM scripts and gstack accessibility/UX output are diagnostic evidence, not an accessibility certification. No screen-reader session, actual mobile hardware, full keyboard traversal of every link, cross-browser matrix, or true browser-zoom test was performed. Relative stylesheet/favicon paths and fragment links support a project-site URL prefix; public-host verification remains after approval.

## Impeccable detector and typography

Source detector produced six cramped-padding warnings. Actual section containers retain visible horizontal insets (120px at 1440px; 20px at 390px), and main sections use 80px / 56px vertical padding. The three definition rows have 14px bottom padding. These measured, visibly inset elements do not match the reported flush-edge condition. Findings are retained rather than represented as a clean detector pass or suppressed globally.

Balanced headings, pretty paragraph wrapping, simpler copy, and adjusted text measures implement the approved typography refinement. The design remains Institutional Overview with the approved palette and font identity. No new independent critique is claimed; the accepted account-limit disclosure remains intact.

## Content and image accuracy

Capability wording was checked against docs/hw9/CONTENT_REVIEW.md and the cited repository sources. Workflow review boundaries are supported by assignment_aware_task_workflow_tests.py. The explanatory numeric example corresponds to methodology_fixtures.py and methodology_browser_acceptance.js; it is visibly labelled illustrative, not a fresh execution result or institutional measurement. No fabricated interface, operational outcome, publicly hosted app, commercial availability, predictive capability, portfolio aggregation, or finalized report-export claim is introduced.

Both approved screenshot candidates use the owner's allowed text fallback. The supported isolated capture route lacked verified PostgreSQL binaries and psycopg in this environment. No application runtime, canonical institutional data, backups, credentials, or providers were accessed. All PNG evidence is a screenshot of the promotional page itself and is excluded from the website.

## Publication-file inspection

`python docs/hw9/validate_publication.py` passed: exactly four allowlisted regular files; committed bytes equal working bytes and local HTTP responses; all internal anchors and local assets resolve; only two approved outbound GitHub destinations; no scripts/embeds/forms; no suspicious credential or machine-path patterns. The first scanner version falsely matched the standard SVG namespace URL as a Windows drive path; the regex boundary was corrected and the final scan passed. No sensitive content was found.

Manual review of all four files found only promotional copy/styles, a small vector brand mark, and the empty .nojekyll marker. The manifest records their hashes, Git blob IDs, 20,687-byte total, and exact public tree. Reports and evidence remain outside promo/. The proposed GitHub Pages branch root will contain only that tree, not the application repository.

## Git and scope

Only the canonical workspace was used for project files. Seven worktrees remain registered with other worktree refs unchanged; no new worktree, checkout switch, stash, reset, clean, force operation, or external project directory was used. The original preview HTML/CSS/generator remain unchanged. Existing Site.txt and local .impeccable artifacts remain untracked and unstaged. Backend and security files were not changed. No HW10 generation, push, publication, or remote configuration change occurred.

The loopback-only static preview remains running for owner review. No disposable application runtime or database process was launched. Final approval must cover both the page and the publication plan before any push or Pages configuration change.
