# 278 · BNVA-02C-02E-P4-02A · 依赖闭包

`sc_norm_engine` → `smart_construction_core` → `hr`（直接依赖）。
`hr` 是 Odoo 官方核心模块（HR 基础），非 OCA、非自研。

`smart_construction_core` 的完整闭包 16 模块中 `hr` 为必需依赖，不可排除。
“Time Off Management” 文本只在 `hr/README.md`，不在任何 manifest description。

