# Demo 用户使用基础数据迭代 · F6 批次记录（2026-10-21）

## 1. 身份

- Repository：`/home/lidefend/workspace/sce-backend-odoo-local-env`
- Branch：`feature/demo-iteration-line-20261020`
- F5 提交：`73644152d89d367b315a2170dddee2459aebd88c`
- Run：`DEMO-USAGE-FOUNDATION-20261020`（active）
- Runtime：`sc-local-dev`（db=sc_dev_demo）

## 2. 层级声明

- Formal Product Layer：P4（ops delivery tooling）
- Layer Target：既有 demo API 场景验收（`verify.local.dev.api_scenario.orm` +
  `verify.local.dev.golden_chain.orm`）
- Why Here：真实业务链通过公开 action 推进，demo 层只消费、只读回读
- Why Not Elsewhere：不绕过审批、不写终态、不伪造审批历史

## 3. 本批单一目标

验证完整业务链可由公开 action 推进并保持金额/状态/角色一致：创建草稿 → 提交 →
逐级真实审批 → 结算/付款/付款登记 → 台账/资金/回款回读；负例拒绝、重复提交拒绝。

## 4. 回读结论

| 目标 | 结果 |
|---|---|
| `verify.local.dev.api_scenario.orm` | passed，2 测试：四层审批链（draft→submit→逐级真实审批人→approved）+ 表面接线；非审批人拒绝；重复提交抛 UserError（幂等） |
| `verify.local.dev.golden_chain.orm` | passed，1 测试：冻结链 结算→付款→台账→回款→资金→对账 的金额/状态/角色接力一致（ledger=120000、treasury=1200000 等） |

结论：API/ORM 层完整业务链已就绪，重复提交不产生重复审批实例，无权角色被拒绝。

## 5. 边界与 F8 承接

- HTTP 传输层的 `trace_id`/`request_id` 回执与完整 `ui.contract` 创建/提交浏览器链
  属 F8（业务全功能账号浏览器验收）口径；F2 已验证 login/system.init 的 HTTP 契约，
  F6 以公开 action 的 API 级链为验收边界。

## 6. 验证结果

| 命令 | 状态 | 层 | 测试数 |
|---|---|---|---|
| `make verify.local.dev.api_scenario.orm` | passed | L3 | 2 |
| `make verify.local.dev.golden_chain.orm` | passed | L3 | 1 |

## 7. 回滚

本批无新增数据/代码改动（只运行既有受管验收）；无需回滚。

## 8. 下一步精确动作

F7（每日运行与体验重置）：scenario manifest 10 日叙事、system_fact 处理器、tick、
timer、experience reset scope 的连续推进与基线指纹不变。
