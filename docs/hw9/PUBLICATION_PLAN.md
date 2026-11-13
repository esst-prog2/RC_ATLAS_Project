# HW9 publication candidate — awaiting final owner approval

Canonical workspace: `D:\MASTER SURVEY STATISTICS & DATA ANALYSIS\ADVANCED PROGRAMING\RC_Atlas_Project`.
Working branch: `hw9-promo-page`. Baseline: `5d487f8ff2fff3a864bc5405a90d2555ee3b5218`.

## Exact proposed source

Repository: `https://github.com/esst-prog2/RC_ATLAS_Project`.
Pages setting: **Deploy from a branch → gh-pages → /(root)**.
The proposed publication branch will contain only the reviewed `promo/` Git subtree, promoted to its root. It will not contain the full HW9 checkout or inherit application files in its root tree.

Reviewed website tree: `0565ed4592454e1c7f4261921cd0cd455985ec24`, from implementation commit `6930cd6b88fcde6bd0a71e427282518810413b54`. This exact tree can be used to make a standalone publication commit through Git object commands after approval, without changing the current checkout, touching its index, or creating a worktree. A normal non-force push will be used. If a competing gh-pages branch appears, stop and reassess; do not overwrite it.

## Complete website inventory

| Canonical source | Publication path | Bytes | Purpose |
|---|---|---:|---|
| promo/index.html | /index.html | 10,400 | The complete promotional page |
| promo/styles.css | /styles.css | 10,125 | Responsive styles and accessibility states |
| promo/favicon.svg | /favicon.svg | 162 | RC Atlas mark used in the selected preview |
| promo/.nojekyll | /.nojekyll | 0 | Static-site publishing marker |
| **Total** | **4 files** | **20,687** | No build dependencies or JavaScript |

See PUBLICATION_MANIFEST.json for each file's SHA-256, Git blob ID, and successful local HTTP verification. The public tree contains only regular files: no symlinks, hard links, runtime files, hidden secrets, source maps, reports, or directories. The external links are the public repository and its local setup guide. There are no third-party assets, forms, embeds, cookies, analytics, or data-upload paths.

PROCESS.md, PLANNING_LOG.md, PRODUCT.md, docs/hw9, docs/ui-01, browser screenshots, manifests, scripts, application source, local data, backups, Site.txt, and .impeccable are **not part of the Pages tree**. Existing untracked artifacts remain unstaged. The topic branch's tracked source and homework records will nevertheless be visible through GitHub if that branch is pushed to the public repository; website exclusion is not repository privacy.

## Method evaluation

| Method | Assessment |
|---|---|
| Publish the HW9 branch root | Rejected: would expose application and technical files through the website. |
| Publish /docs from the HW9 branch | Rejected: includes unrelated reports and evidence. |
| Custom Actions workflow uploading only promo | Supported alternative, but adds workflow permissions/configuration and is unnecessary for four static files. |
| Dedicated gh-pages branch containing only the reviewed tree | Recommended: explicit file boundary, no build tooling, no merge into application main, and no checkout/worktree change required. |

GitHub supports publishing an arbitrary repository branch from its root or /docs, and recommends branch publishing when no custom build is needed. A custom Actions artifact is another supported option. References checked on 2026-11-13: [Publishing-source configuration](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) and [custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Read-only remote verification

The GitHub connector confirmed the repository is public, default branch main, with administrative permission available. Its available tools do not expose Pages configuration, so the public GitHub REST repository endpoint was used read-only: `has_pages=false`. `git ls-remote` showed origin/main still at the stated baseline and no remote gh-pages branch. No remote setting or ref was changed. This does not constitute successful deployment or guarantee that every organization-level deployment condition has been met.

## Approval scope and later execution

Owner approval is requested for this final page, the four-file inventory, pushing the HW9 commits, and publication from the proposed assets-only gh-pages branch. No approval is inferred from the earlier refinement authorization.

After approval:

1. Recheck current Git status, the seven registered worktrees, remote branch state, and the exact public-tree/hash inventory. Stop on unexpected changes or conflicting publication state.
2. Record the actual owner decision in PROCESS.md and PLANNING_LOG.md; commit it on hw9-promo-page. Push only explicitly named HW9/publication refs, never qa-system-audit or unrelated branches.
3. Create the gh-pages publication commit from the approved four-file tree without switching the canonical checkout. Push normally and configure Pages to gh-pages /(root).
4. Wait for the Pages deployment result; inspect failures rather than assuming push success equals publication.
5. Verify the public HTML and assets, desktop/mobile rendering, links, and that unrelated report/runtime paths are not served. Record the final configuration, public URL, checks, and commits, then push the final HW9 process record.

Expected URL, **not yet published or verified**: `https://esst-prog2.github.io/RC_ATLAS_Project/`.

## Local review

Running preview: `http://127.0.0.1:8770/`. It serves only promo/ on loopback. Reopen from the canonical workspace with `python -m http.server 8770 --bind 127.0.0.1 --directory promo` if needed. Desktop/mobile page captures are under docs/hw9/final-evidence; these are review artifacts and excluded from publication.
