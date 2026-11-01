# 338 · BNVA-03 Multi-role & Company Context Audit

## 事实

- 多角色：允许字段有序并集，拒绝字段有序交集。
- route authority 契约携带 `principal_scope: {user_id, company_id, role_code}`。
- 公司上下文由服务端契约传递，前端不自行推导。

## 结论

多角色合并与公司上下文机制成立；公司切换与缓存一致性运行时 NOT_RUN。
