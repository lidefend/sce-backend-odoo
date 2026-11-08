# FE-RENDERER-02C-02B-02 Phase 1 Parallel Audit

- 状态：第一阶段只读审计完成；总控已冻结推进顺序，Provider 与 Button 独立切片已通过定向验证
- 基线：`f1ba79c173c4701c642b3e505daf33c7aaaedfb9`
- 分支：`fix/fe-renderer-02c-02b-02-sc-adapter-phase1-20261108`
- Formal Product Layer：P0 platform kernel product
- Layer Target：Scene Primitive Port injection and Web Sc Adapter binding
- Module：Sc Design System、`@sc/ui/primitive-port`、Scene Provider 和前端验证
- Standard vs User-Specific：platform engineering standard

## 1. 阶段结论

第一阶段不得直接进入产品接线。真实源码证明：

1. Sc 是唯一基础组件权威的方向不变。
2. `@sc/ui/primitive-port` 的 Props/Emits/Slots 与 runtime 语义保持冻结；第 8 节仅放宽
   真实 SFC 所需的实例 bindings 类型兼容。
3. `SceneUiProvider`、`SceneButton`、`SceneFieldControl`、`SceneRelationTable` 和
   `FormSection` 保持不动。
4. Button 适合作为第一个真实行为样板，但当前不能直接作为完整
   `ScenePrimitiveAdapter` 注入现有运行时校验。

原因是冻结的运行时校验要求七个 Primitive 全部存在且每个 required capability
齐全，而七个 Sc 组件并非同时 Conformant。将未验证的 capability 写成已支持，
或为了先接 Button 而放宽七项闭包，都会违背 Port v1。

## 2. 并行执行边界

仓库当前已有超过两个活动 worktree，硬锁要求不得继续创建四个执行 worktree。
因此本阶段采用同一 clean 基线上的四条只读工作线，不产生并行写入：

| 工作线 | 第一阶段交付 | 本阶段写入 |
| --- | --- | --- |
| A Sc API | 七个 Sc Primitive 的真实 Prop/Event/Slot/Expose 与缺口 | 无 |
| B Provider | Provider context、生命周期、共存和失败策略候选 | 无 |
| C Conformance | 编译期、运行期和真实组件行为矩阵 | 无 |
| D Guard | 依赖方向、bundle、导入边界和增量路由设计 | 无 |

执行器 A、B 已产出源码审计，并由总控复核。C 的三次委派会话均未交付审计结果，
因此 C 的内容由总控在同一基线上直接完成；该事实保留为“总控补审”，不记为
独立执行器 PASS，也不伪造并行执行证据。

## 3. 执行器 A：Sc Primitive 事实

| Primitive | 已有能力 | 与冻结 Port 的主要差距 |
| --- | --- | --- |
| Button | `variant/size/status/disabled/loading/loadingLabel`、default slot、`focus()`、loading/disabled ARIA | 无 `defineEmits`；click/focus/blur 仅经 `$attrs`；无 `activate`、`accessibleLabel` 或事件来源封装 |
| Input | 受控值、状态、描述、焦点、键盘、IME、`focus()` | 事件仍是原始 Event；TDesign 路径在缺事件时构造新 Event/FocusEvent/KeyboardEvent；缺 `inputMode`/`name`；Port 要求 string，而 Sc 允许 number |
| Select | 受控值、选项、搜索、弹层、只读和 `focus()` | change/search/popup 丢事件；无 focus/blur/keydown/keyup；loading 未进入值变更防线；选项值允许 number |
| DateField | 日期值、只读、禁用、错误和原生 ARIA 投影 | 只有 `update:modelValue`；无 change/focus/blur/keyboard/expose；Port 使用 CanonicalDateValue |
| Textarea | 受控值、autosize、状态、焦点、`focus()` | 缺键盘/IME emits；缺事件时伪造 Event/FocusEvent；rows 只映射 minRows |
| Table | 基础表格、横向滚动、loading、row click/dblclick | 无 `rowActivate`、行键盘 Enter、行 focus 或 `focus()`；Prop 名与 Port 不同；可暴露 Port 外选择能力 |
| Icon | 五个语义名的基础映射和 size | 固定 `aria-hidden=true`；无 label/decorative；仍通过 `@sc/ui/icons` 获取 TDesign 图标 |

关键源码：

- Button：`frontend/apps/web/src/components/design-system/ScButton.vue:19,43,59-92`
- Input：`frontend/apps/web/src/components/design-system/ScInput.vue:139-149,196-223,246-251`
- Select：`frontend/apps/web/src/components/design-system/ScSelect.vue:84-133`
- DateField：`frontend/apps/web/src/components/design-system/ScDateField.vue:16,24-48`
- Textarea：`frontend/apps/web/src/components/design-system/ScTextarea.vue:64-105`
- Table：`frontend/apps/web/src/components/design-system/ScTable.vue:97-165`
- Icon：`frontend/apps/web/src/components/design-system/ScIcon.vue:1-22`
- Icon vendor edge：`frontend/apps/web/src/components/design-system/scIcon.ts:1-17`

结论：Button 需要薄 wrapper；其余六个组件在真实迁移前也必须先修复 Sc 自身的事件、
焦点、键盘、可访问性或值类型契约，不能由 Adapter 伪造或掩盖。

## 4. 执行器 B：Provider 候选设计

现有 `SceneUiProvider` 是异步 Kit Runtime：

- 必需 `kit`，默认 `fallbackKit='sc-native'`。
- 动态加载 Driver，失败后加载 fallback。
- 本地 Token fallback、硬编码 `36px/44px` density 和全局焦点样式。
- `sceneUiKitKey` 的 context 包含 kit/requestedKit/density/runtime/ready。

证据：

- `frontend/packages/ui/src/components/SceneUiProvider.vue:8-74`
- `frontend/packages/ui/src/kits/context.ts:5-24`

第一阶段建议新增独立 `ScenePrimitiveProvider`，不改变旧 Provider：

```ts
interface ScenePrimitiveProviderProps {
  primitives: ScenePrimitiveAdapter;
  density?: SceneDensity;
}
```

上下文应直接实现冻结的 `SceneCompositionContext`。Adapter 或 density 被父组件替换时，
通过 getter 保留 Vue props 的响应式读取；不另造一套与冻结类型冲突的 Ref 形状：

```ts
interface ScenePrimitiveContext {
  readonly primitives: ScenePrimitiveAdapter;
  readonly density: SceneDensity;
}

const context: SceneCompositionContext = {
  get primitives() {
    return props.primitives;
  },
  get density() {
    return props.density ?? 'compact';
  },
};
```

生命周期规则：

1. Provider 同步校验，不加载 Driver，不维护 load/ready 状态。
2. Adapter 缺失、组件形状错误、identity 错误或 capability 不闭合时 fail-closed。
3. 校验失败时隐藏 slot，渲染带 `role="alert"` 的 Contract Error；不得回退到 Native、
   Scene 自带控件或另一套基础组件。
4. `useScenePrimitiveContext()` 在 Provider 外调用必须立即失败；该错误应使用明确的
   provider misuse 错误，不能伪造某个 Primitive 的 capability 错误。
5. Provider 用独立 InjectionKey，与旧 `sceneUiKitKey` 共存；02B-02 不把新 Provider
   接入任何现存页面。
6. Adapter 变化时重新校验；不缓存跨实例业务状态，不使用模块级 runtime singleton。
7. SSR/hot reload 由 Vue 实例生命周期自然恢复，不引入异步加载或全局清理逻辑。

待冻结问题：是否允许 Provider 在生命周期内替换 Adapter。若允许，slot 必须依据新的
runtime validation 结果重新挂载；若不允许，应以 `:key` 重建 Provider。无论选择哪种，
都不能缓存失效 Adapter，也不能在验证失败后继续渲染消费方。

## 5. 执行器 C：Conformance 候选设计

现有 Port 测试证明协议类型和 runtime shape，但没有证明真实 Sc 行为：

- 类型测试使用声明组件，而非实际 SFC：
  `frontend/apps/web/scripts/primitive_port_type_test.ts:35-98`
- 运行期测试使用手动 fixture：
  `frontend/apps/web/scripts/primitive_port_runtime_test.ts:17-181`
- 当前 target 只编译 Port 测试和 Port 源：
  `frontend/apps/web/tsconfig.primitive-port.json:8-12`
- Make 入口：
  `make/frontend.mk:104-112`

第一阶段建议建立四层证明：

| 层 | 证明 |
| --- | --- |
| 类型 | 实际 Button wrapper 以 `satisfies PrimitiveBinding<...>` 或更严格 witness 对齐；错误 Props/Emits/Slots 使用 `@ts-expect-error` 编译失败；禁止 `as` |
| Runtime | 七个 fixture 的缺失/identity/capability/形状错误仍 fail-closed；Provider 缺失/错误 Adapter 不渲染 slot |
| Bundle | adapter 入口 metafile 不加载 Scene 页面、`@sc/ui` 组合入口或业务页面；vendor 只经 Sc 内部桥接 |
| Browser contract | 真实 Sc wrapper 的 pointer、Enter、Space、programmatic、focus/blur、loading、disabled、ARIA 仅产生一次 `activate`，保留真实事件来源与事件对象 |

真实浏览器契约不新增 `@vue/test-utils` 或 jsdom。仓库已有可复用模式：

- `frontend/apps/web/scripts/professional_collaboration_message_component_test.mjs:36-63`
  先用 esbuild 编译实际 SFC，再由 `page.setContent()` + `addScriptTag()` 挂载；
- `scripts/verify/playwright_runtime.mjs` 负责受管 Chromium 解析与启动。

Button Conformance 应沿用这一模式，以无后端页面验证真实 DOM 键盘、焦点和 ARIA 行为。

Button 真实浏览器样板至少验证：

- pointer click -> `activate(source='pointer')` 一次。
- Enter 和 Space -> 各一次 `activate(source='keyboard')`，不得因 keydown + click 双重触发。
- 程序化 `element.click()` -> `activate(source='programmatic')`，nativeEvent 可保留为
  非 trusted MouseEvent，不得伪造其他事件。
- disabled/loading -> 零 `activate`；loading 同时有 `aria-busy` 和加载文案。
- `accessibleLabel` -> `aria-label`；`focus()`、focus、blur、Tab 顺序真实。

七 Primitive 全量行为测试留到各自 Conformance 修复完成；不能以声明 capability
代替真实行为。

## 6. 执行器 D：Guard 与增量路由候选

现有守卫事实：

- `frontend_primitive_port_guard.py` 已约束 Port 源码、public export 和 bundle，
  不允许 apps/web、Scene 或 vendor 进入 Port bundle。
- `frontend_primitive_adapter_guard.py` 当前只允许
  `@sc/ui/src/primitives.ts` 和旧 TDesign Kit 直接导入 vendor，并扫描 Web 业务面。
- `frontend_scene_component_bridge_guard.py` 当前仍硬性要求旧
  `SceneUiProvider`、Kit 选择和 native fallback，迁移期不能提前翻转。
- `frontend_dev_incremental.py` 已把 `primitive-port` 路由到
  `verify.frontend.primitive_port.unit`，但 `scene-adapter` 和新的 conformance
  目录尚无专用路由。

建议新增守卫采用“零新增债务”而非一次性全仓清零：

1. `scene_vendor_dependency_guard`
   - `@sc/ui` 新代码不得新增直接 TDesign 导入。
   - 当前旧 `primitives.ts`、`icons.ts`、TDesign Kit 和 Scene vendor-icon 消费使用
     精确 legacy allowlist；新增路径或新增 specifier 立即失败。
2. `scene_primitive_authority_guard`
   - 新 `scene-adapter/` 只能导入 Sc Design System 组件和
     `@sc/ui/primitive-port` 的 type/contract。
   - 禁止导入 TDesign、`@sc/ui/primitives`、`@sc/ui/icons`、Scene 页面组合或
     `apps/web` 业务实现。
   - 禁止用 `as PrimitiveComponent/PrimitiveBinding` 冒充兼容性。
3. `scene_adapter_contract_guard`
   - 检查导出键、primitive identity、portVersion 和 capability metadata。
   - 行为正确性仍由类型测试与浏览器契约测试证明，不由静态字符串扫描冒充。
4. `scene_application_import_guard`
   - 业务页面不得导入内部 `scene-adapter/`；只有 Web composition root 可以装配。
   - 现有 `@sc/ui/form` 消费者作为精确迁移清单保留，防止新增旁路。
5. Bundle metafile
   - adapter bundle 必须包含对应 Sc primitive。
   - 不得包含 Scene 页面组合、apps/web 页面或业务模块。
   - vendor 只允许通过 Sc Design System 内部桥接出现；直接 vendor import
     由源码守卫拒绝。

增量路由建议：

| 变更路径 | 最低 target |
| --- | --- |
| `frontend/packages/ui/src/primitive-port/provider/` | `verify.frontend.primitive_port.unit` + Provider runtime |
| `frontend/apps/web/src/components/design-system/scene-adapter/` | `verify.frontend.scene_primitive_adapter.unit` + lint/typecheck |
| `frontend/apps/web/scripts/primitive-port-conformance/` | `verify.frontend.scene_primitive_adapter.unit` |
| `scripts/verify/frontend_scene_*guard.py` 及测试 | 对应 guard unit |
| `make/frontend.mk` / planner | `verify.frontend.dev.incremental.unit` + planner test |

建议新增两个非候选专用入口，名称避开增量规划器禁止的 `browser/build/release/quick`
片段：

| 目标 | 职责 |
| --- | --- |
| `verify.frontend.scene_primitive_adapter.unit` | static guard、实际 wrapper `vue-tsc` 正反向证明、adapter bundle metafile |
| `verify.frontend.scene_primitive_contract.behavior` | 单个 Button 的 esbuild + Playwright 真实 DOM 契约 |

`verify.frontend.scene_primitive_adapter.unit` 必须作为本地迭代可执行目标；真实浏览器
`behavior` 目标只在声明受影响的 Button 契约或进入批次集成复核时执行，不扩展为全页面矩阵。

当前 `frontend_primitive_adapter_guard.py` 的 vendor authority 和
`frontend_scene_component_bridge_guard.py` 的旧 Runtime 断言只能在 02D 迁移时同步
切换；02B 使用新守卫锁定新增边界，不能为了让新代码过门而删除旧断言。

## 7. 必须由总控冻结的接口问题

1. **七 Primitive 与 Button-first 的顺序**
   - 冻结规则要求 `ScenePrimitiveAdapter` 七项齐全。
   - 推荐保持七项 Provider 契约不变：Provider 先用完整七项 fixture 做运行期测试；
     真实 Button wrapper 先独立做类型和浏览器 Conformance；在所有七项真实 binding
     Conformant 前，不把 Provider 接入产品页面。
   - 若要求 Button 样板必须经过 Provider，则必须显式重切批次，先补齐其余六项 Sc
     event/focus/keyboard/accessibility 契约；不得降低 runtime validator。
2. **Provider 命名与公开出口**
   - 推荐 `ScenePrimitiveProvider` 独立于旧 `SceneUiProvider`。
   - 02B-02 仅建立内部实现与测试，不改变旧 `@sc/ui/form` / `@sc/ui/collection`
     消费者。
3. **缺失 Provider 的错误类型**
   - 推荐使用明确的 provider misuse 错误；Adapter 校验错误继续使用
     `ScenePrimitiveContractError`。
4. **Button 事件来源**
   - 由 wrapper 记录实际 keydown/click 链，`source` 不由 nativeEvent class 推断；
     programmatic 依据非 trusted click 或缺失 native event，不得构造 `new Event()`。
5. **文件所有权**
   - A：`frontend/apps/web/src/components/design-system/scene-adapter/`
   - B：`frontend/packages/ui/src/primitive-port/provider/`
   - C：`frontend/apps/web/scripts/primitive-port-conformance/` 与专用 tsconfig
   - D：`scripts/verify/`、`make/frontend.mk`、`frontend_dev_incremental.py`
   - 总控：公共出口、跨线接线、Agent 记录和最终集成

   “一个执行器一个分支”在本仓库当前状态下不能机械执行：已有活动 worktree 超过
   两个的硬上限。第一阶段因此使用同一基线只读审计；进入写入阶段时，同一候选 worktree
   仍只允许一个写入者，其他执行器只能提交补丁建议或只读复核。

## 8. 总控冻结结论

总控采用推荐方案，不作 Button-first 降级：

1. `ScenePrimitiveAdapter` 保持七项必需闭包，`validatePrimitiveAdapterRuntimeShape()` 的
   identity、capability、portVersion 和组件运行时形状检查不降低。
2. Provider 先以完整七项 fixture 证明注入、上下文、响应式替换和 fail-closed 行为；
   不以 fixture 冒充真实组件 Conformant。
3. Button 以真实 `ScSceneButton → ScButton` 薄包装独立推进类型、运行期、bundle 和浏览器
   Conformance。其余六项未补齐前，不创建可接入产品的“全量真实 Adapter”。
4. Provider 使用 `@sc/ui/primitive-port/provider` 独立出口；Port 根出口继续只包含无 `.vue`
   依赖的协议与校验，避免无 DOM 测试被迫加载组件层。
5. 缺失 Provider 使用 `ScenePrimitiveProviderError`；Adapter 形状错误继续使用
   `ScenePrimitiveContractError`，两类错误不混用。
6. Button `source` 由实际事件链决定：pointer click、Enter/Space 原生 click、非 trusted
   programmatic click 分开记录；不根据事件类名推断，不构造假的 `Event`。

真实 SFC 编译还暴露出 Port 类型基础设施的一个过度约束：原 `PrimitiveComponent` 假定组件
没有实例 bindings，与 Port 要求的 `focus()` expose 冲突。本次仅把该类型放宽为允许额外实例
bindings，Props、Emits 和 Slots 的精确兼容检查保持不变；Port 的运行时语义没有改变。

## 9. 已实现的 Button-first 切片

| 层 | 实现 | 证据 |
| --- | --- | --- |
| Provider | `ScenePrimitiveProvider` 同步校验七项 Adapter，通过 reactive getter 注入 context；失败时隐藏 slot 并显示 `role="alert"` | SSR valid/invalid/outside-provider 三例 |
| Context | `useScenePrimitiveContext()` 在 Provider 外抛 `ScenePrimitiveProviderError` | SSR 明确错误态 |
| Button | 真实 `ScSceneButton` 包装 `ScButton`，统一 `activate/focus/blur`，保留 `nativeEvent` | strict SFC type witness + Chromium |
| Type | 实际 SFC 赋给 `PrimitiveBinding<ButtonPortProps, ButtonPortEmits, ButtonPortSlots, 'Button'>`；错误 identity 反例编译失败 | `vue-tsc` |
| Guard | 只允许 ScButton、Vue、Port 依赖；禁用 vendor 旁路和 `as PrimitiveComponent/Binding` | 5 项 guard 单测 |
| Bundle | 实际 adapter 入口包含 ScSceneButton/ScButton，不含 UI Scene 组件或产品页面 | esbuild metafile |
| Routing | `primitive-port` 与 `scene-adapter` 输入路由到非零定向目标 | 83 项 planner 测试 |

Button 浏览器契约在 managed Chromium `147.0.7727.15` 上执行 20 项断言，0 console error、
0 网络请求：pointer/Enter/Space 各只产生一次 `activate`；programmatic click 单独归类；
disabled/loading 为零激活；loading 暴露 `aria-busy` 与可读文案；accessible label、focus/blur
以及 `focus({preventScroll})` 到原生 focus 目标均来自真实 DOM。Provider 活体替换为非法
Adapter 后，slot 立即移除并显示 `Input:ime` 缺口。

最终 `make ci.local.iteration` 真实执行 13 个受影响目标并退出 0，覆盖 acceptance binding、
Agent ledger/resume、基线策略、CI workflow contract、增量规划、lint、页面模式 parity、旧
Primitive Adapter、Primitive Port、Scene Adapter unit、Button behavior 和严格类型。
`make verify.frontend.build`
转换 5373 个模块并成功构建，仅有既有的大 chunk 警告。

首轮迭代还暴露并分类收口了三项验证工具问题，均不是产品行为失败：

1. 新增 behavior target 未纳入 verification lane；已把 Scene Adapter unit 接入已有 quick /
   architecture lane，把真实 Button behavior 接入 release aggregate，不把浏览器样例塞入
   inner-loop unit。
2. `frontend/**` 的保守规则把内部、零消费者 Adapter/Provider 误判为 list-surface 运行时证据
   失效；新增更具体的 Scene Primitive 内部规则，并把 `@sc/ui/package.json` 仅接受“只新增
   export、不改依赖和既有 export”的 narrow condition。依赖或既有出口变化仍回落到保守规则。
3. 新输入未映射到 acceptance binding / planner；已补非零定向路由和反例测试，最终 85 项
   planner 测试与 69 项 acceptance binding 测试通过。

独立 Diff 复核进一步发现：共享浏览器测试曾只路由到 SSR unit、run 台账曾重复声明
`product_l2_l4`、`focus(options)` 缺少组件 ref 行为证明、断言数曾硬编码为 18，以及
“零产品消费者”豁免缺少自动失效机制。对应修复为：

- 浏览器测试输入同时选择 unit 与 behavior，并补 planner 反例测试；
- run 台账合并为唯一结果键；
- 通过 `ScSceneButton` 组件 ref 验证 `focus({preventScroll:true})` 到达原生 focus；
- 浏览器计数改为动态计算，当前 20 项；
- 产品源码一旦导入 `scene-adapter` 或 `@sc/ui/primitive-port/provider`，fixture-only
  豁免 guard 立即失败并要求重新分类 list-surface 证据。

## 10. 未覆盖与下一步

- Input、Select、DateField、Textarea、Table、Icon 的真实事件、焦点、键盘、可访问性和值类型
  缺口仍未修复，不能声明七项真实 Adapter Conformant。
- 本切片没有产品页面导入 `scene-adapter` 或新 Provider；旧 `SceneUiProvider`、Kit、
  `SceneFieldControl`、关系表、Contract V2、后端和数据库均未改变。
- 产品 L2-L4、交付冻结、远端门禁、发布、合并和用户验收均未执行。

下一精确动作：完成本 Button-first 切片的独立 Diff 复核后提交并建立持续集成 PR，将它作为
并行集成基线；随后由 A 处理 Input/Textarea、B 处理 Select/DateField、C 处理 Table/Icon，
D 建设统一 Conformance/Guard/增量矩阵，总控保留 Port、Provider、Registry 与最终集成权。
