# 387 · BNVA-04 Quality Issue Productization

## 业务事实

- Model：sc.quality.issue（质量问题），`_inherit = mail.thread, mail.activity.mixin`。
- 原生视图：form 1731 / tree / search 完整。
- Action：744 `action_sc_quality_issue`（质量问题闭环），tree,form。
- 业务字段：name（问题标题，required）、project_id（required）、standard/standard_item、issue_date、
  source_channel、issue_category、issue_level、responsible_party_id、owner_id、rechecker_id、
  rectification_deadline、state（draft/submitted/rectifying/rechecking/closed/cancel）、
  rectification_ids、recheck_ids、attachment_ids。
- 原生 arch 已表达全部业务事实（问题信息、描述、附件、状态条、整改/复验记录）。

## 最小产品化

- 新增 form view 绑定：view_sc_quality_issue_form → action 744。
- 新增 productized contract：`sc_quality_issue_handling_form_v1`，`composition_mode=native_semantic_surface`，
  `workflow_authority=sc.quality.issue`，`title=质量问题办理`，source=product_release，published。

未重新声明 Identity/Section/FieldOwnership——原生 arch 已足够，遵循同文件 quality/safety 既有口径。
