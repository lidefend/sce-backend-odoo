# 发布恢复闭环（针对当前部署 3f46dd7e）

状态：发布恢复在部署版本 `3f46dd7e` 上重新完整执行并收口。此前回滚制品绑定旧候选
`87e162e8`，不满足“候选与回滚制品匹配”，本轮修正。

## 执行身份

- 部署候选：`3f46dd7eba9f351386fee446151ee9eb545d56a4`
- 演练项目：`sc-release-rehearsal`，数据库 `sc_release_rehearsal`
- fresh clone 干净 checkout（0 unreachable / 0 tag / 0 stash），卫生守卫 PASS

## 完整序列结果

| 步骤 | 结果 |
| --- | --- |
| verify.release.tooling | PASS |
| release.rehearsal.prepare | PASS（77 模块，118s） |
| release.rehearsal.runtime.up | 全部容器 healthy |
| release.rehearsal.upgrade | PASS（幂等重放） |
| fingerprint pre/post + verify.release.rehearsal | pre/post 一致，数据兼容 pass |
| release.rehearsal.backup | 成对回滚制品，绑定 `3f46dd7e` |
| release.rehearsal.restore | PASS（58s，三项一致） |
| release.rehearsal.rollback | PASS（56s，三项一致） |
| verify.release.monitoring | PASS（latency 29ms） |

## 回滚制品

- `database.dump` + `filestore.tar.gz`，manifest 绑定 `release_sha=3f46dd7e`
- 各带独立 SHA-256，证据根 `artifacts/release/frontend-pilot-readiness/`
- 三个演练库存在：`sc_release_rehearsal` / `_restored` / `_rollback`

## 结论

发布恢复与当前部署候选 `3f46dd7e` 匹配，恢复与回滚演练通过。此前的 `87e162e8`
制品不再作为本轮发布恢复证据。
