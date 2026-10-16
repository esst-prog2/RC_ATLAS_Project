# Review 1: Requirements and Specification Drift

## Scope

Reviewed the complete tracked specification and product-documentation surface, then compared it with registered application routes, Studio source contracts, and the automated workflow tests. Generated files, runtime stores, vendor directories, the immutable audit snapshot, and the separate Wave 1 worktree were excluded.

## Method

- Inventoried all tracked files with `git ls-files`.
- Searched canonical and active OpenSpec requirements, QA scenarios, README, development guidance, planning decisions, route declarations, Studio controls, and tests.
- Used the canonical operational workflow rather than implementation behavior as the authority for corrections.
- Reused no protected data and did not start the application.

## Findings

### R1-1: README stopped before the required final approval checkpoint

The prior README described MEAL validation and then said the task was shown as validated. The canonical workflow requires the task to remain `pending_validation` after MEAL validation and become Completed only after Programme Manager approval (`openspec/specs/operational-task-workflow/spec.md:55-78`). The focused regression already encodes this promise (`assignment_aware_task_workflow_tests.py:91-141`).

**Action:** corrected the demo narrative, first-use scope, and acceptance bullets in `README.md:13-65` to include pending approval and final Programme Manager approval. No application behavior changed.

### R1-2: README confused course assessment scope with implementation inventory

The prior heading "Not this term" listed organization administration, Logical Framework, reporting, and notifications as though they were absent, while tracked routes, Studio views, and focused tests implement portions of those surfaces. The canonical workflow explicitly says those broader surfaces remain unaffected rather than making them course-MVP acceptance criteria (`openspec/specs/operational-task-workflow/spec.md:92-100`).

**Action:** renamed the section to "Not part of the assessed course workflow" and clarified that broader surfaces may exist without expanding the homework acceptance scope. This avoids inventing requirements for those modules.

## Corrections

- Documentation-only correction in `README.md`.
- No specification, scenario, source, route, test expectation, or runtime configuration was changed.

## Tests

- Baseline before all homework edits: `py -m unittest discover -p '*_tests.py' -v` -> 261 passed.
- Focused gate for this review: assignment-aware workflow and course-MVP suites.

## Remaining Risks

- The repository contains broader product functionality that is outside the narrow course workflow. It still requires its own approved specifications and QA gates; this review does not promote it into course scope.
- Browser acceptance evidence is historical and was not rerun during this source/documentation review.
