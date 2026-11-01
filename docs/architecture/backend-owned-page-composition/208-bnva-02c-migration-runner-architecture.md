# 208 · BNVA-02B-02C-02B-01 · Migration Runner 架构

## 复用

`ui.business.config.contract` + version snapshots + change_set +
`restore_published_version` + payload_sha256 / definition_sha256。不新增平行 Schema。

## 流程

1. 发现待升级种子（按 external_id/module 锚定）。
2. 校验当前种子版本。
3. 比较源/目标定义摘要。
4. 生成 migration plan。
5. 兼容性校验。
6. 迁移前快照。
7. 经 change_set 受控变更。
8. 校验目标配置。
9. 记录迁移结果。
10. 失败恢复原发布版本。

## 事务与幂等

- 同一 migration_id 只应用一次（幂等）。
- 迁移在单事务内完成；中断不提交。
- 回滚用迁移前快照 `restore_published_version`。

