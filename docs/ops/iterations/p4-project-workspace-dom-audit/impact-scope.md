# P4 · Project Workspace DOM Audit — 影响范围审计

独立工程分支：`feature/p4-project-workspace-dom-audit`。本报告只做能力复用与新增范围
审计，不修改 PC-01/PC-02 产品代码。

## 1. 可复用能力

| 能力 | 现状 | 复用方式 |
| --- | --- | --- |
| candidate 身份守卫 | `frontend_acceptance_runtime.sh` 的 `candidate_identity_guard` /
  `candidate_db_uuid_guard` | 直接复用，不新增身份机制 |
| Playwright 启动与截图 | `scripts/verify/playwright_runtime.mjs` | 直接复用 |
| DOM 几何与四视口 | `frontend_contract_form_presentation_browser.mjs` 的
  `scrollWidth/clientWidth/横向溢出` 采集模式 | 复用采集模式，不复制框架 |
| 项目目标身份解析 | `frontend_delivery_hardening_runtime_ids.py` 已含 `project` 目标
  （project.project / menu 382 / action 590 / 记录 fe_project_a） | 直接复用，受管
  `acceptance.runtime.contract_receipt` 已生成 `project` 目标 |
| preview 身份校验 | `frontend_standard_preview.py identity` | 直接复用 |

## 2. 必须新增的能力

1. `project.project` 原生工作空间 DOM 审计脚本：
   - 模型白名单与身份断言（`project_code`、`name`、`owner_id`、`manager_id`、
     `user_id`、`cost_manager_id`、`doc_manager_id`；状态 `lifecycle_state`、
     `sc_approval_state`、`last_update_status`）。
   - 协作区几何采集：关注者人数/折叠、附件容器宽度、协作时间线结构、
     `data-field-help-trigger` 来源、行动区是否空置。
2. 受管 Make 目标 `verify.frontend.project_workspace_dom.browser`，走 operation entry，
   支持 candidate profile；同时完成验证 lane 登记（dispositions + baseline）。

## 3. 不得复用的部分

- 不得复用 PC-01 旧项目页头断言（`frontend_product_page_header_browser.mjs`）的语义。
- 不得把 `sc.general.contract` 的合同身份断言套到 `project.project`。
- 未知模型失败关闭，不允许自动套用其他模型标准。

## 4. 工具边界测试

- project 目标正确解析；未知模型拒绝；合同 presentation 既有语义不变。
- local/candidate 身份守卫保持有效；四视口采集覆盖
  `1440/1024/768/390`，采集截图、DOM 节点、几何、横向溢出、控制台错误。

## 5. 分工

- P4 工具：本分支，只建设 DOM 审计入口与测试。
- B 轨产品修复：`feature/pc01-r2-identity-status`，B1 已提交，B2 待 DOM 根因定位后
  最小修复。
- C 轨产品整改：待四视口证据后单独设计。
