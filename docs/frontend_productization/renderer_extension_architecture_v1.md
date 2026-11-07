# Renderer Extension Registry 架构 v1（EXP-03B-04A）

状态：只读设计。目标：解除平台 `FormSection` 与 `semantic_registry.generated.ts` 对行业 Renderer 的直接依赖，让行业模块通过正式扩展机制注册专业表达，而不污染平台组件词汇表。

## 一、现状依赖链（根因）

```
contracts/registry/semantic.yaml (含 category: industry 行)
contracts/registry/component.yaml (含 sc.payment.settlement_detail_collection)
        │
        ▼
scripts/contract/generate_semantic_registry.py
        │  当前：把 semantic + component 两类行合并投影到同一 carrier
        ▼
semantic_registry.generated.ts / semantic_registry_generated.py（平台唯一词汇表，混入行业 key）
        ▼
professionalComponentRegistry.ts（PROFESSIONAL_COMPONENT_RENDERERS 硬编码 PaymentSettlementDetailCollectionControl）
        ▼
FormSection.vue（直接 import 行业组件并硬编码 v-else-if 分支）
```

关键事实：`semantic.yaml:117` 已把该行标为 `category: industry`，但生成器未按 category 拆分，运行时注册表也未区分。所以修复方向是**利用已存在的 category 声明做拆分**，而不是新增一套旁路清单。

## 二、目标架构

```
contracts/registry/{semantic,component}.yaml
        │  category: platform | industry
        ▼
generate_semantic_registry.py
        │  拆分输出：
        │    - 平台 carrier：semantic_registry.generated.ts/.py（仅 platform 行）
        │    - 行业 manifest：industry_renderer_manifest.json（industry 行）
        ▼
FormSection.vue ──> Renderer Extension Registry ──> 平台 renderer（Sc / Professional*，内置）
                          ▲                          └─> 行业 renderer（行业模块 bootstrap 注入）
                          │
              行业前端模块启动时按 manifest 注册
```

职责：

| 层 | 职责 |
| --- | --- |
| 平台语义注册表 | 只保留 platform 通用 componentKey |
| 行业扩展注册表 | 行业专属 componentKey + renderer，由行业模块启动时注入 |
| FormSection | 唯一调度器，只按注册结果解析，不 import 行业实现 |
| 行业模块 | 提供专业组件、语义与 manifest |
| Contract V2 | 提供 componentKey 身份与版本参数 |

## 三、扩展注册协议（最小设计）

### 注册表运行时结构

- 单一 `rendererExtensionRegistry: Map<componentKey, Registration>`。
- `Registration = { componentKey, semanticType, supportedFieldTypes, renderer: string, rendererVersion, capabilities, readiness, component: AsyncComponent }`。
- 平台 renderer 在 `FormSection` 模块加载时内置注册；行业 renderer 由行业前端模块在 app bootstrap 阶段注册。

### 注册时机与顺序

1. 平台模块加载：内置注册 Sc / Professional* renderer。
2. app bootstrap：行业模块读取其 manifest，逐条 `registerRenderer`。
3. 首次渲染前完成；晚于首次渲染的注册必须触发显式错误（不允许半注册渲染）。

### fail-closed 规则

- 未知 componentKey → `PROFESSIONAL_COMPONENT_UNREGISTERED`（不静默降级）。
- 未知 renderer → `SEMANTIC_REGISTRY_UNKNOWN_RENDERER`。
- componentKey 或 semanticType 重复注册 → bootstrap 拒绝启动。
- renderer 版本与契约 `contractRegistryEntry.version` 不匹配 → 拒绝渲染。
- 能力（capabilities）不满足 → 拒绝渲染。

### 契约身份绑定

沿用现有 `resolveContractProfessionalComponent` 的 `contractRegistryEntry.version` 校验；行业 manifest 必须携带与契约一致的 `rendererVersion`，缺失即 fail-closed。

## 四、FormSection 改造（仅设计）

- 删除 `import PaymentSettlementDetailCollectionControl` 与对应硬编码 `v-else-if` 分支。
- 字段渲染改为：`resolveRendererComponent(field.componentRenderer)` 得到组件，再用 `<component :is>` 渲染。
- 平台 renderer 继续由 FormSection 内置解析；行业 renderer 从注册表取，FormSection 不感知其实现。

## 五、迁移影响清单

1. `contracts/registry/component.yaml` / `semantic.yaml`：`category: industry` 行拆分输出（声明本身不变）。
2. `scripts/contract/generate_semantic_registry.py`：增加 category 拆分，产出行业 manifest。
3. `semantic_registry.generated.ts/.py`：仅保留 platform 行。
4. `professionalComponentRegistry.ts`：去掉硬编码行业 renderer，改为扩展注册表合并。
5. `FormSection.vue`：去行业 import + 硬编码分支，改动态解析。
6. 行业模块（建筑）：新增 manifest + 注册入口（bootstrap）。
7. 仅迁移 `sc.payment.settlement_detail_collection`；BOQ 等暂不动。

## 六、回归与守卫设计

- 平台 carrier 不得含行业 componentKey（生成时校验 `category != industry`）。
- FormSection / 平台模块不得 import 行业组件（静态守卫）。
- 行业 renderer 只能经 `registerRenderer` 注入（守卫：禁止直接 import 进平台层）。
- 缺扩展/版本冲突/重复注册 → fail-closed，均有负例测试。
- 付款申请页面表现逐项与现状一致（列表/详情/表单/结算弹窗并排验收）。

## 七、本轮边界

只读设计，未改任何代码。实施从 EXP-03B-04B 开始，且只迁移付款结算明细这一个行业 key。
