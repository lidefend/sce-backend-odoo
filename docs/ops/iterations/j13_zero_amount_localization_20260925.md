# J13 零金额分歧定位（2026-09-25）

状态：**已修复并定向/浏览器验收通过**（修复提交 `64c326c4`，第 11 节；收口提交 `5455ca00`，第 12 节）。
**2026-09-27 三态实测已完成裁决**（第 10 节）：清空金额未被前端必填拦截、与 2026-09-24 浏览器
记录一致；第 3.1 节冲突解除，第 3 节的代码推导（清空应被拦）被实测推翻，第 7 节的 `not_run` 已作废。
根因确认为通用校验字段表静默退化为「契约字段映射前 16 个」，必填金额不在其中。
基线：实时 Gitee main `28e4ddffd0f55758382019249249d2f0689d04f7`（含已合入 PR !20），
分支 `audit/j13-zero-amount-localization-main`。
ORM/契约探针采集于 `827fad4bd927c8be22bf940d24937bb2c07f4796`（当时 main，为 `28e4ddff`
的祖先，相距 7 个提交）。两基线之间仅改动 `project_context.py`、
`local_dev_project_profile_write_*`、工程收敛报告与新专题文档；**不触及本文引用的
`payment_request.py`、`valueUtils.ts`、`saveRecordHelpers.ts`、`useRecordFormState.ts`、
`formSection.mapper.ts`、`unified_page_contract_v2_assembler.py`、`ui_contract_v2.py`**，
故探针结论按原身份携带，未重跑。
本文件为 J13 的唯一当前定位记录；结果同时登记到
[frontend_shared_foundation_gap_audit_20260909.md](frontend_shared_foundation_gap_audit_20260909.md)
缺口 `G-F1-10` 与批次记录
[business_entry_surface_normalization_batch_1_20260913.md](business_entry_surface_normalization_batch_1_20260913.md)。
不新建第二套盘点报告。

## 1. 被测旅程与断言

定义在 `scripts/verify/frontend_core_record_form_journeys.mjs::j13()`（约 166–202 行），390px、
角色 `fixture_role_finance`、结算页「新建付款申请」：

1. 清空 `[data-field-name="amount"] input` → 点「保存草稿」→ **断言必须出现**
   `role=alert` 且含标题「请检查以下内容」→ 点首条错误 → 断言焦点落在金额输入框。
2. 转到既有记录，改金额 → 注入一次写冲突 → 断言本地位保留、拦截计数为 1。
3. 点「加载最新数据」→ 确认 → 断言输入框回到权威值。

第 2、3 步属既有 409 冲突保留与权威重载链，不是零金额问题；本定位只覆盖第 1 步涉及的
「必填 + 金额 + 0/空值」语义。

## 2. 字段与服务端契约（实测）

| 项 | 值 | 来源 |
| --- | --- | --- |
| 字段名 | `payment.request.amount` | `addons/smart_construction_core/models/core/payment_request.py:419` |
| 类型 | `fields.Monetary(required=True, currency_field='currency_id')` | 同上 |
| 必填声明来源 | 业务分类策略 `finance.payment.apply.pay` 的 `required=("business_category_id","project_id","amount")` | `addons/smart_construction_core/models/support/business_form_policy_templates.py:455` |
| 契约信号 | 容器节点 `fieldInfo.required=true`、`ttype=monetary`；widget `fieldDescriptor.required=true`、`readonly=false`；`componentKey=sc.value.money` | 真实 `UiContractV2Handler` 容器树，归档 `local-postfix-j13-containertree-amount-node.txt` |

**ORM 行为（本地 `sc_dev_demo`，savepoint 内 create 后回滚）**：`''`、`False`、`0.0` 三种输入
全部 create 成功、落库 `0.0`、`state=draft`；只有**完全省略该字段**才触发
`NotNullViolation`。即「金额为 0 的草稿」在当前后端契约中是合法对象，不是写入失败。

归档：`local-postfix-j13-orm-required-monetary-probe.{py,txt}`、
`local-postfix-j13-contract-required-signal-probe.txt`。

## 3. 输入 0 / 空值 / 未输入 的实际走向

| 阶段 | 输入 `0` | 清空输入 | 从未触碰 |
| --- | --- | --- | --- |
| 控件 `@update:model-value` | `numericValue('0')` → `0` | `numericValue('')` → `null` (`ProfessionalBusinessValueControl.vue:113`) | 不触发 |
| 事件归一化 | `normalizeText(0)` → `'0'` | `normalizeText(null)` → `''` (`fieldChange.dispatcher.ts:10`) | 不触发 |
| 草稿 `setTextField` | `formData.amount='0'` | `formData.amount=''` (`useRecordFormState.ts:130`) | `undefined` |
| 提交载荷 `collectWritableValues` | `normalizeContractFieldValue` → `parseNumeric('0')=0` → 货币取整 → `0` | `parseNumeric('')=null` → **`false`** (`valueUtils.ts:75-77`) | 同清空 → `false` |
| 必填判定（保存路径） | `isRequiredFieldEmptyByType(0,'monetary')` → **不空** | `false` → **空** | `false` → **空** |
| 结果 | 放行 → 提交 `amount=0` → 后端存 `0.0`/draft | 前端拦截 | 前端拦截 |

保存路径使用 `isRequiredFieldEmptyByType`（`saveRecordHelpers.ts:136`，创建态按
`isWritableFieldVisible` 取全部可写字段，`saveRecordHelpers.ts:87`）。

> 2026-09-27 更新：本段是代码推导，**已被第 10 节实测推翻**——三态保存均未被前端必填段拦截。
> 保留原文以记录推导过程与错误位置。

按代码推导：**清空与未输入应被前端必填校验拦下**，错误摘要标题确实是「请检查以下内容」
（`ScErrorSummary.vue:2` 默认 `title`；`ProductFormErrorSummary.vue:6`）；显式 `0` 则前端放行、
后端接受。**没有任何一层把 0 改写成空值。**

### 3.1 该推导与既有浏览器记录冲突（2026-09-27 已裁决：实测支持既有浏览器记录）

`docs/ops/iterations/onchange_draft_identity_roundtrip_20260924.md:81-85` 记录了**实际观察**：
J13 第一步清空金额后点「保存草稿」，**产品允许该草稿保存**（状态草稿、金额 `0.00`），因此
`请检查以下内容` 断言必然超时失败；旁证是 acceptance 库存在 2026-08-24 由同一路径产生的
`PRQ2600326`（金额 `0.00`）。

这与上表的代码推导相反（推导为拦下）。可能原因至少有三类，本轮**无法判定**属于哪一类：

1. 该记录采集时代码与 `28e4ddff` 不同，之后 `valueUtils.ts`/`saveRecordHelpers.ts` 行为已变；
2. 状态实际值不是 `false`/`''`（例如 `collectWritableValues` 在该 action 下未包含 `amount`，
   或该节点被 `isWritableFieldVisible`/`readonly` 过滤掉，使必填分支根本未覆盖它）；
3. 创建态保存存在绕过 `validateBeforeSaveRecord` 必填段的路径。

本地无法裁决：受管环境 `payment.request` 入口被授权层拒绝（第 7 节），表单不渲染，无写入可用。
**裁决方法（下一步）**：在能渲染该表单的环境打开 `/f/payment.request/new`，拦截 `api.data`
写入（0 次真实写入），观察清空金额后点「保存草稿」是否发出写请求 —— 发出即证明未拦截并直接
复现 `PRQ2600326` 的成因；未发出则证明拦截并推翻旧记录。

## 4. 真正的语义分歧（两条必填判定互相矛盾）

| 判定函数 | 位置 | 对 `0` 的结论 | 使用路径 |
| --- | --- | --- | --- |
| `isMissingRequiredValue` | `valueUtils.ts:5-13`（`:8` `!isFinite(v) \|\| v<=0`） | **视为缺失** | 场景预检 `collectSceneValidationPrecheckErrors`（`useRecordActionPresentation.ts:235`），只遍历 `sceneValidationRequiredFields` |
| `isRequiredFieldEmptyByType` | `valueUtils.ts:31-40`（`:37` 只认 `false/null/undefined`） | **视为已填** | 实际保存必填校验 `saveRecordHelpers.ts:132-137` |

`sceneValidationRequiredFields` 取自 `sceneReady` 契约（`useRecordContractSemantics.ts:94`）；
本环境该 action 无 `scene_key`/intake，故该集合为空，第一条判定当前不触发，矛盾处于休眠状态。
一旦该 action 接入 scene-ready 契约，**同一次保存会上报/放行相反结论**。

已排除的假设：**不存在 `false` 被渲染成 `0.00` 的控件层缺陷。**
`resolveTemplateInputValue`（`formSection.mapper.ts:278-280`）在 `raw === false/null/undefined`
时先返回 `''`，再交给 `formatMonetaryInputValue`（`:141`）；因此清空/未触碰显示为空，
只有真实 `0` 才显示 `0.00`。此项为代码级判定，未在运行时复现，故不作为缺陷登记。

## 5. 「金额必须大于 0」的来源核对

「金额必须大于 0」只出现在**办理前置条件提示**，不是保存校验：
`docs/ops/iterations/onchange_draft_identity_roundtrip_20260924.md:81-85`。旁证：acceptance 库存在
`PRQ2600326`（金额 `0.00`）。当前没有找到把「草稿金额 > 0」声明为保存约束的契约或策略。

## 6. 产品决策与最小修改路径

先做两件事，再定规则：

0. **裁决第 3.1 节的冲突**（清空金额到底被不被拦）。这决定 J13 断言是否本身就不成立，
   未裁决前不应改任何校验代码。
1. **裁定草稿 0 的语义**。J13 第一步把「清空必填金额 → 保存草稿必须被拦」当作既有产品规则，
   但后端契约只要求金额非 NULL、不要求大于 0，且已存在金额 `0.00` 的真实单据 `PRQ2600326`。

规则确定后再改代码：

- **若确认「草稿允许 0」**（与当前后端、与 `PRQ2600326` 一致）：
  不改产品代码。把 J13 第一步改成「输入/保留 `0` → 保存成功 → 权威回读金额为 0 且仍 draft」，
  必填错误聚焦改用真正为空的必填字段（如未选择 `project_id`），或由契约显式声明该字段的
  `required` 语义。同时统一两条判定：让 `isMissingRequiredValue` 对数字不再把 0 当缺失
  （`valueUtils.ts:8`），避免 scene-ready 接入后出现相反结论。
- **若确认「草稿必须大于 0」**：
  在 **P1 模型/策略层**加约束（`payment.request.amount` 或其业务分类策略），并同步前端
  required 语义与文案；不得只改前端，否则前后端对同一对象结论不同。
- **无论选哪条**，`valueUtils.ts` 的两条判定必须收敛为同源定义（一条空值规则），
  并以 0/空/未输入三态的非零定向测试固定。

最小修改面（第二种情况下）：`valueUtils.ts`（1 处判定定义）＋ 对应定向测试；
若需要后端约束，再在 P1 策略/模型层补 1 处，不改写契约 schema、不动数据库结构。

## 7. 浏览器执行结果：`not_run`（2026-09-25；2026-09-27 已在 dist-dev 静态服务上实测，见第 10 节）

本轮**实际尝试过**执行 J13 第 1 步，受环境能力阻断，未取得页面结论：

1. `127.0.0.1:5176`（J13 harness 依赖的 Vite 入口）本轮无监听：
   `browser-trace-attempt.mjs` 三例均以 `ERR_CONNECTION_REFUSED` 失败。
2. 本地存在的是 `127.0.0.1:18081`（已构建产物 + nginx）。该入口**可登录**：
   `admin`/`pm1` 均通过 `SC_DEMO_USER_PASSWORD` 完成了 `login`+`system.init`（HTTP 200）。
3. 但 `payment.request` 入口在本地受管环境下被授权层拒绝，表单始终不渲染：

   | 路由 | 结果 |
   | --- | --- |
   | `/f/payment.request/new?action_id=809` | `/access-denied`，`reason=NAVIGATION_AUTHORITY_DENIED`（`pm1` 与 `admin` 均相同） |
   | `/f/payment.request/new` | `/access-denied`，`reason=PERMISSION_DENIED` |
   | `/f/payment.request/1000` | `/access-denied`，`reason=PERMISSION_DENIED` |

   `[data-field-name]` 计数为 0，因此「清空金额 → 保存草稿」无法观察。
4. J13 harness 本身还需要 `DB_NAME=sc_frontend_acceptance`、
   `SC_ACCEPTANCE_FIXTURE_PASSWORD`、`FRONTEND_FINANCIAL_WORKSPACE_TARGETS_JSON` 与
   `fixture_role_finance`；本地数据库列表中无 `sc_frontend_acceptance`，该角色也不存在。

让表单在本地渲染需要改动角色/导航授权配置，属于新增环境与授权权威，不在本任务范围，故停止。

**因此 J13 第 1 步在浏览器中是 pass 还是 fail 仍为 `not_run`，本轮只给出代码级链路结论（第 3、4 节）。**
结论与证据：`local-postfix-j13-browser-entry-check.txt`、`j13-step1-diagnostic.json`、
`j13-route-scan.json`、`j13-step1-browser-probe.mjs`、`j13-step1-diagnostic.mjs`、`j13-route-scan.mjs`、
`browser-trace-attempt.mjs`。已完成 1 次 J13 断言尝试（`j13-step1-browser-probe.mjs`），
因第 3 点未进入断言阶段，不记为 failed 断言，记为环境阻断。
- 前端 `frontend-traversal-harness.ts` 未重跑：本地 `frontend/node_modules` 无 TS 运行器
  （无 `tsx`/`vitest`/`esbuild`），容器树事实改由真实契约输出直接提取（见第 2 节归档）。
- 未运行完整 Quick、未跑浏览器矩阵、未升级依赖。

## 8. 结论摘要

1. 字段：`payment.request.amount`（Monetary, required）。
2. 首次错误映射位置：前端通用必填语义 —— `valueUtils.ts:31-40` 与实际保存路径
   `saveRecordHelpers.ts:132-137`；矛盾方是 `valueUtils.ts:5-13`。
3. 正确呈现要求：0、空值、未输入三态在草稿、校验、提交与回读中保持同一含义；货币 0 必须
   要么被契约接受并原样回读，要么被契约拒绝，不能前端拦、后端收。
4. **已裁决（2026-09-27）**：清空金额**未被前端必填拦截**，写入请求发出并落库 `0.00` 草稿；未触碰
   由后端 `NotNullViolation` 拒绝（HTTP 500）；显式 `0` 原样保存。详见第 10 节。
5. 最小修改路径（2026-09-27 修订，3 项，均在 P0 通用前端层）：校验字段表不得静默截断为 16 个字段、
   空数值不得序列化为 `false`、两条必填判定收敛同源；业务「金额>0」如需要则另立 P1 约束。
   验收为 0/空/未输入三态非零定向测试 + 浏览器回读。详见第 10.4 节。

## 10. 2026-09-27 三态实测裁决与根因确认（本轮）

环境：`sc_dev_demo`（本地受管开发库）、用户 `demo_full`（uid 52、公司 1、具 finance 角色）、
入口 `/f/payment.request/new?action_id=809&menu_id=559`（菜单 559 → action 809，付款申请）。
`127.0.0.1:5176` 由 `scripts/release/release_static_server.mjs` 提供**已构建产物**
（`frontend/apps/web/dist-dev`），不是源码级 dev server：源码探针不会反映到该页面，静态分析必须
针对 `dist-dev/assets/*.js`。本轮未改产品代码。

### 10.1 三态实测结果（三态均为「其余必填合法，只改金额」）

| 三态 | 草稿显示 | 写请求载荷 `vals` | 请求结果 | 权威回读 |
| --- | --- | --- | --- | --- |
| 显式输入 `0` | `0.00`（`field--normal`，无错误） | `…,"date_request":"2026-09-27","amount":0` | HTTP 200，跳转 `/f/payment.request/2121` | `PRQ2600687`，`amount=0.0`，`state=draft` |
| 输入 `5` 后清空 | 空（`field--empty`），无错误摘要 | `…,"date_request":"2026-09-27","amount":false` | HTTP 200，跳转 `/f/payment.request/2122` | `PRQ2600688`，**`amount=0.0`**，`state=draft` |
| 从未触碰 | 空（`field--empty`） | `…"date_request":"2026-09-27"`（**无 `amount` 键**） | **HTTP 500** `/api/v1/intent` | 未创建；页面提示「请检查以下内容／创建失败，请检查填写内容后重试。」 |

三态的金额输入框在保存前都保持 `data-field-state="required"`，且**没有任何一次**出现字段级必填
错误或焦点转移。对照反例：同样必填的 `partner_id` 不选择时，保存**不发出任何写请求**，直接给出
「往来单位不能为空」。即：必填校验对该表单生效，但**不覆盖 `amount`**。

结论：**清空金额未被前端必填拦截**，因此第 3.1 节的「代码推导 vs 浏览器记录」冲突按浏览器记录裁决；
`PRQ2600326`（金额 `0.00`）的成因就是这条路径。三态语义现状为「0 保存、清空静默变 0、未触碰 500」，
三者互不一致。

### 10.2 根因：通用校验字段表静默退化为「契约字段映射前 16 个」

`layoutNodes`（保存前必填校验、字段顺序等共用）来自
`useRecordFormFieldSchemas.ts:96` → `buildLegacyLayoutNodes`，实际入参为：

- `order: []`（不走布局树遍历）；
- `visibleFields: contractVisibleFields` = **空**（契约 `dataContract.dataMeta` 只有
  `fieldCount/sourceContext/businessOperationProfile/fieldGroups`，**没有 `visibleFields`**）;
- `fallbackFieldNames: [...coreFieldNames, ...advancedFieldNames]` = **空**（语义分组取自
  `dataMeta.fieldGroups.groups`，组名为 `business_identity/business_object/basis/...`，既不含
  `core`/`advanced` 分组，widget 的 `componentConfig.surfaceRole` 也全部为空）。

于是 `buildLegacyLayoutNodes` 落入兜底分支 `Object.keys(input.fields).slice(0, 16)`
（`nativeLayoutUtils.ts:741-744`）：**校验字段表退化为契约字段映射的前 16 个字段码**。

按契约 `containerTree` 的 widget 顺序，前 16 个为
`validation_status, can_review, payment_execution_ids, has_active_payment_execution, state,
partner_transaction_eligibility_reason, type, receipt_type, reject_reason, project_id,
partner_id, business_category_id, date_request, company_id, operation_strategy,
partner_transaction_eligibility`；而 `amount` 位于第 35 位（索引 34），**不在其中**。
这与实测完全一致：`project_id`(9)/`partner_id`(10)/`business_category_id`(11)/`date_request`(12)
被校验并拦截，`amount`(34) 从不被校验。

金额仍进入载荷，是因为 `collectWritableValues` 在布局节点主循环之后还有「脏字段回退」：
对 `dirtyFieldSet` 里不在结果中的字段，直接按 `formFields[name]` 取值写入
（`useRecordFormState.ts:151`）。因此**触碰过金额就会写进载荷，从未触碰就不写**——这正是
「清空（`false`）落 0.00」与「未触碰（缺键）500」两种不同结果的唯一来源。

序列化环节（第 3 节表格已验证）：清空经 `normalizeContractFieldValue`（`valueUtils.ts`）对
`float/monetary` 在 `parseNumeric` 为 `null` 时返回 `false`；Odoo `Monetary` 把 `false` 收敛为
`0.0`，满足 NOT NULL，于是**静默落 0.00**，不报错也不提示。

### 10.3 证据（仓外归档，`j13-zero-amount/`）

- `j13-tri-state-20260927.json`（三态原始结果：草稿、载荷、告警、状态码）、
  `j13-tri-state-20260927.cjs`（实测脚本，拦截 `api.data` 写入并记录完整 `vals`）；
- `j13-validation-field-list-evidence-20260927.json`（契约字段码顺序、前 16 个生效列表、
  `amount` 索引、回退分支入参证据）；
- `j13-readback-before-cleanup-20260927.txt` 与 `j13-cleanup-readback-20260927.txt`
  （回读 `amount=0.0/draft` 后删除 2121/2122，`remaining=[]`、`total_recent_left=0`）。

### 10.4 最小修改路径（P0 通用前端层；2026-09-27 已实施，见第 11 节）

1. **校验字段表不得静默截断**：无 `visibleFields`、无 `core/advanced` 分组时，不得取
   `slice(0, 16)`。应按契约节点顺序或契约已有分组（`business_*`）生成完整字段表，或直接用原生
   布局树构建 `layoutNodes`；清单确实缺失时应显式失败，而不是静默选取前 16 个字段。
2. **空数值不得序列化为 `false`**：`normalizeContractFieldValue` 对清空的 `float/monetary`
   应产出 `null`/省略该键，让 ORM 的 required（NOT NULL）语义裁决；合法的 `0` 仍原样提交。
3. **两条必填判定收敛同源**：仅 `null/undefined/''/[]` 视为空；数字 `0` 与非布尔的 `false`
   都不应视为缺失（`valueUtils.ts:8` 的 `v <= 0`）。若产品要求「草稿金额 > 0」，应作为**独立业务
   约束**在 P1 模型/策略层声明，不复用通用必填判定。

验收：0/空/未输入三态非零定向测试；浏览器验证「显式 `0` 保存并回读为 `0`」「清空与未触碰都不得
静默产生 `0.00` 草稿，且必须给出字段级反馈」。

## 9. 证据归档

`artifacts/ci/handoff-20260925/target-acceptance-827fad4b/j13-zero-amount/`（仓外），
sha256 清单见同目录 `SHA256SUMS.txt`。

## 11. 2026-09-27 修复实施与验收（`64c326c4`）

分支 `fix/j13-required-value-semantics-and-write-payload`，起点为实时 Gitee main `1051dfe3`
（含文档提交 `03bdd28e`）。第 10.4 节三项最小路径全部实施，**未新增「金额必须大于 0」业务规则**。

### 11.1 修改文件与责任层（P0 通用前端层）

| 修改 | 文件 | 行为 |
| --- | --- | --- |
| 校验/写入字段表不再静默截断 | `nativeLayoutUtils.ts` `buildLegacyLayoutNodes` | 兜底从 `Object.keys(fields).slice(0,16)` 改为完整契约字段表；`amount`（索引 34）重新参与必填校验与写入 |
| 空数值序列化区分三态 | `valueUtils.ts` `normalizeContractFieldValue` | integer/float/monetary 的未触碰值返回 `null`（原 `false`，被 Odoo 静默收敛为 `0.0`）；显式清空仍走类型化哨兵 `false`；数值 `0` 原样提交 |
| 写入载荷归属 | `saveRecordHelpers.ts` `shouldWriteFieldValue`（新） | `null` 永不写入；编辑态只写改动字段；创建态跳过未触碰空值，避免空串覆盖 ORM 默认值（默认值仍归 ORM） |
| 必填判定同源 | `valueUtils.ts` `isMissingRequiredValue`/`isRequiredFieldEmptyByType` | 前者成为唯一实现（数字 `0` 不再算缺失、布尔字段 `false` 不误伤），后者退化为类型化别名；页面预检与保存前校验不会再给出相反结论 |

### 11.2 定向测试（非零）

- 新增 `frontend/apps/web/scripts/j13_required_value_semantics_test.ts`，接入
  `make verify.frontend.j13_required_value_semantics.unit`（83 例），并纳入
  `verify.frontend.quick.gate` 与 `verify.frontend.release.unit`，不再是游离测试。
- 同一探针在旧实现上为 `zero_missing=true`、`untouched_numeric=false`、`table_size=16/has_f34=false`；
  修复后为 `false` / `null` / `40·true`，证明测试确实约束被测行为。
- 既有受影响定向：`canonical_form_presenter.unit`（PASS，177 例）、`create_record_user_journey.unit`、
  `create_default_hydration.unit`（PASS，28 例）、onchange 三守卫、`contract_form_save_payload_builder_guard`、
  `frontend_professional_base_field_guard`；`vue-tsc --noEmit` 仍为 31 项既有错误、**未新增**（被测文件 0 项）。

### 11.3 浏览器验收（5176，候选 SHA `64c326c4`，`sc_dev_demo`/`demo_full`，入口 `/a/809?menu_id=559`）

| 场景 | 实际操作 | 结果 |
| --- | --- | --- |
| 未触碰金额（末尾必填，契约字段第 35 位） | 其余必填合法，不触碰金额后保存 | **零写请求** + 「请检查以下内容 / 申请金额不能为空」（原为 HTTP 500），证明第 17 个及之后的必填不再漏检 |
| 明确输入 `0` | 输入 `0` 后保存 | 写请求载荷 `…"amount":0`（数值，非 `false`），HTTP 200 → 记录 2124，权威回读 `amount=0.0`、`state=draft` |
| 明确清空 | 输入 `5` 后清空，保存 | **零写请求** + 金额字段级错误（必填被拦） |
| 保存失败后重试 | 输入 `0`，首次 create 被模拟 500 | 失败后草稿保留 `0.00`、提示「模拟保存失败」、未创建记录；重试成功 → 记录 2125，回读 `0.0/draft` |
| 编辑态未触碰 | 打开 2126（金额 `7.50`）直接保存 | **不发写请求**，金额保持 `7.50`；权威回读 `7.5`，未出现 `false`/清空 |

载荷形状：三态成功分支均为 7 个键（`project_id/partner_id/business_category_id/date_request/amount/
actual_payee_unit/attachment_ids`），**未因字段表变完整而膨胀出空串键**，即创建态空值仍交由 ORM 默认值。

### 11.4 清理回执

专用记录 2124/2125/2126 已删除，`remaining=[]`、`total_recent_left=0`。
证据：`artifacts/ci/handoff-20260925/target-acceptance-827fad4b/j13-zero-amount/j13-fix-acceptance-20260927.{cjs,json}`、
`j13-fix-edit-untouched-20260927.{cjs,json}`、`j13-fix-readback-before-cleanup-20260927.txt`、
`j13-fix-cleanup-readback-20260927.txt`、`j13-fix-edit-cleanup-readback-20260927.txt`。

### 11.5 未覆盖 / 边界

- 已补验（第 12 节）：非必填数值「显式清空」的端到端闭环。本批入口内 `amount` 为必填、清空仍被正确拦在保存前；
  非必填数值改在正式入口「公司收入」实测（写入 → 清空 → 保存 → 回读 → 未触碰对照）。
- 未验证：只读角色对 `amount` 的直接写入拒绝（既有后端权限证据继续复用，未在本批重跑）。
- 未覆盖：报表投影、properties、附件 404（仍为未复现）、显式创建能力状态，均保持独立待办。

## 12. 2026-09-27 收口：场景预校验类型接线与非必填数值清空闭环（`5455ca00`）

分支 `fix/j13-required-value-semantics-and-write-payload`，父提交 `1510bafc`。第 11 节把必填判定收敛为
唯一实现，但场景预校验仍是**无类型调用**，两条链路实际并未一致；同时第 11.5 节登记的非必填数值清空
尚无实测。本轮只补这两项，不扩大范围，新增提交 `5455ca00`。

### 12.1 根因与修复（P0 通用前端层）

`useRecordActionPresentation.ts` 的包装函数只传值调用 `isMissingRequiredValue`（
`collectSceneValidationPrecheckErrorsFromRules({ …, isMissingValue: isMissingRequiredValue })`），
`sceneValidation.ts` 的 `collectSceneValidationPrecheckErrors` 也只按值判断。而统一判定是**类型敏感**的：

| 值 | 无类型 | `boolean` | `many2one` |
| --- | --- | --- | --- |
| `false` | 缺失 | 真实答案 | 空关联（缺失） |

因此场景规则要求填写的布尔字段为 `false` 时仍会被拦；反之若靠「无类型时一律接受 `false`」修补，
空关联又必然漏检。函数实现合并了，**调用方的类型信息没有接齐**。

| 修改 | 文件 | 行为 |
| --- | --- | --- |
| 预检输入增加类型解析器 | `sceneValidation.ts` `SceneValidationPrecheckInput.fieldType?` | 逐字段解析契约类型后调用统一判定；无描述符时保持原有类型盲结论 |
| 生产调用点接契约类型 | `useRecordActionPresentation.ts` `collectSceneValidationPrecheckErrors` | `fieldType: (field) => fieldType(formFields.value[field])`，以契约表单字段表为**唯一类型权威** |
| 注释同步 | `valueUtils.ts` | 明确两条链路都必须带类型判定，避免再次据此写出「预检没有类型可用」 |

### 12.2 定向测试（83 → 110 例）

仍为 `make verify.frontend.j13_required_value_semantics.unit`（已接入 quick/release 门禁），新增 27 例：

- **真实预检入口**：直接调用导出的 `collectSceneValidationPrecheckErrors`，按生产接线（契约描述符 +
  `fieldType` + `isMissingRequiredValue`）断言——布尔 `false`/`true` 通过、`null` 驳回；数值 `0` 通过、
  清空驳回；空关联 `false` 驳回；空白文本驳回；`relation=false` 与 `flag=false` 同批时只报前者。
- **类型确实转发**：用记录型 `isMissingValue` 断言逐字段收到 `[false,'boolean']`、`[false,'many2one']`；
  未知字段仍走类型盲结论（证明修的不是「一律接受 `false`」）。
- **调用点接线守卫**：读取生产源文件，断言预检调用块同时含 `isMissingValue: isMissingRequiredValue`、
  `fieldType:` 与 `formFields.value[`——行为测试抓不到调用点漂移，这一条专门防它。
- **非必填数值三态**：编辑态未触碰不写入、显式清空写入类型化哨兵、数值 `0` 原样提交。
- **控件清空输出**：官方数值控件是文本输入，清空发出**空串**；派发器不得把它变成
  `shouldWriteFieldValue` 会跳过的 `null`，否则清空意图丢失（`null` 输入也归一为空串）。

`vue-tsc --noEmit` 仍为 31 项既有错误、**未新增**（本轮改动文件 0 项）。

### 12.3 非必填数值清空闭环（浏览器 + ORM 权威回读）

入口：正式「公司收入」`/f/sc.receipt.income/new?action_id=806&menu_id=545`（P1 入口，`demo_full`／
`sc_dev_demo`，候选 5176 由 `5455ca00` 的 `dist-dev` 构建提供）。

| 场景 | 实测 | 结果 |
| --- | --- | --- |
| 创建：触碰两个非必填数值 | `deducted_tax_amount=3`、`settlement_amount=7` | 载荷为**数值** `3`/`7`；未触碰的 `deducted_invoice_amount` **不在载荷**（10 键） |
| 编辑载入 | — | 回显 `100.00` / `3.00` / `7.00` |
| 清空非必填数值 + 改备注 | 清空 `settlement_amount` | 控件清空后草稿为**空串**（非 `null`）；写载荷仅 `{"settlement_amount":false,"note":…}`，未触碰的 `deducted_tax_amount` **不在载荷** |
| 权威回读（清空后） | ORM `read` | `settlement_amount=0.0`（float）、`deducted_tax_amount=3.0` 保留、`state=draft`、`note` 已更新 |
| 只改备注（两者都未触碰） | 写载荷仅 `{"note":…}` | 回读 `settlement_amount` 仍 `0.0`、`deducted_tax_amount` 仍 `3.0`，与原值一致 |

**必须写清的边界**：`monetary`/`float` 列对 Odoo 空值哨兵 `false` 的类型化收敛就是**数值 `0.0`**。
因此对这类字段，「显式清空」与「从未写入」在**存储上不可区分**（后者来自列默认值 `0.0`）；
清空意图的可观测差异只在**写入载荷**（显式 `false` 与省略键）。不得把该 `0.0` 描述为「数据库空值」，
也不得宣称通用载荷层能表达「已核实的零」与「未填写」的差别——那需要 P1 业务约束。

### 12.4 清理回执

专用探测记录 `257` 已删除，`remaining=[]`、`probe_note_leftover=[]`、`total_probe_left=0`；
首轮探测记录 `256` 同样已回收，无残留。

证据：`artifacts/ci/handoff-20260925/target-acceptance-827fad4b/j13-zero-amount/`
`j13-nonrequired-clear-20260927.{cjs,json}`、`j13-nonrequired-readback-20260927.py`、
`j13-nonrequired-readback-before-cleanup-20260927.txt`、`j13-nonrequired-cleanup-20260927.py`、
`j13-nonrequired-cleanup-readback-20260927.txt`（已并入 `SHA256SUMS.txt`，44 条全部校验通过）。

### 12.5 未覆盖 / 边界

- 场景所需**布尔字段**：现有可达正式入口没有 scene-required 布尔字段，故该修复只有真实入口单测 +
  调用点接线守卫，**无对应浏览器场景**；不据此宣称浏览器已验证场景预检。
- 目标环境只读角色拒绝仍未补验（与第 11.5 节一致，部署后补）。
- 报表投影、properties、附件 404、显式创建能力状态保持独立待办。
