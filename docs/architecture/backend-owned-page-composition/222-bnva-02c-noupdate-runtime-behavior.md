# 222 · BNVA-02B-02C-02B-03A · noupdate 运行时行为

## 结论（基于 Odoo 语义 + 现有代码）

- `noupdate=0`（默认）：模块升级按 XML 重写记录字段，含 contract_json，会重置来源戳。
- `noupdate=1`：升级保留运行态。
- 现有 `create/write/_append_published_version` 不改写 noupdate 行为；无自定义 hook。

## 状态

真实隔离库升级行为 `not_run`（需一次性 DB + `-u module`，留待 03B 切换时实测）。

