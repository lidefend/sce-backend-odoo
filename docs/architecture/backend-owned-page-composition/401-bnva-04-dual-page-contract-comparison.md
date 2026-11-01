# 401 · BNVA-04 Dual Page Contract Comparison

## 共享机制

两页都使用 `composition_mode=native_semantic_surface`，以原生 arch 为结构权威，契约只携带
`title` 与 `view_orchestration.context`，不声明 identity_fields / sections / slots /
fieldGroups / fieldOwnership / pageComposition。

## 独立业务结构

| 维度 | sc.quality.issue | sc.tax.certificate.registration |
| --- | --- | --- |
| 契约名 | sc_quality_issue_handling_form_v1 | tax_certificate_registration_productized_form_v1 |
| 标题 | 质量问题办理 | 外经证登记 |
| workflow_authority | sc.quality.issue | 未声明（对齐 tax 兄弟口径） |
| Form 绑定方式 | 新增 act_window.view 绑定 | action 已显式绑定 tree+form+search |
| 字段结构 | 原生 arch | 原生 arch（04-06B 已去孤儿引用） |

## 结论

两页共享同一套契约机制与内核约束，业务身份和结构相互独立，不存在意外结构复用。
