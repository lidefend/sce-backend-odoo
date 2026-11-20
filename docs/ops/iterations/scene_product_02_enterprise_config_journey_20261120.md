# SCENE-PRODUCT-02：企业配置管理员办理旅程与可用性收口

Base/main: `f2f7fd02f0f28f84e6190102f3bf559db0c28457`

Branch: `feature/scene-product-02-enterprise-config-journey-20261120`

Carried post-merge bookkeeping commit: `74dae16496222bdba07ea67f0fbd5fac550213be`

## 产品结果

企业配置管理员在现有企业初始化入口中，按业务依赖顺序完成企业资料、部门、岗位、人员与账号、同一用户的业务权限及企业场景选择。每条旅程必须有真实对象、提交结果、拒绝或成功反馈、权威回读、返回同一企业和重新诊断。

## 层级与边界

| 项目 | 声明 |
| --- | --- |
| Formal Product Layer | P1/P4 |
| Layer Target | 原生企业配置事实、五类维护入口、企业场景选择及自定义前端消费 |
| Standard vs User-Specific | 施工产品标准与企业运行时配置 |
| Why Here | 组织人事、账号权限和场景选择事实属于 P1 模型；前端只消费其声明 |
| Why Not Elsewhere | 平台只负责建企业和产品发布；P4 不成为业务事实来源，也不扩大权限 |
| Blast Radius | 六个配置入口的输入、拒绝、保存、回读、返回与重新诊断 |

## 运行环境与身份

开工检查结果：

- `make local.dev.health`：PASS，`sc-local-dev / sc_dev_demo`。
- `make local.dev.entry_identity.verify`：PASS，`/t/demo` 与 `ns_000000000002` 绑定 `sc_dev_demo`。
- `make local.dev.verify_authority`：PASS，演示环境模块、财务身份、本位币和税率事实成立。
- `make local.dev.write_lease.status`：`LOCAL_DEV_WRITE_LEASE_FREE`。
- `local.env.status` 的 sample 未启动和主静态入口 404 不影响 persistent local.dev；本批使用候选前端 5176。

精确运行身份：

- 后端源码 revision / 前端构建 revision：`c7de01f85d9fc572ea1c7bbf6d979f93c9c15bce`。
- 配置管理员：`res.users(24)` / `sc_demo_business_config` / 徐磊。
- 当前公司：`res.company(1)` / 四川智汇某某建设集团有限公司。
- 允许公司：`[1]`。
- 候选前端健康同时核对了后端源码挂载、`SC_SOURCE_REVISION`、数据库、dbfilter 和 filestore。

首次登录时，`system.init` 因 `sc_product_policy.business_scene_composition` 列不存在返回 500。先创建受管恢复快照：

```text
artifacts/local-dev/snapshots/20261120T043906Z
```

随后通过写租约执行 `make local.dev.upgrade MODULE=smart_core`，升级成功并恢复：

- 数据库 schema 与当前源码一致；
- `SC_SOURCE_REVISION=c7de01f85…`；
- `/t/demo`、`sc_dev_demo` 和候选前端 5176 健康；
- 登录、`system.init` 和企业初始化页面读取成功。

## 执行顺序

1. C02-01 企业信息：修改、保存、权威回读并返回初始化。
2. C02-02 部门：创建/维护并核对公司、上级和负责人。
3. C02-03 岗位：选择已保存部门并核对唯一编码与关系。
4. C02-04 人员与账号：创建普通内部用户、员工关联、部门和岗位，再修改同一对象并补部门负责人。
5. C02-05 业务权限：对同一用户授予和调整角色/允许公司，使用目标用户核对访问结果。
6. C02-06 企业场景：启用、回读、刷新、撤销/恢复，并区分企业选择、产品可用性和用户访问。

## 当前状态

- `local.dev.health`、入口身份、演示权限、写租约和候选前后端 revision 一致性通过。
- C02-01 在“点击企业信息”处阻断：按钮没有发出请求或改变路由；直接访问 `/a/960?action_id=960` 被前端以 `NAVIGATION_AUTHORITY_DENIED` 拒绝。
- 运行契约中五个入口只声明 `action_xmlid`，而当前执行权限路由没有解析出对应 action/menu。
- 这与未合并的 #950 所修复的 native route discovery 丢失一致。本批依赖 PR #950，当前观察 HEAD 为 `ce1da712e174f002890fdbef8ad7f9320d631060`；不在本分支重复修改同一路由链。
- C02-01 到 C02-05 均未发生业务写入；实际保存、拒绝、回读和用户可用性结论仍为 `not_run`。
- C02-06A 已独立读取：目录返回 92 个源行、0 个可启用业务场景；92 行全部声明 `PRODUCT_RELEASE_UNVERIFIED`、`product_released=false`、`enable_allowed=false`，没有启停动作，因此没有执行场景写入。
- C02-06B 目标用户业务入口可达性未执行，且仍可能依赖 #950 的路由恢复。

## 本批消费修复

- `SceneView` 在办理目录声明存在、但无法解析为当前用户获准目标时，不再静默返回。页面通过现有 `ContractGapError` 错误表面显示入口不可用，并携带缺失契约路径和声明层，不猜测动作 ID、不拼接兜底路由、不发业务写请求。
- `StatusPanel` 优先显示显式传入的契约缺口，不再把已知 `ContractDefectRef` 降级成普通 unknown/permission 状态。
- 场景目录消费者按后端已声明的 `rows`、`row_count` 和 `enablement_blockers` 保留资格诊断。没有可启用场景时，页面显示真实目录数量和启用阻断原因，不再只显示笼统的空目录。

定向验证：

- real `StatusPanel` component 契约缺口渲染与无恢复按钮：通过。
- `verify.frontend.workspace_scenario_lifecycle.unit`：通过，新增目录资格诊断 6 案。
- `verify.frontend.delivery_hardening.guard`：18 项通过。
- `verify.frontend.dev.incremental.unit`：189 项通过。
- frontend lint 仅有仓库既有 warning；strict typecheck 通过。

## 实际浏览器消费结果

候选源码/构建：`a36f24f423148445a30a650d94685cbfc0f2f042`

使用 `sc_demo_business_config`（user 24）/ company 1，在 `sc-local-dev / sc_dev_demo / ^sc_dev_demo$` 的候选前端 5176 执行：

```text
[enterprise_configuration_consumer] PASS entry=contract_gap catalog=blocked_by_declared_qualification rows=92
```

入口反例结果：

- 点击可见“企业信息”后仍停留在 `/s/enterprise.setup`。
- 页面显示“页面执行契约暂不可用”，而不是静默无反馈或普通权限不足。
- 契约缺口为 `scene_ready_contract.scene_internal_actions.enterprise.setup:smart_construction_core.action_sc_enterprise_company`。
- 声明层为 `P0:smart_core:system_init_scene_runtime_surface_builder`。
- 未导航到猜测目标，未发出业务写请求。

五入口只读对账：

| 入口 | XMLID | 当前 action / model | 原生授权 | 原始内部动作 | 最终 `scene_internal_actions` |
| --- | --- | --- | --- | --- | --- |
| 企业信息 | `action_sc_enterprise_company` | 960 / `res.company` | action group、ACL read/write 通过 | 已解析 | 缺失 |
| 组织架构 | `action_sc_organization_department` | 804 / `hr.department` | action group、ACL read/write 通过 | 已解析 | 缺失 |
| 岗位管理 | `action_sc_product_job_management_v1` | 954 / `hr.job` | action group、ACL read/write 通过 | 已解析 | 缺失 |
| 人员与账号 | `action_sc_runtime_user_management` | 807 / `res.users` | action group、ACL read/write 通过 | 已解析 | 缺失 |
| 业务权限分配 | `action_sc_product_data_permission_v1` | 957 / `res.users` | action group、ACL read/write 通过 | 已解析 | 缺失 |

结论：稳定 XMLID 和原始内部动作解析成立，原生授权未阻断；阻断发生在最终 effective delivery 输出/消费边界。该 P0 生产链仍归 #950，当前候选只在消费端显式报告缺口。

C02-06A 结果：

- 目录契约：`scenario_activation_catalog.v1`。
- `row_count=92`，`business_scenarios=0`，`actionable_count=0`。
- 92 项全部为 `PRODUCT_RELEASE_UNVERIFIED`，`product_released=false`，`enable_allowed=false`。
- 页面明确显示“场景目录共 92 项，启用阻断：PRODUCT_RELEASE_UNVERIFIED。”，不再伪装成无目录。
- 没有可执行启停动作，因此未写入场景选择；C02-06B 目标用户访问验证继续 `not_run`。

运行证据：

- `.runtime/agent-runs/SCENE-PRODUCT-02-ENTERPRISE-CONFIG-JOURNEY-20261120/enterprise-configuration-consumer/report.json`
- SHA-256：`2c56d2176d9fa1b1ea9fed63eb1cee8dd789efcbb2920ff58e7d261b37ec822a`
