# 稳定基线增量协作规范登记（2026-10-26）

## 边界与目的

- Formal Product Layer: P4
- Layer Target: repository collaboration and evidence lifecycle
- Module: AGENTS.md / .agent / docs/ops
- Standard vs User-Specific: 仓库共同协作规则，不是客户产品偏好。
- Reason / Why Here: 在已成立测试基线上明确后续增量开发、验证、证据与集成责任。
- Why Not Elsewhere: 不属于 P0-P3 产品语义，不应修改产品、执行器或 CI 阈值。
- Blast Radius: 代理入口、协作协议、任务恢复及历史基线闭环记录；不改变数据库或运行环境。
- Baseline: `5b58d6a1b2ac759c2f1c1cac26e820236fd74f9f`，PR735。
- 复用当前工作树与现有 Make 门禁；无既有 dirty 修改。另一工作树不在范围内。

## 验证与证据

当前唯一结果索引：`.agent/runs/STABLE-BASELINE-COLLABORATION-20261026/run.json`。
L0 身份已确认；L1 执行既有规则/上下文检查与 iteration。产品 L2-L4 不适用：
本次不改产品、测试执行器、依赖或环境，不因文档变化重复 ORM/浏览器验收。
GitHub 集成仍执行冻结候选 Quick、独立复核、外部归档及当前候选四项必需 CI。
冻结后的结果放在 `.runtime/stable-baseline-collaboration/` 与 PR，不追加状态提交。

## 风险与回退

风险是规则间冲突或把声明范围误写为全仓保证。通过既有检查与独立文档复核处理。
回退采用受保护 PR 恢复本次规则内容；不删除历史证据，不改动已成立的测试实现。
批次、主线、部署、用户验收分别报告；本次不包含部署或产品验收。
