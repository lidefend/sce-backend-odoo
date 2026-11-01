# 180 · BNVA-02B-02A · 五页面 Shadow 报告

| 页面 | 合并诊断 | 结论 |
| --- | --- | --- |
| project.project 590/1776 | 无 ERROR | 完整 Formal 样板 |
| project.project 652/944 | 无配置（空） | 缺独立配置，需补齐 |
| payment.request 649/1773 | FORM_STRUCTURE_EMPTY | published 空占位 |
| sc.payment.execution 709/1658 | SECTION_KEY_MISSING + SECTION_FIELDS_EMPTY + IDENTITY_MISSING | 只有 title 无 fields |
| sc.receipt.income 708/1655 | SECTION_KEY_MISSING + SECTION_FIELDS_EMPTY + IDENTITY_MISSING | 退役配置，原生结构缺口 |

报告产物：`artifacts/backend/business_structure_integrity_shadow.json`。

## 说明

- `native_semantic_surface` 的 section 来自原生 Group，不按配置 sections 校验
  IDENTITY_NOT_IN_SECTION（校验器已按 `explicit_sections` 区分）。
- 配置存在或 published 不自动证明结构完整。

