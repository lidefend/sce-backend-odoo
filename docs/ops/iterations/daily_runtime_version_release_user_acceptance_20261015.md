# Daily Runtime — 版本发布与用户视角验收（2026-10-15）

Goal: `DAILY-RUNTIME-VERSION-RELEASE-AND-USER-ACCEPTANCE-20261015`
Run: `.agent/runs/DAILY-RUNTIME-VERSION-RELEASE-AND-USER-ACCEPTANCE-20261015/run.json`
Branch: `release/daily-runtime-version-release-20261015`
Baseline: `ba7577c212b81468491942e972ea28bd64345ebd`（PR #664 合并后的 `main == origin/main`）

## Objective

1. 把目标 daily runtime（`sc-root:/opt/projects/repos/sce-product-odoo`，`ENV=dev`，
   DB `sc_demo`，自定义前端）从当前 `eae0c1c0` 沿受管 main 车道精确推进到当前主线
   `ba7577c2`，恢复服务端前端、服务端 source_revision、发布面并回读身份。
2. 以真实用户身份对已部署版本执行用户视角验收：89 项正式业务入口矩阵
   （入口职责、权限边界、关键写入），并抽验付款申请写入闭环。

## Scope / exclusions

In scope: run/goal 记账；daily runtime 代码面、服务端前端、发布面；`sc_demo` 上的
只读用户验收；验收暴露在归属层的缺陷（如有）。

Explicitly excluded: 弱化任何 ACL/字段权限/断言；新建环境或凭据授权；既存历史残留
（`verify.contract.lint` 49 项、`res.users` 断言漂移、demo seed 与 #525 文档状态守卫冲突、
`span→deliverySpan` 迁移、账号清理 P2 ENV-IDENTITY-CLEANUP）；`PAYMENT-REQUEST-CHAIN-ALIGNMENT`
候选未经授权不得并入主线。

## Status

- [x] R: 把 daily runtime 精确推进到 `ba7577c2` 并回读服务身份。PASS。
      - 发布前远端 runtime 仓库 preflight `verify.daily_dev.runtime_repo.clean` PASS
        （`mode=main branch=main head=eae0c1c0`，customer addons 只读挂载 PASS）。
      - `daily.runtime.main.bundle_sync`：`old_sha=eae0c1c0` → `source_sha=ba7577c2`，
        `normalized_from_candidate=false`，`bundle_sha256=7f07c68bbe40c5152538fc1d51701dd1963ea4d4fc4553e2803c076ce28af0ad`，
        `upstream=origin/main`。
      - `daily.runtime.source_revision.align`：`previous_revision=eae0c1c0` → 服务端
        `source_revision=ba7577c2`，`restarted=true`，`rolled_back=false`。
      - `daily.runtime.frontend.build`：在已部署 HEAD 重建服务端前端，`rebuilt=true`，
        `fingerprint=e88ee704aad5e2d3c306b64f93ff71baf0c0d8367b657df559e0d56687a274c5`，
        `entry_asset=index-BuKwbLKS.js`。
      - `daily.runtime.published_face.converge`：`guard_status=PASS`，`login=wutao`；
        `construction.standard` 快照 118（released 90 / gate 90）、
        `construction.preview` 快照 119（released 90 / preview 39 / gate 129）；
        `upgrade_mode=reused`（`smart_core` 模块树与上次已验证升级逐字节一致）。
      - 服务端 `http://1.95.85.92:18081/api/runtime-version` 回读：
        `source_revision=git_sha=ba7577c212b81468491942e972ea28bd64345ebd`，
        `database=sc_demo`，`environment=dev`，`product_version=1.0.0-rc.20`，
        `frontend_build_sha256=e88ee704…`。
- [x] U1: 89 项正式业务入口矩阵（只读）。PASS。
      - `artifacts/frontend-business-entry-matrix/daily-ba7577c2-full/summary.json`：
        `ok=true`、`completeness=complete`、`entries=89`、`problems=[]`、
        `console_errors=[]`、`served_revision=ba7577c2`、`login=wutao`。
      - 发布面 90 叶子 / 89 action 叶子的口径差异已治理：第 90 项
        `smart_construction_core.menu_sc_workspace_home` 由 scene 交付、无 action，
        已在 `config/frontend/role_surface_exposure_declarations_v1.json` 的
        `non_action_delivery_entries` 显式登记，并由
        `verify.frontend.role_surface_exposure_declaration.guard` 约束
        「验收宇宙 89 + 非 action 交付入口 1 == 发布面 90」。
- [ ] U2: 付款申请写入闭环（付款申请 / 日常合同 / 项目启停三条 lane）。

### U2 根因（2026-10-15，只读定位）

付款申请写入 lane 在展开「按明细填写」后停机：

```
表单页面打开失败：契约缺少合法声明
formStructure.relation_entry.page_size(outflow_line_ids)
```

抓取同一会话的 `ui.contract.v2`（`finance` 账号、记录 36192、action 780）后核实：
缺失**不在后端契约生产者**。`fieldInfo.relation_entry` 与
`componentConfig.relationEntry` 两处都携带整数 `page_size=20`（同页
`options_limit=80` / `options_search_limit=40` 亦齐备）；仅 Odoo 原生
`widget_options.relation_entry` 这一历史别名不含该键。

真正缺陷在**前端消费路径未接线**：`payment.request` 的 `presentationMode=task`，
表单经 `ObjectTaskPage → CanonicalFormNodeRenderer → canonicalFieldToFormSection`
渲染，而该投影从未输出 `one2manyPageSize`；`one2manyPageSize` 当时只在
native 形态（`formSection.mapper`）被投影。渲染层按「声明缺失即停机」消费，
因此停机。

结论：不新增前端默认值、不改后端契约，只补齐 canonical 形态的同源声明投影。

（本文件在批次推进过程中持续更新。）
