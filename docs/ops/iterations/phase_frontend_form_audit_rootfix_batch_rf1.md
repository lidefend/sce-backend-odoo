# 表单验收运行时可编辑性根因修复 — Batch-RF1

## 1. 本轮变更

- 目标：修复日常开发库中 `wutao` 被表单验收工具误判为没有编辑、保存能力的问题。
- 完成：
  - 从当前 `system.init` 导航发现 action/menu，不固定数据库 ID。
  - 从 `ui.contract.v2` action 契约取得模型、domain、context 和排序信息。
  - 对候选记录请求真实 form 契约，仅以 `statusContract.globalStatus.pageAuth=edit` 判定可编辑，并保留 trace 证据。
  - 保存动作支持运行时文案“保存”“保存修改”“保存草稿”。
  - 页面就绪条件由全局 `networkidle` 改为表单模式、画布和目标状态的显式语义条件。
  - 新增负向夹具，证明默认列表前排全部锁定时仍可发现其他排序中的可编辑记录。
- 未完成：完整表单审计发现的 11 个产品视觉/状态断言失败不在本 P4 工具根因批次内关闭，必须进入后续 P0 前端批次；本轮不构成整体视觉候选。

## 2. 影响范围

- Formal Product Layer：P4 运维交付工具。
- Layer Target：`scripts/verify` 运行时表单验收。
- Module：表单审计、可编辑记录发现器、负向夹具和 acceptance environment guard。
- Standard vs User-Specific：通用验收机制；不固化 `sc_demo` 的模型、记录、action、menu、状态或用户偏好。
- Why Here：误判发生在验收工具的采样与定位策略，产品契约已经正确表达工作流锁定和草稿可编辑性。
- Why Not Elsewhere：不应修改 P0/P1/P2 产品权限、工作流、接口或业务数据来迎合错误审计。
- Blast Radius：只读 intent 请求、浏览器验收路由发现和本地验收产物。
- 启动链、contract/schema、default_route、public intent：均不变。

## 3. 根因证据

- `wutao` 运行时角色面包含 `business_config_admin`，一般合同列表契约为 `pageAuth=edit`。
- 日常库一般合同默认排序前排为历史已确认记录，其 form 契约按工作流正确返回 `pageAuth=read`。
- 草稿记录由运行时发现器命中，form 契约返回 `pageAuth=edit`；真实页面显示 30 个可编辑控件和“保存修改”。
- 未点击保存；未修改 `sc_demo` 数据、权限或状态。

## 4. 验证

- `make verify.frontend.acceptance.environment.guard`：PASS。
- `node scripts/verify/frontend_form_editability_discovery_test.mjs`：PASS，包含锁定前排负向夹具。
- 日常开发库真实浏览器只读复验：PASS；动态发现 `sc.general.contract` 可编辑记录，30 个可编辑控件，“保存修改”可见，控制台错误 0。
- `pnpm -C frontend gate`（由 restricted 门禁执行）：PASS，包含 lint、严格类型检查和生产构建。
- `make verify.restricted`：FAIL；隔离验收环境 secondary 公司快照失败，成功 profile 为 1/2。未通过写数据库、建公司或建用户规避。
- 完整日常表单审计：运行完成，121 项中 110 PASS、11 FAIL；运行时错误 0。失败项为现有可见文字裁切、sticky 锚点和 loading 状态，保留在验收 JSON/HTML。
- `git diff --check`：PASS。

## 5. 产物

- `.runtime/final-acceptance/wutao-edit-save-root-fix.png`
- `.runtime/final-acceptance/form-audit.json`
- `.runtime/final-acceptance/form-audit.html`
- `artifacts/backend/scene_company_snapshot_collect_report.json`

## 6. 风险与回滚

- P0：整体表单视觉审计仍有 10 个 P0 失败，本轮不得宣称专业成品候选。
- P1：loading 显式状态断言仍失败 1 项。
- P2：候选记录发现按三个运行时排序各采样 40 条；找不到时 fail closed 并保留检查证据，不退回硬编码记录。
- 回滚：回退本批次提交即可；无需数据库、模块升级或数据恢复。

## 7. 下一批次

- 唯一目标：在 P0 通用前端渲染层关闭本次真实浏览器报告中的文字裁切、sticky 锚点和 loading 状态缺陷，再重新执行五视口表单审计。
- 状态：当前仅完成验收工具根因修复，等待后续产品修复和监督者最终视觉裁决。
