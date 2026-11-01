# 310 · BNVA-02 Kernel Configuration Ownership Audit

| 决策 | 内容 | 状态 |
| --- | --- | --- |
| ARCH-DECISION-004 | 业务结构与布局拓扑两个非重叠权威 | confirmed |
| ARCH-DECISION-005 | 配置所有权与数据边界（三平面模型） | confirmed |
| ARCH-DECISION-006 | 产品默认业务结构属于产品发布资产 | confirmed |

## 运行时证据

- sc_clean 中 `product_release` 来源配置 140 条。
- 预置用户低代码配置 0 条。
- `lowcode_publication_gate_applies` 将产品默认配置排除在租户低代码门禁之外。

## 结论

产品默认配置与用户定制边界成立，发布门禁按来源选择适用性。
