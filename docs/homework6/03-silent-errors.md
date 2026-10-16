# Review 3: Silent Errors and Exception Handling

## Scope

Reviewed all tracked Python application, repository, migration, service, script, and test code for broad exception handlers, empty `pass` blocks, suppressed rollback/cleanup failures, implicit `None` returns, and fallback behavior that can conceal operational or data errors. Generated and vendor artifacts were excluded.

## Method

- Searched every tracked Python file for `except`, `pass`, `return None`, and suppression patterns.
- Traced candidate handlers into their callers and existing tests.
- Distinguished best-effort cleanup and explicitly reported fallback paths from silent loss of authoritative data.
- Ran focused repository tests after the correction.

## Finding

### Persisted user-permission corruption was silently hidden

`repositories/users.py` decoded `permissions_json` inside a broad `except Exception` and replaced any malformed value with an empty list. A valid JSON object was also silently converted to an empty list because only arrays are supported. Both cases concealed repository corruption and could silently change effective authorization after hydration.

The correction now:

- catches the specific JSON decoding failure;
- raises a content-safe `ValueError` for malformed JSON;
- rejects valid JSON with the wrong shape; and
- preserves the existing array contract for valid records.

Focused regression coverage in `repository_tests.py` corrupts a disposable repository record and verifies both malformed JSON and a non-array document are rejected. No stored value is included in the error message.

## Other Reviewed Paths

- Transaction rollback and temporary-file cleanup handlers intentionally suppress secondary cleanup errors while preserving the primary exception.
- Notification due-run handlers convert provider failures into explicit failure results and audit state rather than dropping them silently.
- Projection synchronization logs failures and exposes strict-mode behavior.
- Numeric parsing helpers use documented optional-value fallbacks; changing those semantics would require a business-rule decision.
- The legacy compatibility module contains broad handlers, but modifying that divergent retained surface without confirmed callers would be a risky refactor.

## Tests

Command:

```text
py -m unittest -v repository_tests
```

Result: 7 tests passed, including the two corruption cases.

## Remaining Risks

- `repositories/common.py` still provides a generic JSON-default helper for notification recipient arrays; invalid persisted recipient data can be hidden and should be addressed with a domain-specific validation contract.
- Some analytics aggregation paths ignore malformed optional numeric values. Their desired error/quality-state behavior is not specified and was not changed.
- Best-effort backup creation during JSON persistence does not currently surface backup-write failure to callers.
