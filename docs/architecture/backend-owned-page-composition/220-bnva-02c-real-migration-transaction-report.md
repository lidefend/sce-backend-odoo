# 220 · BNVA-02B-02C-02B-03A · 迁移事务报告

## 流程

resolve（ir.model.data）→ classify → plan → 迁移前快照 → replace_and_publish →
目标摘要核验 → applied / 失败 restore。

## 状态

- 纯逻辑与离线适配测试：22/22 PASS。
- 真实 Odoo 隔离库 + 模块升级：`not_run`（本轮未改 XML，模块升级模拟留待 03B/03C）。

## 事务边界（设计）

- 版本快照不可变、append-only；恢复走 `restore_published_version`。
- 不假设数据库事务与版本恢复天然原子；每步显式落点，失败用快照恢复。

