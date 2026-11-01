# 308 · BNVA-02 Kernel Component Responsibility Audit

| 组件 | 文件 | 职责 | 状态 |
| --- | --- | --- | --- |
| RequestScopedCarrier | `core/native_view_parsed_cache.py` | 单请求内共享已解析 arch | VERIFIED_STATIC |
| Business Structure Adapter | `handlers/ui_contract_v2_form_structure.py` | 业务结构（identity/section/ownership） | VERIFIED_STATIC |
| Layout Adapter | `handlers/ui_contract_v2_projection.py` | 布局 containerTree / listProfile | VERIFIED_STATIC |
| Assembler | `core/unified_page_contract_v2_assembler.py` | 纯组装，不重复解析 | VERIFIED（guard 4 sources） |
| Runtime 语义 Resolver | `core/unified_page_contract_v2_runtime.py` | 统一渲染语义，不保留第二词汇表 | VERIFIED（158 项测试 + guard） |

## 结论

业务结构与布局职责分离，Assembler 不重新解析 XML、不隐式补齐，职责边界成立。
