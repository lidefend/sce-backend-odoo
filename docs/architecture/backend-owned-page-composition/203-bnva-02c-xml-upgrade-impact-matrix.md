# 203 · BNVA-02B-02C-02A · XML 升级影响矩阵

| 事件 | noupdate=0（default） | noupdate=1 |
| --- | --- | --- |
| 模块升级 | 重写记录字段（含 contract_json） | 保留用户/运行态 |
| source stamp | 被重写回 product_release | 保留 |
| External ID 变更 | 重新绑定/可能重复 | 保留原绑定 |
| XML 删除记录 | 删除运行时记录 | 保留（noupdate 记录不随删除移除） |
| 版本快照 | 新版本 + 快照（若 content 变） | 不变 |

结论：payload 内 source stamp 不是独立字段，noupdate=0 重写会重置来源标记；因此
种子治理必须依赖 noupdate=1 或受控迁移，不能靠来源戳保护。

