# 402 · BNVA-04 Kernel Boundary Regression

## 六项内核边界

| 维度 | 结果 |
| --- | --- |
| Canonical Native View Model | 两页结构权威均为原生 arch（native_semantic_surface） |
| Business Structure Adapter | 未重新声明 sections / identity_fields |
| Layout Adapter | 未声明 containerTree / slots |
| RequestScopedCarrier / V2 Assembler | assembler guard PASS（sources=4） |
| Integrity Guard | business_structure_integrity 21/21 OK；contract_structure_lock PASS（domains=14） |
| Renderer 自行推导业务结构 | 未发生（frontend_contract_basis_guard PASS，open_defects=0） |

## 未重新引入

- 字段名启发式：契约不含任何字段推断。
- 隐式 ownership 补齐：未声明 fieldOwnership。
- 原生 arch 复制：契约不含 sections/fields/columns 副本。
- 平行 Schema：未新增 Schema，无重复 XMLID。

## PC-001～PC-011

- 守护器单测 34/34 OK（`test_page_composition_integrity_guard` + `_rules`）。
- 这些规则面向声明 pageComposition（slots/containerTree/fieldOwnership）的契约；两个
  native_semantic_surface 页面不声明该结构，按设计不适用，而非失败。

## 本轮实际运行

- XML 良构：4/4 PASS。
- contract_structure_lock：PASS（domains=14）。
- business_structure_integrity：21/21 OK。
- PC-001～PC-011 守护器单测：34 OK。
- unified_page_contract_v2_assembler_guard：PASS（sources=4）。
- unified_page_contract_v2_runtime_guard：PASS（score=6）；v2 runtime 单测 23+135 OK。
- frontend_contract_basis_guard：PASS（bindings=15, exemptions=8, logic_sites=3, open_defects=0）。
