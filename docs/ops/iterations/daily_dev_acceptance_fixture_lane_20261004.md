# Daily Dev Acceptance Fixture Lane（日常库承载验收夹具）

Run: `.agent/runs/DAILY-DEV-ACCEPTANCE-FIXTURE-LANE/run.json`
Branch: `fix/daily-dev-acceptance-fixture-runtime-20261004`（前序
`codex/daily-dev-acceptance-fixture-lane-20261004` 已由 PR #548 合入）
Baseline: `5153e0ac69f0dd24ac6b472fff2ceef794307a3b`（`main`，含 PR #548）
Date: 2026-10-04
Runtime repository: `sc-root:/opt/projects/repos/sce-product-odoo`
(`ENV=dev`, `ENV_FILE=.env.dev`, `DB_NAME=sc_demo`)

## Objective

Owner authorized the daily development database `sc_demo` to carry the governed
acceptance fixture (`2026-10-04`). This closes the `contract` section of
`make verify.daily_dev.acceptance.readonly.probe`, which had been failing with
`errors=["record_resolution_missing"]` because the managed record-identity
resolution artifact only existed for the isolated acceptance database
`sc_frontend_acceptance`.

The isolated acceptance guard and its database binding stay exactly as they are.
The daily database is added as a **separate declared scope**, reachable only
through a governed, confirmed Make entry bound to `DB_NAME=sc_demo` and
`SC_ENVIRONMENT=dev`.

## 1. 边界与层级

| 项 | 值 |
| --- | --- |
| Formal Product Layer | P4（ops delivery tool） |
| Layer Target | acceptance fixture carrier scope + daily development runtime lane |
| Standard vs User-Specific | 运维交付工具；无产品语义、无客户基线、无平台机制 |
| Module | `smart_construction_acceptance_fixture`（carrier）/ `make/dev.mk`（daily lane） |
| Blast Radius | 仅日常档 `sc_demo` 新增夹具数据；隔离验收范围、`sc-local-*`、生产租户、通用登录默认不变 |

## 2. 根因

1. 日常只读探针的 `contract` 段要求受管记录身份解析件
   `artifacts/backend/acceptance_record_identity.json`（`make/dev.mk`
   `ACCEPTANCE_RECORD_RESOLUTION` 默认值）。
2. 该解析件由 `verify.dev.acceptance.record_identity.resolve` 生成，入口硬绑
   `DB_NAME=sc_frontend_acceptance`；正式声明
   `config/acceptance/backend_contract_instance_v1.json` 同样绑定该库。
3. 日常档此前没有夹具车道，`sc_demo` 未安装夹具、xmlid 为空，解析件无法生成。
4. 夹具构建器 `frontend_productization_fixture.py` 的 `_guard_acceptance_scope()`
   与 `scripts/common/frontend_acceptance_guard.sh` 原本只接受
   `sc_frontend_acceptance` / `acceptance`，并有一条真实 Odoo 守卫测试
   （`addons/.../tests/test_acceptance_fixture_guard.py`，4 个负例）。

**不放宽既有守卫**；改为新增“声明的日常档范围”，守卫仍对未知范围 / 错库 / 错环境 /
无 flags / 无口令 fail-closed。

## 3. 实现（批次范围）

改动文件与内容哈希（相对 `400948c9`）：

| 文件 | blob |
| --- | --- |
| `addons/smart_construction_acceptance_fixture/tools/frontend_productization_fixture.py` | `76585a9013805fd6eafdd9ac48d48344f7f9030b` |
| `make/dev.mk` | `101b33f873723ed4bcf36d7af92a34eb395fd681` |
| `scripts/ops/dev_acceptance_release_probe.py` | `c3906e7bea0a6c95a434cb355f761bbccacc98b5` |
| `config/acceptance/backend_contract_instance_daily_v1.json` | `6cf7270b7588c98f1bf9cfe6159e47be9288a4d0` |
| `scripts/dev/daily_dev_acceptance_fixture.sh` | `feaae1dd6cf489897e5207d34a5bad0d22636db8` |
| `scripts/verify/test_daily_acceptance_fixture_lane.py` | `55e59616d7fc4d97edf5510caa171d7421163fd3` |

1. **声明范围**：夹具构建器新增 `FIXTURE_SCOPES = {"acceptance": {...sc_frontend_acceptance/acceptance},
   "daily_dev": {"database": "sc_demo", "environment": "dev"}}`、`DAILY_DEV_DB="sc_demo"`、
   `FIXTURE_SCOPE_ENV="SC_ACCEPTANCE_FIXTURE_SCOPE"`。`_guard_acceptance_scope` 按 scope 名解析，
   默认仍为 `acceptance`（对既有行为逐字不变）。
2. **契约口令分离**：`dev_acceptance_release_probe.py` 新增
   `CONTRACT_PASSWORD_ENV="ACCEPTANCE_CONTRACT_PASSWORD"` 与纯函数
   `_contract_credential()`（空则回退登录口令，保持原行为）；`--contract-password` 独立于
   登录/导航账号。
3. **日常声明**：新增 `config/acceptance/backend_contract_instance_daily_v1.json`，仅
   `database=sc_demo`、purpose 说明不同；account / resolution / request / schema_asset /
   required_checks 与正式件逐字一致。
4. **日常夹具入口**：新增 `scripts/dev/daily_dev_acceptance_fixture.sh`（`chmod +x`），
   守卫 `guard_prod_forbid`，要求 `DB_NAME=sc_demo` 与 `SC_ACCEPTANCE_FIXTURE_PASSWORD`，
   导出 `SC_ENVIRONMENT=dev / SC_ALLOW_DEMO_DATA=1 / SC_ACCEPTANCE_FIXTURE_SCOPE=daily_dev`，
   经 `scripts/ops/odoo_shell_exec.sh` 调用 `ensure_fixture`，回读 carrier installed + 10 个
   必需 xmlid，并做 fixture 用户 authenticate 自检。
5. **Make 接线**：`make/dev.mk` 新增默认值与三个目标
   （`verify.daily_dev.acceptance_fixture.unit` /
   `daily.dev.acceptance_fixture.ensure`（需确认 + 先 `mod.install`）/
   `daily.dev.acceptance_contract.resolve`（先 HTTP 校验 `served_sha`，再以 daily scope 生成
   绑定 served SHA 的解析件））；日常探针目标追加转发
   `ACCEPTANCE_CONTRACT_DECLARATION / ACCEPTANCE_RECORD_RESOLUTION /
   ACCEPTANCE_CONTRACT_PASSWORD / ACCEPTANCE_REQUIRE_CONTRACT`。
6. **零测试锁定**：新增 `scripts/verify/test_daily_acceptance_fixture_lane.py`（19 项），
   锁定 scope 解析行为、日常声明形状与绑定、契约口令回退、Make 接线 token。

## 3.1 运行时阻断的两个根因修复（本轮）

PR #548 合入后首次在日常库执行 `make daily.dev.acceptance_fixture.ensure` 失败（rc=2）。
在夹具落库链路上暴露两个相互独立、必须各自在正确责任层修复的缺陷。

### 根因 A（P0 平台机制）：`smart_core` 超用户 `_has_group` 直通污染受众分组

- 现象：创建 `res.users` 时抛
  `ValidationError: 频道成员不能包括公众用户`
  （`mail` 的 `discuss_channel_member` 约束）。
- 定位：`addons/smart_core/models/res_users.py` 的 `_has_group` 对
  `self._uid == SUPERUSER_ID` 无条件返回 `True`。OdooBot（uid 1）因此被
  `res.users._is_public()` 判为公众用户（真实成员关系为否），触发核心约束；
  同一误判也会污染 `res.partner.is_public`、`_is_portal` 与
  `auth_signup` 的 portal 判定。
- 修复：超用户直通保留（SC 能力守卫依赖它），仅把 Odoo 的**受众标记组**
  `base.group_public` / `base.group_portal` 排除，使其继续返回真实成员关系。
  SC 侧无任何代码读取这两个组，能力语义不变。
- 锁定：`addons/smart_core/tests/test_res_users_audience_group_boundary.py`
  （3 项真实 ORM：非受众组的超用户直通仍在、超用户不是 public/portal、
  真实 public/portal 成员仍被识别）。

### 根因 B（P1 夹具责任层）：`sc.payment.execution` 只能以草稿创建

- 现象：越过 A 后，夹具在 `_execution(...)` 处以 `state="paid"/"confirmed"`
  直接创建执行单，抛
  `UserError: 单据必须从草稿通过正式审批和业务动作流转。`
- 定位：PR #525 为 `sc.payment.execution.create` 加了守卫，
  仅 `source_origin="legacy"` + `env.su` + `state="legacy_confirmed"` 的
  受管历史导入可非草稿创建。隔离验收库中的 `FE-*-PE-001` 行是守卫引入前
  落库的持久数据（`source_origin=manual`、`state=paid`、投影显示“已付款”），
  新库无法复现，因此此前未暴露。
- 修复：**不放宽模型守卫**。夹具沿用本文件既有的支付申请冻结范式
  （`_request` 的 ORM 建单 + 工作流事实冻结）：`_execution` 经 ORM 以草稿创建
  可编辑事实，再在该夹具自有的可销毁行上把 `state` 与 `paid_amount`
  作为一个工作流事实冻结，随后 `invalidate_recordset` + `flush_recordset`
  让存储型列表投影从冻结事实重算，并回读校验。
- 锁定：`addons/smart_construction_acceptance_fixture/tests/test_execution_freeze.py`
  （真实链路跑通夹具 helper，断言 `state=paid`、`paid_amount`、
  `partner_payment_status_display="已付款"`、`partner_payment_amount_display`，
  并断言直接非草稿 `create` 仍被守卫拒绝）。
- 接线：`make/dev.mk` 新增
  `verify.smart_core.res_users_audience_group.orm` 与
  `verify.acceptance_fixture.execution_freeze.orm`。

## 4. 离线结果

| 层 | 入口 | 状态 | 测试数 | 证据 |
| --- | --- | --- | --- | --- |
| L2（定向，离线） | `make verify.daily_dev.acceptance_fixture.unit` | PASS | 19 | `.runtime/evidence/daily-dev-acceptance-fixture-lane/fixture_lane_unit.log` |
| L1（迭代） | `make ci.local.iteration` | PASS（dirty，L1-only） | — | 命令输出 |
| L2（定向，ORM） | `make verify.smart_core.res_users_audience_group.orm` | PASS | 3（0 failed / 0 error） | 命令输出 |
| L2（定向，ORM） | `make verify.acceptance_fixture.execution_freeze.orm` | PASS | 1（0 failed / 0 error） | 命令输出 |
| L3（容器内守卫回归） | `make local.dev.test MODULE=smart_construction_acceptance_fixture TEST_TAGS=acceptance_fixture_gate` | PASS | 5（0 failed / 0 error） | 命令输出 |

### 4.1 分层声明与跳过理由

- 风险类别：运维交付工具（新增声明范围 + 受管入口），无产品语义、无 schema 变更。
- 受影响层：夹具范围守卫（P4 工具）、日常探针契约口令、Make 日常车道。
- 已跑的最早必需层：L1 / L2（离线单测 + 容器内既有守卫回归）。
- 未跑 L4（冻结候选浏览器矩阵）：本批次不改前端渲染、不改产品页面，无浏览器表面受影响；
  L4 留给第 5 节的日常运行时受管回执（进程内 odoo shell，不是浏览器矩阵）。
- 未跑全量 `ci.local.quick` 之前：该入口只允许在干净冻结 HEAD 上运行一次，见第 5 节流程。

## 5. 运行时结果（待补）

以下受管入口需在日常运行仓 `sc-root:/opt/projects/repos/sce-product-odoo` 内执行；
本轮尚未运行，禁止在补齐前宣称该 lane 通过：

1. `make daily.dev.acceptance_fixture.ensure`
   （`CONFIRM_DAILY_DEV_ACCEPTANCE_FIXTURE=ENSURE_DAILY_DEV_ACCEPTANCE_FIXTURE`，`DB_NAME=sc_demo`）
2. `make daily.dev.acceptance_contract.resolve`
   （`ACCEPTANCE_TARGET_SHA=<served sha>`）
3. `make verify.daily_dev.acceptance.readonly.probe`
   （期望 `contract` 段 PASS 11/11）

## 6. 未改动 / 排除

- 未放宽审计、断言或负例；未新增环境或凭据权威。
- 隔离验收范围 `sc_frontend_acceptance`、`sc-local-*`、生产租户、通用登录默认不变。
- `rendering_detail_state` 的排除引用既有证据与裁决，不重复证明。

## 7. 四层状态

- 批次验收完成：否（离线通过，运行时回执待补）。
- 主线集成完成：否（本记录尚未合入 `main`）。
- 版本发布完成：否。
- 产品交付完成：否。

## 8. 遗留

- 第 5 节三个受管入口的运行时回执与 `contract` 段结果。
- 日常运行仓是否需先刷新到本批次合入后的 `main`（bundle sync）再执行夹具与解析。
