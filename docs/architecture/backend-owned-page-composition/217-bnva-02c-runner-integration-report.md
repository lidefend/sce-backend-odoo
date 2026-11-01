# 217 · BNVA-02B-02C-02B-02 · Runner 集成报告

## Odoo 集成点（设计，未在生产执行）

- 执行更新：`UIBusinessConfigContract.replace_and_publish`（内部已走发布门禁）。
- 回滚：`restore_published_version`。
- 预览/审批：`ui.business.config.change.set`。
- 身份锚：`ir.model.data`（module + external_id）。

## 隔离环境验证

真实 Odoo 隔离库 + 模块升级模拟留待 02B-03（XML noupdate 切换时执行），本轮以
纯逻辑 16 测试 + 40 dry-run case 覆盖状态机与覆盖保护。

## 结论

Runner 薄、复用现有快照/change_set、幂等、跨模块唯一、覆盖隔离成立。

