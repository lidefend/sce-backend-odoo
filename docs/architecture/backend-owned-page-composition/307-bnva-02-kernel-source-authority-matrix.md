# 307 · BNVA-02 Kernel Source Authority Matrix

## 事实来源唯一性

| 事实 | 权威载体 | 状态 |
| --- | --- | --- |
| 原生视图结构 | Odoo `ir.ui.view` arch / `get_view` | VERIFIED_STATIC |
| 请求内解析缓存 | `native_view_parsed_cache.RequestScopedCarrier`（cursor+user+context 绑定，非模块级全局） | VERIFIED_STATIC |
| Canonical Native View 内部模型 | `native_view_projection.NativeView` | VERIFIED_STATIC |
| 原生字段归属/投影 | `native_view_projection.build_native_form_structure_contract` / `derive_native_field_ownership` | VERIFIED_STATIC |
| 契约来源分类 | `backend_contract_boundaries.view_orchestration_source_status` | VERIFIED（16 项测试） |

## 定向测试

- native_view_parser_surfaces：43 项 OK。
- contract_runtime_semantic_resolver：21 项 OK。
- view_orchestrator：62 项 OK（本轮修复了发布门禁接入后的过时测试命名空间）。

## 结论

原生事实路径收敛到 `RequestScopedCarrier → NativeView → Adapter`，未发现第二套原生事实来源。
