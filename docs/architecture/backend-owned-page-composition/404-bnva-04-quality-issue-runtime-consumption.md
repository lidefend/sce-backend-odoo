# 404 · BNVA-04 Quality Issue Runtime Consumption

## L1 · 服务端身份

- 受管验收 profile：local，project=sc-fe-r2-p1-01，db=sc_frontend_acceptance，
  dbfilter=^sc_frontend_acceptance$，volumes=sc_fe_r2_p1_01_{db,redis,odoo}。
- 后端容器 sc-fe-r2-p1-01-odoo-1 健康，端口 19083→8069；5180 预览端口已监听。
- 工作树 HEAD=281199780；sc.quality.issue 产品化契约与 form view 绑定为未提交改动。

## L2 / L3 / L4

| 层 | 结果 |
| --- | --- |
| L2 Contract 返回 | NOT_RUN |
| L3 Vue Renderer 消费 | NOT_RUN |
| L4 业务交互 | NOT_RUN |

## 阻断原因

`make acceptance.runtime.login_probe SC_ACCEPTANCE_RUNTIME_PROFILE=local` 被受管入口 fail-closed 拒绝：

`[acceptance.runtime] DENY managed backend source mount differs from current worktree`

运行中的验收后端源挂载与当前工作树不一致，未承载本批未提交的产品契约与视图改动；观察其运行时
需要受管模块升级（写库）与前端预览重建，超出本轮只读范围。

## 结论

sc.quality.issue 运行时消费验证 NOT_RUN，阻断在 L1 身份层（环境源挂载不一致），非产品缺陷。
