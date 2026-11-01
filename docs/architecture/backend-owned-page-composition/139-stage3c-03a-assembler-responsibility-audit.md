# 139 · BNVA-019 Stage 3C-03A · Assembler 职责审计

## 结论摘要

V2 Assembler 已不再重新读取 arch / 解析 XML（3A/3B/3C-02B 已收敛）。它消费
NCP 的 `formStructureContract` 与 LDP 的 `views.form.layout`，主要职责是
「契约规范化 + 最终组装」。

剩余值得治理的职责混杂：

1. 布局容器语义标准化（名称启发式）仍在 Assembler 内。
2. 旧启发式 fieldOwnership 兜底仍在 Assembler 内。

## 职责边界（目标）

| 层 | 唯一职责 |
| --- | --- |
| Native View Model | 原生结构事实 |
| Business Adapter | 业务结构投影（slots/ownership/identity） |
| Layout Adapter | 布局结构投影（containerTree/columns/widget） |
| ui_contract_v2 | 请求编排、数据来源协调 |
| page_assembler | 业务页面源数据组装 |
| V2 Assembler | 规范化契约组装 |
| Guard | 契约完整性验证 |

