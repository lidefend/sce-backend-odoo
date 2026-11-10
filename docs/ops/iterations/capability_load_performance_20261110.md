# 启动能力装载性能独立修复（2026-11-10）

## 批次身份

- 基线：`main@d014af2e8309f8b4d5dfa55a94967474ad83941f`
- 分支：`fix/capability-load-performance-20261110`
- 层级：P0 平台机制 + P1 能力投影消费
- 状态：`verification_pending`

## 目标

减少同一次 `system.init` 内对发布路由权威、场景 XMLID 和公司路由作用域上下文的重复
解析，并透传已有能力阶段耗时。对外能力行、ACL、发布集合、导航身份和入口目标语义保持
不变。

## 输入证据

未改动主线的完整本地发布链在 delivery-hardening 性能门禁失败：

- 登录中位数 `14160 ms`，预算 `3000 ms`
- My Work 中位数 `10402 ms`，预算 `1200 ms`
- 公司切换中位数 `8764 ms`，预算 `2000 ms`
- `load_capabilities_for_user` 占 `system.init` 约 `10.7-11.0 s`

原始结果：

- `.runtime/agent-runs/MAIN-CONVERGENCE-20261110/release-main-d014af2-run2.log`
- `artifacts/frontend-delivery-hardening/performance.json`
- `artifacts/frontend-release-audit/report.json`

## 影响分析与边界

变化的输入是平台启动能力投影中的重复权威解析。受影响对象限：

- capability startup provider 的 timing hook 传输
- P1 capability registry 的 published route/action 映射
- scene capability entry target 的 XMLID 解析
- company route scope 的请求/进程内上下文构建

不受影响：

- 前端产品代码和性能预算
- ACL、角色、公司作用域、发布集合及其判定结果
- 业务数据、fixture、数据库和部署
- 完整发布长链、PR、合并

提交钩子按仓库规则刷新并由本批次承载的生成型 P4 证据：

- `docs/engineering_convergence/complexity_budget_report.md`
- `docs/engineering_convergence/split_plan_queue.md`

## 验证阶梯

1. L0：分支、基线、dirty scope 与 run 注册。
2. L1：能力 provider 静态守卫、语法检查、针对性纯测试。
3. L2：`TestQueryCapabilityNativeAcl` 真实非零 ORM 用例。
4. L3：按变化需要在已登记 local/test profile 上做能力启动剖面回读。
5. 完整长链：`not_run`，本批次按要求暂停长链收口。

## 结果

### 已通过

- `python3 -m py_compile`：能力 provider、P1 registry、scene target、policy 与测试文件通过。
- `verify.agent.ledger.unit`：18 tests PASS。
- `verify.agent.resume.unit`：56 tests PASS。
- `verify.capability.provider.guard`：PASS。
- `verify.navigation.publication.consumers.unit`：170 tests PASS。
- `TestQueryCapabilityNativeAcl.test_cached_published_query_pairs_match_legacy_first_match`：PASS。
- `TestQueryCapabilityNativeAcl.test_capability_list_resolves_published_route_authority_once`：PASS。
- `TestQueryCapabilityNativeAcl.test_company_route_scope_context_is_reused_within_process_bucket`：PASS。
- `TestQueryCapabilityNativeAcl.test_registry_timing_hook_reaches_startup_provider`：PASS。
- `verify.frontend.acceptance_login_probe.unit`：新增有界认证就绪重试测试。

### 已修复的验证前置

- 首轮 `verify.daily.permission_truth.capability.orm` 中 2 项失败，原因是测试类
  隐式依赖业务场景已经启用；全新 `local.test` 也复现，排除了持久库污染。
- 修复放在测试夹具：对只验证原生 ACL 的两项用例显式注入已发布
  `(menu_id, action_id)`，不改写 `allow` 预期，也不放宽产品判定。
- 修复后 `verify.daily.permission_truth.capability.orm`：14 tests PASS。

### 未运行

- 完整发布长链：按要求暂停。

### 聚焦性能结果

`verify.frontend.delivery_hardening.release.performance_probe` 在
`b121f66de6ec20e7cea11301b03789e3323f04aa` 上 PASS：

| 场景 | 中位数 | P95 | 预算中位数 | 结果 |
| --- | ---: | ---: | ---: | --- |
| 登录到可交互 | 2051 ms | 2234 ms | 3000 ms | PASS |
| My Work | 440 ms | 486 ms | 1200 ms | PASS |
| 付款详情 | 373 ms | 402 ms | 1200 ms | PASS |
| 结算详情 | 326 ms | 343 ms | 1200 ms | PASS |
| 实付详情 | 251 ms | 309 ms | 1200 ms | PASS |
| 新建表单 | 1218 ms | 1328 ms | 1600 ms | PASS |
| 公司切换 | 1457 ms | 1576 ms | 2000 ms | PASS |

登录启动剖面中，`load_capabilities_for_user` 已从 `10.7–11.0 s` 降至 `15 ms`；
其中 published route authority 为 `2 ms`，能力循环访问/状态判定为 `1 ms`。

原始证据：

- `.runtime/agent-runs/CAPABILITY-LOAD-PERF-20261110/performance-probe-clean-b121f66de.log`
- `.runtime/agent-runs/CAPABILITY-LOAD-PERF-20261110/performance-env-readback.log`
- `artifacts/frontend-delivery-hardening/performance.json`
- `artifacts/frontend-delivery-hardening/performance.json` SHA-256:
  `abb078ea83591515b92165f02135b52a184da8fe610ac952f7c59821f2963e62`

### 验证工具问题

- `make ci.local.iteration` 在路由阶段阻断，原因是 8 个 backend capability 路径未被
  frontend incremental planner 映射。已补最小 P4 映射：
  capability provider/registry/scene target -> capability ORM；
  product policy/场景测试 -> capability ORM + navigation publication；
  登录探针 -> 本批次认证就绪单测。
- clean commit 的性能探针在生产构建后立即发起 HTTP 登录，遇到一次无结构
  `401 {"code":"unknown","error_code":"unknown"}`；数秒后单独重放为 HTTP 200。
  这是认证就绪窗口，不是凭据错误。修复为只对 unknown/空错误码的 401 做最多 10 次、
  0.5 秒间隔的有界重试；结构化拒绝立即失败，并改走既有
  `acceptance.runtime.login_probe` 受管入口。
- 性能探针此前在 fixture/snapshot 之前解析记录 ID，浏览器实际打开时 fixture 已完成
  重建，造成旧 ID 404。修复为 backend/frontend 启动完成后、浏览器采样前重新解析
  runtime targets，确保 URL 身份来自当前数据库状态。

原始日志：

- `.runtime/agent-runs/CAPABILITY-LOAD-PERF-20261110/agent-ledger.log`
- `.runtime/agent-runs/CAPABILITY-LOAD-PERF-20261110/agent-resume.log`
- `.runtime/agent-runs/CAPABILITY-LOAD-PERF-20261110/capability-provider-guard.log`
- `.runtime/agent-runs/CAPABILITY-LOAD-PERF-20261110/navigation-publication.log`
- `.runtime/agent-runs/CAPABILITY-LOAD-PERF-20261110/capability-registry-orm.log`

## 回退

回退本性能专题提交即可；本批次不改变持久配置、业务数据或部署状态。
