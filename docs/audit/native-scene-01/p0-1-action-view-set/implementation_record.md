# NATIVE-SCENE-01 / P0-1 · Action identity and effective View Set

Status: independent-review remediation implemented; exact-head re-review and remote CI pending.

Date: 2026-11-16

Baseline: `375dc9ac2ced2d21872fd55d60feb52f6ffec53f`

Predecessor design: PR #904.

## 1. 边界

- Formal Product Layer：P0 platform kernel product。
- Layer Target：`ActionResolver`、`PageAssembler` 的 Action/View identity。
- Module：`smart_core`。
- Standard vs User-Specific：平台通用机制，不含行业或客户差异。
- Why Here：Action identity、有效 View 顺序和请求校验属于所有业务模块共享的
  P0 投影规则。
- Why Not Elsewhere：不需要 P1/P2/P3 配置或前端判断；不在 Renderer 中修补。
- Blast Radius：`ir.actions.act_window` 进入页面装配的路径，以及显式 Action View ID
  请求；数据库、模型和业务方法不变。
- Exclusions：Search Contract、Native Action Contract wire schema、Occurrence、前端消费、
  Widget、专业 Renderer、组合场景、数据库和部署。

## 2. 实现结果

### 2.1 纯 View Set 投影

新增：

- `addons/smart_core/core/native_action_view_set.py:1-5`
  明确 Odoo effective `action.views` 是唯一顺序权威。
- `addons/smart_core/core/native_action_view_set.py:61-90`
  数组化每个 Action View，保留 `actionViewSequence`、View ID、surface role。
- `addons/smart_core/core/native_action_view_set.py:93-140`
  以 effective `views` 为主；`view_mode` 只补足缺失类型。
- `addons/smart_core/core/native_action_view_set.py:143-219`
  校验请求 View 必须命中 Action 候选；授权覆盖必须显式传入。
- `addons/smart_core/core/native_action_view_set.py:34-44`
  只接受已核验预览链写入的严格布尔内部标记；普通 token 或客户端布尔值不构成授权。

关键行为：

- 同类型多个 View 不再压成 `{type: viewId}`。
- `defaultViewType/defaultViewId` 取有效序列第一项。
- `form` 标记为 `record_detail` 且不可作为集合切换项。
- `list` 归一为 `tree`。
- Action View Set 中没有 Menu/Scene 字段。

### 2.2 ActionResolver 身份完整化

- `addons/smart_core/app_config_engine/services/resolvers/action_resolver.py:59-106`
  将有效 `action.views`、默认 View、Action Search View ID 和 XMLID 标准化。
- `addons/smart_core/app_config_engine/services/resolvers/action_resolver.py:183-214`
  `as_action_info()` 对 record/dict 输出统一身份。
- `addons/smart_core/app_config_engine/services/resolvers/action_resolver.py:252-279`
  `normalize_action_dict()` 使用同一投影。

输出包括：

```text
view_id
view_type
view_mode
views[]                 # effective order
view_set
search_view_id
search_view_xmlid
```

Search View ID 本轮只传递和保留，不消费；Search Contract 闭环属于 P0-2。

### 2.3 PageAssembler 请求约束与内部载体

- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:368-402`
  验证显式请求 View 是否为 Action 候选。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:551-583`
  在显式 View ID 进入 `get_view()` 前执行候选校验。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:2295-2342`
  `subject=model + action_id/xmlid` 通过现有 `ActionResolver` 重建完整 Action
  身份和 View Set；Action 无法解析、类型错误、模型不一致或 View Set 不完整均
  fail closed。没有 Action 身份的纯 Model 请求仍保持原有模型级投影。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:828-838`
  在 `ui.contract` 源中加入内部 `action_identity` / `action_view_set` 载体。

授权覆盖只来自现有：

- `addons/smart_core/handlers/ui_contract_preview.py:43-82`
  `build_projection_environments()` 完成 token owner、company、
  database、role、state 和 expiry 校验后写入的
  `native_action_view_override_authorized=true` 内部标记。
- 普通 context 中的 token、原始布尔键或 `contract_view_override_authorized`
  均不构成授权；无有效预览时现有校验链会主动清除该标记。

新增 helper 不自行授权。

### 2.4 Assembled Contract 缓存身份

- `addons/smart_core/handlers/ui_contract_v2.py:97`
  将 assembled contract 缓存版本提升为
  `ui-contract-v2-demand-driven-snapshot-v52`。
- `scripts/verify/unified_page_contract_v2_assembler_guard.py:32,81`
  同步重钉缓存版本和输入摘要
  `636df7bd...6f8d`，防止 Action/Page 装配语义变化后继续命中旧契约。

### 2.5 独立复核 P0 修复

独立复核发现 `subject=model + action_id` 会走 PageAssembler 自身的 Action
读取路径；该路径原先只返回 ID、名称、Domain、Context 和 target，没有返回
`view_set`，导致显式 View ID 校验被跳过。

修订后：

- `subject=model + action_id/xmlid` 复用 `ActionResolver` 的完整 Action
  identity/View Set。
- 请求显式 View ID 时，已绑定 Action 但 View Set 不完整会直接拒绝。
- 不存在的 Action 不再静默退化为纯 Model 页面。
- 真正的纯 Model 请求在没有 Action 身份时仍保持可用。
- 已核验预览可覆盖；客户端伪造内部标记会被现有预览环境构建链清除并拒绝。

全链路测试通过 `ActionDispatcher.dispatch()` 覆盖 action 与 model 两种入口，
不只测试静态 helper。

## 3. 真实 Odoo 验证发现

初始集成测试预期 `pivot` 必须由 `view_mode` 补足，但真实 Odoo `action.views`
已经包含无显式 View ID 的 `pivot` 项。

因此修正为：

- 真实 `action.views` 完整包含的 view type 不再补足；
- `view_mode` 只补 Odoo 有效序列缺失的类型；
- 测试预期改为 `supplementedViewTypes=[]`。

这是本轮必须遵守有效 `action.views` 的直接运行证据。

## 4. 测试与回执

### 纯定向

- `make verify.native_action.view_set.unit`：PASS，9 tests。
- `python3 addons/smart_core/tests/test_ui_contract_id_boundaries.py`：PASS，9 tests。
- `python3 -m py_compile ...`：PASS。

### Odoo 集成

- `make verify.native_action.view_set.orm`：
  PASS，13 tests。
- Receipt：
  `.runtime/test-baseline/1794813496607387067/receipt.json`
- `make local.test.test MODULE=smart_core TEST_TAGS=native_action_view_set,action_dispatcher`：
  PASS，23 tests。
- Receipt：
  `.runtime/test-baseline/1794813078176202246/receipt.json`

覆盖：

- Odoo effective `action.views` 顺序。
- duplicate same-type view candidate。
- Action XMLID、view ID/type、search view ID。
- Action identity 二次标准化不丢失 view/search 身份。
- Action identity 不含 Menu/Scene。
- 请求 View 候选和拒绝。
- `subject=model` 已绑定/未绑定 View、无 Action 纯 Model、无效 Action。
- 已核验预览覆盖与客户端伪造标记拒绝。
- 已核验预览授权、未验证 context 标记清除和独立 override 路径。
- `ActionDispatcher → PageAssembler` 内部身份载体。

### 测试覆盖登记

- `scripts/verify/test_coverage_registry.yaml:713-720` 将
  `native_action_view_set` 登记为受管 on-demand Odoo tag。
- `make verify.test.coverage.registry`：PASS，19 tests。
- `make test.coverage.registry.export`：PASS，快照已更新。
- `scripts/verify/frontend_dev_incremental.py` 将新增 Action/View 路径映射到
  unit、Odoo ORM、UCP V2 assembler 和 entry-equivalence 四个非零目标。
- `make verify.frontend.dev.incremental.unit`：PASS，155 tests。
- `make verify.unified_page_contract.v2.assembler`：PASS，缓存 v51 已重钉。
- `make verify.contract.architecture.suite`：PASS，完整契约/架构套件。
- `make verify.docs.all`：PASS，文档、链接及 inventory 同步。
- `make ci.local.iteration`：PASS。
- Receipt：
  `.runtime/frontend-dev-validation/executions/20261116T071808Z-1594342-389223411/receipt.json`
- `make ci.delivery.freeze.prepare`：PASS；仅同步新增测试与文件计数相关的四份
  `docs/engineering_convergence/` 生成报告。

### 失败分类

第一次 Odoo 运行：

- 结果：0 tests；
- 分类：`validation_tool_defect`；
- 原因：新测试未在 `addons/smart_core/tests/__init__.py` 注册；
- 修复：注册模块后重跑。

扩展 `native_alignment` 运行：

- 92 tests，2 existing failures；
- 失败：
  - `test_reason_code_registry_separates_legacy_business_reason_provider`
  - `test_release_navigation_legacy_fallback_marks_leaf_source`
- 分类：非本批次受影响路径；依赖未安装的 construction/release navigation 数据。
- 处理：不修改失败测试、不放宽断言；本轮正式受影响集合使用
  `native_action_view_set,action_dispatcher` 并已非零通过。

本地增量入口第一次运行：

- 结果：`validation_tool_defect`；
- 原因：新增 P0-1 路径未登记到增量影响映射；
- 修复：登记四个精确受管目标并增加 planner 单测。

本地增量入口第二次运行：

- 结果：`product_defect`；
- 原因：PageAssembler/Action 输入变化后，V2 assembled-contract 缓存身份仍为 v50；
- 修复：缓存版本提升至 v51，并重钉 assembler guard 的输入摘要；
- 受影响入口：`make verify.unified_page_contract.v2.assembler` 已非零通过。

独立复核修复第一次 Odoo 运行：

- 结果：12 tests，3 errors，ORM guard 判失败；
- 分类：`product_defect`；
- 原因：新局部导入的相对路径多了一层，运行时找不到 ActionResolver；
- 修复：改为同级 services 路径后重跑，13 tests PASS。

## 5. 当前状态

- L1 原生 Action/View 事实：已验证。
- L2 后端 identity/contract 投影：已实现并通过定向 Odoo 测试及本地增量门禁。
- L3 前端消费：本轮未变，仍待 P0-5。
- L4 真实业务角色：未执行。

本阶段未新增数据库模型、未修改业务数据、未修改 Renderer。
