# 432 · BNVA-04 Merge Commit Conflict Resolution

## 合并提交

- `dde5224e7` Merge remote-tracking branch 'origin/main' into feature/pc01-phase5-shadow-contraction
- 双亲：5f909dc2e（Feature）+ 37796bc94（GitHub main PR #790）。
- 10 个冲突全部解决，无残留冲突标记，工作树干净。

## 解决方式

- 6 个源码冲突文件 + BNVA-01/run.json + 2 个生成报告：取 Feature 版本。
- active-runs.json：取 Feature 版本（该分支当前活动 run = BNVA-04；PR790 的 BNVA-01 历史记录
  作为 .agent/runs/BNVA-01/run.json 文件单独保留）。

## 硬性保护核查

- PR #790 的 `primary_facts / other_facts` catch-all 赋值块未重新引入（合并 SHA 上
  `ownerSlotRef=slot:primary_facts` 赋值块 ABSENT，走 unclassified_historical / legacy_compatible）。
- 缓存版本 v25（Feature 演进版），未回退到 v15。

## 结论

合并策略按审计执行，未用 ours/theirs 一键覆盖，未恢复已退役 catch-all。
