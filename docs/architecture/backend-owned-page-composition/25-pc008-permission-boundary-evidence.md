# 25 · PC-008 Permission Boundary Evidence

## Evidence

- V2 assembler 输出 `permissionSemanticsPreserved=true`。
- Odoo 服务端仍通过 ACL、Record Rules、字段 groups 授权。
- 前端只读/隐藏由契约权限投影驱动。

## Status

NOT_VERIFIED

## Reason

布尔声明不足以证明权限语义未改变。缺少：

- 真实有权/无权角色测试。
- 直接构造请求的拒绝测试。
- fieldOwnership 不改变授权的对照证据。

