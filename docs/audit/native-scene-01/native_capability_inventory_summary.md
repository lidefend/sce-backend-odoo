# NATIVE-SCENE-01 · A01-A04 原生能力盘点检查点

状态：`verification_pending`，等待独立复核和下一轮调度。

基线：`audit/native-scene-01-a01-a04-20261116@44cfed924b44b690dbb9f833ca9fcb605e8196cc`

## 1. 本轮结果

本轮只读完成 A01-A04，并补齐 A08 所依赖的入口拓扑。未修改产品源码、契约、配置、
数据库、业务数据、菜单、发布快照或运行时环境，未创建 PR。

交付物：

- [A01 模型与字段清单](native_model_inventory.md)
- [A03 Action 清单](native_action_inventory.md)
- [A04 View 清单](native_view_inventory.md)
- [A08/A02 入口拓扑](native_business_entry_topology.md)
- [扫描 Manifest](inventories/inventory_manifest.json)
- [模型机器清单](inventories/native_model_inventory.json)
- [菜单机器清单](inventories/native_menu_inventory.json)
- [Action 机器清单](inventories/native_action_inventory.json)
- [View 机器清单](inventories/native_view_inventory.json)
- [原始证据索引](evidence/README.md)

PR #902 独立审查 R1 已按六项补齐：

1. Registry 原始快照已进入
   [`evidence/navigation_capability_inventory_v1.json`](evidence/navigation_capability_inventory_v1.json)，
   SHA256 `5baa7b10cfe1aab3a75df4594f2ad813ed4245ed799ea422d3c68cd73133415a`。
2. 446 个唯一菜单已输出为 `native_menu_inventory.json`。
3. 模型、Action、View 已输出为独立机器可读清单。
4. 只读扫描工具为 `scripts/audit/native_scene_inventory.py`，精确命令记录在
   `inventory_manifest.json`；写入与校验分别使用脚本默认模式和 `--check`。
5. Markdown 统计已按机器清单重新核对；模型 Abstract/Transient 区分“身份数/声明数”，
   View 类型、SQL 约束和菜单 Groups 等数字已修正。
6. 完成修订后将在新 HEAD 重跑检查并请求独立复审。

## 2. 必须明确的五个答案

### 2.1 我们已经具备哪些 Odoo 原生业务能力？

已经具备一个较大的 Odoo 原生业务底座，而非只有少量 `sc.*` 场景模型：

- Registry 历史只读快照观察到 758 个模型；282 个原生业务入口直接触及 167 个模型。
- 当前仓库源码可见 359 个 distinct 模型身份、5,896 个字段声明、1,434 个关系字段、
  708 个计算字段、124 个 `@api.constrains` 方法、63 个 `@onchange` 方法。
- 92 个模型复用 `mail.thread + mail.activity.mixin`，50 个模型复用 OCA
  `tier.validation`。
- Odoo 原生项目、任务、会计、采购、库存、产品、伙伴、用户、公司、审批和协作模型继续是系统根。
- 行业模块在其上提供合同、预算、成本、付款、结算、材料、劳务、设备、分包、质量、安全、
  投标、人事和报表等业务文档。
- 已登记 36 个投影/读取面，但这些必须继续与业务事实模型分开。

证据入口：
[`native_model_inventory.md`](native_model_inventory.md)；
[`current-native.log:19854`](../capability-explorer-05/evidence/current-native.log#L19854)。

### 2.2 一个原生菜单、Action、View Set 如何构成独立业务场景？

当以下链路全部保持身份和语义时，它可以作为独立业务场景交付：

```text
Menu XMLID
  -> Action XMLID / type / domain / context / groups
  -> Model
  -> declared view modes
  -> every action-bound View + search View
  -> merged inherited XML for current user/company
  -> ui.contract.v2
  -> matching Renderer
  -> CRUD / onchange / button / server execution
  -> ACL / record rule / field groups / multi-company
```

判断条件不是“有菜单”，而是：

- Menu 与 Action 的复合身份稳定；
- 每个 `view_mode` 都有实际 View 和 Renderer；
- domain/context/search defaults 完整进入契约；
- button、modifier、onchange 和业务方法可执行但不再由前端重算；
- ACL、record rule、字段组和多公司事实生效；
- 无权限、空数据、非法操作、事务失败都有明确结果。

当前 132 个正式产品入口已经证明“单 Menu + 单 Action + View Set”可以作为主交付单元。
场景组合应保留给跨对象流程、统一驾驶舱或一个入口确实需要多个原生能力协同的情况。

### 2.3 哪些复杂专业视图已经具备原生事实与后端解析？

| 能力 | 原生事实 | 后端解析 | 前端 | 当前结论 |
|---|---|---|---|---|
| Pivot | 源码 29 个 View；正式产品 8 个入口激活 | measure/dimension/interval/aggregate | `core.pivot` | 专用链存在；全范围统计语义未完整 |
| Graph | 源码 9 个 View；正式产品 5 个入口激活 | type/measure/dimension/interval | `core.graph` | 专用链存在；图表/多度量/联动未完整 |
| Calendar | Registry 历史 8 个 View；当前定制 Action 0 | start/stop/color/scale | fallback | 无专业 Renderer |
| Gantt | 当前运行态和源码均未证 | start/stop/progress/resource/dependency | fallback | 无专业 Renderer |
| Activity | Registry 历史 10 个 View；正式产品 0 | QWeb template、field/action occurrence | `core.activity` | 构造链完整，产品入口和 L4 未证 |
| Dashboard | 外部 Dashboard 和行业自定义驾驶舱并存 | 无统一原生 dashboard parser | fallback | 统一接管缺失 |
| Hierarchy | 11 个专业 tree `js_class` | tree class -> semantic | 三个 Renderer ready | 已接入；业务递归/重算待 D02/D03 |

最重要的统计缺口：

- Pivot/Graph 当前前端从已加载页内 `records` 聚合：
  [`actionViewAnalysisContract.ts:91`](../../../frontend/apps/web/src/app/contracts/actionViewAnalysisContract.ts#L91)。
- `ActionView` 把 `records.value` 直接交给分析模型：
  [`ActionView.vue:1173`](../../../frontend/apps/web/src/views/ActionView.vue#L1173)。
- Odoo `read_group` 已存在于数据代理：
  [`api_data.py:579`](../../../addons/smart_core/handlers/api_data.py#L579)。

因此不能把“AnalysisPage 能显示若干行”视为 C01/C02 已通过。

### 2.4 哪些 Action 或 View 类型尚未接入？

明确未接入或只到部分接入：

- `ir.actions.report`：后端有报表契约适配，前端未消费 `report_name/report_type`。
- `ir.actions.client`：后端保留 tag，当前 SPA 没有通用 Odoo client tag Renderer；
  无 model 时进入 `ACT_NO_MODEL` 诊断。
- `act_window_close`：未发现通用结果消费。
- Calendar/Gantt：有后端 parser，但没有专用 Renderer，当前显示可读记录降级。
- Dashboard：有 profile 名称和行业自定义驾驶舱，但没有统一原生 dashboard parser/Renderer。
- Activity：专用链已注册，但当前正式 132 产品没有 Activity 入口，L4 未证。
- Pivot/Graph：Renderer 已注册，但统计口径、多度量和下钻未完成。
- 3 个正式 `account` Action：View Set 位于外部 Odoo 模块，必须运行态验证。

不得把下面的状态互相替代：

```text
源码中有 View != 已进入契约
契约中有 profile != Renderer 已正确消费
Renderer registered != Action route 已通
Action route 已通 != 权限和业务事务已验收
```

### 2.5 下一轮 B01-B06 应优先检查哪些真实业务入口？

按顺序：

1. `payment.request`：`menu_sc_user_payment_apply` →
   `action_payment_request_user_payment_apply` → `tree,form` + explicit Search。
   适合验证身份、完整 View Set、继承、Search、Form、List 和最终执行边界。
2. `project.project`：`menu_sc_project_project` →
   `action_sc_project_list` → `tree,kanban,form`。
   适合在 B02/B03/B05/B06 验证复杂继承、多关系、stat buttons 和多 View。
3. `project.task`：不在当前正式 132 菜单中，由项目 Form 的 `action_view_tasks`
   object button 进入 Odoo 原生任务 Action。B07 起重点验证 Kanban/Activity，
   不应在 B01 假定它有一个自定义 Menu。

## 3. 关键风险

| 编号 | 风险 | 证据 | 后续归属 |
|---|---|---|---|
| `NATIVE-A04-R1` | Pivot/Graph 是页内聚合，不是全范围 `read_group` 口径 | `actionViewAnalysisContract.ts:91`、`ActionView.vue:1173` | C01/C02、F02 |
| `NATIVE-A03-R1` | Report 只有后端适配，无前端消费 | `client_url_report.py:72`；前端无 `report_name` 引用 | C07/F07 |
| `NATIVE-A03-R2` | Client Action 没有通用 tag Renderer | `client_url_report.py:25`；`actionViewLoadGuardRuntime.ts:52` | C06/F05 |
| `NATIVE-A04-R2` | Calendar/Gantt/Dashboard 仍是显式 fallback | `actionSurfaceRendererRegistry.ts:42` | C03/C04/C06 |
| `NATIVE-A04-R3` | Activity ready 只证明构造链，无当前正式产品入口 | parser/profile/registry 源码；132 正式入口无 activity mode | C05 |
| `NATIVE-A04-R4` | 源 View 静态种类不等于运行态全量 | 797 个仓库 View vs 历史 Registry 2,113 个 View | B02/B03 |
| `NATIVE-A08-R1` | Action XMLID 不能单独标识入口 | 16 个 Action XMLID 被 34 个入口复用 | 所有后续任务使用 Menu+Action 复合键 |
| `NATIVE-A08-R2` | 运行时存在 27 个无 Action 叶子 | [原始证据第 25 行](evidence/navigation_capability_inventory_v1.json#L25) | A08/B01 运行态分类 |

## 4. 四层验收状态

| 层 | 状态 | 实际证据 |
|---|---|---|
| L1 Odoo 原生事实 | `passed_for_declared_scope` | 当前源码扫描；历史 Registry 只读快照；源码精确行号 |
| L2 后端契约 | `partial` | Action resolver、View parser、V2 profile 均有源码和单测；未逐入口证明无损 |
| L3 前端实际消费 | `partial` | Renderer registry、Analysis/Activity 页面和可达分支有代码守卫；未做真实 Action Route |
| L4 真实业务验收 | `not_run` | 本轮不做角色、真实数据、权限负例、浏览器、事务 |

`view_type_render_coverage.guard` 自己明确输出
`action_route=false`、`browser_delivery=false`，本轮没有把它升级成 L4 证据。

## 5. 执行与验证

| 命令 | 结果 | 可信边界 |
|---|---|---|
| `make agent.run.resume` | PASS | 解析到本专项 active run |
| `make verify.agent.ledger.unit` | PASS，18 tests | 治理登记一致性 |
| `make verify.agent.resume.unit` | PASS，58 tests | run 续跑约束 |
| `make verify.frontend.view_type_render_coverage.guard` | PASS，9 tests | 可执行渲染架构，不证明 Action Route/Browser |
| `make verify.frontend.view_type_contract_semantic.guard` | PASS | UI contract + normalizer 保留高级 View 语义标记 |
| `make verify.native_view.workflow_action_coverage` | PASS，3 + 8 tests | 40 个 View action registration；不是全业务验收 |
| `python3 scripts/audit/native_scene_inventory.py` | PASS | 生成 4 个机器清单和 1 份 Manifest |
| `python3 scripts/audit/native_scene_inventory.py --check` | PASS | 机器清单与扫描输入、结果哈希一致 |
| `python3 -m unittest scripts.audit.test_native_scene_inventory` | PASS，2 tests | 最小 fixture 的模型/菜单/Action/View 与漂移检测 |
| 静态 AST/XML 对账 | PASS | 当前 HEAD 的源码声明数量 |
| 正式 `product_menu_source.load_source()` | PASS | 132 个入口全部解析为唯一 native identity |

本轮未修改数据库，因此没有新的当前数据库 Model/Action/View Registry 查询。
运行态数量来自仓库内已归档的历史只读证据，报告已明确其 database、revision 和日期。

## 6. 本轮结论

第一轮研究已经证明：

1. Odoo 原生模型/菜单/Action/View 是一个可接管的产品资产层，不应重新开发业务页面。
2. “原生单入口直接交付”在当前正式产品中已经有 132 个候选身份和完整解析基础。
3. 当前真正的主要缺口集中在完整语义消费，而不是缺少菜单事实：
   - 全 View Set；
   - 权限和业务执行；
   - Pivot/Graph 全范围统计；
   - Calendar/Gantt/Dashboard；
   - Report/Client Action；
   - Activity 的真实入口与 L4。
4. 现阶段不需要新场景模型，也不应进入架构重构。
5. 下一步必须在 `payment.request` 和 `project.project` 上逐项执行 B01-B06，
   用证据决定保留、复用、补齐和退役。

本检查点到此停止。下一轮只启动 B01-B06，不提前做 E/F 架构裁定。
