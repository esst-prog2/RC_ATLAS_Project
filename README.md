# RC Atlas

RC Atlas is an operational workspace for managing project implementation.

For this course, the project focuses on a small but complete operational workflow in which work is assigned, executed, submitted for validation, reviewed, and reflected in the current project status.

## 1. The demo

I start RC Atlas locally and open it in the browser. I log in as Teresa Mbanze, the Programme Manager for the Coastal Resilience and Livelihoods Programme, and create a task called **“Finalize Buzi monitoring report”**, assign it to Aline Duarte, and set its deadline. I log in as Aline, the Field Coordinator; the task appears in her work queue, where I update its progress and submit it for validation. I then log in as Raimundo Cumba, the MEAL Officer, open the submitted task, review it, and validate it. When I return as Teresa, the task is shown as validated and the project view reflects the updated operational status.

## 2. The shape

    in          a configured project, project users, and operational tasks

    out         a project workplan showing who is responsible for each task,
                its progress, deadline, and validation state

    on screen   the manager creates and assigns work; the assigned user updates
                progress and submits it; the MEAL officer reviews and validates it;
                each user sees the project according to the responsibilities of
                their role

## 3. The size

**First useful version**

- local browser application with login for three project roles: Programme Manager, Field Coordinator, and MEAL Officer
- one configured development project
- Programme Manager can create a task, assign it to a project user, and set a deadline
- Field Coordinator can see assigned tasks, update progress, and submit a task for validation
- MEAL Officer can see submitted tasks and validate or return them
- task state persists between logins
- each role sees only the actions available to that role
- the project workplan reflects the current state of its tasks
- a basic activity history records the main task transitions

**Not this term**

- multi-organization onboarding and subscription management
- organization administration UI
- fully configurable roles and permission bundles
- complete logical-framework and indicator builder
- budgeting and financial management
- donor-report generation
- AI-generated narratives
- email, WhatsApp, or external notification integrations
- Kobo, ODK, or other data-collection integrations
- GIS and interactive mapping
- mobile application
- predictive analytics or machine learning
- cloud production deployment

These features belong to the wider RC Atlas idea, but the course project is deliberately limited to the operational task-to-validation workflow described above.

## 4. How we would know it works

- Given a Programme Manager who assigns **“Finalize Buzi monitoring report”** to Aline, the task appears after Aline logs in with the correct owner, deadline, and status; it does not appear as her assigned task before it is assigned to her.
- Given Aline submits the task for validation, she can no longer validate or complete the task herself, and the task appears in the MEAL Officer's validation queue.
- Given the MEAL Officer validates the task, its state changes to validated and remains so after logout and login; a user without validation responsibility cannot perform the same transition.

## 5. What could stop this

- The main technical risk is keeping task state consistent across separate authenticated users. A task changed by one role must appear in the correct state when another user logs in, without relying only on browser state.
- The workflow requires explicit transition rules. If users can move tasks directly between arbitrary states, the role-based workflow demonstrated above would not be meaningful.
- Scope is the largest project risk. RC Atlas is a broader product idea, but implementing its complete administration, reporting, MEAL, financial, and portfolio functionality would not fit the course project. Those features are deliberately excluded from the first useful version.
- No confidential project data is required. The course version uses fictional organizations, projects, users, and tasks, so the repository and classroom demonstration can remain public.
- The final demonstration must run locally from a documented setup and must not depend on a cloud deployment, paid API, or external organizational system.

## Development

Local setup, startup, testing, and runtime-file guidance is available in
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).
