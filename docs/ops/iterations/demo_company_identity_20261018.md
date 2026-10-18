# Demo 公司身份与重建数据完整性收口（2026-10-18）

## 目标

`smart_construction_demo` 必须从模块安装、升级和正式 seed 三条路径都生成
可发布的 demo 数据：公司名为 `demo演示公司`，公开账号统一使用 `123456`，
`demo_full` 有稳定 XMLID，重复 seed 不再制造重复附件。重建或重跑种子不得
回到 Odoo 默认的 `My Company`。

## 层级与载体

- 正式产品层：P4 demo 交付载体
- 模块：`demo_addons/smart_construction_demo`，版本 `0.3.1`
- 数据职责：`sc_demo`（`sc-demo-dev`）
- 最终运行身份以部署服务器 HEAD 为准；本轮功能修复提交为
  `e340b43d70c91762aee59d8b1fee232ec9680926`。

## 根因与修复

- 公司身份：`hooks.apply_demo_company_identity` 同时修正公司和公司往来单位；
  安装钩子与正式 seed 的 `demo_company_identity` 共用该实现，且该步骤位于
  `demo_full` profile 首位。
- 公开账号：`hooks.apply_demo_user_passwords` 覆盖模块 XMLID 用户及
  `wutao/demo_full/demo_pm/demo_finance/demo_cost/demo_audit/demo_readonly/sc_test_admin`
  八个公开身份；`demo_85_passwords` 在所有用户创建后、最终自检前重放。
- `demo_full`：模块 XML 直接声明该用户；`migrations/0.3.1/pre-migration.py`
  先把旧库中已存在但无 XMLID 的同名用户绑定到
  `smart_construction_demo.user_demo_full`，避免唯一登录约束冲突。
- 认证自检：按用户建立独立 `api.Environment` 校验凭据，避免误校验
  `__system__` 后产生假通过。
- 附件幂等：`demo_60_attachments` 对已存在草稿资料复用同名附件，缺失时才
  新增并以 `(4, id)` 追加，不再替换关系或产生重复无主附件。

## 验证

- `make verify.demo.lifecycle.unit`：81 项 PASS（30 + 5 + 46）。
- `make verify.demo.supplemental.unit`：46 项 PASS。
- `daily.runtime.candidate.bundle_sync`：`ffab2696…` → `e340b43d…` PASS，
  `origin_main_mutated=false`。
- 功能候选 `e340b43d…` 上 `daily.runtime.database.duty.refresh/upgrade/seed`
  均 PASS；两次 seed 执行链均包含 `demo_company_identity`、
  `demo_60_attachments`、`demo_85_passwords`、`demo_90_verify`。最终文档
  提交 `94b125ed…` 同步后仅刷新容器以对齐运行身份，未再写业务数据。
- 库内回读：`smart_construction_demo.user_demo_full` 唯一指向 `demo_full`
  （`res_id=60`）；公司与往来单位均为 `demo演示公司`；模块状态
  `installed`，版本 `17.0.0.3.1`。
- 八个公开账号用 `123456` 逐一通过 Odoo 凭据校验，均返回
  `demo演示公司`。
- 两次 seed 前后附件均保持 `883` 行、`1,279,088` 字节，未继续增长；
  历史重复 seed 留下的 100 个无主演示附件保留未删，作为审计残留。

## 边界

- 仅操作 `sc-demo-dev/sc_demo`；未触碰历史保护库、生产库、租户库或用户模块。
- 未重建、未清空日常 demo 库；重建路径由安装钩子、迁移、正式 seed 及幂等
  回归测试共同约束。
