# 07 · SCE Native Capability Mapping

| 能力 | 初步分类 | 依据 | SCE 当前状态 |
| --- | --- | --- | --- |
| 项目负责人/项目经理 | A/B | `user_id` / SCE `manager_id` | 身份字段存在，DOM 仍有重复 |
| 任务与阶段 | A/B | `project.task` / `stage_id` | 已有任务入口 |
| 项目更新 | A/D | `project.update` / 原生按钮 | SUSPENDED，表单 DOM 未消费 |
| 里程碑 | A/B | `project.milestone` | 可复用，尚未系统接入 |
| 关注者与 Chatter | A/B | mail thread | 通用 mail 渲染链消费 |
| 工程进度计划 | C | WBS/施工结构 | SCE 专业扩展 |
| 合同履约 | C | construction.contract | SCE 专业扩展 |
| 项目成本控制 | B/C | analytic/budget | SCE 扩展 |
| 经营分析 | C | 驾驶舱/报表 | SCE 扩展 |

分类需随源码与业务依赖进一步固化。

