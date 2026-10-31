# 03 · Task and Milestone

## Task

Odoo 17 `project.task` 已提供：

- 项目归属。
- 阶段与状态。
- 父子任务。
- 多人受托。
- 任务依赖。
- 截止日期与优先级。
- 个人阶段。

SCE 应优先通过契约消费这些能力，而不是在项目表单里重建任务管理。

## Milestone

`project.milestone` 已提供：

- 名称、截止日期。
- 达成状态与达成日期。
- 关联任务。
- 逾期判断。

SCE 的项目经营进度可以消费 `milestone_ids` / `allow_milestones`。

## SCE current state

SCE 已扩展 WBS、施工结构、工程量清单、进度计量等建筑专业对象。这些属于 C 类
行业专业扩展，不应挤占 `project.task` / `project.milestone` 的原生职责。

