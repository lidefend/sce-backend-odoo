# 付款申请黄金页面 Batch-C：真实提交与刷新闭环

## 边界

- Formal Product Layer：P0 通用动作执行/导航机制；P2 受管 demo 数据基线。
- Layer Target：Contract V2 action refresh policy、按钮结果导航归一化、Floorplan 主动作运行时、`smart_construction_demo` fixture。
- Standard vs User-Specific：通用前端与网关机制；仅验收数据属于 demo 基线，不写入行业或客户业务默认。
- Why Here：业务动作已由后端裁决可用性、确认和刷新策略；前端只执行并刷新，普通业务结果不能被网关伪装成导航动作。
- Why Not Elsewhere：不在付款申请页面按模型/状态推断，不放宽领域提交校验，不扩展 Lite、Native ledger、UI5 或 Scene 平行协议。
- Blast Radius：所有 Contract V2 runtime business action 的刷新策略，以及返回普通 dict 的 model button；通过动作归一化单测、前端桥接门禁、阻断态与真实提交浏览器旅程验证 containment。

## 产品结果

- Contract V2 保留 runtime business action 的 `refresh_policy`，并投影到同一后端方法的 Native occurrence。
- Floorplan 主动作在模型按钮返回普通业务数据或展示通知后仍执行权威 projection refresh。
- `normalize_odoo_action_result()` 只为真实 `ir.actions.*` 或显式 `entry_target` 生成导航；普通 `{warnings: ...}` 不再跳入伪造的 record entry。
- `demo_full` 增加可重复复位的 `DEMO-PR-FLOORPLAN-001`：真实支出合同依据、草稿态、提交动作可执行。
- 新增受管写入验收入口 `make verify.local.dev.payment_request.floorplan.submit`，覆盖 390px 固定主动作、确认、唯一 mutation、状态刷新、审计呈现与 fixture reset。

## 验证证据

- `python3 addons/smart_core/tests/test_navigation_entry_target.py`：PASS，7 tests。
- `python3 addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py`：PASS，70 tests。
- `python3 addons/smart_core/tests/test_execute_button_server_action_boundaries.py`：PASS，5 tests。
- `make verify.frontend.typecheck.strict`：PASS。
- `make verify.frontend.scene_component_bridge.unit`：PASS，38 + 52 cases。
- `make verify.frontend.scene_component_bridge.guard`：PASS，63 checks。
- `make verify.frontend.localized_display.unit`：PASS。
- `make local.dev.sync_demo` / `make local.dev.verify_demo`：PASS。
- `make local.dev.health`：PASS；project=`sc-local-dev`，DB=`sc_dev_demo`，dbfilter=`^sc_dev_demo$`。
- `make verify.local.dev.payment_request.floorplan.readonly`：PASS；阻断记录无伪主动作、无 mutation、390px overflow=0、第二模型复用通过。
- `make verify.local.dev.payment_request.floorplan.submit`：PASS；390px 主动作固定、业务确认、1 次 `execute_button`、HTTP 200、状态 `draft → submit`、10 个语义区、审计区可见、浏览器 error=0；随后 fixture reset 恢复草稿并通过 demo 完整性验证。

## 回滚

回滚本批次提交后执行 `make local.dev.sync_demo`，即可移除并重建本批次受管验收 fixture；业务规则与其他 demo 数据不受影响。
