# Reveal.js speaking script

Five substantive slides: 45 + 120 + 60 + 45 + 30 = 300 seconds. Closing link slide is additional. Rehearse to the time budget; notes are publicly visible through N.

## 1. For whom, and why — 45 seconds

By the end, you will see how one assigned activity becomes an approved, traceable result. RC Atlas is for programme managers, field teams and monitoring staff in development and humanitarian organisations. It addresses scattered plans, unclear ownership and disconnected progress reporting. The platform brings portfolio oversight, tasks, indicators, risks, report previews and contextual narratives into one role-based workspace. These capabilities have different maturity levels: indicator analysis needs suitable methods and data, while report export and delivery remain unavailable. This current overview uses synthetic data. I will now demonstrate one complete operational workflow.

## 2. The demo — 120 seconds

Our example is Review Buzi field report in the Coastal Resilience and Livelihoods Programme. All participants and data are synthetic. First, Teresa Mbanze, the Programme Manager, assigns the task to Aline Duarte, the Field Coordinator. The deadline is 1 December 2026. She selects Validation plus Approval, requires evidence, and names Raimundo Cumba as validator and herself as final approver. This image shows the completed form before Create Task.

Second, Aline accesses the assigned task and starts execution. The task moves from Not Started to In Progress. The screenshot records 25 percent progress, with the same title, owner and deadline.

Third, Aline prepares her submission. She enters 100 percent progress, the evidence note Synthetic Buzi field report reviewed, and the comment Ready for independent validation. This is the form immediately before Submit for Validation; its header still shows the earlier state. The evidence is a text note, not an uploaded real report.

Fourth, the MEAL Officer sees Pending Validation, one evidence entry and three comments. Raimundo reviews the work and can Validate or Request Rework. Validation advances the review stage to approval, rather than closing the task.

Fifth, Teresa grants final approval. The task now shows Completed, stage Complete and Approved, with the designated participants retained.

Finally, the same task appears under the Completed filter in the Workplan. Ownership, deadline, progress and evidence remain visible. This demonstrates accountable task delivery, not proof of programme outcomes.

## 3. Why it works — 60 seconds

A working demonstration is not enough. A concrete acceptance criterion is that only the designated reviewer may advance the task, even if another user has the same capability. This existing repository test deliberately gives Teresa validation capability and Raimundo approval capability. Teresa still receives 403 when she tries to validate a task assigned to Raimundo for validation. Raimundo receives 200 for the designated validation, but 403 when he tries to approve a task assigned to Teresa for approval. The focused check passed with no skips in the guarded synthetic runtime. The agent executed it; I am not claiming I personally ran it. Its assertions and result make the implementation reviewable. It proves this routing restriction, not every permission, tenant boundary or analytical calculation.

## 4. What I learned — 45 seconds

During UI-01 review, Portfolio Health displayed zero percent while Reports retained NOT_ASSESSED. The repository records the explanation: absent portfolio health reaches a JavaScript fallback that replaces it with zero. That turns unknown information into an apparent measurement of poor performance. The technical checks can pass while that meaning is wrong. The issue remains unresolved in the accepted checkpoint; visual acceptance was not certification of analytical correctness. My lesson is that passing technical tests does not necessarily guarantee analytical correctness. Missing information must not be interpreted as zero.

## 5. What's next — 30 seconds

The next priorities are future work. First, extend the established visual conventions across roles while preserving their different permissions. Second, protect analytical meaning by separating missing values from measured zero and improving reliable reporting. Third, prepare an institutional pilot in Mozambique, with agreed user needs, data governance and acceptance criteria. A pilot has not yet taken place. These steps move RC Atlas towards accountable operational use.

## 6. Thank you — 0 seconds

Thank you. The project website is available at the link shown here.