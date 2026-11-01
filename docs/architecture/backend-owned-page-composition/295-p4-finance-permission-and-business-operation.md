# 295 · P4 Finance Permission & Business Operation

## 已证明

- fixture_role_finance 登录，uid=6，非 admin / system。
- payment.request / sc.payment.execution / sc.receipt.income 的 model read/create 通过。
- 三个列表入口可进入，无控制台错误。

## 未证明

打开表单、Identity 显示、关系字段加载、保存、重新进入等真实业务操作尚未执行：
需要先在隔离数据库创建受管测试业务记录（真实产品创建流，非 sudo）。
