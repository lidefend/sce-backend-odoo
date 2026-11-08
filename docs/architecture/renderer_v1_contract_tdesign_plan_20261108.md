# FE-RENDERER-V1：基于业务契约的统一 TDesign 组件交付

- 状态：V1-01/V1-02 已实现；Contract Form、Payment Request 与集合列表已验收；等待独立评审
- 基线：`f1ba79c173c4701c642b3e505daf33c7aaaedfb9`
- 分支：`feature/fe-renderer-v1-contract-tdesign-20261108`
- Formal Product Layer：P0 platform kernel product
- Layer Target：Frontend Contract V2 component identity, binding and unified Sc/TDesign implementation
- Module：Semantic Registry、Component Registry、Canonical Form Render Model、Professional Component Registry、FormSection、Sc Design System、TDesign Bridge
- Standard vs User-Specific：platform engineering standard
- 英文版本：[renderer_v1_contract_tdesign_plan_20261108.en.md](renderer_v1_contract_tdesign_plan_20261108.en.md)

## 1. 第一版目标

V1 只交付：

```text
Contract V2
  -> Semantic Registry
  -> Professional Component Registry
  -> Canonical Render Model
  -> componentKey + declared variant
  -> Sc component
  -> TDesign
```

不建设多 Renderer Runtime、动态插件市场、React Host 或完整 Native 组件库。
Page、Composition、Specialized 和 `@sc/ui` 继续保留现有宿主，只统一组件身份、
基础实现绑定和交互契约。

## 2. 基线与 PR #845 身份

- 最新 `origin/main`：`f1ba79c173c4701c642b3e505daf33c7aaaedfb9`
- PR #845：OPEN、MERGEABLE
- PR #845 HEAD：`7d3ed98979c17125b3dc987c26fcf6df3f1be701`
- PR #845 最新必需检查：全部 SUCCESS
- 合入状态：未合并

PR #845 相对 main 新增 54 个文件、3,423 行。其核心是 Primitive Port、七项
`ScScene*` Adapter、Provider 和 Conformance。V1 只复用其中对现有 Sc 基础组件
有价值的属性、事件、焦点和可访问性修复，不自动继承七项 Scene Adapter 作为生产
架构。

## 3. V1-00 现状对账

### 3.1 声明规模

当前契约注册表：

| 对象 | 数量 |
| --- | ---: |
| semantic | 27 |
| component | 28 |
| field component | 26 |
| platform field component | 25 |
| industry field component | 1 |
| node component | 2 |
| `Sc*.vue` 组件 | 63 |

22 个当前列出的 Sc 文件直接消费 `tdesignPrimitiveBridge`；其余组件是组合、
门面或无 TDesign 依赖的语义组件。

### 3.2 真实调用链

```text
contracts/registry/semantic.yaml
  -> contracts/registry/component.yaml
  -> scripts/contract/generate_semantic_registry.py
  -> semantic_registry.generated.ts
  -> professionalComponentRegistry.ts
  -> contractFormPresenter.resolveContractProfessionalComponent()
  -> CanonicalFormRenderModel.componentResolution
  -> canonicalFieldToFormSection()
  -> FormSectionFieldSchema
  -> FormSection
  -> professional/base controller
  -> Sc component
  -> TDesign
```

证据：

- `contracts/registry/semantic.yaml:90-117`
- `contracts/registry/component.yaml:41-68`
- `scripts/contract/generate_semantic_registry.py:338-396`
- `frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts:113-209`
- `frontend/apps/web/src/app/presentation/contractFormPresenter.ts:277-285`
- `frontend/apps/web/src/app/presentation/canonicalFormRenderModel.ts:38-71`
- `frontend/apps/web/src/pages/contractForm/canonicalFormRenderer.ts:163-219`
- `frontend/apps/web/src/components/template/FormSection.vue:200-406`

### 3.3 当前 componentKey 实现映射

| componentKey | 契约字段类型 | 当前实现 |
| --- | --- | --- |
| `sc.input.text` | char | `ProfessionalBaseFieldControl -> ScInput` |
| `sc.input.binary` | binary | `FormSection -> ScFileField` |
| `sc.input.textarea` | text, html | text: `ScTextarea`; html: `RestrictedHtmlEditor` |
| `sc.input.number` | integer, float, monetary | integer/float: `ScNumberInput`; monetary: business rendering |
| `sc.select.remote` | selection | `ScSelect`; `widget=radio`: `ScRadioGroup` |
| `sc.input.boolean` | boolean | `ScCheckbox` |
| `sc.input.date` | date | `ScDateField`; `widget=daterange`: 两个 `ScDateField` |
| `sc.input.datetime` | datetime | `ScDateField(withTime)` |
| `sc.relation.many2one` | many2one | `ProfessionalRelationFieldControl` |
| `sc.relation.many2many` | many2many | `ProfessionalRelationFieldControl` |
| `sc.select.tags` | many2many | `ProfessionalRelationFieldControl` |
| `sc.relation.table` | one2many | `ProfessionalDetailCollectionControl -> X2ManyRelationRenderer -> ScTable` |
| `sc.payment.settlement_detail_collection` | one2many | 行业动态 Renderer |
| `sc.value.money` | monetary | `ProfessionalBusinessValueControl` |
| `sc.value.percentage` | float, integer | `ProfessionalBusinessValueControl` |
| `sc.display.status` | selection, char | `ProfessionalBusinessValueControl` |
| `sc.value.duration` | float, integer | `ProfessionalBusinessValueControl` |
| `sc.auth.*` | char/selection/text/action | base family；`one_time_secret` fail-closed |
| `sc.display.text` | `*` | type-directed sentinel |
| `sc.table.data` | one2many, many2many | registry 声明存在，Form 字段宿主未闭合 |
| `sc.tree.data` | one2many, many2many | registry 声明存在，Form 字段宿主未闭合 |
| `sc.button.action` | action | registry 声明存在，Form 字段宿主未闭合 |

### 3.4 三个关键事实

1. `componentKey` 不是一对一的原始 Vue 组件身份。
2. 现有 `ProfessionalBaseFieldControl` 已经是基础字段的统一宿主，但内部仍按
   field type 维护多个 Sc 分支。
3. `sc.table.data`、`sc.tree.data`、`sc.button.action` 存在声明多于 Form 字段
   消费的问题，V1 必须显式登记 host gap，不能伪造实现。

因此组件绑定身份必须是：

```text
componentKey
  + declared fieldType
  + declared widget/variant
  + render profile
  -> binding
```

所有选择输入必须来自 Contract V2。不得读取模型名、字段名、菜单名或 action ID
补足组件选择。

## 4. V1 实施切片

### V1-01：基础字段 Component Binding Map

第一刀只收敛无歧义的普通基础字段：

- `sc.input.text -> ScInput`
- `sc.input.textarea -> ScTextarea`，`html` 为显式变体
- `sc.input.number -> ScNumberInput`
- `sc.select.remote -> ScSelect`
- `sc.input.boolean -> ScCheckbox`
- `sc.input.date -> ScDateField`
- `sc.input.datetime -> ScDateField(withTime)`

binding 必须校验：

- componentKey 是当前生成 carrier 中的已登记身份；
- field type 在 binding 的封闭集合内；
- widget/readonly 变体来自声明；
- 缺失、未知或不匹配时可见 fail-closed；
- 不维护第二份完整 componentKey 词表。

### V1-02：TDesign 基础组件收敛

优先复用现有 Sc 组件，只采纳已有候选中的真实能力修复：

- Input / Textarea：name、真实事件上下文、IME、focus/blur。
- Select：name、真实 change/search/popup 事件、focus/blur、键盘。
- DateField：name、focus/blur、键盘、loading/ARIA。
- Table：emptyText 等真实消费者能力。
- Number / Checkbox：保留现有受控值和事件语义，缺口按真实消费者处理。

### V1-03：页面接入

保留宿主：

- `FormSection`
- `PageRenderer`
- `ActionSurfaceRendererHost`
- `ProfessionalComponentRegistry`
- `@sc/ui` Scene Composition

新增 binding 只替换基础字段的实现选择，不重写页面、列表、看板、详情或关系组合。
旧 `SceneFieldControl` 暂留兼容，但不作为 V1 新 binding 的来源。

### V1-04：业务表达与操作

继续使用：

- `businessValuePresentation.ts`
- Contract V2 权限与 readonly 投影
- Action Registry / action contract
- 服务端 ACL

Sc/TDesign 不格式化业务金额、状态或空值，不决定动作是否授权。

### V1-05：真实页面验收

三类样板：

1. Contract Form：基础字段、日期、选择、布尔值和错误态。
2. Payment Request：主从关系、金额、动作、readonly/disabled。
3. 当前已启用的 ActionView collection：集合表格、行导航和只读事实。
   `SceneCollectionSurface` 的产品启用不在本批范围，单独登记为 feature-gated 延期。

现有可复用测试入口：

- `verify.frontend.professional_component_registry.unit`
- `verify.frontend.professional_base_field.unit`
- `verify.semantic_runtime_resolution`
- `verify.frontend.professional_business_value.unit`
- `verify.frontend.professional_relation_field.unit`
- `verify.frontend.professional_detail_collection.unit`
- `verify.frontend.canonical_form_presenter.unit`
- `verify.frontend.business_semantics.unit`
- `verify.frontend.action_surface_renderer_registry.unit`
- `verify.local.dev.payment_request.full_chain`
- `verify.local.dev.payment_request.settlement_component.journey`

## 5. PR #845 资产处置

| 现有成果 | V1 决定 |
| --- | --- |
| Primitive Port | 保留，不扩大 |
| ScSceneButton | 暂不进入 Form 基础字段默认路径 |
| ScSceneInput/Textarea | 复用其中真实事件修复；不默认采用包装层 |
| ScSceneSelect/DateField | 复用事件、焦点和 name 修复 |
| ScSceneTable/Icon | 仅复用实际能力修复 |
| ScenePrimitiveProvider | V1 不引入为全局 Provider |
| 七项 Adapter Registry | 不升级为全局 Component Binding Map |
| 旧 Scene Kit | 保留兼容，待真实消费者迁移后清理 |

## 6. 验收标准

- 平台 component binding 与生成 carrier 不允许漂移。
- 新增绑定不能增加第二份全局 componentKey 词表。
- 普通基础字段由 `componentKey + declared variant` 决定实现。
- unknown、field type mismatch、未登记 variant fail-closed。
- 现有关系、业务值、行业 Renderer 不降级为通用输入。
- 业务表达、权限和操作链不改变。
- 相同 Contract 字段在 Form/Detail 使用一致的 Sc/TDesign 基础组件。
- 新增普通模型和 Contract 只通过声明即可使用统一组件。

## 7. 当前证据

最新 main 的基线专项测试：

- `verify.frontend.professional_component_registry.unit`：PASS；Registry 用例
  `>=184`，Guard 162 tests。
- `verify.frontend.professional_base_field.unit`：PASS；模型矩阵 54、
  counterexamples 6、Guard 16 tests。
- `verify.semantic_runtime_resolution`：PASS；119 cases。

V1 实现专项：

- `contract_component_bindings_test`：PASS；11 个基础 componentKey、
  23 个 key/type 变体、7 个实现。
- `contract_tdesign_components_test`：PASS；67 checks、0 console errors，
  覆盖真实 TDesign DOM、受控值、input/change、focus/blur、键盘、Select
  search/popup、ARIA，以及 `ProfessionalBaseFieldControl` 对 binding map 的消费。
- `verify.frontend.professional_base_field.unit`：PASS；模型矩阵 54、Guard
  19 tests，新增 map/carrier 漂移与 host 消费守卫。
- Professional Registry 162 tests、Primitive Adapter 41 tests、业务值/关系/
  明细/Canonical/Action Surface 专项均 PASS。
- `ci.local.iteration`：PASSED，执行 8 个要求的增量目标。
- `verify.frontend.lint.src`：0 errors；保留 1 个本批范围外的既有
  `StatusPanel.vue` warning。
- `verify.frontend.typecheck.strict`：PASS。

独立评审修复后的专项证据：

- TDesign/Sc browser Conformance 增至 75 checks；Textarea 每个真实 input
  触发 input、blur 只触发一次 change；DatePicker 通过真实日历 `mousedown`
  更新值并只触发一次 change；聚焦和未聚焦清空都消费真实 `onClear` MouseEvent
  且各只触发一次 change。
- `contract_only_business_fixture_test`：PASS；虚构新模型
  `x.ordinary_business` 由 7 个 Contract 字段直接投影到 ScInput、ScTextarea、
  ScSelect、ScNumberInput、ScDateField、ScCheckbox，前端产品源码特判为 0。

真实候选验收：

- 候选 SHA：`5566824ca045ff3c38e6aa5f20de9b006c5d70fc`；
- `verify.frontend.build`：PASS，5,374 modules；
- `local.dev.candidate.frontend`：PASS，同一 `sc-local-dev / sc_dev_demo` 运行时；
- Payment Request settlement component journey：PASS；引入明细、金额同步、取消保留、
  确认删除和 fixture restore 均通过；
- 候选 visual smoke：PASS；付款申请编辑表单、付款申请列表和只读详情在
  desktop/mobile 均通过，0 mutation、0 console error；
- 真实付款申请表单 DOM：16 个 Contract binding、0 binding error；实际出现
  `ScDateField`、`ScInput`、`ScTextarea`、业务值、关系和明细组件；
- 付款申请列表：desktop/mobile 加载真实表格，无横向溢出。

V1 仍有一个明确边界：当前产品配置没有启用独立的 `SceneCollectionSurface`
feature participant，因此本次验证的是真实付款申请 ActionView 集合页，而不是
伪称 `SceneReadonlyCollectionRenderer` 已在产品中启用。独立 Scene Collection
已从本批启用范围中正式移出，继续保留既有 feature-gated 机制，待真实消费者
启用后另立验收批次。
