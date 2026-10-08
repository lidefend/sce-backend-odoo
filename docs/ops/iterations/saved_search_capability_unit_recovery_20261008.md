# 前端 quick gate 红项根因恢复（2026-10-08）

## 1. 目的与边界

把 `make verify.frontend.quick.gate` 从 7 项红还原为全绿，并给出一次完整的运行时契约驱动
检测结论。每一项都在**它自己的责任层**修复。

- Formal Product Layer：P4（受管本地门禁及其测试工具）；P0 通用前端渲染机制（共享间距 token
  与官方 navigation drawer 适配层）。
- Layer Target：`addons/smart_core/tests/`、`scripts/verify/`、`frontend/apps/web/scripts/`、
  `frontend/apps/web/src/styles/tokens/component.css`、`frontend/packages/ui/src/kits/tdesign/theme.css`。
- Standard vs User-Specific：平台机制（通用 token / 官方组件适配）与 ops delivery tool（门禁与其用例）。
- Why Here：每一项红都由产生该行为的层拥有——用例与 harness 拥有各自的依赖绑定；shell/list
  组合用例拥有它所断言的已发布组件结构；协作面板守卫拥有"声明驱动只读"规则；drawer 内边距
  字面量由通用 token 层拥有。
- Why Not Elsewhere：不放宽任何断言、ACL、字段权限或负例；不加业务模型特判；不改门禁入口与其
  注册目标；不做数据库/夹具/运行时写入。
- Blast Radius：`verify.frontend.quick.gate` 的 7 个目标 + 1 个共享 token 与 1 处官方 drawer
  适配；后端契约、模型、权限、动作零改动。

## 2. 红项、根因与修法（逐项）

| # | 目标 | 根因 | 修法 |
| - | ---- | ---- | ---- |
| 1 | `verify.frontend.saved_search_capability.unit` | 用例用 AST 只抽 `seal_runtime_contract` 单个函数，exec 进裸命名空间；PR #533 给该链路加了模块级 helper（`_published_version_ref` 等），命名空间不再满足 | 改为执行**模块自身全部顶层语句**（仅外部 import 用替身），被测函数的传递依赖真实存在；断言不变 |
| 2 | `verify.frontend.contract_record_action_state.unit` | 断言的文案是旧版"当前契约"，实现已改为"当前页面" | 期望值跟随已发布文案 |
| 3 | `verify.frontend.adopted_form_engine_decision.unit` | PR #529 把 `const owner = this` 改为箭头函数 `this`，但 render 闭包内遗留 2 处 `owner.` → `ReferenceError: owner is not defined` | 闭包内改回 `this`（`this.fields.value` / `this.renderedFields()`） |
| 4 | `verify.frontend.standard_collection_composition.unit` | 断言钉旧字面量 `<ProductListSurface v-else-if="status === 'empty'">`；PR #525 后空态是 `<section v-else-if="status === 'empty'">` 包裹 `ProductListSurface` | 改为在空态分支内断言 `ProductListSurface` 且总数=2（不变式，不钉标签写法） |
| 5 | `verify.frontend.standard_shell_composition.unit` | 断言钉旧固定侧栏尺寸 `min(340px, calc(100vw - 44px))`；PR #525 已删除该固定侧栏 | 改为正则不变式，保留 viewport-offset 语义，不钉具体尺寸 |
| 6 | `verify.frontend.contract_form_save_failure_recovery.unit` | harness 缺 `useRecordFormActions` 依赖（`isComponentActive`/`formRouteIdentity`/`formRouteOwnerIdentity`），且 `route`/`session` 不是真实身份形态，`boundSurfaceKey()` 访问空值崩溃 | 补齐依赖与 route/session 身份输入 |
| 7 | `verify.frontend.professional_collaboration.unit` | 守卫仍要求 `:readonly` 由 `renderMode` 推导；PR #607 已改为**声明驱动**（`v-bind="collaborationPanelProps"`，`useRecordCollaborationPresentation.ts` 内 `readonly: configurationPreview === true`），有 blocker 26 裁决 | 守卫改为"宿主不得用 renderMode 推导面板只读 + 必须转发声明 props"；同步更新/重命名/新增正负例，面板改回 renderMode 推导时仍 fail-closed |
| 8 | `verify.frontend.rendering_detail_state.unit` | 刷新官方设计对齐清单暴露真实字面量缺口：`.sc-design-drawer--navigation` 直接写 `--td-comp-paddingTB-l: 0px; --td-comp-paddingLR-l: 0px;`（`visualLiteralGapCount=1`） | 新增通用 token `--sc-space-none: 0px`（`tokens/component.css`），drawer 适配层改消费该 token；再刷新三份清单 |

第 1 项的引入时点由 `git blame` 定位到 PR #533（`9abaa79d`），用例最后一次修改是 `2d164a1f`（PR #525）。
四项必需 CI 中的 `frontend_release_gate` 只跑 pnpm lint/typecheck/test，不含这些 python/node 目标，
因此漏过——这是守门缺口，不是本次修复放宽的对象。

第 8 项的清单刷新同时把若干 surface 的 `stateTypes` 按**当前已发布源码**重新推导（focus/disabled/empty），
即旧清单相对 main 已陈旧；`visualLiteralGapCount` 由 1 归 0，`internalVendorSelectorGapCount` 保持 0。

## 3. 证据（本次取证）

门禁总入口（前台一次运行，日志 `.runtime/agent-runs/SAVED-SEARCH-CAPABILITY-UNIT-RECOVERY/frontend_quick_gate.log`）：

```
make verify.frontend.quick.gate        # /tmp/fe_gate_final2.log → GATE_EXIT=0
[OK] verify.frontend.quick.gate done
```

逐目标 receipt（`make agent.run.record`，`.runtime/agent-runs/SAVED-SEARCH-CAPABILITY-UNIT-RECOVERY/`）：

| check | target | 结果 | 用例数 |
| ----- | ------ | ---- | ------ |
| saved_search_capability_unit | `verify.frontend.saved_search_capability.unit` | passed | 29 |
| contract_record_action_state | `verify.frontend.contract_record_action_state.unit` | passed | 26 |
| adopted_form_engine_decision | `verify.frontend.adopted_form_engine_decision.unit` | passed | 74 |
| standard_collection_composition | `verify.frontend.standard_collection_composition.unit` | passed | 201 |
| standard_shell_composition | `verify.frontend.standard_shell_composition.unit` | passed | 71 |
| contract_form_save_failure_recovery | `verify.frontend.contract_form_save_failure_recovery.unit` | passed | 5 |
| professional_collaboration | `verify.frontend.professional_collaboration.unit` | passed | 82 |
| rendering_detail_state | `verify.frontend.rendering_detail_state.unit` | passed | 76 |
| frontend_quick_gate | `verify.frontend.quick.gate` | passed | 164 |
| contract_drift_guard | `verify.contract_drift.guard` | passed | 11 |
| contract_catalog | `verify.contract.catalog` | passed | 6 |

日志中出现的 `FAIL incomplete={'internalVendorSelectorGapCount': 1}` 是
`scripts/audit/test_generate_frontend_official_design_alignment_inventory` 的**负例预期输出**，
其后的真实运行输出为 `PASS summary={... 'internalVendorSelectorGapCount': 0, 'visualLiteralGapCount': 0}`；
`saved_search` 日志中的 `RuntimeError: ir.filters unavailable` 同样是用例内构造的负例路径。

## 4. 契约族交叉检测结论（运行时契约驱动）

在门禁全绿之后，对**契约族**（`verify.contract*` / `gate.contract*`，共 50 个注册目标）做了一次
交叉检测。结论分三类：

**A. 已通过（离线）**：`verify.contract.structure_lock`（domains=14, fingerprint=current）、
`verify.contract.schema.declaration.sync`（version=2.2.0 status=stable）、`verify.contract.subviews.guard`、
`verify.contract.operation_gateway.guard`、`verify.contract.page_v1_zero_residue.guard`、
`verify.contract.parse_boundary.guard`、`verify.contract.native_integrity_guard`、
`verify.contract.production_chain.guard`、`verify.contract.envelope.guard`、
`verify.contract.governance.coverage`、`verify.contract.scene_coverage.brief`、
`verify.contract.catalog`、`verify.scene.contract.shape`、`verify.business.core_journey.guard`、
`verify.role.capability_floor.prod_like`、
`verify.contract_drift.guard`（修复后）。

**B. 本轮发现的真实缺口并已修复**：

- `verify.contract_drift.guard` 报 `hard-coded reason_code literals`：
  `addons/smart_construction_core/handlers/boq_line_patch.py`、`boq_dangerous_import.py`、
  `overview_rich_text_patch.py` 各写死 `"reason_code": "DONE"`，而同族
  `my_work_complete.py` 已从 `smart_construction_core/handlers/reason_codes.py` 消费 `REASON_DONE`。
  这是**声明未被消费**的契约漂移。修法：三个 handler 改为导入并消费 `REASON_DONE`，清零字面量；
  取值仍是 `DONE`，无行为变化。修复后该目标 PASS（含 idempotency 声明扫描与
  `verify.intent.side_effect_policy_guard`：policy_items=11 intents_scanned=122）。
- `docs/contract/exports/intent_catalog.json` 相对当前工作树陈旧（`test_refs` 未随本轮用例变化刷新）。
  `make verify.contract.catalog` 重新导出，`contract_catalog_determinism_guard` PASS，证明是可复现的
  确定性产物而非噪声。

**C. 运行环境前置未满足（不计为产品缺口）**：以下目标需要在**已注册运行态**上以角色矩阵登录，
本轮本地未提供该凭据面，因此未取得结论，也未被放宽：

- `verify.contract.surface_mapping_guard` → `RuntimeError: missing token`
- `verify.scene_catalog_runtime_alignment_guard` /
  `verify.scene_capability.contract.guard` → `all role-matrix logins failed:
  sc_fx_pm,sc_fx_executive,sc_fx_finance,sc_fx_contract_admin,sc_fx_project_member,
  sc_fx_material_user,sc_fx_cost_user,admin,demo_pm,demo_finance,demo_role_executive`。
- 由此级联：`artifacts/scene_capability_contract_guard.json` 未生成 →
  `verify.role.capability_floor.guard`（提示先跑 `make verify.capability.schema`）→
  `verify.business.capability_baseline.report`、`verify.backend.architecture.full.report`、
  `verify.contract.governance.brief`、`verify.contract.evidence.guard` 一并失败。
  这五项的失败是**同一运行态前置**的下游级联，不是独立缺陷。

因此"完整运行时契约驱动"的结论是：**离线契约族无未决红项**；唯一未结论的是一条运行态登录链，
其状态为**环境前置未满足**（需在受管运行态上以既有凭据入口重跑，不得用放宽或跳过替代）。

## 5. 状态边界

- 批次验收：本批（7 个门禁红项目标 + 1 项 token 补齐 + 1 项契约漂移修复 + 目录导出刷新 + 独立复核）。
- 主线集成 / 版本发布 / 产品交付：本批不主张。
- 运行态契约链（§4.C）：待运行态凭据前置恢复后单独取证，本轮不主张通过。
