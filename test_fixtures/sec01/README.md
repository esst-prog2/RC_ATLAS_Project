# Synthetic SEC-01 response contracts

These immutable fixtures preserve the fully authorized executive snapshot and six
project/portfolio report previews captured before the SEC-01 authorization rework.
They are fictional demo/test responses, not institutional runtime data. The test
code fixes the calendar and uses synthetic identities and audit sentinels.

Both files are byte-for-byte copies of the reviewed fixtures in original local
commit `a739b46940089a44a3585157ad09df982165bd42`. Raw execution logs, snapshots of
runtime stores, recovery archives and other generated evidence are not published.

| Published fixture | Original path | SHA-256 |
| --- | --- | --- |
| `executive_snapshot.json` | `sec01-evidence/rework-before/full-snapshot.json` | `0d11e4c522347eb1f59647ca5ae88a1bf98d9de22a92b73324354ba76000bc14` |
| `report_previews.json` | `sec01-evidence/report-preview-before/full-reports.json` | `6e40ef5e29290ec9fa5d80a299c4d58495fef1e8d229cc741dd5daab9d895279` |

The publication review found no credential fields, credential URL/token patterns,
or machine-local paths in these two JSON files. This bounded check is not a
general production-data certification. Do not regenerate expected responses from
the implementation under test to make a failing comparison pass.

The focused tests use these paths by default. Explicit environment overrides remain
available for controlled reproduction; the regression runner uses these fixtures
for verification and separate, non-overwriting evidence paths for capture modes.
