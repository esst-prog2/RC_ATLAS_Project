# Review 2: Duplicate and Dead Code

## Scope

Reviewed all tracked Python modules, package layouts, wrappers, migration utilities, tests, scripts, specifications, and documentation for duplicate implementations, unreachable copies, divergent compatibility files, and dead public surfaces.

## Method

- Compared tracked file hashes and package trees.
- Searched every tracked Python and documentation file for imports and path references.
- Compared the two relational-store implementations with `git diff --no-index`.
- Preserved compatibility and archive material whenever external callers could not be disproved.

## Findings

### R2-1: Unreachable nested `logitrack_platform` package duplicated active modules

`logitrack_platform/logitrack_platform/__init__.py` and `runtime.py` were byte-identical to the active outer package. The nested `relational_store.py` was an obsolete divergent copy: it lacked current indicator organization ownership, Logical Framework projection tables, user tenant fields, and foreign-key behavior present in `logitrack_platform/relational_store.py:37-776`.

No tracked import, manifest, setup file, command, or documentation referenced `logitrack_platform.logitrack_platform`. Application, repository, migration, and test imports all resolve `logitrack_platform` from the outer package (`LogiTrackRC v4.4.py:42-48`, `repositories/common.py:9`, `migration/sync_helpers.py:8`, `logitrack_smoke_tests.py:8-12`).

**Action:** removed the three unreachable nested package files. The canonical outer package and import paths are unchanged.

### R2-2: Legacy monolith is divergent but not safe to delete

`logitrack_rc_v4_4.py` overlaps substantially with the active `LogiTrackRC v4.4.py`, but the repository labels legacy compatibility files as intentionally retained (`docs/DEVELOPMENT.md:72-76`). The active server wrapper explicitly loads `LogiTrackRC v4.4.py` (`logitrack_rc_v4_4_api.py:4-15`), yet an untracked external user could still invoke the legacy module directly.

**Action:** documented the divergence and retained the file. Consolidating it requires an explicit compatibility/deprecation decision.

### R2-3: Archived specifications are intentional records

Files under `openspec/changes/archive/` repeat canonical requirements by design. They are historical evidence, not executable duplicate code, and were retained.

## Corrections

- Removed only `logitrack_platform/logitrack_platform/`.
- No active import, API, storage schema, or runtime behavior was changed.

## Tests

- Import and relational-store smoke tests.
- Logical Framework projection tests.
- Repository contract tests.

## Remaining Risks

- The legacy `logitrack_rc_v4_4.py` implementation can continue to drift from the active application until a supported entry-point policy and deprecation plan are approved.
- Static repository search cannot prove that no external script imports the removed nested path. The absence of packaging metadata and tracked callers makes that risk low; the supported import remains unchanged.
