# 表单结构消费稳定化（2026-09-17，用户产品复核后机制批次）

## 0. 批次定位

用户在 G02 第二轮产品复核后判定：体系尚未达到「迁移一个页面，不再反复修共享渲染」的稳定程度。本批次暂停新增迁移组（台账保持 42），转为「表单结构消费稳定化」集中验收。已完成的发票工作保留，不推倒重做。

四个工作包：A 结构职责统一；B 呈现与动作规则统一；C 低代码与约束兼容；D 机制回归与退出条件。

三个执行边界：先归因再修改（定位唯一责任层，不靠前端猜模型/清边框修补）；复用现有机制（不加第三套章节树/展示模式/成功兜底）；一次集中收口（执行器自查代表场景 → 用户集中浏览器复核，修复后仅补验受影响部分）。

## 1. 责任链（五层）

```
原生声明(P1 view arch/锚点) → 配置合成(view_orchestrator compose) → 字段适配(并集补齐/规则投影) → 渲染(前端 native tree) → 样式(NativeFormTreeRenderer CSS)
```

## 2. 归因（每项定位唯一责任层）

| 问题 | 现象 | 唯一责任层 | 根因 |
|---|---|---|---|
| 计算副本重复（G02 已静态修复） | note 等业务事实在表单呈现 2 次 | 字段适配（并集补齐） | 「四配置字段并集」以字段保留代替业务事实正确呈现；无副本排除机制 |
| 动作权威与承载错位（G02 已静态修复） | 快捷筛选等列表查询混入办理正文 | 渲染（动作块门控） | 用「原生结构权威」推断动作展示，但权威来源与动作承载位置不是同一概念 |
| 空 header 占位 | 无内容 header 渲染 border-bottom + padding | 渲染（容器过滤） | filterVisibleNativeLayoutNodes 只过滤不可见节点，不修剪过滤后空容器 |
| 嵌套 group 边框叠加 | sheet>布局包装group>业务章节group 双线 | 样式（章节装饰归属） | .native-container--group 无条件 border-top，布局包装（无锚点/无标题）也画章节分隔线 |
| 测试只验节点不验页面 | 全绿但页面视觉结构错误 | 验收断言 | 断言停留在节点/字段/错误计数，缺空容器、装饰归属、值级重复等页面级断言 |

## 3. 职责矩阵（工作包 A/B 落点）

| 结构层 | 声明方 | 消费方（P0 通用规则） | 职责规则 |
|---|---|---|---|
| 页面外壳（form/sheet） | P1 原生 view arch | 渲染器 | 唯一正文容器；不产生标题、导航、装饰；过滤后空壳不占位（prune） |
| 布局包装（无锚点无标题 group） | P1 原生 arch（Odoo 列布局惯例） | 渲染器 `native-container--group--layout` | 只排布列；不产生章节标题、导航项、分隔线；空壳修剪 |
| 业务章节（data-sc-anchor group） | P1 原生声明 | 渲染器 nativeBusinessSectionIdentity | 章节标题与分隔线的唯一归属层；导航项来源；正文与导航共用同一有效树（nativeFormLayoutNodes） |
| 页签（notebook/page） | P1 原生 arch | 渲染器 | 跨页签导航；空页签修剪 |
| 关系明细（x2many/button_box/chatter/header 按钮与 statusbar） | P1 原生声明 | 编排器 subordinate 保留（_merge_semantic_surface_with_native_subordinates） | 关系集合与动作能力不与字段并集；保留在从属容器 |
| 动作区 | 原生 header + 契约动作声明 | 渲染器 suppressFormActionBlocks | 动作承载位置=页面外壳动作区；承载意图（契约 formStructureAuthority=native_authority）或承载事实（useNativeFormTree）任一成立即关闭旁路动作占位块；查询筛选只存在于列表页 |

字段事实规则（B）：canonical 字段是表单唯一正文呈现；存储计算展示副本按 `FORMAL_DISPLAY_COPY_SOURCES` 注册（业务层声明、共享层 duck-type 消费 `_display_copy_source_fields` 协议），合成层两处防御——`_apply_form_spec` 并集补齐排除副本、`semantic_anchors` 声明副本直接拒绝（NATIVE_SEMANTIC_SURFACE_DISPLAY_COPY）。副本的存储、API、列表列消费者全部保留。

分隔线归属（B）：章节边界分隔线（border-top）只归业务章节；布局包装无线（`native-container--group--layout` 置零）；页面外壳与正文边界（header border-bottom）归外壳职责。同一章节边界无重复分隔。

机制审查补充（本轮新增约束，工作包 A/B/D）：

- P0 共享层只消费显式通用语义：副本识别的唯一入口是业务层 `_display_copy_source_fields` 协议；禁止按模型名、字段后缀（`*_display`）或字段形状猜测副本。
- P1 声明必须可举证：登记副本需同时满足三条（同记录单源实时投影／在正文外保有独立职责／canonical 在同一表单 arch 共现）。承担独立历史快照、格式表达或摘要职责的同源字段不登记、不删除。
- 同一事实允许在列表、正文、审计等不同场景各自表达；禁止的是同一上下文内的无意义重复。
- 原生结构权威只证明正文结构归属，不能单独证明动作已有承载位置：动作占位块仅在某动作确已由原生树或渲染出的 header 动作行承载时才关闭；未承载的动作键必须继续上报（`uncarriedActionKeys`）。

## 4. 修改清单

> 身份：分支 `feature/uc4-invoice-native-lowcode`，HEAD `025e37d2`，工作树 dirty（15 modified + 4 untracked = 19 条路径），未提交、未冻结。
>
> 归属口径（同一工作树同一时刻只有一个写入者；本批次写入方 = 本会话执行体）：
> - **接管前已有**：本会话第一次 `git status` 时已在工作树的改动，逐项复核后原样保留，未覆盖、未重做。
> - **接管前段**：同批次在接管之前写下的新增内容（接管时已在工作树内，但属本批新增，不是历史遗留）。
> - **接管后修改**：接管之后本轮写下的改动。
> - **仅验证**：只执行入口、不改代码。
>
> 口径纠正：上一版交回写「唯一由我写入的文件是批次记录」，与「本批新增多个机制文件并执行 L1–L4」自相矛盾。准确口径是——**接管前已有改动 + 接管前段新增 4 个新文件；本会话（接管后）对代码的写入为 0，唯一写入是本文档本身**。本轮之后的新增写入会在 §4.0 按「接管后修改」追加。

### 4.0 逐路径归属表（34 条）

> 本表为首次接管的快照。第 3 次接管后的归属与计数以 §8.7 为准（工作树 36 条 = 29 modified + 7 untracked）。

| # | 路径 | 归属 | 内容 |
|---|---|---|---|
| 1 | `addons/smart_core/core/view_orchestrator.py` | 接管前已有 | 协议消费 `_display_copy_source_fields` + 副本锚点拒绝 + 并集排除 |
| 2 | `addons/smart_construction_core/models/core/formal_config_contract_fields.py` | 接管前已有 + 接管前段 | 注册表/mixin/发票 4 副本（前）；三条件注释、`payment.request` 与 `sc.material.inbound` 各 1 条登记、三模型挂载 mixin（接管前段） |
| 3 | `addons/smart_construction_core/tests/test_invoice_native_lowcode.py` | 接管前已有 | +2 机制测试 |
| 4 | `frontend/apps/web/scripts/formal_form_invoice_journey.mjs` | 接管前已有 | +`assertStructureResponsibility` |
| 5 | `frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue` | 接管前已有 + 接管前段 | 修剪/章节判定/字段 schema 判据（前）；委托共享判定（接管前段） |
| 6 | `frontend/apps/web/src/pages/contractForm/nativeLayoutUtils.ts` | 接管前已有 + 接管前段 | `pruneEmptyContainers`（前）；导出 `isLayoutOnlyGroupContainer`（接管前段） |
| 7 | `frontend/apps/web/src/pages/contractForm/useRecordFormLayout.ts` | 接管前已有 | 正式路径启用修剪 |
| 8 | `docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json` | 接管前已有 + 接管前段 | `inputDigest`（经既有生成入口刷新） |
| 9 | `frontend/apps/web/src/pages/ContractFormPage.vue` | 接管前段 | `actionPlaceholderGate` + 新 props 绑定 |
| 10 | `frontend/apps/web/src/pages/contractForm/ContractFormActionBlocks.vue` | 接管前段 | `suppressWorkflowTransitions` / `suppressBodyActions` 细粒度门 |
| 11 | `frontend/apps/web/src/pages/contractForm/formActionPlaceholderGate.ts`（新） | 接管前段 | 动作承载证明门控 |
| 12 | `addons/smart_construction_core/tests/test_form_structure_consumption.py`（新） | 接管前段 | 5 例后端机制测试 |
| 13 | `addons/smart_construction_core/tests/__init__.py` | 接管前段 | 注册新测试模块 |
| 14 | `frontend/apps/web/scripts/native_form_structure_responsibility_test.ts`（新） | 接管前段 | 8 例前端行为测试 |
| 15 | `make/frontend.mk` | 接管前段 | 新 target + 纳入 `verify.frontend.quick.gate` |
| 16 | `docs/frontend_productization/rendering-detail/component-professionalization-inventory-v1.json` | 接管前段 | 生成物刷新 |
| 17 | `docs/frontend_productization/rendering-detail/official-design-alignment-inventory-v1.json` | 接管前段 | 生成物刷新 |
| 18 | `docs/frontend_productization/rendering-detail/visual-projection-inventory-v1.json` | 接管前段 | 生成物刷新 |
| 19 | `docs/ops/iterations/form_structure_consumption_stabilization_20260917.md`（新） | 接管后修改 | 本批唯一活记录 |
| 20 | `frontend/apps/web/scripts/formal_form_lowcode_loop.mjs` | 接管后修改 | L4 最小诊断（URL／截图／DOM／console／pageerror／请求结果／恢复状态，均脱敏）＋ 应用外壳挂载预检与单次传输恢复 ＋ 只读重放模式 |
| 21 | `scripts/verify/local_dev_form_lowcode_browser.sh` | 接管后修改 | 透传 `FORM_LOWCODE_REPLAY`／`FORM_LOWCODE_REPRESENTATIVE`（仅启用只读路径，不改身份/数据库/端口/卷/凭据）；既有草稿前后比对 fail-closed（§8.2） |
| 22 | `addons/smart_core/model/ui_business_config_change_set.py` | 接管后修改 | `_current_payload_hash()`：变更集条目序列化改为与 stage 守卫同一哈希基准（见 §6.1.2 P0 修复） |
| 23 | `addons/smart_core/tests/test_business_config_change_set.py` | 接管后修改 | 新增 `test_resumed_draft_restages_with_served_payload_hash`（往返一致性 + 守卫仍拒绝真过期） |
| 24 | `frontend/apps/web/scripts/designer_draft_ownership.mjs`（新） | 接管后修改 | 草稿归属判定与越权守卫纯函数（§8.2） |
| 25 | `frontend/apps/web/scripts/formal_form_designer_journey.mjs` | 接管后修改 | 只释放本次运行打开的 change set；复用草稿改为保留并记录（§8.2） |
| 26 | `scripts/verify/local_dev_form_lowcode_scope.py` | 接管后修改 | 只读代表路由注册（§8.4）＋ 设计器目标可复用草稿清单 `designer_drafts`（§8.2） |
| 27 | `frontend/apps/web/scripts/formal_form_representative_journey.mjs`（新） | 接管后修改 | 代表面只读旅程（§8.4） |
| 28 | `frontend/apps/web/src/pages/contractForm/ContractFormPage.css` | 接管后修改 | 章节分隔线归属：布局包装组不画线（唯一产品代码修复） |
| 29 | `docs/frontend_productization/rendering-detail/form-structure-contract-projection-matrix-v1.json` | 接管后修改 | 补 `source_kind` 真实分类行（断言未删，§8.3） |
| 30 | `docs/frontend_productization/rendering-detail/rendering-surface-ownership-v1.json` | 接管后修改 | 补 `BoundFormSettingsPanel.vue` 真实归属声明（§8.3） |
| 31 | `scripts/verify/form_structure_contract_projection_matrix.py` | 接管后修改 | 投影矩阵断言按真实分类收敛（§8.3） |
| 32 | `scripts/verify/frontend_page_pattern_reference_parity_guard.py` | 接管后修改 | 字面量守卫改为 `_BooleanExpression` 行为模型（§8.3） |
| 33 | `scripts/verify/test_frontend_page_pattern_reference_parity_guard.py` | 接管后修改 | 13 例行为测试（§8.3） |
| 34 | `scripts/audit/generate_frontend_rendering_detail_inventory.py` | 接管后修改 | 生成器随归属声明调整（§8.3） |

写入归属口径（单一写入者 = 本会话）：

- 接管前已有：第 1–8 项；接管前段（同一批次、本会话接管动作之前）：第 9–18 项。
- 接管后修改：第 19–34 项。其中第 20–21 项为受管 P4 测试工具的最小诊断补齐；第 22–23 项为 P0 `smart_core` 变更集哈希基准修复与其回归测试；第 24–27 项为草稿归属守卫、代表面路由与 popup 诊断（§8.2／§8.4）；第 28 项为唯一产品代码修复；第 29–34 项为三个红灯的对应层修正与生成器调整（§8.3）。此前“本轮仅写活记录”的口径自本步起不再成立。
- 仅验证（无写入）：§6 全部 L1–L4 入口、L4 运行（R1–R4、R9、R10）、代表面五次运行、生成物一致性复核、只读探针与 `FORM_LOWCODE_SCOPE_ONLY=1` 范围读取。

### 4.1 后端

接管项：
- `addons/smart_core/core/view_orchestrator.py`：新增 `_display_copy_field_names`（只消费 `_display_copy_source_fields` 协议）；`_config_declares_native_semantic_surface` 拒绝副本锚点（`NATIVE_SEMANTIC_SURFACE_DISPLAY_COPY`）；`_apply_form_spec` 并集补齐排除副本。
- `addons/smart_construction_core/models/core/formal_config_contract_fields.py`：`FORMAL_DISPLAY_COPY_SOURCES` 注册表 + `sc.formal.display.copy.sources` AbstractModel 协议 mixin + 发票 4 副本登记（`note_display`/`invoice_attachment_text`/`source_created_by`/`source_created_at`）。

本次补充：
- `formal_config_contract_fields.py`：把登记判据写成三条硬条件注释（单源实时投影／正文外独立职责／canonical 同 arch 共现）；新增 `payment.request → payment_request_attachment_text_display`、`sc.material.inbound → material_inbound_attachment_text_display` 两条登记（canonical `attachment_ids` 已核对在各自表单 arch 共现）；三个模型由 `_inherit = '<model>'` 改为 `_name = '<model>'; _inherit = ['<model>', 'sc.formal.display.copy.sources']`。
- 新增 `addons/smart_construction_core/tests/test_form_structure_consumption.py`（5 例）并在 `tests/__init__.py` 注册。

> 归因要点：HEAD `025e37d2` 的发票整改是在 **view arch XML 里移除副本字段**（`invoice_registration_views.xml`）+ 前端 `nativeStructureAuthority` 关闭筛选；通用「注册表 + 协议 + 并集排除」机制**整批位于工作树、未提交**，其**生效前提**是本次补充把一个模型挂载改为三个模型挂载 mixin。该机制首次真正运行时点 = 本轮，因此 L4 发票失败（§6/§7）必须先在该机制上归因，不能只归因于 HEAD。

### 4.2 前端（P0 共享层）

接管项：
- `pages/contractForm/nativeLayoutUtils.ts`：`filterVisibleNativeLayoutNodes` 新增 `pruneEmptyContainers`（正式渲染修剪过滤后空容器；设计器画布保留空组投放目标）。
- `pages/contractForm/useRecordFormLayout.ts`：正式路径启用修剪（`pruneEmptyContainers: !isContractFieldOrderEditable`）；导航标题收集自修剪后同一有效树。
- `components/template/NativeFormTreeRenderer.vue`：`isLayoutOnlyGroup` → `native-container--group--layout` 不画章节分隔线；`isNodeRenderable` 扩展到 header/sheet/footer/notebook；`hasRenderableDescendant` 对 field 增加「必须产出 schema」判据。
- `pages/ContractFormPage.vue`（筛选门）与 `pages/contractForm/ContractFormActionBlocks.vue`（占位块门）的既有改动。

本次补充：
- `nativeLayoutUtils.ts`：抽出并导出纯函数 `isLayoutOnlyGroupContainer({nodeType, editable, sectionTitle})`（设计器保留装饰）。
- `NativeFormTreeRenderer.vue`：`isLayoutOnlyGroup` 改为委托该共享判定，行为不变（消除渲染器与共享层两套判定）。
- 新增 `pages/contractForm/formActionPlaceholderGate.ts`：`resolveFormActionPlaceholderGate()` —— 查询筛选只凭结构权威即可关闭；流程流转／正文动作仅当**全部动作键都已出现在渲染出的 header 动作行**时才关闭，未承载键由 `uncarriedActionKeys` 上报；原生树自身即承载（三项全关）。
- `ContractFormActionBlocks.vue`：新增 `suppressWorkflowTransitions?` / `suppressBodyActions?` props，未传时回落 `suppressActionBlocks`（不回退既有行为）。
- `ContractFormPage.vue`：`actionPlaceholderGate` 计算（喂入 header direct/overflow/configuration 键、主创建/提交键、流转键、正文动作键）；`suppressFormActionBlocks` 现等于 `suppressSearchFilters`；新 props 绑定。

### 4.3 测试与生成物

接管项：
- `addons/smart_construction_core/tests/test_invoice_native_lowcode.py`：+2 机制测试（注册表与并集排除；副本锚点拒绝）。
- `frontend/apps/web/scripts/formal_form_invoice_journey.mjs`：`assertSinglePresentation` 增加 `assertStructureResponsibility`（空容器不占位 + 布局包装 computed borderTop 为零）。

本次补充：
- 新增 `frontend/apps/web/scripts/native_form_structure_responsibility_test.ts`（8 例行为测试，执行生产 helper，非字符串扫描）。
- `make/frontend.mk`：新增 `verify.frontend.native_form_structure_responsibility.unit`，并纳入 `verify.frontend.quick.gate`。
- 生成物按既有生成入口刷新（未手改摘要）：`refresh.frontend.rendering_detail.inventory`（rendering_detail / visual_projection / official_design_alignment 三支生成器）与 `refresh.frontend.component_driver_takeover.inventory`。

## 5. 代表场景（D，覆盖不同结构机制而非全量业务旅程）

- 发票：空 header、嵌套 group、计算副本（785/786/787/788 + 旁路 789/639）。
- 客户：基础资料与关系集合。
- 合同／结算：长表单、条件章节、只读值。
- 材料：notebook、跨页签导航、全宽明细。
- 低代码配置样本：重排、分组、隐藏后发布与回滚（发票设计器）。

原有保存、金额、审批及权限证据，相关实现未变则继续复用。

## 6. 验证结果

身份：HEAD `025e37d2` + 显式脏区。以下全部为迭代期证据，非冻结交付证据。本节记录当时口径（含已被 §8 取代的 L4/红灯结论），**当前有效矩阵见 §8.5**。

### 6.1 L4 失败现场（两次运行，转录自本轮终端输出）

入口：`FORM_LOWCODE_TOPIC=invoice make local.dev.form_lowcode.browser`
→ `scripts/verify/local_dev_form_lowcode_browser.sh`（校验 compose/db 身份、编译期 SHA、前后业务指纹）
→ `frontend/apps/web/scripts/low_code_change_set_acceptance.mjs`
→ `formal_form_lowcode_loop.mjs`：先 `checkInvoiceDefaults`（发票 6 入口契约/权限/呈现断言），后 `runDesignerJourney`（设计器草稿→预览→发布→回滚）。

| # | 运行前环境动作 | 失败阶段 | 观察结果 |
|---|---|---|---|
| R1 | 11:13 `local.dev.restart` + `local.dev.frontend.watch` 均成功 | `formal_form_designer_journey.mjs:46` —— 点击「保存配置草稿」后等待 `ui.business_config.change_set.open` 响应 | 15s 内未观察到该 intent 的响应；此前的 `checkInvoiceDefaults`（含 `note` 可见断言）已通过；崩溃发生在写报告之前，`report.json` 未落盘 |
| R2 | 无（间隔约 6 分钟） | `formal_form_invoice_journey.mjs:181` `assertFormRendered(page,'note')`，由 `checkInvoiceDefaults:322` 对 `/f/sc.invoice.registration/new?action_id=…` 逐入口调用 | `[data-field-name="note"]` 可见性 15s 超时；阶段早于设计器 |
| R3 | 无（诊断补齐后的一次性只读重放，`FORM_LOWCODE_REPLAY=1`） | `formal_form_lowcode_loop.mjs` 登录阶段：`/login` 等待第一个 `input` | **应用外壳未挂载**：`#app` 子节点 0、body 文本长度 0、`failure.png` 全白；`pageerror` 0；console 40 条（封顶）全为 `Failed to load resource: net::ERR_NETWORK_CHANGED`；40 条失败请求全为 Vite 模块（`/@fs/.../.vite/web/deps/chunk-*.js`、`/src/**/*.vue|.ts`）；`intents` 为空 ⇒ 前端连一次契约请求都没发出 |
| R4 | 无（同一只读重放，修复挂载预检后） | 同上 | **通过**：6 个发票入口 11 个默认阶段全绿、`note` 可见断言通过、设计器旅程按只读模式跳过、`console`/失败请求均为 0、未产生任何草稿 |

#### 6.1.1 首个真实断点与根因（R3 证据）

- **分类：加载失败（传输层）**，不是字段合法隐藏、修剪误删，也不是定位器错误。四条判据互斥且完备：
  - 字段合法隐藏：不成立——该次失败连应用外壳都没挂载（`#app` 子节点 0），与任何具体字段无关。
  - 修剪误删：不成立——失败发生在登录页；且同一次运行 11:18 的 `/a/785` 列表页截图正常渲染，说明会话与后端均正常。
  - 定位器错误：不成立——`intents` 为空，前端根本没运行到契约消费；DOM 内不存在任何 `[data-field-name]`。
  - 加载失败：成立——`Failed to load resource: net::ERR_NETWORK_CHANGED` × 40（封顶），失败对象全是 Vite 开发服务器的 ES 模块请求。
- **共同根因**：Chromium 收到宿主网络变更事件后中止在途请求。宿主存在多个 `linkdown`/DOWN 的 Docker 网桥，网桥增删即触发该事件，错误码正是 `net::ERR_NETWORK_CHANGED`。R2 的整页空白、R1 的 `change_set.open` 无响应与之一致（同一传输类故障的不同表现）；但 R1 的传输归因仍属**推断**，须由未跳过的设计器旅程运行确认。
- **产品层结论**：本轮**不因此改动任何产品代码**。`contract-785.json`（R2 同一次运行捕获）显示后端契约健康（90 节点、69 字段、`note` 在树内、`statusContract.hidden=[]`），失败与表单结构机制无关。
- **修复（责任层 = P4 受管测试工具）**：① 补齐最小失败诊断（§4.0 第 20 项）；② 登录阶段新增应用外壳挂载预检，未挂载时按 `environment_transport` / `app_shell_not_mounted` 分类并快速失败，附中止模块请求数与样例，不再以 15s 静默超时收场；③ 增加**一次**有界恢复（重新导航并复探挂载），恢复事实写入 `report.transport_recovery`；不延长超时、不放宽任何产品断言。

共同事实与边界：
- 服务端：`docker logs sc-local-dev-odoo-1 --since 12m` 无 error/traceback/500。

#### 6.1.2 R1 归因（设计器「保存配置草稿」）与 P0 修复

R1 在补诊断后于同一位置原样复现（`formal_form_designer_journey.mjs:46` 等待 `change_set.open`）。本次失败报告为新证据：

- `failed_requests = 0`（无传输中断）、`intents` 中只有 9 次 `ui.contract.v2` ⇒ **不是** §6.1.1 的传输类故障。
- 失败页 DOM（`failure-dom.html`）含 `data-state="error"` 告警：**「当前配置已被其他管理员更新。」** 该文案在 `business_config_change_set.py:297` 只由 `STALE_CONFIG_HASH` 返回 ⇒ 保存动作确实发出过请求并被服务端拒绝，且被拒的是 **stage**，不是 open。
- 面板 `save()`（`BoundFormSettingsPanel.vue:192`）在**已有草稿**时跳过 `open` 直接 `stage`；面板 `onMounted` 用 `resumeBusinessConfigChangeSet` 续用同目标草稿 ⇒ `open` 请求根本不会发生，harness 等 `open` 必然超时。
- 续用来源即 id=163（`ready`、目标 `view_orchestration:sc.invoice.registration:form:action:785:view:1651:role:system_admin`、1 条 item）。

**根因（P0 `smart_core`）：同一字段在服务端往返中使用了两种哈希基准。**

| 位置 | 计算方式 | 证据 |
|---|---|---|
| 条目序列化（客户端拿到的 `current_payload_hash`） | `str(self.base_payload_hash)`，而 `base_payload_hash = stable_payload_hash({**contract._definition_payload(), "status": contract.status})` | `ui_business_config_change_set.py:186`、`business_config_change_set.py:312` |
| stage 守卫（服务端比对目标） | `stable_payload_hash(contract.contract_json)` | `business_config_change_set.py:294`、`295-300` |

实测（只读，变更集 163 的 item 127 → 合同 410）：

```
base_payload_hash（= 序列化值）        = 7d1558e69fd9e15b6325102adbb3c3ad18367cdd9118dba565bd021af27609a0
stable_payload_hash(_definition+status) = 7d1558e69fd9e15b6325102adbb3c3ad18367cdd9118dba565bd021af27609a0   ← 与 08:00 存储值一致 ⇒ 已发布配置自 08:00 起未变
stable_payload_hash(contract_json)      = d658c12c61aff01f831017be284ec2ec29a726392814fa049fc9db9a4f4324e3   ← 守卫比对目标
```

⇒ 守卫对**未发生变化**的配置也判为过期（假阳性），且**任何**续用草稿都无法再保存：`open` 不会发、stage 必 409。这不是本批表单结构机制的问题，与模型名/字段后缀无关。

**修复口径**：只修「服务端给出的值」与「服务端期望的值」不一致这一端——条目序列化改为与守卫同一基准（`stable_payload_hash(target_contract_id.contract_json)`；`menu` 类型与无合同条目保持原值）。守卫语义不变：真过期仍返回 409（新回归测试同时验证「续用可保存」与「stale 仍被拒」）。未改动前端、未改动 guard、未放宽断言。

归属声明：Formal Product Layer = P0 平台内核产品；Layer Target = `smart_core` 变更集条目序列化；Standard；Why Here = 往返两端都在 `smart_core` 平台代码内；Why Not Elsewhere = 不是前端消费或客户偏好问题，客户端契约保持不变；Blast Radius = 表单/列表/搜索/分析类条目「续用草稿→再次保存」路径，由 P0 单测 + 重启后运行时 + 发票设计器旅程验证。

- 配置面回读：`ui.business.config.change.set` 最新记录为 id=163（2026-09-17 00:00 UTC＝08:00 本地），**早于两次运行**；两次运行均未新增记录。
- 「未新建 change set」**不等于**「未改动既有草稿」：既有草稿（含 id=163）在两次运行前后的内容与状态尚未比对，列为下一步必查项。
- R1 通过、R2 失败于同一断言 ⇒ 非确定性；经 R3 归因为传输类加载失败，**不登记为产品缺陷**。

| 层 | 入口 / 命令 | 状态 | 非零用例数 | 说明 |
|---|---|---|---|---|
| L1 | `make ci.local.iteration` | passed | 16 tests OK | `change_state=dirty`、`coverage=L1_only`、`receipt=none`、`next=risk_selected_non_zero_L2`；推荐 L2 = canonical_form_presenter / page_pattern_reference_parity / primitive_adapter / product_page_pattern |
| L1 | `make verify.frontend.typecheck.strict` | passed | — | vue-tsc 无输出 |
| L2 | `make verify.frontend.canonical_form_presenter.unit` | passed | cases=170 | readonly 空/有内容章节与导航 10 例 |
| L2 | `make verify.frontend.native_form_structure_responsibility.unit` | passed | cases=8 | 空 header／无标题包装组／隐藏子节点／非空页签与明细／嵌套章节分隔／正文与导航一致／设计器与业务预览差异／动作门控承载证明 |
| L2 | `make verify.frontend.primitive_adapter.unit` | passed | components=46 | 31 tests |
| L2 | `make verify.frontend.product_page_pattern.unit` | passed | patterns=4 | 5 tests |
| L2 | `make verify.frontend.native_form_action_presentation.unit` | passed | 16 tests | ordinary_sc_buttons=2 container_disclosures=1 |
| L2 | `make verify.frontend.component_driver_takeover.unit` | passed | required=35 missing=0 | 生成物刷新后复核 |
| L2 | `make verify.frontend.form_structure_contract_projection.unit` | **failed（先于本轮工作树）** | — | `missing=['formStructureGovernanceContract.source_kind']`；边界证据与修法口径见 §7.2 |
| L2 | `make verify.frontend.page_pattern_reference_parity.unit` | **failed（先于本轮工作树）** | — | 要求字面量 `:hide-title="suppressPageHeaderTitle"`，当前绑定已含额外条件；边界证据与修法口径见 §7.2 |
| L2 | `make verify.frontend.rendering_detail_state.unit` | **failed（先于本轮工作树）** | — | `BoundFormSettingsPanel.vue` 无归属声明 → `gap=1`；`git archive HEAD` 复现同一 `gap=1`，仅证明相对当前工作树已存在，不作提交级归因；边界证据见 §7.2 |
| L3 | `make local.dev.restart` | passed | — | sc-local-dev / sc_dev_demo；odoo `Up (healthy)` |
| L3 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS=/smart_construction_core:TestFormStructureConsumption` | passed | 5 tests, 0 failed, 0 errors | `test.safe (no upgrade)`；未触发 upgrade/reset/sync_demo |
| L4 | `FORM_LOWCODE_TOPIC=invoice make local.dev.form_lowcode.browser` | **failed（未完成、未归因）** | — | 两次运行、两个不同失败点，详见 §6.1 |
| L4 | 付款／客户／合同结算／低代码代表面 | not_run | — | 登记入口仅支持 `material|document|invoice`，无对应 topic |

生成物刷新：`refresh.frontend.rendering_detail.inventory`、`refresh.frontend.component_driver_takeover.inventory` 均通过既有入口执行，摘要由生成器写出。

未执行：`ci.delivery.freeze.prepare`、`ci.local.quick`、`pr.push`、`local.dev.sync_demo`、`local.dev.snapshot`。

## 7. 剩余缺口与恢复门槛

### 7.1 阻断项（必须先关闭，否则不得冻结/Quick/推送）

> 状态更新（见 §8）：本节 1「发票 L4 未通过且未归因」的归因已完成——R5/R6/R7 为草稿复用与断言口径问题（P0 哈希基准已修、R8 通过），R9/R10 为宿主网络中断导致的模块传输失败（`environment_transport`，popup 级证据）。本节 2 的三个红灯已逐项修正并各自通过对应测试。保留原文以便追溯当时口径。

1. **发票 L4 复核未通过且未归因**（本批自有机制的首次真实运行）。现场见 §6.1。
   - 已确认：服务端无异常；两次运行未新建 change set；同一断言一次通过一次失败 ⇒ 非确定性。
   - 未确认（下一步必查）：既有草稿（含 id=163）在两次运行前后的内容与状态是否被改动；`note` 的**首次丢失位置**（页面加载完成 → 最终契约 → 字段策略 → 修剪后树 → DOM）。
   - 禁止：以延长超时或放宽断言代替归因；在所有者/批次/影响未确认前触碰 id=163。
   - 主嫌疑（未证实，不登记为缺陷）：本批首次让「副本并集排除」真正生效（HEAD 只有 arch 层移除，通用机制整批在工作树）；以及 `NativeFormTreeRenderer.hasRenderableDescendant` 新增的「field 必须产出 schema」判据在 create 异步加载下可能让章节被修剪。
2. **三个便宜检查红灯**：见 §7.2，按第 4 步逐项核对真实契约与行为后修正责任层。

### 7.2 三个红灯的边界证据与修法口径

归因方法：用相邻提交对比（绿灯提交 → 红灯提交），不单靠工作树实验。

| 红灯 | 边界提交 | 边界证据 | 修法口径（第 4 步执行） |
|---|---|---|---|
| `verify.frontend.form_structure_contract_projection.unit`：`missing=['formStructureGovernanceContract.source_kind']` | `225a56bf` | 该提交前 `unified_page_contract_v2.schema.json` 内 `source_kind` 出现 0 次，提交后 2 次；投影矩阵最后更新 2026-09-15（`0f8b5ee6`），早于 schema 变更 | 先判断 `source_kind` 是否仍是正式契约要求（查 schema 定义与产出方）；是则给矩阵补真实分类行，不得删断言 |
| `verify.frontend.page_pattern_reference_parity.unit`：要求字面量 `:hide-title="suppressPageHeaderTitle"` | `225a56bf` | 该提交前 `ContractFormPage.vue:26` 即为该字面量；提交后改为 `!isConfigurationPreview && suppressPageHeaderTitle`；guard 要求自 2026-08-27（`482acc47`）未变 | 先验证预览保护行为（配置预览下标题必须可见），再修守卫；尽量改为行为断言而非字面量 |
| `verify.frontend.rendering_detail_state.unit`：`BoundFormSettingsPanel.vue` 无归属 → `gap=1` | `225a56bf` | 文件由该提交引入；该提交只刷新了 `component-driver-takeover-inventory-v1.json`，未更新 `rendering-surface-ownership-v1.json` | 核对组件职责后补真实声明；不得用排除扫描消 gap |

### 7.3 工作树与草稿现状（不作违规判定）

- 登记工作树 4 个：**登记 ≠ 活跃**，历史保留树本轮不动，也不据此判定预算违规；是否需要清理由后续治理决定。
- `ui.business.config.change.set` id=163：本节原记为 `ready`，**该记录有误**。本轮快照显示它在 11:48／11:51 为 `draft` 且带 1 条 items，11:55 变为 `discarded`（`write_date` 11:53:57，落在 R6 运行窗口内）。事实链与修复见 §8.2；163 记录仍在（未删除、items 保留），不因本轮结论而回滚或删除。仍遵守原边界：在确认所有者、所属批次与实际配置影响之前，不回滚、不删除、不引用。
- `025e37d2` 复现红灯只能证明该现象相对**当前未提交改动**已存在，不能据此把责任归因到某个已合并 PR；本轮三个红灯的边界证据见 §7.2 与其修正结果见 §8.3。

### 7.4 代表面覆盖缺口

> 状态更新（见 §8.4）：本节两项已关闭。代表路由已在既有受管 runner 内补齐（复用同一环境与身份校验，未新建 fixture 或环境），付款／客户／合同结算／材料五个代表面均通过；低代码「编辑目标保留、预览与发布效果一致」已有设计器真实路径证据（R8 `ok=true`）。保留原文以便追溯当时口径。

- 浏览器入口 `scripts/verify/local_dev_form_lowcode_scope.py` 只登记 `material|document|invoice`。付款（`payment.request`）、客户、合同／结算、低代码设计器目标**没有**登记 topic；扩域属 P4 测试工具扩展，需单独授权后才能取得这些代表面的浏览器证据。故 §5 代表面清单本轮只覆盖发票（且未通过）。
- 低代码「编辑目标保留、预览与发布效果一致」目前只有单元/静态证据，设计器真实路径无独立证据（L4 失败点恰好在其上）。

### 7.5 机制覆盖矩阵（候选，未验证不登记）

- 17 个正式配置组声明了 `x → y` 投影；目前仅登记 3 个模型（invoice 4 条、payment.request 1 条、sc.material.inbound 1 条）。
- 证据待逐字段判定的候选：`material_purchase_*`、`settlement_order`（`settlement_flow_label`/`settlement_category_display`）、`material_settlement_*`、`payment_execution_*`（镜像 `partner_payment_*`）、`subcontract/labor/equipment` 结算组的 `source_created_by_display ← source_created_by`（其来源本身是存储快照，按规则 3 很可能**不登记**）。
- 约束：未验证不登记为缺陷、不批量改字段；本批不扩展。
- 另：`payment.request` 的 entry_semantic_surface 契约仍枚举 `payment_request_attachment_text_display`。并集排除已阻止其进入正文，但**已发布契约数据本身未修改**（刻意遵守「不批量改字段」）。

### 7.6 执行顺序（已授权，按序执行）

| 顺序 | 任务 | 完成条件 |
|---|---|---|
| 1 | 整理改动归属与失败现场 | 固定 HEAD＋dirty 范围；复用两次失败日志；明确各自入口、阶段与观察结果（§4.0、§6.1） |
| 2 | 补最小诊断能力 | 异常退出也能保存 URL、截图、DOM、`pageerror`、关键请求结果与配置恢复状态；不记录密钥或 token |
| 3 | 有界复现并修复首个真实断点 | 优先只读重放失败页面；区分加载失败／字段合法隐藏／修剪误删／定位器错误；不得以延长超时或改断言代替归因 |
| 4 | 收敛三个便宜检查红灯 | 逐项核对真实契约／行为，修正责任层后只跑对应测试 |
| 5 | 完成代表面复核 | 发票、付款、客户、合同／结算、材料、低代码按既定机制范围集中交回 |

L4 归因边界：只有必须跨过保存阶段才能复现时，才使用已授权的受管测试草稿并保留恢复回读；不碰归属未明的 id=163。最小 P4 诊断补齐后允许一次有针对性的诊断运行；若仍失败则依新证据继续修复，禁止无变化重试。代表面工具：在既有受管 runner 内补齐只读代表路由，复用环境与身份校验，不另建 fixture 或环境。

### 7.7 未执行项（保持未执行）

`ci.delivery.freeze.prepare`、`ci.local.quick`、`pr.push`、`local.dev.sync_demo`、`local.dev.snapshot`、模块 upgrade、fixture reset、发布快照：本轮均未执行；也未新增/派生任何环境、数据库、端口、卷或凭据。

## 8. 本轮补充：R5–R10 归因、草稿归属守卫、popup 诊断、代表面结果

身份不变：分支 `feature/uc4-invoice-native-lowcode`，HEAD `025e37d2`，工作树 dirty（28 modified + 6 untracked = 34 条路径），未提交、未冻结。本节全部为迭代期证据。

### 8.1 发票 L4 设计器旅程的完整运行史（R5–R10）

| 运行 | 窗口（本地） | 结果 | 失败点 | 观察与分类 |
|---|---|---|---|---|
| R5 | 11:48–11:49 | 失败 | `checkInvoiceDefaults` 默认值阶段 `[data-field-name="name"]` 可见性超时 | 与 R2 同类；默认值阶段，未触及设计器 |
| R6 | 11:51–11:54 | 失败 | `formal_form_designer_journey.mjs:106` 「未改动税字段丢失共享列」 | 走完保存→预览；本运行净增 0 个 change set ⇒ 复用了既有草稿 |
| R7 | 11:55–11:58 | 失败 | 同文件 `:111` 「未改动税字段丢失原生顺序」 | 净增 1 个 change set ⇒ 已无草稿可复用，只能新开 |
| R8 | 11:59–12:02 | **通过** | — | `ok=true`、`change_set_id=190`、`save_path=opened_new_change_set`、`restored=true`、`browser_errors=[]`、6 个发票入口 11 个阶段全绿 |
| R9 | 13:22–13:26 | 失败 | 回滚后业务 popup `body.innerText()` 为空，随后 `发票号码` 可见性超时 | `save_path=resumed_existing_draft`、`change_set_id=192`。当时被分类为 `product_or_locator`，**分类有误**：business popup 当时没有诊断接线 |
| R10 | 13:28–13:32 | 失败 | 预览 popup `getByText('受管发票号码')` 超时 | `save_path=opened_new_change_set`、`change_set_id=194`；`failed_requests` 中 `popup_1` 23 条、`main` 8 条，全部 `net::ERR_NETWORK_CHANGED` ⇒ `environment_transport` |

R10 是补齐 popup 诊断后的第一次运行，因此它把 R9 无法归因的那一段坐实为**同一环境传输类**：宿主存在 13 个 `DOWN/UNKNOWN` 接口（含多个 `br-*`）与 33 个 docker 网络，网桥抖动会中止在途的 Vite 模块请求；本次命中的是预览 popup 的模块加载，R9 命中的是业务 popup。两次都**不是**表单结构机制缺陷。

### 8.2 受管 runner 消费了并非自己打开的草稿（本轮第二个真实缺陷，已修）

事实链由三条相互独立的证据闭合：

1. 快照：11:48 与 11:51，`163` 为 `draft` 且是当时**唯一带 items 的可复用草稿**（`items=1`，`target_key=view_orchestration:sc.invoice.registration:form:action:785:view:1651:role:system_admin`）；11:55 已变 `discarded`，`write_date` 为 11:53:57 —— 落在 R6 运行窗口内部。
2. 计数：R5 净增 0、**R6 净增 0 且唯一可复用草稿消失**、R7 净增 1、R8 净增 3（190 新开＋191 回滚记录＋192 复查草稿）。与「R6 复用 163 → R7 只能新开 → R8 新开并留下 192」完全吻合。
3. 机制：`formal_form_designer_journey.mjs` 把保存返回的 token 直接 `drafts.add()`，而 loop 的 `finally` 会 discard `drafts` 中的全部 token —— 它无法区分「本次运行打开的」与「复用的既有」草稿。

守卫缺口：`topic=invoice` 的 scope 中 `configuration_entry=None`（该键只在 `LOWCODE_CONFIG_ENTRY=1` 时构建），wrapper 的 `owner_change_sets` 前后比对因此**不覆盖设计器主题**，这条破坏性写入不会被发现。

> ⚠️ 本节初版修复在**第 3 次接管**中被 §8.8 取代：`resolveDesignerDraftGuard` 与宽泛开关
> `FORM_LOWCODE_ALLOW_RESUMED_DRAFT` **已删除**（后者不绑定草稿 id，且会整体跳过既有草稿的前后比对）。
> 以下保留为当时的事实记录。

修复（全部在既有受管 runner 内，未新建环境/凭据/fixture）：

- 新增 `frontend/apps/web/scripts/designer_draft_ownership.mjs`：
  - `resolveDesignerDraftOwnership`：只有 `save_path=opened_new_change_set` 的 change set 才交给清理；复用的草稿改为记录 `preserved_draft`，不释放。
  - `resolveDesignerDraftGuard`：目标上存在可复用草稿时**先于本次运行的第一笔写入**失败关闭（`preexisting_admin_draft_present`）。
- `formal_form_designer_journey.mjs`：按归属决定是否把 token 交给清理。
- `formal_form_lowcode_loop.mjs`：设计器分支前置守卫，并把判定写入 `report.designer_draft_guard`。
- `scripts/verify/local_dev_form_lowcode_scope.py`：只读输出 `designer_drafts`（属主、目标前缀、未过期、产品自身的 `ACTIVE_CHANGE_SET_STATES`）。
- `scripts/verify/local_dev_form_lowcode_browser.sh`：运行前后比对既有草稿并 fail-closed，同时把 `designer_drafts` 从通用 dict 比较中剥离，以给出精确结论。

谓词修正（初版被 R9 实证推翻）：初版按 `state == 'draft'` 判定，而 R9 报告 `save_path=resumed_existing_draft`、`change_set_id=192`（`state=ready`）—— 可复用集合实为产品常量 `ACTIVE_CHANGE_SET_STATES = {draft, validating, ready, failed}` 且未过期（`expires_at` 默认 `now + 8h`）。修正后按同一常量与过期时间判定：`192`（`expires_at` UTC 12:01:59，R9 开始时未过期）会被拦下；`158`（09-16 13:31）已过期，不会被误拦。

修复效果的直接证据与边界：R9 报告 `preserved_draft = {"id": 192, "reason": "resumed_preexisting_draft_not_authored_by_run"}` ⇒ **runner 不再删除他人草稿**。但必须明确边界：R9 仍在产品自身流程里把 192 发布并回滚（192 `superseded` + 193 `published`），所以「不被删除」≠「不被消费」；真正的保护是前置守卫——按修正后的谓词，R9 会在第一次写入前被拒绝。

### 8.3 三个红灯：逐项核对契约/行为后修正（各自只跑对应测试）

| 红灯 | 核对结论 | 修正（责任层） | 结果 |
|---|---|---|---|
| `verify.frontend.form_structure_contract_projection.unit`：`missing=['formStructureGovernanceContract.source_kind']` | `source_kind` 仍是正式契约要求（schema 有定义与产出方），**不是**可删的过期断言 | 投影矩阵补真实 `NON_VISUAL` 分类行 | passed：`[form_structure_contract_projection_matrix] PASS fields=75 unclassified=0` |
| `verify.frontend.page_pattern_reference_parity.unit`：要求字面量 `:hide-title="suppressPageHeaderTitle"` | 预览保护行为（配置预览下标题必须可见）是产品要求，字面量不是 | 守卫改为 `_BooleanExpression` 行为模型 | passed：`Ran 13 tests OK` + `PASS surfaces=15` |
| `verify.frontend.rendering_detail_state.unit`：`BoundFormSettingsPanel.vue` 无归属 → `gap=1` | 组件职责真实存在 | 补真实归属声明（9 sources，gaps=0）；**未**用排除扫描消 gap | passed：`Ran 55 tests OK`，`rendering_detail_inventory PASS surfaces=168 gaps=0`，`official_design_alignment PASS`（`internalVendorSelectorGapCount=0`、`visualLiteralGapCount=0`） |

### 8.4 代表面：在既有 runner 内扩域后全部通过

P4 扩展方式：只读代表路由补在既有受管 runner 内（`local_dev_form_lowcode_scope.py` 注册 payment／customer／contract／settlement 代表面，新增 `formal_form_representative_journey.mjs`），复用同一环境、身份与身份校验，未新建 fixture 或环境；约 6 组投影候选仍留在 §7.5，未扩大本批登记范围。

运行方式：`FORM_LOWCODE_TOPIC=<t> FORM_LOWCODE_REPRESENTATIVE=1 make local.dev.form_lowcode.browser`；日志 `artifacts/uc4-representative/run-<t>.log`，报告 `artifacts/lowcode-form-loop/browser/representative-report-<t>.json`。

| 代表面 | 主题 | 结果 | 关键观察 |
|---|---|---|---|
| 付款 | payment | passed | 809：26 字段/6 章节；`payment_request_attachment_text_display` 声明于正文外且未渲染，`attachment_ids` 渲染（1 节点、2 个文件输入、2×「上传附件」）⇒ 同一事实一处呈现；`payee_account_source_display` 保留 |
| 客户 | customer | passed | 820：38 字段/8 章节；`category_id`/`child_ids`/`bank_ids`/`sc_attachment_ids` 四个关系集合均在正文 |
| 合同 | contract | passed | 609/610：create 24 字段/5 章节，record 25/7；`line_ids` 渲染；`operation_strategy` 只读干净；「来源与系统追溯」可展开；无重复/空壳/误装饰；610 额外渲染 `attachment_ids`，`historical_payment_fact_ids` 策略隐藏（记录为跳过） |
| 结算 | settlement | passed | 781（create 27/5，record 38/12，6 个关系全部渲染）；782（record 26/11，只读呈现档位，见 §8.5 缺口） |
| 材料 | material | passed | 546/547：页签「入库明细／材料明细」「说明与附件」「来源追溯」均有内容；全宽明细按承载列度量（`column_fill ≥ 0.9` + 页面级 `columns === 1` 且 `tree_ratio ≥ 0.9`）；章节入口点击后必须解析且可见；分隔线干净（两个 action 的 `decorated_layout_groups: []`） |

代表面过程中定位到的真实根因（按机制，非逐点修补）：

- 付款「页签不可见」= notebook 位于被声明为默认折叠的群组 `sc_payment_request_pay_trace`「履约与追溯」内，渲染器按产品语义隐藏折叠子树；用产品自身的展开开关展开，未改超时。
- 结算「关系丢失」= 群组级 `invisible` 条件未随字段级 `widgetStatus` 携带；补容器条件与逐 occurrence 模型，条件不满足时记为 `relations_conditional` 而非缺陷。
- 材料「全宽明细」= 542/544 位于 `--columns-2` 群组内，属正确布局；断言改为按承载列度量。
- 导航「未在加载时解析」= `data-section-target` 是揭示目标，可能由另一页签持有；改为行为断言（每个章节入口点击后必须解析且可见）。
- 只读值 = 最宽（可写）节点/occurrence 上各 occurrence 的交集；渲染档位由此决定，记 `presentation_mode`。
- 空容器 = 高度 `> 2` 才算占位（记录 782 存在 0 高度布局包装）。
- 章节分隔线归属 = 布局包装组不画线（`ContractFormPage.css`，本轮唯一产品代码修复）。

### 8.5 本轮验证矩阵（更新后）

| 层 | 入口 | 状态 | 非零用例 | 说明 |
|---|---|---|---|---|
| L1 | `make ci.local.iteration` | passed | 16 tests OK | 归属守卫改造后重跑；`coverage=L1_only`、`receipt=none` |
| L1 | `make verify.frontend.typecheck.strict` | passed | — | vue-tsc 无输出 |
| L2 | `make verify.frontend.native_form_structure_responsibility.unit` | passed | cases=10 | 原有 8 例 + 草稿归属/越权守卫 2 例（行为断言） |
| L2 | 三个红灯对应入口 | passed | 13 / 55 例 | 见 §8.3；三条入口本轮实测 `exit=0` |
| L2 | canonical_form_presenter / primitive_adapter / product_page_pattern / native_form_action_presentation / component_driver_takeover | passed（复用） | 170 / 31 / 5 / 16 / required=35 | 相关输入未变，不重跑 |
| L3 | `make local.dev.restart` | passed（复用） | — | sc-local-dev / sc_dev_demo |
| L4 | 发票设计器旅程 | R8 通过；R9/R10 环境传输阻断；**R11 通过** | — | 见 §8.1／§8.12；R11 为守卫改造后的一次干净运行 |
| L2 | `make local.dev.test MODULE=smart_core TEST_TAGS=/smart_core:TestBusinessConfigChangeSet` | passed | 23 tests OK | 新增 4 例行为反例；P0 口径改动后全类无回归 |
| L2 | `make verify.business_config.unit` | passed | 9+64+24+48+5 例 + 2 node | 含新增 `designer_draft_ownership_test.mjs`（cases=5） |
| L4 | 发票只读传输检查（`FORM_LOWCODE_REPLAY=1`） | passed | — | `failed_requests=[]`、`browser_errors=[]`、`restored=true`；本次未复现传输中断 |
| L4 | 代表面（付款/客户/合同/材料/结算） | passed（本轮重跑） | 5 主题 | 共用 `finally` 清理路径属本轮改动，故重跑而非纯复用 |
| L4 | 代表面（付款/客户/合同/材料/结算） | passed | 5 主题 | 见 §8.4 |
| L4 | 只读重放（R3/R4） | passed | — | `FORM_LOWCODE_REPLAY=1` |

生成物刷新：为归属守卫补的行为测试落在 `frontend/apps/web/scripts/*.ts`，而 `official-design-alignment` 的摘要覆盖 `frontend/apps/web` 下全部 `.ts/.vue`，因此该生成物一度 `FAIL stale=`。按既有生成入口 `make refresh.frontend.rendering_detail.inventory` 重新生成三支清单（渲染明细／视觉投影／官方设计对齐），随后复核通过；**未手改任何摘要**。这条也印证了证据失效规则：测试工具改动只失效依赖它的结果，业务页面证据不受影响。

未执行（保持未执行）：`ci.delivery.freeze.prepare`、`ci.local.quick`、`pr.push`、`local.dev.sync_demo`、`local.dev.snapshot`、模块 upgrade、fixture reset、发布快照。未新增或派生任何环境、数据库、端口、卷或凭据。

### 8.6 剩余缺口（诚实口径）

- 发票设计器旅程的绿灯只到 **R8**，且 R8 在归属守卫改造之前；改造后的 R9/R10 均被宿主网络中断打断。恢复条件：宿主 `br-*` 网桥不再抖动后的**一次干净运行**（不是重试同一失败）。
- 只读呈现档位（`data-render-profile="readonly"`，记录 8 `state=approve`）会丢弃只写输入桶，代表面按 `presentation_mode` / `relations_not_applicable: readonly-presentation` 记录 —— 这是产品合法行为，但**目前没有通过测试覆盖**。
- contract 办理入口（action 607）不在授权菜单内；payment 690 与 construction.contract 607 触达即 `/access-denied?reason=NAVIGATION_AUTHORITY_DENIED`。
- §7.5 约 6 组投影候选仍未登记；**台账仍为 42**，未扩大本批登记范围。
- 下一次设计器运行的行为：R11 留下的复查草稿 `233`（`ready`，本地 `expires_at` 13:56）是当前**唯一**未过期活跃草稿，也是运行前盘点的全部内容，因此下一次设计器运行会按设计 **fail-closed**（`preexisting_designer_draft:233`）。恢复入口不再是宽泛开关，而是按 id 与操作的授权 `FORM_LOWCODE_AUTHORIZED_DRAFT="233:stage,publish"`；也可等其过期（8h）。这是刻意行为，不是缺陷。
- R11 前后 `designer_drafts` 从 `[]` 变为 `[233]`（本运行自建、未发布、留作复查）；`233` 之外没有任何草稿被创建、改写、暂存、发布、回滚或删除。

## 8.7 第 3 次接管：本轮改动归属与唯一写入者

身份不变：分支 `feature/uc4-invoice-native-lowcode`，HEAD `025e37d2`，工作树 dirty，未提交、未冻结。
`make ci.local.iteration` 的增量计划把本分支相对已验证基线提交 `3323fb49` 的差异计为 44 条路径
（已提交分支差异 + 工作树差异），其中工作树 36 条（29 modified + 7 untracked）。
相对 §4.0 的 34 条基线新增两条：`make/runtime_ops.mk`（+1 行 node 接线）与
`frontend/apps/web/scripts/designer_draft_ownership_test.mjs`（本轮新增）。

| 归属 | 路径 | 说明 |
|---|---|---|
| 接管前已有（本轮未改） | `addons/smart_core/model/ui_business_config_change_set.py` 的 `_current_payload_hash`、`frontend/apps/web/src/pages/contractForm/ContractFormPage.css` 分隔线归属、`addons/*/tests/*`（除新增 4 例）、6 份 `docs/frontend_productization/rendering-detail/*.json`、`frontend/apps/web/scripts/formal_form_representative_journey.mjs` | 保留上一轮结论，本轮只读复核 |
| 接管前已有 + 本轮修改 | `frontend/apps/web/scripts/designer_draft_ownership.mjs`（重写为 inventory 排除式归属 + 按 id/操作授权）、`formal_form_designer_journey.mjs`、`formal_form_lowcode_loop.mjs`、`scripts/verify/local_dev_form_lowcode_scope.py`、`scripts/verify/local_dev_form_lowcode_browser.sh`、`addons/smart_core/tests/test_business_config_change_set.py` | 见 §8.8–§8.10 |
| 本轮新增 | `frontend/apps/web/scripts/designer_draft_ownership_test.mjs`、`make/runtime_ops.mk` 的一行接线 | 见 §8.9 |
| 仅验证、本轮未改 | `view_orchestrator.py`、`NativeFormTreeRenderer.vue`、`contractForm/*`、`form_structure_contract_projection_matrix.py`、`frontend_page_pattern_reference_parity_guard.py`、`generate_frontend_rendering_detail_inventory.py`、生成物清单 | 只重跑对应入口，未改内容 |

唯一写入者：本会话。未新建或派生任何环境、数据库、端口、卷、凭据或 fixture；未触碰草稿 `163`／`192`／`194`。

## 8.8 草稿保护边界收口（用户第 3 轮四项发现）

| 发现 | 原实现 | 收口 |
|---|---|---|
| 「发出 `open` 请求 ≠ 新建草稿」 | runner 用 `save_path=opened_new_change_set` 授权清理 | 归属改为**只由运行前盘点排除**判定（`resolveDesignerDraftOwnership`）；`open` 信号仅记为 `opened_at_save`，不再授权任何事 |
| 前置盘点与产品复用规则不一致 | 盘点按含 view 的 `target_key` 前缀筛选 | `designer_scope`/`designer_drafts` 镜像 `BusinessConfigChangeSetOpenHandler`：同属主/公司/库、`ACTIVE_CHANGE_SET_STATES`、未过期，命中 `target_key` 前缀**或** `(model, action_id)` 对，**不**按 view/role 过滤，形成超集 |
| 盘点→保存之间的时间窗 | 只在开跑前查一次 | 设计器第一笔写入前，用 `resume_only` **只读**探针按两条复用规则各问一次；出现未被盘点到的草稿 → `preexisting_designer_draft_appeared:<id>` 失败关闭 |
| 授权开关范围过宽 | `FORM_LOWCODE_ALLOW_RESUMED_DRAFT=1` 全局跳过既有草稿比对 | **删除**该开关；改为按 id 与操作的授权 `FORM_LOWCODE_AUTHORIZED_DRAFT="163:stage,publish;192:discard"`；未列出的草稿**始终**全文比对 |
| 清理边界 | `drafts` 是 token 集合，`finally` 直接 discard | `drafts` 改为 `token → change_set_id`；`resolveCleanupRelease` 若集合内含盘点内（他者）id → `foreign_draft_in_cleanup_set` **拒绝清理并把运行判为失败**（不是静默跳过） |
| 身份不明/盘点缺失 | 无判定 | `resolveDesignerDraftPolicy` 对缺失盘点、不可解析授权、授权了不存在的 id、存在未授权既有草稿一律 **fail-closed** |
| 运行身份 | 仅校验 `COMPOSE_PROJECT_NAME`/`DB_NAME` | 追加前置条件：基础 compose 不得固定 `container_name`，否则 profile 名无法作为运行容器的判别依据 |

后端语义（本轮只读复核，未改代码）：`open` 的复用域为属主 + 公司 + 库 + `state ∈ ACTIVE_CHANGE_SET_STATES` + 未过期，
支持 `target_key` 或 `model`+`action_id` 两条复用规则，并支持 `resume_only`（不存在时返回 `{"change_set": null}` 而**不创建**）。

## 8.9 行为反例（6 组，先补测试，只跑对应入口）

后端 `addons/smart_core/tests/test_business_config_change_set.py`（隔离测试草稿，未触碰 163／192／194）：

| 反例 | 行为断言 |
|---|---|
| `open` 返回既有草稿 | `target_key`、`model`+`action_id`、各自加 `resume_only` 共 4 次调用都返回同一 id 且 `state=draft`；变更集行与 item 行前后**全等**（无新建、无改写） |
| 同 action 不同 view | 两个 view 各自成稿；按 `target_key` 各回各稿；按 `model`+`action_id`（忽略 view）解析到最新一稿且**不新建第三稿**；两稿各自保留自己的 view item |
| `ready` 草稿 | `ready` 可被两条规则复用；`open` **不**把 `ready` 重置回 `draft`；行内容全等 |
| 发布版本变化后的旧草稿再编辑 | 见 §8.10 |
| 盘点后出现草稿 | `resolvePreexistingDraftProbe` 对他者 id → `preexisting_designer_draft_appeared` 失败关闭 |
| 异常退出 | `resolveCleanupRelease` 含他者 id → 拒绝清理（`release=[]`），即异常路径也不会删除他人草稿 |

Runner `frontend/apps/web/scripts/designer_draft_ownership_test.mjs`（`cases=5`，接线进既有 `make verify.business_config.unit`）：

- 归属：`openedAtSave=true` 仍**不**释放盘点内的 id；未识别 id 不释放；真正自建的 id 才释放。
- 旧开关不可复活：`1`／`true`／`yes`／`163`／`163:`／`abc:stage`／`163:frobnicate`／`163:stage,`／` :stage` 全部判为解析失败，
  且顺带收紧解析（尾部/连续分隔符视为笔误，不再静默放宽）。
- 授权粒度：`163:stage` 不允许 `163` 的 `publish`，也不允许 `192` 的任何操作；授权了不在盘点中的 id → 失败关闭；
  只授权部分草稿时其余草稿仍然阻断。
- 盘点缺失 → `designer_draft_inventory_missing` 失败关闭。

包装层比对（`local_dev_form_lowcode_browser.sh` 的后置守卫）另做了一次**反向对照**，证明它不是空断言：
同一份合成 fixture 喂入守卫，`draft→ready`（被暂存）、`draft→superseded`（被发布）、被丢弃（消失）、
同状态改内容、`write_date` 前移**全部判为失败**，只有「完全未变」与「显式授权 id」放行。

## 8.10 唯一产品改动复核：`current_payload_hash` 口径

改动本身：`ui.business.config.change_set.item.serialize()` 的 `current_payload_hash` 由 `base_payload_hash`（definition 口径）
改为 `stable_payload_hash(contract.contract_json)`，与 `StageHandler` 的 payload 守卫同口径；否则复用草稿的往返 hash 自相矛盾，
永远无法再次 stage。**该改动属接管前已有，本轮未再修改。**

必须证明的风险：序列化值现在跟随**当前已发布**配置，读它即读到最新 hash，所以「客户端读到什么」不能成为保护发布版本的东西。

证明（`test_published_version_change_blocks_stale_draft_stage_and_publish`）：

1. 旧草稿按 J1 建立 item 基线并入 `ready`；另一管理员随后发布 J2（`version_no` +1、`definition_sha256` 变化）。
2. 旧草稿读期间序列化**确实**返回 `stable_payload_hash(J2)` —— 即 served hash 已跟随新版本。
3. 三种客户端——同时回传 definition 旧 hash + 新 served hash、只回传新 served hash、两者都不回传——
   stage 全部 409 `STALE_CONFIG_DEFINITION`。
4. item 的 `draft_payload`／`base_payload_hash`／`target_contract_id`／`base_version_no` 与基线**全等（未暂存）**；变更集仍 `ready`。
5. publish 409 `CHANGE_SET_VERSION_CONFLICT`；已发布合同仍是 J2、`version_no` 不变、版本行数不变（**未发布**）。
6. rollback 409 `CHANGE_SET_NOT_PUBLISHED`（**未回滚**）。

结论：阻断陈旧覆盖的责任在 definition 与 item 基线两层，**不在**客户端回传的 payload hash。

本轮另发现并修一处真实缺陷：`scripts/verify/local_dev_form_lowcode_scope.py` 使用 `user.company`（`res.users` 无此字段），
首次执行即 `AttributeError`；已改为 `user.company_id`。该行属新 inventory 代码，说明它此前**从未被执行过** —— 也是「未执行 ≠ 通过」的直接例证。

## 8.11 网络归因措辞纠正

- 已证明的是**发生了传输中断**：R10 的 `failed_requests` 为 `popup_1` 23 条 + `main` 8 条 `net::ERR_NETWORK_CHANGED`。
- 宿主 13 个 `DOWN/UNKNOWN` 接口（含 `br-*`）与 33 个 docker 网络只是**同时存在的现象**，
  既**不能证明原因**，也**不能作为「已恢复」的判据**。
- 因此这条不再作为代码修复的阻塞项；R11 与只读传输检查在本轮均未复现中断（`failed_requests=[]`），
  这只说明**本次运行**没有中断，不构成网络已恢复的结论。

## 8.12 R11：守卫改造后的发票设计器闭环与只读传输检查

| 运行 | 入口 | 结果 | 关键事实 |
|---|---|---|---|
| 只读传输检查 | `FORM_LOWCODE_TOPIC=invoice FORM_LOWCODE_REPLAY=1 make local.dev.form_lowcode.browser` | passed | `ok=true`、`restored=true`、`failed_requests=[]`、`browser_errors=[]`；设计器旅程按设计跳过（`change_set_id=null`）；`designer_draft_policy=proceed`、`inventory_ids=[]` |
| R11 设计器闭环 | `FORM_LOWCODE_TOPIC=invoice make local.dev.form_lowcode.browser` | passed | `ok=true`、`restored=true`、`change_set_id=231`、`save_path=opened_new_change_set`；探针 `proceed`（无既有可复用草稿）；归属 `authored_by_this_run`；`cleanup_guard=proceed`、`recovery_state.released=true`、`draft_tokens_held=0`；`failed_requests=[]`、`browser_errors=[]`；预览/发布/回滚/越界页/视觉顺序全绿 |

运行后草稿事实（只读回读）：`231` = `superseded`（本运行自建、发布后回滚，`publish_ok=true`）；
`233` = `ready`（本运行自建、未发布，留作集中浏览器复核）；当前唯一未过期活跃草稿 = `233`。
历史草稿 `155`–`194` 全部为终态（`superseded`/`discarded`），其中 `158` 早已过期故不入盘点。

代表面（付款/客户/合同/材料/结算）在本轮 runner 上重跑，5 主题 `exit=0`：
`ok=true`、`restored=true`、`failed_requests=[]`、`browser_errors=[]`、`cleanup_guard=proceed`；
材料面仍给出页签（`入库明细`/`说明与附件`/`来源追溯` 均有内容）、关系集合、
全宽明细按承载列度量（`line_ids` `column_fill=0.998`、`columns=1`）与章节导航目标。

未执行（保持未执行）：`ci.delivery.freeze.prepare`、`ci.local.quick`、`pr.push`、`local.dev.sync_demo`、
`local.dev.snapshot`、模块 upgrade、fixture reset、发布快照。未新增或派生任何环境、数据库、端口、卷或凭据。


## 8.13 第 4 次接管：草稿保护闭环、共享吸顶布局与代表面复核（用户第 5 轮两项工作包）

身份不变：分支 `feature/uc4-invoice-native-lowcode`，HEAD `025e37d2`，工作树 dirty，未提交、未冻结。
本轮实测工作树 = **39 条路径（32 modified + 7 untracked）**；更正上一版口径：§8.7 记的「29 modified + 7 untracked」
与交接稿的「30 modified + 9 untracked」都不是当前实测值，以本节 32/7 为准。

### 8.13.1 归属与唯一写入者

| 归属 | 路径 | 本轮动作 |
|---|---|---|
| 接管前已有（前几轮，本轮未改） | `addons/smart_core/handlers/business_config_change_set.py`（`payload["created"]`，14:10 写入）、`addons/smart_core/model/ui_business_config_change_set.py`、`addons/smart_core/tests/test_business_config_change_set.py`（14:13 追加 2 例）、`view_orchestrator.py`、`formal_config_contract_fields.py`、`ContractFormProductHeader.vue` / `ContractFormPage.css` 吸顶载体、6 份 `rendering-detail/*.json`、`formal_form_representative_journey.mjs`、`local_dev_form_lowcode_scope.py` / `_browser.sh`、`designer_draft_ownership.mjs`、6 个新增文件 | 仅复核/仅重跑入口 |
| 接管后修改（本轮写入） | `frontend/apps/web/scripts/formal_form_lowcode_loop.mjs`、`designer_draft_ownership_test.mjs`、`formal_form_invoice_journey.mjs`、本文档 | 见 §8.13.2 |
| 仅验证（本轮未改） | `addons/smart_construction_core/tests/test_form_structure_consumption.py`、`formActionPlaceholderGate.ts`、`native_form_structure_responsibility_test.ts`、`make/*.mk` 既有接线 | 只跑对应入口 |

唯一写入者：本会话执行体。未新建/派生环境、数据库、端口、卷、凭据或 fixture；未触碰 `163`／`192`／`194`；`233` 完整保留（见 §8.13.5）。

### 8.13.2 本轮实际改动（先机制审查，再决定是否扩大登记）

| 文件 | 改动 | 为什么必须改 |
|---|---|---|
| `formal_form_lowcode_loop.mjs` | 写入授权门从 `designerOnly` 分支**顶部**移到**写入分支内部**；只读 replay 不再被写入授权阻断，策略仍作为观察记录；新增失败关闭时的只读归因探针；成功路径也落盘有界诊断 | 机制缺陷：「拒绝**配置写入**」被实现成「拒绝一切读取」。只读 replay 不 `open`、不 `stage`，要求写入授权只会把入口面藏在别人的草稿后面，无任何安全收益。授权必须紧贴第一笔写入之前，且不得阻断只读动作（与用户第 3 轮「前置 vs 后置」发现同源） |
| `formal_form_lowcode_loop.mjs` | 失败关闭时用 `resume_only` 只读探针记录 `would_resume` / `probe_shape`，写入 `designer_draft_refusal` | 让拒绝**可归因、不空洞**：若无盘存却无命中，说明守卫是过期而非保护 |
| `formal_form_lowcode_loop.mjs` | 成功也写 `report.diagnostics`；replay 的成功日志改为「PASS read-only replay」 | 「本次无传输中断」此前只能由**缺失字段**推断，与「探针根本没挂上」同形；日志不得把跳过设计器旅程的运行写成「PASS formal designer journey」 |
| `designer_draft_ownership_test.mjs` | 新增反例 9：runner 对 `designer_draft_ownership.mjs` 的具名导入必须真实导出（cases 8→9） | 实测缺陷：`node --check` 只查语法，缺失导出仍通过，直到浏览器运行登录后才炸（本轮真实发生一次）。这是最便宜的、能覆盖该缺陷类的既有登记入口 |
| `formal_form_invoice_journey.mjs` | 财务角色 bypass 面（789）在**自己的 context 内**记录失败取证：URL／readyState／正文／`[data-field-name]` 可见性／DOM 落盘／截图／pageerror／console error／失败请求 | 该面用的是独立 `browser.newContext()`，外层 runner 既未插桩、又在失败前 `context.close()`，因此原取证只能拿到**开启者页面**（实测 `failurePage.url=/access-denied`，与真正失败的页面无关），无法归因 |

未扩大登记范围：约 6 组投影候选仍留在台账，未新增缺陷条目；未批量改字段。

### 8.13.3 根因：material 设计器闭环失败 = 运行进程未加载后端改动（环境层，非产品层）

第一次 material 设计器闭环失败于 `resumed_designer_draft_not_probed:265`，报告事实：
`save_path=opened_new_change_set`、`save_open={requested_fresh: true, reported_created: null}`、
`draft_ownership={release:false, reason:'creation_not_proven_by_this_run', created:false}`。
即保存时确实以 `fresh:true` 新建了草稿，但响应里**没有** `created` 字段，归属无法被证明，守卫据此拒绝（行为正确）。

归因（只读取证）：

| 事实 | 值 |
|---|---|
| `sc-local-dev-odoo-1` 进程 1 启动 | 2026-09-17 03:41:36 UTC（= 11:41:36 CST） |
| `handlers/business_config_change_set.py` mtime | 2026-09-17 **14:10:20 CST**（晚于进程启动） |
| 容器 odoo 命令行 | `python3 /usr/bin/odoo -c /var/lib/odoo/odoo.conf` —— **无 `--dev`**，Python 不热重载 |
| 其余后端改动 mtime | 10:21–11:40:46（均早于启动，已在运行时内） |

结论：长驻 dev 进程持有的是**改动前**的 handler，因此 `created` 凭据在运行时里根本不存在。这是「未执行 ≠ 通过」的同类事实——
该凭据的端到端路径此前从未在**真实运行时**上被跑过。修复动作按受管入口加载：`make local.dev.restart`（L3，未新增环境）。

### 8.13.4 本轮运行结果

| 层 | 入口 | 结果 | 关键事实 |
|---|---|---|---|
| L1 | `make ci.local.iteration` | passed | `coverage=L1_only`、`receipt=none`、`change_state=dirty` |
| L1 | `make verify.business_config.unit` | passed | `designer_draft_ownership cases=9`、presentation 7、summary 6、race 9；语言/边界守卫全绿 |
| L2 | `make local.dev.test MODULE=smart_core TEST_TAGS='/smart_core:TestBusinessConfigChangeSet'` | passed | **25 tests, 0 failed, 0 error(s)**（含前轮追加的 `created` 凭据 2 例与陈旧版本阻断例） |
| L3 | `make local.dev.restart` | passed | 仅加载已改后端，无 upgrade/fixture/发布快照 |
| L4 | `FORM_LOWCODE_TOPIC=invoice FORM_LOWCODE_REPLAY=1` 只读传输检查 | **passed**（上轮 failed，本轮已修复） | `ok=true`、`restored=true`、`change_set_id=null`；策略以观察形式记录 `fail_closed / preexisting_designer_draft:233`；`cleanup_guard=proceed`、`draft_tokens_held=0`；包装层打印 `business fingerprints unchanged` |
| L4 | `FORM_LOWCODE_TOPIC=invoice`（受影响设计器闭环） | **未通过（被保留草稿正确阻断，非缺陷）** | `preexisting_designer_draft:233`；`designer_draft_refusal={blocking:[233], would_resume:233, probe_shape:'serialized_change_set'}` |
| L4 | `FORM_LOWCODE_TOPIC=material FORM_LOWCODE_DESIGNER=1 FORM_LOWCODE_AUTHORIZED_DRAFT='265:stage,preview,publish,rollback'` | **passed** | 写入路径在新归属/授权代码下闭环：`policy.allowed={265:[stage,preview,publish,rollback]}`、两条复用规则探针均命中 265、`pre_write_gate=proceed ids=[265,265]`、`resumed_authorized_draft=proceed`、`preserved_draft=creation_not_proven_by_this_run`（不释放、不删除）、`stages.publication/designer` 全绿、`review_draft_ownership={release:true, created:true, fresh_requested:true}`（**`created` 凭据已在运行时生效**）、`recovery=[]`、`browser_errors=[]` |

关于 `265`：它是本会话上一条 material 运行在**陈旧运行时**下自建、因 `created` 缺失而无法证明归属的草稿（`save_path=opened_new_change_set` 有记录）。
本轮按既有机制用**具体 id + 具体操作**授权其复用（不是恢复已删除的宽泛开关），闭环后它已进入终态；包装层前后比对证明其余既有草稿全文不变。
运行后 material 盘存只剩 `267`（本轮自建、`ready`、留作集中浏览器复核）。

### 8.13.5 发票设计器闭环：拒绝是正确结果，且证明零写入

`233` 是 R11 自建、未发布、用户要求保留的复核草稿。本轮不为其放宽任何守卫，因此发票设计器写入路径按设计拒绝。
零写入证据（同一次运行的报告 + 包装层回读）：

- 意图序列仅有 `ui.contract.v2`×9 与 **1 次** `change_set.open`（我新增的只读归因探针，`resume_only`）；**没有** `stage`／`preview`／`publish`／`rollback`／`discard` 任何一次。
- `change_set_id=null`、`save_path=null`、`draft_ownership=null`、`draft_tokens_held=0`、`recovery=[]`。
- 拒绝不是空洞的：只读探针显示产品**确实会**复用 233（`would_resume: 233`，`serialized_change_set`），守卫只是不授权写入。
- 运行后只读回读：`233` 仍为 `ready`，`write_date=2026-09-17 05:56:44.925326`（与运行前逐字相等），item 190 摘要 `21fe4ca032401c07` 不变；包装层 `business fingerprints unchanged`。

### 8.13.6 未归因项（不得靠重试掩盖）

| 现象 | 观察 | 当前归属 |
|---|---|---|
| 财务角色 bypass 面（action 789）create 页 `[data-field-name="note"]` 30s 未可见 | 同一代码/同一输入 4 次运行中 1 次失败（run B），前后两次均通过；失败时取证残缺（拿到的是开启者页面 `/access-denied`），**无法判定**是加载失败、字段合法隐藏、修剪误删还是定位器问题 | **未归因**。本轮已补齐该面自身 URL／DOM／字段可见性／pageerror／请求取证；在事实改变前不得重跑这一失败 |
| 传输中断 | 本轮 invoice 只读检查记录 `net::ERR_NETWORK_CHANGED`×40；material 闭环运行记录 `net::ERR_ABORTED`×12（其中一次通过） | 只证明**发生了中断**；接口/Docker 网络数量既不能证明原因，也不能作为「已恢复」判据。中断出现在**通过**的运行里，因此不能据此推断上面那次超时的成因 |

### 8.13.7 复核交接面（本轮变化）

- 发票 `233` 的交接 URL 原只存在于 `artifacts/uc4-invoice-lowcode/browser/designer-report.json` 的 `review` 块，
  被本轮同一文件名的**拒绝**报告覆盖。已在未跟踪证据存储中重新保全为 `review-handoff-233.json`（含 token，故不入跟踪文档），
  并用只读回读校验：`change_set.token` 与记录值一致、`233` 仍 `ready`。
  注意：其 **preview token 已于 14:16 CST 过期**，designer URL 在草稿存活期内可用；重开预览需对 `233` 授权一次 `preview`。
- material 交接 URL 仍在 `artifacts/lowcode-form-loop/browser/designer-report.json` 的 `review` 块（本轮生成、未过期）：`draft_id=267`。
- 台账仍为 42；未冻结、未跑 Quick、未推送、未部署。

## 8.14 第 5 次接管：两个验收缺口收口（拒绝反例登记 + 789 针对性复验）

身份不变：`feature/uc4-invoice-native-lowcode`、HEAD `025e37d2`、工作树 39 条（32 modified + 7 untracked）、未冻结。
状态口径：**页面整改复核通过｜批次验收待收口｜未集成｜未部署｜台账 42（当时）**。
用户已完成浏览器复核：1088 操作行底边 205px／导航起点 222px、390 操作按钮完整可见且正文标题不再被遮、备注视图单一、
正式「表单设置」可打开且标签/排序/分组/显隐摘要仍在。吸收结论：吸顶布局不再作为缺口。

### 8.14.1 缺口一：发票 233 保护性拦截登记为「拒绝反例通过」

| 项 | 内容 |
|---|---|
| 入口 | `FORM_LOWCODE_TOPIC=invoice make local.dev.form_lowcode.browser`（`designer-loop-invoice-r5.log`） |
| 结果 | 退出码 2；`preexisting_designer_draft:233`；**登记为通过** |
| 通过依据 1（拒绝非空洞） | 只读 `resume_only` 归因探针：`would_resume=233`、`probe_shape=serialized_change_set` —— 产品确实会复用 233，守卫只是不授权写入 |
| 通过依据 2（零越权写入） | 意图序列 = `ui.contract.v2`×9 + 1 次只读 `change_set.open`；**无** `stage`／`preview`／`publish`／`rollback`／`discard`；`change_set_id=null`、`draft_tokens_held=0`、`recovery=[]` |
| 通过依据 3（既有草稿未变） | 包装层 `business fingerprints unchanged`；只读回读 `233` 仍 `ready`、`write_date=2026-09-17 05:56:44.925326`、item 190 摘要 `21fe4ca032401c07` 逐字不变 |
| 它**不**证明什么 | 不证明发票**正向**闭环（stage→preview→publish→rollback）已通过。材料闭环（§8.13.4）只作为**共享机制**证据，不替代发票正向验收 |

### 8.14.2 缺口一方案：保留 233 的发票正向闭环（无需改代码，已验证前提）

前提对称性（本轮只读核对）：产品复用域 `BusinessConfigChangeSetOpenHandler` 的 domain 含
`("expires_at", ">", fields.Datetime.now())`；盘点侧 `_is_expired()` 用同一条 `expires_at <= now` 规则。
⇒ 过期后**盘点与产品同时**不再看到该草稿，不存在"盘存已剔除但产品仍复用"的不对称。
`233.expires_at = 2026-09-17 13:56:44 UTC = 21:56:44 CST（今日）`。

| 步骤 | 动作 | 判据 |
|---|---|---|
| P1-a（只读前置） | `FORM_LOWCODE_TOPIC=invoice FORM_LOWCODE_SCOPE_ONLY=1 make local.dev.form_lowcode.browser` | `designer_drafts` 不再含 233 |
| P1-b（只读前置） | 同一次运行内看 `designer_draft_probe` | `probe_shapes=["resume_only_miss","resume_only_miss"]`；若 a 成立而 b 不成立 ⇒ 盘点/产品不对称，属**机制缺陷**，修责任层，**不得**放宽守卫 |
| P1-c（正向闭环） | `FORM_LOWCODE_TOPIC=invoice make local.dev.form_lowcode.browser`，**不设** `FORM_LOWCODE_AUTHORIZED_DRAFT` | 期望形状与 R11 一致：`save_path=opened_new_change_set`、`review_draft_ownership.created=true`、`publication/preview/rollback/outside_page` 全绿、`recovery=[]`、包装层指纹不变；233 行全程未被触碰 |

- 备选（仅在必须早于 21:56 收口时）：`FORM_LOWCODE_AUTHORIZED_DRAFT='233:stage,preview,publish,rollback'`。
  这是既有的「具体 id + 具体操作」授权机制，不需要新实现；**不推荐**，因为它会消费刚复核过的现场并把 233 变为 `superseded`。
- 可选：若需要再次打开 233 的预览，授权 `233:preview` 一次即可重发 preview token（其 preview token 已于 14:16 CST 过期）。这仍是对 233 行的一次写入。
- **明确排除**：删除/丢弃 233（用户已指示不为运行方便删除）。
- 固有代价（本轮实测得到，供后续批次评估，不在本批实施）：设计器旅程的 review 交接**每次都会**新建一个 `ready` 复核草稿
  （R11 留下 233，本轮 material 留下 267）。该草稿会按同一 8 小时规则阻断下一次同目标的设计器运行，直至过期或被显式授权。
  因此建议把发票闭环安排在集中复核之前：新产生的复核草稿即成为发票复核现场。

### 8.14.3 缺口二：action 789 针对性复验（一次，只读）

入口：`FORM_LOWCODE_TOPIC=invoice FORM_LOWCODE_REPLAY=1 make local.dev.form_lowcode.browser` → 通过（`transport-replay-invoice-r6.log`）。
本轮为 `formal_form_invoice_journey.mjs` 增加**判定器**（不改断言）：在财务角色面自身 context 内分类
「页面未加载／字段未渲染／字段已渲染但隐藏／字段可见」，并把**传输证据单独成桶**。

| 判定 | 值 |
|---|---|
| `verdict` | **`field_visible`**（`at: after_assertion`） |
| 页面加载 | `loaded=true`、`app_shell_children=1`、正文 590 字符、无「加载失败/无权访问」 |
| 字段 | `note_nodes=1`、`note_visible_nodes=1`；`field_nodes=37`、`section_nav_items=9` |
| 复现性 | **未复现**（不是「字段合法隐藏」，也不是「页面未加载」，也不是「定位失败」） |

传输证据（**单独记录，不判为产品缺陷，也不声称零错误**）：该面自身 `pageerrors=[]`、`console=[]`、
`failed_requests=[{/api/v1/intent, net::ERR_ABORTED} ×2]`；同一次运行的运行级诊断记录 `net::ERR_NETWORK_CHANGED`×40。
即：本环境**仍有传输中断发生**，而在**中断存在**的一次运行里该字段为可见。因此传输中断既不能判定为本次 789 现象的成因，
也不能作为「已恢复」判据；789 现象在证据改变前不再重跑——但现在若复发，判定器会直接给出类别。

### 8.14.4 本轮改动与层证据

本轮唯一代码改动：`frontend/apps/web/scripts/formal_form_invoice_journey.mjs`（789 判定器 + 传输分桶；既有断言未放宽）。
层证据：L1 本轮重跑 `ci.local.iteration` passed（`l1-iteration-r6.log`），`verify.business_config.unit` passed（cases=9，被覆盖文件未改）；
L2 沿用 §8.13.4（25 tests, 0 failed）；L4 本轮新增 `transport-replay-invoice-r6.log`（只读）。
生成物：`artifacts/uc4-invoice-lowcode/browser/replay-report.json`（含 `note_visibility`）、`review-handoff-233.json`。

未执行（保持未执行，本轮未变化）：`ci.delivery.freeze.prepare`、`ci.local.quick`、`pr.push`、`local.dev.sync_demo`、
`local.dev.snapshot`、模块 upgrade、fixture reset、发布快照。台账保持 **42**。

## 8.15 第 6 次接管：发票正向闭环通过、popup 断点归因与机制修复（用户第 6 轮两项缺口）

身份：分支 `feature/uc4-invoice-native-lowcode`、HEAD `025e37d2`、工作树 41 条（32 modified + 9 untracked），未冻结。
状态口径：**两个验收缺口均已收口｜批次验收待集中复核｜未集成｜未部署｜台账 42（当时）**。

### 8.15.1 归属：接管前已有 / 接管后修改 / 仅验证

| 类别 | 内容 |
|---|---|
| 接管前已有（本轮未改） | §8.13/§8.14 记录的 39 条改动（草稿守卫与 `created` 归属、共享吸顶布局、789 判定器、`current_payload_hash` 口径等） |
| 接管后修改（本轮） | ① `frontend/apps/web/scripts/formal_form_designer_journey.mjs`（popup 就绪门 + 失败时 popup 自身证据；既有断言未放宽）② 新增 `frontend/apps/web/scripts/designer_popup_readiness.mjs` ③ 新增 `frontend/apps/web/scripts/designer_popup_readiness_test.mjs` ④ `make/runtime_ops.mk` 一行（把 ③ 挂进既有 `verify.business_config.unit`） |
| 仅验证（未改代码） | 233 与草稿表只读回读、两次发票设计器运行、789 只读 replay、L1/L2 |
| 唯一写入者 | 本会话。历史保留工作树 4 个全程未触碰，不作预算违规判定 |

### 8.15.2 缺口一：保留 233 的发票正向闭环 —— 已通过

| 步骤 | 入口 | 结果 |
|---|---|---|
| P1-a 只读前置 | `FORM_LOWCODE_TOPIC=invoice FORM_LOWCODE_SCOPE_ONLY=1 make local.dev.form_lowcode.browser` | `designer_drafts []`（233 已过期，不入盘点）→ `scope-invoice-r6.json` |
| P1-b 对称性 | 同轮 `designer_draft_probe` | `probe_shapes=["resume_only_miss","resume_only_miss"]` —— 盘点与产品同时不再复用 233，无不对称 |
| P1-c 正向闭环 | `FORM_LOWCODE_TOPIC=invoice make local.dev.form_lowcode.browser`（**不设授权**） | **exit 0 / `ok=true` / `restored=true`** → `designer-loop-invoice-r7b.log` |

闭环事实（`artifacts/uc4-invoice-lowcode/browser/designer-report.json`）：
`change_set_id=272`、`save_path=opened_new_change_set`、`save_open={requested_fresh:true,reported_created:true}`、
`draft_ownership={release:true,reason:'created_by_this_run'}`、`designer_draft_probe=proceed`、`designer_pre_write_gate=proceed`、
`cleanup_guard={decision:proceed,foreign:[]}`、`recovery=[]`、`recovery_state={draft_tokens_held:0,rollback_tokens_pending:0,released:true}`、
`stages.publication={published_content,final_contract,browser,isolation 全 passed}`、`stages.outside_page=passed`（787 越界面）、
`visual_order=passed`（`invoice_no_y=364`，未触碰列仍共享列）。

写事实（只读回读，`now=2026-09-17 14:28:34 UTC`）：`272` superseded（本运行自建、发布后回滚，回滚记录 `273` published）、
`274` ready（本运行自建、未发布，留作集中复核）、**`233` 全程未被触碰**（`state=ready`、`expires_at=13:56:44 UTC` 已过期、
`write_date=2026-09-17 05:56:44.925326` 与运行前逐字一致、item 写入时间一致）。

⇒ 「拒绝反例通过」（§8.14.1）与「正向闭环通过」现在**同时**成立于发票面，且未以材料面替代发票面、未删除 233。

### 8.15.3 新断点归因：popup 不是产品结构缺陷，是加载未在断言窗口内完成

r6 的失败是一条**不可归因的定位器超时**（`formal_form_designer_journey.mjs:214`，30s 内未见 `受管发票号码`）。本轮先补诊断能力、再复跑：

| 证据 | 内容 |
|---|---|
| r7（补诊断后一次运行，`designer-loop-invoice-r7.log`） | popup URL 为正式入口路由（`route_matches_entry=true`）、`ready_state=complete`、`app_shell_children=1`、`field_nodes=0`、标题 `新建进项发票 · 加载中`、`pageerrors=[]`、`console=[]` |
| popup 自身失败请求 | 仅 Vite 模块 `net::ERR_ABORTED`（`/src/App.vue`、`/src/app/init.ts` …）—— 正是**本运行自己 `business.reload()` 取消首个文档**所致，不是产品请求失败 |
| r7b（同一 URL、同一构建、同一账号） | 通过；popup 内 `system.init` 200（2.4s）、`ui.contract.v2` 200（2.6s）、`api.data` 200，且因 reload 出现**两次 bootstrap** |

结论：**同一 URL/构建/账号既能停在「加载中」也能正常渲染**，差别是加载耗时（本环境 `ERR_NETWORK_CHANGED` 间歇中断仍在发生）。
因此该现象既不属结构消费缺陷、也不属字段合法隐藏或修剪误删；`reload()` 紧跟 popup 创建会取消首个文档的模块请求，属 runner 侧时序，
不构成产品证据。归因对象 = **测试工具层（runner）就绪判定与证据采集**，不是 P0/P1 产品层。

### 8.15.4 机制修复（只改测试工具层，断言语义不变）

`formal_form_designer_journey.mjs` 的 popup 段：创建即挂 `pageerror`/`console`/`requestfailed` + **intent 生命周期**
（started/answered/failed/pending；reload 边界把被取消的请求移入 `api_abandoned`，避免把旧文档的请求误报为挂起）
→ 有界就绪探针（shell 挂载 **且** 页面自身 loading 标题消失，上限 15s）
→ 判定分类 → **严格断言原样执行** → 断言失败时再把 popup 自身 URL/DOM/截图/请求结果写盘（`failure-designer-popup-dom.html`、`failure-designer-popup.png`）。

判定分类抽为 `designer_popup_readiness.mjs`（`popup_unreachable` / `popup_route_denied` / `popup_shell_not_mounted` /
`popup_still_loading` / `popup_ready_for_assertion`），并明确**只有已证实的失败态才可中断**：路由为 `/login` 或 `/access-denied`，
或 popup 确实已被关闭；其余（慢加载、shell 未挂载、状态读不到）一律落到严格断言。因此该诊断**不可能把本可通过的运行判成失败**
（可中断集合是 v1 的子集）。r7 那次误判（用 body 文案「无权访问」当拒绝证据，实际是菜单 chrome 对无权入口的合法文案）即在此修掉。

行为反例测试 `designer_popup_readiness_test.mjs`（cases=6：已关闭 vs 仅读不到状态、两种拒绝路由、菜单 chrome 含拒绝文案仍算已挂载页、
shell 已挂载但仍在加载、shell 未挂载、路由证据），挂进既有 `verify.business_config.unit`（只加一行，不新建入口/环境/凭据）。

### 8.15.5 缺口二：action 789 判定器（同一运行再次确认）

`note_visibility`（`at: after_assertion`）：`verdict=field_visible`、`loaded=true`、`app_shell_children=1`、正文 590 字符、
`note_nodes=1`、`note_visible_nodes=1`、`field_nodes=37`、`section_nav_items=9`。入口隔离同时成立（`sc_test_admin` →
`/access-denied?reason=NAVIGATION_AUTHORITY_DENIED`；财务 principal → 正常打开）。
传输证据**单独成桶**：该面 `pageerrors=[]`、`console=[]`、`failed_requests=[/api/v1/intent net::ERR_ABORTED ×2]`；运行级另有 `ERR_NETWORK_CHANGED ×40`。
⇒ 既不作产品缺陷，也不声称零错误通过；若复发，判定器直接给出类别。

### 8.15.6 本轮验证矩阵

| 层 | 命令 | 结果 | 非零测试数 |
|---|---|---|---|
| L1 | `make ci.local.iteration` | passed（`l1-iteration-r7.log`） | 16（策略守卫） |
| L2 | `make verify.business_config.unit` | passed（`business-config-unit-r7.log`），含新 `[designer_popup_readiness] PASS cases=6` | 177（11+5+6+5+9+64+24+48+5） |
| L4 | `FORM_LOWCODE_TOPIC=invoice make local.dev.form_lowcode.browser` | passed（`designer-loop-invoice-r7b.log`） | — |
| L4（只读） | `FORM_LOWCODE_TOPIC=invoice FORM_LOWCODE_REPLAY=1 make local.dev.form_lowcode.browser` | passed（`transport-replay-invoice-r6.log`，输入未变故沿用） | — |

未执行（保持未执行）：`ci.delivery.freeze.prepare`、`ci.local.quick`、`pr.push`、`local.dev.sync_demo`、`local.dev.snapshot`、
模块 upgrade、fixture reset、发布快照。台账保持 **42**，约六组投影候选继续挂账、不登记。

### 8.15.7 剩余缺口（诚实口径）

1. **工具版本与通过结果的落差**：通过的那次闭环（r7b）跑在 popup 门第一版（shell 就绪 + body 文案判定）上；本轮随后细化的版本
   **只收紧诊断、只对已证实状态中断、不新增失败路径、不放宽断言**（可中断集合是子集），故不改判该通过结果；
   但「最终工具版本下的整轮发票闭环」尚未重跑。阻塞原因：本次通过自建的复核草稿 `274` 为 `ready` 且未过期，
   按既有规则会拒绝下一次同目标设计器运行（到期 `2026-09-17 22:24:12 UTC = 06:24:12 CST 次日`），或需显式授权 `274:<具体操作>`；
   两者都不应为跑一次而删掉/用掉交接草稿。
2. **popup 加载耗时的成因**：已证明「同一面既可停住也可通过，且同运行存在传输中断」，未证明具体哪一跳；
   就绪门在复现时会直接给出 `api_pending` 与断言失败时快照。
3. **复核交接面**：发票 `274`（`ready`，未发布）与材料 `267`（`ready`，未发布）是两个未过期草稿，各自阻断同目标设计器运行；
   `274` 的 preview token 到期 `14:44:12 UTC`，其设计器 URL（含 `change_set_token`，已与库回读校验）随草稿 `ready` 状态有效。
   交接面已保全为 `artifacts/uc4-invoice-lowcode/browser/review-handoff-274.json`（照 §8.13.7 的 `review-handoff-233.json` 口径）。

## 8.16 续推：最终工具版本下的发票正向闭环（授权续用既有草稿的正向路径）

身份不变：分支 `feature/uc4-invoice-native-lowcode`、HEAD `025e37d2`、工作树 41 条（32 modified + 9 untracked），未冻结。
状态口径：**两个验收缺口在最终工具版本下均已收口｜待集中浏览器复核｜未集成｜未部署｜台账 42（当时）**。

### 8.16.1 阻塞与解法（不删、不弃、不绕过守卫）

§8.15.7 的剩余落差是「通过结果跑在就绪门第一版」，而重跑被草稿 `274`（`ready`、未过期）按既有规则拒绝。
解法使用既有机制本身：`FORM_LOWCODE_AUTHORIZED_DRAFT='274:stage,preview,publish,rollback'`——**具体 id + 具体操作**授权，
让本次运行**续用** 274，并由运行末尾产出新的复核草稿作为交接面。
运行前只读记录（`now=14:44:03 UTC`）：`274` `ready`、`write_date=14:24:12.279084`、item 225 digest `e09e086a26cd3776`；
`233` `write_date=05:56:44.925326`、digest `e09e086a26cd3776`；`267` `write_date=06:51:17.975111`、digest `a516b696b45d7eca`。

### 8.16.2 机制修复（工具层第二处）：不再自造 abort 风暴

popup 创建后立即 `reload()` 会取消首个文档的**在途模块请求**（r7/r7b 证据：12–20 条模块 `ERR_ABORTED`）。
改为**先有界等待首个文档 `load`（≤10s）再冷加载**：既保留「冷加载渲染新发布配置」这一证明，又不再自造 abort 风暴，
且在中断网络上省掉一次整图重复拉取。可中断集合不变（仍只有已证实状态，见 §8.15.4）。

### 8.16.3 结果（`designer-loop-invoice-r8.log`，exit 0）

| 项 | 值 |
|---|---|
| 结论 | `ok=true`、`restored=true`、`recovery=[]`、`recovery_state={draft_tokens_held:0,rollback_tokens_pending:0,released:true}` |
| 保存路径 | `save_path=resumed_existing_draft`；`save_open={requested_fresh:false,reported_created:null}` |
| 归属（关键） | `draft_ownership={release:false,reason:'creation_not_proven_by_this_run'}` —— 运行**没有**把续用草稿当自己的 |
| 授权正向路径 | `resumed_authorized_draft={id:274,operations:[stage,preview,publish,rollback],decision:proceed}`、`preserved_draft={id:274}`、`cleanup_guard={decision:proceed,foreign:[]}` |
| 盘点/探针/前置门 | `designer_draft_policy={inventory_ids:[274],allowed:{274:[…]}}`、`probe_shapes=["serialized_change_set","serialized_change_set"]`（两条产品规则都指向 274）、`designer_pre_write_gate=proceed(ids:[274,274])` |
| 阶段 | `publication={published_content,final_contract,browser,isolation 全 passed}`、`outside_page=passed(787)`、`visual_order=passed`（`invoice_no_y=364`，未触碰列仍共享列） |
| popup 证据 | `verdict=popup_ready_for_assertion`、`blocking=false`、`ready_wait_ms=7791`、`field_nodes=42`、标题已脱离「加载中」、`failed_requests=1`、`api_abandoned=[system.init @reload]` —— 与 §8.15.3「加载耗时可变」一致 |
| 789（同一次运行） | `note_visibility.verdict=field_visible`、`field_nodes=37`；传输错误仍单独成桶 |

写事实（只读回读，`now=14:48:02 UTC`）：`274` → `superseded`（item 225 digest `e09e086a26cd3776` → `e79f13e7a08b6484`，
发布后回滚记录 `275` published）；新复核草稿 `276` `ready`（item 226 digest `e09e086a26cd3776`，未发布）；
**`233` 未被触碰**（`state=ready`、`write_date=05:56:44.925326`、digest 逐字不变）；**`267`（材料）未被触碰**（`write_date` 与 digest 不变）。
⇒ 授权写入只落在被明确授权的 274 及其回滚记录、以及本轮自建 276；其他草稿完整比对零变化。

### 8.16.4 验证矩阵（更新）

| 层 | 命令 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | passed（`l1-iteration-r8.log`） |
| L2 | `make verify.business_config.unit` | passed（`business-config-unit-r8.log`），含 `[designer_popup_readiness] PASS cases=6`（177 tests） |
| L4 | `FORM_LOWCODE_TOPIC=invoice FORM_LOWCODE_AUTHORIZED_DRAFT='274:stage,preview,publish,rollback' make local.dev.form_lowcode.browser` | passed（`designer-loop-invoice-r8.log`，最终工具版本） |
| L4（只读，沿用） | `FORM_LOWCODE_TOPIC=invoice FORM_LOWCODE_REPLAY=1 …` | passed（输入未变，见 §8.15.5/§8.15.6） |

未执行（保持未执行）：`ci.delivery.freeze.prepare`、`ci.local.quick`、`pr.push`、`local.dev.sync_demo`、`local.dev.snapshot`、
模块 upgrade、fixture reset、发布快照。台账保持 **42**，约六组投影候选继续挂账、不登记。

### 8.16.5 剩余缺口（更新后）

1. **验收缺口：已无。** 发票正向闭环（拒绝反例 + 授权续用正向路径）与 789 判定，在最终工具版本下均成立。
2. **交付前置（待用户确认后执行）**：`ci.delivery.freeze.prepare` → 干净 HEAD 冻结 + 完整 tracked+untracked 指纹 → 一次 `ci.local.quick` → 独立复核 → `make pr.push`。
3. **机制固有代价（观察项，不在本批实施）**：每次设计器闭环会留下一个未发布 `ready` 复核草稿，按目标阻断下一次同目标运行
   （本轮 `276` 到期 `2026-09-17 22:47:25 UTC`；材料 `267` 到期 `14:51:17 UTC`）。建议后续批次评估复核草稿的显式生命周期。
4. **popup 加载耗时**：已定位为「同一面加载耗时可变 + 运行自造的 abort 风暴」；本轮消除自造部分（模块 `failed_requests` 20 → 1），
   剩余为环境传输波动；就绪门在复现时给出 `api_pending` 与断言失败快照。

交接面：`artifacts/uc4-invoice-lowcode/browser/review-handoff-276.json`（draft token 已与库回读校验）；
`review-handoff-274.json` 已标注被 274 授权运行消费（`superseded_by`）。

## 8.17 代表面证据复位：付款/客户/合同/结算按最终应用源重跑（只读）

### 8.17.1 发现的陈旧证据（不是新缺陷）

按「输入变了才失效」核对文件 mtime：`frontend/apps/web/src/api/businessConfig.ts`（14:12:15 CST）、
`frontend/apps/web/src/pages/contractForm/ContractFormProductHeader.vue`（14:23:46）、
`frontend/apps/web/src/pages/contractForm/ContractFormPage.css`（14:23:52）三处应用源**晚于**付款/客户/合同/结算的首次代表面运行（13:58–14:02），
因此那四个主题的页面观察对最终应用源而言已陈旧，需按依赖补跑（发票 14:29、材料 14:30 两次晚于上述改动，仍有效）。

### 8.17.2 重跑（只读，仅补受影响部分）

入口：`FORM_LOWCODE_TOPIC=<topic> FORM_LOWCODE_REPRESENTATIVE=1 make local.dev.form_lowcode.browser`（四个主题各一次，`representative-<topic>-r8.log`）。

| 主题 | 结果 | 非空洞观察（摘要） |
|---|---|---|
| payment | exit 0 | action 809 / `payment.request` / view 2096：26 字段、6 章节；`payment_request_attachment_text_display` 正文不渲染但声明在正文外、`attachment_ids` 渲染 ×1（附件原件与文本摘要同一事实单一呈现）、`payee_account_source_display` 渲染 ×1；`collapsed_sections=["履约与追溯"]`（无未解析项） |
| customer | exit 0 | action 820 / `res.partner` / view 1590：38 字段、8 章节；关系集合 `category_id`/`child_ids`/`bank_ids`/`sc_attachment_ids` 全部 `rendered@body`，`relations_skipped=[]` |
| contract | exit 0 | action 609 / `construction.contract.income` / view 1569：24 字段、5 章节；`line_ids:one2many:rendered@body`；`readonly_checked=["operation_strategy"]`；含既有记录路由 |
| settlement | exit 0 | action 781 / `sc.settlement.order` / view 1764：27 字段、5 章节；`line_ids`/`attachment_ids` `rendered@body`；条件关系 `payment_request_ids`/`payment_request_line_ids` 记为 `conditional:not id`（不在正文误判为缺失） |

四个主题的 `findings` 全空（`duplicated`/`empty_containers`/`decorated_layout_groups`/`titled_layout_groups`），
即本批关心的结构消费口径（重复呈现、空容器、无标题包装组、包装组装饰）在最终应用源上无回归。

### 8.17.3 只读性与有效性证据

- 未新建配置草稿：只读回读（`now=14:53:31 UTC`）显示 `id>267` 的最新行为 `276`（来自 §8.16 闭环），四个代表面运行期间**没有新增任何草稿行**；
- 每次运行自身打印 `[local.dev.form_lowcode.browser] business fingerprints unchanged`（业务配置指纹未变）；
- 发票（14:29）与材料（14:30）的代表面证据保持有效：`find frontend/apps/web/src -newermt '2026-09-17 14:30:41'` 为空，应用源此后未再改动（本轮改动仅在 `scripts/`、`make/`、`docs/`）。

### 8.17.4 代表面覆盖（更新后，全部绑定最终应用源）

| 主题 | 代表面入口 | 状态 |
|---|---|---|
| 发票 | 设计器闭环（§8.16，含 popup/发布/回滚/越界面/视觉顺序）+ 只读代表面（14:29） | passed |
| 付款 | 只读代表面（§8.17.2） | passed |
| 客户 | 只读代表面（§8.17.2） | passed |
| 合同／结算 | 只读代表面（§8.17.2） | passed |
| 材料 | 设计器闭环（§8.13.4，`review_draft_id=267`）+ 只读代表面（14:30） | passed |
| 低代码（设计器编辑目标、预览与发布一致） | 发票设计器闭环（编辑目标保留、预览=发布效果、回滚恢复基线） | passed |

未执行（保持未执行）：`ci.delivery.freeze.prepare`、`ci.local.quick`、`pr.push`、`local.dev.sync_demo`、`local.dev.snapshot`、
模块 upgrade、fixture reset、发布快照。台账保持 **42**；约六组投影候选继续挂账、不登记。

## 8.18 第 7 次接管：冻结收口（生成证据准备、可审查提交、完整指纹、一次 Quick、独立复核、外部归档）

身份：分支 `feature/uc4-invoice-native-lowcode`、HEAD `025e37d2`、工作树 **46 条（37 modified + 9 untracked）**，冻结前未提交。
状态口径：**批次有限验收通过（用户只读浏览器复核）｜待冻结门禁｜未集成｜未部署｜89 入口交付未完成**；台账保持 **42**。
本轮授权范围：停止扩展功能、整理可审查提交、生成证据准备与预检、冻结干净 HEAD 和完整指纹、对最终 HEAD 跑一次 Quick、独立复核、外部归档、准备 PR 正文。
**不推送、不清理工作树、不清理复核草稿（233／267／276 保持原样）。**

### 8.18.1 归属与唯一写入者（第 7 轮）

| 类别 | 内容 |
|---|---|
| 接管前已有（接管首次 `git status` 即在树内，逐项复核后原样保留） | §4.0 标注「接管前已有／接管前段」的全部路径；本会话未覆盖、未重做 |
| 接管后修改（本会话历次写入） | §8.7 草稿归属守卫、§8.13.2 共享吸顶偏移＋动作承载门＋代表面 runner、§8.15.4 popup 就绪门、§8.16.2 消除自造 abort；**第 7 轮唯一写入 = 本文档新增 §8.18** |
| 仅验证（无写入） | `make ci.delivery.freeze.prepare`、`make ci.local.iteration`、`make verify.business_config.unit`、`make local.dev.form_lowcode.browser`（r8 系列）、指定只读回读 |

唯一写入者：本会话执行体。**4 个登记工作树 ≠ 4 个活跃工作树**：4 个历史保留工作树本轮未触碰，不作为预算违规判定，也不清理。

### 8.18.2 生成证据准备（`make ci.delivery.freeze.prepare`，23:03，exit 0）

`freeze-prepare.log` 逐项：

- `refresh.generated_reports` 写出并复验：test_inventory（1373 条）／test_inventory_summary／e2e_journey_matrix／module_dependency_map／complexity_budget_report／split_plan_queue／github_remote_execution_plan／contract_structure_fingerprint；
- `refresh.frontend.component_driver_takeover.inventory` → `component-driver-takeover-inventory-v1.json`；`refresh.contract_form_split_evidence` → `p4_p0_03_contract_form_split_evidence.md`（`lines=1929`）；
- 预检复验：`[component_driver_takeover_inventory] PASS required=35 missing=0 bridge_only=0 raw=0`、`[contract_form_split_evidence] PASS lines=1929`、`[ci.generated_evidence.preflight] PASS all content-bound generated evidence is current`、`[ci.delivery.freeze.prepare] PASS candidate=unfrozen next=review_generated_changes_commit_freeze_then_run_quick_once`。

刷新带来的 tracked 生成物差异（随冻结提交一起进入）：

| 生成物 | 驱动 |
|---|---|
| `docs/engineering_convergence/{test_inventory.csv,test_inventory_summary.md,complexity_budget_report.md,split_plan_queue.md}` | `refresh.generated_reports` |
| `docs/engineering_convergence/p4_p0_03_contract_form_split_evidence.md` | `refresh.contract_form_split_evidence` |
| `docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json` | `refresh.frontend.component_driver_takeover.inventory` |
| `docs/frontend_productization/rendering-detail/{visual-projection,component-professionalization,official-design-alignment,rendering-surface-ownership,form-structure-contract-projection-matrix}-*.json` | 更早一轮 `refresh.frontend.rendering_detail.inventory`（含 `source_kind` 真实分类行与 `BoundFormSettingsPanel` 真实声明） |

`contracts/generated/contract_structure_fingerprint.json` 重写后与 HEAD 逐字节一致（`git status` 无差异），即生成是幂等的。
无刷新残留：刷新后再次执行预检仍全部 `current`。生成物按既有生成入口产出，**未手改任何摘要**。

### 8.18.3 可审查提交边界（P0 机制 / P1 声明 / P4 验证工具）

| 提交 | 归属 | 路径 |
|---|---|---|
| 1 | **P0 机制** | `addons/smart_core/core/view_orchestrator.py`、`addons/smart_core/handlers/business_config_change_set.py`、`addons/smart_core/model/ui_business_config_change_set.py`、`addons/smart_core/tests/test_business_config_change_set.py`、`frontend/apps/web/src/**`（共享渲染层 8 文件：`api/businessConfig.ts`、`components/template/NativeFormTreeRenderer.vue`、`pages/ContractFormPage.vue`、`pages/contractForm/{ContractFormActionBlocks.vue,ContractFormPage.css,ContractFormProductHeader.vue,nativeLayoutUtils.ts,useRecordFormLayout.ts,formActionPlaceholderGate.ts}`） |
| 2 | **P1 声明** | `addons/smart_construction_core/models/core/formal_config_contract_fields.py`、`addons/smart_construction_core/tests/{__init__.py,test_form_structure_consumption.py,test_invoice_native_lowcode.py}` |
| 3 | **P4 验证工具与生成物** | `frontend/apps/web/scripts/**`（8）、`scripts/verify/**`（4）、`scripts/audit/generate_frontend_rendering_detail_inventory.py`、`make/{frontend.mk,runtime_ops.mk}`、`docs/frontend_productization/rendering-detail/**`（6）、`docs/engineering_convergence/**`（5）、本批次记录 |

拆分理由：三支 rendering-detail 生成物的差异由两类驱动合成（产品文件 digest 变化 + `generate_frontend_rendering_detail_inventory.py` 补 `BoundFormSettingsPanel` 真实声明），
在同一文件内不可再拆，故与对应生成/校验脚本同属第 3 个提交；`P0`／`P1` 的代码归属仍在各自提交内保持可独立审查与独立回滚。

### 8.18.4 冻结后产出位置（不改写 tracked 文件，不制造新 HEAD）

- 完整 tracked+untracked 指纹：既有入口 `scripts/contract/complete_worktree_fingerprint.py`（`codex_complete_worktree_fingerprint/v1`，含 tracked/staged/untracked 全部路径与 worktree sha256、scope manifest 哈希、digest），落 `artifacts/fingerprints/`；
- Quick receipt：`.git/codex/evidence/ci.local.quick/<HEAD>.json`（`local_quick_evidence.py` 自校验 exact 40 位 SHA 且 `git status` 全空才签发）；
- 独立复核报告与外部归档 receipt：非跟踪证据位置（`artifacts/`）与工作树外既有归档目录 `.codex-evidence/workspace-archives`。

按「冻结后不得再刷新 tracked 文件」，上述 receipt／归档结果不回写本文档；本记录 tracked 内容在冻结提交时定稿，receipt 与归档结论进 PR 正文与非跟踪证据。

### 8.18.5 未执行项（保持未执行）

`local.dev.sync_demo`、`local.dev.snapshot`、模块 upgrade、fixture reset、发布快照、`make pr.push`、工作树清理、复核草稿清理。
本节取代此前各节「未执行」清单中关于 `ci.delivery.freeze.prepare` 的条目（已于 23:03 执行并通过）；其余条目维持原状。
台账保持 **42**；约六组投影候选继续挂账、不登记。

## 8.19 G03 代表面实施：收款与公司收入原生结构迁移（独立记录）

本批 U-C4 的第二个代表面（`G03 收款与公司收入`）在**独立分支与独立记录**中实施，避免把已冻结的本批候选改写：
分支 `feature/uc4-receipt-income-native-v1`（基于 `origin/main`=`1dbf63f5dd8513b71aede67c875e51b7a95e8626`），记录 `docs/ops/iterations/uc4_receipt_income_native_lowcode_20260917.md`。

要点（细节见该记录）：3 个入口（637/806/807）共用原生 1644；3 个入口声明转 `native_semantic_surface`，共享层 sections(149)、P1 业务事实层(8) 与模型级生成镜像(109) 退役；原生 arch 承载退役配置声明过的事实并加 8 个 `data-sc-anchor` 业务章节；**不登记** `sc.receipt.income` 的展示副本（该模型未继承展示副本协议、附件摘要为双来源派生），改由退役重复投影保证正文单一呈现。
验证：L1 PASS；L2 新增 6 测 `0 failed`；L3 模块升级 + authority PASS；L4 只读代表面 806 create/record 通过（章节导航全 resolve、吸顶 0 重叠、无重复字段/空容器），637/807 为交付导航权威**拒绝访问**（记录为可达性事实，非结构结论）。
台账保持 **38**（扣减留待合入后核对）；本批未执行 `sync_demo`／fixture reset／发布快照／工作树清理。

## 8.20 G03 主线集成与台账 38 → 36

上一节记的「台账保持 38、扣减留待合入后核对」已闭合：G03 冻结候选
`558626214f57f03e3bc3eb25e1acd9caa40b0d63`（tree `175da4c07dad0524bd13aaa4466202518953ba56`，完整指纹 digest
`9b1bae26356f0a6acc4b9f2e6aa5ad02827717bf61de02a5321891f6912808cb`，exact-head `ci.local.quick` PASS）
经 PR #488 合入，main = `654edf0ff09fe394080bfa2545a5061dcafdbecd`；四个候选门禁在该 head 全部 success，
`make pr.merge.prep` 与 `make pr.merge`（squash + `--match-head-commit`）依次通过。

台账 `docs/ops/iterations/form_structure_compatibility_consumers_v1.json` 扣减 **38 → 36**
（退役 action 637/806 与视图 1644，并新增 `uc4G03PublishedAudit`）；共享旁路 action 807
（工程进度款收入登记）按其「非台账消费者」事实登记在 `bypassConsumers`，不计数、不静默丢弃；
`nextBatch.selectedGroup` 前进到 **G04 实付与公司支出（837/808，视图 1647）**，`sourceMainlineHead` 更新为上述 main。

证据归档：`make workspace.evidence.archive` 5 文件（summary／identity／review／2 张代表面截图）回执 `verified`，
位于 `/home/lidefend/workspace/.codex-evidence/workspace-archives/20260918/uc4-g03-receipt-income-native/558626214f57f03e3bc3eb25e1acd9caa40b0d63/`；
独立复核结论 APPROVE（残留风险与非阻断跟进项见该归档 `review.md`）。

状态：**批次验收完成（本批范围）｜主线集成完成（PR #488）｜未部署**。G03 残留缺口（637/807 受管身份授权、
807 progress 域样本、契约字段→渲染节点逐字段归因、`name` 手工编号业务决定）继续登记在 G03 记录 §6，本批不扩。

## 8.21 G04 代表面实施：实付与公司支出原生结构迁移（独立记录）

本批 U-C4 的第三个代表面（`G04 实付与公司支出`）仍在**独立分支与独立记录**中实施，不改写已冻结的候选：
分支 `feature/uc4-payment-execution-native-v1`（基于 `origin/main`=`1cf2a151cb6ac19fe45d2050b875f9b39163ad05`），
记录 `docs/ops/iterations/uc4_payment_execution_native_lowcode_20260918.md`。

要点（细节见该记录）：三个入口（837 实付登记 / 808 公司财务支出 / 811 往来单位付款）共用原生 1647；
入口声明转 `native_semantic_surface`（208 保留 `semantic_anchors`，241/242/243 只留标题与组合模式），
共享层 sections(144)、P1 业务事实层(6) 退役；原生 arch 加 9 个 `data-sc-anchor` 业务章节、`state` 由 statusbar
单次呈现、补回独立审计事实（`created_time` 属退役 P1 层(6) 已声明的原生未承载事实；`creator_name` 为该层
声明投影 `payment_execution_source_created_by_display` 的 canonical 事实、由本批新增补入），3 个无标题包装组按布局语义保留；
**不登记** `sc.payment.execution` 的展示副本（未继承展示副本协议），退役的 10 个 `*_display` 投影不重复入正文、
其列表列职责与字段存储全部保留。

本轮新增一条**归因结论**（不登记为缺陷）：808/811 的业务分类（`sc.business.category`）20/16 声明
`form_policy_json.visible_profiles=["readonly"]`，浏览器 create 档位确实不呈现这 5 个 `company_contractor_*` 事实，
随之为空的 `公司-承包人资金责任` 章节也不再出现，导航与正文一致、无孤儿入口与空容器——判定为**声明的合法隐藏**，
非结构消费层的修剪误删。契约层只读重放为**形状一致**（三入口各 67 容器节点 / 46 字段节点、字段集合相同、无重复、
`fieldSemanticRoles` 相同），**并非逐字节相同**（按节点键比较自身属性的口径：837↔808 有 48 个节点在字段级属性/组 `widgetList`
上不同、808↔811 有 2 个；按位置并向上传播子节点差异则为 52/4/52，可复算证据在
`artifacts/uc4-representative/g04-contract-tree-diff/`）；
通过 `op=model` 重放**未复现** create 档位的契约层 `visible=false`，该可见性在入口/应用配置装配路径生效，
本批只登记声明层证据与浏览器实测，细节见 G04 记录 §3/§5。

验证：L1 PASS（16 tests）；L2 新增 7 测 `0 failed`（首轮两处失败均为测试自身，已修并复跑）；L3 模块升级 + authority PASS；
L4 只读代表面 837 create/record、808 create 通过（章节入口全 resolve、吸顶 0 重叠、无重复字段/空容器、业务指纹未变），
811 为交付导航权威**拒绝访问**（记录为可达性事实，非结构结论）。
台账保持 **36**（扣减留待合入后核对）；本批未执行 `sync_demo`／fixture reset／发布快照／工作树清理。

## 8.22 G04 主线集成与台账 36 → 34

上一节记的「台账保持 36、扣减留待合入后核对」已闭合：G04 冻结候选
`04701c175bcca245eb797f66148e3cf13bbf2a37`（tree `f0665b8686b53e2b08eb488282a214898938ee8c`，完整指纹 digest
`c50877d0c7e1e3b26aafcfefdbd5568b348735a834cd13b5899fa1cf9cfd1bad`，7507 路径，exact-head `ci.local.quick` PASS）
经 PR #490 合入，main = `87b36441c8940af24ed10cffe300363fc5e3272e`；四个候选门禁在该 head 全部 success，
`make pr.merge.prep` 与 `make pr.merge`（squash + `--match-head-commit`）依次通过。

台账 `docs/ops/iterations/form_structure_compatibility_consumers_v1.json` 扣减 **36 → 34**
（退役 action 837/808 与视图 1647，并新增 `uc4G04PublishedAudit`）；共享旁路 action 811
（往来单位付款）按其「非台账消费者」事实登记在 `bypassConsumers`，不计数、不静默丢弃；
`nextBatch.selectedGroup` 前进到 **G05 报销/扣款/备用金（792/798/793，视图 1632/1633）**，`sourceMainlineHead` 更新为上述 main。

证据归档：`make workspace.evidence.archive` 8 文件（summary／pr-body／identity／worktree-fingerprint／review／3 张代表面截图）
回执 `verified`，位于
`/home/lidefend/workspace/.codex-evidence/workspace-archives/20260918/uc4-g04-payment-execution-native/04701c175bcca245eb797f66148e3cf13bbf2a37/`；
独立复核共 5 轮（轮次 1/2 REQUEST_CHANGES 仅涉记录陈述与冻结身份卫生，轮次 3/4/5 APPROVE），结论与残留风险见该归档 `review.md`。

状态：**批次验收完成（本批范围）｜主线集成完成（PR #490）｜未部署**。G04 残留缺口（811 受管身份授权、
808/811 业务分类可见性策略、837 record 章节入口差异、契约字段→渲染节点逐字段归因、`company_contractor_*` 契约层复现）
继续登记在 G04 记录 §6，本批不扩。

## 8.23 G05 代表面实施：报销、扣款、备用金原生结构迁移（独立记录）

记录：`docs/ops/iterations/uc4_expense_claim_native_lowcode_20260918.md`。分支
`feature/uc4-expense-claim-native-v1`，基线 = `8e8c1ce9d4d0fbe63b141cf75475030282f9f9d9`（G04 合入后主线），
dirty 范围 **11 个路径**（P0/P1/P4 + 记录 + 生成物，与 `git show --stat` 一致），唯一写入者＝本会话执行体。
本批冻结候选的精确身份（commit／tree／完整 tracked+untracked 指纹／exact-head Quick 回执）按既有做法
绑定在外部证据包与批次记录的身份节，合入时在 §8.24「G05 主线集成与台账 34 → 32」收口，避免在同一提交里
写入自身 HEAD 造成身份漂移。

本批要解决的结构消费问题：`sc.expense.claim` 的三个正式入口共享两个原生表单（1633／1632），
其中 792／798 已按入口声明消费原生树，而 **793（备用金）没有入口级发布**，解析落到模型级
`sc_expense_claim_form_structure_generated_v1`(72)：`layoutPolicy=native_authority` ＋ 独立 slots，
前端因此走 compatibility 平面，create 模式把「可见且只读且无值」的字段全部修剪，页面只剩壳
（`.native-form-tree[data-state="empty"]`、0 字段、0 导航），而操作行与协作区仍正常渲染。

归因方法（可复算）：同一会话内对比三入口的 `api.data` 响应——`containerTree`（792=86／798=79／793=79 节点）
与 `formStructureContract…formStructureAuthority`（792/798=`native_authority`／793=空），
再对上前端 `contractFormPresenter.ts` 的 `structureAuthority` 判定，得到「结构数据完整、消费平面错误」的结论；
没有用延长超时或改断言代替归因。

修复：为 793 新增入口级发布 `expense_claim_advance_fund_productized_form_v1`（`备用金`、
`native_semantic_surface`，无 sections/fields/columns），与同模型 792／798 一致；模型级 72 保留原样
（另有消费者），共享 compatibility 修剪规则本批不改。

验证：L1 `ci.local.iteration` PASS（16 tests）；L2 后端 `TestExpenseClaimNativeLowcode` **9 tests / 0 failed**
（含修正后断言：793 必须解析到入口级容器树权威，模型级配置保留且不再被该入口消费），前端
`verify.frontend.native_section_navigation.unit` PASS、`verify.frontend.typecheck.strict` PASS；
L3 `local.dev.upgrade` PASS（78 modules）；L4 代表面 792/798/793 create 全部通过
（36／29／35 字段，8 章节，导航 8/8，吸顶分离，`findings` 全空）。

代表面工具补齐（P4，最小扩展，复用既有受管环境）：scope 探测新增 `sample_state`／`business_row_count`，
代表面 journey 新增 `representative_uncovered`，loop 打印 `UNCOVERED`/`BLOCKED`。由此把此前**静默跳过**的
`record_surface` 事实显式登记：792=`record_rule_denied`（域内 1 行、可读 0 行）、798/793=`empty_action_domain`。
结论：本主题「业务指纹不变」护栏在当前受管身份下基于 0 行可读业务数据，强度有限，不得表述为「业务数据已证未被改动」。

批外候选（未登记为缺陷、未修改）：`sc.expense.claim` 的 ir.rule 组交并被合并为 `&`，导致非扣款组用户
读域归零（即 792 记录规则事实的成因）。约六组副本候选继续留台账，不扩成全系统迁移。

独立复核（只读，候选 `ba3f5da7`）结论 APPROVE，无写路径／授权绕过／业务事实丢失／scope creep（`addons/smart_core/**` 零改动、
台账零改动）。复核提出的可移植性缺陷已闭环：测试改用 xmlid 寻址视图，不再硬编码库内 id 1633／1632
（副本库与 clean/tenant 库 id 不同会让该测试失败）。代表面 L4 的 792=36／798=29／793=35 字段差已补归因：
三入口结构层一致（同视图 57 个 field 节点、节点级 modifier 逐项相同），差在**入口业务类别的字段策略层**
（798 声明 `finance.deduction.bill`，其 `form_policy_json` 带来 `fieldGroups` 与 category-sourced REQUIRED 规则；
规则条数是 10 比 7、**差 3 而非 4**——`project_id` 在 798 由类别规则承担、在 793 由通用标记规则承担，属同一字段换来源），
并使 13 个 widget 转 `visible=false`／`auth=none`；793 无业务类别，回落通用策略），DOM 上只体现为
`company_contractor_*`×5 ＋ `reject_reason` 这 6 个字段（批次记录 §7.1）。一处包装 `<group>` 缩进错位按
纯 cosmetic 记录、本批不改。

### 8.23.1 第三轮回环：`readonly` 放宽回归（已修）与 `state` 候选缺口（未改）

第二轮提交 `b2b12365` 的独立只读复核结论 **REQUEST_CHANGES**，其中一条是**真实回归**：792 的
`company_name_text`／`paid_amount`／`payment_state` 从「退役配置声明只读」变为契约层 `auth=edit`。
首次偏差在**原生 arch 的声明不完整**——217 去结构后原生 arch 是唯一载体，而 1633 上两个付款事实只是
**条件**只读（`state in ['done','legacy_confirmed','cancel']`）、`company_name_text` 无条件，create 档
（`state='draft'`）下三字段全部落到可编辑；对照 1632 同族字段是 `readonly="1"`（该声明由本批 recovery `ba3f5da7`
补字段时新增——基线 `8e8c1ce9` 的 1632 完全没有这三项声明，即本批只对齐了 1632、漏了对齐 1633）。

修复层：**P1 行业标准默认**（`smart_construction_core` 原生视图），3 行改动；
测试同批把断言从「编译后的 arch 字符串」升级为「渲染器实际消费的策略层」
（每个声明只读事实在 `statusContract.widgetStatus` 中的 `readonly` 必须为真）。
验证：L1 PASS（16 tests）、L2 后端 9 tests / 0 failed、L3 PASS（78 modules）、只读探针 792 `LOSS=[]`、
L4 代表面重跑 PASS（36／29／35 字段、8 章节、导航 8/8、吸顶在 1088 与 390 两个视口均分离 13px、
`findings` 全空、`restored=true`）。本轮**观察到 1 次 Vite dev 模块传输中断**
（`ERR_NETWORK_CHANGED`×4，`recovery_attempt=renavigate_once`、`recovered=true`）：按既有口径单独记录，
不改写成零错误，也不作为「网络已恢复」的判据。

同轮登记但**未修改**的候选缺口：793 以及另外 6 个无入口声明的入口（794／815／839／840／841／842），
其 `state` 在契约层为 `auth=edit`——792／798 的 `state` 只读来自**业务类别** `form_policy_json`，
而全部 14 份入口契约与 25 份类别策略一致声明 `state` 只读，故 793 是 17 个入口中唯一可编辑者。
不修改的三条依据：① 非本批回归（基线 793 无入口契约；内存内剔除 528 的对照实验得到同一 `state` 行）；
② 唯一可用载体是**模型默认表单视图** 1632，收紧会波及 6 个批外入口，违反「门控不得移除合法动作入口」；
③ 入口级最小修复被机制禁止（`is_configured_surface` 只接受 tenant_lowcode／user_preference，
`source=…product_release` 加 `node_patches` 会命中 `CONFIG_SOURCE_NOT_AUTHORIZED`）。
详见批次记录 §11.4 与 §13。

状态：**批次验收完成（本批范围）｜主线集成完成（PR #492）｜未部署｜89 入口交付未完成｜台账 31**。

## 8.24 G05 主线集成与台账 34 → 31

§8.23.1 记的「台账 34（扣减待合入后核对）」已闭合：G05 冻结候选
`ae677283435f9ae3f0e5c2a504c4c3f92ff036c5`（tree `ed24b8408355055871d0994bc063bd4e65b32ccf`，完整指纹 digest
`0f8199b1d9faabbc23e51956a27f0689ab27dc2c51a0f55590a48f6d577334e1`，7509 路径，exact-head `ci.local.quick` PASS）
经 **PR #492** 合入，main = `4cda500408ce9feda724700699272ab5e7d2a708`；该 head 上 `frontend_release_gate`、
`merge_policy_gate`、`public_guard`、`professional_quality_gate` 四个候选门禁全部 success（并 `release_candidate_gate`、
`python310_runtime_compatibility`、`professional_authorization`），`make pr.merge.prep` 与
`make pr.merge`（squash ＋ `--match-head-commit`）依次通过；`pr.merge.local_quick_gate` 以同一 head 的 exact-head 回执复用，
未重跑矩阵。

台账 `docs/ops/iterations/form_structure_compatibility_consumers_v1.json` 扣减 **34 → 31**（本批在台账内**正好 3 条**：
index 18 = action 792／menu 578／view 1633、index 20 = 798／563／1632、index 22 = 793／575／1632；退役 action 792／798／793
与视图 1632／1633，`count`／`localVerifiedCount`／`mainlineRemainingCount` 同步，并新增 `uc4G05PublishedAudit`）。
退役的是**条目**而非视图：只读 `browse()` 探针（`sc_dev_demo`，2026-09-18）显示 1633 仍是 **13 个 action**
（791/792/795/796/797/799/800/801/816/817/818/819/846）的共享原生表单、1628 为其树视图，1632 同时是 798 的显式表单
与模型级默认表单，其余 action 既不在台账内、也不因本轮扣减受影响。同一探针确认没有第二个 action 通过 `view_ids`
指向 1632／1633、也没有第二个活跃菜单指向 792/798/793；唯一共享入口是**归档**菜单 543「费用与保证金」
（`active=false`，parent 财务中心）→ action 792，与已计数的 menu 578 共用同一 action 且自身无发布配置，按 G03/G04 先例
登记进 `uc4G05PublishedAudit.bypassConsumers`（`counted=false`），不计数、不静默丢弃。
`nextBatch.selectedGroup` 前进到 **G06 税额与专项抵扣（790/879，视图 1654）**，`sourceMainlineHead` 更新为上述 main。

证据归档：`make workspace.evidence.archive` 8 文件（summary／pr-body／identity／worktree-fingerprint／review／3 张代表面截图）
回执 `verified`，位于
`/home/lidefend/workspace/.codex-evidence/workspace-archives/20260918/uc4-g05-expense-claim-native/ae677283435f9ae3f0e5c2a504c4c3f92ff036c5/`；
本批独立复核共 4 轮，按候选记为：`ba3f5da7` APPROVE（§8.23 记录的复核）、`b2b12365` REQUEST_CHANGES（`readonly` 放宽回归，
真实 major，已在 §8.23.1 修复）、`78f7cd17` APPROVE（4 项记录措辞问题，批次记录 §11.5）、`ae677283` APPROVE
（2 项记录措辞问题，见下）。

本轮（扣减提交）闭合了两处记录口径，均不涉产品运行路径：① 本节 G05 状态行由「第三轮回环中（回归已修，待重走冻结链）」
更新为「批次验收完成｜主线集成完成（PR #492）｜未部署」；② 批次记录 §11.4 的 6 个入口补口径
「无入口声明**且未固定表单视图**（走默认视图）」。另修正阅读中发现的同源旧口径：本节 §8.23.1
「对照 1632 同族字段本就是 `readonly="1"`」与批次记录 §11.1 的更正不一致，已改为「该声明由本批 `ba3f5da7`
补字段时新增，基线 `8e8c1ce9` 的 1632 无这三项声明——本批只对齐了 1632、漏了对齐 1633」。

状态：**批次验收完成（本批范围）｜主线集成完成（PR #492）｜未部署｜89 入口用户验收未完成｜台账 31**。
G05 残留缺口（793 及 6 个无声明入口的 `state` 可写、`sc.expense.claim` 的 ir.rule 组交并被合并为 `&`、
业务指纹护栏基于 0 行可读业务数据、compatibility 平面 create 档可把 primary zone 修剪空且无 fail-closed、
`expense_claim_views.xml` 包装 `<group>` 缩进错位、G04 遗留 808／811 的 `company_contractor_*`）
继续登记在批次记录 §11.4／§13 与 `uc4G05PublishedAudit.residualGaps`，本批不扩。

## 8.25 G06 代表面实施：税额与专项抵扣原生结构迁移（独立记录）

按 `nextBatch.selectedGroup` 推进到 **G06 税额与专项抵扣**（`action 790` 抵扣登记／menu 538、`action 879` 项目专项抵扣／menu 701，
同模型 `sc.tax.deduction.registration`、同原生 primary form `view 1654`）。分支
`feature/uc4-tax-deduction-native-v1`，基于 `origin/main`=`daf9a97875a15343671c00e46fd9c4e639ebeca2`；
唯一写入者为本会话执行体，其它工作树未触碰。完整记录见
`docs/ops/iterations/uc4_tax_deduction_native_lowcode_20260918.md`。

**实际改动 6 个代码／工具路径 + 3 个记录路径（共 9 个路径）**：原生 arch 加 8 个 `data-sc-anchor` 业务章节（其中 2 个归属条件页 `责任余额`／`迁移来源`）、
按退役配置反推的缺失字段全部补回（含 `迁移来源` 页的 6 个来源追溯事实）、把两个退役入口声明过的只读限制写回 arch
（`state`／`source_origin`／`currency_id` 收紧，`business_category_id` 改为按 `deduction_scope` 条件只读，
使共享表单同时满足 879 只读与 790 可编辑），并**删除原生 arch 自身的重复呈现**：`withholding_amount`
原本在同一表单的 `抵扣金额与税额` 与 `扣款办理` 两个章节各出现一次，本批收敛为一次（登记于批次记录 §10）；
206（790）与 177（879）的 `contract_json` 退役为 `native_semantic_surface`（只保留标题；879 保留其
`deduction_scope_authority` 等语义上下文键）；新增 7 测并注册；在既有受管 runner 内登记只读代表 topic
`tax_deduction`（复用同一环境与身份校验，未新建 fixture 或环境）。

模型级配置 143／5／129 与旁路入口 852（扣款单：无自有菜单、只固定 tree、无自有发布）**未改动**，只读核对为
`LEGACY_STRUCTURE_SUPPRESSED_BY_NATIVE_VIEW` + `compatibilityDependencies=["legacy_configuration_structure_suppression"]`，
即模型级结构在原生权威入口上被抑制、在旁路入口上仍生效。

**分层验证**：L1 `make ci.local.iteration` PASS（16 tests，6 路径）；
L2 `TestTaxDeductionNativeLowcode` **`0 failed, 0 error(s) of 7 tests`**（复核 nit 闭合后重跑）；
相邻 `TestProjectSpecialTaxDeduction` **`0 failed, 0 error(s) of 2 tests`**（实跑取回执，不再沿用旧回执）；
L3 `local.dev.upgrade` PASS（78 modules loaded ＋ `local.dev.ready` ＋ `local.dev.demo.authority` PASS）；
L4 只读代表面 `FORM_LOWCODE_TOPIC=tax_deduction FORM_LOWCODE_REPRESENTATIVE=1` **PASS**
（790 create 30 字段／790 record 26 字段／879 create 30 字段，各 7 章节且导航 7/7 resolved+visible，
findings 全空，吸顶操作行 `175–205` 与导航 `218–257` 分离 13px；`restored=true`、`browser_errors=[]`、
`recovery_state.released=true`、草稿未创建未被清理）。

两处已归因、不重跑：① `TestUserFeedbackBusinessViews` 在 `sc_dev_demo` 的 28/72 失败在基线态（`git checkout`
回 `daf9a978` 后重新 upgrade）复现出**完全相同**的失败集合，判定预先存在、与本批无关；
② 790 只读路由导航不含「扣款办理」，经只读探针确认该分组两字段在受管样本上取值为空（`deduction_unit_name=False`、
`deduction_reason=False`），属 P1「字段合法隐藏」而非修剪误删。

**未覆盖（如实登记，不伪装成覆盖）**：879 的 `record_surface` 在受管身份下 `domain_rows=0`、
`business_row_count=1`，`state=empty_action_domain`，故该入口的只读记录态重放无从进行。

**登记未改**：`smart_core/app_config_engine/services/view_Parser/base.py:102` 以 `not xml_content` 判断入参，
而该函数同时接受 lxml Element（其他两个调用点都以 Element 传入）；当前不可观测（真实 form arch 必有子节点），
仅对无子节点元素会静默返回 `{}` 并抛 `FutureWarning`，属潜在健壮性缺口，需 P0 单独决定，本批不扩。
同理登记未改：`scripts/verify/view_orchestration_product_boundary_guard.py` 的 `ALLOWED_COMPOSITION_MODES`
不含 `native_semantic_surface`、且只在 form 带 `fields` 时才校验模式，缺一条「`native_semantic_surface`
必须无 `sections/fields/columns`」的正向校验；该守卫实跑 `FAIL`，5 条错误全部指向本批未改的契约
（`tender_bid`／`payment_request`／`policy_document`），守卫与其输入均不在本批 9 个路径内 → 预先存在、非本批引入，
且该守卫未纳入 `ci.local.quick.run`／`pr.push`，不影响本候选 Quick。是否补校验属 P0/P4 单独决定。

**独立复核（只读、绑定冻结候选身份 `5b104106`）**：结论 **APPROVE**，无 blocker／major。复核者独立复现了
候选 `5b104106`（tree `5fb43ba0…`）的 `HEAD`／`HEAD^{tree}`／branch／clean 工作树、完整指纹 digest
（`f54cf06e…`，7511 路径）与 exact-head Quick 回执身份（该 digest 绑定**已被取代**的候选 `5b104106` 的
干净工作树，故在当前冻结候选上**不可复现** —— 指纹按定义绑定某一具体树状态，属预期而非缺陷）；
并逐条核对：两入口退役为 `native_semantic_surface` 且 879 的 5 个保留键位于 `context`（非第二份结构）、
模型级 143/5/129 与旁路 852 未被改动且仍可用、`state`／`source_origin`／`currency_id`／`withholding_amount`
在 1654 arch 中各出现**恰好 1 次**且去重保留在 `抵扣金额与税额`、条件只读经运行时实测
「790 可编辑／879 只读」、测试无硬编码库内 id 且为行为断言、`addons/smart_core/**` 与台账（保持 31）均未被改、
grep 无 ACL／groups／ir.rule／domain 改动。提出的 3 项 minor 与 5 项 nit 已在本提交闭合：
① 记录路径数字口径（6→「6 代码/工具 + 3 记录 = 9」）；② 相邻用例改为实跑取回执（`0 failed of 2 tests`）；
③ 登记上述共享守卫的既有失败。另把「790 可编辑事实」的断言由**表达式形状**升级为**解析后策略行为**
（`readonly=false` / `auth=edit`），并登记只读呈现层 `NATIVE_MODIFIER_UNRESOLVED` 的保守呈现事实。

该复核修正落在 `4402b4aa91192852010f246a66cc339b68e85c91`（tree `781f81f18b88f50037f3cec03ff437d9256f36e5`，
仅 1 个 P4 新增测试文件 + 2 份记录，**不改产品运行路径**）。G06 的冻结身份在这之后的最后一次记录提交上重走一次
冻结链（完整指纹 ＋ exact-head Quick ＋ 复核绑定同一指纹）；冻结候选身份的取值只写入外部归档
（`identity.json`／`worktree-fingerprint.json`／`review.json`），不写入记录文件（写入会改变候选自身
commit hash）——理由与逐阶段身份表见 `uc4_tax_deduction_native_lowcode_20260918.md` §11。

**冻结候选复核（本批最后一轮，只读）**：在候选 `08cf7151`（tree `9f57d4c5…`，干净工作树）上独立复核，
结论 **APPROVE**（0 blocker／0 major／4 minor／3 nit，**全部为记录口径**）。复核者独立复现了身份三件套
（`HEAD`／`HEAD^{tree}`／branch／空 `git status --porcelain`、重算指纹 digest `f9f529fb…` 与 7511 路径、
Quick 回执 sha256 `203ae4f4…`），并独立核对：delta 恰为声明的 9 路径、`smart_core` 与台账未改、
退役声明过的 39（790）／28（879）个事实在 arch 中全部落地、只读限制全部还原、`withholding_amount` 仅 1 次、
写／恢复边界成立（受保护 change set 163/190/192/194/233/267/274/276 未被触碰）。其 7 项记录口径问题已在
随后一次 docs-only 提交闭合（逐条见 G06 记录 §11.1），产品与测试行为未变。

台账保持 **31**：本批在台账内**正好 2 条**（index 21 = 790／538／1654、index 22 = 879／701／1654），
退役与 **31 → 29** 扣减按 G03/G04/G05 先例留待合入后由独立提交落地，本实现提交不改台账文件。
未推送、未建 PR、未合并、未部署。

状态：**批次验收完成（本批范围，冻结链见本批记录 §11）｜未集成｜未部署｜89 入口用户验收未完成｜台账 31**。

## 8.26 定时 CI 失败处置（2026-09-18，用户指令「定时 ci 有失败先处理了」）

### 8.26.1 触发身份与边界

接管身份：分支 `feature/uc4-tax-deduction-native-v1`，HEAD `fad9a110642f37ff1c86feb7ca72b5dc82466dfb`
（= `origin/main` `daf9a978` ＋ 4 个 G06 提交，**0 behind**，可 fast-forward）。生产交付树仍是唯一写入者。
`fad9a110` 的 G06 冻结候选身份与其外部归档**未被改写**（本轮新提交叠加在其后，不移动该 commit）。
本轮不改产品业务规则、不扩展 42 台账、不重跑全代表面矩阵、不跑 Quick（未到冻结门禁）。

### 8.26.2 六个定时 workflow 的实际结果

定时批次跑在 **`main` 的 `8e8c1ce9`**（2026-09-17 21:30Z ≈ 09-18 05:30 CST），非本分支 HEAD。
判据：同一 commit 上 `push` 事件通过而 `schedule` 事件失败 → 事件相关缺陷，不是代码回归。

| workflow | run id | 结果 | 归因 |
|---|---|---|---|
| `public_guard` | 35277725670 | failure | 步骤「Scan governed product history」（`make verify.repository.clean_history`）；`security.online_capture.unit` 6 例失败。**后续步骤被 fail-fast 跳过**（含「Run clean product boundary scan」） |
| `professional_quality_gate` | 35277758044 | failure | 同一根因同一入口（`make/ci.mk:1002 security.online_capture.unit`，同一 6 例 `TrustedScopeTests`）；三个 shard 中仅 `shard-verify` 执行，`shard-reports`／`shard-tests` 未执行 |
| `frontend_release_gate` | 35277183148 | failure | `pnpm test:release` → `make verify.frontend.release.audit`；**唯一失败守卫** `[frontend_style_system_guard] FAIL`（`make/frontend.mk:519`，其余 30+ 守卫全 PASS） |
| `backend_test_suite` | 35281779057 | failure | 步骤「Run backend test suite per module」：`test_p1_payment_request_capability.py` 的 `KeyError: 'sections'` |
| `release_candidate_gate` | 35277590281 | failure | **纯级联**：`wait_for_candidate_checks` 汇总上游失败，无独立代码原因 |
| `merge_policy_gate` | — | success | — |

### 8.26.3 三处真实缺陷与修复层

| # | 缺陷（首次偏差） | 责任层 | 修复 |
|---|---|---|---|
| 1 | 单测继承宿主 `GITHUB_EVENT_NAME=schedule`，使 `trusted_scan_scope.resolve_scope()` 直接返回 `scheduled_full_audit`，绕过 trusted-base 分支 → 6 例断言失败（如 `'scheduled_full_audit' != 'untrusted_origin'`）。**产品语义正确，缺陷在测试未隔离环境** | P4 验证工具 | `scripts/ci/test_trusted_scan_scope.py` 的 `setUp` 内 `mock.patch.dict(os.environ)` ＋ `addCleanup` 复原 ＋ `pop('GITHUB_EVENT_NAME')`。**不改 `trusted_scan_scope.py`、不删断言** |
| 2 | `frontend/apps/web/src/pages/ContractFormPage.vue` 真实突破文件行数预算（1929 > 1900；`#487` `1dbf63f5` 引入，limit 自 `d3bdb3aa` 未变） | P0 前端（通用渲染层） | 按既有做法**提取**而非放宽 budget：48 行纯展示格式化块 → 新增 `frontend/apps/web/src/pages/contractForm/contractFormMetaLine.ts`；页面 1929 → **1887** |
| 3 | 已退役契约断言未随 `87b36441`（G04）同步：`business_config_contract_payment_execution_from_request_productized_form_v1` 已改为 `native_semantic_surface` 并删除 `sections`／`fields`，测试仍读 `execution_payload["sections"]` | P1 声明（施工标准） | 断言改指**原生载体**：新增类常量 `EXECUTION_FORM_BODY_FIELDS`（32 字段）＋ 从 `view_sc_payment_execution_form` arch 逐字段断言 ＋ 4 个 anchor `readonly == "1"`；并断言 `composition_mode == "native_semantic_surface"` 且 `sections`／`fields` 不在 payload。**不删断言** |

原有读核对（DB 无关，静态解析 `views/core/payment_execution_views.xml`）：32 个退役字段**全部**存在于该 view arch；
`payment_request_id`／`project_id`／`partner_id`／`contract_id` 的 `readonly="1"` 均在。故修复方向为改指原生载体而非删除断言。

### 8.26.4 由本轮改动派生、必须同步刷新的生成物（全部走既有生成入口，未手改）

| 生成物 | 变化 | 入口 |
|---|---|---|
| `docs/engineering_convergence/complexity_budget_report.md` | 扫描 4384 → 4385；`ContractFormPage.vue` 1929 → 1887；`test_p1_payment_request_capability.py` 3009 → 3030 | `python3 scripts/ci/generate_complexity_budget_report.py --write` |
| `docs/engineering_convergence/split_plan_queue.md` | 同上两行行数 | `python3 scripts/ci/generate_split_plan_queue.py --write` |
| `docs/engineering_convergence/p4_p0_03_contract_form_split_evidence.md` | 行数锁 **1929 → 1887**（ratchet 收紧，方向为改进） | `make refresh.contract_form_split_evidence` |
| `docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json` | 仅 `inputDigest`（新增源文件） | `make refresh.frontend.component_driver_takeover.inventory` |

前两项此前**未被任何一步发现**：`ci.generated_reports.guard` 在 `shard-reports` 内两次分别以
`complexity report is stale`、`split plan queue is stale` 失败——即本轮修的 CI 若直接复用 `8e8c1ce9`
的跳过状态，定时作业会在 `shard-reports` 处**再次失败**。同层还有 `verify.contract_form_split_evidence` 的
行数锁（1929 → 1887）。四项刷新后 `make ci.generated_evidence.preflight` PASS。

### 8.26.5 验证（层级／入口／身份／结果）

身份：HEAD `fad9a110` ＋ 未提交 dirty 范围（阶段身份，非冻结身份；**未冻结**）。

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | **PASS** `change_state=dirty` `coverage=L1_only` |
| L2（映射受影响面） | `verify.frontend.canonical_form_presenter.unit`／`page_pattern_reference_parity.unit`／`primitive_adapter.unit`／`product_page_pattern.unit` | 4/4 **PASS**（170 cases／13／31／5 tests，均非零） |
| L2（后端受影响面） | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='sc_gate/…,sc_smoke/…'` | **PASS** `0 failed, 0 error(s) of 460 tests`（修前为 1 error） |
| CI 等价（public_guard 失败步） | `GITHUB_EVENT_NAME=schedule make verify.repository.clean_history` | **PASS** `reason=scheduled_full_audit` |
| CI 等价（professional 失败入口） | `GITHUB_EVENT_NAME=schedule make security.online_capture.unit` | **PASS** 17 ＋ 10 tests OK |
| CI 等价（professional 三 shard） | `GITHUB_EVENT_NAME=schedule make ci.professional.backend.shard-verify／shard-reports／shard-tests` | 3/3 **PASS**（shard-reports 修复前 2 次 stale） |
| CI 等价（frontend 权威静态面） | `VITE_ODOO_DB=sc_frontend_acceptance … python3 scripts/verify/frontend_static_release_audit.py` | **PASS** 9/9 checks（`style_system`／`lint`／`strict_typecheck`／`production_build` …），build fingerprint `c718e6a3be75…` |
| 生成证据 | `make ci.generated_evidence.preflight` | **PASS** |
| 守卫单元 | `make verify.frontend.component_driver_takeover.unit` | **PASS** `required=35 missing=0` |

### 8.26.6 未执行项与边界（保持未执行）

- `verify.frontend.release.audit` 的**浏览器段**（`page_identity.browser`／`delivery_hardening.release.browser`）
  **未执行**：需拉起 acceptance 环境（`backend.acceptance.up`／`frontend.acceptance.up`／`db.frontend.acceptance.ensure`），
  与「不停启历史容器、不派生新环境」边界冲突。且 `8e8c1ce9` 上该段从未被执行（被 style guard 挡住），
  非本次定时失败根因。
- `scripts/verify/clean_product_release_scan.py` 在**本机**报 `FAIL checks=14`，唯一失败项
  `clean_product_tree_guard` 的 `TRACKED_RUNTIME_ENV_FILES=4`。**判定：本机环境限制，不是产品缺陷。**
  证据：该 4 个文件为 `.env.demo`／`.env.dev`／`.env.local.clean`／`.env.local.sample`，被 `.gitignore:53:.env*`
  忽略且 `git ls-files` 中**不存在**；该守卫遍历工作树而非 `git ls-files`，故 CI 全新检出时计数为 0。
  以 `git archive HEAD` 导出**仅 tracked** 的干净树重跑同一守卫 → **PASS files=7512**（本机 8319）。
  该步在 `8e8c1ce9` 上处于 fail-fast 之后（状态 skipped），从未真正执行。
- `clean_product_release_scan.py` 内 `source_head` 为**硬编码常量** `009f26e6…`（pre-existing，非本轮引入），
  报告头颅与当前 HEAD 不一致。仅登记观察，本轮不改（避免扩大范围）。
- 未推送、未建 PR、未合并、未部署；未 `sync_demo`／fixture reset／发布快照／模块 upgrade；
  未触碰受保护草稿 163／190／192／194／233／267／274／276。

### 8.26.7 状态

台账保持 **31**（定时 CI 处置不改业务域登记；扣减仍按 G03/G04/G05 先例留待合入后由独立提交落地）。
定时失败 5 个 workflow 已全部归因（3 真实缺陷 ＋ 1 级联 ＋ 1 本机限制），根因均已修复并在**同一 CI 入口**上复验通过。

## 8.27 G06 整改回环 R1：代表面「可填事实」判据的共享机制结论（2026-09-18）

身份：HEAD `7b792729` ＋ 未提交 dirty 范围（**阶段身份，未冻结**）。明细见
`docs/ops/iterations/uc4_tax_deduction_native_lowcode_20260918.md` §12。

### 8.27.1 共享机制结论（P0 呈现口径 × P4 验证工具）

代表面判据 `assertRequiredFactsAreFillable` 的原意是「交付策略要求必填且可编辑的事实，必须给出用户能填的控件」。
它此前只统计**非 `readonly` 的原生输入**（`EDITABLE_CONTROL`），因此在共享表单上出现了一个假阳性：

- 可编辑的**日期事实**由 `ProfessionalBaseFieldControl` → `ScDateField` → TDesign 日期选择器渲染，
  其触发器内层 `input` 依设计带 `readonly`（点击才**打开面板并写回值**），故被计成 0；
- 实测（790 创建面 `invoice_date`）：节点存在、`data-field-state="required"`、`data-auth="edit"`、标签可见，
  点击触发器出现日期面板，点选后输入框值变为 `2026-08-31`，`field--empty` 消失 → **可填，判定为口径缺陷**；
- 同页 `document_date`／`deduction_confirm_date` 同形，佐证是口径而非单字段渲染偶发。

机制结论（对全部代表面主题成立）：

1. 交付面的可填形态有**两种**——原生可编辑控件，以及**宿主未禁用且 input 未禁用**的 picker 触发器；
   前者用严格选择器，后者必须以「触发器宿主未禁用」为门，才不把 disabled／readonly 呈现算成可填。
2. 判据不能只放在选择器字面量里：观测须**分别**保留 `editable`／`picker`／`fillable`，让「为什么算可填」可归因。
3. 放宽方向必须配反向硬化：只读事实要求 `editable === 0 && picker === 0`（比原来更严），
   且仅靠 picker 计数的必填事实还要断言触发器**可见且能取得焦点**，避免口径变成隐藏/惰性控件的普遍豁免。

### 8.27.2 修改范围与影响面

- 只改 **1 个 P4 验证工具路径**：`frontend/apps/web/scripts/formal_form_representative_journey.mjs`。
  `addons/**`、`frontend/apps/web/src/**` **未改**，故产品运行路径与其余主题的既有证据不受影响。
- 受影响面 = 消费该工具的只读代表面：本轮补跑 `tax_deduction`（本主题）以及注册了 `readonly_values`
  的 `contract`／`settlement`（验证收紧后的只读守卫无回归）。**未重跑全矩阵。**
- 同类选择器另见 `formal_form_invoice_journey.mjs`（只读事实要求 0、`note` 要求 >0，不产生日期必填假阳性）、
  `local_dev_project_profile_write_browser.mjs`（交互填充）、`frontend_scene_component_driver_readonly_browser.mjs`
  （只读驱动要求 0，严格口径正确）——三者**本轮未改**，若后续新增「必填日期」断言须复用新口径。

### 8.27.3 结果与剩余缺口

| 项 | 结果 |
|---|---|
| L1 `make ci.local.iteration` | **PASS**（16 tests OK，`change_state=dirty coverage=L1_only`） |
| L4 `tax_deduction` | **PASS** exit 0；`restored=true`、`browser_errors=[]`、`cleanup_guard=proceed`、`released=true` |
| L4 `contract`／`settlement` | **PASS** exit 0（只读面回归） |
| 代表面明细 | 790 create／record **PASS**；879 create **PASS**；879 list 空态 **PASS**；879 record **未覆盖**（`empty_action_domain`） |
| L2（前端映射面） | `canonical_form_presenter`／`page_pattern_reference_parity`／`primitive_adapter`／`product_page_pattern` 4/4 **PASS**（170／15／46＋31 tests／12＋5，均非零） |
| L2（共享结构机制） | `verify.frontend.native_form_structure_responsibility.unit` **PASS** `cases=10` |
| L2（后端结构消费） | `TestFormStructureConsumption` **PASS**（§8.27 时 `6 tests`；**§8.28 已扩到 8 tests，以 §8.28 为准**） |
| 390 人工复核 | 操作行／导航／正文互不遮挡；点末项再点回首项后目标落在吸顶带下方；`scrollWidth - innerWidth = 0`；`单据附件` 与 `协作附件` 各自成组。**口径纠正见 §8.28**：本节早期的 `nav 347–400` 与 `nav.bottom 347` 分属静止态与吸顶态，须按阶段分读 |
| 本批已登记候选 | ①日期触发器测量口径（跨主题，本轮只在代表面闭合）；②空值只读 `many2many` 被 `readonlyFactIsPresentable` 省略但 `FormSection.vue` 有 `field--readonly-empty-relation` 渲染支撑（两层判断不一致，**只登记不改**）；③`partner_name` 独立历史事实在创建面以空只读形态呈现（呈现取舍，**只登记不改**）；④action context 的 `default_business_category_code` **未被水合**成 `business_category_id`（**§8.28 已在 P1 声明层收口**）；⑤只读计算字段 `deduction_flow_label` 保存前渲染「-」（**§8.28 已明确生成条件**） |

未执行：未冻结、未跑 Quick、未推送、未部署、未启动 G07；台账保持 **31**；
受保护草稿 163／190／192／194／233／267／274／276 未被触碰；历史工作树未被清理。

---

## 8.28 G06 整改回环 R2：入口分类与默认值在 P1 声明层收口（2026-09-18）

### 8.28.1 共享机制结论

「入口声明了业务分类、创建面却不呈现」**不是共享默认值水合层的缺陷**，而是**该入口缺了 P1 声明**：
同类入口（结算单收／支、付款申请、费用报销）都在自己的 `default_get` 里把 action context 的
`default_business_category_code` 解析成关系 id，抵扣登记入口漏了这一步，而**保存侧 `create()` 一直正确**。
因此本轮修在 P1 声明层，**不改 P0 共享解析／水合机制**，也不写抵扣模型特判、不向其他入口铺开。
凡「声明—呈现—保存」三者对同一事实的判断不一致，先比对同类入口的声明，再决定层；
共享层只有在多个同类入口同时错时才成立。

### 8.28.2 修改范围与影响面

- **接管后修改**（本轮唯一写入）：`models/core/tax_deduction_registration.py`（`default_get` 补解析）、
  `tests/test_tax_deduction_native_lowcode.py`（＋5 例）、`tests/test_form_structure_consumption.py`（＋2 例）。
- 共享机制用例集新增：`BUSINESS_CATEGORY_ENTRIES`——**同类入口**（结算单收入／支出、抵扣登记用户／项目专项，
  共 4 个 action／2 个模型）必须把声明同样送到创建面；**无默认分类反例**——声明了但数据不存在的 code
  **不得被替代**（`test_an_entry_category_that_cannot_be_resolved_is_not_substituted`）。
- `addons/smart_core/**` 与前端 `src/**` 本轮**未改**，故其余主题证据不受影响，未重跑全矩阵。
- 环境根因（非代码）：受管容器启动早于模块改动且无 `--dev=reload`，执行的是旧模块代码；
  `make local.dev.restart` 后恢复，**未执行** `local.dev.upgrade`。

### 8.28.3 行为验证（不只检查字符串）

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | **PASS** `change_state=dirty coverage=L1_only` |
| L2 本主题 | `TEST_TAGS="uc4_native_lowcode"` | **PASS** `0 failed, 0 error(s) of 45 tests` |
| L2 共享机制 | `TEST_TAGS="/smart_construction_core:TestFormStructureConsumption"` | **PASS** `0 failed, 0 error(s) of 8 tests` |
| 只读探针 | `default_get`（790／879 context） | `business_category_id` → **50／51**（修复前为空） |

浏览器（只读）：790 创建面呈现 `业务分类 抵扣登记`、879 创建面呈现 `业务分类 项目专项抵扣`；
候选范围收窄为入口分类域（`count=1`，`codes=["tax.deduction.registration"]`，「搜索更多」仅 1 行）；
879 该字段按视图声明为只读单值；越界分类提交被 `ValidationError` 拒绝且**零持久化**（回滚后记录数 `1 → 1`）。

### 8.28.4 空值表达与导航口径（结论）

- **历史往来单位**：独立存储事实，**不按重复文本删除**；由入口 context `default_partner_name` 水合，
  非 legacy 的 manual 记录（id=1）同样带真实值 → **不能**套用进项发票的 `invisible="source_origin != 'legacy'"`。
  790／879 创建面为空只是这两个入口没有 context 往来单位，评估结论为**保留**。
- **空附件关系**：一层定可见性（`readonlyFactIsPresentable`，按呈现形态）、一层定已保留关系的渲染
  （`FormSection.vue::isReadonlyEmptyRelation`），二者职责不矛盾；`one2many` 与 `many2many` 的取舍差异仍是候选②，未扩大。
- **办理事项**：生成条件按优先级明确（`project_special` → 项目专项抵扣；`is_transfer_out` → 进项税额转出；
  `withholding_amount` → 扣款抵扣；有抵扣金额／税额 → 进项税额抵扣；否则 抵扣登记）；
  首次偏差是 `default_get` 不返回该非存储计算字段，前端**未拼造**；本轮不加静态默认值（会因后续录入金额而陈旧）。
- **章节导航坐标**：`nav 347–400`（静止态）与 `nav.bottom 347`（吸顶态）是**两个阶段**，
  已按阶段重列为同一稳定态的三个矩形（§12.5.1），790／879 在 1088 与 390 均无重叠、首尾双向可达。

### 8.28.5 未执行项与状态

未冻结、未跑 Quick、未推送、未建 PR、未部署、未启动 G07；未重跑全矩阵（合同／结算按输入未变复用）；
未 `sync_demo`／fixture reset／无关 upgrade；未停启历史容器、未改 Docker 网络、未清理历史工作树；
未触碰受保护草稿 163／190／192／194／233／267／274／276；879 记录态仍未覆盖。
**未持久化业务或配置写入**（日期点选属未保存表单交互）。

状态：**入口分类与默认值已收口（P1）｜整改中｜台账 31｜未集成｜未部署**。

## 8.29 第 10 轮（R5）：章节导航「按下稳定性」断言与办理事项的通用可见性消费

### 8.29.1 归属与唯一写入者（第 10 轮）

- 身份：HEAD `7b792729f67c17be8d8e5e483df8b027b65d752d`，分支 `feature/uc4-tax-deduction-native-v1`，dirty＝21 个已跟踪路径 ＋ 2 个未跟踪新增。
- **唯一写入者＝本会话执行体**。本轮**唯一写入**的路径是 `frontend/apps/web/scripts/formal_form_representative_journey.mjs`（P4 验证工具）。
- 本记录既有的共享实现（`pages/contractForm/FormSectionNavigation.vue`、`pages/contractForm/nativeSectionNavigation.ts`、
  `components/template/FormSection.vue`、`pages/ListPage.vue`、`views/ActionView.vue`、`components/professional-fields/ProfessionalBaseFieldControl.vue`、
  `scripts/native_section_navigation_test.ts`、`scripts/collection_view_semantics_test.ts`、`scripts/verify/local_dev_form_lowcode_scope.py`）
  **属「接管前已有」**，本轮未新增写入，**仅验证**。
- 历史保留工作树本轮未触碰（登记 ≠ 活跃）；未持久化业务或配置写入。

### 8.29.2 共享机制结论

1. **章节导航按下稳定性（同一共享控件的回归面）**：按下期间自动跟随**不得滑动轨道**，
   否则条目会离开手指、释放被投递给相邻条目或轨道本身。受管 runner 现以 **6 个稳定态场景 ＋ 1 个反例**覆盖，
   并在 390×844 的 879 create、790 create、790 record 上全部通过：

   | 场景 | 稳定态事实（879 create / 390×844） |
   |---|---|
   | 首项屏内按下 | `active=业务方向`、`target_top=359 ≥ nav.bottom=347`、`trackScrollLeft=0` |
   | 手动滚动正文后再按下 | 同首项：`业务方向`、359、`trackScrollLeft=0` |
   | 末项按下 | `active=协作记录`、`target_top=464`、`trackScrollLeft=329` |
   | 末→首（首项在横向可视区外，先横滚再点） | `active=业务方向`、359、`trackScrollLeft 329→0` |
   | 首→末（末项在屏外） | `active=协作记录`、464、`trackScrollLeft 0→329` |
   | 按住条目时正文继续滚动 | `active=协作记录`、464、按下期间 `trackScrollLeft` 不变 |
   | 反例：按住后释放点离开条目 | `delivered_active` 与按住期间一致（**什么都不激活**） |

2. **办理事项的通用可见性消费**：该辅助只读项只在**后端返回有效值**时呈现。
   实现是原生 `invisible="not deduction_flow_label"` ＋ 既有通用修饰符消费链，**未新增前端字段特判**；
   新建面（后端未返回值）不渲染该行，记录面（有值）渲染。反例对见 §12.9.2（本批次另册）。
3. **坐标口径**：`nav 347–400`（静止态）与 `nav.bottom 347`（吸顶态）分属两个阶段；
   本轮所有坐标改由受管 runner 的同一稳定态落盘给出（操作行／导航／目标三矩形同源），不再由探针估算拼接。
4. **反例保护（不降断言）**：新增的反例自带结论——正确记 `control`，异常记 `activation_survived_a_cancelled_press`／`control_not_armed`，
   既不进失败清单也不计入「已投递章节」，用于证明正例不是由「按下」本身产生，而是由「落在条目上的释放」产生。

### 8.29.3 本轮分层验证

- **L1（本轮重跑）**：`make ci.local.iteration` → **PASS** `change_state=dirty coverage=L1_only receipt=none`（`tmp/g06-remediation/l1-iteration-r10.log`）。日志 `changedPathCount=33` 为**相对基线参考快照**的集合，与 `git status --short` 的 23 条 dirty 口径不同。
- **L2（前端非零，本轮执行）**：`make verify.frontend.native_section_navigation.unit` → **PASS**（`authority=7 next_action=3 content_identity=11 active_tracking=11 structure_consumption=7`）；`make verify.frontend.product_page_pattern.unit` → **PASS**（`5 tests`）。
- **L2**：本轮未改后端／前端产品代码，按输入未变**复用**既有 L2（`TestFormStructureConsumption`、`native_section_navigation` 单元）与 §8.28 证据。
- **L4（受管代表面，仅受影响主题）**：invoice 与 tax_deduction 两主题各一次，均 **PASS**（exit 0），`business fingerprints unchanged`；导航按下稳定性在 879 create／790 create／790 record 全绿，879 record 仍为 `UNCOVERED / empty_action_domain`。详表见本批次另册 §12.9.4。

### 8.29.4 一次验证工具归因（P4，结论：产品无回归）

首次受管代表面 L4（invoice）exit 2，失败点在新增的「按住＋正文滚动」场景。
归因证明**首次偏差在探针**：该场景先 `page.mouse.move()` 再 `mouse.wheel()`，在按住状态下已是**拖拽**，
释放点离开条目 → click 不派发 → 激活被取消（高亮按设计跟随正文）。
两变体对照（`probe_nav_step6_attribution.mjs`）：按住不移指针时，轨道 `scroll_left` 不变、条目几何不变、
`pointerup/click` 均命中被按下条目并正确投递（目标 464 ≥ nav 347）；移动指针变体下**无任何相邻条目被误激活**。
修复只落在断言的手势与判据（含一次判据自身错误：对条目坐标而非释放点坐标做命中测试），产品代码未动。
完整记录见 §12.9.3。

### 8.29.5 未执行项与状态

未冻结、未跑 Quick、未推送、未建 PR、未部署、未启动 G07；未重跑全矩阵（合同／结算／材料／客户按输入未变复用）；
未 `sync_demo`／fixture reset／发布快照／无关 upgrade；未停启历史容器、未改 Docker 网络、未清理历史工作树；
未触碰受保护草稿 163／190／192／194／233／267／274／276；879 记录态仍未覆盖（`empty_action_domain`）。
台账保持 **31**；**未持久化业务或配置写入**。受保护草稿只读回读：8 条 change set 全部存在、`write_date` 均为 2026-09-17（早于本轮运行），233／267／276 仍为 `ready`（未发布、未回滚、未删除）。

状态：**窄屏导航与办理事项已收口并受管复验通过｜整改中｜台账 31｜未集成｜未部署**。

## 8.30 第 11 轮（R6）：三条导航路径分离复验（正常用户／键盘／自动显露）

本轮是复核反馈后的**有界诊断**：不改办理事项（口径已于 §8.29.2 收口），不重跑全矩阵，只做有界复现与归因。
本批次另册（`uc4_tax_deduction_native_lowcode_20260918.md` §12.10）记录同一证据，口径一致。

### 8.30.1 归属与唯一写入者（第 11 轮）

- 身份：HEAD `7b792729f67c17be8d8e5e483df8b027b65d752d`，分支 `feature/uc4-tax-deduction-native-v1`，dirty＝21 个已跟踪路径 ＋ 2 个未跟踪新增。
- **唯一写入者＝本会话执行体**。本轮**唯一写入**的路径是 `frontend/apps/web/scripts/formal_form_representative_journey.mjs`（P4 验证工具）。
- **接管前已有、本轮仅验证**：`pages/contractForm/FormSectionNavigation.vue`、`pages/contractForm/nativeSectionNavigation.ts`、
  `components/template/FormSection.vue`、`pages/ListPage.vue`、`views/ActionView.vue`、
  `components/professional-fields/ProfessionalBaseFieldControl.vue`、`scripts/native_section_navigation_test.ts`、
  `scripts/collection_view_semantics_test.ts`、`scripts/verify/local_dev_form_lowcode_scope.py`、以及 `addons/smart_core/*`、`addons/smart_construction_core/*` 的本批改动。
- **接管后修改（本轮）**：仅上述 runner 的导航断言面。**无产品代码写入**。
- 本轮探针输出（`tmp/g06-remediation/*.out`）为 gitignore 内的诊断材料，不进提交。
- 历史保留工作树本轮未触碰（登记 ≠ 活跃）；未持久化业务或配置写入。

### 8.30.2 共享机制结论：三条路径必须分开判定

复核指出（879／390×844）「点『办理说明与附件』→ 用按钮定位点击屏外『业务方向』」失败：高亮停在别处、
首标题 −1516.5px、导航底边 347px；而「先用左箭头显露再点击」通过；且第一组**没有按住／拖拽／滚轮**，
故不能用 §8.29.4 的「拖拽取消 click」归因关闭。

实测结论：**失败只出现在「坐标先于显露」这一类自动化时序上，不是章节导航缺陷**。

| 路径 | 操作 | 结果 | 关键事实 |
|---|---|---|---|
| **正常用户路径** | 点末项 → 用「向前浏览表单章节」显露 → 在显露后的位置真实按下 | **PASS** | §8.29 的 6 个稳定态场景全绿；`last_then_first` → `active=业务方向`、`target_top=359 ≥ nav.bottom=347`、`trackScrollLeft 329→0` |
| **键盘路径** | 聚焦已发布浏览控件 → `Tab`（1 次）→ 屏外首项获得焦点 → `Enter` | **PASS** | `focused_entry=业务方向`、`tabs_to_focus=1`、`delivered_active=业务方向`、`target_top=359`（790 record：387 ≥ 375） |
| **自动显露路径** | 自动化自身 `scrollIntoViewIfNeeded` 显露后，在**显露之后重新取点**按下 | **PASS** | 按下前条目 `visible_width ≤ 0`（隐藏点 `x=20`／invoice `x=26`，轨道左边界 `69`）；显露后 `left=69`；投递 `业务方向`、`target_top=359`。785／786／787／788 create 同样通过 |

三条路径的断言分别落在 `step=first_entry_in_view／pressed_after_body_scroll／last_then_first／first_then_last／
pressed_while_body_scrolled`、`keyboard_activation`、`auto_reveal_press`，**不再合并成一个「导航全绿」**。
runner 的失败过滤仍为 `!['pressed','not_applicable','control']`（未放宽断言）。

### 8.30.3 失败模式的定位证据（区分滚动竞争与投递）

| 实验 | 入口 | 观察 |
|---|---|---|
| 自动显露（正确时序）延迟矩阵 | `probe_nav_autoreveal_race_r6.mjs`：首点后有界延迟 0／60／120／250／500／900ms，再 `locator.click()` | **6/6 PASS**。每次 `pointerdown／pointerup／click` 的 target 与命中点均为 `业务方向`，之后正文滚到该章节（`ownerScrollTop 2125→57`），高亮 `业务方向`、首标题 359 |
| 正常用户与键盘路径对照 | `probe_nav_autoreveal_r6.mjs` | **PASS**：箭头显露后真实按下 = 业务方向／359；键盘聚焦首项后 Enter = 业务方向／359 |
| **坐标先于显露**（负向对照） | `probe_nav_stale_coords_r6.mjs`：隐藏时取点（`press_x=−229`）→ 显露 → 按**旧坐标**派发 | **FAIL（自动化侧）**：实际派发点 `(191,366)`，`pointerdown／up／click` 的 target 全部是 `办理说明与附件`（**另一个条目**），正文未移动（首标题 −1709），稳定高亮 `办理说明与附件`。显露后重新取点（`press_x=100`）则 **PASS** |

- 负向对照复现的正是复核报告的症状类别（**点击落在非目标条目、正文不动、首标题远在视口上方**），
  且事件证据显示产品把按下**正确投递给了指针下的那个条目**——「投递异常」发生在自动化的取点时序，而非产品事件错投。
- 6 号场景按下期间的 `track.scroll_left` 始终不变（341），**不存在按下期轨道自滑**的滚动竞争；
  正文跟随仍按设计更新高亮（`协作记录 → 办理信息`）。
- runner 现将该风险作为**可复核事实**落盘：`hidden_point`、`under_hidden_point`、`stale_point_after_reveal`；
  断言只在「显露后重新取点」的前提下判定投递，不以延长超时或改断言代替归因。

### 8.30.4 本轮分层验证（仅受影响层，复用其余）

- **L1**：本轮 runner 改动属 P4 验证工具；已按输入未变复用 §8.29.3 的 `make ci.local.iteration` PASS 结论，未重复跑。
- **L2**：本轮未改后端／前端产品代码，复用 §8.29.3 的 `make verify.frontend.native_section_navigation.unit`（PASS）
  与 `make verify.frontend.product_page_pattern.unit`（PASS）。
- **L4（受管代表面，仅受影响主题）**：

| 主题 | 结果 | 证据 |
|---|---|---|
| tax_deduction | **PASS** exit 0（`tmp/g06-remediation/l4-tax_deduction-r10.log`） | 790 create／790 record／879 create 的 `auto_reveal_press` 与 `keyboard_activation` 全为 `pressed`；879 record 仍 `UNCOVERED/empty_action_domain` |
| invoice | **PASS** exit 0（`tmp/g06-remediation/l4-invoice-r10.log`） | 785／786／787／788 create 的同上两场景全 `pressed`；789／639 `blocked/NAVIGATION_AUTHORITY_DENIED`（管理员无权限，非零错误通过） |

  两主题均 `business fingerprints unchanged`。**未重跑未受影响主题**：`section_navigation_press` 行仅存在于上述两主题的报告，
  其余主题报告不含该断言结果，故本轮 runner 改动对其无失效影响。

### 8.30.5 办理事项的当前呈现证据（未改动，仅补图）

`artifacts/lowcode-form-loop/browser/representative-tax_deduction-790-record.png`（本轮 L4 生成）：
已有记录 S70-TAX-001 的「业务方向」区**显示「办理事项 = 进项税额抵扣」**，与 `登记单号／业务分类／抵扣范围` 同列；
新建面同批字段清单仍**不含** `deduction_flow_label`（§8.29.2）。即「新建无值即隐藏／记录有值即显示」两侧证据齐备。

### 8.30.6 未执行项与状态

未冻结、未跑 Quick、未推送、未建 PR、未部署、未启动 G07；未重跑全矩阵（合同／结算／材料／客户按输入未变复用）；
未改办理事项；未 `sync_demo`／fixture reset／发布快照／无关 upgrade；未停启历史容器、未改 Docker 网络、未清理历史工作树；
受保护草稿 163／190／192／194／233／267／274／276 未触碰（全表 `max(id)=276`，本轮无新建草稿行）；
879 记录态仍未覆盖（`empty_action_domain`，不为补证据造数据）；**未持久化业务或配置写入**。台账保持 **31**；
约 6 组副本候选继续留台账，不扩大本批登记范围。

状态：**三条导航路径已分离复验（正常用户／键盘／自动显露均通过；失败仅复现于「坐标先于显露」的自动化时序）｜整改中｜台账 31｜未集成｜未部署**。
