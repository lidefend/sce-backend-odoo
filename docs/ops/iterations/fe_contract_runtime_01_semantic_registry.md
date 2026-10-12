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

- **01-B** 后端统一消费 registry：`_component_key()` → semantic resolver
  （`contract_runtime/semantic_resolver.py`），保留 `componentKey` 兼容 +
  `deprecated_component_key_usage` 警告，证明 `payment.request` 渲染不变。
- **01-C** 前端 registry 接管：`semanticResolver` + 单测
  `verify.semantic_runtime_resolution`（money→CurrencyInput 等）。
- **01-D** `payment.request` 字段语义化 + presentation 契约收口（identity /
  presentation / behavior 必备）+ 浏览器验收。
- **01-E** 产出 `docs/contract-runtime-state-ownership.md`
  （业务状态=domain；UI 状态=runtime；按钮显示=behavior；权限=policy）。
