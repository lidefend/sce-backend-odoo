# 405 · BNVA-04 Tax Certificate Runtime Consumption

## L1 · 服务端身份

同 404：受管验收 profile local（project=sc-fe-r2-p1-01，db=sc_frontend_acceptance，
dbfilter=^sc_frontend_acceptance$）。后端健康，5180 预览端口已监听；工作树 HEAD=281199780，
sc.tax.certificate.registration 契约与视图修正均为未提交改动。

## L2 / L3 / L4

| 层 | 结果 |
| --- | --- |
| L2 Contract 返回 | NOT_RUN |
| L3 Vue Renderer 消费 | NOT_RUN |
| L4 业务交互 | NOT_RUN |

## 孤儿字段

静态侧已确认：source_created_by / source_created_at 已从 tree/form 删除，剩余 15 个 arch 字段全部有效
（04-06B / 04-06C）。运行时「加载不再出现字段解析错误」尚未观察，因运行后端源挂载不一致，NOT_RUN。

## 阻断原因

同 404：受管入口 fail-closed，`managed backend source mount differs from current worktree`。
运行时验证需要受管模块升级与前端预览重建，超出本轮只读范围。
