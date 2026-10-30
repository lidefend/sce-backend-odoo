# PAGE-CONVERGENCE-01A · B3 阶段要求只读查看

## 改动

- `project_core.py::action_view_stage_requirements` 不再创建临时向导
  `sc.project.stage.requirement.wizard`，改为返回只读 `ir.actions.act_window` 打开
  `sc.project.stage.requirement.item` 树视图，domain 按当前 `lifecycle_state` 过滤，
  context 禁用 create/edit/delete。
- 保留后端 record rule / ACL 对 item 模型的真实读权限校验。

## 待运行时验证

- pm1 真实点击「查看阶段要求」可查看内容并返回详情。
- 无权限账号得到明确错误语义，不伪装成功。
- 不产生 `sc.project.stage.requirement.wizard` 记录，不产生业务数据写入。

