# FE-RENDERER-02C-01-R2B：状态语义身份闭合

## 批次边界

- Formal Product Layer：P0 platform kernel product。
- Layer Target：业务表达状态类型身份；附带 P4 guard registry 分类闭合。
- Module：`businessValuePresentation`、共享业务语义测试、静态守卫与 guard registry。
- Baseline：`53c4f3dd185c36e5a276fd89f032376fa39b6294`。
- PR：#840，仅更新候选，不合并、不部署。

## 审查结论

`status=true`、`cellRole=status` 与 `componentKey=sc.display.status` 可以进入 status
表达分支，但字段类型缺失时仍可能直接展示原始内部 key。状态身份不是字段类型权威：

- selection-backed status 必须由 `selection` 类型和有效选择项投影共同证明。
- readable char-status 必须显式声明 `char` 类型，契约提供的可读值才可作为标签。
- 仅声明状态身份而缺少 `selection|char` 类型时必须 `ContractGapError`。

同一 exact HEAD 的 `professional_quality_checks` 还在
`verify.guard.registry` 失败：一个 stale disposition、一个未登记 orphan 和一个缺少
wire-or-retire 处置的脚本。该失败属于 P4 验证工具分类，不是产品运行时缺陷。

修复 registry 后，真实 `ci.local.iteration` 首次以 `BLOCKED` 正确拒绝
`scripts/verify/registry.yaml` 的 unmapped 路径。因此规划器增加明确路由：
registry 行、审计实现及审计测试都执行 `verify.guard.registry`。未知路径仍保持 fail-closed。

## 验收

- `cellRole=status` + selection + 缺少选项：拒绝。
- `status=true` + 类型缺失：拒绝。
- `cellRole=status` + char + 明确可读值：通过。
- `componentKey=sc.display.status` + 类型缺失：拒绝。
- 保留合法 selection-backed status、dataType fallback 与显式 char 路径。
- 业务语义、BOQ、Lint、Strict Typecheck、guard registry 与真实
  `ci.local.iteration` 必须有非零执行结果。

## 执行结果

- 业务语义：PASS，`money=6 status=17 temporal=4 empty=3`。
- 静态守卫：PASS，11 tests；删除 `selection|char` 类型身份检查会被拒绝。
- BOQ：PASS，只读投影 22 checks、请求模型 27 checks。
- guard registry：PASS，24 tests，1601 scripts 审计完整。
- 增量规划器：PASS，81 tests；registry 输入会执行 `verify.guard.registry`。
- Lint：PASS，0 errors，仅保留既有 warning。
- Strict Typecheck：PASS。
- `ci.local.iteration`：PASS，8/8 targets 实际执行，无 blocked/not-run/unmapped。
- `ci.delivery.freeze.prepare`：PASS。生成差异限于：
  - `complexity_budget_report.md` 与 `split_plan_queue.md` 的 registry/planner 行数更新。
  - `component-driver-takeover-inventory-v1.json` 的输入 digest 更新。

Receipt：
`.runtime/frontend-dev-validation/executions/20261108T005856Z-413866-718314972/receipt.json`

首次执行因 `scripts/verify/registry.yaml` 未映射而返回 `BLOCKED`，对应 receipt：
`.runtime/frontend-dev-validation/executions/20261108T005547Z-393134-760933745/receipt.json`。
该失败促成了 planner 的明确路由修复；没有把该次 BLOCKED 改写成 PASS。

## 未覆盖

- 不修改金额、日期、Kanban、审批、验收 fixture、Renderer 协议或业务页面。
- FE-PAYMENT-ENTRY-01 的 409 仍独立处理。
- 不触碰 PR #834。
- 本次产品源码变化只影响共享状态类型判定，不触发既有浏览器证据重跑；若远端检查或独立
  评审证明实际页面输入受影响，再按受影响集合补验。
