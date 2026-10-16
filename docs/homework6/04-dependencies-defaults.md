# Review 4: Dependencies and Dangerous Defaults

## Scope

Reviewed all tracked dependency manifests, Python imports, installation and run documentation, environment-driven configuration, storage defaults, CORS setup, provider configuration, and test setup. No package was installed or upgraded during this review.

## Method

- Inventoried manifest files and imports across active source, scripts, migrations, and tests.
- Compared direct third-party imports with `requirements.txt`.
- Queried the local interpreter for installed direct versions already used by the baseline suite.
- Traced environment defaults for storage, CORS, scheduler, relational synchronization, API protection, and notification adapters.
- Ran import and route-registration checks after updating dependency metadata.

## Findings and Corrections

### Direct dependencies were unconstrained

`requirements.txt` declared FastAPI, Uvicorn, and HTTPX without versions. A fresh installation could therefore resolve a future incompatible release even though no compatibility evidence exists for it.

The manifest now constrains each direct dependency to the compatible release line exercised by this checkout:

- FastAPI `>=0.141.1,<0.142`
- Uvicorn `>=0.53.0,<0.54`
- HTTPX `>=0.28.1,<0.29`

This is deliberately not presented as a transitive lock. Producing a deployment lock requires a clean target-platform environment and review of the complete resolved graph.

### Development documentation contradicted the available baseline

`docs/DEVELOPMENT.md` stated that FastAPI and Uvicorn were unavailable and dependencies were unpinned. It now records the versions used by the baseline test run and distinguishes compatible direct constraints from a deployment lock.

### Third-party import coverage

All active non-standard imports are supplied by FastAPI or the three direct requirements. Pydantic and Starlette are transitive FastAPI dependencies and are not imported directly by application modules.

## Dangerous Defaults Retained for Dedicated Security Work

- `LOGITRACK_API_ALLOW_ORIGINS` defaults to wildcard CORS in `LogiTrackRC v4.4.py`.
- Provider settings and destinations may be supplied through request payloads as well as environment variables.
- The local JSON data path defaults to the current working directory.
- Relational projection synchronization is enabled by default and non-strict unless configured otherwise.

These behaviors are security and deployment-policy concerns. They were documented rather than changed in this dependency commit because changing them would alter runtime/API behavior and needs focused security tests and migration guidance.

## Tests

Commands:

```text
py -c "import fastapi, httpx, uvicorn; print(fastapi.__version__, httpx.__version__, uvicorn.__version__)"
py -m unittest -v route_compatibility_tests logitrack_smoke_tests
```

Validated direct versions: FastAPI 0.141.1, HTTPX 0.28.1, Uvicorn 0.53.0.

## Remaining Risks

- There is no platform-specific, hash-checked transitive dependency lock.
- The supported Python version range is not established beyond the tested Python 3.14.7 environment.
- No software-composition vulnerability scan or package-signature verification was available in this review.
- Production-safe configuration remains a release concern; local defaults must not be treated as an internet-deployment profile.
