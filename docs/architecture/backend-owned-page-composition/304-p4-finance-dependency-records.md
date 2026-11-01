# 304 · P4 Finance Dependency Records

## 结论

BLOCKED：项目/往来单位创建存在超出授权的强制依赖链，未创建记录。

## 依赖清单

1. `fixture_role_finance_dependency_creator` 发布导航为 0，无法通过菜单使用“真实产品创建界面”。
2. `project.project` 强制 `stage_id`（many2one → project.task.type），sc_clean 中 project.task.type=0，
   即没有可用的项目阶段，创建项目需要先有项目阶段记录。
3. `project.project` 其他必填字段大多有默认值：operation_strategy=direct、sc_approval_state=draft、
   rating_status=stage、rating_status_period=monthly、last_update_status=to_define。
4. `res.partner` 强制 `property_account_payable_id` / `property_account_receivable_id`，
   sc_clean 有 account.account=47，通常可由公司默认科目满足，仍需在真实界面确认。

## 未执行

未创建第六条记录（项目阶段），未扩张角色菜单权限，未修改 ACL。
