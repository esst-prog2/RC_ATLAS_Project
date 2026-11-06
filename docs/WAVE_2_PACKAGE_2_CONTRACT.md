# Package 2 consumer contract (2026-10-25)

Authority: OC-A01–A05, QA-003, the verified Package 1 core and the current user
instruction. No organization configuration is approved by this implementation.

Read adapters call `services.methodology.calculate` unchanged. All selected
consumers require the same explicit project/indicator, method/version, start/end,
as_of and locale. No default date, inferred method or legacy observation binding.
Unsupported filters are rejected by selected HTTP consumers. The registered
TidyDataset is the population; location and reporting-history records cannot
silently replace it. Legacy numeric source fields remain available as source facts.

The indicator KPI endpoint, project dashboard indicator rows, dataset quality,
dataset narrative, canonical explanation and Studio indicator table carry the
same complete calculation envelope. Context-free calls retain collection shapes
and keys, with null unsupported values and explicit states. Existing fields named
mean/weighted progress are not relabelled as a different estimand. Selected
calculated_value is a display string; exact arithmetic lives in the calculation.
Whole-response legacy warning headers remain on mixed analytical endpoints. The
selected envelope identifies its own contract; adding an as_of query parameter
cannot certify a deferred consumer or its surrounding operational values.

Cross-indicator/district/portfolio progress, legacy-history derived progress,
statistical trend, quality composite and indicator-derived delivery-health scores
are unavailable pending their approved contracts. Operational task counts and
workflows remain operational data. No new risk or portfolio engine is introduced.
The broader operational confidence/risk system remains deferred and unvalidated;
this package does not claim RCQA-011 closure for operational clocks or reports.

Independent expected values, frozen before adapter implementation:

| Input | Expected |
| --- | --- |
| B20, T100, A60 | exact 50, display 50.00, numerator40/denominator80 |
| Same A60, planned60 | exact100, schedule_attainment separately named |
| TARGET_RATIO A0/T100 | VALID0; missing A -> MISSING/null |
| A150/T100 | 150%, uncapped |
| T0, B=T | INVALID/null, ZERO_DENOMINATOR |
| Down B100/T20/A60 | 50% |
| Mean 0,5,MISSING,INVALID,N/A | actual5/2, applicable4, included2, total5 |
| PROVISIONAL only | INVALID/null with explicit excluded flag |
| MILESTONE | NOT_ASSESSED/null |
| Inclusive September endpoints, August31/October1 | two included, two period-excluded |
| Required actual+period on A60/September30 | completeness2/2=100%; other unconfigured dimensions NOT_ASSESSED |
| Unconfigured quality and any dataset size | five NOT_ASSESSED dimensions; no overall score |
| Same exact method/source/context | identical entire result, identity, quality and explanation in each consumer |
| Changed method version/source revision/as_of | distinct calculation identity; preserved historical instance |

Read boundaries require VIEW_INDICATORS and VIEW_REPORTS for selected calculation
envelopes. Existing tenant/project/source authorization, session, CSRF, version and
PostgreSQL transaction semantics remain in force. No schema change, dual write,
history repair or real-data migration. Recovery is source-only into an empty path.
