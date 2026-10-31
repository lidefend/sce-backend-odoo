# 81 · Permission Test Identity Inventory（PC-008）

## 结论

权限测试身份可用性：READY_WITH_CONSTRAINTS

## 已有 fixture 身份（只读盘点）

来源：`addons/smart_construction_acceptance_fixture/tools/
frontend_productization_fixture.py`

| 登录名 | 角色组 | 用途 |
| --- | --- | --- |
| fixture_role_config_admin | group_sc_role_business_admin | 业务配置管理员（当前登录） |
| fixture_role_pm | group_sc_role_project_manager | 项目权限授权样本 |
| fixture_role_contract_operator | group_sc_role_operation_user | 业务操作样本 |
| fixture_role_owner | group_sc_role_owner | 业主样本 |
| fixture_role_executive | group_sc_role_executive | 高管样本 |
| fixture_role_partner_manager | group_sc_role_partner_manager | 无项目基线入口（负样本） |
| fixture_role_system_admin | smart_core.group_smart_core_admin | 平台面，能力闭包与项目基线不相交（判别性负样本） |

## 判断

- 存在可构成“授权 vs 未授权”的身份对（如 pm 与 partner_manager / system_admin）。
- 无需创建用户、改角色或改 ACL。
- 但尚未执行实际运行时权限测试，PC-008 仍 NOT_VERIFIED；本轮只确认身份可用。

## 约束

不得修改 ACL、Record Rules、用户、角色；不得输出凭据。
