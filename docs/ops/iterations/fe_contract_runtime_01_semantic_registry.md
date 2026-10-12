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

- ~~**01-B** 后端统一消费 registry~~（本批次完成，见上）。
- **01-C** 前端 registry 接管：`semanticResolver` + 单测
  `verify.semantic_runtime_resolution`（money→CurrencyInput 等）。
- **01-D** `payment.request` 字段语义化 + presentation 契约收口（identity /
  presentation / behavior 必备）+ 浏览器验收。
- **01-E** 产出 `docs/contract-runtime-state-ownership.md`
  （业务状态=domain；UI 状态=runtime；按钮显示=behavior；权限=policy）。
