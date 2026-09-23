# Logical Framework Foundation

Phase 5A.2a adds a canonical result hierarchy without changing the existing
Portfolio, Workplan, task workflow, reporting calculations, or frontend.

## Canonical State

The application snapshot is the source of truth for `ResultNode` and
`IndicatorResultLink` records. The relational warehouse is a rebuildable
projection of that snapshot.

The supported hierarchy is:

```text
Project -> Goal -> Outcome -> Output
```

An existing indicator may be linked to one Outcome or one Output, or remain
unassigned. `Indicator.level` remains legacy descriptive metadata; it is not a
canonical parent relationship and must not be used to infer one.

## Compatibility

Old snapshots omit `logical_framework_results` and `indicator_result_links`.
They hydrate as empty collections. Existing embedded indicators receive their
organization and project ownership from the containing project when those
fields are absent. IDs, observations, activity links, and task links are not
rewritten.

## Persistence Boundary

Logical Framework HTTP writes now pass through a capability-specific
application coordinator, unit of work, and organization/project-scoped
repository. The domain service depends on that repository contract rather than
on `LogiTrackData`, JSON, SQLite, or relational projection details.

The current adapter is transitional. It loads a private request-local snapshot
and commits the Logical Framework mutation plus its success audit event in one
canonical snapshot save. JSON snapshots, SQLite `app_state` snapshots, and old
snapshots without Logical Framework collections remain supported. No
PostgreSQL adapter or data migration is part of this boundary.

Relational synchronization remains a derived, rebuildable projection and runs
after the canonical snapshot commit. A projection failure therefore does not
roll back or invalidate already committed canonical data. The existing strict
mode reports that post-commit synchronization failure to the caller; non-strict
mode records synchronization diagnostics. In either case, the projection can
be reconciled later from canonical state. This is not a cross-store ACID
guarantee.

The snapshot adapter also retains the existing multi-process read-modify-write
limitation: concurrent writers can overwrite one another. The repository
contract does not require last-write-wins behavior and reserves room for a
future adapter to provide optimistic version checks or database locking, but
this change does not add global concurrency control.

## Current Integration

Authenticated, organization/project-scoped HTTP routes expose the Logical
Framework hierarchy and indicator links. Successful mutations create audit
events in the same canonical snapshot commit. Project cloning remaps result
IDs and parent relationships within the existing outer project save, and the
Studio includes the project-scoped Logical Framework builder.

Archived projects remain readable but reject Logical Framework mutations. The
demo seed intentionally leaves the canonical hierarchy empty until users
configure it; it does not fabricate result relationships for existing
indicators.

Composite Outcome or Output result metrics remain deferred to the later
metrics architecture. The current Logical Framework stores structure and
indicator relationships without inventing cross-indicator aggregation.
