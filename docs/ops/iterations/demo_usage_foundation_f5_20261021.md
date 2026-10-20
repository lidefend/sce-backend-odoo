# Demo 用户使用基础数据迭代 · F5 批次记录（2026-10-21）

## 1. 身份

- Repository：`/home/lidefend/workspace/sce-backend-odoo-local-env`
- Branch：`feature/demo-iteration-line-20261020`
- F4 提交：`9e0f7bcbb176b0e04eec07ec4f0acba4d4d90786`
- Run：`DEMO-USAGE-FOUNDATION-20261020`（active）
- Runtime：`sc-local-dev`（db=sc_dev_demo）

## 2. 层级声明

- Formal Product Layer：P4（ops delivery tooling + demo 数据载体）
- Layer Target：既有 `baseline_readiness` manifest/verifier + ORM 回读；`scripts/dev`
  凭据守卫对齐
- Why Here：项目启动基线由既有 P4 回读判定 ready/partial/blocked，只读不补
- Why Not Elsewhere：不写业务终态、不绕过产品守卫、不手工组装 Compose/DB

## 3. 本批单一目标

验证项目启动基线（项目主档、负责人/成员、资金基线、预算、BOQ/WBS、合同/采购依据）
的 ready/partial/blocked 四态，确认付款提交前硬前置有服务端来源。

## 4. 回读结论

`make verify.local.dev.baseline_readiness.orm` PASS：`test_g0_g4_hard_baseline_ready`
1 测试 0 失败。G0–G4 硬基线全部就绪，含 G4 项目启动基线：

- project_basic / project_parties / project_membership_scope / funding_baseline /
  budget_boq_wbs / settlement_anchor 均存在；
- 与 F3 的 `project.project=33`、F4 的审批/编号就绪一致，构成「项目可办理」闭环。

结论：项目启动基线已就绪，本批无需 P4 数据修复。

## 5. 阻断解除（P4 凭据对齐）

F5 回读曾被 `local.dev.demo_credentials.prepare` 的 `DENY invalid existing demo
credential` 阻断：`SC_DEMO_USER_PASSWORD` 已是 `123456`，而守卫常量仍为
`scdevpass`。按所有者 2026-10-21 口径（demo 固定口令 `123456`）做最小对齐：

- `scripts/dev/local_dev_demo_credentials_prepare.sh`：`FIXED_DEV_DEMO_PASSWORD="123456"`
- `scripts/verify/test_local_development_lifecycle.py`：对应断言同步

对齐后 `reuse canonical demo credential` 生效，F5 ORM 回读通过。

## 6. 已知无关失败（不修复）

`make verify.local.development_lifecycle.unit` 仍 1 例失败：
`test_local_make_targets_isolate_inherited_identity` 断言
`local.dev.upgrade: guard.prod.forbid local.dev.ready`，而当前 `make/dev.mk` 该目标
已由他人主基线同步改为 `local.dev.upgrade: guard.prod.forbid`（移除 `local.dev.ready`）。
此为他人同步引入的陈旧断言，与本批口令改动及 F5 无关；不单边修测试或目标，留待 owning
方定夺。

## 7. 验证结果

| 命令 | 状态 | 层 | 测试数 |
|---|---|---|---|
| `make verify.local.dev.baseline_readiness.orm` | passed | L3 | 1 |

## 8. 回滚

- 凭据守卫回滚：恢复 `FIXED_DEV_DEMO_PASSWORD="scdevpass"` 与测试断言；
- 本批无运行时数据写入，无产品代码改动。

## 9. 下一步精确动作

F6（API 驱动真实业务链）：login → system.init → ui.contract → 创建/提交 → 逐级审批 →
结算/付款/付款登记 → 台账/工作台回读；负例拒绝与幂等。
