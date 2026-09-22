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

## Deferred Behavior

HTTP routes, user-facing audit events, project-clone wiring, and demo hierarchy
content belong to Phase 5A.2b. The frontend builder belongs to Phase 5A.2c.
Result metrics belong to the later metrics phase.

Archived projects should eventually be read-only for logframe mutations. That
policy must be enforced with the authenticated project lifecycle contract in
Phase 5A.2b; this foundation does not alter existing lifecycle behavior.
