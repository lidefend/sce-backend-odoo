# ADR-FE-RENDERER-02C-02A：薄层 Primitive Adapter 架构裁定

- 文档状态：所有者方向已裁定，等待独立架构评审；本 ADR 不授权产品代码迁移
- 审计基线：`c8be18bc26cb262a30764a53b9d0765f646427aa`
- 日期：2026-11-08
- Formal Product Layer：P0 platform kernel product
- Layer Target：Frontend renderer / Scene composition / Sc primitive authority boundary
- Module：Sc Design System、`@sc/ui` Scene composition、Primitive Port、Web Sc Adapter
- Standard vs User-Specific：platform engineering standard
- 英文版本：[frontend_thin_primitive_adapter_adr_v1.en.md](frontend_thin_primitive_adapter_adr_v1.en.md)

## 1. 决策

保留 Sc Design System 与 `@sc/ui` 两个体系，但重新冻结它们的权威和依赖方向：

1. Sc Design System 是唯一基础组件权威。
2. `@sc/ui` 只承担 Scene 页面区域、布局和组合，不实现第二套基础控件。
3. `@sc/ui` 定义由 Scene 需要、但不含 TDesign 属性的 Primitive Port。
4. Web 产品运行时提供 Sc-backed adapter，将 Port 映射到 `ScButton`、`ScInput`、`ScSelect`、`ScDateField`、`ScTextarea`、`ScTable` 和平台图标。
5. TDesign 与 Browser Native 是 Sc 内部可选择的实现细节，不是 Scene 或用户可选择的第二组件权威。
6. TDesign Bridge 归属 Web 的 Sc Design System 实现边界；不新建 `@sc/tdesign` package。
7. 设计 Token 的唯一来源是 `frontend/packages/design-tokens`；`@sc/ui` 只保留 `compact` / `cozy` 场景密度语义，不维护第二套颜色、圆角或控件高度事实。
8. `SceneObjectPage`、`SceneCollectionSurface`、`SceneHierarchySurface` 等专业场景组合能力保留，不迁入 Sc，也不被合并掉。

本 ADR 只记录架构事实、目标协议、迁移图、守卫和验收边界。它不修改产品代码，不删除旧驱动，不改变运行态，也不宣称迁移完成。

## 2. 为什么需要这次优化

当前问题不是“组件库数量太多”，而是同一基础能力存在三个相互冲突的权威：

- 厂商桥接权威被放在 `@sc/ui/primitives`。
- 基础控件视觉和交互权威在 Sc。
- Scene 又通过自己的 Kit Runtime 决定使用 TDesign 还是 Native。

由此形成反向依赖：

```text
Sc Design System
      |
      v
@sc/ui/primitives
      |
      v
TDesign
```

同时产品运行态又依赖 `@sc/ui` 的 Scene 组合。这使 `@sc/ui` 同时成为“厂商统一出口”和“上层场景库”，无法独立演进。

两套基础控件驱动还重复承担属性映射、事件映射、readonly/disabled、错误态、密度和 Native 回退。Scene 自有的业务语义和 Token 值进一步造成平台表达与设计规范的双来源。

因此本轮是有限的架构减负：减少重复的基础实现和运行时选择机制，保留 Scene 的专业组合能力。

## 3. 只读审计事实

### 3.1 `@sc/ui` 的职责与消费者

`frontend/packages/ui/src` 当前有 30 个文件，其中 12 个 Vue 组件。组件分类如下：

| 类别 | 组件 | 当前职责 | 目标职责 |
| --- | --- | --- | --- |
| Scene 页面组合 | `SceneObjectPage`、`SceneCollectionSurface`、`SceneHierarchySurface` | 页面区域和业务场景组合 | 保留 |
| Scene 布局/内容组合 | `ScenePageFrame`、`SceneWorkspaceHeader`、`SceneActivityTabs`、`SceneNotice`、`SceneReviewPanel` | 组合布局、事实和活动区域 | 保留 |
| Scene 基础控件 | `SceneFieldControl`、`SceneButton`、`SceneRelationTable` | 同时驱动 TDesign 或 Native | 改为 Primitive Port 薄适配 |
| 适配器容器 | `SceneUiProvider` | 加载 Kit、选择 Driver、注入 Token 和 Density | 简化为 Primitive Adapter 和密度上下文 |

应用源码中实际 `@sc/ui` 导入共 11 处：

| 消费者 | 当前用途 | 处理方向 |
| --- | --- | --- |
| `pages/contractForm/ContractFormDriverHost.vue` | `SceneUiProvider`、`SceneButton` | 保留 Provider；操作区直接使用 `ScButton` |
| `pages/contractForm/CanonicalActionBar.vue` | 直接使用 `SceneButton` | 改为 `ScButton` |
| `components/template/FormSection.vue` | `SceneFieldControl`、可选 Kit Context | Scene 试点字段经 Port 调用 Sc |
| `components/action/SceneReadonlyCollectionRenderer.vue` | `SceneUiProvider`、`SceneCollectionSurface` | 保留只读组合，移除 Kit 选择 |
| `pages/contractForm/useContractFormComponentDriverRuntime.ts` | Kit 决策、偏好读写 | 随迁移逐步退役 |
| `app/action_runtime/useActionViewSceneComponentDriverRuntime.ts` | 集合 Scene 决策、偏好读写 | 随迁移逐步退役 |
| `app/renderers/sceneComponentDriverPolicy.ts` | Scene/Form Driver 策略 | 由单一 Primitive Adapter 取代 |
| `app/renderers/sceneReadonlyCollectionBridge.ts` | Scene 组合契约桥 | 保留 Scene 数据适配 |
| `components/template/contractFormDriverField.ts` | Scene Field DTO 映射 | 保留并改为 Port DTO |
| `components/design-system/tdesignPrimitiveBridge.ts` | 从 `@sc/ui/primitives` 获取 TDesign | 迁入 Web Sc Design System 内部 |
| `components/design-system/scIcon.ts` | 从 `@sc/ui/icons` 获取 TDesign 图标 | 改为 Web 内部 Icon Adapter |

`SceneObjectPage` 和 `SceneHierarchySurface` 当前没有 apps/web 消费者。它们仍是有效的 Scene 组合能力，不是无消费者即可删除的代码。

Form Scene 路径只覆盖被 Feature Flag 和字段类型允许的一部分字段；只读集合路径只允许无修改动作、无选择能力的页面。当前并非“所有业务页面都已迁移到 Scene”。

### 3.2 TDesign 运行时依赖

- `frontend/packages/ui/package.json` 直接依赖 `tdesign-vue-next@1.20.5` 和 `tdesign-icons-vue-next@0.4.9`。
- `frontend/packages/ui/src/primitives.ts` 导出 61 个带 `TDesign` 前缀的符号（含类型别名），覆盖 Input、Button、Select、Table、Dialog、DatePicker、Form、Descriptions、Tree、Upload 等。
- `frontend/packages/ui/src/icons.ts` 导出 49 个 TDesign 图标。
- `frontend/packages/ui/src/kits/tdesign/register.ts` 直接导入 TDesign 组件和样式，实现 `tdesign-modern` Scene Driver。
- `SceneHierarchySurface`、`SceneReviewPanel`、`SceneObjectPage`、`SceneWorkspaceHeader` 直接使用 `@sc/ui/icons` 中的 TDesign 图标包装。
- Sc Design System 当前有 63 个 `Sc*.vue` 组件，其中 52 个消费 `tdesignPrimitiveBridge`。
- `tdesignPrimitiveBridge.ts` 从 `@sc/ui/primitives` 导入 TDesign，形成 `Sc -> @sc/ui -> TDesign` 的架构反向边。

结论：`@sc/ui` 目前不是纯 Scene 组合包，而是同时承担厂商桥接和上层组合。

### 3.3 双驱动与 Kit 选择

当前有两个真实运行机制：

```text
A: ScInput / ScSelect / ScButton / ScTable
       -> tdesignPrimitiveBridge
       -> TDesign / Browser Native

B: SceneFieldControl / SceneButton / SceneRelationTable
       -> SceneUiProvider
       -> SceneUiDriverRuntime
       -> Native HTML / TDesign
```

- `SceneUiKitId` 只有 `sc-native` 和 `tdesign-modern`。
- 两个 Kit 声明几乎相同的能力集合。
- `sceneComponentDriverPolicy.ts` 将 `allowUserOverride` 固定为 `false`。
- 两条 Runtime Hook 仍读取和写入 `scene_ui_driver` 用户偏好。
- apps/web 实际挂载 `SceneUiProvider` 的入口只有 `ContractFormDriverHost.vue` 和 `SceneReadonlyCollectionRenderer.vue`。
- `SceneUiProvider` 继续通过动态 Driver Loader 和 fallback Kit 决定基础组件实现。

因此当前系统并没有形成有效的“用户自由选择组件库”产品能力，却保留了相应的策略、偏好、遥测、回退和双实现复杂度。

### 3.4 业务语义重复

`@sc/ui` 当前自己决定以下业务表达：

- `SceneFieldControl.vue` 在 TDesign 和 Native 两条路径都硬编码 `CNY`。
- `SceneRelationTable.vue` 使用 `row.values[column.key] || '无'`。
- `SceneCollectionSurface.vue` 的移动卡片也使用 `|| '无'`。
- `SceneObjectPage.vue` 的只读事实使用 `field.value || '无'`。
- `SceneTone` 与 `data-tone` 样式形成本地状态语汇。
- `sceneFieldControlValue.ts` 在 Scene 内再次规范化字段值。

这些行为绕过了已进入主线的 `frontend/apps/web/src/app/presentation/businessValuePresentation.ts`。金额币种、金额精度、空值文本、状态标签和日期显示必须由平台业务表达层给出已经解释后的结果；Scene 只负责放置和组合。

### 3.5 Token、Theme 与 Density 重复

权威包 `frontend/packages/design-tokens` 已定义 primitive、semantic、component 和 pattern Token。`component.json` 已包含 button、input 和 table 的高度、圆角、间距与焦点参数。

但当前仍存在第二套事实：

- `frontend/packages/ui/src/kits/tokens.ts` 定义 `enterprise-neutral`、`business-soft`、`accessible-contrast` 三套颜色、品牌、状态、焦点和圆角。
- `apps/web/src/styles/tokens/profile.css` 又按相同 ID 重复声明品牌、边界、状态和圆角。
- `frontend_theme_profile_guard.py` 目前通过比较两处值来防止漂移；这实际上把“双来源相等”锁成了规则，而不是验证单一来源。
- `SceneUiProvider.vue` 使用本地 Token 值作为 CSS fallback，并直接声明 `cozy=44px`、`compact=36px`。
- `SceneObjectPage.vue` 还在 `:root` 声明本地 `--sc-scene-*` 值。
- apps/web 没有传入 `tokenProfile`，但两个真实 Provider 入口仍会触发 Provider 的默认本地值。

目标不是删除明暗 Theme 或 Theme Profile，而是让 profile 只覆盖 semantic Token，让 Scene density 成为映射到 component Token 的语义，不再在 `@sc/ui` 保存第二套设计数值。

### 3.6 文档与守卫事实

`docs/frontend_productization/runtime-theme-profile-switching.md` 称 apps/web 从不挂载 `SceneUiProvider`。该陈述已过时：当前有两个受管使用入口。准确的剩余事实是“没有 apps/web 调用方传入 `tokenProfile`”，不是“Provider 未挂载”。

现有守卫也必须纳入迁移：

- `scripts/verify/frontend_primitive_adapter_guard.py` 当前要求 Web Bridge 从 `@sc/ui/primitives` 获取 TDesign，因此守卫本身阻止了目标依赖方向。
- `scripts/verify/frontend_scene_component_bridge_guard.py` 当前要求 `@sc/ui/form`、Provider、Kit 选择和旧驱动接线继续存在，并检查 Scene Driver 行为。
- `frontend/apps/web/scripts/primitive_adapter_contract_test.ts` 验证 Sc Primitive 的标识、事件与部分交互，但没有验证 Scene Port 到 Sc 的等价性。
- `frontend/apps/web/scripts/scene_component_driver_bridge_test.ts` 验证旧 Kit/Runtime 决策，但没有验证同一字段经普通 FormSection 与 SceneFieldControl 的运行时一致性。
- `frontend_business_semantics_guard.py` 只扫描 apps/web，不会阻止 `@sc/ui` 新增 `CNY`、`无` 或本地状态语汇。

守卫迁移必须与实现同步，不能先让实现违反现有守卫，也不能为了保留旧守卫而保留错误依赖。

## 4. 目标架构

### 4.1 四层

| 层 | 责任 | 权威边界 |
| --- | --- | --- |
| L1 Vendor Layer | TDesign / Browser Native | 不掌握平台业务语义 |
| L2 Platform Primitive Authority | Sc Design System | 唯一基础组件和 Sc 内部驱动权威 |
| L3 Scene Composition | `@sc/ui` | 页面区域、布局和 Scene 组合 |
| L4 Product Runtime | Vue Web Application | Contract V2、业务表达、Renderer、权限、操作和 Adapter 装配 |

### 4.2 允许的依赖方向

```text
Product Runtime
      |
      +-------------------> Sc Design System
      |                           |
      |                           v
      |                     TDesign / Native
      |
      +-------------------> @sc/ui
                                  |
                                  v
                          Primitive Port
                                  ^
                                  |
                          Sc-backed Adapter
                                  |
                            Product Runtime
```

规范性规则：

1. Product Runtime 可以依赖 Sc、`@sc/ui` 和 Adapter。
2. Sc 可以依赖 Web 内部的 TDesign Bridge。
3. Sc 不得依赖 `@sc/ui`、`@sc/ui/primitives`、`@sc/ui/icons` 或 Scene 组件。
4. `@sc/ui` 可以依赖 Vue、自身 DTO 和 Primitive Port。
5. `@sc/ui` 不得依赖 apps/web 内部文件、TDesign、具体 Sc Vue 实现或厂商图标类型。
6. Adapter 由 Product Runtime 提供；它可以把 Port 映射到 Sc，但不把 Sc Props 暴露为 Scene 协议。
7. Scene DTO 可以保留 `SceneField`、`SceneRelationTable` 等领域无关组合结构；业务解释结果必须是平台已解释值，不是 Scene 本地格式化结果。

### 4.3 TDesign Bridge 与图标

第一阶段不新建 workspace package。Web 内部形成：

```text
frontend/apps/web/src/components/design-system/
    ScInput.vue
    ScSelect.vue
    ScButton.vue
    ScTable.vue
    vendor/tdesignBridge.ts
    vendor/scIconAdapter.ts
```

`vendor/tdesignBridge.ts` 是 Web Sc Design System 的唯一 TDesign 运行时出口。`@sc/ui` 取消 `primitives`、`icons` 和 Scene TDesign Driver 的运行时导出后，才从 package 依赖中移除 TDesign。

迁移期允许旧导出暂时存在，但任何新 Scene 代码不得增加厂商依赖。

## 5. Primitive Port v1

### 5.1 协议目标

Port 是 Scene 与平台之间的稳定接口，不是 TDesign Props 的别名，也不是 `Record<string, Component>`。

Port v1 的强制规则：

- 受控值由调用方持有；Adapter 不得维护影子业务状态。
- `readonly` 和 `disabled` 控制不得发出值改变事件。
- `loading` 不得伪造成功值；按钮不得触发业务动作。
- 所有事件在平台能提供时必须携带真实原生事件，IME 与键盘调用方不能丢失事件身份。
- 错误态必须同时提供可感知状态和 `aria-invalid` / `aria-describedby` 关联。
- 必有或图标型按钮必须有可访问名称。
- 控件必须暴露 `focus()`；可获得焦点的控件必须发出 `focus` / `blur`。
- Port 不定义币种、金额精度、状态文案、日期展示文本或空值文本。

### 5.2 基础类型

以下为 schema 级 TypeScript 协议；实际实现由 02C-02B 在 `@sc/ui` 中落地，并以类型测试约束 Adapter。

```ts
export type ScenePrimitiveSize = 'small' | 'medium' | 'large';
export type SceneControlStatus = 'default' | 'error';
export type SceneDensity = 'compact' | 'cozy';

export interface PrimitiveHandle {
  focus(options?: FocusOptions): void;
}

export interface PrimitiveCommonProps {
  id?: string;
  name?: string;
  size?: ScenePrimitiveSize;
  status?: SceneControlStatus;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  loading?: boolean;
  describedBy?: string;
  ariaLabel?: string;
}

export interface ControlEvents {
  change: [value: string, event: Event];
  focus: [value: string, event: FocusEvent];
  blur: [value: string, event: FocusEvent];
  keydown: [event: KeyboardEvent];
  keyup: [event: KeyboardEvent];
}
```

### 5.3 ButtonPort

```ts
export interface ButtonPortProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: ScenePrimitiveSize;
  disabled?: boolean;
  loading?: boolean;
  loadingLabel?: string;
  accessibleLabel?: string;
}

export interface ButtonPortEmits {
  activate: [event: MouseEvent | KeyboardEvent];
  focus: [event: FocusEvent];
  blur: [event: FocusEvent];
}

export interface ButtonPortSlots {
  default(): unknown;
}
```

要求：

- Enter/Space 激活；禁用或 loading 时不激活。
- 图标型或省略文本时必须提供 `accessibleLabel`。
- `loading` 必须暴露忙碌状态和可读的加载文案。
- Product Runtime 的操作区直接使用 `ScButton`；Scene 的 `SceneButton` 只作为组合层薄包装。

### 5.4 InputPort

```ts
export interface InputPortProps extends PrimitiveCommonProps {
  value: string;
  type?: 'text' | 'search' | 'number' | 'email' | 'tel' | 'url' | 'password';
  inputMode?: 'text' | 'decimal' | 'numeric';
  placeholder?: string;
  autocomplete?: string;
  min?: string | number;
  max?: string | number;
  step?: string | number;
  maxLength?: number;
}

export interface InputPortEmits extends ControlEvents {
  'update:modelValue': [value: string];
  input: [value: string, event: Event];
  compositionstart: [event: CompositionEvent];
  compositionend: [event: CompositionEvent];
}

export interface InputPortSlots {
  prefix?(): unknown;
  suffix?(): unknown;
}
```

要求：

- IME `compositionend` 必须保留真实事件，Scene 不得重新推导组合文本。
- readonly/disabled/loading 不得发出值改变。
- 金额的币种和精度不在 InputPort 内表达。

### 5.5 SelectPort

```ts
export interface SelectPortOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectPortProps extends PrimitiveCommonProps {
  value: string;
  options: readonly SelectPortOption[];
  placeholder?: string;
  filterable?: boolean;
  emptyText?: string;
}

export interface SelectPortEmits extends ControlEvents {
  'update:modelValue': [value: string];
  search: [query: string];
  popupVisibleChange: [event: { visible: boolean; trigger: string }];
}
```

要求：

- 提供组合框可访问名称、展开状态、错误和描述关联。
- 键盘打开、选择、搜索、Escape 和焦点移动必须由 Sc 实现并通过契约测试。
- 迁移前必须补齐或包装 ScSelect 当前缺失的 `focus` / `blur` / 原生 change 事件事实。

### 5.6 DateFieldPort

```ts
export interface DateFieldPortProps extends PrimitiveCommonProps {
  value: string;
  format: 'YYYY-MM-DD' | 'YYYY-MM-DD HH:mm:ss';
  placeholder?: string;
  clearable?: boolean;
}

export interface DateFieldPortEmits extends ControlEvents {
  'update:modelValue': [value: string];
}
```

要求：

- `format` 是值协议，不是展示文案；展示文本由平台业务表达层提供。
- 必须验证焦点、清空、键盘输入和弹层关闭。
- 当前 `ScDateField` 只有 `update:modelValue`，缺少 change/focus/blur；02C-02B 必须先解决该 Conformance Gap。

### 5.7 TextareaPort

```ts
export interface TextareaPortProps extends PrimitiveCommonProps {
  value: string;
  placeholder?: string;
  rows?: number;
  maxRows?: number;
}

export interface TextareaPortEmits extends ControlEvents {
  'update:modelValue': [value: string];
  input: [value: string, event: Event];
}
```

要求：

- 保持 rows/autosize、焦点和错误语义一致。
- ScTextarea 内部可以选择 TDesign 或 Native，但 Port 不暴露厂商属性。

### 5.8 TablePort

```ts
export interface TablePortColumn {
  key: string;
  label: string;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

export interface TablePortRow {
  id: string | number;
}

export interface TablePortProps<Row extends TablePortRow> {
  rows: readonly Row[];
  columns: readonly TablePortColumn[];
  rowKey?: keyof Row & string;
  loading?: boolean;
  emptyText?: string;
  interactiveRows?: boolean;
  selectionMode?: 'none' | 'single' | 'multiple';
  selectedRowKeys?: readonly (string | number)[];
  accessibleLabel: string;
}

export interface TablePortEmits<Row extends TablePortRow> {
  rowActivate: [row: Row, event: Event];
  selectionChange: [keys: Array<string | number>, event: Event];
}

export interface TablePortSlots<Row extends TablePortRow> {
  topContent?(): unknown;
  empty?(): unknown;
  cell?(props: { row: Row; column: TablePortColumn }): unknown;
}
```

要求：

- 行激活与选择是不同动作。
- 可交互行必须支持键盘激活并保持可访问名称。
- 水平滚动区域不能吞掉 Focus。
- 表格空态由平台已经解释的 `emptyText` 提供，Scene 不自行写 `无`。

### 5.9 IconPort

```ts
export type SceneIconName =
  | 'check' | 'close' | 'chevron-down' | 'chevron-right'
  | 'file' | 'folder' | 'refresh' | 'search' | 'user';

export interface IconPortProps {
  name: SceneIconName;
  size?: 14 | 16 | 18 | 20 | 24;
  label?: string;
  decorative?: boolean;
}
```

要求：

- Scene 只使用语义图标名，不导入 TDesign Icon 组件。
- `decorative=true` 时从辅助技术隐藏；非装饰图标必须有 `label`。
- Web Icon Adapter 将语义名映射到 `ScIcon`。

### 5.10 Adapter 注入

```ts
export interface PrimitivePortDefinition<Props, Emits, Slots> {
  props: Props;
  emits: Emits;
  slots: Slots;
  exposed: PrimitiveHandle;
}

export interface PrimitiveBinding<Props, Emits, Slots> {
  component: Component;
  readonly contract: PrimitivePortDefinition<Props, Emits, Slots>;
}

export interface ScenePrimitiveAdapter {
  Button: PrimitiveBinding<ButtonPortProps, ButtonPortEmits, ButtonPortSlots>;
  Input: PrimitiveBinding<InputPortProps, InputPortEmits, InputPortSlots>;
  Select: PrimitiveBinding<SelectPortProps, SelectPortEmits, Record<never, never>>;
  DateField: PrimitiveBinding<DateFieldPortProps, DateFieldPortEmits, Record<never, never>>;
  Textarea: PrimitiveBinding<TextareaPortProps, TextareaPortEmits, Record<never, never>>;
  Table: PrimitiveBinding<TablePortProps<TablePortRow>, TablePortEmits<TablePortRow>, TablePortSlots<TablePortRow>>;
  Icon: PrimitiveBinding<IconPortProps, Record<never, never>, Record<never, never>>;
}

export interface SceneCompositionContext {
  primitives: ScenePrimitiveAdapter;
  density: SceneDensity;
}
```

`PrimitiveBinding.component` 的实际包装必须在 02C-02B 使用 Vue `DefineComponent`、`ComponentProps` / `ComponentEmits` / `SlotsType` 类型断言或等价机制证明其符合 `contract`，禁止退化为无类型组件字典。`contract` 同时作为组件契约测试的运行时声明，不得只存在于文档。

### 5.11 Provider 目标

```ts
interface SceneUiProviderProps {
  primitives: ScenePrimitiveAdapter;
  density?: SceneDensity;
  compositionContext?: SceneCompositionContext;
}
```

目标 Provider 只负责：

- 注入 Primitive Adapter。
- 注入 `compact` / `cozy` 场景密度。
- 提供 Scene 组合上下文。

Provider 不再负责：

- 选择 `sc-native` / `tdesign-modern`。
- 动态加载厂商 Driver。
- 在 Driver 失败时切换另一套基础控件。
- 维护颜色、圆角、控件高度或业务文案。

## 6. 组件和依赖迁移计划

### 6.1 阶段依赖图

```text
02C-02A  ADR（本批）
      |
      v
02C-02B  Primitive Port v1 + Sc Adapter + Conformance Tests
      |
      +----> 02C-02C-1  Product direct actions: SceneButton -> ScButton
      |
      +----> 02C-02C-2  SceneFieldControl -> ScInput/Select/Date/Textarea
      |
      +----> 02C-02C-3  SceneRelationTable -> ScTable
                              |
                              v
02C-02D  Driver / Kit / Preference / Vendor / Token / Guard 收口
```

### 6.2 02C-02B

交付：

- `@sc/ui` Port 类型、Provider 注入和 Adapter 契约测试。
- Web `createScScenePrimitiveAdapter()` 薄包装。
- ScDateField、ScSelect 等缺失事件与可访问性能力的缺口清单和最小补齐。
- 新旧路径 Feature Flag；不迁移全部消费者。

退出条件：

- Port 类型不含 TDesign 类型。
- Adapter 通过类型检查和组件契约测试。
- `@sc/ui` 不新增 apps/web 或具体 Sc Vue import。

### 6.3 02C-02C

三个真实样板：

1. SceneButton → ScButton；同时清理 `CanonicalActionBar` 和 `ContractFormDriverHost` 的操作区旁路。
2. SceneFieldControl → ScInput / ScSelect / ScDateField / ScTextarea，保留 SceneField DTO。
3. SceneRelationTable → ScTable，保留 Scene 表格组合和行导航语义。

每个样板必须独立开关、独立验证、可独立回滚。通过“同一字段普通 FormSection 直用 Sc”和“SceneFieldControl 经 Port 使用 Sc”的比较矩阵。

### 6.4 02C-02D

顺序：

1. 停止产生新的 `scene_ui_driver` 偏好，保留历史读取。
2. 迁移所有 Scene 控件和 TDesign Scene Driver。
3. 将 TDesign Bridge 和图标桥移入 Web Sc Design System。
4. 从 `@sc/ui` 移除 `primitives`、`icons` 和厂商 Driver 运行时依赖。
5. 将 Scene density 映射到 design-token component Token。
6. 删除旧 Kit Registry、Native Driver 和用户 Kit 选择机制。
7. 更新过时的主题文档，并把守卫改为目标方向。

## 7. 守卫设计

| 目标守卫 | 现有锚点 | 必须新增或改变的断言 |
| --- | --- | --- |
| `scene_vendor_dependency_guard` | `frontend_primitive_adapter_guard.py`、Scene Bridge Guard 的 vendor import 检查 | 禁止 `@sc/ui` 导入 TDesign/TDesign Icons；唯一厂商出口移至 Web Sc Design System；逆向继承旧依赖路径必须失败 |
| `scene_primitive_authority_guard` | `frontend_scene_component_bridge_guard.py` | Scene 基础交互控件必须经 Port；允许布局 section/div/dl 和专用组合；禁止 Scene 重新实现 button/input/select/textarea/table 基础交互 |
| `scene_semantic_authority_guard` | `frontend_business_semantics_guard.py` | 扫描 `@sc/ui`，禁止本地币种、金额格式、空值文案和状态词表；Scene 只消费平台已解释值 |
| `scene_token_authority_guard` | `design_token_system.py`、`frontend_style_system_guard.py`、`frontend_theme_profile_guard.py` | 禁止 `kits/tokens.ts` 和 Scene 组件新建颜色/圆角/控件高度事实；profile 验证 semantic Token 派生，而不是双份值相等 |
| `scene_adapter_contract_guard` | `primitive_adapter_contract_test.ts`、`scene_component_driver_bridge_test.ts` | 验证全部 Port Props/Events/Slots/Focus/ARIA；验证 Scene Adapter 与 Sc 组件契约一致 |
| `scene_application_import_guard` | Scene Bridge Guard 的受管入口检查 | 普通产品页面不得直接导入 Scene 基础控件；允许 Scene 组合、受管只读 Renderer 和装配 Adapter；不禁止合法布局 HTML |

守卫的 allowlist 必须按“组件角色和受管入口”声明，不以全仓 HTML 元素黑名单代替架构判断。

现有守卫不能原样保留：

- `frontend_primitive_adapter_guard.py` 当前明确要求 `@sc/ui/primitives`。
- `frontend_scene_component_bridge_guard.py` 当前明确要求旧 Kit 选择和 Driver 接线。
- `frontend_theme_profile_guard.py` 当前明确要求 `kits/tokens.ts` 和 `profile.css` 双份值相等。

修改这些守卫属于对应当前迁移阶段的实现工作，不属于本 ADR 批次。

## 8. 验收矩阵

### 8.1 Port Conformance

| 能力 | 断言 |
| --- | --- |
| 值变化 | `update:modelValue` / `change` 值与真实 DOM/TDesign 事件一致 |
| readonly / disabled | 不发出值变化或业务激活；视觉和辅助状态明确 |
| 错误态 | `status=error`、`aria-invalid=true`、错误说明通过 `aria-describedby` 关联 |
| Focus / Blur | Adapter 暴露 `focus()`；两个方向的事件顺序与目标一致 |
| 键盘 | Button Enter/Space；Select 打开/选择/Escape；Date 输入/弹层；Table 行激活 |
| 插槽/辅助说明 | Button 内容；Input prefix/suffix；Table top/cell/empty 不丢失 |
| IME | `compositionstart` / `compositionend` 保留真实事件和提交文本 |
| 可访问性 | 控件名称、role、状态、表格区域与图标隐藏规则一致 |

### 8.2 同一业务字段双路径验收

测试必须使用同一份合成 Contract V2 字段声明，分别经过：

1. 普通 `FormSection` 直接使用 Sc 基础组件。
2. `SceneFieldControl` 经 Primitive Port 和 Web Sc Adapter。

比较：

| 维度 | 必须一致 |
| --- | --- |
| 值变化 | 输入、选择、日期、文本域最终回调值 |
| readonly / disabled | 是否可编辑及是否发出事件 |
| 错误显示 | 可见错误和 `aria-invalid` / `aria-describedby` |
| Focus / Blur | 事件顺序、目标值、可访问焦点 |
| 键盘操作 | Enter、Space、Escape、Tab、方向键 |
| 插槽/辅助说明 | prefix/suffix、help、source/hint 和空态 |
| 可访问名称 | label 关联和图标按钮名称 |

这不是截图可比性证明。必须检查 DOM 事件、ARIA、焦点顺序和真实值回调。

### 8.3 分层验证

- L1：Port 类型、静态依赖方向、Adapter 契约、守卫单测。
- L2：Scene 组件非零测试、现有 Primitive Adapter 测试、业务语义测试。
- L3：受管本地开发环境验证三个样板页面。
- L4：受影响字段与集合的浏览器验收。
- L5：独立审查、当前精确 HEAD 的远端门禁和受保护 PR 集成。

本 ADR 批次仅需要文档和 `.agent` 元数据层检查；产品 L2-L4 不适用。

## 9. 回滚与兼容边界

1. 本 ADR 可通过删除文档和运行元数据回滚，不影响运行态。
2. 02C-02B 的 Port 和 Adapter 在未迁移消费者前无行为影响；回滚删除新注入行即可。
3. 02C-02C 每个样板必须在 `scene_primitive_adapter_v1` 下独立启用；失败时回退该样板，不改变 Contract V2 或数据。
4. 旧 Kit Driver 在 02C-02D 删除前保留；删除后若需回滚，应恢复前一个已评审版本，不重建旧的用户选择功能。
5. `scene_ui_driver` 只停止新写入并逐步消费存量；不做未审计的数据删除。
6. TDesign Bridge 迁移期间可以保留只读兼容导出，但新代码必须使用 Web 内部 Bridge。
7. Scene DTO、Contract V2、业务表达、权限、后端契约和持久化格式不在本计划回滚面内，因为没有计划修改它们。

## 10. 明确不做

- 不把 Sc 组件全部搬入 `@sc/ui`。
- 不把 Sc 和 `@sc/ui` 合并成巨型 package。
- 不新建第三套组件库。
- 不让所有页面经过 Scene 组合。
- 不强制所有底层控件必须使用 TDesign。
- 不立即删除 Native 实现。
- 不让用户选择 `sc-native` 或 `tdesign-modern` 作为产品功能。
- 不修改 Contract V2、Renderer Extension Protocol、业务表达、后端性能或权限架构。
- 不在本批修改产品代码、旧主题文档或运行配置。
- 不部署、不合并。

## 11. 已知缺口与风险

1. `ScDateField` 当前事件面不足，不能直接满足 DateFieldPort。
2. `ScSelect` 当前没有完整的 focus/blur/change 原生事件契约，Adapter 不能默默伪造事件。
3. `ScTextarea` 和 `ScTable` 当前主要走 TDesign Bridge，Port 的 Native 回退能力不能仅靠文档假定。
4. `SceneButton` 同时存在 `activate` 事件和 `$attrs` 透传 `click` 的消费方式，迁移必须先收敛激活语义。
5. `@sc/ui` 的 49 个图标和 61 个厂商导出与 Scene 组合共处一包，依赖移除必须分阶段，避免一次性破坏构建。
6. 现有守卫和主题文档锁定了旧架构事实，必须在对应迁移阶段同步更新。
7. 本轮是静态只读审计，不证明浏览器交互、视觉、键盘或屏幕阅读器行为已经等价；这些必须在 02C-02B/02C-02C 实测。

## 12. 结论与下一步

本次架构优化的核心不是增加一个名为 `PrimitiveAdapter` 的抽象，而是同时消除：

- 基础组件的双重权威。
- Sc 对 `@sc/ui` 的反向依赖。
- Scene 内部的厂商驱动和运行时 Kit 选择。
- Scene 自行决定业务表达和设计 Token 的事实。

最终架构保持“Sc 基础组件权威 + `@sc/ui` Scene 组合 + Primitive Port 依赖倒置 + Web Sc Adapter + TDesign/Native 作为 Sc 内部实现”的有限减负方案。

下一步是在独立评审通过后启动 `FE-RENDERER-02C-02B`，先定义并验证 Primitive Port v1 和 Sc Adapter；未通过本 ADR 评审前，不迁移产品组件。
