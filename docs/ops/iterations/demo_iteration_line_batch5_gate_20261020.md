# Demo 迭代线 Batch 5 门槛证据（timer 目标租户身份，只读，2026-10-20）

## 结论（静态事实）

1. `deploy/demo-tenant/scems-demo-tenant.timer`：`OnCalendar=*-*-* 04,16:00:00 Asia/Shanghai`，
   触发 `scems-demo-tenant.service`，描述为“Periodic reset of the isolated SCEMS public demo tenant”。
2. `scems-demo-tenant.service`：`ExecStart=/usr/bin/make demo.tenant.reset ENV=demo ENV_FILE=/etc/scems/demo-tenant.env`，
   `WorkingDirectory=/opt/sce/demo-product`——独立 env 与独立产品根，非本地 `sc_dev_demo`。
3. `scripts/demo/tenant_lifecycle.sh`：reset 要求 `ODOO_DBFILTER == ^DB_NAME$`，流程为停公共代理 →
   清 filestore/移除该租户 Odoo 数据卷 → `demo.reset` → `demo.load.release` →
   `verify.demo.release.seed` → `verify.demo.formal_product_coverage`。即全库基线重建 + release seed。
4. 仓库内不存在 scoped experience reset（未找到只清理体验用户增量的机制）。

## 待 owner 确认（改 timer 前的唯一事实门槛）

- 若体验用户操作发生在该“公开 demo 租户”上：定时全库重建会清掉体验增量，需新增 scoped
  experience reset 后才能改/保留该 timer。
- 若该公开租户只作静态 showcase、体验用户操作在 demo 主租户（`sc_demo`/`sc_dev_demo`）：
  则 timer 只影响 showcase，需另行确认主租户上不存在类似全库重建定时任务。

在以上身份未确认前，不修改 timer，不把 `demo.tenant.reset` 当作体验清理入口。

## Owner 裁定（2026-10-20 补充）

- 体验用户当前以全功能账号在主租户完成功能；后续允许通过系统注册为体验用户并授权。
- 更优方案：单独定义「体验用户」角色（`group_sc_role_experience_user` + 最小能力），
  使体验增量清理边界由角色确定——清理 `create_uid`/`write_uid` 持有该角色的业务记录，
  以及其附件、消息、活动、会话与审批实例，且体验用户不获得业务审批权限。
- 该角色是产品层语义：P1（role_surface 角色 + 能力）、P3（可见性/菜单）、P0（注册授权）。
  demo 层只消费、不自造；在角色落地前，demo 层以「demo 声明的体验登录集合」作为临时清理键。
- 结论：公开 demo 租户 timer 保持不变（showcase 全库重建）；scoped experience reset
  以「体验用户角色」为清理键，待产品角色落地后接入。
