# 自定义前端字段语义单一权威（P0 表达收口）

日期：2026-09-21
状态：开发候选验证通过，待独立只读复核与合并授权
分支：`feature/frontend-field-semantics-authority-v1`
基线：`origin/main@f9c73588210937dcce8fb96e1e736fe0eef0bf37`（开始与冻结前工作区干净）

## 1. 交付结论

自定义前端此前把「同一字段语义」在 8 处以上各写一份：`utils/display.ts`（记录／详情路径）、
`pages/listPage/listCellPresentation.ts` 与 `pages/ListPage.vue`（集合路径）、`utils/semantic.ts`、
`app/contracts/actionViewActivityContract.ts`、`app/contracts/actionViewAnalysisContract.ts`、
`app/presentation/collectionStatusPresentation.ts` 以及各区块组件。结果是同一条记录在列表与详情可以给出不同取值：
数值列空值在集合显示 `0`、在记录显示 `-`；日期在集合被格式化为 `2026-09-21 10:17`、在记录／表单直接泄漏
机器格式 `2026-09-21T10:17:01Z`；附件引用检测在集合缺少 `/web/content/` 分支。

本批建立唯一权威模块 `frontend/apps/web/src/utils/fieldSemantics.ts`：字段类型归一与分类、空值判定、
布尔与空值文案、数值解析与格式化、日期／时间解析与两档呈现、附件引用检测全部集中于此；上述 18 个消费方
改为只消费该权威，不得再自行分支。守卫同时把「权威之外不得出现空值／布尔文案字面量、不得各自重写附件检测与
日期解析」写成可执行断言。

## 2. 架构边界

- Formal Product Layer：**P0** 前端通用表达机制；本记录与守卫脚本属 **P4**。
- Layer Target：`frontend/apps/web` 共享取值呈现与集合单元格表达。
- Module：`frontend`。
- Standard vs User-Specific：平台通用机制，不承载施工行业事实、客户偏好或低代码运行配置。
- Why Here：字段类型归一、空值口径、数值／日期／附件呈现，是列表与记录共用渲染器的共同职责，必须只有一处权威。
- Why Not Elsewhere：不改契约 schema、字段权限、状态动作或业务取值；不在前端推断模型或字段名；不改原生视图、
  fixture、数据库、Compose/profile、端口或凭据；不新增 token authority 或渲染主链。
- Blast Radius：集合单元格取值、记录／表单字段取值、活动面与分析面单元格取值、场景区块取值呈现。
  业务字段顺序、分区、权限、状态动作与写链路不变。

## 3. 变更范围

新增：

- `frontend/apps/web/src/utils/fieldSemantics.ts`：唯一权威。导出 `normalizeFieldType` 与类型分类、
  `isEmptyFieldValue`、`FIELD_VALUE_EMPTY_TEXT`／`FIELD_VALUE_TRUE_TEXT`／`FIELD_VALUE_FALSE_TEXT`、
  `numericFieldValue`／`formatNumericFieldValue`、`formatTemporalFieldValue`（`compact`｜`full` 档）、
  `containsAttachmentReference`／`containsAttachmentReferenceIn`、`ATTACHMENT_REFERENCE_URL_SOURCE`、
  以及登记的 `COLLECTION_NUMERIC_EMPTY_TEXT`。

改为只消费权威（18 文件）：

- 记录／详情与共享展示：`utils/display.ts`、`utils/semantic.ts`。
- 集合：`pages/listPage/listCellPresentation.ts`、`pages/listPage/listColumnWidth.ts`、`pages/ListPage.vue`。
- 业务面与状态面：`app/contracts/actionViewActivityContract.ts`、`app/contracts/actionViewAnalysisContract.ts`、
  `app/presentation/collectionStatusPresentation.ts`、`pages/contractForm/one2manyUtils.ts`、
  `pages/contractForm/RelationSearchDialog.vue`、`views/ActionView.vue`、
  `components/action/ActionSurfaceToolbar.vue`。
- 区块与场景：`components/page/blocks/BlockRecordTable.vue`、`BlockMetricRow.vue`、
  `BlockRecordSummary.vue`、`BlockAccordionGroup.vue`、`components/scene/SceneBlocksRenderer.vue`、
  `views/SceneContractBlockGridView.vue`。

守卫与生成物：

- `scripts/verify/frontend_localized_display_contract_test.ts`：新增跨面一致性行为断言与非重复化源码断言
  （遍历 `frontend/apps/web/src` 下 `.ts`／`.vue`／`.js`，排除权威自身，禁止空值／布尔文案字面量与重写的
  附件检测、日期解析正则）。
- `scripts/verify/action_view_responsibility_map_guard.py` 与
  `docs/engineering_convergence/action_view_responsibility_map.md`：`ActionView.vue` 行数锁按既有 Stage
  约定重基线 `<=3769` → `<=3770`（新增 Stage 9 Re-baseline 段；唯一增量是权威 import 一行，等价改写不引入
  任何职责、副作用或编排分支）。
- `docs/engineering_convergence/complexity_budget_report.md`、`split_plan_queue.md`：
  L1 重生成（扫描 4404 → **4405**；`ActionView.vue` 3769 → **3770**；`ListPage.vue` 2135 → **2123**；
  `ActionSurfaceToolbar.vue` 1040 → 1041）。
- `docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json`：
  经 `make refresh.frontend.component_driver_takeover.inventory` 刷新（新增模块改变源码摘要）。

## 4. 统一后的口径

| 语义 | 统一前 | 统一后 |
| --- | --- | --- |
| 空值文案 | 记录路径 `-`；集合／活动／分析路径 `--` | 全部 `--`（`FIELD_VALUE_EMPTY_TEXT`） |
| 布尔文案 | `display`／`semantic`／列表／活动／分析各一套字面量 | 全部 `是`／`否`（契约 `uiLabel` 仍可覆盖） |
| `date` | 集合 `2026-09-21`；记录直出原值 | 两路径均 `2026-09-21` |
| `datetime` | 集合 `2026-09-21 10:17`；记录直出 `2026-09-21T10:17:01Z` | 集合 `compact`＝`2026-09-21 10:17`；记录／表单 `full`＝`2026-09-21 10:17:01`（同一解析规则，声明式档位） |
| 数值 | 列表与记录各自 `toLocaleString` 分支 | `zh-CN`，`integer` 0 位、`float`／`monetary` 2 位 |
| 附件引用检测 | 集合缺 `/web/content/` 分支 | 同一模式，含 `/web/content/` |
| 集合数值列空值 | 隐式分支 `'0'` | 保留 `0`，登记为 `COLLECTION_NUMERIC_EMPTY_TEXT` 声明式集合密度策略，不擅自改变 |

`datetime` 的档位差异是**声明式**的：集合为列表密度用 `compact`，记录／表单为保留秒用 `full`，两者共用同一解析
函数；这不是各写一套。若产品要求两档一致，应在权威层改档位，而不是在页面重新分支。

## 5. 验证证据

- `make verify.frontend.localized_display.unit`：**PASS**，回执
  `FRONTEND_FIELD_SEMANTICS_AUTHORITY=PASS sources=685` 与 `FRONTEND_LOCALIZED_DISPLAY_CONTRACT=PASS`。
- 非空守卫实测：向 `utils/semantic.ts` 注入 `'--'` 字面量后守卫**失败**
  （`utils/semantic.ts 不得自行定义空值文案`，退出码 1），随即回滚；守卫非空。
- 集合类：`verify.frontend.collection_row_cell.unit`、`verify.frontend.collection_navigation_controls.unit`、
  `verify.frontend.list_optional_columns.unit`、`verify.frontend.collection_view_semantics.unit`：**PASS**。
- 表达与专业面：`verify.frontend.primitive_adapter.unit`、`verify.frontend.navigation_shell.unit`、
  `verify.frontend.product_page_header.unit`、`verify.frontend.product_page_pattern.unit`、
  `verify.frontend.professional_component_registry.unit`、`verify.frontend.professional_base_field.unit`、
  `verify.frontend.professional_business_value.unit`、`verify.frontend.professional_relation_field.unit`、
  `verify.frontend.professional_detail_collection.unit`、`verify.frontend.professional_workflow.unit`、
  `verify.frontend.professional_collaboration.unit`、`verify.frontend.prompt_action_presentation.unit`、
  `verify.frontend.action_view_page_actions.unit`、`verify.frontend.relational_action_primitives.unit`、
  `verify.frontend.state_dashboard.unit`、`verify.frontend.mobile_viewport.unit`、
  `verify.frontend.form_header_action_primitives.unit`、`verify.frontend.low_code_field_create_dialog.unit`、
  `verify.frontend.official_icon.unit`、`verify.frontend.global_component_capability.unit`、
  `verify.frontend.component_driver_takeover.unit`（刷新生成物后）：**PASS**。
- `scripts/dev/pnpm_exec.sh -C frontend/apps/web lint:src`：**0 error**（39 条既有风格 warning）。
- `vue-tsc --noEmit`（全 `src`，非门禁口径）：本分支与基线 `main@f9c73588` 均为 **32** 条错误、错误文件集合
  一致；逐条核对 `SceneContractBlockGridView.vue` 为 `L169-173 → L170-174`、`L211 → L212` 的整体 +1 行位移
  （即本批新增的 import 行），错误码不变，**零新增类型错误**。
- L1 `make ci.delivery.freeze.prepare`：**PASS**，`ci.generated_evidence.preflight` PASS。
- exact-head `make ci.local.quick` 第 1 次运行**抓到本批自身缺陷并已在本批内修复**：
  `action_view_responsibility_map_guard` 报 `ActionView.vue line budget exceeded: 3773 > 3769`。
  该守卫不在 L1 preflight 与 `verify.frontend.*` 集合内，是精确候选上的 L5 才暴露的行数锁。处置为把本批改动的
  布尔标签分支压回单行等价写法（唯一增量为权威 import 一行，3770），并按既有 Stage 约定重基线
  `<=3770`（Stage 9 段 ＋ 守卫 token／budget 同步更新），不使用「抬预算掩盖增长」的写法：本次增量是单一
  import，不是新增职责。修复后该守卫、其余 L5 步骤与 L1 全部 **PASS**。

## 6. 排除项与残限

- `verify.frontend.scene_component_bridge.guard` 失败（`collaboration region must follow the normalized runtime
  capability or subordinate node authority`）：已在干净基线 `main@f9c73588` 用同一命令复现同一消息，
  判定为**本批之前的既有失败**，不在本批范围，不修、不掩盖。
- `vue-tsc --noEmit` 全域 32 条类型错误为既有类型债（`tsconfig.json` 自述 `LEGACY_TYPE_DEBT`；门禁使用
  `typecheck:strict` 的窄覆盖），本批不扩大清理。
- 技术／诊断只读面（`layouts/AppShell.vue` 研发上下文、action_view HUD、`ReleaseOperatorView`、
  `SceneHealthView`、business-config 审计面板、contract form 技术 meta 行）仍使用单破折号 `-`。这些呈现的是
  机型标识与治理字段而非业务取值，故**显式排除**在权威口径外；守卫只约束 `--` 与布尔文案，不与之冲突。
- 记录／表单路径的 `datetime` 由直出 ISO 改为 `full` 档，属可见表达变化；本批以单元与源码守卫证明口径统一，
  尚未做浏览器运行态复核（见 §7）。
- **已登记但本批未改动**：`pages/contractForm/one2manyUtils.ts` 的 `one2manyColumnDisplayValue` 仍自带
  `datetime`（`Intl.DateTimeFormat('zh-CN')` → `2026/09/21 10:17`）与数值（最多 6 位小数）两条本地分支。
  原因：该函数同时充当内联单元格**输入框**的 `model-value`（`components/template/One2ManyCellEditor.vue`
  以 `:type="one2manyColumnInputType(column)"` 绑定），并入权威的记录／表单呈现档位会改变可编辑行的取值显示；
  且其 `datetime` 分支产出并非 `datetime-local` 输入可接受的格式，疑为既有缺陷。需单独决策 ＋ 运行态复核后另批处理，
  本批不擅自改动（不掩盖、不静默统一）。

## 7. 未做与下一步

- 未执行受管运行态浏览器复核（`local.dev` 候选 + 只读页面证据）。本批不改业务语义与写链路，但 `datetime`
  档位变化属可见表达变化；若准入要求运行态证据，应按既有 `local.dev` 口径补一次只读代表面抽验。
- 未改动集合数值列空值 `0`、`many2one` 元组归一、集合列宽采样等已登记口径。
- Next Step：冻结本批 HEAD → exact-head `make ci.local.quick` 回执 → 两轮独立只读复核 → 显式合并授权 →
  `make pr.push`／`pr.create`／`pr.ready`／`pr.merge` → 主仓库 `make main.sync` → `make branch.cleanup.feature`。
