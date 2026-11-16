# P4-01 Shadow Planner v1

## 状态

这是 P4-01 的第一个可执行纵向切片，只生成 shadow plan。

- 不接入 `ci.local.iteration` 裁决。
- 不接入 required CI。
- 不替换 path ownership 或 acceptance binding。
- `cutover_eligible` 固定为 `false`。

## 入口

```text
make verification.change-impact.plan \
  CHANGE_IMPACT_BASE=<stable-base-sha> \
  CHANGE_IMPACT_OUTPUT=.runtime/change-impact/plan.json
```

单元验证：

```text
make verify.change_impact.plan.unit
```

## 已实现

- TypeScript/Vue 通过 TypeScript Compiler API 提取声明、字段、import 和动态 import 线索。
- Python 通过 AST 提取类、Model 基类、字段、方法和 import。
- XML 通过结构化解析提取 record model、field 和 tag。
- ChangeFact 表达 path、change kind、semantic kinds、layers、confidence、basis 和 UNKNOWN。
- 每个 obligation 声明所需 assertion；检查选择按 assertion 覆盖和相对成本做集合覆盖。
- 没有检查覆盖 assertion 时输出 uncovered，并 BLOCK。
- dynamic dependency、类型解析失败、未知文件语义输出 UNKNOWN，并 BLOCK。
- 证据文件只有在 status、input fingerprint 和 assertion closure 同时匹配时才 REUSE。
- 计划输出 obligation sources，未再把整套 PR 路径错误关联到每个 obligation。

## 已实现检查目录

| check | 执行入口 | 证据类型 |
| --- | --- | --- |
| `contract.unified_v2` | `make verify.unified_page_contract.v2` | contract static |
| `frontend.contract_unit` | `make verify.frontend.pr.unit` | unit |
| `frontend.renderer_registry_unit` | `make verify.frontend.professional_component_registry.unit` | unit |
| `frontend.presentation_browser` | `make verify.frontend.presentation.browser` | browser |
| `backend.contract_suite` | `.github/workflows/backend_test_suite.yml` | ORM/contract runtime |
| `delivery.ci_workflow_contract` | `make verify.ci.workflow.contract` | unit |
| `delivery.change_impact_planner` | `make verify.change_impact.plan.unit` | unit |
| `delivery.docs_links` | `ENV=dev make verify.docs.links` | docs |

## 回放观察

### PR #905

近期 contract/action-view identity 候选：

- shadow status：`planned`
- obligations：L1 consumer、producer、schema + L4 delivery/docs
- selected checks：contract、frontend contract、CI workflow、docs
- 未选择 presentation browser
- UNKNOWN：0

该结果符合“后端/契约变化不自动进入浏览器”的目标，但仍是 shadow 结果，不是现有门禁结论。

### PR #886

近期 backend + frontend mixed 候选：

- shadow status：`blocked`
- 成功识别 L1 contract、L2 page presentation、L4 delivery/docs 并选择 browser
- 一个 frontend test 文件的 changed symbol 未被当前语义分类器解析，输出 UNKNOWN

因此计划正确 fail-closed，而不是猜测该测试文件不受影响。该 UNKNOWN 需要由 P4-02 的真实测试 assertion/consumer 图关闭。

## 当前未实现

- Producer → Decoder → Consumer 的完整编译器引用图。
- Renderer Registry → Component → Page 的全图反向追踪。
- ORM Model → Business Method → Workflow 的全图追踪。
- obligation-to-assertion-to-evidence 的持久图。
- 历史 PR 的自动批量 replay 与 False Negative/FER 统计。
- 稳定基线 proof record 的生成与推进。

这些缺口使 v1 仍不能 cutover。
