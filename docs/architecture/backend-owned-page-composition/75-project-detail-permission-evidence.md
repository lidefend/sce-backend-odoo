# 75 · Project Detail Permission Evidence（PC-008）

## 结论

PC-008 = NOT_VERIFIED（两个入口一致）

## 已确认事实

- 登录身份：`fixture_role_config_admin`（uid=12），仅此一个受管 fixture 账号。
- 服务端权限机制在源码中存在（ACL / Record Rules / field groups），但未取得
  实际运行时权限测试产物。
- `permissionSemanticsPreserved=true` 仅为本页 pageComposition 声明，不构成权限证明。

## 阻断原因

1. 只有授权样本，没有未授权样本；未取得“授权用户可访问 + 未授权用户被拒绝”
   的两侧运行时证据。
2. 执行限制禁止创建/修改用户、ACL、Record Rules 来制造测试通过。
3. 未取得覆盖 `server_permission_mechanism / authorized_access /
   unauthorized_denied` 的 TEST_EXECUTION 或 RUNTIME_OBSERVATION 产物。

## 判断

不得因存在权限机制源码或声明就判定 PASS；PC-008 保持 NOT_VERIFIED，待提供
双样本运行时权限测试证据。
