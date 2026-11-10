# BE-U02 Authorization Boundary

状态：本地批次验收完成；主线集成、部署和租户用户验收未执行。候选分支
`codex/be-u02-authorization-boundary-20261110`，基线为
BE-U01 候选 `6bba76043ffdee0474a0f91f3390634c6b792180`。

## 目标

BE-U02 不新增权限引擎。它统一两个已有判断：

- `REQUIRED_GROUPS` 继续采用原生的任一组语义；
- 租户配置管理员只在显式配置 intent 上保留配置职责，不再自动通过付款、审批、
  结算引入、风险动作或待办完成等业务命令。

`permission.check` 保留 `allow` 兼容字段，但明确标记为产品可用性投影，并返回
`does_not_authorize`，避免被消费者误读为数据或执行授权。

## 层与范围

- `Formal Product Layer`：P0，支撑 P1 业务入口。
- `Layer Target`：intent 组门禁、配置 intent 范围、产品可用性投影。
- `Module`：`smart_core`、`smart_construction_core`。
- `Why Here`：组门禁属于平台机制；业务入口应由所属行业处理器持有来源条件。
- `Why Not Elsewhere`：本批不改前端、数据库、ACL、记录规则、发布或页面契约。

## 预期行为

| 场景 | 结果 |
| --- | --- |
| 普通业务 intent + 配置管理员身份，无业务组 | 拒绝 |
| 已声明配置 intent + 配置管理员身份 | 保留配置职责 |
| 付款审批 + 配置管理员身份，无财务组或审批任务来源 | 拒绝，单据不变 |
| `permission.check.allow=true` | 只表示订阅/功能开关可用 |
| 有模型 ACL 但缺少业务组 | 仍由 intent 组门禁拒绝 |

## 验证

| 检查 | 结果 |
| --- | --- |
| `make verify.backend.authority_closure.unit` | PASS，7 tests；G02/G03 的源码锚点与禁止旁路断言一致 |
| `make verify.intent_group.authorization.unit` | PASS，25 tests；配置 intent 保留职责，普通业务 intent 不再接受配置管理员旁路 |
| `make verify.permission_check.availability.unit` | PASS，2 tests；`allow` 与 `does_not_authorize` 同返回 |
| `make verify.payment.authorization_boundary.orm` | PASS，7 tests；配置管理员审批请求被拒绝，单据不变 |
| `make verify.verification.lane_coverage` | PASS，73 tests；结构覆盖，不等于功能验收 |
| `make verify.frontend.dev.incremental.unit` | PASS，106 tests；U02 路径均有专属目标 |
| `make ci.local.iteration` | PASS，affected targets=10；付款 ORM 在 `sc-local-test/sc_test` 上重新执行并 7/7 通过 |

第一次映射校验失败来自 U01 台账锚点尚未随 U02 行为更新，已改为正向语义和禁止 token 双向校验。
第一次 `ci.local.iteration` 失败来自两个现已接线的目标仍保留零引用 disposition；已按审计要求移除
陈旧登记，没有放宽 baseline。失败日志保留在 `.runtime/`。

提交钩子刷新了测试覆盖 registry、复杂度预算和拆分队列；这些生成差异只描述新增测试选择与文件规模，
不改变产品断言，已纳入本批范围。

覆盖限制：付款域的真实 ORM 已验证；风险动作、待办完成、结算引入和付款执行由源码守卫 +
通用 intent 组单测覆盖，本批没有为每类业务再建浏览器旅程。前端无需业务特判。

## 回退

回退 BE-U02 提交即可。本批不改变数据库结构、ACL、记录规则、发布内容或部署产物。
