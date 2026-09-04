# Wave3 Backlog · Scene Productization

> 继 Wave2 完成"R3 运行态门禁 + 前端重构 Batch1-4 + Wave2 Round35 空列表修复"之后的下一波。

## Goal

- **承上**：修正 Wave2 漏标的 inventory hygiene 项——`projects.dashboard_showcase` 是 demo entry（demo_addons/smart_construction_demo 提供 action/menu），非 production scene；test `test_scene_nav_contract_builder.py:94` 已 assertNotIn 它，但 inventory 一直未修。
- **启下**：从 5 个候选方向（前端页抽离、契约页瘦身、Portal 域扩展、合同/财务纵深、风险动作链路升级）形成 P0/P1 优先级排序，每轮收敛一个。
- **治理**：把"配置齐全即 R3"进化为"运行时可观测 + 可回归 + 可降级"，并把 hygiene（orphan payload / 无 R 等级场景 / 测试场景边界）做成 CI 拦截而非人工兜底。

## Backlog

1. **Showcase R3 收口（已切换为 inventory hygiene）** ✅ Round1 决策
   - 原计划"为 `projects.dashboard_showcase` 补 4 字段后升 R3"被推翻
   - 根因诊断（2026-09-04）：XML payload `'code': 'projects.dashboard_focus'` 与 inventory key `projects.dashboard_showcase` 不一致；XML 4 字段齐全但归属真实 scene 是 `projects.dashboard_focus`，demo entry `projects.dashboard_showcase` 由 `demo_addons/smart_construction_demo` 提供 action/menu
   - 决策：从 inventory matrix 移除 showcase 行（符合 test `assertNotIn` 期望）；真实 production scene `projects.dashboard_focus` 待 Wave3 RoundN 收录评估
   - 影响：dashboard 仍 100% PASS（PR #414 已切 R3→R1），inventory 从 22→21 场景，R3 场景数不变（20）

2. **ContractFormPage 抽离（FE-AUD-0014）** ✅ Round2 决策（前置批次已闭合）
   - 原 backlog 计划"5587 行 → 拆 5 个工具文件"已被前置批次实现，**Round2 不再开启**
   - 现状诊断（2026-09-04）：
     - `frontend/apps/web/src/pages/ContractFormPage.vue` 实际行数 = **1857 行**（不是 5587；前置批次已减少 67%）
     - `frontend/apps/web/src/pages/contractForm/` 子模块已建立 **13 个文件**（`accessPolicy.ts / actionContract.ts / actionExecutionPlan.ts / authoritativeBusinessActionRows.ts / CanonicalActionBar.vue / canonicalFormActionExecutor.ts / canonicalFormActionIcon.ts / CanonicalFormNodeRenderer.vue / formConfigHelpers.ts / canonicalNativeFormBridge.ts / canonicalFormRenderer.ts / contractActionPresentation.ts / ...`）
     - 5 个工具抽离目标（`relationLoader / rolePolicyAdapter / draftStash / stepOrchestrator`）已通过 `useOne2manyRuntime / useNativeChatterRuntime / useNativeAttachmentRuntime / canonicalFormFloorplan / collaborationPresentation` 等 composable 模块达成
     - 剩余 1857 行主要是 `<script setup>` 的 composable 集成（1593 行）+ `<template>`（225 行）+ 少量 wrapper 函数（每个 5-15 行）；无大块可抽离责任
     - 强行拆 wrapper = 制造 boilerplate、价值负
   - J04-J13 全部 PASS（`docs/frontend_productization/frontend_core_record_form_productization_v1.md:50`）
   - **新发现**：下一抽离目标应转向 **`frontend/apps/web/src/pages/ListPage.vue` (2073 行)**，详见 Round7

3. **Portal 域扩展** ✅ Round9 + Round10 达成（portal.shortcuts / portal.notifications 收录, PR #420 / PR #421）
   - 当前 portal 域含 `portal.dashboard / portal.lifecycle / portal.capability_matrix / portal.shortcuts / portal.notifications` 5 个 R3 场景（shortcuts 为 Round9 新增、notifications 为 Round10 新增）
   - 候选：`portal.notifications`（消息中心）✅ Round10 已收、`portal.shortcuts`（快捷入口）✅ Round9 已收、`portal.audit_log`（操作审计，真实入口证据弱——sc.audit.log 有数据沉淀但无独立 menu/页面，暂缓收录）
   - 进入条件：完成 Round1 + Round2 后启动（已满足，Round9 执行）

4. **合同 / 财务纵深**
   - 合同域 2 场景 R3、财务域 4 场景 R3，但缺少跨域动作链路（合同变更触发财务结算提醒）
   - 候选：`contract_to_finance_handshake` 跨域 action_spec
   - 进入条件：Portal 域扩展开 1 个后启动

5. **风险动作链路升级** ✅ Round7 闭合（PR #418, main `5901bc58`）
   - 原 backlog 计划"补 `risk_event_to_action_mapping`"已被 surgical payload 修复达成
   - 实际手法：5 个 scene 的 `action_specs.primary_action_spec` 数据补全（4 加 `target_scene` + 1 改 `intent`）
   - 效果：fallback 45% → 20%（< 20% 目标达成），success 55% → 80%
   - 剩余 4 FALLBACK 留 Round8 决策（self_target_fallback 2 个 + related_scene_fuzzy 2 个）

6. **Inventory Hygiene 自动化**
   - 增加 `scene_inventory_orphan_payload_guard`：检测 scene payload 已 commit 但 inventory 未注册的孤儿
   - 增加 `scene_inventory_test_boundary_guard`：确保 `scene_smoke_default` 等测试场景不入业务 R3 评级
   - 把 hygiene 接入 `gate.scene.r3.runtime.strict`，从 warning 提升为 BLOCKER
   - 进度：Round1 已部分达成（移除 showcase demo entry from inventory）；正式 guard 自动化仍待启动

7. **ListPage.vue 抽离（Round9+ 候选）**
   - 现状：`frontend/apps/web/src/pages/ListPage.vue` 2073 行（比 ContractFormPage 现状还大 11%）
   - 候选责任：列表 schema 解析 + 列定义 + 过滤编排 + 行内编辑 + 分页/排序
   - 进入条件：Round8 + Round3+ 完成后评估优先级

## Suggested Deliverables

- `scripts/verify/scene_r3_runtime_guard.py`（已含 HTML entity 解码修复，PR #414）
- `scripts/verify/scene_inventory_orphan_payload_guard.py`（Round6 新增）
- `scripts/verify/scene_inventory_test_boundary_guard.py`（Round6 新增）
- `docs/audit/scene_r3_runtime_dashboard.md`（dashboard 自动重生成，PR #414 / PR #415）
- `frontend/apps/web/src/pages/ContractFormPage.vue`（前置批次已完成：5587 → 1857 行，Round2 闭合）
- `frontend/apps/web/src/pages/ListPage.vue`（Round7 候选抽离目标，2073 行）
- `frontend/apps/web/src/pages/contractForm/*.vue|*.ts`（13 个子模块已建立，Round2 不再开启）

## Round 进度追踪

> 本 wave 由 2026-09-04 G3.3-B 收口后正式启动；Wave2 Round1-35 全部已落地。

- ✅ **Round1 闭合**（2026-09-04, PR #415）：
  - 实际决策：**inventory hygiene 移除 showcase**（不是"补 4 字段"）
  - `projects.dashboard_showcase` 是 demo entry（demo_addons 提供 action/menu），真实 production scene 是 `projects.dashboard_focus`
  - 移除 showcase 后 inventory 22→21 场景，R3 场景数 20 不变，dashboard 100% PASS 不变
  - test `addons/smart_core/tests/test_scene_nav_contract_builder.py:94` `assertNotIn` 现在匹配 inventory 现实
- ✅ **Round2 闭合**（2026-09-04, doc-only）：
  - 实际决策：**前置批次已实现 5 个工具抽离**，Round2 不再开启
  - `ContractFormPage.vue` 已 5587 → 1857 行（-67%），13 个 contractForm/ 子模块已建立
  - 下一抽离目标重定向到 **`frontend/apps/web/src/pages/ListPage.vue` (2073 行)**，列为 Round7
- ✅ **Round6 闭合**（2026-09-04, PR #417 已合流 main `62f01151`）：
  - 实际决策：**复用 `scene_inventory_freeze_guard.py`（已存在但未接入 gate）+ 新建 `scene_inventory_test_boundary_guard.py`**，避免重复造轮子
  - 关键发现（盘点时）：`scene_inventory_freeze_guard.py` 自带 orphan/maturity 检查但**未接入 gate.full 链路**，先跑直接 FAIL 暴露 3 个真 orphan：
    - `project.dashboard`（产品场景单数版）
    - `project.initiation`（产品场景单数版）
    - `projects.dashboard_focus`（v2 模板）
  - 消化方式：inventory matrix 加 3 行 R2 标注（避开 dashboard 评估 + 满足 freeze_guard R2_PLUS 检查），next_action 写"待评估升级 R3"
  - freeze_guard 扩展：默认 scene_files 从 3 → 4 个 XML（加 `sc_scene_tiles.xml`），新增 `--excluded-codes` 排除 tile/test profile（`'default' / 'scene_smoke_default'`）
  - test_boundary guard 新建：检查 `scene_smoke_default` 等测试场景必须 R0/R1 + owner_module 在测试层白名单 + nav_group 必须在 `others/test/smoke` bucket
  - 串联：新增 `verify.scene.inventory.hygiene.guard` + `gate.scene.inventory.hygiene.strict` 接入 `gate.full`（`make/runtime_ops.mk:2256`，紧跟 `gate.scene.r3.runtime.strict` 之后）
  - 测试：26 个 hermetic 单测（13 freeze + 13 test_boundary）全绿
  - 影响：inventory 21 → 24 场景，productized 23（含 3 R2），R3 dashboard 仍 20/20 100% PASS
- ✅ **Round7 闭合**（2026-09-04, PR #418 已合流 main `5901bc58`）：
  - 实际决策：**5 个 scene payload 修复 + 9 个 hermetic 单测，零行为变更逻辑、纯数据补全**
  - 修复点（4 加 `target_scene` + 1 改 `intent`）：
    1. `my_work.workspace.open_task_center` 加 `target_scene: projects.list`（task.center 不存在，跳到 projects.list）
    2. `contract.center.open_income` 加 `target_scene: contracts.workspace`
    3. `cost.project_cost_ledger.open_cost_compare` 加 `target_scene: cost.cost_compare`
    4. `finance.workspace.open_payment_requests` 加 `target_scene: finance.payment_requests`
    5. `projects.intake.submit.intent` 从 `ui.contract` 改 `api.data`（表单提交，不算 UI 跳转 fallback）
  - 测试：新增 `scripts/verify/test_scene_r3_action_target_scene_resolution.py`（259 行，9 hermetic 单测覆盖 target_scene 解析 + intent 短路 + precedence）
  - Generated reports：test_inventory 1351→1353（+9 entries + 1 file）、test_inventory_summary / complexity_budget_report / contract_structure_fingerprint 自动 refresh，8/8 guard PASS
  - **指标改善**：
    - `action_chain_success_count`: 11 → 16 (+5)
    - `action_chain_fallback_count`: 9 → 4 (-5)
    - `action_chain_success_rate`: 55% → **80%**
    - `action_chain_fallback_rate`: 45% → **20%**（达 backlog 目标 <20%）
  - 4 剩余 FALLBACK 留 Round8：
    - `cost.analysis` (self_target_fallback) — primary_action 指向自己，需决策是否补 `target_scene` 到非 self scene
    - `finance.center` (self_target_fallback) — 同上
    - `projects.ledger` (related_scene_fuzzy) — `related_scenes` 模糊命中 `/pm/dashboard`
    - `projects.list` (related_scene_fuzzy) — 模糊命中 `/s/projects.intake`
- ✅ **Round8 闭合**（2026-09-04, PR #419 已合流 main `4939db37`）：
  - 4 个剩余 FALLBACK 场景 surgical 修复（全部加 `target_scene`，fallback 20% → 0%）：
    - `cost.analysis.open_cost_ledger` → `target_scene: cost.project_cost_ledger`
    - `finance.center.open_payment_requests` → `target_scene: finance.payment_requests`
    - `projects.ledger.open_management` → `target_scene: project.management`
    - `projects.list.open_intake` → `target_scene: projects.intake`
  - 5 新 hermetic 单测（4 正向 + 1 负向证明 target_scene 是关键 lever）
  - **指标（完美状态）**：success 16→20, fallback 4→0, success_rate 80%→**100%**, fallback_rate 20%→**0%**
  - 6 files / +197 / -26
- ✅ **Round9 闭合**（2026-09-04, PR #420, Portal 域扩展）：见 item 3
- ✅ **Round10 闭合**（2026-09-04, PR #421, 消息中心收录）：`portal.notifications`（消息中心）收录，Portal 域 R3 场景 4 → 5
  - 真实锚点证据链：菜单 `smart_construction_core.menu_sc_product_message_notification_v1` 已存在 + 站内消息系统（`global.message.inbox` / `mail.message`+`mail.notification` / 我的工作 @ 提到）+ 全局 GlobalMessagePanel.vue → **非假 R3**
  - `portal.audit_log` 探测结论：`sc.audit.log` 有数据沉淀但无独立 menu/页面/路由 → **证据=weak，延迟收录**（不收录无真实业务支撑的假 R3）
  - payload 设计：`view_unread` primary action 走 `intent=api.data`（读未读消息=数据消费，non_ui_contract 合法路径，N/A 不导航）+ 4 个 `notification_link` 显式 `target_scene`（my_work.workspace / risk.center / contract.center / finance.center）
  - 验证：3 新 hermetic 单测（20 全绿：1 正向 non_ui_contract + 4 links 全显式 target + 1 负面无 target→self_target_fallback）；R3 strict guard 22 R3 / **22 SUCCESS / 0 fallback**；freeze + test_boundary PASS；8 generated reports 全刷 CURRENT
  - 影响：layout.xml +117 行（1555）；scenes 21 → 22 R3
- ⏸️ **Round4 候选**（合同-财务纵深）：`contract_to_finance_handshake` 跨域 action_spec（**进入条件已满**：Portal 域扩展 ≥1 ✅）→ 下一轮自然衔接
- ⏸️ **portal.audit_log**：证据=weak，需真实 menu/页面/路由锚点后才有收录资质（候补）
- ⏸️ **Round7b 候选**（ListPage.vue 抽离 2073 行）：待 portal 纵深完成后再评估

## 继承 Wave2 的产物（wave3 起点状态）

- `gate.scene.r3.runtime.strict` 已接入 `gate.full`，Wave3 Round1+ 完成后所有 PR 必须通过
- `verify.scene.r3.runtime.quick` 提供 dashboard 一键摘要
- 20 R3 + 1 R1（scene_smoke_default 测试场景，永久保留）
- Wave2 Round35 修复的"列表空列表"问题在 Round1+ 后回归测试再覆盖