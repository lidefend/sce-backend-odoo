# 303 · P4 Restricted Fixture Role Report

## 已建立

- login：`fixture_role_finance_dependency_creator`，uid=7。
- 组：`Fixture Finance Dependency Creator` + `base.group_user` 隐含组。
- is_admin=false，不含 `base.group_system`。
- model access：project.project / res.partner 均为 read=true、create=true、write=false、unlink=false。
- 其他模型 create：payment.request、sc.payment.execution、sc.receipt.income、construction.contract 均无 create。

## 发现

该角色发布导航为 0 条（total=0），无法通过前端菜单到达项目/往来单位创建界面。
