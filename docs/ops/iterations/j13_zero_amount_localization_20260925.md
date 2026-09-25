# J13 零金额分歧定位（2026-09-25）

状态：定位完成，**未修改任何产品代码**；产品决策未定，J13 断言在浏览器中为 `not_run`。
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

按代码推导：**清空与未输入应被前端必填校验拦下**，错误摘要标题确实是「请检查以下内容」
（`ScErrorSummary.vue:2` 默认 `title`；`ProductFormErrorSummary.vue:6`）；显式 `0` 则前端放行、
后端接受。**没有任何一层把 0 改写成空值。**

### 3.1 该推导与既有浏览器记录冲突（本轮未裁决）

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

## 7. 浏览器执行结果：`not_run`（附实测原因）

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
4. **未裁决**：清空金额在浏览器中是「被拦」还是「保存成功」。代码推导为被拦，既有浏览器记录
   （2026-09-24，旁证 `PRQ2600326`）为保存成功；本地受管环境无法渲染该表单，故本轮为 `not_run`。
5. 最小修改路径：先按第 6 节第 0/1 步裁决并裁定产品语义，再收敛 `valueUtils.ts` 1 处判定定义并
   补 0/空/未输入三态非零定向测试。

## 9. 证据归档

`artifacts/ci/handoff-20260925/target-acceptance-827fad4b/j13-zero-amount/`（仓外），
sha256 清单见同目录 `SHA256SUMS.txt`。
