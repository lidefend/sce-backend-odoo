# PR #907 独立审查修订说明

## 结论边界

本次修订仍属于 P4-00 审计与设计审查，不进入 P4-01，不修改现有验证裁决。

修订后，P4-00 可以证明：

- 现有门禁、Make、workflow、脚本生命周期和主要调用面已被枚举。
- 结构性问题、责任层边界、证据权威和增量设计已被明确提出。
- 审计产物符合仓库文件治理，且可确定复现。

修订后，P4-00 仍不能证明：

- 539 个 gate-reachable 文件的每个 assertion 已被准确识别。
- 传递调用、动态注册、真实服务依赖和重复覆盖已经闭合。
- 新 planner 能正确选择检查或接管现有门禁。

## P0：审计事实与推断分离

已修订：

- 每个 item 增加 `answer_grades`、`evidence_profile`、`responsibility_status` 和
  `call_chain_status`。
- workflow/Make/registry 的直接引用标为 `observed_declaration`。
- 脚本 docstring/header 的用途标为 `declared_metadata`。
- 资源、层和共享执行文件标为 `static_inference`。
- workflow job 的人工归纳标为 `manual_review`。
- 未建立的运行时、传递调用、assertion 和 duplicate 关系标为 `UNKNOWN`。
- `duplicate_or_overlap` 不再输出空数组，而是 `UNKNOWN` 加 shared invocation candidates。
- 新增 `analysis_coverage`，当前 `obligation_linked_items=0`、`assertion_linked_items=0`。

## P1：机器产物与 RH007

首次远端 public_guard 因 `verification_mapping_matrix.json` 超过 5 MiB 触发 RH007。

已修订：

- `verification_mapping_matrix.json` 改为索引。
- workflow、Make target、gate scripts 和 script lifecycle 分域存储。
- script lifecycle 按稳定顺序分片。
- 生成器测试断言任何输出文件均小于 5 MiB。
- 未增加 RH007 例外。
- 重新生成后逐字节一致性作为可复现条件。

## P2：影响分析准确性验收

新增 `impact_analysis_acceptance_matrix.json`，覆盖：

- Decoder-only。
- Renderer-only。
- CSS/responsive-only。
- ORM / ACL。
- 前后端混合。
- 动态依赖 UNKNOWN。
- contract field rename/delete。
- assertion 或 fixture 变化。
- 纯文档变化。
- 错误 evidence reuse。
- CI selector/tooling 变化。

历史回放样本引用 PR #905、#877、#870、#886、#893、#904、#883；无直接历史样本的安全反例
明确标为 synthetic conformance。

每个 case 同时声明 expected obligations、check classes、evidence、禁止执行层和 BLOCK 条件。
后续不能只比较分类标签，必须证明选中的 checks 覆盖目标 assertions。

## P3：验证体系自身安全指标

设计和 acceptance matrix 已固定：

- False Negative = 0 才允许 cutover。
- Evidence Reuse Error = 0 才允许 cutover。
- Obligation Coverage = 1.0。
- Unknown Obligations = 0。
- Stale Proof Accepted = 0。
- False Positive 必须逐例解释；未解释的相关误报阻断。

## 未解决问题

以下问题不在 P4-00 伪造解决：

1. TypeScript symbol/compiler 级真实依赖图尚未实现。
2. Python/Odoo model-method-workflow 级依赖图尚未实现。
3. 动态组件、字符串调用、反射和跨模型运行关系仍为 UNKNOWN。
4. obligation-to-assertion-to-evidence 双向图尚未实现。
5. duplicate coverage 尚未基于真正 assertion 集分析。
6. 历史 PR shadow replay 尚未执行；当前只定义预期契约。
7. 新 planner 未接管现有 CI，也不能被描述为已具备接管资格。

这些项目分别属于 P4-01、P4-02、P4-04 和 P4-06 的退出条件。
