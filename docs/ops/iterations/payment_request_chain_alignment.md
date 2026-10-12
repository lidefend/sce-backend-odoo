# 付款申请链路对齐（PAYMENT-REQUEST-CHAIN-ALIGNMENT）

Status: 批次验收完成（F1–F4 处理完毕，整链实机对账通过；未 commit/push/PR）
Baseline HEAD: `aeee27b0a6e30d5d3f6b9cd66953e4a999b48804`
Branch: `fix/payment-request-chain-alignment-20261013`
Runtime: `sc-local-dev` / `sc_dev_demo` / nginx `18081`（dist-dev），受管口令 `scdevpass`
前序确认：`docs/ops/iterations/payment_request_chain_confirmation.md`（PAYMENT-REQUEST-CHAIN-CONFIRMATION，已 completed）

## 裁定来源

Owner 授权按 F1 → F2 → F3 → F4 顺序执行，且要求：只修确认失败项，不扩探针框架，不放宽验收断言。

| 编号 | 层 | 处理 |
|---|---|---|
| F1 | P4 验证仪器 | 对齐 PR #525 官方模板落位（受管入口 `verify.local.dev.payment_request.full_chain`） |
| F2 | P0 前端渲染机制 | `extractListProfile` 契约未就绪时短路，契约缺失 `batch_policy` 声明不再误判为声明缺口 |
| F3 | P1/P0 契约治理 | `contracts/domain/payment-request.yaml` transitions 与运行时权威对齐 |
| F4 | 契约边界 | 只读字段不再对外声明 relation 新建权威 |

## 执行记录（回填）

### 候选身份（本批，全部未 commit）

- `SOURCE_SHA=aeee27b0a6e30d5d3f6b9cd66953e4a999b48804`
- `CANDIDATE_FINGERPRINT=360e4cf82c52ea4f6c153a9f384d347c477d7f6891d289b81a03a321f2b50e3e`
  （`python3 scripts/contract/complete_worktree_fingerprint.py --baseline <sha> --output .runtime/evidence/payment_chain_candidate_fingerprint.json`，8173 paths，`codex_complete_worktree_fingerprint/v1`）
- 受管入口：`make verify.local.dev.payment_request.full_chain`

### F1 — P4 验证仪器对齐官方模板（PR #525 后落位）

仪器 `scripts/verify/local_dev_payment_request_floorplan_submit.mjs` 相对 #525 的落位漂移已按官方渲染事实修正：

- 新建入口归 `[data-list-surface-header]`，页头 `#actions` 不再承载列表操作（`ActionView.vue` `standardListOperationsInCard`）。
- 创建/编辑面指标作用域改 `CanonicalNativeFormSurface`（`[data-native-contract-structure]`），断言不再依赖已退役的 `[data-object-task-page]`/`[data-floorplan-region]`。
- 返回列表动作改契约定名 `[data-form-secondary-action="return-list"]`。
- 业务分类"同值不触发切换"前置假设按现产品默认分类事实修正。
- 只读字段不再断言 relation 新建权威（与 F4 同源）。

`full_chain.mjs` 提交选择器对齐官方 primary 槽位规则（可编辑记录上唯一强调 primary 是保存动作，业务"提交审批"以 enabled 直接动作携带契约身份下发）：

```
- [data-product-primary-action][data-action-method="action_confirm"][data-action-enabled="true"]:visible
+ [data-action-method="action_confirm"][data-action-enabled="true"]:visible
```

权威来源：只读探针 `.runtime/diag/execution_action_authority.mjs`（`action.action_confirm` 的 `enabled/allowed` 官方裁决 = true）。

### F2 — P0 前端投影就绪门控

`frontend/apps/web/src/app/action_runtime/useActionViewContractShapeRuntime.ts`：

- `extractListProfile` 在契约未就绪（`!store`）时短路返回 `null`，不再于对象字面量中提前求值 fail-closed 断言（此前导致消费 computed 被缓存为 `undefined`，契约返回后再次读取时 `.map` 崩溃）。
- `batch_policy` 仅在 `listProfile` 显式声明时构造；未声明属正常，声明但不完整仍 fail closed。

回执：`verify.frontend.contract_shape_projection.unit` PASS cases=5。

### F3 — 契约治理：payment.request transitions 与运行时权威对齐

`contracts/domain/payment-request.yaml`：

- 补齐 `submit`（from 增 `rejected`）、新增 `reverse_payment`（`done→approved`），`done` actions 增 `reverse_payment`，`approve_pass` from 增 `submit`（未配置审批链时自动通过路径）。
- `notes` 显式声明：本文件是领域声明（对账/生成用），**非运行时权威**；运行时"状态→可用动作"由 P1 `ScWorkflowContractService.PROFILE_BY_MODEL['payment.request']` 投影，转移合法性由 ORM `ScStateMachine.PAYMENT_REQUEST_TRANSITIONS` 与模型方法执行；归属细则见 `docs/contract-runtime-state-ownership.md`。

回执：`verify.contract.structure_lock` PASS。

### F4 — 契约边界：只读字段不声明 relation 新建权威

`addons/smart_core/app_config_engine/services/assemblers/page_assembler.py`：`descriptor.readonly is True` 时 `can_create=False`（保留查看/搜索入口）。同 payload 不再自相矛盾。

回执：`verify.frontend.relation_entry.contract_guard` Ran 14 tests OK。探针确认 `payment.request.funding_baseline_id → can_create:false / create_mode:disabled / reason_code:NO_VISIBLE_ACTION`。

### 根因（本批收敛的写入链阻断）

1. **夹具缺付款方快照（run1 保存超时根因）** — `step_payment_request_floorplan_demo.py` 未携带 `legacy_payment_account_name/no`；执行面 create context（`payment_request.py:1592-1593`）与 `_payment_request_values`（`payment_execution.py:386-387`）以 legacy_* 为载体，`_check_account_contract_or_raise` 要求付款三元组完整，缺失导致前端 REQUIRED precheck 阻断保存。修复：夹具补 `legacy_payment_account_name="演示付款单位基本户"` / `legacy_payment_account_no="DEMO-PAYER-0001"`（官方 P0 模式同源 `test_p0_state_closure.py:390-470`）。非前端/契约缺陷。
2. **提交选择器与官方 primary 槽位规则不一致（run2 count=0 根因）** — 见 F1。
3. **前端投影在契约边界缺就绪门控** — 见 F2。
4. **域契约 transitions 与运行时权威漂移** — 见 F3。
5. **只读字段仍声明 relation 新建权威** — 见 F4。

### 夹具漂移修复（本轮附带的独立事实，非 F1–F4）

- **DEMO 结算发票快照漂移**：`scripts/ops/repair_demo_settlement_invoice_snapshot.py` + `make/dev.mk` 目标 `local.dev.demo.settlement_snapshot.repair` + `scripts/ops/odoo_shell_exec.sh` 白名单；已 apply（id 25 `invoice_amount NULL→280000.0`，受管只读回读收敛）。
- **demo seed 与 #525 状态守卫冲突（独立 finding，未修，待裁定是否单开专题）**：`demo_addons/smart_construction_demo/seed/steps/step_60_attachments_demo.py:126-130` 直写 `state`（`done`/`review`/`draft`），而 `addons/smart_construction_core/models/support/document_center.py:114`（create）与 `:119`（write）要求"资料状态必须通过办理动作产生"。#525 引入守卫后该 demo step 必红（`demo.ci`）。本批 F1 改用夹具域复位（`local.dev.reset_payment_request_fixture`）以**不掩盖**该缺陷，未在本批修复。需排查 demo seed 全链受 #525 影响的直写处。

### 验收（受管入口实机）

`make verify.local.dev.payment_request.full_chain`（run3，`EXIT=0`）：

- F1 floorplan submit：`record=2880 transition=draft->submit mutations=1`。
- 审批链：fin1→wutao→fin_mgr→demo_role_executive，终态 `approved/validated`，review_ids=[1300..1303]。
- 执行面：generate execution 权威目标；save succeeds（executionId=614/615）。
- 执行提交（policy id=10 `payment_execution_optional_approval` approval_required=false mode=none）→ 直接 confirmed。
- 收款事实：execution=paid、request=done、`paid_amount_total=10000`、`unpaid=0`、posted ledger=1×10000；重复提交被 paid-state guard 显式拒绝（403 `duplicate_payment_contract_state_guard`）。
- 390px 无横向溢出。
- 对账终态：`authoritative request/execution/ledger facts reconciled`；`completed payment facts retained as immutable acceptance history`。

制品：`artifacts/playwright/local-dev-payment-request-full-chain/summary.json`（`pass=true`，61 assertions；唯一 error/failed_request 为预期 403 guard）。

### 阶段结论

- 批次验收：**完成**（scoped 改动 + 定向测试 + 整链实机对账通过）。
- 主线集成：**未完成**（未 commit/push/PR）。
- 版本发布 / 产品交付：**未完成**（本批不涉及）。
- 剩余失败（本批外，勿混入）：`verify.contract.lint` 49 项；`test_frontend_quality_safety_domain_rollout.py:123` 陈旧 res.users 断言；`wutao` 访问 `/a/809?menu_id=559` 403；demo seed 状态守卫冲突（独立 finding）。
