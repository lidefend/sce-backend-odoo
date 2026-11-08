# Smart Core 请求作用域缓存与关系入口性能收口

## 身份

- 原 PR：#834
- 原候选：`ac7a858fd394563347baa805055cf546727a91f2`
- 当前 main 基线：`cf2afc2a127036ee6e75b0d355ada157c1455c0d`
- 独立分支：`fix/smart-core-request-cache-performance`
- Formal Product Layer：P0
- Layer Target：`smart_core` request-scoped identity cache、投影源失效与关系入口候选收缩
- Standard vs User-Specific：平台工程标准

## 对账结论

PR #834 的 Renderer、金额表达、Semantic Registry、前端 Guard、测试和旧文档均由
#839/#840 及后续主线实现取代，不进入本候选。仅提取以下 7 个 `smart_core` 文件：

1. `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py`
2. `addons/smart_core/delivery/runtime_route_authority.py`
3. `addons/smart_core/tests/__init__.py`
4. `addons/smart_core/tests/test_load_contract_response_cache.py`
5. `addons/smart_core/tests/test_principal_group_signature_request_scope.py`
6. `addons/smart_core/tests/test_principal_group_signature_request_scope_orm.py`
7. `addons/smart_core/utils/load_contract_response_cache.py`

另有一项 P4 增量验证映射：

- `scripts/verify/frontend_dev_incremental.py`
- `scripts/audit/verification_lane_dispositions.json`
- `scripts/verify/unified_page_contract_v2_assembler_guard.py`
- `scripts/verify/test_coverage_registry.yaml`
- `make/dev.mk`

这些文件只负责把后端路径映射到已有非零 L2 target、移除
`verify.product.entry_publication.unit` 的“零引用”历史 disposition、
登记真实 ORM tag 并补充主线已有的覆盖登记缺口；不承载产品语义，
也不引入旧 PR 的前端守卫。

真实 ORM 测试通过
`make verify.smart_core.principal_group_request_scope.orm`
登记为 on-demand Odoo tag，复用一次性 `local.test/sc_test` 身份，
避免只留下不可重复执行的测试声明。

由于 `load_contract_response_cache.py` 是 assembled-contract 的输入，本候选
同时提升 `ASSEMBLED_CONTRACT_CACHE_VERSION` 到
`...-v32-request-cache-identity`，并按 guard 重新绑定输入摘要，防止旧装配契约
继续被服务。对应产品文件为
`addons/smart_core/handlers/ui_contract_v2.py`。

## 审计中修正的问题

旧候选把 `sc.business.category.name` 当作非投影元数据，但
`PageAssembler._inject_business_category_form_policy` 会把该值发布为
`business_form_policy.category_name`。独立候选将 `name` 纳入 source token，
并分别验证：

- `name` 变化会使契约投影缓存失效；
- `sequence`、`note` 等非投影元数据变化不会产生无效抖动。

## 边界

- 不回退当前 Renderer Extension Protocol。
- 不恢复 `utils/money.ts` 或 `businessValuePresentation.ts` 的第二实现。
- 不恢复旧 Semantic Registry 或前端 expression guard。
- 不修改 PR #834 的历史。
- 不部署。

## 验证

### L0/L1/L2

- `python3 addons/smart_core/tests/test_load_contract_response_cache.py`：PASS，51 tests。
- `python3 addons/smart_core/tests/test_principal_group_signature_request_scope.py`：PASS，4 tests。
- `make verify.business_config.formal_list.unit`：PASS，281 tests。
- `make verify.product.entry_publication.unit`：PASS，34 tests。
- `make verify.frontend.relation_entry.contract_guard`：PASS，24 tests。
- `make verify.contract.entry_equivalence.guard`：PASS，10 tests。
- `make verify.frontend.dev.incremental.unit`：PASS，81 tests。
- `make verify.unified_page_contract.v2.assembler`：PASS，契约缓存输入摘要与版本已重新绑定。
- `make verify.verification.lane_coverage`：PASS，73 tests，冻结验证面未扩大。
- `make verify.test.coverage.registry`：PASS，211 tag groups；新增 ORM tag 已登记为 on-demand。
- `make verify.baseline.iteration.execution.policy`：PASS，19 tests。
- `make verify.agent.ledger.unit`：PASS，18 tests。
- `make verify.agent.resume.unit`：PASS，56 tests。

### L3 真实 ORM

- `make local.test.test MODULE=smart_core TEST_TAGS=principal_group_request_scope_orm`：
  PASS，3 tests。证明真实 Odoo cursor 可被 `WeakKeyDictionary` 持有，同 cursor
  稳定、新 cursor 独立计算。
- `make verify.smart_core.relation_entry_publication.orm`：PASS，12 tests。
  覆盖隐藏父链、未发布菜单、已发布回退、创建 ACL 和关系入口 override。

## 缓存键与生命周期分析

- memo 的弱引用键是 `env.cr`，不是用户、进程或数据库名。
- memo 内层键是 `(uid, sorted(group_ids))`；同 cursor 下用户或组集合变化仍会重算。
- Odoo 17 `odoo.sql_db.Cursor` 没有 `__slots__` 且声明了 `__weakref__`，可被
  `WeakKeyDictionary` 引用；真实 ORM 测试已实际通过。
- cursor 随请求事务结束回收，弱引用条目随之释放，不跨请求复用。
- 契约投影缓存键独立包含 `company_id` 与排序后的 `allowed_company_ids`。
- 路由权限缓存键还显式包含 `env.company.id`；发布路由按公司作用域再次过滤。

## `sc.business.category` 失效字段矩阵

| 字段 | 进入 source token | 理由 |
| --- | --- | --- |
| `code` | 是 | 分类解析键、关系入口与契约元数据身份 |
| `name` | 是 | 发布为 `business_form_policy.category_name` |
| `target_model` | 是 | 分类绑定目标模型并进入契约元数据 |
| `active` | 是 | 决定默认搜索是否命中分类 |
| `form_policy_json` | 是 | 生成字段策略、分组、必填和只读投影 |
| `required_fields_json` | 是 | 生成 REQUIRED 校验与字段标记 |
| `default_values_json` | 是 | 生成关系切换与默认清空字段 |
| `sequence` | 否 | 不改变契约载荷；动态选择顺序不属于本缓存内容 |
| `note` | 否 | 非投影元数据 |
| `domain_json` / `ledger_policy_json` | 否 | 下游动作与账务策略，不属于页面契约投影 |
| `visible_groups_json` / `attachment_policy` / `approval_policy_id` | 否 | 当前页面契约组装不消费 |

记录集合仍使用安全的宽范围绑定（同一模型全部类别）。字段矩阵最小化，记录范围
偏保守但没有正确性缺口；按 `target_model` 进一步缩窄属于后续性能优化，不阻断本批。

## ACL、公司与关系入口

- 候选菜单首先受 `ir.ui.menu._visible_menu_ids()` 约束。
- 每个候选还校验完整父链可见、菜单组、动作组以及模型的 create/read/write
  `check_access_rights`。
- 仅当 `(menu_id, action_id)` 同时属于当前 principal 的发布路由 authority 时才
  声明 `can_open=true`；原生可见但未发布菜单不会扩大入口。
- 目标动作必须精确匹配关系字段的 `res_model`，并继续排除非记录打开型 action。
- 发布 authority 的缓存键包含公司；未知或不匹配公司身份不会复用另一公司的发布面。

## 既有失败排除

`make verify.form_structure_authority_unification.unit` 运行 253 tests、1 failure：
测试仍期望合同首组标题 `身份与基本资料`，当前主线 XML 已提交为 `合同身份`。
该失败已在主 `main` worktree 原样复现，并已由
`docs/architecture/backend-owned-page-composition/159-stage3c-03c-02b-compatibility-regression.md`
登记为既有排除项。相关 XML 与测试不在本候选范围，本批不修改，以免扩大历史产品化范围。

## 缓存版本

- `ASSEMBLED_CONTRACT_CACHE_VERSION`：
  `ui-contract-v2-native-persisted-relation-dependencies-v32-request-cache-identity`
- `ASSEMBLED_CACHE_INPUTS_SHA256`：
  `da8d2230990aa061bfd3c88cf4b3aaad62e2625f1d2cd94eca30511a98dc8a76`

## 性能证据

当前没有可比较的精确前后基准；本批优先证明缓存正确性、生命周期和权限边界。
不把缺少性能数字伪装成已验证的性能收益。

## 回退

通过受保护 PR revert 本独立候选。本批不改变数据库、fixture、部署或持久运行配置。
