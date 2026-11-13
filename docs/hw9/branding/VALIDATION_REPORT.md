# Approved logo integration: review candidate

13 November 2026. **Local implementation complete; not pushed or published.**

## Result

The Institutional Overview promotional page now uses the exact owner-supplied logo. The source PNG is archived byte-for-byte and identified by SHA-256 in ASSET_MANIFEST.json. Derivatives retain its original transparency, complete composition and proportions. There is no cropping, recolouring, vector tracing, AI-generated replacement or application change.

The website image has 192x128 and 384x256 PNG sources. Its display box is 90x60 on desktop and 78x52 on mobile. Transparent square icon versions at 48, 96, 192 and 384px and an ICO with 16/32/48px frames are ready for future reuse. All of these are raster assets, not SVGs.

## Preview and checks

- Local website: http://127.0.0.1:8782/ (loopback server rooted only at promo).
- Local background/size review: http://127.0.0.1:8783/preview.html (rooted only at this branding review directory).
- Saved browser captures: evidence/desktop.png, evidence/mobile.png, evidence/desktop-full.png, evidence/mobile-full.png and evidence/backgrounds-and-sizes.png.
- Actual gstack headless Chromium renders at widths 320, 390, 768 and 1440px: logo decoded, 3:2 aspect ratio intact, no horizontal overflow or broken anchor targets. Header links remain at least 44px tall. At device scale 2, the browser selected logo@2x.png.
- Keyboard Tab reached the skip link; Enter focused main. Clicking the brand reached #main and clicking The workflow reached #workflow. Brand link accessible name remains RC Atlas without a duplicate image announcement.
- The visible page text and all anchor hrefs were compared with the previously published implementation: identical. Five capabilities, headline, workflow, evidence explanations and local-setup notice remain intact. Application source diff is empty.
- Every one of the seven proposed public files returned HTTP 200 locally with bytes equal to the committed candidate. PNG dimensions, RGBA transparency, absence of metadata, ICO frame sizes, regular-file boundary, anchors, srcset references and existing outbound-link allowlist passed. No scripts, forms, application data, reports or credentials are included. Unchanged external destinations were checked against the approved allowlist; no new external-link availability claim is made.
- Browser network confirmed CSS and both resolution-specific logo sources loaded; there were no page console errors. Favicon files were HTTP-checked and decoded; native browser tab chrome was not captured.
- Impeccable 4.7.0 context and detector ran. Six existing cramped-padding warnings remain static-analysis false positives for nested wrappers: actual hero insets are 120px desktop / 20px mobile, section vertical padding 80px / 56px, bordered definition rows 14px. No layout redesign was made to silence these warnings.
- gstack skill-start reported a workflow lease warning; browser execution itself succeeded. No upgrade or lease repair was attempted. Aside was unavailable on this Windows environment, so the gstack headless Chromium fallback was used. No independent agent review is claimed.

## Visual limitation requiring owner awareness

The supplied composition includes generous transparent margins. Its complete mark looks balanced beside the website name and remains recognizable on white, navy and near-black backgrounds. At a 16px square favicon size the actual symbol occupies roughly half the box and loses fine detail; 24/32px are also reduced. This is visible in the background/size sheet. A tighter crop or simplified small-size mark could improve it, but neither has been performed or approved. Current assets preserve the exact design as requested.

## Proposed deployment inventory

The old four-file site remains live at gh-pages commit 1f1a1f9. A **new deployment and explicit approval of this seven-file inventory are needed** for the logo update:

| Root file | Bytes |
|---|---:|
| .nojekyll | 0 |
| favicon.ico | 3,170 |
| favicon.png | 1,635 |
| index.html | 10,526 |
| logo.png | 11,925 |
| logo@2x.png | 37,965 |
| styles.css | 10,240 |
| Total | 75,461 |

Exact Git tree: `3a6e92000e6437f754a1b70f2f7174a39bd02e33`. See PUBLICATION_MANIFEST.json here for hashes. The original logo, application-size variants, scripts, plans, screenshots and this report stay outside Pages. favicon.svg is removed from the candidate because it contained the old placeholder.

## Preservation and reuse

All seven worktrees remain registered; no branch switch, force operation, new worktree, backend execution, application edit, mapping implementation or consolidation occurred. The supplied root PNG and existing .impeccable/Site.txt remain untracked; the approved source is preserved in the committed branding archive. gh-pages and main were not updated, and no commits were pushed.

Application branding integration is **planned only** in APPLICATION_PLAN.md. The future favicon route replacement needs a separately authorized application/backend scope; existing organization logos must remain distinct from the product identity. Owner's post-HW10 mapping/consolidation sequence is recorded there, not started.

Durable learning: the approved PNG has transparent outer margins, despite appearing black in the initial image viewer. Preserve alpha and inspect real backgrounds; do not infer an opaque background or auto-trim based on that viewer.
