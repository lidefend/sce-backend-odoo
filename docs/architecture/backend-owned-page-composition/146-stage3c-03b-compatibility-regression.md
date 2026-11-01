# 146 · BNVA-019 Stage 3C-03B · 兼容与回归

## 契约输出

| 页面 | 结果 |
| --- | --- |
| project.project 590 | native_form_slots，manager_id 在 mainData |
| payment.request 880 | container_tree，slots=0 |

## 无变化项

- containerTree 结构、容器身份、字段 occurrence、布局顺序不变。
- fieldOwnership 不受影响（本轮未改 ownership 规则与旧兜底）。
- 无新增原生 arch 获取或 XML 解析。

## 测试

- assembler guard PASS。
- 精确 HEAD Quick：待补。

