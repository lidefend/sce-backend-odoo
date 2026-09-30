# 会计 JSON 详情阻塞：定位结论与只读展示修复（2026-09-24）

来源缺口：`docs/ops/iterations/frontend_shared_foundation_gap_audit_20260909.md` → `G-F3-02 / B02`。
本记录只收口该缺口，不新建盘点报告，不扩大为账务写入、过账或数据库升级。

## 层与边界声明

- Formal Product Layer：P0 平台通用产品。字段类型 → 组件能力是平台机制，不是会计模块或客户语义。
- Layer Target：`addons/smart_core/core/unified_page_contract_v2_assembler.py`（契约生成：字段类型 → 组件键）、
  `frontend/apps/web/src/utils/display.ts`（通用只读展示）、
  `frontend/apps/web/src/components/template/FormSection.vue`（通用字段装配）。
- Module：`smart_core`（P0 契约机制）+ frontend（web app 通用渲染）。
- Standard vs User-Specific：平台通用规则；不对 `account.move`、日记账或任何模型加特例。
- Why Here：`fieldType` 与 `componentKey` 的对应关系属于平台契约机制；对象值的只读文本化属于通用展示层。
- Why Not Elsewhere：不在会计模块、页面层或低代码配置里绕过；不隐藏字段、不吞异常、不把对象
  `JSON.stringify` 塞进可写文本框来让页面“通过”。
- Blast Radius：所有含 `fields.Json`/`widget="json"` 字段的 v2 页面契约（含平台自身 `*_json` 字段）；
  受影响守卫为 `scripts/verify/unified_page_contract_v2_assembler_guard.py` 与前端展示契约测试。

## 复现（受管本地开发环境）

- 环境：`local.dev`（project `sc-local-dev`、database `sc_dev_demo`、nginx `18081`、odoo `8070`），
  管理员会话；列表 → 详情 `/f/account.move/2?menu_id=175&action_id=289`（action 289 / menu 175）。
- 现象：整页显示 `页面契约无法渲染 PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH:sc.input.text:json`，
  除该错误外无控制台/网络错误。
- 契约快照：`/tmp/acct-json-detail-20260924/account_move_2_form_contract.json`。

## 定位结论（四项）

### 1. 字段名

`quick_encoding_vals`（`account.move` 记录 2，label「快速编码值」）。

| 事实 | 值 |
|---|---|
| 后端字段类型 | `fields.Json`（`ttype=json`，`store=false`，模型默认只读） |
| 契约类型 | `componentConfig.fieldType = "json"`（真实） |
| 组件键 | `componentKey = "sc.input.text"`（错误） |
| 只读状态 | `readonly = true`、`invisible = true`（原生视图 `<field name="quick_encoding_vals" invisible="1"/>`） |
| 实际值形状 | JSON 对象（空 `{}` 或非空对象）；无 `widget` 属性 |
| widgetId / locator | `field.quick_encoding_vals.occ.e81ec38124a82a2f` / `/form[1]/sheet[1]/field[35]` |

同一模型上 `send_and_print_values`、行上的 `analytic_distribution` 同为 json；平台自身视图另有
`feature_flags_json`、`limits_json`、`payload_json`、`result_json` 等 `widget="json"` 字段，属同一缺陷类。

### 2. 首次错误映射的位置

链路：后端契约 → Decoder → normalized store → Resolver → Registry → renderer。首次错误映射在**契约生成层**：

1. `unified_page_contract_v2_assembler._widget_type_from_field` 对 `ttype=json` **没有分支**，
   落到函数末尾 `return "input"`；`_canonical_widget_type` 同样把显式 `widget="json"`
   （以及来源字段上被回退填充的 `widget="input"`）交给同一默认值。
2. `_component_key("input", field)` → `mapping["input"] = "sc.input.text"`，于是契约声明为文本输入组件，
   且 `componentConfig.nativeWidget` 也带着这个回退值。
3. 前端 `professionalComponentRegistry.ts` 中 `registration('sc.input.text','text',['char'])` 不含 `json`，
   `resolveProfessionalComponentRegistration` 抛 `PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH:sc.input.text:json`；
   `canonicalFormRenderState.resolveCanonicalFormRenderState` 捕获后返回 `{model:null,error}`，
   于是整页不可渲染（组件解析发生在可见性求值之前，`invisible` 字段同样会解析并触发）。

归属判定：**契约把类型/组件声明错了**（把 JSON 值声明为文本输入），且**注册表确实没有 json 能力**
（唯一兜底 `sc.display.text` 支持 `'*'`，但它走通用只读文本路径，对象值被本地化归一为空文本）。
Resolver 的 fail-closed 是设计内行为，不是本次要改的错误。

### 3. 正确呈现要求

- 任何客户端都没有 JSON 编辑控件：契约必须声明**只读可读展示**，不得声明文本输入。
- 只读展示必须反映真实值：对象/数组输出其 JSON 文本；`{}`、`[]`、`null`、`false`、空字符串按空值处理
  （沿用现有空值规则：只读事实可隐藏或显示为空值占位）。
- 可编辑的 json 字段（平台 `widget="json"` 字段、`send_and_print_values`）同样只读展示：
  不出现可写文本框，也不允许把对象字符串化写回字段。该「JSON 编辑能力缺失」按缺口登记，不在本批扩展。
- 空值与非空值都不导致整页失败；契约声明 `invisible` 的字段按其契约不参与展示。

### 4. 最小修改路径

| 层 | 修改 | 理由 |
|---|---|---|
| 契约生成（P0 `smart_core`） | `_widget_type_from_field` 增加 `json → "display"`；`_canonical_widget_type` 对 `ttype=json` 先行判定并复用前者 | 字段真实类型优先于任何 widget 拼写或来源回退值；`display` 已在 `widgetType` 枚举内，`_component_key("display")` 复用既有 `sc.display.text`，不新增组件键、不改 schema |
| 通用展示（P0 frontend） | `utils/display.ts` 在本地化归一之前处理 json；`FormSection.vue` 只读分支覆盖 json 类型 | 对象值需要真实文本化，且不得落进可编辑 `ScInput` 兜底 |
| 定向测试 | 契约映射三类输入（`ttype=json`、`widget="json"`、伪造 `widget="input"`）与守卫案例表；前端展示契约测试的空/非空 json 用例 | 锁定错误不再回归 |
| 明确不改 | Decoder / store / Resolver 的 fail-closed；lite 契约构建器 `unified_page_contract_lite_adapter._widget_type` 的同类回退 | 后者是不同契约构建器与不同消费者，未证明可达同一失败页，登记为同类缺口 |

## 缺口清单同步项

- `G-F3-02 / B02`：由「按症状描述」更新为本定位结论，并按上表进入修复与验收。
- 登记同类未修缺口：`unified_page_contract_lite_adapter._widget_type`（`FIELD_TYPE_TO_WIDGET.get(ftype, "input")`）
  对 `json` 同样回退为 `input`；属 lite 契约构建器，消费者与 v2 不同，本批不修改。
- 登记能力缺口：平台无 JSON 编辑控件，json 字段按只读展示；若后续需要编辑，应作为独立产品需求新建组件能力。

## 实施（读取与展示闭环，不含账务写入）

| 文件 | 改动 |
|---|---|
| `addons/smart_core/core/unified_page_contract_v2_assembler.py` | `_widget_type_from_field` 增加 `json → "display"`；`_canonical_widget_type` 对 `ttype/type == json` 先行判定并复用同一函数，使字段真实类型优先于显式 widget 拼写与来源回退值 |
| `frontend/apps/web/src/utils/fieldSemantics.ts` | `CanonicalFieldType` 与 `CANONICAL_FIELD_TYPES` 纳入 `json`；新增 `isJsonFieldType`，避免归一后退化为 `unknown` |
| `frontend/apps/web/src/utils/display.ts` | 新增 `formatJsonDisplayValue`；`formatDisplayValue` 在本地化归一之前处理 json，对象/数组输出 JSON 文本，`{}`/`[]`/`null`/`false`/空串走既有空值口径 |
| `frontend/apps/web/src/components/template/FormSection.vue` | 只读分支条件改为 `field.readonly \|\| isJsonField(field)`，可编辑 json 不再落入可写兜底控件 |
| `frontend/apps/web/src/pages/contractForm/canonicalFormRenderer.ts` | `inputValue` 对 json 返回空输入值，禁止对象字符串化冒充输入 |
| `frontend/apps/web/src/components/template/formSection.mapper.ts` | `resolveTemplateInputValue` 对 json 返回空输入值，同上 |
| `addons/smart_core/tests/test_unified_page_contract_v2_kanban_action_registry.py` | 新增 `test_json_field_declares_readable_display_instead_of_a_text_input`（`type=json`、`widget=json`、伪造 `widget=input`、`ttype=json` 四类输入） |
| `scripts/verify/unified_page_contract_v2_assembler_guard.py` | 组件投影案例表新增 `({"type":"json","widget":"json"}) → display/sc.display.text` |
| `scripts/verify/frontend_localized_display_contract_test.ts` | json 展示契约：非空对象/数组/JSON 字符串 → 文本；`{}`/`[]`/`false`/`null`/空白 → 空值文本 |

未新增组件键、未改 schema、未隐藏字段、未吞异常：`display` 已在 `widgetType` 枚举内，`_component_key("display")` 复用既有 `sc.display.text`。

## 定向验证（非零，全部通过）

| 命令 | 结果 |
|---|---|
| `python3 addons/smart_core/tests/test_unified_page_contract_v2_kanban_action_registry.py` | 7 tests OK |
| `make verify.unified_page_contract.v2.assembler` | passed: sources=4 |
| `make verify.frontend.localized_display.unit` | PASS（含 json 展示契约用例） |
| `make verify.frontend.canonical_form_presenter.unit` | PASS cases=177 + 10 cases |
| `python3 scripts/verify/frontend_professional_component_registry_guard.py` | PASS |
| `python3 -m unittest scripts.verify.test_frontend_professional_component_registry_guard` | 147 tests OK |
| `make ci.local.iteration` | PASS（L1 入口，receipt=none，仍推荐按风险选非零 L2 目标） |

## 浏览器与契约验证（受管 `local.dev`，管理员会话）

- **原失败记录（列表 → 详情）**：`/a/289?menu_id=175` 列表点行 → `/f/account.move/2?menu_id=175&action_id=289` 整页渲染完成（标题 `SC-DEMO-INV-002`），`PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH` 与「无法渲染」文本为空，无 `[object Object]`，json 字段的文本/文本域输入数为 0。
- **返回列表**：详情点「返回」回到 `/a/289?menu_id=175`，列表仍为 4 行，原 `menu_id` 查询上下文保留。
- **契约探针（同环境，fix 后）**：`quick_encoding_vals` → `widgetType=display`、`componentKey=sc.display.text`、`readonly=true`、`invisible=true`；`sc.capability.default_payload`（非空对象，可见）、`sc.pack.installation.last_diff_json`（对象）/`upgrade_history`（数组）同样为 `display/sc.display.text`。
- **同一缺陷类的原生可编辑 json**：`account.move.line.analytic_distribution` 旧行为复算为 `sc.input.text`（无 json 分支 → `input`），修复后为 `sc.display.text`；注册表中只有 `sc.display.text` 支持 `'*'`，`sc.input.text` 仅支持 `['char']`，故旧行为必然触发 Resolver fail-closed，此改动不是把可用编辑器改成只读。

## 残留验证缺口与同批登记（不在本批修改）

- **可见且非空的 json 值在本数据集不存在**：`account.move` 的 `quick_encoding_vals`/`send_and_print_values` 全为 `false` 且原生 `invisible`；`account.move.line.analytic_distribution` 全空；`mail.tracking.value.field_info` 全空；`account.payment` 无记录；`project.task.duration_tracking` 虽有非空对象，但其入口被导航授权层拒绝（见下）。因此「可见非空 JSON 文本」的页面级证据缺失，改由发布模块的展示单测与契约探针承担。补齐方式：在有可见非空 json 字段的可达记录上复验（需写入数据，超出本批只读范围）。
- **导航授权拒绝（独立缺口，登记不修）**：`/s/task.center` 列表可打开，但其行 → `/f/project.task/3?action_id=355&scene_key=task.center` 被 `NAVIGATION_AUTHORITY_DENIED` 拦截；`/a/355?menu_id=216` 同样被拒，而 Odoo 侧 menu 216 对该用户可见。属「正式入口按职责验收」，与本批无关。
- **lite 契约构建器同源回退**：`unified_page_contract_lite_adapter._widget_type` 的 `FIELD_TYPE_TO_WIDGET.get(ftype, "input")` 对 json 仍回退 `input`；不同契约构建器与消费者，未证明可达同一失败页，登记不修。
- **Resolver 整页 fail-closed**：单个不受支持的字段仍会让整页不可渲染；这是设计内行为，本批未改，仅记录观察。

## 验收边界

- 本批只完成**读取与展示闭环**：`批次验收完成`（定向 + 浏览器复验通过）；`主线集成完成`与后续状态在 PR/CI/合并单独跟进，未合入前不宣称。
- 未纳入本批：JSON 编辑能力、账务写入/过账、数据库升级、lite 契约构建器、导航授权拒绝、`ScAutoComplete.vue` 与 many2many 失焦逻辑、显式创建入口（仍为未验收）。
