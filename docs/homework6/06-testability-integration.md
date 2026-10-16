# Review 6: Testability, Architectural Assumptions, and Integration

## Scope

Reviewed the complete tracked application, wrappers, route registrars, services, repositories, migrations, tests, scripts, and documentation for live-value dependencies, mixed I/O and business logic, implicit global assumptions, untested contracts, and integration gaps. No live provider, server, browser, production value, or external endpoint was used.

## Method

- Mapped the active entry wrapper to the monolithic application and modular service/route dependencies.
- Compared dependency call sites with their wired callable signatures.
- Reviewed tests for source-string assertions, real integration behavior, isolated storage, clocks, environment dependence, and network boundaries.
- Added deterministic contract tests for two high-confidence gaps.

## Findings and Corrections

### SendGrid service-to-adapter keyword mismatch

`services/notifications.py` invoked the SendGrid dependency with `sender=`, while the active adapter in `LogiTrackRC v4.4.py` declares `sender_email`. Python therefore raised `TypeError` before provider I/O for every configured SendGrid request.

The service now uses `sender_email`. `notification_integration_tests.py` supplies a strictly declared fake adapter and proves the service reaches it with the expected arguments. The test performs no network operation and uses only synthetic values.

### Route tests collapsed duplicates

Registrar tests converted route lists to sets before comparison. They verified expected membership but could not detect duplicate method/path registration. A new active-application test counts method/path pairs and fails on duplicates without hard-coding a route total.

## Architectural Observations

- `logitrack_rc_v4_4_api.py` is a thin import wrapper around the active `LogiTrackRC v4.4.py`; the latter combines domain models, persistence, analytics, provider adapters, application assembly, and many direct routes. This increases import cost and makes dependency substitution uneven.
- Modular services use injected dependency dataclasses, which enables deterministic tests, but their callable contracts are typed only as broad `Callable[..., Dict[str, Any]]`; the SendGrid mismatch demonstrates that static checking cannot validate them.
- Several Studio tests inspect HTML/JavaScript source strings. They are useful structural checks but are not browser interaction, accessibility, responsive-layout, or persistence evidence.
- Date-sensitive analytics call the wall clock directly. Reproducible analytical tests require an injected `as_of` or clock contract.
- Provider adapters, persistence, and rule state are not coordinated through a durable outbox; success followed by save failure remains ambiguous.

## Tests

Commands:

```text
py -m unittest -v notification_integration_tests route_compatibility_tests
py -m unittest discover -v -p *tests.py
git diff --check
```

Focused result: 9 tests passed without network access.

Final complete-suite result: 265 tests ran in 179.483 seconds; all passed with zero failures, errors, or skips. The four tests added during Homework 6 cover corrupt permission JSON (two cases), SendGrid adapter wiring, and active route uniqueness.

## Remaining Risks

- Provider acceptance, timeouts, partial recipient delivery, retries, and duplicate prevention require a separately authorized sandbox and durable delivery design.
- Callable protocols or typed adapter interfaces would catch more wiring errors than broad callables, but introducing them across every adapter is a wider refactor.
- Active route uniqueness does not prove each request/response/error contract.
- Browser journeys, restart recovery, concurrent writes, and deterministic clock behavior remain outside the synthetic suite.
