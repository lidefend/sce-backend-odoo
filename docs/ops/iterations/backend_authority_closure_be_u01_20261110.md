# BE-U01 Backend Authority Closure

状态：本地批次验收完成；主线集成、部署和租户运行验收未执行。候选分支
`codex/be-u01-authority-map-20261110`，固定主线
`1ad805b621de6ced0a497c5a5f6e10bec358896d`。

## 目标

BE-U01 不新建能力平台、场景引擎或审批引擎。它先以普通查询、真实审批和平台职责三条
后端样本固定事实、发布、启用、运行投影和服务端执行的实际权威，并把结论变成源码绑定
的离线守卫。

机器可读结果：`docs/architecture/backend_authority_closure_map_v1.json`。

## 层与范围

- `Formal Product Layer`：P4，支撑 P0/P1 源码事实。
- `Layer Target`：后端权威映射与源码锚点守卫。
- `Module`：`docs/architecture`、`scripts/verify`、`make`、`.agent`。
- `Why Here`：BE-U01 固定责任关系，不改变业务运行。
- `Why Not Elsewhere`：本批没有前端、数据库、ACL、页面或业务方法变更。
- `Blast Radius`：三条声明样本、一个离线 Make 入口和当前批次记录。

## 当前源码发现

映射登记了五个交叉点，分别归属 BE-U02 至 BE-U05。特别是：

- `permission.check` 的 `allow=true` 不能当作业务执行授权；
- 租户配置管理员仍可绕过通用 intent 组门槛及付款审批 handler 组门槛；
- 菜单派生 `capability_key` 仍只具备入口兼容身份，不能证明能力资格；
- 场景发布仍使用发布者当前可见集合构造版本；
- 行业 finalize 后置钩子仍可直接改变页面。

这些结论来自固定源码，不替代租户数据库运行验收。

## 验证

| 检查 | 结果 |
| --- | --- |
| `make verify.backend.authority_closure.unit` | PASS，6 tests；三条映射、源码锚点和负例一致 |
| `make verify.agent.ledger.unit` | PASS，18 tests |
| `make verify.agent.resume.unit` | PASS，56 tests |
| `make verify.verification.lane_coverage` | PASS，73 tests；结构覆盖，不等于功能验收 |
| `make verify.frontend.dev.incremental.unit` | PASS，105 tests；新守卫和测试有专属路由 |
| `make ci.local.iteration` | PASS；受影响 7 个目标全部真实执行且退出为零 |

提交钩子按既有生成证据机制刷新了复杂度预算、拆分队列、测试清单和清单摘要。差异只为新增守卫与
测试增加条数和行数，不改变业务断言；这些生成载体已纳入本批范围。

第一次映射校验失败来自本批映射语义：投影阶段误填 `authorizes`，执行候选被误声明为事实消费。
第一次增量规划失败来自 P4 路由缺口：新守卫和测试未映射到自身目标。两者均已按责任层修复并重跑；
原始失败日志保留在 `.runtime/`，未改写为通过。

通过只表示三条映射和源码锚点一致，不表示 U02-U06 已修复，也不表示产品已发布、部署或
租户数据库已验收。

## 回退

回退 BE-U01 提交即可。该批不改业务数据、ACL、契约运行结果、数据库结构或部署产物。
