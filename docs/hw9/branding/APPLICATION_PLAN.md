# Approved RC Atlas logo: source and application reuse plan

Owner instruction, 13 November 2026: use the supplied logo exactly, prepare proportional website/favicon/application sizes, preserve Institutional Overview, and show the result before publishing. No application UI changes are authorized until this plan is reviewed.

## Source and sizing

The source is `a_clean_professional_flat_logo_on_a_white_backgro.png` in the canonical project root. Its exact-byte archival copy is `approved-source.png` here; SHA-256 `479835cff8a75eabb4e8f62e1d51093a374e775344628a77db1b2d2c10459cc7`. It is a 1536 by 1024 RGBA raster PNG with transparent margins, not a vector. Original file metadata contains no extra fields. Source and alpha are retained without cropping, redrawing, recolouring, stretching, background removal, or generated replacement artwork.

`prepare_assets.py` uses Pillow Lanczos resizing and optimized PNG encoding. Website copies are 192 by 128 and 384 by 256. Icon-only versions use the supplied symbol, which already has no wordmark: the complete source is centered on a transparent square and resized to 48, 96, 192 and 384px. ICO contains 16, 32 and 48px frames. The broad original margins limit tiny favicon legibility; a tightly cropped or simplified mark requires separate owner permission. No true-vector SVG is claimed.

## Inspected application locations (source inspection only)

| Location | Safe proposed change after approval |
|---|---|
| `logitrack_studio.html` `.sidebar-brand`, around line 7178; role-specific CSS around 5586; translated name selector around 9732 | Add an image beside the existing RC Atlas text; retain text, subtitle, translation selectors, navigation, and role rules. Use proportional sizing and empty alt when adjacent text already names the product. |
| `logitrack_studio.html` `#loginShell .auth-panel.brand`, around line 6967; translated name selector around 9687 | Add the approved mark to the existing brand block; leave login forms, bootstrap controls, authentication and trusted-setup behavior untouched. |
| `logitrack_studio.html` `.splash-brand`, around line 6948 | Assess a shared brand treatment only after the requested sidebar/login integration is approved; preserve status and loading semantics. |
| `LogiTrackRC v4.4.py` `/favicon.ico`, around line 8102 | Currently returns a placeholder SVG despite the ICO route name. Replacing it requires a separately scoped backend/static-serving change and content-type checks; no route changes in this HW9 task. |
| Organization settings `orgLogoPlaceholderInput`, around line 8597 | Keep separate: institutional/customer branding is not the RC Atlas product mark. |

Reuse the prepared assets through a narrow explicit static asset route once authorized; never expose the repository directory as application static content. Confirm the then-current implementation before applying this plan, because UI-01 and remediation branches must remain untouched now. Test the eventual change in a verified disposable synthetic runtime, including roles, languages, keyboard access, login states and asset MIME types. No canonical runtime/data/provider access was performed for this plan.

## Sequencing and publication boundary

Only the promotional page is being changed now. The updated candidate requires a new GitHub Pages deployment and approval of its revised asset inventory; prior four-file approval does not cover new assets. Do not push or update `gh-pages` until the owner reviews the preview.

Owner-directed future sequence: finish HW9 and HW10 before backend/frontend consolidation or Mozambique mapping work. After HW10, resume UI-01 by auditing existing backend mapping, administrative boundaries, province/district matching, and frontend integration points. Reuse working components. The future map should locate projects by Mozambique province/district names and support district-level project and indicator exploration. This records the requirement only; no mapping audit, implementation, consolidation, or HW10 work has started.
