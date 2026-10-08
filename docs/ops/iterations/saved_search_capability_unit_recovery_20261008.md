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
findings=139 distinct=99 contract-derived=51 projectable-gaps=0
frontend-logic-defects=0 render-interaction=88 unclassified=0
PASS: every scoped decision is contract-derived, a recorded projectable gap, or declared render/interaction
```

- 不变式 R1（字面能力门）与 R5（字面 action_id）在声明范围内命中数均为 **0**。
- R2 全部 intent 字面命中已发布 intent 目录（结构校验通过）。
- `contract-projectable-gap` 由 **7 → 0**（关闭方式见 5.3），`unclassified` 保持 **0**。
- **结论**：在声明的扫描面与声明的规则集下，"除渲染/交互外全部契约驱动"成立，
  且本轮已不存在"投影责任仍在前端"的登记缺口。该成立仍是有条件的、可复核的、只减不增的
  ——任何新增未登记决策都会被守卫判红。

### 5.3 缺口关闭记录（7 → 0，`contract-projectable-gap` 清零）

7 条缺口**不是**通过放宽断言、增加豁免或调低判定关闭的；每一条都把投影责任移回它的所有者层，
再由新增的 fail-closed 守卫断言钉住，防止回退。

| # | 原缺口 | 所有者层与修法 | 契约/证据 | 守卫断言 |
|---|---|---|---|---|
| 1 | `disabled_capability` / `disabled_permission`（`capabilityPolicyCore.js`、`SceneView.vue`、`WorkbenchView.vue`） | P0 前端契约消费：从渲染侧重算改为投影消费 `capability_state` + `capability_state_reason`；后端契约已发布该字段，前端 schema 声明补齐（`frontend/packages/schema/src/index.ts`） | `addons/smart_core/docs/Contract-2.0-Spec.md:247-249`（`allow \| readonly \| deny \| pending \| coming_soon`，明确"不允许前端自行推断状态"）；`docs/contract/exports/intent_catalog.json` 字段 `capabilities[].capability_state_reason` | `frontend_decision_authority.check_capability_projection_consumption` + `verify.frontend.capability_policy.unit` |
| 2 | `enabled`（`actionViewLoadGuardRuntime.ts`） | P0 前端契约消费：消费同一投影态，不再依赖前端 `CapabilityPolicyState` 字面 | 同上 | 同上 |
| 3 | `unconfigured` / `hidden` / `visible`（`MenuConfigView.vue`） | P0 后端契约投影：`smart_core` 新增每菜单 `handling_state` 词表与投影（`addons/smart_core/handlers/menu_configuration.py:37` 词表、`:349` 逐行投影），渲染侧删除本地 `policy_id` 推导 | `docs/product/menu_configuration_runtime_boundary_v1.md` §3 状态模型（投影映射：`visible_*`→`visible`，`hidden_*`→`hidden`，`candidate`/无配置意图→`unconfigured`） | `frontend_decision_authority.check_menu_handling_state_projection_consumption` + `addons/smart_core/tests/test_menu_configuration_audit.py` |
| 4 | `projection.refresh`（`projectionRefreshRuntime.ts`） | P0 前端渲染机制：本地 trace 标签改用 `local:` 命名空间（`local:projection_refresh`），与契约 intent 命名空间显式隔离；不伪装成契约 intent | 契约 intent 目录不含该名；`frontend:dispatch` 面不得发射该字面 | `frontend_decision_authority.check_client_trace_label_declaration`（声明类 `client_telemetry_trace`） |

守卫侧同步：`scripts/verify/frontend_decision_authority.py` 新增声明类 `client_telemetry_trace` 与
`DECLARED_CLIENT_TRACE_LITERALS`，新增上述两个 fail-closed 检查并接入 `reconcile()`；
`scripts/verify/test_frontend_decision_authority_guard.py` 由 11 → **15** 个用例
（含"本地推导被检出""后端投影被钉住""client trace 未发射被检出""client trace 不得 dispatch"
四个负例/正例）。台账 `docs/frontend_productization/decision-authority-inventory-v1.json` 重新导出。

**边界声明（不放宽）**：`contract-derived` 是**结构校验**结果（消费面确实消费了已发布的契约字段/词表），
不是"页面一定正确"的证明；本轮未下调任何既有验收断言，也未把任何未取证项记为通过。

### 5.4 结论的适用范围（诚实边界）

- 规则集是**有限**的：覆盖"字面能力门 / 字面 intent / 字面路由 / 字面业务状态 / 字面 action_id"五类形状；
  非字面形式（先赋值再比较、间接表驱动等）不在检出面内，属已知残余面。
- 渲染/交互半区来自**声明类**（UI 状态机 allowlist + 导航 shell 规则），不是逐文件豁免；
  守卫打印分类计数，任何未落入声明类或台账的命中都会判红。
- 本结论仅是**批次验收**级。运行态凭据链与 `local.clean` 档案前置（§4.C）仍未结论。

## 6. 状态边界


- 批次验收：本批（7 个门禁红项目标 + 1 项 token 补齐 + 1 项契约漂移修复 + 目录导出刷新 + 独立复核
  + 前端决策权属台账/守卫 + quick gate 全目标重跑通过，`-k` 单次全量 `GATE_EXIT=0`，57 个 unittest 入口 / 1030 用例，含本节 P0 投影闭环）。
- 主线集成 / 版本发布 / 产品交付：本批不主张。
- 运行态契约链（§4.C）：待运行态凭据前置恢复后单独取证，本轮不主张通过。

### 6.1 本次 P0 投影闭环的候选身份与结果索引

- 基线：`c9e4823899a1b834d3d0941b0578905f466e1c87`；候选 HEAD：**`cc4bedff`**（clean，无未跟踪文件）。
- 分层提交（同一分支、同一产品结果，按 P0/P1 责任层拆分，便于独立回滚）：
  - `5f2f6919` P0 后端契约投影：`addons/smart_core/handlers/menu_configuration.py` + 用例。
  - `c5a19c15` P0 前端契约消费：能力态/菜单处置态投影消费 + `local:` trace 标签 + schema 声明补齐 + 由前端源派生的 rendering-detail 清单刷新。
  - `cc4bedff` P4 台账/守卫与生成物：`frontend_decision_authority.py` / guard / 15 用例 / capability 冒烟计数 / `make/frontend.mk` / 台账导出 / 本记录 / run 索引。
- 结果索引：`.agent/runs/SAVED-SEARCH-CAPABILITY-UNIT-RECOVERY/run.json`，**17 项 check 全部 `reusable`**（绑定当前 clean HEAD）。
- 受影响 L2 门禁：`make verify.frontend.quick.gate`（`GATE_EXIT=0`）+ `verify.business_config.unit`（236）+ 计划推荐的
  `verify.frontend.scene_entry_contract.unit`（217）、`verify.frontend.style_system.guard`（2，另含 2 条 size-advisory，非失败）。
- L1：`make ci.local.iteration` → `PASS change_state=clean coverage=L1_only`。

### 6.2 本轮显式跳过项（附理由，非"通过"）

- **`make ci.local.quick` 未运行**：按 `AGENTS.md` 最新所有者分工（2026-09-23）节，本地 Quick 已降级为可显式诊断项，
  不再是普通 Gitee 候选推送前置；另按本项目既有环境结论，依赖受管运行环境的重建/快照车道存在未恢复的挂载独占 DENY 前置，
  在恢复前不进入依赖它的运行验收。因此本轮不以 Quick 作为结论依据，也不宣称"环境全部通过"。
- **独立复核未在本轮完成**：独立复核需由另一执行器或远端 PR 复核通道完成；本记录只提供精确候选身份供其绑定。
- **主线集成 / 版本发布 / 产品交付**：均未主张。

## 7. 合并车道补正：`ci.local.quick` 红项根因与处置（2026-10-08 同日追加）

### 7.1 红项事实

`make pr.merge PR=612` 的合并前置 `pr.merge.local_quick_gate`（`make/codex.mk`）在无 Quick 回执时
fail-closed 调用 `make ci.local.quick`。该 Quick 在 `verify.boq.dangerous.import.capability` 处退出 2：

```
addons/smart_construction_core/tests/test_boq_dangerous_import_handler.py:187 _load_handler_module()
addons/smart_construction_core/handlers/boq_dangerous_import.py:42
  from odoo.addons.smart_construction_core.handlers.reason_codes import (REASON_DONE,)
ModuleNotFoundError: No module named '...handlers.reason_codes';
'odoo.addons.smart_construction_core.handlers' is not a package
```

**说明**：本分支对齐产品面后，三个 handler 与模块内既有 `reason_codes` 声明载体保持同源导入（真实运行时
`handlers` 是 package，导入正常）。红项只出现在桩加载场景。

### 7.2 根因（责任层与边界）

- **责任层：P4 测试装载器**，不是产品投影/权限语义。
- 三个桩测试的 `_load_handler_module()` 把 `odoo.addons.smart_construction_core.handlers` 注册为**无 `__path__` 的假包**，
  同一函数内 `smart_core` / `core` / `utils` 却按真实目录绑定 `__path__` —— 装载器**声明与真实模块布局不一致**，
  使「handler 从本模块 `handlers.reason_codes` 导入原因码」这一真实依赖在桩下无法解析。
- 未放宽任何断言、未加业务/模型特判、未改产品语义；`reason_codes.py` 仍是从
  `odoo.addons.smart_core.utils.reason_codes` 重导出的声明载体。

### 7.3 处置

- 三个桩测试的装载器显式绑定真实包路径：`handlers_pkg.__path__ = [str(_ROOT / "handlers")]`
  （与同函数内 `smart_core.*` 的既有真实绑定一致）。
- run scope 补齐 `addons/smart_construction_core/tests/`（此前漏声明，属**元数据纠正**，非放宽范围）；
  越界集合清零后 run 恢复 `resolved`。

### 7.4 本轮重跑（受影响 L2）

| 目标 | 用例 | 结果 |
| --- | --- | --- |
| `verify.boq.dangerous.import.capability` | 29 | PASS |
| `verify.boq.line.patch.capability` | 17 | PASS |
| `verify.overview.rich.text.patch.capability` | 30（21+9） | PASS |

三条已写入 run 索引（`boq_dangerous_import_capability` / `boq_line_patch_capability` /
`overview_rich_text_patch_capability`，均 `passed`）。

### 7.5 系统性缺口（本轮暴露，已记录）

- **迭代 L2 集与冻结 Quick 集不一致**：`verify.frontend.quick.gate` **不含**上述 boq capability 目标，
  只有 `ci.local.quick` 覆盖 → 迭代期用 quick.gate 收口会漏掉该类桩装载缺陷。后续迭代若改动
  `addons/smart_construction_core/handlers/` 或对应桩测试，应把 `ci.local.quick` 的 handler 能力目标纳入
  L2 影响集（本条为入口选择规则，不是新增全局测试框架）。
- **合并入口 fail-closed 语义**：`pr.merge` 在无 Quick 回执时强制执行 Quick；故本轮 §6.2 关于“Quick 非推送前置”
  的结论**不适用于合并车道**，合并前必须在 clean 冻结 HEAD 上取得 Quick 回执。
