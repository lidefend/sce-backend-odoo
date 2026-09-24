# 通用关系控件收敛到官方 Select 驱动（2026-09-24）

状态：Batch A/B/C 代码与守卫已完成；R5 浏览器验收证据见文末“验收证据”。
本地只跑定向验证；完整集成检查交远端 PR。

## 层与边界声明

- Formal Product Layer：P0 平台通用产品。通用关系字段渲染属于平台机制；P4 仅承担守卫、验收脚本与生成清单。
- Layer Target：`frontend/apps/web/src/components/design-system/ScRelationField.vue`（关系选择原语）、
  `frontend/apps/web/src/components/design-system/relationSelectPanelA11y.ts`（官方面板 ARIA 投影）、
  `frontend/apps/web/src/components/professional-fields/ProfessionalMany2oneFieldControl.vue`（业务面板包装）、
  `frontend/apps/web/src/components/professional-fields/professionalRelationFieldModel.ts`（关系字段状态模型）、
  `frontend/apps/web/src/components/template/FormSection.vue`（关系字段装配）、
  `frontend/apps/web/src/pages/contractForm/`（关系查询、创建意图、保存联动运行时）。
- Module：frontend（web app）+ P4 证据工具。
- Standard vs User-Specific：平台通用规则。控件不得承载任何行业、客户或某个模型的语义。
- Why Here：一个通用关系控件必须由唯一的官方驱动负责候选浮层与键盘选择，业务运行时只负责权限、
  查询、创建意图、保存与 onchange。
- Why Not Elsewhere：不在页面层或业务模块里补写浮层/焦点逻辑；不把 TDesign 的私有 DOM 作为依赖；
  不改后端契约、数据库、权限、路由与菜单。
- Blast Radius：所有契约表单的 many2one 字段（含只读投影标记）、关系字段守卫与验收脚本、
  前端生成清单（driver takeover / rendering detail / visual projection / official design alignment）。

## 交互归属（本轮确立的统一原则）

先使用当前版本官方组件的能力和推荐用法；官方扩展接口能满足的通过接口扩展；只有明确的产品需求缺口
才允许自定义，且每项自定义都要说明官方能力缺在哪里。

| 层级 | 负责内容 | 不应承担 |
|---|---|---|
| 官方组件 | 输入、候选选择、键盘操作、焦点、浮层定位与开关、基础无障碍 | 业务权限、数据创建、保存 |
| `Sc*` 适配层 | 类型明确的属性与事件映射、主题、统一外观、必要的无障碍属性 | 重新实现候选列表、方向键、失焦时序 |
| 业务关系控件 | 将契约能力映射为选项和动作，连接“搜索更多／维护／创建”入口 | 第二套浮层、第二套键盘选择逻辑 |
| 关系运行时 | 查询、请求取消与旧响应隔离、明确创建、错误状态 | 操纵 DOM 焦点、推测用户创建意图 |
| 表单运行时 | 真实字段值、草稿、onchange、校验与提交 | 把搜索词当字段值，把失焦当提交 |

## 问题（本轮根因）

1. 控件选了 `AutoComplete`（字符串补全）却在外层重新实现记录选择器的浮层、候选列表、方向键、
   Enter/Escape、焦点抑制与延时 `blur()`，等于维护两套叠加的交互生命周期。
2. `ScRelationField` 只把 `change` 折成字符串并伪造 `Event`，业务层拿不到“查询变化/选中记录”两种语义。
3. 搜索文字与业务值共用一个 `relationKeywords`：不改变 ID 只留查询词会出现“显示 B、实际还是 A”；
   直接提交查询词又会出现失焦修改与隐式创建。
4. 暂存创建先把关联置为 `false` 再标记字段变更，等于把“创建意图”伪装成“关联被清空”，
   可能触发空关联 onchange。

## 目标契约（已实现）

```text
ProfessionalMany2oneFieldControl（业务包装：能力判定 + 面板动作）
  └─ ScRelationField（设计系统原语，驱动 = TDesign Select）
       value        = 记录 ID（业务值，唯一权威）
       inputValue   = 搜索词（瞬态，仅存在于查询通道）
       options      = 候选（value=ID，label=显示名）
       popupVisible = 由原语与官方浮层共同持有
       #panel-actions 槽 = 维护当前项 / 搜索更多 / 新建 / 清除选择 / 快速创建
```

- 候选浮层、键盘选择、Enter/Escape、定位由官方 `Select` 负责；不再自写候选列表与键盘循环。
- 面板动作只放进官方 `panelBottomContent` 扩展位（`ScRelationField` 暴露为 `#panel-actions`）。
- 业务运行时不持有浮层与焦点状态；`query`（查询）与 `select`（选中记录）是两种显式事件。
- 创建意图以显式暂存状态表达，不修改 `formData`，不作为“关联被清空”。
- 面板定位与开关由官方持有：`overlayClassName` 提供稳定锚点（`many2one-option-panel`），
  `aria-controls` 指向面板 id，验收脚本据此判断“该字段的面板是否已打开”，不再猜焦点。

## 官方能力核对（tdesign-vue-next@1.20.5，锁定版本）

- `useSingle`：`displayedValue = popupVisible && allowInput ? inputValue : getInputValue(value, keys)`。
  浮层关闭时输入框永远显示所选记录，未选时为空 —— 这是“搜索词不冒充选中”的官方保证。
- `popupVisible` 被显式传入时 `useDefaultValue` 走受控分支，`inputValue` 同理；
  传入字符串 `input-value` 才能保持受控（传 `undefined` 会退回内部状态）。
- `isRemoteSearch = (filterable || 全局 filterable) && isFunction(onSearch)`；
  此时 `displayOptions = options`（不做本地过滤），标签从 options 解析 —— 因此
  必须绑定 `@search`，并且必须把当前已选记录补进候选（`primitiveOptions` 的合成行）。
- `handlerPopupVisibleChange` 仅在 `trigger === 'trigger-element-click'` 且打开时清空输入；
  于是“点击输入框 = 官方清空搜索词”，映射到运行时的 `update:queryValue('')`
  即“退出搜索并重载默认候选”，不需要额外自写逻辑。
- 官方选项行是 `<li class="t-select-option">`（悬停类 `t-select-option__hover`），
  选项列表为 `ul.t-select__list`，**没有** listbox/option role，也没有 option 行插槽。
- 弹层 portal 到 `document.body`（`Popup.props.attach` 默认 `'body'`，`getAttach` 解析为 body）。
  因此面板不是字段子节点，任何字段内选择器都必须改为页面级 + 稳定锚点类名。

## 允许的自定义交互（三项问答）

唯一新增自定义：`relationSelectPanelA11y.ts` 的官方面板 ARIA 投影。

1. **具体产品需求**：读屏用户需要能被告知“候选列表存在”和“当前高亮的是哪个候选”，
   否则关系字段在键盘下无法被无障碍使用。
2. **官方能力不足在哪里**：1.20.5 的 `Select` 渲染 `li.t-select-option` 时既不给 `role="option"`／
   `aria-selected`，也不给选项列表 listbox role，且公开 API 没有 option 行插槽，
   无法通过官方扩展接口补齐。
3. **放在哪一层、如何验证、如何退出**：放在 `ScRelationField` 原语层（不经业务层，
   不改官方组件内部）。验证由 `frontend_form_system_audit.mjs` 的
   `arrow_navigation`（`aria-activedescendant` 指向 `role="option"` 行）与
   `escape_closes_and_retains_focus` 承担。退出条件：官方 `Select` 提供 option role 或 option 行插槽后删除本模块。

投影只写属性、不接管任何交互：键盘、焦点、选择、浮层生命周期仍在官方组件手里；
投影仅把官方自身状态（悬停行、所选值）镜像成 ARIA 属性，并提供稳定自动化锚点
`data-relation-option-value`（仅在渲染行数与选项数一致时写入，虚拟滚动窗口下不写，避免错位）。

## 状态分离（R4）

- `many2oneTextValue` = 仅所选记录显示名（去掉查询词回退）；`relationQueryKeyword` = 仅搜索词，独立通道。
- `resolveProfessionalMany2oneDisplayValue` 先取所选候选标签，再退回显示名；搜索词永不作为显示名。
- `resolveProfessionalMany2oneQueryKeyword` 只读 `relationQueryKeyword`，不做任何回退。
- 暂存创建意图改为 `{keyword, recordKey, stagedValue}`，在关联值与暂存时的值发生分歧时失效；
  不再把 `formData[name]` 写成 `false`（旧的 `>0` 启发式因此删除，选 B 后再暂存创建也可正常工作）。
- `pendingInlineCreateFields` / `hasPendingInlineRelationChange` 不再要求 `!formData[name]`。

## 批次

### Batch A：原语与状态模型（完成）

- `ScRelationField` 改为官方 `Select` 驱动，持有 value/inputValue/popupVisible；
  删除自写候选列表、方向键/Enter/Escape 循环、焦点抑制、延时 `blur()`、伪造 `Event`。
- 事件改为显式类型：`update:modelValue` / `update:queryValue` / `select{value,option}` / `query` /
  `clear` / `popup-visible-change{visible,trigger}` / `focus` / `blur`。
- 模型区分“显示名”与“搜索词”。验收：严格类型检查、`verify.frontend.professional_relation_field.unit`、
  `verify.frontend.primitive_adapter.unit`、`verify.frontend.lint.src`（均通过）。

### Batch B：业务运行时（完成）

- 创建意图不再置空关联；查询/选中/提交保持权限门禁；onchange 不再收到伪空关联。
- 验收：`verify.frontend.create_record_user_journey.unit`（含关系创建意图反例 8 项）通过。

### Batch C：证据与文档（完成）

- 守卫改为绑定新契约，并新增“旧自写交互已删除”的反向检查（`ScPopover`、`role="listbox"`、
  `activeIndex`、`focused`、`blur()`、`setTimeout`、`emitSelect`、`TDesignAutoComplete`、伪造 `Event`）。
- 浏览器验收脚本换成新 DOM 契约：面板地址由“字段内”改为“页面级 `.many2one-option-panel` +
  稳定锚点”，动作按钮改为“先打开官方面板再取”，选项身份改为 `data-relation-option-value`。
- 旧的自写交互路径按“官方优先”原则替换：
  - 裸 `Enter` 的“精确/包含自动提交”删除，改为官方键盘选择（`ArrowDown` → `Enter`）。
  - 搜索关键词单独输入不再被视为清空/提交；清空改为面板中的显式“清除选择”动作。
  - 字段内自建选项行（`many2one-option-row`）与自写内联创建行选择器删除。

## 不做清单

- 不升级 `tdesign-vue-next@1.20.5`，不使用私有 `lib/cjs` 入口。
- 不新建 Compose project、数据库、端口、卷、凭据或 fixture。
- 不改后端契约、权限模型、菜单、路由与业务模型语义。
- 本批不做会计与收款专题修复。

## R6 清理结论

- 删除：自写候选浮层/键盘/失焦时序、伪造 DOM `Event`、`many2one-option-row`/`many2one-actions` 结构与样式。
- 保留（并有理由）：`FormSection.vue` 的 many2one 回退分支。它不是第二套交互，而是同一原语在
  `componentRenderer !== 'ProfessionalRelationFieldControl'` 时的原语级装配路径，删掉会改变未分类
  many2one 渲染；它复用同一个 `ScRelationField`，不存在双浮层/双键盘。
- 保留：`restoreSearchOnCancel` 生命周期参数仍被 `openRelationCreateForm` 与新建对话框运行时使用
  （“搜索弹窗 → 新建子表单 → 取消后恢复搜索上下文”），不是死代码。
- 记录遗留缺口：`relationDescriptor` 在候选为空时会合成 `#<id>` 标签，若后端未回填 `display_name`，
  该合成文本可能作为显示名出现。此为改动前既有问题，不在本批范围。

## 回滚

- 回滚单位：Batch A / B / C 各自独立提交；生成清单必须与来源一起回滚。
- 停止条件：官方公开 API 在锁定版本不可用、类型检查失败、或既有保存/失败恢复证据出现回归时，
  停止后续浏览器验收，仅修复本层后重新冻结。

## 验收证据

### L0/L1/L2（本地定向）

| 层 | 命令 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | PASS（`coverage=L1_only`，16 tests OK，policy guard PASS） |
| L2 | `make verify.frontend.professional_relation_field.unit` | PASS（模型 matrix=18 反例=13；守卫反向检查 6+28 tests） |
| L2 | `make verify.frontend.primitive_adapter.unit` | PASS（`components=46`，31 tests） |
| L2 | `make verify.frontend.create_record_user_journey.unit` | PASS（关系创建意图反例 8 项） |
| L2 | `make verify.frontend.canonical_form_presenter.unit` | PASS（cases=170） |
| L1 | `make verify.frontend.lint.src` | PASS（0 error） |
| L1 | `pnpm run typecheck:strict` | PASS（干净） |

上表在批次 B 面板宽度修复后已重跑：`ci.local.iteration` PASS（16 tests）、
`professional_relation_field.unit` PASS（28 tests）、`primitive_adapter.unit` PASS（31 tests）、
`lint.src` PASS（0 error，39 warning）、`typecheck:strict` PASS。

### 批次 B 修复：窄视口面板宽度（R5-7 反例）

`make local.dev.project_profile_write_browser … RELATION_ONLY=1`（专用对象 3930）首次运行：
`customer_query_blur_preserves_draft`、`customer_search_cancel_and_overlay` PASS，
`customer_narrow_escape_no_write` FAIL。原因是 1440px 打开面板后缩到 390px 再打开，面板仍为
`542px`，`document.documentElement.scrollWidth (542) > innerWidth (390)`，页面产生横向溢出。

官方核对（已安装 TDesign Vue Next 1.20.5）：

- `esm/select-input/hooks/useOverlayInnerStyle.js`：默认 `matchWidthFunc` 取
  `max(triggerWidth, popupElement.offsetWidth)`，只夹到固定 `MAX_POPUP_WIDTH = 1000`，不按视口收敛；
  上一次的内联宽度会回灌进 `max`，因此面板只增不减。
- `esm/popup/popup.js`：`updateOverlayInnerStyle()` 只在
  `watch([overlayStyle, overlayInnerStyle, overlayEl])` 与 `Container` 首次 `contentMounted` 时执行；
  `esm/popup/container.js` 的内容节点首次可见后不会卸载。实测（诊断脚本，未入库）：关闭后清空
  `.t-popup__content` 的内联 `width`，重开仍为空，证明官方不会在重开或视口变化时重新计算。
- `esm/select/select.js`：`popupProps` 中除 `overlayClassName` 外的键经 `useEventForward`
  透传给 `SelectInput`，因此 `popupProps.overlayInnerStyle` 是可达的官方覆盖入口。

修复（仅使用官方接口，未新增交互代码）：`ScRelationField.vue` 的 `popupProps` 提供
`overlayInnerStyle(trigger)`，按“打开时视口宽度 − 16px”夹取触发宽度；`panelViewportWidth`
在每次打开时记录视口，使该样式对象在重开时获得新标识，从而走官方响应式重应用路径。
修复后 1440px 面板仍等于触发宽度（542px，无回归），390px 重开为 323px（右边界 349 < 390）。

新增自定义基础交互三问：

1. 具体产品需求：窄视口（390px）下面板不得超出视口，页面不得出现横向滚动。
2. 当前官方组件及扩展接口为何不满足：`popupProps.overlayInnerStyle` 虽是官方入口，但官方只在
   面板内容挂载时应用一次，重开与视口变化都不重算；默认宽度策略也只按固定 1000px 收敛，
   无法表达随视口变化的约束。
3. 增强放在哪一层、如何验证、如何退出：放在 `Sc*` 适配层的外观职责内（`popupProps`），
   用 `RELATION_ONLY` 的 390px 断言验证；当官方组件在打开或尺寸变化时重新测量面板宽度后，
   即可删除该函数。

### L4（受管环境浏览器验收）

见下方“R5 场景矩阵”表；脚本、环境与结果在完成时回填。

## R5 场景矩阵

| 场景 | 载体 | 结果 |
|---|---|---|
| A→搜索 B→失焦/Escape/弹窗取消：显示恢复、ID 与草稿不变 | 待回填 | 待回填 |
| 鼠标与键盘选择 B：显示名/ID/修改状态一致 | 待回填 | 待回填 |
| 明确清除：可选字段可保存刷新为空；必填字段阻止保存 | 待回填 | 待回填 |
| 查询失败/零结果/恢复/快速连续搜索：旧响应不覆盖新结果 | 待回填 | 待回填 |
| 有权限显式创建：失败可恢复、重试不重复；无权限无创建入口 | 待回填 | 待回填 |
| 保存失败保留草稿，重试成功后刷新回读一致 | 待回填 | 待回填 |
| 桌面与 390px：候选可操作、无重复浮层与横向溢出、取消后焦点合理 | 待回填 | 待回填 |
