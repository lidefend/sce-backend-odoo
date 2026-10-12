# FE-CONTRACT-RUNTIME-01 语义注册表收敛 — 批次记录

- 分支：`feature/fe-contract-runtime-01-semantic-registry`
- 基线：`991a9d9b57525850f99a8643ce3f4f0d322d00dd`
  （= `origin/main` `5dd4a846` + FE-CONTRACT-RUNTIME-00 产物）
- run：`.agent/runs/FE-CONTRACT-RUNTIME-01/run.json`
- goal：`.agent/goals/FE-CONTRACT-RUNTIME-01.yaml`

## 缺陷来源

00 清单 `G1`：渲染型组件词表被劈成两半——后端
`addons/smart_core/core/unified_page_contract_v2_assembler.py::_component_key()`
持一份私有映射，前端
`frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts`
持另一份 `registration(...)` 表。契约层既不枚举也不校验，后端可以产出前端未
登记的键，未识别 widget 静默回落。前端注册表里的 `semanticType` 字段没有消费
方，属于第二本死词典。

注意与"信息型语义"区分：运行时契约里的 `runtimeContract.fieldSemantics`
（生产端 `unified_page_contract_v2_assembler.py:1445` / `handlers/ui_contract_v2.py:4227`，
消费端 `frontend/apps/web/src/pages/contractForm/nativeLayoutUtils.ts`）描述的是
`semantic_type`（technical/relation/computed/system/business）+ `surface_role`，
回答"这个字段在治理上是什么"，不是"用哪个组件渲染"。两套概念不合并。

## 01-A 交付（本批次）

| 文件 | 作用 |
| --- | --- |
| `contracts/registry/semantic.yaml` | 唯一的"字段意味着什么"声明权威。27 条语义 + 23 条有序推导规则 + `readable_value` 兜底。 |
| `contracts/registry/component.yaml` | 唯一的"由哪个组件渲染"声明权威。26 条组件键、6 个渲染器、类型导向哨兵 `FormSectionField`。 |
| `contracts/registry/registry.schema.json` | 机器可读形状约束（draft 2020-12），`oneOf` 判别 semantic/component。 |
| `contracts/registry.yaml` | 两条 `kind: schema` 登记（registry 用 schema 语义：纯映射，版本只在 registry）。 |
| `contracts/README.md` | R6 之后追加第 5 条：`registry/` 是平台词表映射、唯一声明权威。 |
| `scripts/verify/semantic_registry_lint.py` | 7 项静态检查（见下）。 |
| `scripts/verify/test_semantic_registry_lint.py` | 聚焦单测：1 正例 + 9 负例 + 1 合法引用例。 |
| `make/contract.mk` | 新增 `verify.semantic.registry.lint`。 |

### 推导链

```
semantic.yaml --derivation--> semantic --component--> componentKey
```

`derivation` 是**数据而不是代码**：Odoo 字段事实（`field_types` / `widgets` /
`widget_suffix` / `widgets_exclude`）命中即得 semantic，再经 `component.yaml`
得到组件键。新增业务字段时，命中已有规则、或由上层契约直接声明 `semantic`，
就不需要新增任何前后端映射代码——这正是本目标的验收标准。

第一批 27 条语义中，21 条可由推导规则命中；6 条
（`credential_entry` / `secret_confirmation` / `challenge_status` /
`one_time_secret` / `support_action` / `payment_settlement_detail_collection`）
属于"必须由生产方显式声明"的类型，没有字段事实可推导，lint 会把这份名单打印
出来，避免它们静默漂移。

### 检查项

1. 两份文档匹配 `registry.schema.json`；
2. 无重复 YAML 键（YAML 静默保留最后一个，重复键即不可见覆盖）；
3. semantic ↔ component 双向引用成立；
4. 每个 `renderer` 已登记，且类型导向哨兵在其中；
5. 每条推导规则与 `derivation.default` 指向已声明语义；
6. `contracts/**/*.yaml` 中的 `semantic:` 引用合法；
7. **前端 `professionalComponentRegistry.ts` 的 `registration('key'` 集合与
   `component.yaml` 逐项双向相等** —— 这一条使第二本私有词典不可能存在。

## 01-B 交付（本批次）

### 关键约束与决策

运行容器只挂载 `./addons`（`docker-compose.yml` 的
`./addons:/mnt/source-addons`），**运行时读不到 `contracts/`**。因此采用
「声明在 `contracts/` + 生成运行时可消费载体」的模式，与既有
`contracts/generated/contract-registry.json` 同构：声明只有一处，载体由生成器投影，
lint 逐字节查漂移。

### 文件

| 文件 | 作用 |
| --- | --- |
| `scripts/contract/generate_semantic_registry.py` | 声明 -> Python 载体投影器；`--check` 检测漂移；`root` 参数化以便单测。 |
| `addons/smart_core/core/contract_runtime/semantic_registry_generated.py` | 生成物：`DERIVATION_RULES` / `SEMANTIC_COMPONENTS` / `DERIVATION_DEFAULT`。 |
| `addons/smart_core/core/contract_runtime/semantic_resolver.py` | 运行时解析：`resolve()` 返回 `{semantic, componentKey, semanticSource}`；`declared` 优先于 `derived`。 |
| `addons/smart_core/tests/test_contract_runtime_semantic_resolver.py` | 行为基线矩阵（逐条复现被删除私有映射的决策）+ 来源语义 + 弃用信号。 |
| `addons/smart_core/core/unified_page_contract_v2_assembler.py` | 删除 47 行私有 `_component_key` 映射；调用点改用 `_resolve_component_key`；4 处硬编码组件键字面量改为注册表查询；汇编器现零组件键字面量。 |
| `scripts/verify/semantic_registry_lint.py` | 新增第 8 项：载体与声明逐字节同步。 |
| `make/contract.mk` | `verify.semantic.registry.lint` 扩为 py_compile + lint + 单测 + `generate --check` 全链；新增人工目标 `contract.semantic.registry.generate`。 |

### 行为与兼容

- 组件键的唯一权威从"汇编器私有函数"变为"注册表声明 + 解析器"。
- 旧入口 `_component_key()` 降级为一次性弃用 shim，触发
  `DEPRECATION_EVENT = deprecated_component_key_usage`（每进程一次），供未迁移调用方
  平滑过渡；**旧 `componentKey` 字段保留在投影里**，前端消费面不变。
- 字段显式声明 `semantic` 优先；未命中的声明语义会记 error 并回落推导结果，而不是
  产出一个前端未登记的组件键。
- 未识别的 widget 拼写仍落到 `derivation.default`（`readable_value`）；本批次不改变
  该回落，但把它从"私有映射的最后一行"变成"注册表里一条可被 lint 与普查审计的规则"
  （覆盖率普查与 domain 类型接线列入 01-D）。

### 渲染不变证据

| 层 | 命令 | 结果 |
| --- | --- | --- |
| L2 | `make verify.semantic.registry.lint` | PASS（34 用例：lint 13 + 解析器 11 + 汇编器边界 10） |
| L2 | `make verify.business_config.formal_list.unit` | PASS（201 用例） |
| L2 | `make verify.frontend.professional_business_value.unit` | PASS（19 用例） |
| L2 | `make verify.frontend.professional_component_registry.unit` | PASS（149 用例） |
| L2 | `make verify.frontend.professional_detail_collection.unit` | PASS（57 用例） |
| L2 | `make verify.contract.schema.declaration.sync` | PASS（9 用例） |

行为基线单测逐条钉住原私有映射的决策（reference 类型优先于 widget、`monetary`、
`statusbar/badge`、`many2one`、`many2many` 排除 `tags`、`one2many` 等），因此"删除第二
本词典"被证明为**不改变前端被告知渲染什么**。

### 范围边界

本批次仍**不改运行时渲染行为**，因此不是产品交付证据；容器内 `payment.request`
渲染复验（L3/L4）留在 01-D 的浏览器验收一并做。


## 01-C 交付（前端接管同一份声明）

目标：前端不再维护第二份词表。前端注册模块从生成表构建注册项，语义解析入口由同
一份声明驱动。

### 投影与消费

| 文件 | 作用 |
| --- | --- |
| `scripts/contract/generate_semantic_registry.py` | 投影器扩展为**两个载体**：加 `render_frontend_registry()` / `render_frontend_repository()`，`main()` 同时写 addon 载体与前端载体（TS 头含 `{}`，用 `__SOURCES__`/`__VERSION__` 占位替换而非 `.format()`）。 |
| `frontend/apps/web/src/app/presentation/semantic_registry.generated.ts` | 新增前端载体（26 行）：`SEMANTIC_REGISTRY_ROWS`（componentKey / semanticType / supportedFieldTypes / readiness / renderer）+ `SEMANTIC_REGISTRY_VERSION`。**这是前端唯一的组件词表**。 |
| `frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts` | 26 条手写 `registration('sc.…')` 字面量全部删除，改为 `SEMANTIC_REGISTRY_ROWS.map(row => registration(...))`；新增 `RENDERER_NAMES` + `declaredRenderer()` 守卫（漂移的渲染器名在编译期就不可通过）；`ProfessionalComponentReadiness = SemanticRegistryReadiness`（单一来源）。 |
| 同上（新增导出） | `professionalSemanticIndex`（semantic → 注册项，重复语义直接抛错而非静默覆盖）+ `resolveSemanticRegistration()` + `componentKeyForSemantic()`；未声明语义返回 `null`（fail-closed，不静默回落），由调用方决定如何呈现。 |
| `make/frontend.mk` | 新增 `verify.semantic_runtime_resolution`。 |
| `frontend/apps/web/scripts/semantic_runtime_resolution_test.ts` | 覆盖命名语义解析、大小写/空白归一、未声明语义、以及"解析表 = 生成词表逐行一致"。 |

### 关于命名渲染器

owner 清单里写的 `money→CurrencyInput` / `date→DatePicker` / `relation→RelationPicker` /
`status→StatusTag` 是**示意名**，不是本仓库的渲染器名。按声明层的真实事实：

| semantic | componentKey | renderer |
| --- | --- | --- |
| `money` | `sc.value.money` | `ProfessionalBusinessValueControl` |
| `date` | `sc.input.date` | `FormSectionField`（类型导向） |
| `relation` | `sc.relation.many2one` | `ProfessionalRelationFieldControl` |
| `status` | `sc.display.status` | `ProfessionalBusinessValueControl` |

因此测试断言的是**契约声明里的 semantic → componentKey**，并且逐行断言"解析表等于生成
词表"，而不是硬编码一个并不存在的组件名。这样声明改动会改变测试权威，但不会需要新增前端代码。

### widget 覆盖率普查（lint 检查 9）

枚举域来自 `docs/architecture/unified_page_contract_v2/enum_registry.json` 的 `widgetType`
（17 个拼写）。普查命中 4 个此前**无语义声明**的拼写，已在 `semantic.yaml` 补 4 条带
`reason` 的推导规则：`upload→binary`、`radio→choice`、`relation→relation`、`gantt→detail_table`。
推导规则 23 → 27 条；语义 27 条、组件 26 条、前端键 26 条。未声明的 widget 拼写现在是
lint 失败，而不是运行时静默回落。

### 连带修正（01-C 暴露的既有耦合）

前端词表迁移让四个 guard 的"键权威"失效，逐个改为读生成载体：

| guard | 原权威 | 现权威 |
| --- | --- | --- |
| `frontend_professional_component_registry_guard.py` | 手写注册表 | 生成表；新增"不得有第二张表"（`registration('…')` 字面量）失败 |
| `frontend_professional_business_value_guard.py` | 手写注册表 | 生成表（`ProfessionalBusinessValueControl` 渲染器联合仍留在注册模块） |
| `frontend_professional_relation_field_guard.py` | 手写注册表 + 汇编器字面量 | 生成表 + 「汇编器经 `contract_runtime.semantic_resolver` 解析」 |
| `frontend_auth_surface_guard.py` | 5 条 `registration('sc.auth.…')` 字面量 | 生成表里的同名行（key + semantic + 字段类型 + readiness） |

另有一处**缓存指纹**耦合：汇编器现在经解析器选组件键，`semantic_resolver.py` 与
`semantic_registry_generated.py` 因此是装配的真实输入。
`verify.unified_page_contract.v2.assembler` 的 `ASSEMBLED_CACHE_INPUTS` 已把这两个文件
纳入，`ASSEMBLED_CONTRACT_CACHE_VERSION` 升级为
`ui-contract-v2-2026-10-12-semantic-registry-component-key`，`ASSEMBLED_CACHE_INPUTS_SHA256`
重钉；并做了反向验证（改动生成载体后门禁如期失败），确认 fail-closed 仍然成立。

发现过程记录：`verify.unified_page_contract.v2.assembler` 与
`verify.frontend.professional_relation_field.unit` 不在 01-B 的已记录检查集里，这两个
断裂直到 01-C 迁移前端词表才暴露；已在 01-C 一并修复并纳入 run 检查集。

### 验证（均为本批次实际执行）

| 检查 | 目标 | 用例 | 结果 |
| --- | --- | --- | --- |
| `semantic_registry_lint` | `verify.semantic.registry.lint` | 37 | PASS |
| `semantic_runtime_resolution` | `verify.semantic_runtime_resolution` | 123 | PASS |
| `assembler_cache_pin` | `verify.unified_page_contract.v2.assembler` | 1 | PASS |
| `assembler_contract_surface` | `verify.business_config.formal_list.unit` | 201 | PASS |
| `frontend_component_registry` | `verify.frontend.professional_component_registry.unit` | 284 | PASS |
| `frontend_business_value_alignment` | `verify.frontend.professional_business_value.unit` | 42 | PASS |
| `frontend_detail_collection_alignment` | `verify.frontend.professional_detail_collection.unit` | 127 | PASS |
| `frontend_relation_field_alignment` | `verify.frontend.professional_relation_field.unit` | 77 | PASS |
| `frontend_base_field_alignment` | `verify.frontend.professional_base_field.unit` | 70 | PASS |
| `frontend_auth_surface` | `verify.frontend.auth_surface.guard` | 1 | PASS |
| `frontend_typecheck` | `verify.frontend.typecheck.strict` | 1 | PASS |
| `frontend_lint_src` | `verify.frontend.lint.src` | 1（0 error / 64 既有 warning） | PASS |
| `schema_declaration_sync` | `verify.contract.schema.declaration.sync` | 8 | PASS |
| `agent_ledger` | `verify.agent.ledger.unit` | 15 | PASS |

### 范围边界

本批次同样**不改运行时渲染行为**：解析入口已就位，但前端渲染分发尚未改为"先看
`semantic`"；真实浏览器渲染复验（L3/L4）留在 01-D。

## 01-D 交付（字段语义不手写：输入收敛到模型 + 视图）

### 决策修正

01-D 原计划是在 `contracts/domain/payment-request.yaml` 逐字段手写
`semantic: money/relation/status`。实测证明这是**第二维护点**：字段的
ttype / widget / relation 已经由保真解析体系产出，语义可由同一套推导规则解出。
手工枚举一份可推导的数据就是分叉，因此改由解析产物生成。

### 输入与链路

```
模型元数据 + 视图 arch（contracts/generated/product_view_structure_contract.json，
  contracts/domain/*.yaml 按 source_of_truth.model 绑定管辖模型）
        │  assembler 的 widget 规范化（_canonical_widget_type）
        ▼
semantic_resolver.semantic_widget_type()  ← 唯一实现，页面与契约产物共用
        ▼
contracts/registry/semantic.yaml 推导规则（27 条）
        ▼
addons/smart_core/core/contract_runtime/domain_field_semantics_generated.py
        ▼  运行时 assembler 注解字段描述符 → resolve() → componentKey
```

`payment.request` 由解析事实单独解出的结果（无任何手写映射）：
`name→text`、`project_id/contract_id/settlement_id→relation`、`amount→money`、
`state→status`（来自表单视图的 `widget="statusbar"`）、`payment_basis_type→choice`。

### 关键实现点

- `semantic_widget_type()`：`statusbar/badge/monetary/percentage/percentpie/float_time`
  这些**本身就是语义信号**的原生控件名必须在规范化中存活；此前内联在汇编器里的
  这条判断被折叠成 `statusbar→display`，会让 `status` 规则永远不可达。
- `SOURCE_DOMAIN/ORIGIN_DOMAIN` 改名 `SOURCE_PROJECTED/ORIGIN_PROJECTED`：
  该语义来自解析事实的投影，而不是人工声明，命名必须如实。
- 汇编器缓存指纹新增 `domain_field_semantics_generated.py` 为输入，重钉
  `ASSEMBLED_CACHE_INPUTS_SHA256` 并把
  `ASSEMBLED_CONTRACT_CACHE_VERSION` 提升为
  `ui-contract-v2-2026-10-12-entity-semantics-from-parsed-facts`。

### 验证（均为本批次实际执行）

回执见 `.runtime/agent-runs/FE-CONTRACT-RUNTIME-01/<check>.json`（`make agent.run.resume`
显示 14 个 check 全部 `reusable`，无 `stale`）。

| 层 | 命令 | 用例 | 结果 |
| --- | --- | --- | --- |
| L1 | `make verify.semantic.registry.lint` | 46 | PASS（三载体 `--check` 一致） |
| L1 | `make verify.unified_page_contract.v2.assembler` | 4 源 | PASS（缓存指纹已重钉） |
| L1 | `make verify.semantic_runtime_resolution` | 123 | PASS |
| L1 | `make verify.business_config.formal_list.unit` | 201 | PASS |
| L1 | `make verify.frontend.professional_component_registry.unit` | 284 | PASS |
| L1 | `make verify.frontend.professional_detail_collection.unit` | 127 | PASS |
| L1 | `make verify.frontend.professional_relation_field.unit` | 77 | PASS |
| L1 | `make verify.frontend.professional_business_value.unit` | 42 | PASS |
| L1 | `make verify.frontend.professional_base_field.unit` | 70 | PASS |
| L1 | `make verify.contract.schema.declaration.sync` | 8 | PASS |
| L1 | `make verify.agent.ledger.unit` | 15 | PASS |
| L1 | `make verify.frontend.auth_surface.guard` | 1 | PASS |
| L1 | `make verify.frontend.typecheck.strict` | 1 | PASS |
| L1 | `make verify.frontend.lint.src` | 1 | PASS |
| L2 | `make verify.form_structure_authority_unification.unit` | 215 | PASS（`ci.local.iteration` 推荐） |
| L2 | `make verify.frontend.dev.incremental.unit` | 29 | PASS（`ci.local.iteration` 推荐） |

负例（先确认基线干净，再证明注入被检出）：载体被手改 → 漂移检出；
把解析产物里 `amount` 的 `monetary` 改成 `char` → 载体漂移检出（证明输入确实是解析产物）；
`semantic.yaml` 撤掉已投影语义 → 投影 fail-closed。

### 范围边界

- 不做 presentation/behavior 段：`contracts/` 下目前没有任何 `presentation:`/`behavior:`
  顶层段，也没有消费方；凭空新增即"已声明未消费"，留给 01-E/02 按真实消费方落地。
- 15 份域契约中只有 `payment-request.yaml` 绑定了 `source_of_truth.model`，
  其余 14 份未绑定即不会被投影（保持可见的未投影，而不是猜 key）。补绑定是后续收口项。

## 01-E 交付（状态归属边界冻结）

产出 `docs/contract-runtime-state-ownership.md`：明确四类"状态/可用性"的事实源、
运行时载体与消费方，**不建状态机 DSL、不新增运行时能力**。判定依据取自代码事实，
不是新声明：

- `statusContract` / `actionContract` / `dataContract` / `runtimeContract` 的生产模块
  都自带 `NO_BUSINESS_FACT_AUTHORITY = True`：它们是投影，不持有业务事实。
- `workflowContract` 由 P1 模块按记录现算
  （`smart_construction_core/core_extension.py` -> `sc.workflow.contract.service.describe_record(record)`），
  所以业务状态永远以 ORM 记录为准；行业档案只提供"状态 -> 动作"。
- 权限判定在后端（group / access rule / record rule + Scene-action 绑定校验），
  前端只消费 `statusContract.globalStatus` 的结论与 `REASON_*` 码。

该文档把"前端不得用 state 字符串自判、不得用用户组复现授权"固化为可复核结论，
并把状态机 DSL 明确推到 FE-CONTRACT-RUNTIME-02。

验证：`verify.docs.all`（含 inventory/links/temp_guard/contract_sync/product_boundary）
7 例 PASS；`verify.agent.ledger.unit` 15 例 PASS。

## 范围边界（本轮明确不做）

- 不声明 `capabilities`：当前没有运行时消费方，声明即为悬空能力声明，与 00 清单
  `G8` 登记的 extensions 占位同类。能力语义随行为运行时（02）落地。
- 不做行为/状态机 DSL：状态与转移的归属见 01-E 的
  `docs/contract-runtime-state-ownership.md`。
- 不新增页面、不新增组件（除非某语义确无渲染器）、不做低代码设计器。
- 01-A 不改运行时渲染，因此**不是产品交付证据**。

## 验证

| 层 | 命令 | 结果 |
| --- | --- | --- |
| L1 | `make verify.semantic.registry.lint` | 见 run 回执（非零用例） |
| L1 | `python3 scripts/verify/contracts_lint.py` | 49 issues，与 `origin/main` 基线一致、无 `registry/` 相关项 |

`make verify.contract.lint` 的 49 项为 pre-existing 债务（00 清单 `G7`），
本批次既未引入也未修复，登记在 run 的 `blockers`。

## 后续批次（owner 指定顺序，不并行）

- ~~**01-B** 后端统一消费 registry~~（完成，见上）。
- ~~**01-C** 前端 registry 接管：`semanticResolver` + 单测
  `verify.semantic_runtime_resolution`~~（完成，见上；命名渲染器按声明层真实事实断言）。
- ~~**01-D** 字段语义化~~（完成，见上：改为由模型+视图解析产物生成，删除手写 semantic）。
  剩余 01-D3：浏览器验收（新建→保存→刷新，确认 money/date/relation 由语义渲染）。
- ~~**01-E** 状态归属边界~~（完成，见上：`docs/contract-runtime-state-ownership.md`）。

## 边界收口轮（交付语义 vs 渲染实现裁定落地）

owner 裁定：契约可以表达"为了某终端如何交付"，不能表达"前端组件如何布局和渲染"。
本轮按该裁定清理三层中的混合，不新增探针框架，不放宽任何断言。

### 删除（渲染实现出契约）

- `layoutHints.columns`：契约不再声明栅格列数；列数由前端 `layoutSpan.layoutGridUnits()` 唯一权威。
  同步删除守卫里 `columns == renderer_layout_grid_units()` 与 `DESKTOP_LAYOUT_GRID_UNITS` 绑定。
- 终端投影不再改写 `runtimeContract` 的渲染策略（原来移动端会把 `renderStrategy` 改成
  `scheduled` 并注入 `virtualization.mobile`）；`renderStrategy`/`virtualization` 作为 Runtime 内部
  策略保留在运行时层，不作为终端交付内容。
- 移动端 `span=1` 重写：删除。终端投影不再按终端改写字段宽度。
- `componentConfig.mobile.fullWidth`：删除（CSS 级行为属前端）。

### 改名保留（交付语义）

- `clientDensity`（UI Kit 词汇 `comfortable/compact`）→ `deliveryDensity`（交付语义 `standard/compact`）。
  映射到 UI Kit 视觉密度是前端职责（`ContractFormDriverHost.vue`）。
- `span` 保留为"交付表达"分面；本轮不改名（见下"未决"）。

### 机制与守卫

- 投影边界清洗 `ui_contract_v2_projection.normalize_layout_hints_entries`：剥离
  `columns/gridColumns/cssWidth/renderStrategy/virtualization`。
- 守卫 `unified_page_contract_v2_client_guard.py`：源契约与每个终端的投递面都 fail-closed 禁止渲染实现键；
  终端投影必须保留 `runtimeContract`（除 `deliveryProfile` 外不得改写）。
- 组件注册表守卫测试同步到新不变量（`version` 必填 + 渲染键禁止），147 例通过。
- 示例契约与 `client_trimming_snapshot_v2.json` 对齐新投递面；`ASSEMBLED_CONTRACT_CACHE_VERSION`
  与缓存输入指纹重钉（`ui-contract-v2-2026-10-12-delivery-face-render-traits-removed`）。
- 新增边界文档 `docs/architecture/rendering-trait-contract-boundary-v1.md`。

### 验证（17 项回执全部 passed）

`unified_page_contract_client`1、`unified_page_contract_schema`3、`semantic_registry_lint`46、
`frontend_component_registry`284、`schema_declaration_sync`8、`assembler_cache_pin`1、
`semantic_runtime_resolution`123、`frontend_business_value_alignment`42、
`frontend_detail_collection_alignment`127、`frontend_relation_field_alignment`77、
`frontend_base_field_alignment`70、`frontend_auth_surface`1、`assembler_contract_surface`201、
`frontend_typecheck`1、`frontend_lint_src`1、`docs_governance`7、`agent_ledger`15。

### 未决（未擅自执行，交由 owner 判断）

1. `span → deliverySpan` 契约面改名：仓库内 `span` 同名但不同义——`scene_orchestration.span`
   是无关的 Odoo ORM 字段（`fields.Integer(default=1)` + `<field name="span"/>` 视图）。改名须逐处
   分类契约分面与无关字段，并会失效已采集的运行时证据（`docs/contract/snapshots/ui_contract_v2_intent_admin.json`、
   `artifacts/backend/daily_dev_acceptance_probe.*`）。建议作为同分支的独立小批次。
2. `docs/contract/exports/intent_catalog.json` 与 `docs/contract/snapshots/ui_contract_v2_intent_admin.json`
   仍列出旧键（`layoutHints.clientDensity`/`layoutHints.columns`）。后者是**实采 intent 快照**，
   且在本轮改动前就已陈旧（`columns: 12`，而当时投影已发 24），刷新需受管运行时重新采集（L3/L4），
   不手改证据。

  → **已在本节"边界冻结轮"解决**（受管运行时再采集 + 派生 catalog 重生成）。

## 边界冻结轮（B：运行时事实再采集 → 终端交付面 → 运行时策略守恒）

owner 裁定顺序：**B1 运行时事实再采集 → B2 证据快照更新 → B3 `span → deliverySpan` 独立迁移**；
本轮只做 B1/B2，`span` 改名留作后续独立批次（与无关 ORM 字段同名，不是字符串替换）。

### B-01 受管运行时再采集（不手改证据）

入口：受管隔离档 `local.contract-snapshot.*`（项目 `sc-contract-snapshot-v1`、库 `sc_contract_snapshot`、
dbfilter 精确、nginx 18091 / odoo 8080），`ENV=dev` 源码挂载优先
（`addons_path` 中 `/mnt/source-addons` 先于 `/mnt/product-addons`，且
`/mnt/source-addons/smart_core/handlers/ui_contract_v2_projection.py` 的 md5 与本工作区一致）。

- 重建播种：seed = `sc-local-dev/sc_dev_demo`（只读），dump sha256
  `c66afb379546b5b9e683bcfe86fe231a05b65394187698d2ebcb0f32d2926157`（196240685 bytes），
  恢复后校验 `project_project=72 / payment_request=139 / res_users=61`，`smart_core=17.0.1.1.14`。
- 再采集 `ui_contract_v2_intent_admin`：blob `8ccbbd4fe1b88f35c0d8ee3d037bb9e1c371c691`
  → sha256 `e09bf36869a27a07486823d42c490aea96d9700fffe991d55b697a5ffd5ec3d6`。

快照陈旧性已证伪为"未刷新"而非"代码回归"：HEAD 的 assembler 本就发 `layoutHints: {}`，
旧快照里的 `layoutHints.clientDensity/columns` 早于 HEAD 的边界收口提交。再采集后：

- 源契约 `layoutHints`：`{clientDensity, columns:12, deliveryProfile, mobileCollapse}`
  → `{deliveryDensity:"standard", deliveryProfile:"full", mobileCollapse:false}`。
- 源契约 `runtimeContract` 不再含 `renderStrategy`（仅 runtime 内部策略：patchStrategy/cachePolicy/
  optimistic/lazyContainer/virtualization/retryPolicy/interactionMode/actionTarget/deliveryProfile）。
- 派生 `docs/contract/exports/intent_catalog.json` 同步重生成
  （`make contract.catalog.export`，确定性可复现），sha256 `8e04403f62ddea6cf23a5b41db22e51398aa45668be910a2b1e2f089f7a5fda2`。

### B-02 三端交付面（真实运行时，非重投影）

在 `docs/contract/cases.yml` 增加两个终端用例并受管导出（同一 intent、仅 `client_type` 不同），
使三端各自有实采快照，而不是把 web_pc 的投递面再投影一次：
`ui_contract_v2_intent_admin_wx_mini.json`（sha256 `dd717740a85b3f92d1dab55f561cf3792c4f1508c7e04a0f8bf576eec89ba3`）、
`ui_contract_v2_intent_admin_harmony_h5.json`（sha256 `93dec47a89445c69c5c594f659bd5e4baf8849112c367c125ac3ed90e763e4be`）。

| client | adaptMode | deliveryProfile | deliveryDensity | mobileCollapse | 交付裁剪 | 渲染实现键 |
|-|-|-|-|-|-|-|
| web_pc | pc | full | standard | false | 14→14 widgets | 无 |
| wx_mini | mobile | mobile_compact | compact | true | 14→12 widgets（上限 12） | 无 |
| harmony_h5 | mobile | mobile_compact | compact | true | 14→12 widgets（上限 12） | 无 |

三端 `runtimeContract` 除 `deliveryProfile` 外逐键一致；`renderStrategy`/`virtualization` 未出现在
终端投递面。受管 gate（限定这 3 个用例、`REF_DIR=docs/contract/snapshots`）：
`PASS ui_contract_v2_intent_admin / _wx_mini / _harmony_h5`，即跟踪快照与实时导出确定性一致。

### B-03 断言补强：Runtime 内部策略 ≠ Delivery Contract

原有断言 `offered_runtime != source_runtime` 是**非对称**比较（只对终端侧剔除 `deliveryProfile`），
在真实契约（源含 `runtimeContract.deliveryProfile`）下会误报，而 fixture 恰好没这个键才"看起来通过"。

- 守卫改为**对称**比较（两侧都剔除 `deliveryProfile`），并新增
  `RUNTIME_INTERNAL_POLICY_KEYS`（renderStrategy/virtualization/patchStrategy/cachePolicy/optimistic/
  lazyContainer/retryPolicy）**逐键守恒**断言：终端投影不得改写运行时内部策略。
- `examples/form_project.json` 补 `runtimeContract.renderStrategy/deliveryProfile`，使断言对真实形态非空转。
- 负例（内存注入，未新增探针框架）：未注入基线下守卫 exit 0；注入 `runtimeContract.virtualization`
  后 exit 1 并精确报 `terminal projection must not rewrite runtime-internal policy virtualization`；
  注入 `layoutHints.renderStrategy/columns` 后 exit 1 并报 `layoutHints must not carry rendering implementation ...`。

### 受影响与新增回执（19 项）

本轮被真实失效并重跑：`unified_page_contract_client`1、`unified_page_contract_schema`3、
`assembler_cache_pin`1（三者的声明输入含 `examples/` 或守卫本身，被本次 fixture/守卫改动失效）。
新增登记：`contract_catalog`16（`verify.contract.catalog`）、`page_contract_v1_zero_residue`1。
`agent_ledger`15 因 run 账本变更刷新。其余 12 项声明输入未变，按复用规则保留原回执，不重跑。

### 仍未决（留待后续）

1. `span → deliverySpan` 契约面改名（B3）：限定在 `contracts/`、runtime 投影、前端契约类型；
   不动无关 ORM 字段 `scene_orchestration.span`；改名后需再次刷新受其影响的运行时证据。
2. `FE-CONTRACT-RUNTIME-01-B` Semantic Registry 收口在干净边界上进行（owner 指定：B → 提交 → Semantic Registry）。

### 边界冻结轮补记：L2 证据缺口闭合（27 项回执）

`make ci.local.iteration` 对本次改动建议的 8 个前端 L2 目标此前只在会话内执行过、未进入 run 索引，
属于真实证据缺口。本轮把这 8 项登记为受管检查并以受管入口重跑（`make agent.run.begin/record`），
全部 exit 0、非零用例：

| 检查 | 目标 | 用例数 |
|-|-|-|
| form_container_presentation_guard | verify.form_container_presentation.guard | 1 |
| form_structure_authority_unification | verify.form_structure_authority_unification.unit | 215 |
| canonical_form_presenter | verify.frontend.canonical_form_presenter.unit | 180 |
| frontend_dev_incremental | verify.frontend.dev.incremental.unit | 29 |
| page_pattern_reference_parity | verify.frontend.page_pattern_reference_parity.unit | 28 |
| frontend_primitive_adapter | verify.frontend.primitive_adapter.unit | 41 |
| product_page_pattern | verify.frontend.product_page_pattern.unit | 17 |
| frontend_style_system | verify.frontend.style_system.guard | 1 |

登记后 `agent_ledger` 因 run 账本字节变化被判失效并已重跑刷新。最终 run 索引 27/27 可复用，
未变更层的原回执继续复用、不重跑。

## 01-B（payment 语义化）交付：产品特判退场 + 后端字面量守卫

owner 裁定：**用 `payment.request` 证明 Semantic Registry + Delivery Projection + Runtime Renderer 的第一条完整链路**，
不再做架构设计。本批次按 01-B「Payment Contract Migration」执行：payment 字段语义化、presentation contract 对齐、
移除 payment 特殊 component 映射。01-E（`span → deliverySpan`）按裁定延后为独立迁移批次。

### 根因（三处，都是"渲染与交互之外的判断"离开了契约）

1. **产品层持有组件键。** `core_extension_contract_normalizers.py::normalize_payment_settlement_detail_component`
   以 `model == "payment.request"` + `field_code == "outflow_line_ids"` 分支写入字面量
   `sc.payment.settlement_detail_collection`。字段语义（"这是一个可从结算单引入、金额与明细合计绑定的集合"）
   因此没有进入声明层，新增同类字段只能再写一段映射代码——违背"新增字段只声明 semantic"的验收标准。
2. **历史 component identity 假象。** 同文件 `general_contract_tax_contract` 给 `tax_id` 生成的字段节点写
   `"componentKey": "sc.input.many2one"`。该键从未被 `contracts/registry/component.yaml` 声明（该文件声明的是
   `sc.input.text/number/date/...`，many2one 的事实身份是 `sc.relation.many2one`）。改动前装配器
   `_component_registry` 不过滤，会把任意键原样发布，于是"契约宣称了一个前端无法解析的身份"：
   前端对未登记键是**抛错**而非静默回落（`professionalComponentRegistry.ts:193`
   `PROFESSIONAL_COMPONENT_UNREGISTERED`）。
   该行由基线提交 `401bcb3b` 引入，非本批次新增。
3. **后端私有版本字面量。** `unified_page_contract_v2_assembler.py::_component_registry` 与
   `handlers/ui_contract_v2.py` 各自持有 `{"version": "1.0"}`，即组件身份事实的第二份副本。

### 交付

| 文件 | 作用 |
| --- | --- |
| `addons/smart_construction_core/core_extension_contract_normalizers.py` | 新增 `FIELD_SEMANTIC_DECLARATIONS`（模型→字段→语义）与 `SEMANTIC_PRESENTATION_VOCABULARY`（语义→交付词表，原 `componentConfig` 逐字节搬迁）；新增通用函数 `normalize_declared_field_presentation`（无模型分支、无组件键）；删除 `normalize_payment_settlement_detail_component` 与 `PAYMENT_SETTLEMENT_DETAIL_COMPONENT_KEY`；tax 节点改用 `semantic_resolver.component_key("many2one", {"ttype": "many2one"})`。模块头部不再 import 任何组件键。 |
| `addons/smart_core/core/contract_runtime/semantic_resolver.py` | 新增公共入口 `component_registry()` + `COMPONENT_CONTRACT_VERSION`：全运行时唯一的组件身份/版本构造器，**fail-closed**——未登记键报 `contract_component_undeclared` 且不发布。 |
| `addons/smart_core/core/unified_page_contract_v2_assembler.py`、`addons/smart_core/handlers/ui_contract_v2.py` | 私有 `"1.0"` 字面量退场，统一委托 `component_registry()`。 |
| `scripts/verify/semantic_registry_lint.py` | 新增后端方向检查 `backend_component_key_literals`：扫描 `addons/**/*.py` 中的组件键字面量，未声明即报错（测试模块除外）。 |
| `scripts/verify/test_construction_semantic_declarations.py` | 新增 12 项：声明语义均在 registry、组件来自 registry、registry 身份发布、词汇合并、未声明字段/其他模型/非表单不动、未声明语义的负例（**先确认未注入基线正常**）、前端 required-paths 全部被词汇满足。 |
| `scripts/verify/frontend_professional_detail_collection_guard.py` | 改为读 `SEMANTIC_PRESENTATION_VOCABULARY` 表抽取 dialog 词条。 |

### 行为与兼容

- 解析结果不变：`payment.request.outflow_line_ids` 仍渲染 `sc.payment.settlement_detail_collection`，
  只是来源从"产品层字面量"改为"声明语义 → registry 解析"。
- **历史 component identity 假象消除**：`sc.input.many2one` 从产物中消失，字段恢复真实语义身份——`many2one` 不是组件，是关系语义，正确身份由 `relation` 语义解析为 `sc.relation.many2one`。
- **装配缓存指纹重钉**：装配输入（handler/assembler/projection/client/resolver + 两个生成载体）变化，
  `ASSEMBLED_CONTRACT_CACHE_VERSION` 升为 `ui-contract-v2-2026-10-12-product-semantic-declarations`，
  `ASSEMBLED_CACHE_INPUTS_SHA256` 重算（守卫按失败信息给出的方向重钉，未放宽断言）。
- 文档同步：`docs/frontend_productization/contract-runtime-gap-list.md` G6 中失效符号引用改为闭合结论。

### 验证（本批次实际执行；run 索引 28/28 可复用）

`make ci.local.iteration` 判定 8 个前端 L2 目标 stale，全部经 `make agent.run.begin/record` 重跑并登记；
另新增 1 项登记、2 项检查输入依赖修正（此前 `scripts/verify/test_construction_semantic_declarations.py`、
P1 归一化器、dialog 模型未在任何检查输入内，属证据缺口）：

| 检查 | 目标 | 用例 |
| -|-|-|
| semantic_registry_lint | verify.semantic.registry.lint | 64 |
| native_view_workflow_action_coverage（新增登记） | verify.native_view.workflow_action_coverage | 62 |
| form_structure_authority_unification | verify.form_structure_authority_unification.unit | 215 |
| assembler_contract_surface | verify.business_config.formal_list.unit | 201 |
| assembler_cache_pin | verify.unified_page_contract.v2.assembler | 1 |
| frontend_component_registry | verify.frontend.professional_component_registry.unit | 147+137 |
| frontend_detail_collection_alignment | verify.frontend.professional_detail_collection.unit | 127 |
| frontend_business_value_alignment | verify.frontend.professional_business_value.unit | 42 |
| frontend_relation_field_alignment | verify.frontend.professional_relation_field.unit | 77 |
| contract_catalog | verify.contract.catalog | 16 |
| agent_ledger | verify.agent.ledger.unit | 15 |

语义 resolver 单测由 17 项扩到 21 项（新增 `ComponentRegistryTest`：单一版本事实、未登记键 fail-closed、
非序列声明不发布、解析器可产出的键必可发布）。

### 边界修复记录 RUNTIME-BOUNDARY-FIX-01

> 定位：**Contract Runtime 边界治理发现的基线缺陷修复**，不是 FE-CONTRACT-RUNTIME-01 的业务能力扩展。

```text
发现：历史 synthetic field 使用未注册 component key（sc.input.many2one）
修复：component identity -> semantic registry identity（many2one -> relation -> sc.relation.many2one）
范围：sc.general.contract tax 字段（general_contract_tax_contract）
影响：不在 payment runtime 路径上
验证：verify.semantic.registry.lint PASS（含 backend_component_key_literals）
```

不纳入产品文档，不扩大扫描范围。

### 范围边界（本批次明确不做）

- 不动 `span → deliverySpan`（owner 裁定：01-E 独立迁移，限定 `contracts/`、runtime 投影、前端契约类型，
  不动 ORM `scene_orchestration.span`）。
- 不动前端组件实现与渲染分发（仍是 6 个已登记渲染器）。
- 不处理历史失败项：`verify.contract.lint` 49 项、陈旧 `res.users` 断言、容器内 L3/L4 用例。

## 01-C（Runtime Verification）交付：声明驱动解析的自动化 + 运行时回执

目标不是"页面好看"，而是证明"新增字段只声明 semantic，不新增任何前后端映射代码"这条标准是可执行事实。

### 自动化（本批次新增用例）

`scripts/verify/test_construction_semantic_declarations.py::NormalizerConsumptionTest
.test_a_new_field_needs_only_a_semantic_declaration`：把一个原本按事实渲染为文本的字段
（`settled_amount`）只加一行 `semantic: money` 声明，断言

1. 基线（注入前）该字段由自身事实选择 `sc.input.text`——先证明对照正常，再证明注入被检出；
2. 注入后节点 `componentKey == sc.value.money`，`fieldDescriptor.semantic == "money"`；
3. 该身份被发布进 `layoutContract.componentRegistry`。

若任何一侧仍需为新字段写映射代码，此用例无法通过。绑定检查 `verify.semantic.registry.lint`
用例数 63 → 64。

### 运行时回执（受管 `sc-local-dev`，非诊断环境）

受管入口 `make local.dev.restart` 后，以受管 demo 身份（`.env.dev` 的 `SC_DEMO_USER_PASSWORD`）经
`POST /api/v1/intent` 取 Bearer，再调 `ui.contract.v2` intent（注意：`/api/contract/get` 是旧 v1 端点，
不产 `layoutContract`，不可用于本证据）：

- `payment.request` form：`outflow_line_ids` 节点 `componentKey=sc.payment.settlement_detail_collection`、
  `fieldDescriptor.semantic=payment_settlement_detail_collection`、交付词表 `introduceLabel=从结算单引入`、
  三条 `actionRefs` 齐全 —— 声明语义 → registry → 契约 → 前端全链贯通。
- 全量 payload 中 `sc.input.many2one` 已消失。
- 终端投影：`web_pc` → `adaptMode=pc`/`deliveryProfile=full`；`wx_mini`、`harmony_h5` → `mobile`/`mobile_compact`
  （`meta.deliveryTrim` 记录容器 129→6、widget 94→5）；`runtimeContract` 三端逐键一致且不含渲染实现键。
- `sc.general.contract` tax 节点 → `componentKey=sc.relation.many2one`（真实解析，非字面量）。

浏览器侧 PC/mobile + 明暗主题的实机核对按 01-D 执行，回执单独记录。

## Layout Vocabulary 收口（owner 裁定 A+：词汇升级，行为不变）

### 问题

`formStructureContract.layoutPolicy` 一个字段名同时承载三件不同事实（结构来源、结构权威、兼容模式），
并且取值混入实现史词：`container_tree_authority`、`native_authority`、`business_config_sections`、
`overview_then_task_slots`、`category_sections_as_task_tabs`。契约应当表达事实，而不是表达实现过程。

### 裁定边界（不扩范围）

- 保留 native_view / business_orchestration 两条结构分支，**不合并**。
- 不改已发布编排契约（payment 145 / 4），不迁移 payment slots。
- `span → deliverySpan` 仍留 01-E，本轮不动。

### 双维词表

- `structureSource` ∈ {`native_view`, `business_orchestration`, `business_category_policy`, `entry_semantic_surface`}
- `structureAuthority` ∈ {`container_tree`, `native_form_slots`, `task_sections`}

旧值→新值（仅 `layoutPolicy` 语境）：`container_tree_authority`→`container_tree`；
`native_authority`→`native_form_slots`；`business_config_sections`/`overview_then_task_slots`/
`category_sections_as_task_tabs`→`task_sections`。

**关键区分（勿混）**：`form_structure_authority="native_authority"` 是 view_orchestrator 的治理 token，
仍然有效，本轮不改；`native_authority_safe` 是另一套词，不改。

### 逐位等价证明

`_build_form_structure_contract`（`addons/smart_core/handlers/ui_contract_v2.py`）三处 return 加
`_inject_business_operation_contract` 一处，共 4 个产出点。新 `structureAuthority` 在每一点都等于旧
`layoutPolicy` 经上述双射替换后的结果，谓词（`presentation_mode == "task"`、
`structure_authority == "entry_semantic_surface"`）保持不变，故为**同一函数的重命名**；
`structureSource` 为新增维度，旧消费者不读它。

实证（旧代码采集于 `/tmp/fe01d_*`）：

| 对象 | 旧 `layoutPolicy` | 新 `structureSource` / `structureAuthority` |
|-|-|-|
| project.project | `container_tree_authority` | `native_view` / `container_tree` |
| payment.request | `native_authority` | `native_view` / `native_form_slots` |

### 交付

- 后端生产者：`ui_contract_v2.py`（4 产出点）、`unified_page_contract_v2_runtime.py`
  （`FORM_STRUCTURE_TREE_AUTHORITIES={container_tree}`）、`unified_page_contract_v2_assembler.py:2747`、
  `ui_contract_v2_projection.py`。
- schema：`unified_page_contract_v2.schema.json`（required 双字段 + enum + allOf 绑
  `structureAuthority.const=container_tree`）；fixtures 同步。
- 前端：`contracts/v2/types.ts`、`schema.ts`（fail-closed 解码，**不默认** container_tree）、
  presenter / render model / floorplan / driver host / native bridge / `ContractFormPage.vue` 同步；
  presenter 内部 identity 字段改名 `structureAuthority`→`bodyStructureAuthority`（避免与契约键同名混淆）。
- 消费端测试/守卫：P1 容器内 15 个测试断言迁移；`canonical_form_presenter_test.ts`、
  `contract_v2_runtime_policy_test.ts`、`form_structure_surface_contract_test.ts`、
  `standard_page_type_browser.mjs`、`form_structure_contract_projection_matrix.py`（重生成产物 `--check` PASS）、
  `frontend_material_domain_browser.mjs`、`local_dev_candidate_visual_smoke.mjs`、
  `test_local_dev_candidate_frontend.py`、`local_dev_project_create_contract_action_scope.py`、
  `frontend_v2_policy_projection_guard.py`（schema enum == 常量 + strict decoder 接受性检查 + 兼容别名拒绝）。
- 新守卫：`scripts/verify/layout_vocabulary_lint.py`（9 个载荷面禁旧字段名与 5 个旧取值，四载体一致性，
  生产者必须真的发布两个字段）+ `scripts/verify/test_layout_vocabulary_lint.py`（11 项负例）；
  `make/contract.mk` 新增 `verify.layout.vocabulary.lint`。
- 残留扫描：代码中已无读取 `layoutPolicy` 的逻辑；剩余命中仅为历史叙事注释与 lint 自身定义。
  两处"结果态"注释（light_forms / engineering_process）已改为新词；历史叙事段保留。
- 文档：`docs/contract/form_structure_contract_v2.md`、
  `docs/contract/frontend_mainline_contract_integration_v2.md`、
  `docs/architecture/form_structure_surface_contract_boundary_v1.md`、
  `page-pattern-reference-detail-ledger-v1.json`、`page-pattern-reference-contract-gaps-v1.md`。

## 01-D（产品验收）交付：语义/终端/闭环/结构来源一致

受管环境 `sc-local-dev`（odoo 8070 / nginx 18081），demo 固定口令（`.env.dev`）。证据目录
`.runtime/agent-runs/FE-CONTRACT-RUNTIME-01/01d/`。

### 场景 1：字段表达

`/f/payment.request/new`（wutao）渲染 `ProfessionalRelationFieldControl` /
`ProfessionalBusinessValueControl` / `ProfessionalBaseFieldControl`；金额、关系、日期标签齐全；
native locator 采用 `/form[1]/sheet[1]/group[g]/field[f]` 原生路径。

### 场景 2：终端投影

1440×950 light 与 390×844 dark 均渲染成功，renderer 集合一致（23 locators），0 pageerror。

### 场景 3：保存闭环

`/f/payment.request/new` 填 project/partner（内联关系补全）+ amount=100 → `保存草稿`。
校验未通过时正确阻断（"不能为空/必填"）；补齐后落库为记录 `payment.request#2847`（PRQ2601066，草稿）。
刷新 `/f/payment.request/2847`：金额持久化 `100.00`，renderer 集合与保存后一致（32 locators）。

**注意**：删除/批量能力尚未接入 UI（`更多操作` 无删除项），故该记录未被清理；如后续需要，走
`make local.dev.reset_payment_request_fixture` 受管入口，不使用容器直连绕过。

### 场景 4：结构来源一致性（owner 新增验收点）

同一 renderer 家族（`NativeFormTreeRenderer` + `FormSection` + `ScFormItem`）承载两条结构来源：

| 对象 | structureSource / structureAuthority | 渲染 |
|-|-|-|
| project.project | `native_view` / `container_tree` | 18 locators，含 `ProfessionalDetailCollectionControl` |
| payment.request | `native_view` / `native_form_slots` | 23 locators，4 slots |

即"不是两个页面系统，而是两个 Contract Runtime 输入源"。

### 附：tax 字段完整性（发现 A 回归）

`sc.general.contract` create 契约中 `tax_id` 节点 `componentKey=sc.relation.many2one`（合法登记身份），
全 payload `sc.input.many2one` 计数 0。

### 范围外观察（不修，仅记录）

`wutao` 点击侧栏"付款申请"（菜单 559 / action 809）返回
`403 PERMISSION_DENIED · 用户无权访问菜单 付款申请`；同菜单 `demo_finance` 正常（共 0 条）。
本批次 `git diff` 无任何菜单/权限/security 改动，属角色权限数据事实，非本轮引入。

## 本轮验证回执

| 层 | 命令 | 结果 |
|-|-|-|
| L1 | `make verify.layout.vocabulary.lint` | PASS（11 tests OK，surfaces=9） |
| L1 | `python3 scripts/verify/frontend_v2_policy_projection_guard.py` | PASS |
| L1 | `python3 scripts/verify/form_structure_contract_projection_matrix.py --check` | PASS fields=77 |
| L1 | `make verify.frontend.typecheck.strict` | PASS |
| L2 | `make verify.frontend.canonical_form_presenter.unit` | PASS（177 cases） |
| L2 | `make verify.frontend.form_structure_surface_contract.unit` | PASS |
| L2 | `make verify.frontend.contract_v2_runtime_policy.unit` | PASS（page access cases=6） |
| L2 | `make verify.frontend.contract_v2_render_authority.unit` | PASS fields=326 |
| L2 | `make verify.frontend.native_form_structure_responsibility.unit` | PASS cases=12 |
| L2 | `scripts/verify/test_form_structure_authority_unification.py` | 215 tests OK |
| L2 | `addons/smart_core/tests/test_unified_page_contract_v2_runtime.py` | 23 tests OK |
| L2 | `..._mobile_compact.py` | 119 tests OK |
| L2 | `addons/smart_core/tests/test_ui_contract_v2_boundaries.py` | 135 tests OK |
| L3 | `make local.dev.restart` + `make local.dev.frontend` | EXIT=0 |
| L4 | 01-C 运行时探针（3 身份 × 2 模型 × 2 profile） | 新双维、无旧字段 |
| L4 | 01-D 浏览器 4 场景 | PASS，0 pageerror |

## 列表批处理能力事实核对（收口期，仅记录）

触发：收口期发现 `payment.request#2847` 需要清理，但界面未见可用的批量入口。

事实（契约消费链，非猜测）：

- **批量删除已接入且契约驱动**：
  - 契约 `actionContract.surfacePolicies.batch_policy.available_actions` 含 `delete`；
  - `execution_intents.delete = api.data.unlink`；
  - 前端客户端能力表 `DECLARED_BATCH_EXECUTORS['api.data.unlink'] = 'unlink'`；
  - 后端 `handlers/api_data_unlink.py` 以 `delete_policy.allowed && delete_mode == "unlink"` 把关；
  - 列表 `available_actions` 由 `utils/contract_governance_list_surface.py` 依据契约 `batch_policy` + ACL(read/write/unlink) 推导。
  - 结论：删除不是未接线，而是本轮未对 `#2847` 走列表工具栏，故保留该记录，清理走受管入口
    `make local.dev.reset_payment_request_fixture`。
- **批量导入已接入（本轮完成，取代此前「能力缺口」结论）**：
  - 后端单一能力声明源 `addons/smart_core/utils/collection_action_capability.py`
    （`SELECTION_SCOPE_INTENTS`、`IMPORT_ACTION`/`IMPORT_INTENT`）。`build_collection_capabilities()`
    产出 `surface_policies.collection_capabilities.actions[]`（`action/scope/intent/available`），
    `batch_policy` 改为同一份 actions 的 selection 投影，消灭双来源；
    `project_scope_actions()` 的可用性判定改为 `row.get("available") is True`（未声明即不可用）。
  - 受管意图 `api.data.import`：`addons/smart_core/handlers/api_data_import.py` 委托内核 `base_import`，
    要求 `smart_core.group_smart_core_data_operator`，支持 dry-run 预览与非 dry-run 幂等；
    `core/intent_operation_policy.py` 将 `import` 归入 `create` 权限面。
  - 前端单一意图→执行器表 `DECLARED_CAPABILITY_EXECUTORS`（含 `api.data.import -> import_records`）
    与单入参解析器 `resolveDeclaredCapabilities(surfacePolicies)`；已删除「从 `batch_policy` 反推声明」的
    客户端归一化——集合策略缺声明时以 `ContractGapError` 停机，不再把动作静默降级到 selection 域。
  - 登记为 ledger `declarationBinding #5`（`onMissing: stop`）。

运行时实测（local.dev，`payment.request` list，action 809）：

| 身份 | `collection_capabilities.actions` | `batch_policy.available_actions` |
|-|-|-|
| `wutao` | export / archive / activate / delete / **import** | export / archive / activate / delete |
| `demo_finance` | export / archive / activate / **import** | export / archive / activate |
| `demo_pm` | export | export |
| `demo_readonly` | （403，无页面权限） | — |

即 `import` 以 collection 域出现，可见性完全由契约声明 + ACL/组权限推导
（`demo_finance` 无 unlink 权限，`delete` 不出现）。本轮契约驱动的列表批能力集合：
`export / archive / activate / delete / import`。

## 环境根因：本地登录反复「认证失败」（本轮修复 + 实测）

现象：本地 `sc-local-dev` 经反代登录报 `AUTH_REQUIRED 用户名或密码错误`，被误判为密码问题。

根因（非密码）：`config/nginx/conf.d/default.conf` 的
`map $http_x_odoo_db $sc_proxy_db_from_header { '' sc_demo; }` 把「无 db 提示」的请求硬编码兜底到
`sc_demo`；该库在 local.dev 的 dbfilter `^sc_dev_demo$` 下不存在，于是任何不带 `?db=`/`X-Odoo-DB`
的 `/api/` 请求都落到错误的库并返回认证失败。代理拥有了它不该拥有的「库默认」。

修复（库默认归 profile）：
- `config/nginx/conf.d/default.conf` → `config/nginx/templates/default.conf.template`，兜底写为 `${SC_PROXY_DEFAULT_DB}`；
- `docker-compose.yml` nginx 服务注入 `SC_PROXY_DEFAULT_DB=${DB_NAME}` 与
  `NGINX_ENVSUBST_FILTER: '^SC_PROXY_DEFAULT_DB$'`（只替换该变量，nginx 自身 `$变量` 原样保留），
  volume 改挂 `./config/nginx/templates`（镜像自带 envsubst 入口在容器启动时渲染）；
- 新增 `scripts/verify/nginx_proxy_db_authority_guard.py`（锁机制不锁库名）+ 6 个负例自测，
  并入 `verify.environment.topology.guard`；
- `docs/ops/dev_bootstrap.md` 记录该边界，禁止把库名写回模板 literal。

实测：容器内已渲染 `'' sc_dev_demo;`，`nginx -t` OK；无 db 提示 `POST /api/v1/intent{login}`
对 `wutao/demo_pm/demo_finance/admin` 均 200；Playwright 真实浏览器 `wutao/scdevpass` 登录落到 `/`，
`system.init` 200、0 pageerror。

固定口令：`scdevpass`，仅在 `scripts/dev/local_dev_demo_credentials_prepare.sh` 声明一处并写入
0600 `.env.dev`，见 `docs/ops/local_development_environment_v1.md`；`.env.dev`、`make/dev.mk`、
生命周期测试口径一致。

范围外观察（不修，仅记录）：本库另有未被 demo 模块登记的历史账号
（`demo_full`、`sc_fx_*` ×7、`svc_project_ro`、`codex_p4_person_batch2a_auth_20260913`），
不在 `local.dev.demo_users.sync` 覆盖范围内，故不是固定口令；属早期 P4/prod-like 运行遗留。
在 57 个 active 账号中 47 个按 `scdevpass` 登录成功，10 个失败即上述名单。
是否清理或纳入固定口令需所有者裁定（涉及凭据覆盖面，属独立授权）。

## 收口期补充：集合能力权限投影事实核对（owner 裁定 1，并入本轮）

### 结论先行

**native 通道没有缺 `permissions.effective.rights`，不需要修代码、更不允许加模型配置。**
先前"native 通道返回 `permissions: null`"的读数是用错入口造成的探测假象：那次探测用的
`action_id=506` 在 `ir_act_window` 中根本不存在（`count(*)=0`），返回的是"配置问题"降级页
（`head.model=null`、`permissions=null`），并不是某个 surface 的投影缺陷。

### 事实一：同一模型、同一角色，两条入口的权限事实逐位相同

受管 `sc-local-dev`（`sc_dev_demo`），`ui.contract` 实测：

| 角色 | 模型 | `head.permissions`（ACL 事实） | `surface_policies.collection_capabilities.actions` |
|-|-|-|-|
| `wutao` | project.project（model 入口 + 12 个 native list action 入口） | read/write/create/unlink 全 true | export/archive/activate/delete/**import** |
| `wutao` | payment.request（model 入口 + action 809） | 同上 | 同上 |
| `demo_finance` | project.project（model + 12 action） | 仅 read | 仅 export（无 create → 无 import、无 delete） |
| `demo_pm` | project.project / payment.request | 仅 read | 仅 export |
| `demo_readonly` | project.project（model + 12 action） | 仅 read | 仅 export |
| `demo_readonly` | payment.request | 无页面权限（降级页 `head.model=null`） | 空 |

即：**能力差异只来自角色/权限事实，不来自入口**。这既是 owner 提出的"同一模型不同 surface
不得产生能力差异"的实测证明，也说明 `build_collection_capabilities()` 不需要按模型分支。

### 事实二：全库普查零违例（本轮最强证据）

对 `sc_dev_demo` 中所有带 tree 的 `ir_act_window`，以 `wutao` 逐动作探测 `ui.contract`：

- `probed=292`、`skipped=53`、`violations=0`；
- 规则：`rights.create is True` ⟺ 声明 `import`（双向），292 个全部满足；
- 53 个 skip 全部确认为 `403 PERMISSION_DENIED`（`hr.employee`、`ir.model.access`、
  `sc.workflow.def` 等返回"用户无权以 read 访问模型"），不是投影缺口。

### 事实三：入口两轴不是冗余，第三轴与它们正交

`params{model}` 与 `params{action_id}` 是同一条契约生成链的两个**入口事实**，不是两套实现：

| 观察项 | `action_id=345` | 仅 `model` |
|-|-|-|
| `head.action_id` | 345 | null |
| 视图溯源 | `action:345:project.project:tree:view:2076` | `view:2076:project.project:tree` |
| `head.view_type` | kanban（action 自带 view_mode 为准） | list（调用方请求） |
| `head.permissions` / `collection_capabilities` | 完全一致 | 完全一致 |

`loadModelContractV2()` 是真实产品路径（`useRecordRelationships`、`useRecordRelationshipNavigation`、
`useRecordPageLifecycle` 用于关系下钻与记录页），不是测试专用入口；`loadActionContractV2()` 用于
菜单/动作进入并携带 action 的 domain/context/target。第三条轴 `contract_surface ∈ {user,native,hud}`
与入口轴正交：`contract_surface=native` 被交付策略 `410 UI_CONTRACT_NATIVE_BLOCKED` 阻断（应走
scene 路由），实测确认。因此三者都不多余，且**权限/能力轴在任一路径上必须一致**——已实测一致。

### 本轮的代码增量：只做 fail-closed 收紧，不加配置

同一模块对 `available` 用严格 `is True`，对 `create` 却用宽松 `bool()`——真值字符串/数字
（如 `"yes"`）会放行一条 ACL 从未授予的能力。按"未声明即不授权"收紧为 `resolved_rights.get("create") is True`，
影响面仅限"非布尔 rights"（现有生产方 `permissions.effective.rights` 只发布尔），无模型特判、无配置项。

新增离线守卫 `verify.contract.collection_capability_projection.unit`
（`scripts/verify/collection_capability_rights_projection_test.py`，cases=35）：锁定
`import` 声明 ⟺ `create` 为真 的双向规则、缺失/非布尔 rights 的不授权语义、`available` 的声明语义、
`batch_policy` 是同一份声明的 selection 投影（空声明得空投影，不退化为第二套推导），
以及"该规则不存在 model/surface/action 入参，故按模型特判在结构上不可表达"。

### 验证体系接线（消除新增零引用目标）

本批新增的守卫目标一度让 `verify.verification.lane_coverage` 报"surface grew"
（`targets_zero_reference 766 > 760`、`6` 个未登记），即新增守卫没有被任何车道真正执行。
按仓库既有边界约定接线，**未改写冻结基线**：

- 前端 unit（需 node_modules）→ `verify.frontend.pr.unit` / `verify.frontend.release.unit`：
  `verify.frontend.record_delete_action.unit`、`verify.frontend.collection_action_capability.unit`、
  `verify.semantic_runtime_resolution`；
- 纯 python 守卫 → `verify.contract.architecture.suite`：`verify.layout.vocabulary.lint`、
  `verify.contract.collection_capability_projection.unit`；
- 人工生成入口 `contract.semantic.registry.generate` → `ci.delivery.freeze.prepare`
  （冻结前重建派生载体，与"冻结前生成物必须新鲜"同一语义）。

结果：`targets_zero_reference` 回到 760、未登记 0；`make audit.verification.lane_coverage.check`
`PASS surface within the frozen baseline`，`make verify.guard.registry` AUDIT PASS（1419 scripts）。

## 环境身份卫生：非受管账号清单（登记 `ENV-IDENTITY-CLEANUP`，P2，本轮不处理）

`sc_dev_demo` 中 60 个账号：active 57，其中 48 个由模块通过 `ir_model_data` 登记（受
`local.dev.demo_users.sync` 的固定口令覆盖），**9 个未被任何模块登记**；另一 1 个
`codex_p4_person_batch2a_auth_20260913` 由 `codex_p4_personnel_authorization` 模块登记但不在
demo 模块口令同步范围内。这 10 个正好是 57 中按 `scdevpass` 登录失败的 10 个。

| 账号 | id | 建立时间 | 观察到的权限 | 判断 | 处理建议 |
|-|-|-|-|-|-|
| `demo_full` | 52 | 2026-09-07 | 51 组，含「SC 能力 - 业务配置管理员」「会计/账单开具管理员」 | demo 全集账号，权限偏高 | 保留或收紧至高权限组之外 |
| `sc_fx_pm`/`executive`/`finance`/`contract_admin`/`project_member`/`material_user`/`cost_user` | 3400-3406 | 2026-10-08 | 13–34 组，按角色发放（含「合同管理员」「物资员」「成本员」等） | 某次 P4 验收的角色化夹具账号 | 保留为夹具或整体退役，二选一 |
| `svc_project_ro` | 3407 | 2026-10-08 | 6 组，含「项目 / 用户」 | 名为只读、实为可写项目组 | **权限收紧候选**（名实不符） |
| `codex_p4_person_batch2a_auth_20260913` | 445 | 2026-09-13 | 含「技术 / Smart Core Data Operator」 | P4 授权测试遗留，且持有导入/导出算子组（正是 `api.data.import` 所需组） | 退役候选 |

处理边界：**不直接批量改密码**（会扩大凭据覆盖面，需独立授权）；账号是否仍需要由用途决定，
上表"用途"依据名称/建组/建立时间推断，需 owner 确认后再处置。本批不含任何账号写入。

## Owner 裁定：保持双入口，补不变量守卫（本批次最后一个增量）

### 裁定

`loadActionContractV2()` 与 `loadModelContractV2()` 是**两个入口适配器，共享同一个 Contract Runtime**，
不合并、不删除 model 入口、不改 scene route。新增 `contract_v2_entry_equivalence_guard`，
只比较 `head.permissions` 与 `surface_policies.collection_capabilities`，
**不比较** layout / action binding / navigation / domain（这些本来就允许不同）。

### 本轮新守卫锁定的不变量（结构 + 行为）

结构不变量（静态，任何一处漂移即失败）：

| 不变量 | 断言内容 |
|-|-|
| 单一取数 | 前端 `intentRequestRaw<` 全仓恰 1 处 |
| 单一解码 | `decodeContractV2Snapshot(` 全仓恰 1 处；两个 loader 都必须经 `loadContractV2(` |
| 单一分发 | `_dispatch_native_form_source` 仅 1 处定义、模块内仅 1 个 `ActionDispatcher`、函数体内仅 1 次 `.dispatch(` |
| 入口映射固定 | subject 取值恰为 `["action","model"]`；调用点仅 1 处 |
| 权限解析与入口无关 | `_ui_contract_permission_rights(source, ui)` / `resolve_permission_rights(permission_contract)` 签名不含入口身份；`_forbidden_hits` 扫描 `op/subject/action_id/menu_id/entry/surface/view_id/client_type` |
| 能力规则与入口无关 | `build_collection_capabilities` 形参恰为 `["selection_actions","rights","fields_map","has_list_view"]` |

行为不变量（`_check_carrier_independence`）：同一份 rights 从 4 种载体
（`effective.rights` / `effective` / `rights` / 裸 map）解析结果一致；非布尔 `create` 不提升能力；纯函数可复现。

负例自检 `scripts/verify/test_contract_v2_entry_equivalence_guard.py`：10 个负例，先基线绿再注入，
覆盖第二 decode、loader 私有 fetch、丢失 model 映射、第二 dispatcher、权限解析器加 entry 参数、
解析器读 `op`/`entry_kind`、能力规则加 `model` 参数、载体依赖解析、非布尔提升。

接线：`make/dev_test.mk` 定义 `verify.contract.entry_equivalence.guard`
（`py_compile` + 负例自检 + 守卫），并挂入 `verify.contract.architecture.suite` 前置链，
因此 `ci.local.quick` 会强制执行。

### 为什么保留双入口

| 入口 | 携带的入口事实 |
|-|-|
| action | `action_id` / domain / context / target / menu / view_mode |
| model | 模型身份、关系下钻、无 action 场景 |

合成一个 `loadContract(model|action)` 会丢失入口语义，并迫使前端用 `if(actionEntry)` 补业务分支——
正是本轮要禁止的"前端成为业务解释补偿层"。正确形态是**入口不同、业务事实同一、表达不同**。

### 产品导航纪律（冻结，不新增实现）

- 产品页面：`scene → action/menu → contract`（必须带 action/menu/context/policy）。
- 资源下钻：`record → relation → model → contract`（允许）。
- 禁止：`用户菜单 → model → 页面`（绕过 action/menu/context/policy）。

### 同层修复（本轮一并收口，非新能力）

1. **schema 声明漂移**：`addons/smart_core/core/contract_lifecycle.py` 的 `UNIFIED_PAGE_SCHEMA_SHA256`
   仍是 `0beb7bba` 改 schema 之前的旧值。由唯一派生入口
   `python3 scripts/verify/contract_schema_declaration_sync.py` 重算为
   `cdec8497fe9bbda2c035783026c77b84b77a5499f75b19543137535d5b7d8ece`。
2. **4 个 canonical example 的 body seal 从 `5a227641` 起就陈旧（既有潜伏缺陷）**：
   把 seal 派生并入同一条派生路径——`contract_schema_declaration_sync.py` 新增
   `load_lifecycle_authority()` / `example_integrity_span()` / `derived_example_integrity()` /
   `example_integrity_drift()` / `render_example_integrity()`；`--check` 同时检测 `exampleIntegrity`，
   默认模式重绑定 seal（复用 `contract_lifecycle.payload_sha256` + `contract_semantic_payload`，不重实现）。
   `form_project.json` / `list_project.json` / `nested_form_relation.json` / `tree_project.json`
   各 2 行变更。`test_contract_schema_declaration_sync.py` 增 3 例（seal 自洽、陈旧 seal 检出并重绑、
   seal 基于语义载荷而非文件字节），现 11 例。
   修复后 `make verify.backend.contract_lifecycle.authority` exit=0、`errors: []`。
3. **`verify.contract_form_split_evidence` 陈旧**：`ContractFormPage.vue` 现 2011 行，
   经 `make refresh.contract_form_split_evidence` 由生成器刷新
   `docs/engineering_convergence/p4_p0_03_contract_form_split_evidence.md`。
4. **`construction_core_extension_contract_normalizers_split_guard` ModuleNotFoundError**：
   `0beb7bba` 引入的 `odoo.addons.smart_core.core.contract_runtime` 包在纯 python 守卫里不可见。
   已加 `_register_odoo_package_paths()`（设置 `odoo.addons` / `odoo.addons.smart_core` /
   `odoo.addons.smart_core.core` 的 `__path__`），守卫转 PASS。

### 本轮实际执行与回执（10 个新 receipt，全部 reusable）

| check_id | target | tests | 结果 |
|-|-|-|-|
| contract_v2_entry_equivalence | verify.contract.entry_equivalence.guard | 10 | passed |
| schema_declaration_sync | verify.contract.schema.declaration.sync | 11 | passed |
| agent_ledger | verify.agent.ledger.unit | 15 | passed |
| layout_vocabulary | verify.layout.vocabulary.lint | 11 | passed |
| collection_capability_projection | verify.contract.collection_capability_projection.unit | 35 | passed |
| verification_lane_coverage | verify.verification.lane_coverage | 44 | passed |
| environment_topology | verify.environment.topology.guard | 7 | passed |
| collection_action_capability | verify.frontend.collection_action_capability.unit | 15 | passed |
| frontend_typecheck | verify.frontend.typecheck.strict | 1 | passed |
| frontend_lint_src | verify.frontend.lint.src | 1 | passed（0 error / 64 warning） |

同时 `make verify.contract.architecture.suite` 全绿（`exit=0`，
`[OK] contract & architecture guard suite passed`，其中含 `[OK] Node syntax check passed (384 files)`）。

**索引说明**：run 中其余 23 个 receipt 因本批次改动落在其声明输入目录内而转为 `stale`，
按仓库规则应"由最早失效层重跑"；本批次的权威本地门禁是提交后**干净冻结头上的一次**
`make ci.local.quick`，它覆盖这些层。本地 receipt 是开发观察，不是交付门禁，故不再逐个重跑。

### 本批次明确不做

合并 `loadActionContractV2` / `loadModelContractV2`；删除 model 入口；改 scene route；重做 navigation；
`extractListProfile` 全面拆分；Action Runtime 全量治理；01-E（`span → deliverySpan`）。

## 冻结前 Quick 暴露的同层缺陷：assembled contract 缓存指纹未重固定

`make ci.local.quick`（干净头 `aea17141`）在 shard 2 的 `verify.unified_page_contract.v2`
处以 `verify.unified_page_contract.v2.assembler` 失败收尾：

```
the assembled contract cache inputs changed without re-pinning: set
ASSEMBLED_CACHE_INPUTS_SHA256 = '84f62b18...' and bump ASSEMBLED_CONTRACT_CACHE_VERSION
```

### 根因

`0beb7bba`（结构词汇双维收口）修改了 `handlers/ui_contract_v2.py`、`core/unified_page_contract_v2_assembler.py`、
`handlers/ui_contract_v2_projection.py` —— 三者都在 `ASSEMBLED_CACHE_INPUTS` 内 —— 但没有重新固定
`ASSEMBLED_CACHE_INPUTS_SHA256`，也没有 bump handler 的 `ASSEMBLED_CONTRACT_CACHE_VERSION`。
`verify.contract.architecture.suite` 不含该目标，所以 19:48 的 suite 全绿并不能说明它通过；
本批次此前把该 check 的 receipt 判为 stale 却没有追下去，是这一轮真正的漏检点。
守卫在 Quick 里如实 fail-closed，说明机制本身有效。

### 修复（所属层，不扩范围）

1. `ASSEMBLED_CONTRACT_CACHE_VERSION` → `ui-contract-v2-2026-10-12-collection-capability-declaration`
   （handler 与守卫同步改；版本字面量必须变，否则旧装配会继续被当作新契约服务）。
2. 补齐指纹遗漏的运行时生产链——它们直接产出 assembled contract 的权限与集合能力：
   `core/unified_page_contract_v2_permissions.py`（assembler 直接 import）、
   `utils/collection_action_capability.py`、`utils/contract_governance.py`、
   `utils/contract_governance_list_surface.py`、`utils/contract_governance_user_surface.py`。
   本批次正好改了后三者，缺一个都会让"能力声明改动"被缓存吞掉。
3. 由唯一算法重算 `ASSEMBLED_CACHE_INPUTS_SHA256`
   = `a6fc054688afccc79995b68a3b863dfccb4fbd9829ed44c0b4ccb3635c5e4bc8`（不手算、不猜）。
4. `make verify.unified_page_contract.v2.assembler` PASS（sources=4）。

### 同轮补跑（避免用下一次 Quick 去逐个发现兄弟失败）

shard 2 在失败点之后未执行的目标，本地 `make -k` 一次补齐并全部通过：
`verify.boq.dangerous.import.capability`、`verify.frontend.dev.incremental.unit`、
`verify.frontend.overview_rich_text.unit`、`verify.frontend.lint.src`。

### 顺便回答"Quick 为什么这么久"

本次 Quick 的实测分布（`.runtime/quick-shard-aea17141c86a-*.log`）：

| shard | 状态 | 耗时 |
|-|-|-|
| 0 | passed | 353.6s |
| 1 | passed | 15.4s |
| 2 | failed | 10.0s |
| 3 | passed | 7.1s |

墙钟 ≈ 354s，其中 shard 0 独占 99.7%。shard 0 里包含 `verify.contract.architecture.suite`
以及 `trusted_scan_group` 的三次全量安全扫描（`security.secrets.scan` 140.3s、
`security.personal_data_scan` 172.0s、`repository.clean_history.scan` 280.7s，
三者在组内并行，组墙钟 ≈ 281s），并都判为 `mode=full reason=scan_authority_changed`。

结论：慢不在断言数量，而在 (1) 分片是 `manifest[index::4]` 的跨步切片，重活恰好落在同一片；
(2) 三个全量扫描每次都从头扫。这两点都属于本仓库迭代效率范围，登记为独立改进项，
不在本批次改动（本批次只做契约收口）。

## 第二次冻结头 Quick 暴露的三个同层缺陷（web 消费面）

`make ci.local.quick`（干净头 `7f7a2125`）在 shard 2 再次失败。实测分布：
shard 0 = 353.5s、shard 1 = 16.5s、shard 2 = 38.6s（fail）、shard 3 = 7.2s。

`make -k verify.unified_page_contract.v2` 一次枚举出 3 个**互相独立**的失败，按"同层集中修复、
不逐个用下一次 Quick 去发现"的原则一并处理：

| 目标 | 直接现象 | 真正根因 |
|-|-|-|
| `...v2.web_consumer` | `contractActionRuntime.ts` 缺 `resolveContractV2GlobalStatus` / `pageAuth === 'none'` / `UNIFIED_PAGE_CONTRACT_V2_PAGE_FORBIDDEN` | `0beb7bba` 把访问裁决收敛到 `contracts/v2/store.ts`，但**表单页仍在自行重导裁决谓词**，守卫也仍断言旧 token |
| `...v2.web_architecture` | `product_page_direct_data_imports`：`ContractFormPage.vue` 直接 import `../api/data`（count=1 > 0） | `f0dd95e3` 引入的记录删除 `unlinkRecord` 绕过了受管 runtime 模块 |
| `...v2.stable_projection` | `frontend_v2_policy_projection_guard.py:915`：`useActionViewContractShapeRuntime.ts` 含 `list_profile` 却未调用 `resolveUnifiedPageContractV2ListProfile` | 守卫用整文件子串判断"是否直读契约"，把 `ContractGapError` 里的**声明路径文案**误判为契约直读 |

### 1. 页面级访问裁决的唯一化只做了一半

`0beb7bba` 的提交信息声称"`resolveContractV2PageAccessVerdict` 由 store 单一裁决，action runtime
与表单消费同一 selector"。事实核查：action runtime 确实只消费 selector，但 `ContractFormPage.vue`
的 `rights` computed 自己重写了同一个谓词
（`globalStatus?.pageVisible === false || pageAuth === 'none'`）——这正是入口双通道架构要防的
"同一业务事实两个判断点"，也是本次失败被守卫如实暴露的原因。

修复（收口事实，不放宽断言）：

- `ContractFormPage.vue` 的 `rights` 改为消费 `resolveContractV2PageAccessVerdict(v2ContractStore.value).blocked`，
  页面不再自行裁决；`resolveContractV2GlobalStatus` 仍保留给 `renderProfile`（职责不同，不是重复裁决）。
- `unified_page_contract_v2_web_consumer_guard.py`：访问裁决 token 断言迁到真正拥有者 `app/contracts/v2/store.ts`，
  并新增"表单页必须消费 selector""表单页不得再出现 `pageAuth === 'none'`"两条断言。
- `web_unified_page_contract_v2_guard.py`：`contract_runtime_source` 断言 `resolveContractV2PageAccessVerdict`；
  store 断言拥有规则（`resolveContractV2GlobalStatus` / `UNIFIED_PAGE_CONTRACT_V2_PAGE_FORBIDDEN` /
  `pageAuth === 'none'`）；表单页断言同上。**断言数量只增不减**，杜绝"换个文件就算通过"。

### 2. 契约表单页仍在直连底层数据 API

`unlinkRecord` 直接从 `../api/data` 引入，绕开了本批次建立的受管 runtime 边界。
修复：`app/runtime/contractFormDataRuntime.ts` 增加 `unlinkContractFormRecord` 重导出（与
`createContractFormRecord` / `writeContractFormRecord` 同构），页面改经该模块调用；`../api/data`
直连计数归零，`web_architecture` 的 `product_page_direct_data_imports` 断言（max_count=0）保持原值。

### 3. 守卫把"声明路径文案"当成了"契约直读"

`useActionViewContractShapeRuntime.ts` 的两处 `list_profile` 都在 `ContractGapError` 的 `missing`
载荷里（用于告诉运维是哪个声明缺失），文件本身通过冻结的归一化 store accessor
`resolveContractV2ListProfile(store)` 消费同一个解码载体，**并不存在直读**。

这里必须区分两件事，且不做前者：

- ❌ 不把守卫断言放宽成"出现词就算过"。
- ✅ 把检测口径改精确：新增 `DECLARATION_RESOLVERS`，按声明键列出可用解析器
  （原始契约 helper 或冻结的归一化 store accessor，两者都是声明消费、都不是本地兜底），
  命中任一即通过；直读仍由 `FORBIDDEN_DIRECT_READS` 单独 fail-closed。

结论是"没提到声明就必须走声明解析器"这条约束强度不变，只是不再把错误文案当作契约读取。
否则下一个同类失败还会再花一次 Quick（约 7 分钟）。

### 本轮验证（受管、离线层）

| check | 结果 |
|-|-|
| `verify.unified_page_contract.v2.web_consumer` | PASS（11 tests） |
| `verify.unified_page_contract.v2.web_architecture` | PASS（debt_lock findings=0） |
| `verify.unified_page_contract.v2.stable_projection` | PASS（6 tests） |
| `verify.contract.architecture.suite` | PASS（exit=0，含 384 文件 Node 语法检查） |
| `verify.frontend.typecheck.strict` | PASS（0 error） |
| `verify.frontend.lint.src` | PASS（0 error，64 warning） |
| `verify.frontend.style_system.guard` | PASS |
| `verify.form_structure_authority_unification.unit` | PASS（215 tests） |
| `verify.frontend.page_pattern_reference_parity.unit` | PASS（28 tests） |
| `test_frontend_v2_policy_projection_guard` | PASS（6 tests） |

生成的 `contract_form_split_evidence` 因 `ContractFormPage.vue` 行数变化而过期，
由受管生成器 `make refresh.contract_form_split_evidence` 重写（lines=2013），未手改生成物。

### 台账覆盖缺口（本轮一并补上）

`scripts/verify/frontend_v2_policy_projection_guard.py`、
`unified_page_contract_v2_web_consumer_guard.py`、`web_unified_page_contract_v2_guard.py`
三个守卫原本**不在任何已登记 check 的 `inputs` 内**——即改动它们不会让任何回执失效，
这是"证据体系无法快速定位职责"的具体形态。现按守卫实际归属登记 3 个 check
（`unified_page_contract_web_consumer` / `..._web_architecture` / `..._stable_projection`），
并按变更影响重录失效回执，不用下一次 Quick 去逐个发现兄弟失败。

## 第三次冻结头 Quick 的收口：契约目录派生链（`contract_catalog`）

`make ci.local.quick`（干净头 `69f707373f12`）在 `verify.branch.governance.consistency`
一次瞬时失败（宿主层 spawn EFAULT，见下节），修掉后唯一残留失败是：

```
[FAILED] contract_catalog  target=verify.contract.catalog  rc=2  tests=16
❌ inferred intent examples detected: api.data.import
```

根因不是守卫缺陷，而是本批次新增的 intent `api.data.import`
（`addons/smart_core/handlers/api_data_import.py`）在 `docs/contract/cases.yml` 里没有
`intent.invoke` 用例：`export_catalogs.py` 对无用例的 intent 会写入
`example="__inferred__" / inferred=true / source="handler_params_scan"`，
`intent_catalog_inferred_guard.py` 据此 fail-closed。**不放宽该守卫**，按既有模式补事实：

| 动作 | 产物 |
|-|-|
| `docs/contract/cases.yml` 增 `api_data_import_intent_pm`（`demo_role_pm` / `dry_run: true` / `compare_mode: shape`） | 用例覆盖 |
| `make local.contract-snapshot.contract_export CONTRACT_CASE_ONLY=api_data_import_intent_pm` | `docs/contract/snapshots/api_data_import_intent_pm.json` |
| `make verify.contract.catalog` | 五项守卫全 PASS（tests=16） |

### 补齐用例时暴露的真实后端缺陷（同层修复，未放宽断言）

首轮快照生成本身就失败了，报 `BUSINESS_RULE_FAILED: list index out of range`，
不是用例写法问题，而是 handler 与 Odoo 导入内核的边界不一致：

- `base_import.import.file` 的官方声明是
  `fields.Binary('File', help="File to check and/or import, raw binary (not base64)", attachment=False)`，
  且 `_read_csv()` 直接 `csv_data = self.file or b''`，把缓存字节当文件内容解析；
  实测 `create({"file": <base64 str>})` 后 `rec.file == b'bmFtZQo...'`，
  CSV 被当成"一行一列"，`preview.pop(0)` 之后 `preview[0]` 即 `IndexError: list index out of range`。
- 而 `api_data_import.py` 先把传输层 base64 解码成 `content`，又
  `base64.b64encode(content).decode("ascii")` 塞回内核，等于**多编了一层**。

修复（一行语义 + 说明注释）：内核 `create` 直接传 `content`（原始字节）。
传输层用 base64、内核用 raw binary，这不是双通道，而是"JSON 载体"与"内核契约"的分工；
`_read_file_payload` 的 base64 解码保持原样。

修复后同一快照：`{"valid": true, "file_length": 2, "headers": ["name"], "mapping": ["name"], "imported_count": 1, "error_count": 0}`。

### 台账 inputs 补齐与连带失效（不放宽、不重扫全量）

`contract_catalog` 的目录由 handler 扫描派生，但登记的 `inputs` 只有
`docs/contract/*` 与守卫脚本，**漏了派生源**——即改了 handler 也不会让该回执失效，
属于"证据体系无法快速定位职责"的同类缺口。按派生关系补登
`addons/smart_core/handlers`、`addons/smart_construction_core/handlers`。

补登后按"改动输入必须重取回执"重跑，只跑被本次改动真正失效的兄弟项：

| check | 失效原因 | 复跑结果 |
|-|-|-|
| `contract_catalog` | inputs 变更 | PASS（tests=16） |
| `page_contract_v1_zero_residue` | inputs 含 `docs/contract/snapshots`（新增快照） | PASS |
| `collection_action_capability` | inputs 含 `api_data_import.py` | PASS（cases=15） |
| `agent_ledger` | inputs 含 `.agent/runs`（run.json 更新） | PASS（tests=15） |

38 个 check 全部 `reusable`，run `resolved`，`outside_scope=[]`。

## 本地资源利用收口（owner："本地电脑资源还没有充分利用"）

先量化再改，避免凭感觉调参。实测（`.runtime/quick-*.log`）：

| 事实 | 数值 |
|-|-|
| 本机 | 18 核 / 15 GiB / 无 seccomp / CapEff=0 |
| quick 分片 worker 上限 | `min(cpu//2, mem//3GiB, members)` = **3**（内存是硬约束，不是核数） |
| 4 分片实测（两处冻结头） | 353.6/15.4/10.0/7.1s（`aea17141` 段）与 328/16/105/8s，墙钟 328—354s |
| 8 分片实测 | 72.0 / 7.7 / 9.1 / 6.0 / 338.5 / 8.0 / 111.6 / 1.3s，worker 链 347.5s |
| 扫描组自报 | `members=3 jobs=3`：secrets 169.5s、personal 200.4s、history 315.5s → 组墙钟 = 315.5s |
| 关键路径 | 单条不可再分的 `repository.clean_history.scan`（315.5s），不是分片、也不是核数 |

**结论（更正 `3bc39ee6` 的结论）**：分片数不是有效杠杆。4 分片与 8 分片重切的是同一份覆盖集合，
墙钟 328s vs 347.5s 属噪声级差异，两者都被同一条不可再分的地板压住——`repository.clean_history.scan`
单条 315.5s（`HEAD --branches --tags --remotes` 全历史，组内已 3 路并行，无法再切）。

**真正的杠杆是"该候选能否复用已验证的祖先扫描回执"**，实测：在 HEAD `02b6fe28` 上运行
`python3 scripts/ci/trusted_scan_scope.py`，三个 kind 全部
`mode=incremental base=02b6fe28e40972e3f6dbf70bb24e143517307bbe`、
`reason=verified_ancestor_coverage_unchanged_authority`、`changed_worktree_paths=0`。
上一次 Quick 之所以付全量，根因是**该候选自身改了 `scripts/ops/local_quick_evidence.py`**——
它属于 `scripts/ci/trusted_scan_scope.py:COMMON_AUTHORITY`，于是没有任何祖先回执携带新的权威摘要，
`select_scope` 落到 `scan_authority_changed`，三个扫描全部重跑，地板从数十秒抬到约 315s（墙钟 ≈347s）。

处置：

- `DEFAULT_SHARDS` / `QUICK_SHARDS` 保留 8，但理由更正为**恢复粒度**（中断后只补未完成分片），
  不再声称它能削关键路径；覆盖集合与断言一字未改，单测继续锁定两处默认值不得漂移。
- `spawn()` 只对**未启动子进程**的瞬态 errno（`EAGAIN`/`ENOMEM`/`EFAULT`）重试 3 次并打印
  `RETRY` 行；其它 errno 与非瞬态错误立即 fail-closed，覆盖 `git()` 与 `_shard_popen()`。
  这是 `69f70737` 那次 `OSError: [Errno 14] Bad address: 'git'` 的宿主层瞬态失败，
  单跑与 6 路并发 + 3GiB 压力均未复现，因此按"瞬态、且禁止掩盖真实失败"的边界处理。
- `docs/ops/codex_workspace_execution_rules.md` 的 `## 并行执行与本地资源利用` 按上述实测重写：
  唯一写入者、三类允许并行、禁止并行、回执与并行、判定顺序、瞬态 spawn 边界，
  并新增第 7 条"扫描权威改动单独开候选"（权威集合：`Makefile`、`scripts/ops/local_quick_evidence.py`、
  `scripts/ci/trusted_scan_scope.py`、`scripts/dev/local_dev_frontend_quick.py`、各 kind 的 `AUTHORITY`、
  能改写受管扫描目标声明的 `make/` 片段），避免下次再凭感觉判断"是不是没吃满机器"。
- 登记独立改进项（不在本批次动）：全量扫描自身的增量化或内部并行化——
  `repository.clean_history.scan` 单条 315.5s 是对全历史的扫描，缩减它要改扫描器覆盖语义，
  属独立专题；本次只更正结论与固化纪律，不动扫描范围。

## 证据过度失效修复（`__pycache__` 不是输入）

本轮跑定向检查时发现：5 个已 `reusable` 的 check 变成 `stale`，而它们的输入源码一字未改。
定位（对比 receipt 记录的状态与当前重算状态）：

```
changed: addons/smart_core/core/contract_runtime/__pycache__/semantic_registry_generated.cpython-312.pyc
changed: addons/smart_core/core/contract_runtime/__pycache__/domain_field_semantics_generated.cpython-312.pyc
only_old: []    only_new: []
```

根因：`agent_run_context.dependency_state()` 对声明为**目录**的输入递归 `rglob('*')`，于是
`__pycache__/*.pyc` 进入依赖状态；而 `.pyc` 头部内嵌源文件 mtime，受管生成器每次以**字节完全相同**
的内容重写到 `contract_runtime/*.py`（`freeze.prepare` 的生成步骤）都会让 `.pyc` 变字节，
把一个未变的结论判成 `stale`。这与 owner 反复提出的"已经跑通的结论不能复用"是同一类缺陷。

修复（不放宽任何断言）：

- `agent_run_context` 新增 `is_derived_bytecode()` / `comparable_inputs()`：派生字节码
  （`__pycache__` 与 `.pyc`/`.pyo`）不计入依赖状态，且**比较时两侧都归一化**，
  使修复前写入的旧 receipt 也能与当前状态可比。声明的 `.py` 源码仍按文件整体哈希，
  所以源码改动照样判 `stale`（新增单测锁定这一点）。
- 新增 3 条单测：`test_derived_bytecode_is_not_a_declared_input`、
  `test_legacy_receipt_carrying_bytecode_keys_stays_comparable`、
  `test_derived_bytecode_exemption_still_reports_a_source_change`；
  `make verify.agent.resume.unit` 43 tests PASS。
- 效果（实测）：本 run 中被误判的 6 个 check 在**不重跑任何检查**的前提下恢复 `reusable`，
  38/38 `reusable`、`outside_scope=[]`。
