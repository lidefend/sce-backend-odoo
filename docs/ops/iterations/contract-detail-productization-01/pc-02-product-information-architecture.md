# PC-02 · 合同详情页产品信息架构

结论类型：DESIGN_PROPOSAL；数据来源为 CODE_FACT。

## 目标

将传统合同长表单转为合同履约与资金管理工作空间。复用 PC-01 七条标准，但不预设与项目详情相同布局。

## 七个区域

| 区域 | 数据来源 | 交互/空态 | 类型 |
| --- | --- | --- | --- |
| 合同身份带 | name/subject/type/business_category_id/state | 唯一标题、状态栏、只读权限投影 | DESIGN_PROPOSAL |
| 金额状态带 | 五层金额链（amount-*） | 数值、币种、待接入状态 | DESIGN_PROPOSAL |
| 主体与关联项目 | partner_id/project_id/operation_strategy/affiliated_person | 两列资料布局 | DESIGN_PROPOSAL |
| 条款与合同明细 | engineering_content/duration/payment_method/line_ids | 长文本与明细分离 | DESIGN_PROPOSAL |
| 变更及补充协议 | sc.contract.change / original_contract_id / supplement_contract_ids | 关系视图、只读列表 | DESIGN_PROPOSAL |
| 审批与办理时间线 | validation_status/can_review/approval_info | 协作时间线 | DESIGN_PROPOSAL |
| 附件与档案 | attachment/archived/change.attachment_ids | 既有附件组件 | DESIGN_PROPOSAL |

## 目标视图与 Action

- 目标模型：`construction.contract`
- 目标视图：`view_construction_contract_form`（`contract_views.xml`）
- 目标 Action：575
- 环境：`sc_dev_demo`（后续真实合同数据验收）

## 实施顺序

PC02-P1 身份带 → PC02-P2 金额状态带（重点）→ PC02-P3 主体关联 → PC02-P4 条款明细 →
PC02-P5 变更审批档案 → PC02-P6 四视口真实合同验收。
