# 211 · BNVA-02B-02C-02B-01 · Migration Dry-run 报告

## 产物

`artifacts/backend/controlled_seed_migration_dryrun.json`（40 case，5 样本 × 8 场景）。
纯模拟，不写 Odoo。

## 结果摘要

| 样本 | normal_upgrade | overlay_protection | 关键保证 |
| --- | --- | --- | --- |
| immutable_default_seed | skip_no_change | skip_no_change | 无变更不迁移 |
| versioned_template_seed | migrated_new_version | migrated_new_version（不触覆盖） | 受控迁移 |
| generated_baseline_seed | skip_no_change | skip_no_change | 生成基线不迁移 |
| tenant_overridden_seed | migrated_new_version | migrated_new_version（不触覆盖） | 覆盖保护 |
| retired_seed | skip_retired | skip_retired | 退役不自动恢复 |

8 场景：no_change / normal_upgrade / duplicate（幂等）/ source_mismatch /
target_mismatch（回滚）/ interrupt（不提交）/ overlay_protection / rollback。

