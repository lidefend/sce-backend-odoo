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
