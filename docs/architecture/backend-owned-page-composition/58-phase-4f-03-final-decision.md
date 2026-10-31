# 58 · Phase 4F-03 Final Decision

## Verdict

READY_WITH_CONSTRAINTS

- Phase 4F-03 架构裁定本身完成并冻结（ARCH-DECISION-004）。
- 约束：containerTree 未进入 Guard、fallback / 权限 / 旧消费者 / 历史身份仍
  NOT_VERIFIED、页面资产全集仍为 partial_known_samples。
- Phase 4 不予关闭。
- Phase 5 不予启动。

## 七个问题

1. 四种结构的最终职责：见 54 / 55 号文档。slots=业务组合权威，
   fieldGroups=业务分组事实，fieldOwnership=唯一主归属，containerTree=布局
   拓扑权威，Renderer=表现权威，服务端权限=最终授权。

2. 是否需要调整 Backend-Owned Page Composition v1：

   需要调整治理边界表述（引入布局层，与业务组合层分离），不需要新增平行
   Schema；`fieldOwnership` minimal schema 保持不变。

3. containerTree 是否纳入 Guard：

   需要。建议新增 PC-011 布局一致性规则；本轮不实施。

4. 是否需要增加 slots 与 containerTree 的映射校验：

   需要。防止同一字段业务归属被两个来源分别决定。

5. 是否具备进入配置治理准备的条件：

   否。无页面同时具备完整结构、唯一归属、权限、版本与历史身份证据。

6. Phase 4 是否可以关闭：

   否。布局权威治理（containerTree → Guard）与运行时证据闭环未完成。

7. Phase 5 是否可以启动：

   否。Phase 5 三项准入条件（Guard 可信、Legacy 可盘点、迁移风险可控）均未
   达成。

## 五个真实样本反向验证

| 页面 | 新模型能否解释 | 裁决 |
| --- | --- | --- |
| project.project 590/1776 | 能：slots=0 但 containerTree 支撑渲染，布局权威 ≠ 业务组合权威 | 未准入；unclassified_historical |
| project.project 652/944 | 能：与 590 共享 pageId，无结构分叉证据，render profile 不同 | 未准入；unclassified_historical |
| payment.request 649/1773 | 能：slots=9 说明业务组合已声明，但 ownership 缺失 | 未准入（最接近 Formal） |
| sc.payment.execution 709/1658 | 能：fieldGroups 存在但 slots=0，落入场景 5 | 未准入 |
| sc.receipt.income 708/1655 | 能：无记录无契约，证据域外 | NOT_VERIFIED |

该模型没有把 slots=0 + fieldGroups=true + containerTree 存在合并为
“结构完整”结论。

## 下一阶段建议（不授权，待统一调度）

1. Phase 4G-01：将 containerTree 纳入 Guard（PC-011 布局一致性），并建立
   slots ↔ containerTree 映射校验。
2. Phase 4G-02：补齐 PC-007～PC-010 的运行时 / 权限 / 旧消费者 / 历史身份证据。
3. Phase 4G-03：完成页面资产全集盘点（消除 partial_known_samples 缺口）。
4. 将 ARCH-DECISION-004 注册到 `.agent/decisions/`（需另行批准，不在本轮
   交付路径内）。

## 执行边界确认

- 本轮未修改 Schema、assembler、Guard、Renderer、业务配置、数据库或权限。
- 未删除 Legacy fallback，未迁移页面，未重建 Candidate。
- 仅新增 54～58 号架构决策文档。
- 工作树既有未提交改动全部保留。
