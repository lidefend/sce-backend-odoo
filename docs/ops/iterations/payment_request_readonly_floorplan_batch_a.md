# 付款申请黄金 Floorplan Batch-A

## 1. 本轮变更

- 目标：把付款申请真实只读详情接入 `Contract V2 → Canonical Render Model → Product Floorplan → 语义组件 → TDesign`，并以第二个真实模型证明复用。
- 完成：
  - 生产表单 Host 正式调用 `composeCanonicalFormFloorplan()`；具有稳定语义角色的只读页面进入 Object Summary、Current Task、Risk、Context、Relation、Activity/Audit 和 Canonical Action Bar。
  - 付款申请列表使用权威 display field，空态在有权限时提供唯一“新建”动作；真实记录首屏显示摘要、阻断原因和唯一主动作“提交审批”。
  - `sc.payment.execution` 使用同一 Floorplan/TDesign 链路完成第二模型复用验证；过期的 generated form contract 通过 `17.0.0.132` 幂等迁移归档。
  - 首页快捷入口以菜单树的真实目标身份覆盖同路由旧标题，消除目录标题与后代页面目标错配。
  - TDesign 成为正式默认，Native 仅作加载失败和非语义页面兼容回退；普通用户不再看到或选择 kit/driver。
  - 用户界面移除 `runtime_status`、`payment_entry`、`direct delivery`、legacy ID 和 kit 名称等技术文本。
- 未完成：仓库级 Scene 角色矩阵基线仍独立失败，四个角色的 `scene_count=1`，低于既有阈值 30；不属于本专题，未通过扩契约或修改 Scene 基线掩盖。

## 2. 影响范围

- Formal Product Layer：P0 通用前端呈现机制；P1 仅承载施工行业付款/实付登记的标准契约语义与旧契约归档。
- Layer Target：frontend renderer/presentation、`smart_core` Contract V2 action modifier hydration、`smart_construction_core` 标准付款表单契约。
- Standard vs User-Specific：平台通用机制 + 施工行业标准；无客户特例、无模型名/中文标签/角色分支。
- Why Here：Floorplan 只组织 Canonical 语义；权限、阻断、状态和动作最终结果仍由后端契约裁决。
- Why Not Elsewhere：未创建 Lite/Scene 平行协议，未扩 Native capability ledger，未发展 UI5 产品线，未把供应商信息写入契约。
- Blast Radius：语义只读表单、付款申请列表/详情、实付登记详情、角色首页快捷入口；创建/编辑和无语义角色页面仍走兼容渲染。
- 启动链：消费 `system.init` 与 `ui.contract.v2`，没有新增 public intent。
- contract/schema：没有新增 Contract V2 变体；调整现有 P1 表单内容和 P0 动作最终 modifier 投影。
- 路由：不创建新路由；修复首页同路由入口的身份对齐。

## 3. 风险

- P0：仓库级 restricted 门禁被既有 Scene 角色矩阵阻断；本批以定向 Contract V2、后端测试和真实浏览器旅程形成可信证据，不能宣称全仓门禁通过。
- P1：Native 兼容路径仍保留，后续非语义页面不会自动获得黄金 Floorplan。
- P2：UI5/Native 仍作为注册适配器存在，只暂停产品化扩张，未做破坏性删除。
- 缓解：Floorplan 仅在 Canonical 模型具备决策语义时启用；TDesign 加载失败自动回退 Native；数据库迁移只归档精确 XMLID。

## 4. 验证

- `make verify.frontend.localized_display.unit`：PASS。
- `make verify.frontend.scene_component_bridge.unit`：PASS，38 + 52 cases；Python 辅助测试 13 + 7 cases。
- `make verify.frontend.scene_component_bridge.guard`：PASS，63 checks。
- `python3 addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py`：PASS，69 tests；同时证明 Native modifier 可恢复权威动作且不会覆盖 runtime business unavailability。
- `make verify.frontend.typecheck.strict`：PASS。
- `make verify.frontend.build` / `make local.dev.frontend`：PASS。
- `make local.dev.upgrade MODULE=smart_construction_core`（受管显式升级变量）：PASS。
- `make local.dev.test ...test_payment_form_exposes_controls_and_task_sections`：PASS，1 selected test，0 failed。
- `make local.dev.sync_demo` / `make local.dev.verify_demo`：PASS。
- `make local.dev.health`：PASS，project=`sc-local-dev`，DB=`sc_dev_demo`，dbfilter=`^sc_dev_demo$`。
- `make verify.local.dev.payment_request.floorplan.readonly`：PASS；10 个语义区、1 个 enabled primary、390px overflow=0、第二模型复用通过、业务指纹不变。
- `make verify.restricted`：FAIL（独立既有门禁）；首个失败为 Scene 四角色 `scene_count 1 < 30`。此前 Contract V2、前端 typecheck/build 均 PASS。
- `make codex.snapshot.export`：FAIL（独立既有快照账号基线）；`demo_role_pm` 无 `payment.request` 读取权限，失败导出的部分生成物已撤回，旧目标快照由工具保留。
- `make verify.backend.guard`：FAIL（同一 Scene 基线，`scene count 1 < 4`）；此前边界、controller、frontend intent 等守卫均 PASS。

## 5. 产物

- E2E：`artifacts/playwright/local-dev-payment-request-floorplan/summary.json`。
- 截图：同目录下 `workspace-home-desktop.png`、`payment-request-list-desktop.png`、`payment-request-list-empty-desktop.png`、`payment-request-desktop.png`、`payment-request-390.png`、`payment-execution-reuse-desktop.png`。
- 可恢复快照：`artifacts/local-dev/snapshots/20260821T183427Z/`。
- Restricted 失败证据：`artifacts/backend/scene_base_contract_source_mix_role_matrix_report.json`。
- Backend guard 失败证据：`artifacts/backend/scene_contract_field_schema_report.json`。

## 6. 回滚

- 代码：回退本批 P0 Floorplan/语义组件投影和 P1 `17.0.0.132` 契约归档提交，再通过受管模块升级与前端构建恢复。
- 数据：必要时使用 `artifacts/local-dev/snapshots/20260821T183427Z/` 按受管 local.dev 恢复流程回退。
- 兼容：Native renderer 未删除，可作为非语义页面与 TDesign 加载失败时的安全回退。

## 7. 下一批次

- 本专题产品目标已完成，不继续扩付款契约、Native ledger、UI5 或 Lite Contract。
- 独立治理批次应修复 Scene 注册/角色矩阵和全量快照账号基线；该工作需单独授权，不能混入付款黄金页面。
