# Demo 数据重建进展（2026-10-28）

状态：受管写入链已端到端打通并开始实际重建；恢复点已建立，两条场景记录已落库。

## 受管前置（已完成）

- 修复两个 P4 工具链不一致：daily continuity 备份命名空间对齐 demo duty（PR #747），
  demo 写入门禁改读 demo continuity 恢复回执（PR #748）。
- 新写前恢复点：baseline、配对备份、隔离恢复演练全部通过。
  - backup_set_id：`sc_demo-20261027T154124Z-ee24e88c`
  - 数据库 UUID：`c7ffe700-ce02-11f1-9a86-a213133df790`
  - restore-drill 40s，DB / filestore / sentinel 三项一致
- `daily.demo.write.recovery_gate` 预检 PASS。

## 已重建场景（通过受管 walkthrough 前台业务动作）

| 缺口 | 模型 | 新记录 | 状态 | 与既有记录形成的场景 |
| --- | --- | --- | --- | --- |
| DD-06 劳务实名 | `sc.labor.worker` | ID 2 `DEMO-WALK-20261026-WORKER02` | active 在场 | 与 ID 1（exited）形成多状态名册 |
| DD-02 招投标机会 | `tender.opportunity` | ID 2 `DEMO-WALK-20261026-TENDER02` | draft 未跟进 | 与 ID 1（converted）形成多阶段 |

每条记录都经过：key 唯一性检查 → 前台新建 → 保存回读 → 正式业务动作 → 持久化重载，
数据库独立回读确认，blocked=0、errors=0。

## 已确认的工具限制

- `daily_demo_walkthrough_ui.mjs` 硬编码 key 前缀 `DEMO-WALK-20261026-`，本轮重建沿用该前缀。
- 受管 walkthrough 当前仅支持 6 个模型；DD-04/05/14/15/16/19 等需走官方入口或扩展支持列表。

## 下一批（按计划依赖顺序）

- 材料退货（DD-08）先补材料入库单前置，再关联退货。
- 薪资发放（DD-09）先补薪资核算单前置，再发放。
- 质量验收（DD-04）、签证（DD-05）按官方入口前台办理。
- 完整矩阵与移动端在场景重建后冻结部署一次性重跑。
