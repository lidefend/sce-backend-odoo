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
