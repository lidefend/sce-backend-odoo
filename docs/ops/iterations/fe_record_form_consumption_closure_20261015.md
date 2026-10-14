# FE-RECORD-FORM-CONSUMPTION-CLOSURE（2026-10-15）

目标：收口核心记录表单旅程（J12/J13/J14）暴露的契约消费缺陷，并把验收夹具的 ORM
冻结车道接回唯一受管入口。所有改动只落在 P0 通用消费层与 P4 验收车道接线，不新增
前端业务推断，不为夹具放开产品守卫，也不改动已交付契约或 schema。

## 1. 基线

- 分支：`fix/fe-record-form-consumption-closure-20261015`
- 基线：`main` `9c3851d323a7a0c639d3faab9548d98bcc99d873`
- 验收身份：受管 `make acceptance.frontend.core_record_form.journeys` 自选运行时
  profile（`sc-fe-r2-p1-01` / `sc_frontend_acceptance` / 后端 18082 / 前端发布态 5175）；
  执行器不手工拼 compose、数据库、端口或凭据。

## 2. 已定位的三处缺陷

### 2.1 旅程绑定了「已声明但未交付」的入口身份（P4 夹具）

finance 只读 intent 探针（`fixture_role_finance`，uid 19，company 4）事实：

- `system.init` 的 `data.navigation.nav` 只投递「系统菜单 / 工作台 / 财务中心(8) /
  税务中心(6)」，**不含结算中心**。
- `data.navigation.route_authority`：primary=15、role_home=1、contextual=20、admin=0、
  **denied=33**、menu_containers=1。
- menu 362 / action 762（`menu_sc_settlement_order`）落在 `denied_actions`：
  `route_kind=DENIED`、`allowed_operation=none`、
  `source=role_surface.denied_menu_xmlids`、`reason_code=PRODUCT_ENTRY_NOT_VISIBLE`。
- `role_surface.menu_xmlids` 含 `menu_sc_settlement_center`，`primary_menu_xmlids` 45 条含
  `menu_sc_settlement_order`，`exposure_policy_declared=true`。
- **决定性**：产品政策面 `sc.product.policy`（product_key=`construction.standard`，
  version v1，state stable）共 90 条 menu rows，**完全不含结算中心/结算单**；
  `sc.settlement.order` 只出现在合同中心的收入/支出/总包结算条目里。付款申请在财务中心
  有已交付入口 `menu_sc_user_payment_apply`（878/559）。

结论：结算单是「角色面声明了、交付面未投递」的条目，后端按设计 fail-closed 记
`PRODUCT_ENTRY_NOT_VISIBLE`，前端守卫 `/access-denied` 是**正确**的。所以修复方向是
把旅程绑到已交付的付款申请入口，**不是**改产品守卫，也**不是**在前端补偿。

因此 `scripts/verify/frontend_core_record_form_journeys.mjs` 的 `openLegalPaymentCreate()`
不再从 `recordRoute(TARGETS.settlement)` 进入，改为直接打开已交付入口
`/f/payment.request/new?action_id=…&menu_id=…`，并在注释里写明绑未交付身份即为被拒根因。

### 2.2 保存成功后 `canSave` 抖动把成功回执判成换页（P0 消费层）

`useRecordFormActions.ts` 的 `boundSurfaceKey()` 把 `canSave` 计入 surface 身份。保存
自己的写后场景刷新会重读契约与记录，`canSave` 在一次刷新里可见地抖动 false 再 true，
于是这次保存「顶替了自己」：写入已落库，但成功回执被丢弃，用户看不到确认。

修复：surface 身份只承载**身份**（模型/记录/活动/路由/身份与 owner/会话上下文），
`canSave` 从键里移除；它仍在每个操作证明所有权的地方被显式校验，只是不再当作换页证据。

### 2.3 更正聚焦落到配置控件而不是取值控件（P0 消费层）

`applyFocus()` 用 `querySelectorAll('input, select, textarea, button, [tabindex]')` 后取
文档序第一个可用控件。金额字段容器由 `sc.value.money` →
`ProfessionalBusinessValueControl` 渲染，容器内先出现的可能是「币种选择」这类**只配置
取值**的按钮，取值 `input` 在后，于是错误汇总点击后焦点落在按钮上，用户无法直接改值。

修复：新增与 DOM 无关的更正控件优先级规则（`validationErrorPosition.ts` 的
`correctionControlRank` / `selectCorrectionControl`），把「取值控件（text/number/
textarea/select/勾选）」排在「配置控件（按钮、仅 tabindex 的容器）」之前，同一档内保留
文档序；`formValidationFocus.ts` 的 `applyFocus` 改为按该规则选择，并用
`isControlUsable` 优先于「仅未禁用」。

## 3. 验收车道接线

`verify.acceptance_fixture.execution_freeze.orm` 原先转到 `local.dev` 上按 tag 跑
`smart_construction_acceptance_fixture`，但该模块在 `forbidden_implicit_modules` 里，
**没有任何产品/demo profile 安装它**，选标签匹配 0 条测试却仍然 exit 0 —— 一张证明不了
任何事情的绿色回执。现在该车道改转 `acceptance.frontend.fixture_orm`，在模块真实存在的
验收载体上执行，并对「无 summary」「0 tests」「失败数非 0」fail-closed。
`scripts/verify/test_coverage_registry.yaml` 的登记同步改为新入口。

## 4. 待续

- J12 / J13 / J14 合并重跑与报告。
- 已知既存红项（零金额草稿被允许、required summary 不出现）不属于本批，不顺手修。

## 5. 本轮结果（本地批次证据）

全部经受管入口执行，均为非零测试计数。

| 检查 | 入口 | 结果 |
|---|---|---|
| 契约错误业务归属与聚焦 | `make verify.frontend.contract_error_business_ownership.unit` | PASS 100 例 |
| 保存失败恢复 | `make verify.frontend.contract_form_save_failure_recovery.unit` | PASS 34 项断言 |
| J13 必填语义 | `make verify.frontend.j13_required_value_semantics.unit` | PASS 110 例 |
| 夹具执行冻结（ORM） | `make acceptance.frontend.fixture_orm` | PASS tests=3 failed=0 |
| 核心记录表单旅程 | `make acceptance.frontend.core_record_form.journeys` | PASS J12 J13 J14 |

旅程报告 `artifacts/frontend-professional/fe-pro-03/journeys/report.json`：

- J12：`dirty_guard` / `cancel_retains_input` / `save_and_reload` 全通过。
- J13：`required_error_focus` / `conflict_retains_input` / `authoritative_reload` 全通过；
  `authority_amount=20.00`、`retained_amount=21.00`。
- J14：故障反馈、未重输重试、清理回读全部通过。

### 5.1 J13 断言修正的依据

首次重跑暴露 `J13 conflict did not retain local input`。只读事实：金额由
`sc.value.money` → `ProfessionalBusinessValueControl` 渲染，`formatMonetaryInputValue`
按币种精度 `toFixed(scale)`，所以用户输入 `21` 在控件里的显示值是 `21.00`。冲突提示
本身写明「当前页面保留了你的输入」，且报告记录的 `authority_amount=20.00` 与
`retained_amount=21.00` 说明**用户的修改确实被保留**。因此这是**旅程断言的字符串比较
缺陷**，不是产品缺陷：断言改为数值比较，并额外要求「保留值 ≠ 权威值」，这样一旦页面
真的把用户输入替换成权威值，断言仍然失败。

### 5.2 聚焦缺陷的反例验证

`applyFocus` 的旧实现在 `amount-input` 用例上聚焦 `currency-button`，100 例测试会失败
（实测 `AssertionError: a currency picker button never receives the value error focus`，
实际值 `currency-button`、期望值 `amount-input`）；打上优先级规则后通过。

## 6. 状态口径

- 批次验收：进行中（本地五条检查通过，等待冻结点门禁与远端四项必需检查）。
- 主线集成：未开始。
- 版本发布：未开始。
- 产品交付：未开始，且本批不主张。
