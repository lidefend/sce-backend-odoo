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

日志中出现的 `FAIL incomplete={'internalVendorSelectorGapCount': 1}` 是
`scripts/audit/test_generate_frontend_official_design_alignment_inventory` 的**负例预期输出**，
其后的真实运行输出为 `PASS summary={... 'internalVendorSelectorGapCount': 0, 'visualLiteralGapCount': 0}`；
`saved_search` 日志中的 `RuntimeError: ir.filters unavailable` 同样是用例内构造的负例路径。

## 4. 检测结论与残留

- `verify.frontend.quick.gate`：**全绿**（exit 0；164 条 PASS 行，0 失败目标）。它是本轮唯一已知的
  本地前端契约阻断入口，现在没有未决红项。
- 未纳入本轮主张的层：远端必需 CI（`frontend_release_gate` 等）、受管 Quick、部署与用户级验收。
  本报告只主张**批次验收**，不主张主线集成 / 版本发布 / 产品交付。
- 已知守门缺口（不在本轮职责、仅记录）：`frontend_release_gate` 的 pnpm 链**不覆盖** python/node
  契约目标，因此这类漂移只能在本地 quick gate 或 `ci.local.quick` 暴露；若要根治需在 P4 门禁层
  单独立项。

## 5. 状态边界

- 批次验收：本批（7 个红项目标 + 1 项 token 补齐 + 独立复核）。
- 主线集成 / 版本发布 / 产品交付：本批不主张。
