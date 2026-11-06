# Full development consolidation — local publication candidate

Prepared 5 November 2026. No push, merge, deployment, or published-history rewrite.
The independent clone is on `integration/full-development-20261105`, based on
published GitHub main `aed00a04e395da09b8246503370c5692432c03d0`. The original worktrees and recovery archives were
not modified. This report describes local integration, not production readiness.

## Ancestry and traceability

All four unpublished commits form one dependency chain from common ancestor
`6ee278af46abe37968c03b256252d7824c75ecf5`. GitHub main already contains that ancestor
and the HW6 review. Replaying the four unpublished changes onto main avoids
replaying published work or reverting its corrections.

The owner explicitly selected publication-only copies because the SEC-01 original
contains 83 generated evidence files. All original authors, author dates,
committer identities and committer dates are preserved. Each copy records its
original SHA in an `Original-Commit` trailer. The copies have new IDs and parents;
they do not claim the original development branch as a Git ancestor. Original
objects and branches remain local. Do not merge the original remediation branches
after publishing these copies: that would duplicate development and expose the
excluded historical evidence.

| Original commit | Publication copy | Original author date |
| --- | --- | --- |
| `2ec64f7b100c317daed4061efe46b896a38e2888` | `90c0c40153a571448572456d1f3b1d35ec9c20be` | 2026-10-23T20:16:57+02:00 |
| `fadf7de6781c7fb96e3978e7b3b5aac5f195af26` | `e1870cce8f88d1276f4d15bb799f78dbd98a9802` | 2026-10-25T16:16:27+01:00 |
| `8113299e5bfa1c310015f6b30fd2680abca2538d` | `fab04a4fb0b0da5794130845928a8439f2ae3fa6` | 2026-10-27T23:11:59+01:00 |
| `a739b46940089a44a3585157ad09df982165bd42` | `2f8217c177f8a29e729215aaa57a4795b5352a09` | 2026-11-04T17:45:06+01:00 |

The order is Wave 1 persistence/security, methodology core, analytical consumers,
then SEC-01. A separate integration checkpoint records the fixture relocation,
test reconciliation and this publication review. It represents real integration
work, not an artificial homework milestone.

## Included and excluded content

The accompanying JSON contains all **90 changed/added paths** relative to
published main, the full 83-path exclusion list, source hashes and test receipts.
Production code, migration definitions, tests, methodological contracts, security
conditions, implementation reports and planning history are retained.

The published academic README is byte-identical as a Git blob. Course demonstration,
HW6 review documents, dependency constraints, provider adapter keyword correction,
repository corruption tests and route-uniqueness tests remain. The published removal
of the unused nested platform copy is retained; active platform files are preserved.

Raw `sec01-evidence/` is absent from every publication-copy tree. Two independently
captured synthetic response fixtures were reviewed and copied byte-for-byte into
`test_fixtures/sec01/`; their README records provenance and hashes. Test verification
now uses those files, while reproduction captures retain separate non-overwriting
paths. No production snapshot or runtime database was included.

Untracked Package 1/2 generated evidence stays in its original worktree. The local
Package 1 precommit review stays local: it is an approval/recovery artifact rather
than implementation content. Its previously uncommitted commit-authorization line
was preserved by appending it to the integrated planning log. No source changes
were silently discarded.

## Conflict resolutions

- `requirements.txt`: retain published FastAPI/Uvicorn/HTTPX constraints and add
  the Wave 1 psycopg dependency.
- `repositories/users.py`: retain published rejection of corrupt JSON and invalid
  non-array records, while allowing SEC-01's validated versioned envelope. Invalid
  envelopes still fail in the shared decoder; valid legacy lists keep their meaning.
- Semantic test reconciliation: the HW6 SendGrid adapter test still verifies
  `sender_email`, now using synthetic server-side environment configuration. It
  additionally checks that request-supplied credentials cannot override it. The
  security implementation's rejection of caller-provided provider secrets remains.

No unresolved index conflicts remain. Other source changes combine without manual
conflict resolution. New fixtures do not replace expectations with current output.

## Validation

| Run | Tests | Failures | Errors | Skips |
| --- | ---: | ---: | ---: | ---: |
| boundary-verified | 120 | 0 | 0 | 0 |
| workflow-security-verified | 287 | 0 | 0 | 0 |
| postgresql-verified | 31 | 0 | 0 | 0 |
| fixture-portability | 15 | 0 | 0 | 0 |

The first three runs total **438 tests**. The final 15 are a focused repeat after
fixture relocation, not additional unique tests. They cover academic workflow,
permissions, tenant boundaries, CSRF/session behavior, methodology/provenance,
analytical consumers, notification boundaries, concurrency/idempotency, logical
framework persistence, and actual disposable PostgreSQL/PostGIS behavior.

The initial diagnostic boundary run recorded 1 failure and 101 errors: the test
harness blocked Windows asyncio's internal socket pair, and the old SendGrid test
used the superseded request-credential contract. A concurrent workflow diagnostic
was stopped after the harness error was identified. Both were corrected before
the accepted runs above; diagnostic artifacts remain local and are not passes.

Synthetic canonical paths and temporary directories were verified inside fresh
local runtimes; external-provider credentials were not inherited. The local runner
blocked non-loopback Python socket connections. The PostgreSQL helper created new
loopback-only clusters and independently checked their data directories, ports,
server identities and application-role boundaries. All owned database processes
were stopped. No packages were installed and no existing database was accessed.

Each accepted run verified unchanged tested source hashes. Final diff whitespace,
ancestry, unique SHA mapping, README blob identity and raw-evidence exclusion were
checked separately. Browser-related Python tests do not constitute a new real-browser
acceptance run. Live-provider/browser acceptance and production behavior are not
certified by this consolidation.

## Publication/security findings and remaining conditions

- The bounded scan covered 184 unique changed blobs across the unpublished commits;
  no high-confidence private-key/token/JWT/credential-URL pattern was found. This
  is not proof that all possible secrets or all older history are absent.
- The original SEC-01 archive contains machine/runtime/recovery metadata, e.g.
  `sec01-evidence/local-checkpoint-manifest.json:744,747` and
  `sec01-evidence/rework-verification-summary.json:3`. A later deletion could not
  prevent publication through original ancestry; the approved copies exclude it.
- Retained implementation reports contain local evidence references, e.g.
  `SEC01_IMPLEMENTATION_REPORT.md:3,136`. These are technical development references,
  not bundled runtime data or proof those private/local evidence paths exist on
  GitHub. No confidential institutional records were identified in reviewed additions.
- SEC-01's old-binary compatibility fence and MANAGE_USERS grant-ceiling/separation
  policy remain unresolved production blockers, documented in
  `SEC01_ROLLOUT_AND_DELEGATION_CONDITIONS.md`. No deployment gate or delegation
  policy was silently implemented during integration.
- Package 2 **CONDITIONAL**; RCQA-011 **OPEN**; Internet release **NO-GO**.

## Commands for final review and separately approved publication

Run from this integration clone. Review commands are read-only:

```powershell
git status --short
git log --oneline origin/main..integration/full-development-20261105
git diff --check origin/main..integration/full-development-20261105
git diff --stat origin/main..integration/full-development-20261105
git ls-remote --heads origin main
```

Only after publication approval and confirmation main has not moved:

```powershell
git push origin integration/full-development-20261105:refs/heads/integration/full-development-20261105
```

That explicit branch push is proposed, not executed. No `--all`, `--mirror`, force
push or original remediation-branch push is intended. Integration into GitHub main
requires separate approval. Do not rerun the four commits on top of this branch.
