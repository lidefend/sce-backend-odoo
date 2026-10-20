# Demo 用户使用基础数据迭代交接（2026-10-20）

## 1. 身份

- Repository：`/home/lidefend/workspace/sce-backend-odoo-local-env`
- Branch：`feature/demo-iteration-line-20261020`
- Current main baseline：`74063688e928d25c8e65037ac3306956c954244d`
- Plan：`docs/demo/demo_usage_foundation_plan_v1.md`
- Goal：`.agent/goals/DEMO-USAGE-FOUNDATION-20261020.yaml`
- Run：`.agent/runs/DEMO-USAGE-FOUNDATION-20261020/run.json`

## 2. 当前状态

- 计划：已完成
- F1–F3：实现、证据和运行时回读已完成
- F3 银行账户：`res.partner.bank=9`，已加载
- 下一批次：F4 审批、编号和权限配置
- F4–F8：`not_started`
- 主线集成：`not_run`
- 部署：`not_run`
- 用户验收：`not_run`
- Run 状态：`active`

## 3. 执行器启动

```bash
cd /home/lidefend/workspace/sce-backend-odoo-local-env
git switch feature/demo-iteration-line-20261020
git status --short
make agent.run.resume
```

必须确认：

1. HEAD 是 planning commit；
2. worktree clean；
3. run 解析到 `DEMO-USAGE-FOUNDATION-20261020`；
4. 当前 worktree 只有本 demo 执行器一个写入者；
5. 不触碰主产品 worktree `/home/lidefend/workspace/sce-backend-odoo`。

## 4. 第一精确动作

从 F1 开始：先写“用户路径 → 基础数据 requirement”只读清单和审计测试，不补业务数据。

F1 的最小产物：

- 一份机器可读 manifest，至少覆盖 U0–U5；
- 一个只读审计入口，返回每项 observed/missing/blocked；
- 每个缺口的责任层、repair hint、阻断批次；
- 非零离线测试，覆盖完整、缺失、非法声明和重复键。

完成 F1 后停止，向所有者报告：

- 已存在但字段不完整的基础数据；
- 完全缺失的基础数据；
- 需要 P0/P1/P2/P3 修复的产品缺口；
- 可继续进入 F2 的精确文件范围。

## 5. 批次顺序

`F1 → F2 → F3 → F4 → F5 → F6 → F7 → F8`

任一前批失败时，不启动后批。每批执行器必须：

- 更新同一份 run 结果索引；
- 写批次记录；
- 记录测试数、身份、环境 readback、失败分类和原始日志路径；
- 只重跑受影响集合；
- 完成后向所有者提交短交接，不自行合并 main。

## 6. 立即发现的缺口

| 缺口 | 归属 | 影响 | 处理 |
|---|---|---|---|
| demo 分支缺 active-run 绑定 | P4 context | `agent.run.resume` 原返回 unregistered | 本交接同步补齐 |
| `system_fact` 仍是 `unbound` | P4 | 每日定时任务不产生真实业务事实 | F7 |
| readiness 以记录存在性为主 | P4 validation | 错误地把“表里有数”当成“用户可用” | F1/F3/F5 |
| role smoke 只覆盖 3 角色 | P4 validation | 业务全功能账号可能登录后无真实待办 | F2/F8 |
| 2025 固定日期、50/100 样例金额 | P4 data | 演示数据与当前业务日期/金额感不一致 | F3/F8 |
| 场景 manifest 仅 D1–D3 | P4 scenario | 声明 10 天但无法连续每日推进 | F7 |

产品缺口继续使用 `docs/demo/product_gap_registry_v1.md` 的 owning-layer 登记，不在 demo 数据层兜底。

## 7. 边界与排除

- 不修改主产品 worktree。
- 不新建 database、tenant、Compose project、port、volume 或 credential。
- 不直接写 `ir.config_parameter` 改变产品配置。
- 不手工写业务终态、审批历史、台账或派生投影。
- 不在 demo 层按角色名/模型前缀/菜单数量推导产品能力。
- 已完成的 demo 机制线 Batch 1–6 不重做；只消费其入口和证据。
- 体验 reset 只清理体验用户操作增量，不重置 demo 基线。

## 8. 完成维度

- 批次验收：F1–F8 各自完成并通过定向验证后分别成立。
- 主线集成：未执行；需所有者单独授权。
- 部署：未执行；timer 变更属于后续受管部署步骤。
- 用户验收：未执行；F8 完成后另行报告。

## 9. 回滚

- 计划/交接回滚：撤回本规划提交。
- F1 manifest/verifier 回滚：删除新增工具与测试，保留原缺口登记。
- F2–F5 数据回滚：按具体 seed/XML/管理变更集回退；不使用全库重建。
- F6 API 驱动回滚：停用驱动入口，保留日志。
- F7 定时任务回滚：停用新 timer/入口并恢复前一计划；不删除用户历史证据。
- F8 浏览器验收回滚：只修正 owning layer，不降低验收门槛。
