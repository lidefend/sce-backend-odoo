# 收款返回路径：定位结论与通用导航运行时修复（2026-09-24）

来源缺口：`docs/ops/iterations/frontend_shared_foundation_gap_audit_20260909.md` → `G-F2-04 / B03`。
本记录只收口该缺口，不新建盘点报告；修改落在通用导航运行时，不涉及账务写入、过账或数据库升级。

## 层与边界声明

- Formal Product Layer：P0 平台通用产品。路由身份、历史栈模式和返回目标属平台机制，不是收款业务语义。
- Layer Target：`frontend/apps/web/src/router/index.ts`（全局 `beforeEach` 守卫）、
  `frontend/apps/web/src/app/recordFormActivityRoute.ts`（新增，创建表单活动身份注入）、
  `frontend/apps/web/src/pages/contractForm/useCreatedRecordNavigationRuntime.ts`（通用返回运行时）、
  `frontend/apps/web/src/pages/ContractFormPage.vue`（返回动作接线）。
- Module：frontend（web app 通用路由与表单运行时）。
- Standard vs User-Specific：平台通用规则；不写死收款路由，不对「前一业务页面」做特例判断。
- Why Here：`push/replace` 语义与历史条目存活属路由层；返回目标选择属通用表单返回运行时。
- Why Not Elsewhere：不在收款页面、action 配置或低代码层绕过；不新增业务特例分支。
- Blast Radius：所有走 `record`/`model-form` 创建表单入口的模型（合同、收款及其余正式入口），
  以及所有使用 `executeRecordFormReturn` 的表单页；定向测试覆盖创建注入与返回模式。

## 复现与根因（受管本地开发环境）

- 环境：`local.dev`（project `sc-local-dev`、database `sc_dev_demo`、nginx `18081`、odoo `8070`），管理员会话；
  路径 `/a/637?menu_id=338`（action 637 / menu 338，收款登记列表）→「新建」→ 返回。
- 现象（修复前）：`createUrl=/f/sc.receipt.income/new?menu_id=338&activity_page_id=…`，
  `backUrl=/s/workspace.home`，`returnedToReceiptList=false`；合同页与报表页两种来源都越过收款列表。
- 历史栈取证：`/f/…/new` 那次导航在 history 中是 `replace`（`receipt-chain-instr.json` / `receipt-chain-instr.png`）。

根因（单点、通用）：`ActionView.vue:1647 openCreateRecordWithBusinessCategory()` 用 `router.push` 打开
`/f/<model>/new`，而全局 `beforeEach` 守卫为「创建表单 + 无 `activity_page_id`」补注入时**返回了 `replace: true`**。
`vue-router@4.6.4` 的 `pushWithRedirect` 会把原导航的 `replace` 透传给守卫重定向的后续导航
（`node_modules/vue-router/dist/vue-router.mjs:1311` `assign({ replace: replace$1 }, …)`），
于是用户发起的 `push` 变成 `replaceState`：**来源收款列表条目被销毁**，表单自带的「返回」(`router.back()`)
不再回到收款列表，而落到真实前驱（`/s/workspace.home` 等）。

## 修改文件

| 文件 | 改动 |
|---|---|
| `frontend/apps/web/src/app/recordFormActivityRoute.ts`（新增） | `resolveCreateFormActivityRedirect()`：为创建表单注入 `activity_page_id`，**返回值不带 `replace`**，交回调用方保留自身导航模式（用户创建仍为 push，已 replace 的入口/首载仍收敛条目） |
| `frontend/apps/web/src/router/index.ts` | 守卫改为调用 `resolveCreateFormActivityRedirect(...)`，删除内联的 `replace: true` 重定向 |
| `frontend/apps/web/src/pages/contractForm/useCreatedRecordNavigationRuntime.ts` | 新增 `hasInAppReturnHistory(historyState)`（读 `router.options.history.state.back`）与 `resolveRecordFormReturnFallbackRoute(authorityRoute)`（只接受契约给出的以 `/` 开头的目标）；`executeRecordFormReturn` 增加可选 `hasInAppHistoryEntry`/`fallbackRoute`/`navigateFallback`，返回 `'dialog_cancel' \| 'history' \| 'fallback'`。内嵌弹窗取消与普通历史返回行为不变 |
| `frontend/apps/web/src/pages/ContractFormPage.vue` | 返回动作从 `currentRouteAuthority.value?.route`（即契约 `entry_target.route`）接线 `hasInAppHistoryEntry`/`fallbackRoute`/`navigateFallback`（`router.replace`）；无应用内前驱时走契约允许的回退入口 |
| `frontend/apps/web/scripts/record_form_return_navigation_test.ts`（新增） | 11 条定向用例 |
| `make/frontend.mk` | 新增 `verify.frontend.record_form_return.unit` 入口 |

未写死收款路由，未对前一业务页面做特例判断；回退目标只来自路由授权已声明的入口路由。

## 定向验证（非零，通过）

| 命令 | 结果 |
|---|---|
| `make verify.frontend.record_form_return.unit` | PASS，`record_form_return_navigation_test cases=11` |
| `npx vue-tsc --noEmit -p tsconfig.json`（`frontend/apps/web`） | 与基线**错误集完全一致**（31 项既有错误，逐条 diff `IDENTICAL ERROR SET`），本次未引入新错误 |
| `make local.dev.frontend` | 构建成功（41.59s），dist 已带修复上线 |

## 浏览器与历史栈验证（受管 `local.dev`，管理员会话，`errors: []`）

证据：`/tmp/pay-return-20260924/pay-return-verify5.json` 及 5 张截图。

| 场景 | 结果 |
|---|---|
| 合同页来源（`/a/609?menu_id=660` → 侧栏 财务中心/收款登记 → 列表 → 新建 → 返回） | `createNavigationMode="push"`，`backUrl` 等于收款列表 URL，`returnedToReceiptList=true`，`backListReady=true`，`backRows=1` |
| 报表页来源（`/a/699?menu_id=366` → 同链路） | `createNavigationMode="push"`，`returnedToReceiptList=true`，`backListReady=true`，`backRows=1` |
| 列表筛选+分页上下文（`/a/637?menu_id=338&search=SC-DEMO-INV-002&list_offset=0`） | `contextKept=true`，`createCarriedContext=true`，`backUrl` 含 `search`+`list_offset`，`returnedToReceiptList=true` |
| 直达新建 URL（`/f/sc.receipt.income/new?menu_id=338`） | `hasInAppBackEntry=false` → `backUrl=/a/637?menu_id=338`，`returnedToReceiptList=true`，`backListReady=true`（契约允许的回退入口，不是空白/无历史退出） |
| 新建有草稿离页保护 | 填入 `bill_no` → 弹「当前修改尚未保存…是否继续？」(`confirmShown=true`)，停留保留草稿；选「离开页面」→ `/a/637?menu_id=338`，`returnedToReceiptListWhenLeaving=true` |

说明：报表中心投影页（`sc.fund.daily.summary` `/a/699?menu_id=366` 等）在本数据集为 0 行，
其「收款登记」对象按钮不可点，故报表页来源经侧栏进入同一列表验证（两种来源的列表 URL 一致：
`/a/637…&menu_id=338&action_id=637`）；收款列表另已用等价直达 URL 单独验证。

## 残留与同批登记（不在本批修改）

- 报表中心投影页 0 行导致其行内对象按钮不可达：属「正式入口按职责验收」的数据/入口问题，登记不修。
- 显式创建入口在当前测试契约下仍 `not_available`：保持**未验收**，不并入完整创建闭环。
- many2many 失焦逻辑、无消费者的 `ScAutoComplete.vue`：留作后续任务，不扩大本批。

## 验收边界

- 本批只完成收款**返回路径闭环**：`批次验收完成`（定向 11 条 + 浏览器 5 场景通过）；
  `主线集成完成`与后续状态在 PR/CI/合并单独跟进，未合入前不宣称。
- 未纳入本批：账务写入/过账、数据库升级、显式创建闭环、其它正式入口的职责验收。
