# INDUSTRY-BUSINESS-MODEL-02

## 1. Identity and boundary

- Baseline and current HEAD: `b0c08392679b9f305c9b6e6819c86e254b9e7d61`
- Branch: `feature/industry-business-model-02-20261123`
- Formal product layer: P1 `smart_construction_core`
- Supporting layer: P4 read-only inventory, focused tests and evidence carriers
- Standard vs user-specific: construction product standard
- Current slice: 02-A project execution entry boundaries, 02-B plan/WBS/task
  connection, 02-C business-pending/task separation and code-only 02-D
  settlement/BOQ/progress semantic convergence
- Excluded: destructive retirement of the legacy settlement model, retirement
  of the legacy BOQ relation table, plan predecessor retirement, task lifecycle
  bridge T0, frontend source changes and P0 platform changes

This is an unreleased dirty-tree iteration. It is not a frozen candidate,
mainline integration, deployment or user acceptance result.

## 2. Pre-implementation gate responsibility

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| base/head and worktree identity | required and checked | repository preflight + `make agent.run.resume` | exact baseline and one-writer worktree |
| syntax/static guards | required | `py_compile`, `git diff --check`, industry and model guards | P1 service/handler changes |
| focused changed behavior | required | `verify.industry_business_model_02.orm` | 02-A/02-C behavior |
| install | required | fresh isolated `smart_construction_core` installation through `local.test` | changed Python must load and install |
| restart | required | `make local.dev.restart && make local.dev.health` | changed services must reload without startup failure |
| generated content | required | `verify.industry_business_model_02.data_audit` contract-content readback | configured execution-task block must contain the expected facts |
| affected existing ORM families | excluded by Owner decision | none | industry business execution changes do not alter the generic contract system |
| owning-module baseline | excluded by Owner decision | none | generic contract schema/producer/assembly remains unchanged |
| frontend lint/type/build | excluded | none | no frontend source changed |
| browser journey | excluded | none | backend facts are covered by ORM; no UI source changed |
| remote required gates | not run | exact-head PR checks | no frozen clean candidate or PR authorized |

## 3. Read-only data inventory

The read-only inventory ran against the registered persistent
`sc-local-dev/sc_dev_demo` profile. The shell issued a rollback. Raw output is in
`.runtime/agent-runs/INDUSTRY-BUSINESS-MODEL-02/data_audit_readback.json`.

| Fact | Observed value |
| --- | ---: |
| projects | 26 |
| project tasks | 155 |
| projects with tasks | 17 |
| projects with multiple tasks | 17 |
| tasks named as project root tasks | 0 |
| WBS nodes | 91 |
| WBS nodes with related tasks | 0 |
| tasks without WBS | 155 |
| plans | 1 |
| plan nodes | 1 (`node_type=task`) |
| plan node task relation field | absent |
| plan predecessor relation rows | 0 |
| formal `sc.settlement.order` | 33 |
| legacy `project.settlement` | 1 (`confirmed`) |
| BOQ rows with scalar `task_id` | 1 |
| BOQ/task many-to-many relation rows | 0 |
| scalar/many-to-many BOQ-task drift | 1 |
| `project.budget.contract_id` non-empty | 0 |
| `sc.project.document.contract_id` non-empty | 0 |

`project.task.state` currently has 155 rows in `01_in_progress`, while
`project.task.sc_state` has 155 rows in `draft`. `project.project.sc_execution_state`
has historical values `done=22`, `in_progress=2`, `ready=2`. These observations
confirm that native task lifecycle, SCE handling state and project compatibility
state are not interchangeable.

Required interpretation:

- Multiple open tasks per project are a real business shape; the
  `single_open_task_only` execution constraint is contradicted by data.
- The sampled data had no plan-to-task relation. The selected convergence keeps
  plan nodes in `sc.plan.line` and uses the existing WBS
  `construction.work.breakdown.task_ids` carrier for actual tasks.
- Legacy settlement still has data and cannot be deleted or retired in this
  batch.
- BOQ already had two relation carriers and one observed drift. Current writes
  now use scalar `project.boq.line.task_id`; legacy relation rows remain
  available through the computed task read while table retirement is deferred.
- `sc_execution_state` cannot be removed immediately because non-empty legacy
  values exist.

## 4. Source-confirmed defects and corrections

### 02-A project creation and execution entry

The baseline implementation made project initialization create a “项目根任务
（Project Root Task）”, attempted to write the removed/illegal
`project.task.user_id` field, and made project initialization depend on task
creation success.

Corrected behavior:

- Project creation initializes the `project.project` management object only.
- A project may have zero tasks.
- Project initialization no longer creates tasks or writes `project.task.user_id`.
- `post_create_bootstrap()` now returns the initialization summary consumed by
  the initiation handler instead of always returning `None`.
- `ProjectExecutionConsistencyGuard` no longer enforces one open task or a
  project-execution/task-state linear match.
- `sc_execution_state` is exposed as a non-authoritative compatibility value.
- Project context and dashboard milestone text consume native
  `project.milestone` records; they no longer alias `sc_execution_state`.
- The next-action summary counts native task lifecycle states.
- Project engineering progress consumes `project.progress.entry` aggregation;
  native task completion is a separate indicator.
- Canceled tasks are excluded from the task-completion denominator.
- Dashboard task waiting, completion, overdue and milestone-delay signals use
  native `project.task.state`, `project.milestone.is_reached` and
  `project.milestone.deadline`.
- `project.budget.contract_id` and `sc.project.document.contract_id` retain their
  compatibility field names but now truthfully declare the actual
  `account.analytic.account` model as an analysis dimension.
- Plan nodes now optionally reference an existing WBS work package through
  `sc.plan.line.wbs_id`; native tasks are exposed through the WBS
  `project.task.work_id` relation instead of a second plan-to-task table.
- Plan task blocks show only tasks reached through plan-node WBS links and
  retain the native task state.
- `sc.settlement.order` is the current settlement authority for project paid
  totals, settlement completeness, BOQ freeze and project-close blockers.
  `project.settlement` remains a read-only historical model.
- `project.boq.line.task_id` is the current BOQ-to-task write authority.
  `project.task.boq_line_ids` is a computed effective read that also preserves
  rows from the legacy relation table, so historical data remains visible while
  new writes have one authority.

### 02-C business pending versus construction tasks

The baseline execution-task block merged `construction.contract`,
`payment.request` and `sc.settlement.order` records into task-shaped rows.

Corrected behavior:

- The project execution-task block consumes only `project.task`.
- Its `state_field` is native `project.task.state`.
- Open, in-progress, waiting and overdue counts derive from native task facts.
- Contract, payment and settlement records remain source-preserving business
  pending items for My Work and are not emitted as `task_id/task_kind` rows.
- My Work excludes natively completed and canceled tasks from open task queries.
- Historical `sc.workflow.workitem` rows do not become active todos while the
  legacy workflow runtime is disabled.
- Duplicate My Work rows for the same `(section, model, record_id)` are
  displayed once while all sources and source-specific actions are retained in
  `sources`, `source_count` and `source_refs`.
- Summary totals remain database/source counts rather than being replaced by the
  limited item sample.

## 5. Consumer impact matrix

| Consumer | Current input | Result after this slice | Remaining boundary |
| --- | --- | --- | --- |
| project initiation handler | `ProjectCreationService` summary | receives explicit `project_tasks=optional` | project remains valid with zero tasks |
| project execution guard | native `project.task.state` counts | allows multiple open tasks; no root-task check | T0 approval/dependency bridge still pending |
| project execution task block | `project.task` only | no business-document pseudo-tasks | native waiting and closed semantics are consumed |
| project context | native `project.milestone` | no longer reports `sc_execution_state` as milestone | milestone selection policy still needs product review |
| project dashboard milestone text | native `project.milestone` | reports next/unreached or latest reached milestone | dashboard progress remains a later convergence batch |
| project progress block | engineering progress + native task facts | engineering and task completion are separate | plan-node progress remains a later relation decision |
| project metric/header/risk blocks | native task and milestone facts | no `kanban_state` task statistics | T0 lifecycle bridge remains pending |
| My Work task list | assigned task + native open states | closed/canceled tasks do not enter todo | native reopened tasks follow Odoo state |
| My Work business pending | contract/payment/settlement source projections | source model and record identity retained | duplicate count across all sources remains source-count based |
| project execution projection service | source-preserving inbox projection | no task-shaped API remains | service name is retained for compatibility |
| plan task block | plan node → WBS → native task | no second plan-task relation | plan predecessor remains planning-only |
| project paid/close facts | formal `sc.settlement.order` | legacy settlement no longer controls current facts | migration/retirement remains a data project |
| BOQ task links | scalar `project.boq.line.task_id` writes | legacy many-to-many rows remain readable | relation table retirement remains a data project |

## 6. Validation results

Identity:

- `make agent.run.resume`: branch, baseline and dirty scope resolved without an
  out-of-scope path.
- `git diff --check`: passed.
- `python3 -m py_compile`: passed for all changed Python files.

Focused ORM:

- `make verify.industry_business_model_02.orm`: passed, 14 tests.
- Readback:
  `.runtime/agent-runs/INDUSTRY-BUSINESS-MODEL-02/boundary_orm_readback.json`.
- The governed `local.test` runner installed `smart_construction_core` into a
  fresh disposable `sc_test` database before executing the non-zero test set.
- Covered zero-task project creation, bootstrap summary, multiple open tasks,
  native milestone context, business-document exclusion from the task block,
  native task-state consumption, closed-task filtering in My Work, disabled
  legacy workflow todos, multi-source aggregation, separate engineering/task
  completion, canceled-task denominator exclusion, native waiting metrics and
  truthful analytic-account field labels, plan-to-WBS task links, formal
  settlement authority and BOQ write/read convergence.
- Backend model declaration guard: passed, 5840 declarations with no duplicate
  or same-class duplicate declarations.

Restart:

- The earlier non-schema slice restart and health check passed.
- The 02-B/02-D follow-up adds a nullable plan WBS field and changes the BOQ
  task read model, so it was installed only in the disposable test template.
  The persistent development database was intentionally not upgraded in this
  local-only batch.

Generated content:

- `make verify.industry_business_model_02.data_audit`: passed against read-only
  `sc_dev_demo` with rollback.
- Contract-content readback selected project `1` / task `155` and generated
  `block.project.execution_tasks` with `block_state=ready`.
- `source_model=project.task`, `state_field=state`, item sources are exactly
  `project.task`, and displayed native states equal ORM states.
- The same project read back engineering progress `45.0%` and native task
  completion `0.0%`, proving the two facts are not aliased.
- Budget and document compatibility fields read back
  `account.analytic.account` with label `关联分析账户`.

Additional observations, excluded from this batch gate:

- An affected-family ORM run was executed before the Owner narrowed the gate; it
  passed 112 cases but is not required for this batch.
- `test_project_semantic_carriers.py`: passed 6 pure tests.
- `test_project_close_guard_internal_privilege.py` fails on unchanged HEAD
  because its AST expectations predate `_workflow_lifecycle_blockers()`; it is a
  pre-existing baseline-evidence defect unrelated to this diff.
- `make agent.run.resume` reports runtime receipts as stale after recording
  because `scripts/ops/agent_run_context.py` rejects every non-offline run
  environment at its runtime reuse check. The raw local-test receipts and Odoo
  logs are genuine and non-zero, but the P4 reuse verdict is classified as
  `validation_tool_defect`; no identity or readback was altered to hide it.

## 7. Owner decisions still required

1. Can `sc.plan.line.predecessor_ids` be retired after confirming no external
   consumers, or must historical data be migrated first?
2. Is `project.settlement` migrated into `sc.settlement.order`, retained
   read-only, or archived by a separate data project?
3. When may the legacy `project_task_boq_rel` relation table be retired after
   confirming no remaining legacy read consumers?
4. When may `project.project.sc_execution_state` become read-only compatibility,
   and which historical values must be migrated before removal?

No field deletion, data migration or repair is authorized by this record.

## 8. Current status and next exact step

Status: `local_criteria_passed_pending_commit`.

No further full-contract, module-baseline or frontend regression is required
for this slice by the Owner criterion. The remaining action is a clean local
commit. The new WBS field and BOQ computed-read change require a governed module
upgrade when a future integration/deployment is authorized; no persistent
database upgrade was performed in this local-only slice. T0 lifecycle bridging
remains a separate batch.
