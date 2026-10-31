# 60 · PC-011 Layout Integrity Design（containerTree）

## 目标

新增独立规则 PC-011：`containerTree` 布局一致性。它验证布局拓扑的完整性、引用
有效性、稳定性及其与业务组合（slots / fieldOwnership）的一致性，但不决定字段
业务归属。

## 核心原则

- containerTree 是布局拓扑权威，不是业务组合权威。
- containerTree 不得替代 slots；不得推断或分配字段业务归属。
- 仅凭 containerTree 存在，不得判定页面结构完整或 Formal 资格。
- 没有 slots ↔ containerTree 映射证据时，PC-011 输出 NOT_VERIFIED。
- 布局与业务结构冲突时输出 FAIL。

## 输入（证据 payload 扩展）

```text
page.layoutContract.containerTree   # 容器树，含稳定 node id
evidence.layout_consumption          # 哪一 Renderer 消费 containerTree 及证据等级
evidence.slot_container_mapping      # slot<->container 映射（可选，缺失即 NOT_VERIFIED）
```

每个容器节点至少携带：

```text
id（稳定身份）
type / role
parentId（或 children）
fieldRefs（可选；若携带则为布局投影引用）
businessRegionRef（可选；显式映射到 slot）
```

## 检查项

### A. 结构完整性

- 根节点存在且可解析。
- 每个节点 id 稳定；children / parentId 引用无悬空。
- 缺失或无法解析 → NOT_VERIFIED（不是 FAIL，布局缺失不必然是缺陷）。

### B. 容器引用有效性

- 每个 children/parentId 指向已声明节点。
- 悬空引用 → FAIL（已确认的结构缺陷）。

### C. 布局拓扑稳定性

- 节点身份基于稳定 id，不是位置序号。
- 无法证明稳定身份 → NOT_VERIFIED。

### D. 容器与业务区域映射

- 若 `slot_container_mapping` 存在：每个 business slot 与容器节点的映射一致、
  无遗漏、无冲突。
- 若映射证据缺失 → NOT_VERIFIED。
- 映射冲突 → FAIL。

### E. 不得决定字段业务归属

- 字段业务归属只来自 `fieldOwnership`。
- 若 containerTree 的 fieldRefs 暗示的归属与 fieldOwnership 冲突 → FAIL。
- 若 containerTree 是唯一归属依据（无 fieldOwnership）→ NOT_VERIFIED。

### F. 布局与业务结构冲突

- slots 与 containerTree 同时声明区域/字段成员且不一致 → FAIL。
- 只有一侧声明 → 对应映射维度 NOT_VERIFIED。

## 判定矩阵

| 条件 | 结果 |
| --- | --- |
| containerTree 有效 + 映射证据完整 + 与 ownership 一致 | PASS |
| 悬空引用 / 映射冲突 / 归属冲突 | FAIL |
| containerTree 缺失 / 映射证据缺失 / 仅源码级证据 | NOT_VERIFIED |
| 页面无布局契约且无 Renderer 消费布局（有据） | NOT_APPLICABLE |

任何“存在 containerTree”本身不产生 PASS。

## 五个样本的预期输出（设计推演，非本轮运行）

| 页面 | 预期 |
| --- | --- |
| project.project 590/1776 | containerTree 存在，映射缺失 → NOT_VERIFIED |
| project.project 652/944 | 同上 → NOT_VERIFIED |
| payment.request 649/1773 | containerTree 存在，slots=9，映射缺失 → NOT_VERIFIED |
| sc.payment.execution 709/1658 | containerTree 存在，slots=0，映射缺失 → NOT_VERIFIED |
| sc.receipt.income 708/1655 | 无 V2 Contract → NOT_VERIFIED |

## 测试矩阵（实现前必须通过独立测试）

1. containerTree 有效且映射一致 → PASS。
2. 悬空 children 引用 → FAIL。
3. 映射冲突 → FAIL。
4. 归属冲突（containerTree 暗示 vs fieldOwnership）→ FAIL。
5. 映射证据缺失 → NOT_VERIFIED。
6. containerTree 缺失 → NOT_VERIFIED。
7. 无布局契约且有消费证据 → NOT_APPLICABLE。
8. 仅凭 containerTree 存在不得 PASS。
9. slots=0 + containerTree 存在 → 不得借此判定 Formal（跨 PC-001）。
10. 辅助 role 集合以 Schema 为准，Guard 不得自行扩大。

## 与既有规则的边界

- PC-001 管业务组合权威（slots）；PC-011 管布局权威（containerTree）。二者不
  合并为一条规则。
- PC-005 管 slot 内重复投影；PC-011 管容器级布局一致性与跨层映射。
- 权限、版本、历史身份仍分别由 PC-008/009/010 负责，PC-011 不越界。
