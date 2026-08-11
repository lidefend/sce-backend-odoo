# 制度文件能力基线 v1

制度文件复用 `sc.document.admin.document` 统一资料载体，但以
`fact_type=policy_document` 形成独立业务事实。公司资料存档、证照登记、借阅申请和制度
文件由后端数据域与默认值严格隔离，前端仅按动作契约渲染，不推断文件类型。

制度文件基线包含制度类别、版本、发布部门、发布日期、生效/失效日期、密级、正文说明
和附件。信息完整度不阻断使用节奏；仅生效日期晚于失效日期这一运行一致性错误阻断完成。

权威入口：

- 菜单：`smart_construction_core.menu_sc_product_policy_document_v1`
- 动作：`smart_construction_core.action_sc_product_policy_document_v1`
- 模型：`sc.document.admin.document`
- 表单契约：`smart_construction_core.business_config_contract_policy_document_form_v1`

禁止再次把“制度文件”菜单改名映射到公司资料存档动作，也禁止在前端按菜单文案重写
`fact_type`。
