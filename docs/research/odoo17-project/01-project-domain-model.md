# 01 · Project Domain Model

## project.project

Odoo 原生 `project.project` 是项目组织载体，SCE 在其上扩展了大量建筑业务字段。

核心原生关系：

- `user_id`：项目管理员 / 负责人（SCE 页面中译作“项目管理员/项目负责人”）。
- `manager_id`：项目经理（SCE 扩展）。
- `partner_id`：客户。
- `company_id`：公司。
- `stage_id`：项目阶段。
- `privacy_visibility`：可见性。
- `analytic_account_id`：分析账户。
- `task_ids` / `update_ids` / `milestone_ids`：任务、项目更新、里程碑。

SCE 扩展字段示例：

- `lifecycle_state` / `sc_approval_state` / `sc_execution_state`。
- `project_code`、`business_nature`、`operation_strategy`。
- `cost_manager_id`、`doc_manager_id`。
- `budget_ids`、`wbs_ids`、`contract_ids`、`payment_request_ids`。

当前 candidate 中 `project.project` 共 235 个字段。

## project.task

`project.task` 是执行管理对象：

- `project_id`：所属项目。
- `stage_id` / `state`：阶段与状态。
- `parent_id` / `child_ids`：父子任务。
- `user_ids`：受托人。
- `depend_on_ids` / `dependent_ids`：任务依赖。
- `priority`、`date_deadline`、`allocated_hours`。

## project.update

`project.update` 是项目状态快照/更新记录：

- `project_id`：项目。
- `user_id`：编写者。
- `status`：状态。
- `progress` / `progress_percentage`。
- `date`。

它不是 `TransientModel`，是持久化业务记录。

## project.milestone

`project.milestone` 是里程碑：

- `project_id`：项目。
- `name`：名称。
- `deadline`：截止日期。
- `is_reached` / `reached_date`：是否达成、达成日期。
- `task_ids`：关联任务。

