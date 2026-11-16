# NATIVE-SCENE-01 / P0-2 · Action-bound Search View Contract

Status: implementation and focused verification complete; final exact-head CI and
independent review pending.

Date: 2026-11-16

Baseline: `3c7682647352cdf52b790e9a46b893e2535be77d`

Predecessor: P0-1 / PR #905.

## 1. 边界

- Formal Product Layer：P0 platform kernel product。
- Layer Target：`PageAssembler`、`app.view.config`、`app.search.config` 的
  Action-bound Search View 投影，以及 Unified Page Contract V2 的协同 Decoder。
- Module：`addons/smart_core` 与通用 Web Contract Decoder。
- Standard vs User-Specific：平台通用原生语义，不含行业、客户或角色特例。
- Why Here：Search View 身份、Action 绑定、缓存隔离和权限裁剪对所有 Odoo
  业务模块具有相同语义，必须由 P0 平台统一投影。
- Why Not Elsewhere：不在 P1/P2/P3 为付款或项目复制 Search 解析；不让前端
  猜测 Action 与 Search View 关系；不在 Renderer 内修补契约缺口。
- Blast Radius：带 Window Action 的页面装配、Action Search View 解析、
  `searchContract.nativeIdentity`、V2 schema/Decoder、Search 缓存身份及相关验证登记。
- Exclusions：Native Action Contract 根节点、Occurrence、Widget、Renderer、
  Gantt/Calendar/Dashboard、新业务模型、数据库、部署、P0-3、P0-4、P0-5。

## 2. 原生事实与调用链

Odoo 原生事实没有被重新定义：

- `addons/smart_construction_core/views/core/payment_request_views.xml:440-477`
  的付款 Action 明确声明 `search_view_id=view_payment_request_search`。
- `addons/smart_construction_core/actions/project_native_action_overrides.xml:8-42`
  的项目 Action 明确绑定 `view_project_project_search_sc_business`。
- `addons/smart_core/app_config_engine/services/resolvers/action_resolver.py:59-106`
  保留 `search_view_id` 和 `search_view_xmlid`。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:2382-2429`
  对 `subject=model + action_id/xmlid` 同样通过 `ActionResolver` 取得完整 Action
  身份，避免 P0-1 修复过的绕过路径重新出现。

当前链路为：

```text
ir.actions.act_window.search_view_id
  -> ActionResolver.as_action_info()
  -> PageAssembler._resolve_search_view_projection()
  -> app.view.config._safe_get_view_data(..., "search")
  -> app.search.config._generate_from_search()
  -> searchContract.nativeIdentity
  -> UiContractHandler / Unified Page Contract V2
  -> frontend decodeContractV2Snapshot()
```

## 3. 实现结果

### 3.1 纯 Search identity

`addons/smart_core/core/native_action_search_view.py:7-60` 新增确定性身份构造：

```json
{
  "model": "payment.request",
  "actionId": 123,
  "viewId": 456,
  "viewXmlId": "module.view_search",
  "authority": "action_search_view",
  "sourceLocator": "ir.actions.act_window.search_view_id"
}
```

仅接受以下两种权威：

- `action_search_view`：来自 Action `search_view_id`；
- `model_default_search_view`：无 Action 绑定时来自模型原生 Search View。

Action authority 必须有正 Action ID 和已解析 View ID；未知 authority 直接拒绝。

### 3.2 Action-bound 解析与 fail-closed

- `addons/smart_core/app_config_engine/models/app_view_config.py:117-180`
  在解析 Search View 时优先使用当前 Action 的 `search_view_id`，并验证 View 的
  model/type 与请求模型一致。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:419-488`
  解析并校验最终 Search View；Action 声明 ID 与实际解析 ID 不一致时抛出
  `ACTION_SEARCH_VIEW_IDENTITY_MISMATCH`，不会静默回退到模型默认 Search View。
- 同一入口区分两种合法事实：
  - Action 显式声明 Search View 却没有解析出持久化 View ID：继续 fail closed；
  - 无 Action 的模型级 `get_view(view_type="search")` 返回 Odoo 生成的 arch，
    但 Odoo 没有解析出持久化 View ID：保留 Search arch/profile，返回空的
    `nativeIdentity`，不伪造 View ID。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:750-772`
  只把当前 Action 对应 Search View 的数据和 native identity 传给
  `app.search.config`。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:920-931`
  内部 Action identity 同时保留 `search_view_id` 与 `search_view_xmlid`。

本轮真实 CI 进一步定位了长期 Search View 异常的根因：`PageAssembler` 同时接收
`ActionResolver` 标准字典、Action recordset 和 Odoo `record.read()[0]` 结果。
many2one 在 `read()` 的传输表示是 `(id, display_name)` tuple，而 Search 投影
原先假定它是整数；旧 Resolver 对 tuple 又会静默得到 ID 0。结果是部分入口看起来
正常，但 Search 已丢失 Action binding 并退回模型默认视图。

根因修复复用 Odoo 自身的表示边界：

- `addons/smart_core/app_config_engine/services/resolvers/action_resolver.py:40-54`
  `_related_id()` 统一处理 scalar、recordset、dict 和 many2one tuple。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:2435-2473`
  新增 `_canonicalize_page_action()`；完整 Action/View Set 已提供时直接复用，
  不重复查库；缺少完整身份时才通过现有 `_resolve_action_from_payload()` 回表补齐。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:504-509`
  所有 PageAssembler Action 入口统一走该规范化边界。

当前请求面没有独立的“受权 Search View 覆盖”参数；`requested_view_id` 只用于
当前 Activity View 候选校验。因此本阶段不虚构新的预览覆盖协议，也不允许普通
客户端通过 `requested_view_id` 改写 Action Search View。授权 Search View
覆盖若后续确有产品入口，应作为新的受管协议单独设计，而不是在 P0-2 私自增加参数。

### 3.3 缓存隔离

- `addons/smart_core/app_config_engine/models/app_search_config.py:58-164`
  `_generate_from_search()` 接收当前原生 Search identity。
- `:133-147` Action-bound Search profile 强制走 transient projection，不写入
  model 级 `app.search.config` 单例缓存。
- `:168-208` `get_search_contract()` 在运行时深拷贝上发布同一
  `nativeIdentity`，保留 filters、group_by、fields、favorites 和 defaults 语义。

这避免了同一模型两个 Action 使用不同 Search View 时互相污染；纯 Model
投影仍保留原有模型级行为。

### 3.4 V2 契约与前端 Decoder 协同

- `docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json:255-355`
  新增严格 `searchContract.nativeIdentity` 定义和 `$defs/searchNativeIdentity`，
  关闭额外字段并限定两种 authority/sourceLocator。
- `addons/smart_core/core/contract_lifecycle.py:12-17`
  将 schema SHA256 重钉为
  `e9994018c00dbdd841bb2f18474e3cafad6fdf74f1f6caf1b62f67981e1fd678`。
- `frontend/apps/web/src/app/contracts/v2/schema.ts:2525-2556`
  Decoder 接受并保留 `nativeIdentity`；未知 Search Contract 字段仍 fail closed。
- `scripts/verify/contract_v2_render_authority_matrix.py`
  将其登记为不直接渲染的原生身份/来源证明，并同步生成
  `contract-v2-render-authority-matrix-v1.json`。

契约版本仍为 `2.2.0`。这是现有 `searchContract` 的向后兼容语义增量；
Native Action Contract 根节点与 schema `2.3.0` 仍属于未启动的 P0-3。

### 3.5 验证层边界

本专项的核心验收对象是后端返回的 `ui.contract.v2` 契约正确性，而不是像素外观：

- `addons/smart_core/controllers/intent_dispatcher.py:312-313` 提供统一
  `/api/v1/intent` 入口；
- `addons/smart_core/handlers/ui_contract_v2.py:1222-1233` 由后端装配完整
  UCP V2 契约，`:1450-1483` 返回契约及来源、缓存和耗时元数据；
- `frontend/apps/web/src/app/contracts/v2/client.ts:122` 只对响应执行
  `decodeContractV2Snapshot()`，`schema.ts` 是契约 Decoder，不是页面表现实现。

因此 `frontend/apps/web/src/app/contracts/v2/**` 的变更只要求
`frontend_contract`，不再错误触发 `frontend_presentation` 浏览器证据。
`config/acceptance/evolution_binding.v1.json` 新增独立
`frontend-contract-v2-codec` 规则，`test_acceptance_evolution_binding_guard.py`
锁定该分类。页面浏览器证据只在布局、组件、Renderer 或真实用户交互改变时保留。

## 4. 测试覆盖

纯身份单测 `scripts/verify/test_native_action_search_view.py:16-87` 覆盖：

- Action authority、XMLID、source locator；
- model-default authority 不含 Action ID；
- Action authority 必须同时具有 Action ID 和 View ID；
- 非法 authority 拒绝；
- 缺失 XMLID 不伪造值。

`addons/smart_core/tests/test_native_action_search_view_integration.py:8-227` 通过
`ActionDispatcher -> PageAssembler` 覆盖：

- Action-bound Search View 身份与 filter；
- 同模型两个 Action 保持两个 Search View 和各自 filter；
- 无 Action 的纯 Model 投影标记 `model_default_search_view`；
- Action Search View 模型错误时 fail closed；
- Action Search 投影不写 model 级缓存；
- 非系统用户的受限 filter 被运行时裁剪，同时 Action Search identity 保持不变。
- 原始 `record.read()[0]` Action 的 many2one tuple 在 PageAssembler 边界被正确规范化。
- 无 Action 且 Odoo 未解析出持久化 Search View ID 时，保留生成 arch 并省略
  `nativeIdentity`，不构造虚假身份。

## 5. 验证回执

通过的验证：

- `make verify.native_action.search_view.unit`：5 tests。
- `make verify.native_action.search_view.orm`：8 tests。
  Receipt：`.runtime/test-baseline/1794825114476741506/receipt.json`。
- `make test.payment-settlement.component-profile.orm`：PASS，7 tests；
  真实付款执行/收入结算/支出结算 Action 和 Search View 全链路通过。
- `make local.test.test MODULE=smart_core TEST_TAGS=native_action_search_view,native_action_view_set,action_dispatcher`：
  31 tests。
  Receipt：`.runtime/test-baseline/1794825197986822863/receipt.json`。
- `make verify.frontend.contract_record_action_state.unit`：29 checks，含
  native identity 保留、数组拒绝和未知 Search 字段拒绝。
- `make verify.frontend.contract_v2_render_authority.unit`：335 fields，
  unclassified=0。
- `make verify.frontend.dev.incremental.unit`：156 tests。
- `make verify.unified_page_contract.v2.assembler`：PASS，4 sources，缓存 v57。
- `make verify.backend.contract_lifecycle.authority`：PASS，schema digest 与 4
  examples 一致，authority guard L4 100/100。
- `make verify.verification.lane.coverage`：PASS，74 tests。
- `make verify.test.coverage.registry`：PASS，19 tests。
- `make verify.native_scene.inventory.unit`：PASS，2 tests。
- `make verify.agent.ledger.unit`：PASS，18 tests。
- `make verify.agent.resume.unit`：PASS，58 tests。
- `make verify.frontend.typecheck.strict`：PASS。
- `python3 addons/smart_core/tests/test_contract_projection_json_boundaries.py`：
  PASS，4 tests。
- `make verify.docs.all`：PASS。
- `make verify.acceptance.evolution.binding`：PASS，72 tests；
  `contracts/v2/**` 经 `frontend-contract-v2-codec` 只要求
  `frontend_contract`。

测试证据限制：

- Odoo receipt 的干净来源身份是 baseline HEAD `3c7682647` 加声明的 dirty
  source fingerprint；它不是 clean candidate SHA。
- Search ORM 使用 disposable `sc-local-test/sc_test`，不等于真实业务数据库验收。
- 本轮没有执行浏览器或真实业务角色验收，因此 L3/L4 不因 Decoder/ORM 通过而升级。

## 6. 失败分类与修复

- 首次 ORM 测试假设省略 Action search binding 会得到无绑定结果；真实 Odoo
  自动解析模型默认 Search View。分类：`validation_tool_defect`。修正为用真正的
  Action-free model dispatch 验证 `model_default_search_view`。
- UCP Decoder 固定白名单会拒绝后端新增 `nativeIdentity`。分类：
  `product_defect`（跨层契约未协同）。同步 schema、Decoder、digest、examples 和
  focused test 后通过。
- render-authority 矩阵发现 8 个既有 schema 字段未登记。分类：
  `baseline_evidence_defect`。逐项确认 Decoder/消费者用途后补登记，没有放宽断言。
- schema 变更后 lifecycle digest 与 4 个 example 摘要仍是旧值。分类：
  `baseline_evidence_defect`。通过唯一权威 schema SHA 和受管生命周期守卫收口。
- 新增映射使 render-authority target 成为可达目标，但旧 lane disposition 仍把它
  登记为零引用。分类：`baseline_evidence_defect`。使用受管
  `--unregister-target --reason` 注销陈旧登记，未修改冻结阈值或扩大豁免。
- 回执批跑脚本未启用 `errexit`，在 native inventory 因实现记录新增而出现 stale
  manifest 后仍继续登记了错误的 PASS。分类：`validation_tool_defect`。该错误回执
  已用原始失败日志覆盖为 failed；重新生成 inventory 后，
  `verify.native_scene.inventory.unit` 和 `verify.docs.all` 以新的 begin/record
  非零通过，未删除或改写失败事实。
- 远端 `professional_quality_gate` 首次失败：真实付款/结算测试把
  `read()[0]` Action 直接传给 PageAssembler，`search_view_id` many2one tuple
  进入 Search 投影并触发 `TypeError`。分类：`product_defect`。修复没有在 Search
  子层猜类型，而是统一 Action 入口并补强 `ActionResolver._related_id()`；随后专项
  ORM 7/7 和同一付款/结算真实 ORM 7/7 均通过。
- candidate 页面预检中，`project.responsibility` 的模型级 Form 请求返回 HTTP 400
  `native search identity requires a resolved view id`。Odoo 能为该模型生成 Search
  arch，但没有持久化 Search View ID；P0-2 把“没有 ID”错误等同于“身份非法”。
  分类：`product_defect`。修复只放宽无 Action 的模型级生成 Search arch，
  Action 显式绑定仍 fail closed；新增专项回归，缓存指纹升级到 v57。
- 同一失败也暴露验证分层缺口：既有 L1/L2 用例只证明“收到无 ID arch 时如何分支”，
  没有证明真实 Odoo 模型会产生这一输入；既有页面证据又没有先校验新的 exact
  contract receipt。该缺口不通过增加相邻单元测试解决。本轮继续使用 L2 定向回归，
  并在精确 candidate 上执行 `ui.contract.v2(project.responsibility/form)` 的真实
  HTTP receipt，直接证明完整契约输出；页面表现不是本专项的验收对象。

## 7. L1-L4 状态

- L1 原生事实：PASS。Action `search_view_id`、XMLID、模型和 View type 有真实源码
  与 Odoo ORM 证据。
- L2 后端契约：PASS（本阶段范围）。身份、filter 语义、缓存隔离、fail-closed 和
  schema 摘要已有非零测试。
- L3 前端实际消费：PARTIAL。严格 V2 Decoder 已证明保留 `nativeIdentity` 并拒绝
  未知字段；尚未执行浏览器页面和真实 Action 切换。
- L4 真实业务验收：NOT RUN。未使用真实付款/项目角色、真实数据、浏览器操作和
  权限拒绝业务闭环；不能把 ORM 权限负例冒充 L4。

## 8. 下一步

1. 在最终未改动候选上重跑 `make ci.local.iteration` 和完整
   `make verify.contract.architecture.suite`。
2. 提交并发布 P0-2 独立 PR，绑定精确 HEAD 的远端必需 CI。
3. 停止在 P0-2 独立审核检查点；审核通过并另行调度后才进入 P0-3。

Rollback：回滚 P0-2 提交即可；没有数据库 schema、持久化业务数据或部署变更。
