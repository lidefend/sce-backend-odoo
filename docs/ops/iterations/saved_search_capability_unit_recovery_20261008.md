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
`verify.role.capability_floor.prod_like`、`verify.contract_drift.guard`（修复后）、
`verify.contract.authority_hierarchy.guard`、`verify.contract.handler_boundary.guard`、
`verify.contract.governed_policy_guard`、`verify.contract.form_field_policy.unit`（4）、
`verify.contract.probe_routing.unit`（5+3）、`verify.contract.api.mode.smoke`（http://localhost:8070）、
`product_view_structure_contract_guard`（formal_menu_count=89、resolved view actions=89、surfaces=281）。

以上合计 16 个离线契约目标在本轮取得通过结论；`verify.contract.probe_routing.unit` 在依赖顺序中
先执行，故单独作为显式目标时显示为 no-op，其两个 unittest 模块已实际执行。

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
- `verify.contract.ordering.smoke` → `login failed for determinism smoke: admin`；
  `verify.contract.mode.smoke` → `runtime probe authentication unavailable: source=dev_test_bootstrap`；
  `verify.contract.view_type_semantic.smoke` → `login response missing token`；
  `verify.contract.assembler.semantic.smoke`（及其 schema guard）→ 同一运行态探针。
- `verify.contract.native_view_normalized_map` 的 `contract.view_carrier.export` →
  `ValueError: carrier collector requires database sc_clean`：该导出绑定 `local.clean`（一次性
  洁净安装）档案，不是每日开发/样例库；属于**受管档案前置**，不得用其它库替代。

因此"完整运行时契约驱动"的结论是：**离线契约族无未决红项**（16 个目标通过，其中 1 个为本轮修复）；
未结论的部分有两条，都是前置而非缺陷：一条运行态登录链（凭据面），一条受管档案前置（`local.clean`）。
两者都需在受管入口下重跑取证，不得用放宽、跳过或换库替代。

## 5. 前端决策权属台账：`除渲染/交互外全部契约驱动` 的可判定结论

用户提问："现在的结论能支撑自定义前端除了渲染与交互外的所有逻辑都来自契约驱动的终极目标吗？"
本轮把该命题从叙述升级为**可判定检查**，并给出结论。

### 5.1 新增权威与守卫（唯一来源 + fail-closed）

- `scripts/verify/frontend_decision_authority.py`：台账唯一来源。声明 5 条检测规则
  （R1 字面能力门 / R2 字面 intent / R3 字面路由 / R4 业务状态字面 / R5 字面 action_id），
  扫描 `frontend/apps/web/src/{pages,views,app}`（排除 node_modules，去注释行）。
- `docs/frontend_productization/decision-authority-inventory-v1.json`：生成并提交的台账，可在 diff 中评审。
- `scripts/verify/frontend_decision_authority_guard.py`：fail-closed 守卫。
- `scripts/verify/test_frontend_decision_authority_guard.py`：11 个用例，含负例
  （先证明未注入的基线干净，再注入新决策，守卫必须检出）。
- `make verify.frontend.decision_authority.{unit,guard,export}`，并作为前置挂入 `verify.frontend.quick.gate`。

判定语义（每个命中必须落三类之一，否则 FAIL）：

1. `contract-derived`：消费后端契约投影。R2 中该分类的断言必须能在
   `docs/contract/exports/intent_catalog.json` 找到同名 intent —— 这是**结构校验**，不是字符串冻结。
2. `contract-projectable-gap`：前端决策当前没有契约载体、但可由后端投影。这是到目标的**唯一合法剩余距离**。
3. `excluded-render-interaction`：声明的渲染/交互半区（UI 状态机 allowlist + 导航 shell 规则）。

### 5.2 实测结论（`make verify.frontend.decision_authority.unit`，含守卫）

```
findings=137 distinct=97 contract-derived=43 projectable-gaps=7
frontend-logic-defects=0 render-interaction=87 unclassified=0
PASS: every scoped decision is contract-derived, a recorded projectable gap, or declared render/interaction
```

- 不变式 R1（字面能力门）与 R5（字面 action_id）在声明范围内命中数均为 **0**。
- R2 全部 intent 字面命中已发布 intent 目录（结构校验通过）。
- **结论**：在声明的扫描面与声明的规则集下，"除渲染/交互外全部契约驱动"成立；
  该成立是**有条件的、可复核的、只减不增的**——台账给出唯一缺口清单（5.3），
  任何新增未登记决策都会被守卫判红。

### 5.3 剩余缺口（`contract-projectable-gap`，逐条可行动）

| decision | 位置 | 缺口 |
|---|---|---|
| `disabled_capability` | `frontend/apps/web/src/app/capabilityPolicyCore.js:7` | 能力态词表在前端计算；后端已发布 `PERMISSION_DENIED` 与 `allow/readonly/deny/pending/coming_soon`，但未投影该状态名 |
| `disabled_permission` | `frontend/apps/web/src/app/capabilityPolicyCore.js:12` | 前端按用户组重算权限拒绝，后端已有 `PERMISSION_DENIED`，应改为投影 |
| `disabled_permission` | `frontend/apps/web/src/views/SceneView.vue:990` | 同上，消费点 |
| `disabled_capability` | `frontend/apps/web/src/views/WorkbenchView.vue:462` | 同上，消费点 |
| `enabled` | `frontend/apps/web/src/app/runtime/actionViewLoadGuardRuntime.ts:23` | 依赖前端 `CapabilityPolicyState`，应消费投影态 |
| `unconfigured` | `frontend/apps/web/src/views/MenuConfigView.vue:364` | 菜单处置态由渲染侧本地 `policy_id` 推导；后端只发布 `unconfigured_hidden_count` |
| `projection.refresh` | `frontend/apps/web/src/app/projectionRefreshRuntime.ts:42` | intent 命名空间字面未在契约目录声明（仅作本地 trace 标签），须登记或改名 |

**边界声明（不放宽）**：这些 gap 只表示"投影责任仍在前端"，不等于页面出现错误行为；
本批不下调任何既有验收断言，也不把 gap 记为通过或已修复。它们属于后续批次的实际工作项。

### 5.4 结论的适用范围（诚实边界）

- 规则集是**有限**的：覆盖"字面能力门 / 字面 intent / 字面路由 / 字面业务状态 / 字面 action_id"五类形状；
  非字面形式（先赋值再比较、间接表驱动等）不在检出面内，属已知残余面。
- 渲染/交互半区来自**声明类**（UI 状态机 allowlist + 导航 shell 规则），不是逐文件豁免；
  守卫打印分类计数，任何未落入声明类或台账的命中都会判红。
- 本结论仅是**批次验收**级。运行态凭据链与 `local.clean` 档案前置（§4.C）仍未结论。

## 6. 状态边界


- 批次验收：本批（7 个门禁红项目标 + 1 项 token 补齐 + 1 项契约漂移修复 + 目录导出刷新 + 独立复核
  + 前端决策权属台账/守卫 + quick gate 重跑 165 PASS）。
- 主线集成 / 版本发布 / 产品交付：本批不主张。
- 运行态契约链（§4.C）：待运行态凭据前置恢复后单独取证，本轮不主张通过。
