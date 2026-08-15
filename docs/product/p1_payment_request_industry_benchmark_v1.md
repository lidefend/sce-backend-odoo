# 付款申请行业标杆与字段完整度标准 v1

## 1. 适用边界

本标准属于 P1 建筑业标准产品，只约束 `payment.request` 与 `sc.payment.execution` 的业务办理和事实投影，不包含客户特例，不重建合同、结算、成本或资金台账事实。

字段多不等于专业。付款办理的专业完整度必须同时证明：付款依据可追溯、金额可解释、合规可判断、动作可执行、结果可回写、异常可恢复、权限不越界。

机器可执行的字段分类、页面表面和旅程门禁见 `config/p1_payment_request_field_completeness_v1.json`。

## 2. 标杆事实

- Oracle Primavera Unifier 的付款申请与合同关联，并覆盖工作流、必填校验、草稿、附件、合同详情、币种及工程量清单延续表；批准结果进入成本与资金事实。
- Autodesk Construction Cloud / GCPay 将付款申请与预算编码、工程量清单、已完工作、在场材料、保留金和合规资料联动，批准后同步成本管理。
- Procore 的工程付款办理覆盖合同、计费期间、工程量清单、已完工作、在场材料、保留金、变更与已付款事实。
- SAP Fiori 的审批任务强调清单/详情、附件、说明、历史及批准、驳回、转交；必填说明由业务规则控制。

权威参考：

- [Oracle Primavera Unifier Payment Applications](https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/accelerator-user/paymentapplicationbusinessprocess-10296630a.html)
- [Oracle Primavera Unifier Cost Transactions](https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/udesigner/howcosttransactionsworkinunifier-77655a.html)
- [Autodesk Construction Cloud GCPay Integration](https://help.autodesk.com/cloudhelp/ENU/Build-Cost/files/setup-cost/cost-integrations/Cost_GCPay_Integration.html)
- [Procore Project Invoicing](https://support.procore.com/products/online/user-guide/project-level/invoicing)
- [SAP Fiori Approve Requests](https://help.sap.com/docs/SAP_FIORI/5d441ea8c6ba4ee798d1a679165b3970/eb53ee52f0720175e10000000a44538d.html)

## 3. 字段归属规则

| 事实 | 权威归属 | 付款页面责任 |
|---|---|---|
| 合同双方、付款条件、累计变更、累计结算/开票/付款 | 合同 | 只读摘要与钻取 |
| 结算期间、工程量清单、审定金额、扣款、合规状态 | 结算 | 只读带入、金额校验与阻断 |
| 项目、收款单位、本次金额、账户快照、说明与附件 | 付款申请 | 办理输入、快照和审批事实 |
| 付款账户、本次实付、付款凭证 | 付款登记 | 财务执行输入与资金事实 |
| 已付累计、资金/成本台账 | 后端台账 | 只读回写与双向追溯 |

任何上游事实投影到付款页时必须展示来源。不能为了字段齐全重复手工录入，也不能以空占位冒充已经具备事实。

驳回不是流程终点，也不能退回成无约束草稿。当前驳回原因必须明确显示；经办人只在 `rejected` 状态修正项目、依据、对象、金额、账户、说明和附件，重新提交后这些事实再次锁定。当前驳回原因在再提交时清空，但历次原因和状态转换永久保留在审计记录中。

一张付款申请允许分多次实付。唯一性约束只能限制同一申请同时存在一个办理中的付款登记，不能限制历史付款登记总数。通过专业付款登记办理的每次分次实付，必须形成独立付款登记和以该登记为锚点的台账事实；费用报销等相邻业务直接形成的台账属于各自受控来源流程，不纳入本分次付款登记合同。部分付款后申请保持已批准并展示累计已付、剩余待付与下一次可付金额，只有累计有效台账达到申请金额时才能完成。冲销任一笔分次付款后，累计与剩余金额必须重新计算，且原台账事实继续保留。

## 4. 完整度分级

- `required`：在指定办理门禁前必须由用户提供或由系统确定性带出。
- `conditional`：适用条件成立时才必填，并显示明确原因。
- `derived`：后端权威计算，前端只读呈现。
- `optional`：增强说明，不得无条件阻断基础旅程。
- `audit`：用于追溯，默认后置。

每个字段必须同时具备模型、原生视图、产品合同、normalized payload 和用户旅程证据。ORM 中存在字段不算完成。

## 5. 当前行业差距

当前项目合同/结算已有付款条件、累计变更、累计结算/开票/付款、结算期间、扣款、已付累计和可付余额等来源事实，付款申请以只读方式投影这些权威事实。综合合同虽已有质保金字段，但正式付款申请使用的 `construction.contract` 尚无统一质保金事实，因此保留金维度继续标记为缺口，不能跨模型借值或在付款申请重复录入。

工程量清单的“以前完成、本期完成、在场材料”专业拆分仍属于结算产品缺口。它不得以付款申请临时字段替代；在结算专业拆分形成前，该维度保持 `gap`，不能宣称达到完整工程进度款标准。

多币种换算与项目本位币对照目前为 `partial`，同样不得用前端换算冒充后端财务口径。

## 6. 发布出口

发布必须同时满足：

1. 静态矩阵证明字段存在、归属明确、表面覆盖完整。
2. 新建保存后退出再进入，关键事实不丢失。
3. 提交、审批、驳回、再提交均验证必填、只读、待办和历史。
4. 付款登记新建前即可读出四个关系锚点、金额与账户来源。
5. 单次付款、分次付款、撤销、重复请求和超时重试不产生重复或孤儿台账；专业付款执行旅程产生的每笔台账均可追溯到具体付款登记。费用报销等相邻台账沿用各自独立受控的来源链，不冒充付款登记锚点。
6. 跨公司、跨项目和无能力角色在菜单、页面、选择器、API、RPC、ORM 五层一致拒绝。
7. 移动端必须能完成待办查看、审批/驳回、阻断修复与唯一主动作，不以“页面能缩小”代替任务完成。
