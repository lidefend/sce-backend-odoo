# 214 · BNVA-02B-02C-02B-02 · 种子身份与幂等

## migration_id

`hash(module + external_id + seed_version + target_digest)`。module 参与哈希，
避免跨模块相同 External ID/版本/摘要碰撞。

## 状态机

| 状态 | 重复执行行为 |
| --- | --- |
| planned | 执行 |
| running | 拒绝并发 |
| applied | 幂等跳过 |
| rolled_back | 允许重执行 |
| failed | 核验清理后允许重试 |

只有 applied 视为不可重复应用。

