# 验收体系与代码演进绑定 v1

本机制解决一个结构性问题：验收曾经是“改完代码后再补跑”的旁路，代码变更与
验收覆盖之间没有强制关系。现在每次变更都必须先经过验收影响解析，运行期变更
还必须在受管合并前提交与该提交完全一致的验收证据。

## 两层绑定

| 层 | 触发点 | 强制内容 |
| --- | --- | --- |
| 影响解析 | 每个 PR / 本地 quick / 架构守卫套件 | 每个变更路径必须在 `config/acceptance/evolution_binding.v1.json` 中被分类；未分类路径直接失败 |
| 证据绑定 | `make pr.merge` | 运行期变更所需的验收套件必须提供 `head_sha` 等于待合并提交的证据清单，且证据文件哈希、状态和计数复核通过 |

影响解析是确定性的静态门禁，远程 CI 与本地 exact-head lane 使用同一份注册表。
证据绑定发生在受管合并入口，避免用另一个提交的验收结果冒充当前提交。

## 注册表

`config/acceptance/evolution_binding.v1.json` 由三部分组成：

- `suites`：验收套件、执行入口，以及运行期套件的证据适配器。
- `rules`：有序的路径规则。第一个命中的规则决定该路径需要的套件。
- `policy`：未分类路径失败策略与证据有效期（默认 72 小时）。

当前运行期证据适配器：

| 套件 | 证据来源 | 关键断言 |
| --- | --- | --- |
| `daily_runtime_entry` | `scripts/ops/daily_runtime_entry_verify.py` 报告 | `status=PASS`、`expected_sha=head`、全部 checks 通过 |
| `path_namespace_identity` | `scripts/ops/path_ns_c_acceptance.py` 报告 | 23/23 通过、`provenance.expected_sha=head` |
| `list_surface_structure` | 列表结构浏览器报告 | `passed=true`、零 failures、零 runtime errors、入口指纹 = head |
| `relation_roundtrip` | 关系回环报告 | `status=pass`、零 failures、`expected_sha=head` |

`backend_contract`、`frontend_contract`、`governance_static` 由各自的受管套件
直接执行，不需要额外证据文件。

## 执行流程

```bash
# 1. 查看本次变更需要哪些验收（CI 与本地 quick 自动执行）
make acceptance.evolution.plan

# 2. 部署待验收提交后，运行对应套件并记录 exact-head 证据
make acceptance.evolution.record \
  ACCEPTANCE_EVOLUTION_SUITES="daily_runtime_entry=.runtime/final-acceptance/daily-runtime-entry-verify.json path_namespace_identity=.runtime/final-acceptance/path-ns-c-acceptance.json"

# 3. 受管合并入口自动复核证据（也可单独执行）
make acceptance.evolution.verify
```

`make pr.merge` 已依赖 `acceptance.evolution.verify`。若本次变更不需要运行期证据
（例如纯文档），该目标自动通过，不要求证据清单。

## 新增变更域

1. 在 `suites` 中登记套件与执行入口；运行期套件必须声明 `evidence.adapter`。
2. 在 `rules` 中按从具体到宽泛的顺序增加路径规则。
3. 在 `scripts/verify/acceptance_evolution_binding_guard.py` 中实现新的适配器，
   并在 `ADAPTERS` 注册。
4. 在 `scripts/verify/test_acceptance_evolution_binding_guard.py` 中补充正负例。
5. 运行 `make verify.acceptance.evolution.binding`。

未登记的新路径会让 CI 直接失败，而不是静默跳过验收。
