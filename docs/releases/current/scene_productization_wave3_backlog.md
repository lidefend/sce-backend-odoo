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

2. **ContractFormPage 抽离（FE-AUD-0014）**
   - `frontend/packages/ui/src/pages/ContractFormPage.vue` 当前 5587 行，承担 relation one2many 加载 + 角色化配置 + 草稿持久化 + 多 step 编排
   - 拆分策略：relation 加载抽 `relationLoader.ts`、角色配置抽 `rolePolicyAdapter.ts`、草稿持久化抽 `draftStash.ts`、step 编排抽 `stepOrchestrator.ts`
   - 完成 5 个抽离后回归 J04-J13 验收 runtime 不退化

3. **Portal 域扩展（可选）**
   - 当前 portal 域仅含 `portal.dashboard / portal.lifecycle / portal.capability_matrix` 3 个 R3 场景
   - 候选：`portal.notifications`（消息中心）、`portal.shortcuts`（快捷入口）、`portal.audit_log`（操作审计）
   - 进入条件：完成 Round1 + Round2 后启动

4. **合同 / 财务纵深**
   - 合同域 2 场景 R3、财务域 4 场景 R3，但缺少跨域动作链路（合同变更触发财务结算提醒）
   - 候选：`contract_to_finance_handshake` 跨域 action_spec
   - 进入条件：Portal 域扩展开 1 个后启动

5. **风险动作链路升级**
   - `risk.center` 已是 R3，但 `risk_event` -> `project_action` 的链路主要靠 `related_scene_match` fallback（45%）
   - 目标：补 `risk_event_to_action_mapping`，将 fallback 比例降到 < 20%

6. **Inventory Hygiene 自动化**
   - 增加 `scene_inventory_orphan_payload_guard`：检测 scene payload 已 commit 但 inventory 未注册的孤儿
   - 增加 `scene_inventory_test_boundary_guard`：确保 `scene_smoke_default` 等测试场景不入业务 R3 评级
   - 把 hygiene 接入 `gate.scene.r3.runtime.strict`，从 warning 提升为 BLOCKER

## Suggested Deliverables

- `scripts/verify/scene_r3_runtime_guard.py`（已含 HTML entity 解码修复）
- `scripts/verify/scene_inventory_orphan_payload_guard.py`（Round6 新增）
- `scripts/verify/scene_inventory_test_boundary_guard.py`（Round6 新增）
- `docs/audit/scene_r3_runtime_dashboard.md`（dashboard 自动重生成）
- `frontend/packages/ui/src/pages/ContractFormPage.vue`（重构后预计 < 3000 行）
- `frontend/packages/ui/src/app/relationLoader.ts`（Round2 新增）
- `frontend/packages/ui/src/app/rolePolicyAdapter.ts`（Round2 新增）
- `frontend/packages/ui/src/app/draftStash.ts`（Round2 新增）
- `frontend/packages/ui/src/app/stepOrchestrator.ts`（Round2 新增）

## Progress

> 本 wave 由 2026-09-04 G3.3-B 收口后正式启动；Wave2 Round1-35 全部已落地。

- ⏳ Round1 待启动（Showcase R3 收口）：
  - 为 `projects.dashboard_showcase` 补 4 R3 字段，inventory 升至 R3
  - dashboard `pass_rate` 从 95.24% 回到 100%
  - `scene_r3_runtime_guard` 通过（0 BLOCKER / 0 WARNING）
- ⏸️ Round2 待启动（ContractFormPage 抽离）：
  - 等待 Round1 dashboard 验证 + 用户授权
- ⏸️ Round3+ 按 (Portal 域扩展 / 合同财务纵深 / 风险动作链路 / Hygiene 自动化) 顺序展开

## 继承 Wave2 的产物（wave3 起点状态）

- `gate.scene.r3.runtime.strict` 已接入 `gate.full`，Wave3 Round1 完成后所有 PR 必须通过
- `verify.scene.r3.runtime.quick` 提供 dashboard 一键摘要
- 21 个业务场景 + 1 个测试场景，21 R3 + 1 R1（Round1 完成后预期 22 R3 + 0 R1 业务）
- Wave2 Round35 修复的"列表空列表"问题在 Round1 后回归测试再覆盖