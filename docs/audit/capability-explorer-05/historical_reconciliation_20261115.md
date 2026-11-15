# CAPABILITY-EXPLORER-05 历史能力资产身份对账报告

状态：`PASS`

对账规模：历史 `282 / 75 / 207`，当前原生目录 `282 / 75 / 207`。

## 1. 权威边界

本报告中的“历史资产”是授权只读探针在 `sc_demo` 上生成的入口快照，
不是当前运行事实，也不是产品能力 Registry。

对账身份固定为复合键：

```text
(menu_xmlid, action_xmlid)
```

Menu 只取
`smart_construction_core.menu_sc_root` 下、有 action、无活动子节点的入口。
场景、发布和业务领域只消费现有场景绑定与发布快照，不从名称、模型前缀或中心推断。

当前事实来自 `main@f35d981b2a37d6268e31592edeef460c9580240c` 的只读
`sc_demo` 探针。

## 2. 快照来源与完整性

| 来源 | 身份 | 原始证据 | SHA256 |
|---|---|---|---|
| 历史发现 | `ODOO-NATIVE-CAPABILITY-EXPLORER-01`，候选 `6689f601b`，运行基线 `sc_demo@2571346af` | `.runtime/agent-runs/ODOO-NATIVE-CAPABILITY-EXPLORER-01/runtime-probe.log` | `65c2b6b19bea5dc1170e1b0213024c8839e079c71c9402dd9f8e2c68d5826a18` |
| 历史分类 | `ODOO-NATIVE-CAPABILITY-EXPLORER-02`，候选 `3639f35b1`，运行基线 `sc_demo@2571346af` | `.runtime/agent-runs/ODOO-NATIVE-CAPABILITY-EXPLORER-02/runtime-classification.log` | `646a98626a2f8ba423396d591cf12d8d179ddafc740a65a20517078af715efcd` |
| 当前原生事实 | `main@f35d981b2` | `.runtime/agent-runs/CAPABILITY-EXPLORER-05/current-native.log` | `8115a40110cc43049522e47779ea81aec3104879054fc22d7e65b074362bed52` |

原始日志中的历史与当前 JSON 均完整解析，均为 282 行；两代历史快照的复合身份集合完全相同。

## 3. 总结论

| 指标 | 历史 | 当前 | 结果 |
|---|---:|---:|---|
| 原生入口 | 282 | 282 | MATCH |
| 复合身份唯一数 | 282 | 282 | MATCH |
| Menu XMLID 唯一数 | 282 | 282 | MATCH |
| Action XMLID 唯一数 | 264 | 264 | MATCH |
| 场景绑定入口 | 75 | 75 | MATCH |
| 仅中心分类 | 207 | 207 | MATCH |
| 已发布 | 274 | 274 | MATCH |
| 发布未知 | 8 | 8 | MATCH |
| 技术阻断 | 0 | 0 | MATCH |
| 模块未安装 | 0 | 0 | MATCH |
| 模型缺失 | 0 | 0 | MATCH |

必需字段逐入口差异：

| 字段类别 | 差异行数 |
|---|---:|
| 身份、Menu/Action | 0 |
| 模块、模块版本、依赖 | 0 |
| 模型、字段、View、ACL、Record Rule | 0 |
| 场景绑定、场景状态 | 0 |
| 发布状态、发布中心 | 0 |
| 中心分类、业务领域分类 | 0 |

当前对历史：缺失 0、新增 0、映射不一致 0。

## 4. 差异分类

### 身份失效

0。历史 282 个复合身份全部可在当前原生目录解析；Menu、Action、模块和目标模型均存在。
所有入口均为 `draft_selectable=true`，`selection_blockers` 为空。

### 重复

复合身份重复为 0，Menu XMLID 重复为 0。

存在 16 个 Action XMLID 被多个 Menu 复用，共覆盖 34 个入口。这不是
“重复能力”，但证明 Action XMLID 不能单独作为稳定身份。完整冲突组位于
`historical_reconciliation_20261115.json` 的 `action_identity_reuse`。

示例：

- `action_project_budget` 被 3 个 Menu 复用。
- `action_project_dashboard` 被 3 个 Menu 复用。
- `action_construction_contract_income`、`action_project_cost_ledger`、
  `action_sc_general_contract` 等 14 个 Action 各被 2 个 Menu 复用。

另有 41 个 `(module, model)` 组被多个入口复用。该复用只说明多个入口可消费同一模型，
不能合并为同一业务能力。

### 缺失与新增

- 历史缺失于当前：0。
- 当前独有：0。

### 映射与状态差异

- 模块、模型、场景绑定、发布状态和分类差异：0。
- 历史 `released:bound=73`、`released:unbound=201`、
  `unknown:bound=2`、`unknown:unbound=6`，当前完全一致。

### 场景引用范围

场景表共有 78 条入口引用，其中 75 条指向 282 原生目录内的 Menu。另外 3 条是当前激活的
Odoo 会计原生菜单，位于业务根之外：

这 3 条及总数 78 已在同一授权 `sc_demo@f35d981b2` 上重新只读核验；
来源不是本地 `sc_dev_demo` 拼接。

| Menu XMLID | 名称 | 场景 | 分类 |
|---|---|---|---|
| `account.menu_action_move_journal_line_form` | 日记账分录 | `accounting.management` | OUTSIDE_282_CATALOG |
| `account.menu_action_account_moves_all` | 日记账项目 | `accounting.management` | OUTSIDE_282_CATALOG |
| `account.menu_action_account_form` | 会计科目表 | `accounting.management` | OUTSIDE_282_CATALOG |

这 3 条不是“缺失的 282 项”，也不应自动补入 282 目录。它们说明场景系统当前可以引用
业务根之外的原生菜单；后续产品化必须由后端明确场景引用范围，不能由 Explorer 推断。

## 5. 未决项

| 编号 | 状态 | 内容 |
|---|---|---|
| `CAP05-H01` | OPEN | 207 个入口只有原生中心，没有权威业务领域；仍为 `center_only`，不得自动命名或发布。 |
| `CAP05-H02` | OPEN | 8 个入口发布状态为 unknown；不得按已发布入口处理。 |
| `CAP05-H03` | OPEN | 16 个 Action XMLID 被多 Menu 复用；所有下游身份必须保留 Menu+Action 复合键。 |
| `CAP05-H04` | OPEN | 3 条场景引用位于 282 目录之外；是否允许、如何治理需产品决策。 |
| `CAP05-H05` | NOT_VERIFIED | 75 个有场景绑定不代表 Preview/Standard 资格；现有 evidence-backed 资格仍为 0。 |
| `CAP05-H06` | NOT_VERIFIED | 本对账只证明当前授权的 `sc_demo` 快照，不推广到其他租户。 |

## 6. 证据索引

| 证据 | 位置 / 摘要 |
|---|---|
| 282 行完整身份映射 | `identity_mapping_20261115.csv`，SHA256 `05c4d1b016fc9a09cbaa5bc0ae39a31d3b739f886f8a986b9ad9e57f2385f255` |
| 机器可读对账摘要 | `historical_reconciliation_20261115.json`，SHA256 `edc79fc1f9afec35f67ff8d6741489f39c2082ce1a96a5798f599a444b65dee5` |
| 历史发现原始日志 | `.runtime/agent-runs/ODOO-NATIVE-CAPABILITY-EXPLORER-01/runtime-probe.log` |
| 历史分类原始日志 | `.runtime/agent-runs/ODOO-NATIVE-CAPABILITY-EXPLORER-02/runtime-classification.log` |
| 当前原生原始日志 | `.runtime/agent-runs/CAPABILITY-EXPLORER-05/current-native.log` |
| 当前原生解析 JSON | `.runtime/agent-runs/CAPABILITY-EXPLORER-05/current-native.json` |
| 同库 `sc_demo` 场景范围回读 | `.runtime/agent-runs/CAPABILITY-EXPLORER-05/daily-scene-scope.log`，SHA256 `bc3ed7a1f1dd80846d03de616fd1ff9d298100e1aa1a56bd8d54cfd6c5d7bf8e` |

映射 CSV 只记录对账事实，不是运行时注册表，不允许被运行时写入或作为发布资格来源。

## 7. 结论

在授权历史快照范围内，282 个原生 Menu/Action 资产可以完整、可追溯地映射到当前
Odoo 原生事实，缺失、复合重复、无效和技术映射差异均为 0。历史 `75 / 207`
场景分类也应保持原样：75 个有权威场景绑定，207 个仅能确认原生中心，不能为了数字整齐
而补造业务领域、资格或发布记录。
