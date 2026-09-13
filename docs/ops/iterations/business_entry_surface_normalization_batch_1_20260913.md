# Batch-1 项目资料办理面交付记录

[English](business_entry_surface_normalization_batch_1_20260913.en.md)

## 1. 本轮变更

- 目标：关闭项目资料办理面的正式入口、真实保存和网络失败恢复链。
- P1：项目资料字段、日期范围、说明、责任明细及资料保存/生命周期动作边界。
- P0：共享保存错误把浏览器原始 `Failed to fetch` 本地化为可操作的网络错误提示，不含项目模型特例。
- P4：受管 `local.dev` 专用数据生命周期、正式菜单旅程、单次写请求阻断、失败/重试分段报告、实际控件快照和主记录/责任明细权威回读。
- 未完成：浏览器无权角色拒绝反例因既有凭据不可用保留为未覆盖；Batch-2 未启动。

## 2. 影响范围

- 模块：`smart_construction_core`、共享 contract-form 前端、`scripts/verify`、`make/dev.mk`。
- 启动链：仅修复项目经理既有授权菜单的运行时投影，不改变认证或公司上下文。
- contract/schema：不新增 schema，不绕过契约；沿用 `ui.contract.v2` 与 `api.data op=write`。
- 路由：正式菜单使用 `menu 681/action 861`；不把手拼路径作为授权入口。
- 数据：仅操作 `sc-local-dev/sc_dev_demo` 中受管专用批次，未使用项目 2/8 写入。

## 3. 风险与边界

- P0：网络错误文案为共享前端行为；定向测试约束其不泄露原始浏览器错误。
- P1：资料保存不推进生命周期；本次回读保持 `draft`。
- P4：runner 的正常保存和失败恢复期望已分离；恢复 PASS 要求失败前后实际控件值及明细操作一致、主记录及责任明细内容未变、错误元素真实可见；两次浏览器尝试中仅一次到达后端并成功。
- 未覆盖：无权角色浏览器反例。既有后端权限证据继续复用，但不替代该浏览器缺口。

## 4. 验证

- `python3 -m unittest scripts.verify.test_local_dev_project_profile_write_fixture`：PASS，13 项。
- `create_record_user_journey_test.ts` 经仓库现有 esbuild 入口执行：PASS。
- 受管失败恢复：PASS。首次请求被阻断；错误摘要元素真实可见并单独截图；失败前后名称、双日期、说明和责任明细控件快照一致，明细保持新增/修改/删除三类操作；主记录全部涉及字段及责任明细角色、人员、备注均与初始化事实一致。同会话重试业务成功，权威回读与刷新全量一致。
- 预收口 `make ci.local.quick`：在生成报告门禁前的守卫均通过，随后因新增测试导致 test inventory 陈旧而按预期失败；已使用 `make refresh.generated_reports` 对齐。最终 exact-head Quick 由冻结候选的受管 receipt 和独立评审包记录，不在本文预声明结果。

## 5. 产物

- 浏览器摘要：`/tmp/p4-recovery-evidence-0913/summary.json`。
- 可见错误元素截图：`/tmp/p4-recovery-evidence-0913/failure-feedback-visible.png`。
- 失败态整页截图：`/tmp/p4-recovery-evidence-0913/failure-before-retry.png`。
- 成功刷新截图：`/tmp/p4-recovery-evidence-0913/recovery-after-refresh.png`。
- 摘要 SHA-256：`e27df862a76c680f5be2b1016b6ba0ed2888fb4889520bd1760556cd4e91a0ce`。

## 6. 数据处置与回滚

- 批次：`recovery-evidence-0913`；项目 374。
- 清理：PASS，项目与责任明细 `[24,25]` 已由受管入口删除，`clean=true`；后续 inspect 确认批次不存在。
- 回滚：按提交边界反向回退 P4 runner、P0 错误本地化和 P1 入口/页面提交；无需业务数据库回滚。

## 7. 下一步

- Batch-1 已归档。PR #465 最终 HEAD 为
  `73842d9248867599a54f9ce4647381b2ab59ea28`，其后于初始交付候选增加三项审查修正：
  共享字段/P4 runner 缺口关闭、组件接管清单刷新、登录角色与业务角色判定分离。
- 最终 PR HEAD 的 `frontend_release_gate`、`merge_policy_gate`、
  `professional_quality_gate`、`public_guard` 与 `release_candidate_gate` 均为
  `SUCCESS`。GitHub 没有人工 review 记录；独立代码复核与 CI 证据不得表述为
  GitHub 人工批准。
- squash 合并提交为
  `dbf1e171281bd920c39099be7085718c892b10f4`；最终 PR HEAD 与合并提交的 tree
  均为 `2f52649c86587c94e9dfbc1e318538eca41741e2`，产品内容一致。
- Batch-2 另行实施；不再重跑 Batch-1 浏览器保存链。
