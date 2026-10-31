# P4 · Project Workspace DOM Audit — 验收记录

独立工程分支：`feature/p4-project-workspace-dom-audit`。目标模型：`project.project`。

## 能力

- 脚本：`scripts/verify/frontend_project_workspace_dom_audit.mjs`。
- 受管入口：`make verify.frontend.project_workspace_dom.browser`，走 operation entry，
  支持 local/candidate，复用 candidate 身份守卫与 preview identity。
- 目标：`project.project`（menu 382 / action 590 / fe_project_a），由受管
  `acceptance.runtime.contract_receipt` 解析。
- 采集：项目身份字段、`lifecycle_state` / `sc_approval_state` / `last_update_status`、
  关注者/附件/时间线/帮助触发器/空行动区、四视口几何与截图、控制台错误、5xx。

## 工具边界测试

| 场景 | 结果 |
| --- | --- |
| project 目标解析 | PASS（受管 resolver 已含 project） |
| 未知模型 | 脚本失败关闭（非 project.project 拒绝） |
| 工具矩阵与 env 解析 | `verify.frontend.acceptance.environment.guard` PASS |
| lane 登记 | `audit.verification.lane_coverage.check` PASS |
| PC-02 合同 Presentation 语义 | 未改动 |
| PC-01 旧页头断言 | 未改动 |

## 验证

- `node --check` 与 `bash -n`：PASS。
- `verify.frontend.acceptance.environment.guard`：PASS（59 tests）。
- Local Quick：`426e1557f` PASS。

## 待运行时采集

需在 candidate/local 受管环境重建后，用该入口采集真实项目工作空间四视口证据，
用于 B2 渲染分支定位与 C 轨协作区整改设计。未部署、未合并。
