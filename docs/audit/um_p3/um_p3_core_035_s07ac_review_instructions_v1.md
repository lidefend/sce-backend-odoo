# CORE-035 S07A-C 人工确认说明

本工作集用于逐条确认历史分包结算明细与分包登记明细之间的业务关系。它只是一份待审核
材料，不是迁移映射；任何候选都不得因出现在工作集中而被视为已经确认。

## 审核角色

| 角色 | 职责 |
| --- | --- |
| 历史分包业务负责人 | 第一审核，依据原始合同、登记单、结算单和审批资料确认业务事实 |
| 数据治理负责人 | 校验证据来源、候选完整性、冲突标识和审计摘要 |
| 独立第二审核人 | 独立复核最终决定，且不得与第一审核人相同 |
| 项目所有者 | 决定是否将完成双审的结果提交 S07B 评审，不替代业务事实确认 |

审核人字段应填写经组织授权的稳定身份引用，不填写密码、联系方式或其他不必要的个人
信息。`PROJECT_OWNER` 不能自动作为历史关系确认人。

## 决策规则

`reviewer_decision` 只能使用：

- `CONFIRM_ONE`
- `CONFIRM_NONE`
- `REQUIRE_SOURCE_DOCUMENT`
- `REQUIRE_BUSINESS_OWNER_DECISION`
- `INVALID_SOURCE_RECORD`

`decision_status` 只能使用：

- `PENDING`
- `FIRST_REVIEW_COMPLETED`
- `SECOND_REVIEW_COMPLETED`
- `AUTHORIZED_FINAL`
- `REJECTED`
- `ESCALATED`

只有下列条件全部成立时，审核项才可进入 `AUTHORIZED_FINAL`：

1. `reviewer_decision=CONFIRM_ONE`；
2. `confirmed_register_ref` 位于完整候选集中，或填写了可审计的
   `authoritative_source_document_ref`；
3. 第一审核人、时间和授权证据齐全；
4. 第二审核人和时间齐全，且与第一审核人不同；
5. `evidence_digest` 与不可变来源证据一致；
6. 整个确认集通过机器 validator。

任何未满足条件的记录继续保持未确认，不得出现在迁移映射中。

## 候选与冲突

- `ATTRIBUTE_CANDIDATE_ONLY` 只表示项目和往来单位等属性形成了有限候选池，不证明关系。
  不得按金额相等、名称、最近日期、合同组合或排序选择候选。
- `CONFLICTING` 表示旧字段形成了明确边界冲突。所有此类记录必须索取原始合同附件、
  登记单、结算单、审批记录或业务负责人书面确认。
- `pid→RowIndex` 已被 S07A 证明为伪关联，任何审核或工具都不得使用它作为确认依据。
- 多候选必须完整保留，不得只展示或选择所谓“最高分”候选。

## 文件签署

1. 审核前确认 manifest 和 confirmation-items 文件 SHA-256。
2. 第一审核完成后运行 validator，保留结果和证据编号。
3. 第二审核必须独立完成，再次运行 validator。
4. 数据治理负责人填写授权模板；未签署模板不得改为已签署状态。
5. 项目所有者仅在全部最终项通过审计后决定是否申请 S07B。

本阶段不允许修改 LEGACY_SOURCE_A、LEGACY_SOURCE_B、任何既有业务数据库或
`sc.subcontract.settlement.line.register_line_id`，也不允许执行迁移、回填或批准 S07B。
