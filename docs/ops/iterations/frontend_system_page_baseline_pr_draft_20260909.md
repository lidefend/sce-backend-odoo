# PR 草稿：统一共享前端体验并冻结官方组件接入

## Summary

统一系统外壳、首页、我的工作、集合/详情、关系表单和层级工作区的页面表达；把 Input、Select、Card、Alert、Button 等共享组件收敛到官方公开 props、事件和插槽，并补齐真实组件参数、单次重试、明暗主题及 1440/1088/390/320 的最终证据。

本草稿描述完整分支范围，而不是只描述最后一次视觉调整。分支同时包含独立 P4 acceptance 环境恢复工具，已在下文单列，不将其称为前端产品改进。

## User-visible improvements

- 首页入口恢复完整宽度，待办、状态、常用入口和最近访问形成稳定层级。
- “我的工作”减少重复包框，搜索、排序、工作事实和主要操作在桌面/窄屏保持可访问。
- 付款列表/详情统一页头、工作表面、金额与返回上下文，移动端保留关键事实和操作。
- 收入合同层级工作区补齐范围选择、横向浏览、详情和滚动恢复。
- 表单错误、关系搜索、空态、loading、Alert 恢复和浮层焦点使用共享组件一致表达。
- 明暗/系统主题消费同一套语义 token，没有新增平行样式体系。

## Architecture Impact

- P0：通用前端 primitives、shell、page header、list/form/hierarchical renderers 和主题桥；少量通用后端页面装配/失败文案。
- P3：配置工作台已有状态的前端表达，不改变配置事实、发布和回滚语义。
- P4：静态/浏览器验证、生成 inventory、候选证据、交付文档，以及独立列明的 acceptance 完整恢复入口。
- 启动链 `login → system.init → ui.contract`、contract/schema、public intent、default route、权限裁决和业务状态写入均未改变。

## Layer Target

`frontend shared runtime + generic page renderers + business-config presentation + P4 verification/delivery tooling`

## Affected Modules

- `frontend/apps/web`
- `frontend/packages/design-tokens`
- `frontend/packages/ui`
- `addons/smart_core`（仅通用页面装配、失败文案及测试）
- `scripts/verify`、`scripts/audit`、`scripts/dev`
- `make/frontend.mk`、`make/runtime_ops.mk`、`make/dev.mk`
- `docs/frontend_productization`、`docs/ops`

## Scope identity

- Base：`main`；整理时 base SHA `74297675ea86af98af0d222efa4fe692c28e1ffe`。
- 前端阶段产品基线：`3d3975b3d45c1462677df0abcbb5708e4b53e0b1`。
- 冻结产品候选：`df3227c38e908b883ed45553e9511b03b59a3348`。
- 最终审查证据 HEAD：`8cd5cdebcd0b1127e1d7ddcada672077f25afa7f`。
- PR exact head：创建前以本地 clean HEAD 重新冻结，禁止沿用本草稿中的历史 SHA 推断。

## P4 acceptance tooling carried by the branch

以下内容不是用户可见前端产品范围：

- `scripts/dev/frontend_acceptance_baseline_rebuild.sh`
- `scripts/dev/frontend_acceptance_runtime.sh`
- `scripts/verify/test_frontend_acceptance_baseline_rebuild.py`
- `make/dev.mk`
- `docs/ops/environment_tiers_unified_runbook_v1.md`
- `docs/ops/iterations/frontend_acceptance_fixture_namespace_rebuild_design_20260909.md`

这些文件只提供 fail-closed audit/dry-run、整卷恢复和失败注入测试。没有执行 destructive rebuild、fixture reset 或 release gate。历史 P1 `.163/.164` 迁移及 funding fixture 修改已经从当前净候选撤出。

## Verification

- `make verify.frontend.quick.gate`：产品候选 PASS。
- 官方组件 inventory：内部 vendor selector、视觉字面量、未知项目 token、孤立 appearance variant 均为 0。
- `python3 -m unittest scripts.verify.test_local_dev_candidate_frontend`：9 tests PASS。
- `make verify.frontend.overlay_lifecycle.unit`：10 tests PASS。
- `make verify.frontend.primitive_adapter.unit`：27 Python tests + 46 JS component scenarios PASS。
- `make verify.frontend.overlay_lifecycle.browser`：10 browser scenarios PASS；真实 `ScButton` props 证明 disabled/loading 和恢复。
- Alert 正式页面四个桌面/移动组合均为 `operationCount=1`、`retryRequestCount=1`。
- 首页、我的工作、付款列表/详情、收入合同工作区在 light 1440/390、dark 1088/320 共 20 个最终样本 PASS；mutation 0，errors/failures 0。

详细索引：`docs/ops/iterations/frontend_stage_delivery_package_20260910.md`。

## Historical failures kept as history

- 首次系统页面独立审查的 `REQUEST_CHANGES` 已由后续候选修正；旧报告不作为最终通过证据。
- `016a8443…` 的历史 release gate 仍记为 FAIL，归因 P4 validation-tool defect；没有改写或用视觉 smoke 替代。
- 当前 acceptance authority 尚未重建，因此当前版本的 release/production qualification 为 `not_run`。该恢复任务只建立当前源码候选的可信验收载体，不证明任何旧版本升级兼容。

## PR/CI state

- 本地 `make pr.status`：当前分支没有关联 PR。
- 完整范围分类：`HIGH_RISK`，`frontend_mode=full`、`professional_mode=full`、`backend_changed=true`。
- PR 创建后必须在 exact head 通过 `public_guard`、`professional_quality_gate`、`frontend_release_gate`、`merge_policy_gate`。
- `release_candidate_gate` 属于后续发布资格，不是本 PR 草稿的已完成项。

## Not included

- 不新增或补写业务契约、角色权限和业务规则。
- 不覆盖多角色、真实保存/审批/配置发布、旧版本升级兼容和生产发布。旧版本兼容需另行指定源版本数据库、filestore、模块版本与预期迁移结果，不能由当前版本 acceptance 重建替代。
- 不执行 acceptance 重建、数据库/fixture/module lifecycle、push、merge 或 release。

## Risk and rollback

- 完整 PR 范围大且包含 backend/Make/P4 environment paths，必须按 HIGH_RISK 分层审查。
- 产品阶段可整体回到 `3d3975b3`；官方组件、最终表达、证明修正分别以 `f9797273`、`df3227c3`、`c755e551` 为审查/回退节点。
- acceptance 恢复工具以 `aba26adc`、`c6f5658e` 为独立 P4 回退节点，不与前端产品混回退。

## Delivery status

`READY_FOR_PR_AUTHORIZATION`：等待明确授权后，通过受管入口 push 并创建 draft PR。当前不是 `merge-ready` 或 `release-ready`。
