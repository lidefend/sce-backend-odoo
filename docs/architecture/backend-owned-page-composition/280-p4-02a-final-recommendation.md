# 280 · BNVA-02C-02E-P4-02A · 最终建议

1. 故障模块：Odoo 官方 `hr`（间接必需依赖）。
2. 故障点：`hr/README.md` “Time Off Management” 下划线短 2 + 缩进问题。
3. 建议：修复 reST 格式（方案 A），不排除 hr、不改 LOCAL_CLEAN_MODULES。
4. 实施层：P4 环境（镜像补丁或挂载覆盖），不改 Odoo 上游、不改产品代码。

待你确认最小修复载体（镜像补丁 vs 挂载覆盖 vs 其他受管方式）后再执行。

