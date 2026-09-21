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

## 8.31 第 12 轮（R12）：独立复核 REQUEST_CHANGES 的整改——退役声明的真实作用域（2026-09-18）

本轮**只做复核整改**：不扩展代表面、不改产品行为、不扩大登记范围。整改对象是「退役声明的范围口径」与「证据／记录一致性」。
本批次另册（`uc4_tax_deduction_native_lowcode_20260918.md` §12.11）记录同一证据，口径一致。

### 8.31.1 复核结论与本轮归属（第 12 轮）

- 独立复核（只读，绑定候选 `d14020bb`）结论：**REQUEST_CHANGES**，**无 blocker**；1 major ＋ 9 minor ＋ 4 nit。
- 四项重点判定**通过**：分类约束、只读／空值呈现、共享机制、测试未被削弱（无放宽断言换通过）。
- **Major（本轮闭合对象）**：被退役的 `sc_tax_deduction_registration_p1_form_business_facts_v1` 是**模型级**契约
  （`action_id`／`view_id`／`role_key`／`company_id` 全为空，`applies()` 对 0 一律放行），因此它作用于**该模型的所有渲染面**；
  而声明只写了「790／879／852 三个入口」。复核指出第 4 个消费者真实存在：`sc.tax.filing.action_open_deductions()`
  （正式菜单「税务申报」→ 申报期抵扣来源）。
- **唯一写入者＝本会话执行体**；本轮写入范围见 §8.31.4。

### 8.31.2 共享机制结论：模型级声明必须按「模型全部渲染面」声明并取证

| 事实 | 结论 | 依据 |
|---|---|---|
| 派生面是否真在该契约作用域内 | **是**。该面由代码内构造的 action dict 打开（无 `id`、`view_mode=tree,form`、`context={'create': False}`），无 action／view 作用域，模型级契约不因收窄条件被拒绝 | 契约记录四字段为空 ＋ `_effective_view_orchestration_contracts.applies()` |
| 退役是否**改变**派生面的 authority | **不改变**。退役体自身声明 `composition_mode=entry_semantic_surface`，派生面解析出的 authority 正是它；790／879 的 `native_authority` 来自**它们各自的 action 级声明**，与退役体无关 | 实测该面 `formStructureAuthority=entry_semantic_surface` |
| 退役在该面实际移除了什么 | 只移除该体并入的 **4 个章节标题 ＋ 其字段 `readonly` 注解**；authority 与事实集合不受影响 | 实测 `sectionTitles` 不含「单据识别／业务对象／金额与办理／附件与来源」；`businessConfigContracts` 不含退役体、含模型级 `..._form_sections_v1` |
| 是否丢事实 | **未丢**。该面未渲染的 5 个退役体事实全部是 `compute+store+readonly` 投影，各自保留场景（扣款单列表／业务层声明的 display-copy 源） | 新增用例内 `_assert_declared_facts_survive` 对派生面通过 |

**剩余观察（不登记为缺陷、不扩本批）**：派生面与 852 仍消费模型级 `entry_semantic_surface` 兜底，`sectionTitles` 为 `..._form_sections_v1` 的 9 个旧标题、`presentationMode=task`。
这是**本批之前既有**的呈现（退役后该面标题由 13 个降为 9 个，方向为收敛，不新增回归），本批只**声明**其范围、不整改 852／派生面的任务模式；
本批未对其做浏览器复核，故按候选问题留台账观察，不作缺陷登记、不批量改字段。

### 8.31.3 本轮分层验证（仅受影响层）

| 层 | 入口 | 结果 | 证据 |
|---|---|---|---|
| L2 后端（受影响） | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestFormStructureConsumption,/smart_construction_core:TestTaxDeductionNativeLowcode'` | **PASS** `0 failed, 0 error(s) of 25 tests`（含本轮新增派生面用例） | `tmp/freeze-r12/l2-sc-core-structure-consumption.log` |
| L2 后端（定向诊断，两次） | `... TEST_TAGS='/smart_construction_core:TestTaxDeductionNativeLowcode'` | 第 1 次 FAIL（断言期望错误，见下）／第 2 次 FAIL（菜单读取口径）／第 3 次 **PASS** `of 17 tests` | `tmp/freeze-r12/l2-tax_deduction-r12{,b,c,d}.log` |
| 前端 L2／L4／契约 | 输入未变的面按 §8.30 复验结论**复用**，未重跑 | — | 见 §8.30.4／§12.10.4 |

失败归因（本轮无无变化重试）：

1. 第 1 次 FAIL：`formStructureAuthority` 期望写成 `native_authority`——**期望错误，不是产品缺陷**。派生面无入口级 native 声明，解析结果本应为模型级 `entry_semantic_surface`；
   据此**按事实改写断言**并补「退役体自身声明同一 mode、故退役不可能改变任何模型级面的 authority」的断言，未放宽任何既有断言。
2. 第 2 次 FAIL：`ir.ui.menu.action` 的读取口径写成 `str(...)=="model,id"`，实际返回 recordset。改为按 `.action.res_model`／`.action.id` 断言（同一事实，换读取方式）。

### 8.31.4 本轮修改范围（P1 声明 ＋ P4 验证工具）

| 路径 | 归属 | 改动 |
|---|---|---|
| `addons/smart_construction_core/data/p1_daily_business_form_orchestration_contract_data.xml` | **P1 业务声明** | 退役记录的注释改为真实作用域：该模型**所有渲染面**（790／879／852／派生面）；并写明 790／879＝`native_authority`、852 与派生面＝模型级 `entry_semantic_surface` |
| `addons/smart_construction_core/tests/test_tax_deduction_native_lowcode.py` | **P4 验证工具** | 新增 `test_a_derived_surface_without_an_action_scope_keeps_the_declared_facts`：派生面溯源（无 `id`／`view_mode`／`context`）＋正式可达性（菜单→action→form 按钮）＋无作用域请求解析结果（`resolvedActionId=0`、`resolvedViewId=view 1654`、authority＝`entry_semantic_surface`）＋退役体不在 applied／模型级兜底在 applied／退役标题不再并入＋退役体事实一条不丢 |

**未改**：任何产品渲染代码、契约 payload（仅注释）、台账、代表面 runner；未重做迁移。

### 8.31.5 交付前口径与归属修正（复核 minor）

| # | 复核发现 | 处置 |
|---|---|---|
| 1 | 另册头部状态与末段状态冲突 | 已在另册头部标注取代关系（§12.11） |
| 2 | `ActionView.vue` 已被本批提交 `d14020bb` 修改，但归属表仍记「未改」 | §8.31.4 与另册 §12.11 明确该文件为**本批 P0 产品改动**（提交 `d14020bb`），§12.9.1／§8.30.1 中「本轮未改」的时间边界同时标注 |
| 4 | 证据摘要的 scope manifest 值写错 | 以完整指纹产物字段 `scope_manifest_sha256` 为准重生成（`/tmp/freeze-r12/**` 与外部归档件同步） |
| 7 | `ListPage.vue` 的 `showFallbackCreate` 在提交 `d14020bb` 后成为无消费者分支 | **保留并登记**：删除共享组件分支需要其自身的受影响面验证；本轮不扩产品改动，登记为 P0 卫生项待下批处理 |
| 9 | `views/support/user_confirmed_formal_list_alignment_views.xml` 的 852 列表域引用不存在的 `finance.tax.deduction` | **本批外观察项**：登记待办，不在本批整改（不扩面） |
| nit 3 | `models/core/tax_deduction_registration.py` 的 `init()` 以裸 SQL 回填 general，绕过 constrains | **本批外待办**：登记，不在本批整改 |

其余 minor／nit 由绑定**最终候选**的 R12 独立复核重新采集，逐条并入归档件 `review.json`；本批不在同一轮内混改产品行为。

### 8.31.6 未执行项与状态

未推送、未建 PR、未合并、未部署、未启动 G07；未重跑全矩阵；未改办理事项；
未 `sync_demo`／fixture reset／发布快照／无关 upgrade；未停启历史容器、未改 Docker 网络、未清理历史工作树；
受保护草稿 163／190／192／194／233／267／274／276 未触碰；**未持久化业务或配置写入**；
879 记录态仍未覆盖（`empty_action_domain`，不为补证据造数据）；台账保持 **31**。

状态：**批次验收完成（本批范围）｜主线集成完成（PR #494，main=`5938d6c620952e9c4c1af9fa6c33dbda14da0374`，squash 同树）｜未部署｜台账 29**。

## 8.32 G06 主线集成与台账 31 → 29（2026-09-18）

§8.31 记的「台账 31｜未集成」已闭合：G06 冻结候选 `dea896d229c17628d4f770f06da21dfbe28eff6d`
（tree `f709bccacff913fcd26aeac0b245337a4ae046d2`，完整指纹 digest
`44e8a72ca7f5d543bd88f921a36314aaa1bc0c9823cee5907584641c9a2a503c`，7514 路径，exact-head `ci.local.quick` PASS）
经 **PR #494** 合入，main = `5938d6c620952e9c4c1af9fa6c33dbda14da0374`（squash）。
该 head 上 `frontend_release_gate`／`merge_policy_gate`／`public_guard`／`professional_quality_gate` 四个候选门禁全部
success（并 `release_candidate_gate`、`python310_runtime_compatibility`、`professional_authorization`）；
`make pr.merge.prep` 与 `make pr.merge`（squash ＋ `--match-head-commit`）依次通过；
`pr.merge.local_quick_gate` 以同一 head 的 exact-head 回执**复用**，未重跑矩阵。squash 树
`f709bcca…` 与冻结候选 tree 逐字节一致（`origin/main^{tree}` 比对）。

台账 `docs/ops/iterations/form_structure_compatibility_consumers_v1.json` 扣减 **31 → 29**（本批在台账内**正好 2 条**：
index 21 = action 790／menu 538／view 1654、index 22 = 879／701／1654；退役 action 790／879 与视图 1654，
`count`／`localVerifiedCount`／`mainlineRemainingCount` 同步，并新增 `uc4G06PublishedAudit`）。

**「已退出兼容路径」按已合入源码核对，不重开调查**：契约 206（`tax_deduction_registration_productized_form_v1`）
与 177（`project_special_tax_deduction_form_v1`）的 `view_orchestration.views.form` 只剩 `title` ＋
`composition_mode=native_semantic_surface`，`sections`／`fields`／`columns`／`field_slots`／`layout` 等结构键全部消失，
故 `structural_form_declarations()` 无声明、`diagnose_structure_ownership()` 不可能再为这两条产出
`LEGACY_STRUCTURE_KEY_OVERRIDE`；`TestTaxDeductionNativeLowcode::test_entry_contracts_spend_one_native_structure`
同时断言两契约 native 且无结构体、790／879 为 `native_authority`／`configuredSections=[]`／
`layoutPolicy=container_tree_authority`（同一 tree 上 25 测 0 失败，输入未变故复用）。

**852 与派生面不额外计入退役消费者**：两者因 R12 的范围更正被纳入该模型级退役声明的作用面，
但都不是台账消费者——852（扣款单）无自有菜单、只固定 tree 视图、记录回落同一 primary form 1654；
派生面 `sc.tax.filing.action_open_deductions()`（税务申报 → 申报期抵扣来源）无 action／view 作用域，
按 `entry_semantic_surface` 消费模型级契约。二者登记在 `uc4G06PublishedAudit.bypassConsumers`
（`counted=false`），不计数、不静默丢弃；被扣减的是**条目**，primary form 1654 及其它消费者仍然存活。

`nextBatch.selectedGroup` 前进到 **G07 工资社保与发放（873／884／858／874，视图 1697／1700）**，
`priorityActions` 同步为 `[873,884,858,874]`，`sourceMainlineHead` 更新为上述 main。

证据归档：`make workspace.evidence.archive` 8 文件（identity／summary／pr-body／worktree-fingerprint／review／
3 张代表面截图）回执 `verified`，位于
`/home/lidefend/workspace/.codex-evidence/workspace-archives/20260918/uc4-g06-tax-deduction-native/dea896d229c17628d4f770f06da21dfbe28eff6d/`；
归档中的 `pr-body.md` 是提交前草稿，实际提交正文为其澄清版（补全 33 路径分层范围与 852 三项区分），差异见 PR #494 正文。
代表面 3 张截图生成于 `d14020bb`、按页面输入未变复用，**不是在最终 HEAD 重拍**。

## 8.33 G07 工资社保与发放整组原生结构迁移（2026-09-18）

### 8.33.1 归属与唯一写入者（本批）

工作树：`feature/uc4-g07-payroll-social-native-v1`，HEAD `d2997196`（`origin/main` =
`5938d6c620952e9c4c1af9fa6c33dbda14da0374` = PR #494 squash）。**交付脏范围 9 条路径**
（8 modified ＋ 1 untracked）；本轮另追加本记录文档 1 条，合计 10 条，故当前 dirty
相对 `5938d6c6` 为 12 条（含 HEAD 提交 `d2997196` 自带的 3 条文档）——这是**接管阶段的身份**
（提交 `bd3df6f7` 处实测 12 条）；本批**最终候选为 13 条**，第 13 条为
`docs/engineering_convergence/complexity_budget_report.md`（由 `96f0c9bd` 的生成证据刷新加入）。
一个候选工作树一个写入者：本 worktree 只交付一个 PFL
（**G07 工资社保与发放整组迁移**），不混入 G08 或六组副本候选。

| 归属 | 路径 | 层 |
|---|---|---|
| 接管前已有（本批前段、同一写入者） | `views/core/hr_payroll_document_views.xml`、`data/hr_payroll_form_productization_contract.xml`、`data/social_fund_contract.xml` | P0 结构／P1 声明 |
| 接管前已有（同一写入者） | `tests/test_hr_payroll_native_lowcode.py`（新增）、`tests/test_project_salary_product.py`、`tests/__init__.py` | L1/L2 |
| 接管前已有（同一写入者） | `scripts/verify/local_dev_form_lowcode_scope.py`、`frontend/apps/web/scripts/formal_form_lowcode_loop.mjs` | P4 验证工具 |
| **接管后修改（本次会话）** | `frontend/apps/web/scripts/formal_form_designer_journey.mjs` | P4 验证工具 |
| 仅验证、未改 | `docs/ops/iterations/form_structure_compatibility_consumers_v1.json` | 台账（本轮**不扣减**，合入后再独立核对） |

接管后对验证工具的 4 处修改（全部为 P4，未改任何产品文件、未放松任何断言）：
1. 新增 `payrollTopic` 身份（`requester_id`／`contact_phone`／`受管申请人`／`受管申请信息`），
   使设计器对该 topic 依据真实字段投放补丁，而不是沿用材料页的字段猜测；
2. 新增发布后**业务页**的 payroll 断言分支（原实现只有 material／invoice／document 三种，
   payroll 会落进材料分支去点 `说明与附件` 页签而超时）；
3. 把 `popupSignals`／`instrumentPopup`／`signalSnapshot` 提升到**预览 popup 创建之前**，
   并对预览 popup 增加一次性状态与信号取证（URL／DOM／截图／pageerror／意图生命周期）；
4. outside 入口（873）改用**本入口锚点字段的原生标签**判定隔离，替换材料页字面量。

### 8.33.2 三项已知口径的收口

**① 858 缺入口级发布 —— 已补，不是回落模型级平面。**
`action 858`（工资薪酬／menu 673）是活跃正式入口，此前没有入口级 release，因此消费模型级
`sc_hr_payroll_document_form_structure_generated_v1` 的稀疏平面，渲染的不是兄弟入口的业务任务面。
本批在 `hr_payroll_form_productization_contract.xml` 补入
`business_config_contract_hr_payroll_management_productized_form_v1`
（name `hr_payroll_management_productized_form_v1`，action 858，priority 800，title「工资薪酬」）。
升级后库内该契约 **id 662**／`act=858`／`prio=800`／`title=工资薪酬`；L2 断言 858 与 873
消费**同一原生树、同一字段集合**（`test_the_entry_that_had_no_release_renders_the_sibling_business_surface`）。

**② view 1697 由 8 个 action 共享 —— 一次原生承载、不按字段名批量去重。**
1697 被 858／873／884／663／660／661／662／664 八个 action 共享（663 另钉 tree 2067）。
本批把结构权威一次性交给原生 arch：按 `fact_type` 组织的业务分组（社保／工资／公积金／补助奖金）、
只有退役体声明过的 4 个 provenance 字段（`legacy_document_no`／`legacy_document_state`／
`legacy_source_table`／`legacy_source_id`，`readonly`）、同样只有退役体声明过的货币伴随字段
`currency_id`（`invisible`／`readonly`，该 Monetary 事实的货币伴随项）与稳定 `data-sc-anchor` 身份。
同名重复字段 **不是副本**：同一事实在各自的 `fact_type` 分组里各出现一次，且同一 `fact_type`
下只有一个分组可见；按用户口径**禁止按字段名批量去重**，L2 以
`test_repeated_fact_names_are_per_fact_type_contexts`（`REPEATED_FACTS`：`period_year`／
`period_month`／`people_count`＝3，`payer_unit`／`company_amount`／`individual_amount`／
`payout_unit`＝2）与 `test_the_fact_type_groups_are_mutually_exclusive` 固定该口径。

**③ 旧配置清单 4 条 vs 实际 8 条 —— 清单是命名不全，不是范围不同。**
台账 `nextBatch.groups[G07].legacyConfigurations` 只列了 4 个名字
（`project_payroll_productized_form_v1`／`project_salary_payment_productized_form_v1`／
`sc_hr_payroll_document_form_structure_generated_v1`／`social_fund_form_v1`），其
`evidenceStatus` 自述为 `grouped_from_existing_44_entry_ledger_not_runtime_revalidated`：它是早期
按 44 条清单分组时**按样本命名**的几条，不是完整枚举。按已改源码实际做法：**入口级 body 退役 8 条**
（873／874／884／663／660／661／662／664），**新增入口级发布 1 条**（858）；
模型级 `sc_hr_payroll_document_form_structure_generated_v1`（id 79）**不退役、不修改**——它是稀疏
字段序注解，与 G05 的 `sc_expense_claim_form_structure_generated_v1`（id 72）同类；
L2 `test_the_model_wide_annotation_keeps_serving_the_model` 固定 79 仍 `active`、`act=False`、27 字段、无 sections。
**本批不修改台账文件**（扣减留合入后独立提交核对）。

### 8.33.3 修改范围与影响面

| 层 | 文件 | 内容 |
|---|---|---|
| P1 声明 | `data/hr_payroll_form_productization_contract.xml` | 8 条退役入口契约只留 `title` ＋ `composition_mode: native_semantic_surface`；新增 858 入口级发布；顶部记录决策与回滚方式（`git revert`，无数据迁移） |
| P1 声明 | `data/social_fund_contract.xml` | 884（`social_fund_form_v1`）同样只留 `title` ＋ `native_semantic_surface`；`fact_authority`／`allowed_fact_types` **原样保留在 `view_orchestration.context`**，未连带退役 |
| P0 结构 | `views/core/hr_payroll_document_views.xml` | 两个 form 视图共 **11 个分组**补 `name` ＋ `data-sc-anchor`（实测 1697 的 11 个分组中 8 个带锚点、1700 的 4 个分组中 3 个带锚点。该计数**必须路径限定**：`git diff -U0 5938d6c6..HEAD -- addons/smart_construction_core/views/core/hr_payroll_document_views.xml \| grep -c '^+.*data-sc-anchor'` ＝ 11；**不限定路径时的读数会被测试、契约、脚本及本记录正文中的同名字符串一并命中，且随本记录自身内容变化而不可复现，故此处不引用该读数、不得用于分组计数**），另有 **4 个无标题包装组保持未动**（1697 3 个 ＋ 1700 1 个，初始基线 5938d6c6 为 1697 3 个 ＋ 1700 3 个）。1697：「历史来源」补 `invisible="not legacy_document_no"` ＋ 4 个 provenance 字段；notebook 前补隐藏只读 `currency_id`；**从 `payroll_provident_fund` 删去 `employee_user_id`／`employee_name`**（见 8.33.6）。1700：2 个原无标题包装组补名（`salary_payment_identity`／`salary_payment_amount`），新增第三组 `salary_payment_handling`（「经办与依据」）承载 `responsible_id` |
| L1/L2 | `tests/test_hr_payroll_native_lowcode.py`（最终候选 **15 测**，tag `uc4_native_lowcode`）、`tests/test_project_salary_product.py`、`tests/__init__.py` | 见 8.33.8 |
| P4 | `scripts/verify/local_dev_form_lowcode_scope.py`、`formal_form_lowcode_loop.mjs`、`formal_form_designer_journey.mjs` | payroll topic 只读代表路由（复用既有 runner／环境／身份，未另建 fixture 或环境）＋设计器闭环 |

**边界保持**：未触碰受保护草稿 163／190／192／194／233／267／274／276（见 8.33.9 的写入核对）；
未执行 `sync_demo`／fixture reset／发布快照／无关 upgrade／Docker 网络调整／历史工作树清理；
未执行任何真实工资发放或业务确认。

**在范围差异内的 G06 收口（非 G07 内容）**：本批相对 `origin/main` 的 13 路径中包含提交
`d2997196`（G06 合入后台账扣减 31→29 与发布审计），它改动的是台账
`docs/ops/iterations/form_structure_compatibility_consumers_v1.json` 与 G06 记录
`uc4_tax_deduction_native_lowcode_20260918.md`，属 G06 收口沿用同一分支带入，**不是 G07 的修改面**。

### 8.33.4 入口矩阵（L3 运行时实测，`sc_dev_demo`，action id 为库内真实值）

| 入口 | action | menu | view | 分组 | domain | 样本 | 浏览器 |
|---|---|---|---|---|---|---|---|
| 工资薪酬 | 858 | 673 | 1697 | 78,108 | `fact_type in [salary_registration, subsidy, bonus]` | 2 行 | 新建＋查看 ✔ |
| 薪资核算清单 | 873 | 695 | 1697 | 84,83 | `salary_registration & project_id != False` | 1 行 | 新建＋查看 ✔ |
| 社保公积 | 884 | 706 | 1697 | 108 | 3 类 social | 0 行 | 新建 ✔／查看 ⊘ |
| 薪资发放登记 | 874 | 696 | 1700 | 84 | 无 | 0 行 | 新建 ✔／查看 ⊘ |
| 项目管理人员工资登记 | 663 | 351 | 1697（＋tree 2067） | 78,108 | `salary_registration` | 1 行 | ⊘ 导航拒绝 |
| 社保人员登记 | 660 | 349 | 1697 | 78,108 | `social_person_registration` | 0 行 | ⊘ 导航拒绝 |
| 社保登记 | 661 | 350 | 1697 | 78,108 | `social_registration` | 0 行 | ⊘ 导航拒绝 |
| 补助 | 662 | 352 | 1697 | 78,108 | `subsidy` | 0 行 | ⊘ 导航拒绝 |
| 奖金 | 664 | 353 | 1697 | 78,108 | `bonus` | 1 行 | ⊘ 导航拒绝 |

升级后 9 条契约 state 全部正确：858 → id 662（新增）、166＝873、179＝884、167＝874、
168/169/170/171/172＝663/660/661/662/664；模型级 79 未动。
四个优先入口的身份与最终契约逐个核验（`ui.contract.v2` 200 且 `action_id`／`view_id`／`menu_id` 与入口一致）。

### 8.33.5 用户可见前后差异

- **858 变化最大**：此前渲染通用工作台平面（模型级稀疏字段序），现在渲染与 873／884 同源的业务任务面，
  含申请信息／人员／社保／工资／公积金／补助奖金／办理／历史来源分组的锚点导航。
- 八个归档入口：字段与分区**不减少**——退役体的 **57 个字段并集逐条在原生 arch 中命中**
   （`missing_from_arch: []`）。本批新增到该 arch 的字段共 **5 个**：4 个 provenance
  ＋ 货币伴随字段 `currency_id`（该视图**记录作用域字段节点** 66 → 69，其中 **arch 内呈现字段** 63 → 66，
  `removed: []`）。二者都只有退役体声明过，
  **没有凭空新增的业务事实**；订正见 8.33.11。
- 1697 新增条件性「历史来源」章节（仅 `legacy_document_no` 有值时出现），新建态默认不出现；
  1700 新增「经办与依据」承载 `responsible_id`，原先该字段落在无标题包装组里没有章节身份。
- **同一上下文重复被消除**：`employee_user_id`／`employee_name` 在 `provident_fund_registration`
  下此前**可见 2 次**（无条件的「人员」组 ＋ 公积金组），8 个退役体在人员／期间章节只呈现 1 次。
  已从 `payroll_provident_fund` 删除并加注释；L2 `test_the_person_is_presented_once_in_every_fact_type`
  以 `SINGLE_PRESENTATION_FACTS` 固定该事实。

### 8.33.6 首次偏差与修复层

| # | 现象 | 首次偏差位置 | 修复层 |
|---|---|---|---|
| 1 | `employee_user_id`／`employee_name` 在 `provident_fund_registration` 下同一上下文可见 2 次 | 产品：1697 原生 arch 的 `payroll_provident_fund` 组同时声明了只属于「人员」组的事实 | P0 结构（删重复声明，**未**按字段名批量去重其它分组） |
| 2 | 858 渲染通用平面而非业务任务面 | 产品：`action_sc_payroll_management` 无入口级 release，回落模型级 79 | P1 声明（补入口级发布，**未**改模型级 79） |
| 3 | 设计器工具在该 topic 下无法投放补丁（`Cannot read properties of undefined (reading 'label')`） | 工具：`formal_form_designer_journey.mjs` 只登记 material／document／invoice 三种字段身份 | P4 验证工具（新增 payroll 身份；`/tmp/g07-evidence/l4-designer-fail1-locator.log`） |
| 4 | 工具在发布后落到材料页签 `说明与附件` 超时 | 工具：业务页断言分支缺 payroll | P4 验证工具（新增 payroll 分支，改用产品自述的 `data-section-target` 做导航↔正文一致断言；`…fail2-preview-tab.log`） |
| 5 | 预览 popup 标签超时，**环境传输中断**：`popup_1` 19 条 `net::ERR_NETWORK_CHANGED`（模块图 CSS／Vue 资源） | 环境：宿主网络在运行时变更；**不是产品缺陷** | P4 验证工具（把 popup 信号与状态取证提前到预览 popup 创建前，使"传输未完成"与"标签缺失"可区分；`…fail3-preview-transport.log`） |
| 6 | outside 入口（873）等待材料页字面量 `出库日期` 超时 | 工具：隔离锚点是材料页字段 | P4 验证工具（改用本入口锚点字段的**原生标签**；`…fail4-outside-label.log`） |

第 5 条按用户口径**单独记为传输失败**，不改写成"零传输错误"，也不作为"已恢复"的判据：
重跑前只做了可恢复性核对（5174 在监听并返回页面、网络接口稳定），失败分类与恢复事实先记录。

### 8.33.7 低代码闭环（预览 → 发布 → 刷新 → 回滚 → 跨入口隔离）

入口：**858**（`sc.hr.payroll.document`／view 1697／menu 673）；隔离对照：**873**（同模型同 view 不同入口）。
报告 `artifacts/lowcode-form-loop/browser/designer-report.json`（`ok=true`、`restored=true`）：

- **归属**：`change_set_id=395`，`save_path=opened_new_change_set`，
  `draft_ownership={release:true, reason:created_by_this_run, created:true, fresh_requested:true}`，
  `save_open={requested_fresh:true, reported_created:true}` —— 以产品自身的 `fresh` 请求＋`created`
  回执证明"本轮创建"，不是"不在盘点里"。
- **前置授权**：`designer_draft_probe.decision=proceed`（`resume_only` 两次探测均 miss）、
  `designer_pre_write_gate.decision=proceed` —— 检查发生在**写入之前**。
- **投放补丁 3 条**：`requester_id` 改标签为「受管申请人」、移入新组「受管申请信息」、`contact_phone` 隐藏。
- **预览**：`preview_structure.parent=payroll_application_info`（7 个子节点），
  `visual_order.status=passed`（未改字段保持原生相对顺序，且至少一行保留共享列流）。
- **发布**：`published_content_verified=true`、`runtime_verified=true`，
  `stages.publication={published_content:passed, final_contract:passed, browser:passed, isolation:passed}`。
- **刷新后业务页（冷加载）**：`payroll_business_surface.navigation_target`
  ＝产品自述的 `[data-form-section-target="node:designer:business-section"]`，
  配置章节进入视口（`configured_section_y=227`），重命名字段确实在导航指向的章节内，
  被隐藏的 `contact_phone` 在业务页**不可见**。
- **回滚**：`restored=true` —— 回滚后**重新读取生效契约并与基线比对相等**（不是只看按钮回执）。
- **跨入口隔离**：`stages.outside_page={action_id:873, status:passed}` —— 873 新建页仍渲染
  `requester_id` 的**原生标签**、且不含「受管申请人」。
- **同屏复用复核草稿**：`review={draft_id:397, published:false, same_screen_reuse:passed}`，
  其归属同为 `created_by_this_run`。
- **恢复**：`recovery=[]`、`cleanup_guard={decision:proceed, foreign:[]}`、`browser_errors=[]`、
  `transport_recoveries=[]`。

### 8.33.8 分层验证结果

| 层 | 入口 | 身份 | 结果 |
|---|---|---|---|
| L1 | `make ci.local.iteration` | 接管阶段的 HEAD＋dirty（阶段身份 12 路径，含本批 3 条文档；最终候选 13 路径见 8.33.1） | **PASS**：16 静态测 0.109s OK；`baseline_iteration_execution_policy_guard` PASS；`coverage=L1_only`；`next=risk_selected_non_zero_L2_targets_required`。复核处置后以候选 `b0e54aa6` 重跑 L1 **PASS**（16 静态测 0.155s；`changedPathCount=13`，`unmappedPathCount=11`；当次**未持久化回执**）。冻结候选 `324394cc` 再跑 L1 **PASS**（16 静态测 0.130s，`change_state=clean`，`coverage=L1_only`，`receipt=none`；日志 `tmp/g07-evidence/l1-324394cc.log`） |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1` | `sc_dev_demo` | **PASS**：exit 0，`[local.dev.demo.authority] PASS`（`tmp/g07-evidence/l3-module-upgrade.log`） |
| L2 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestHrPayrollNativeLowcode,/smart_construction_core:TestProjectSalaryProduct,/smart_construction_core:TestSocialFundCapability,/smart_construction_core:TestTaxDeductionNativeLowcode'` | 接管阶段的 HEAD＋dirty | **PASS**：**34 测 0 failed 0 error**（`tmp/g07-evidence/l2-native-lowcode-34.log`）。过程中 13 测（2 failed）与 34 测（1 failed）两次中间失败已修后重跑，各自首次偏差见 8.33.6 |
| L2-重跑（受影响两类） | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestHrPayrollNativeLowcode[,/smart_construction_core:TestProjectSalaryProduct]'` | 复核处置后的候选 | **PASS**：口径订正后 `14 测 0 failed`（`tmp/g07-evidence/l2-refresh-nativelowcode-14.log`）；S5／S10 处置后 `16 测 0 failed`（payroll 类 15 测 ＋ 项目工资 1 测，`tmp/g07-evidence/l2-round2-16.log`）。未重跑其余两类（输入未变） |
| L4-只读 | `FORM_LOWCODE_TOPIC=payroll FORM_LOWCODE_REPRESENTATIVE=1 make local.dev.form_lowcode.browser` | 同上 | **PASS**：`ok=true`、`restored=true`、`browser_errors=[]`、`transport_recoveries=[]`、`cleanup_guard=proceed`、`recovery=[]`、业务指纹未变；报告 `artifacts/lowcode-form-loop/browser/representative-report-payroll.json` |
| L4-设计器 | `FORM_LOWCODE_TOPIC=payroll FORM_LOWCODE_DESIGNER=1 make local.dev.form_lowcode.browser` | 同上 | **PASS**：`[formal_form_lowcode_loop] PASS formal designer journey`（`tmp/g07-evidence/l4-designer-payroll.log`） |

**复用理由**：接管后只修改了 P4 验证工具 `formal_form_designer_journey.mjs`，它既不是 L1 静态扫描对象
（L1 已重跑确认无守卫漂移），也不是 L2 Python 测试的任何输入（测试集、模块代码、原生 arch、
契约声明均未变），因此 L2／L3 结果按"输入未变"复用，未重跑。

**桌面与窄屏**：只读代表报告已含 **1088×900 与 390×844** 双视口，约 180 组几何读数
（含首项在屏外／屏内、末→首、首→末、手动滚动后、轨道滚动后）**全部为"操作行与导航分离"**，
例如 858 查看态 390×844：`actions.bottom=309 < nav.top=322`；章节跳转后目标标题在视口内、
高亮与正文一致（`auto_reveal_press`、`keyboard_activation` 两条路径均 `delivered_active` 与 `pressed` 相同）。
`390` 新建态章节轨不溢出故 `section_navigation_press=not_applicable`（非通过，非失败）。

### 8.33.9 未覆盖项与剩余阻断（如实登记，不造数据）

- **884／660／661／662／874 的记录态（record_surface）未覆盖**：`empty_action_domain`（domain 0 行）。
  884／660／661／662 该 action 域内 0 行、模型内 2 行；874 域内 0 行。**未为补样本造数据。**
- **663／660／661／662／664 未做浏览器复核**：`NAVIGATION_AUTHORITY_DENIED`，原因是运行角色的
  `route.authority` **不含**「人事薪酬」分支（父链 349~353 ← 646 人事薪酬 ← 343 行政中心 ← 304）。
  菜单 349~353 的分组（78／108）与该用户分组**一致**，拒绝来自角色级路由权威，不是分组缺失；
  按 G06 对 action 789 的既有口径，**记为角色边界，不计产品缺陷、不把拒绝写成功**。
  这 5 个入口的原生结构与契约由 L2 断言覆盖（同一 view 1697／同一原生树）。
- **未执行项（保持未执行）**：最终 Quick、推送、建 PR、合并、部署、G08 启动、
  六组副本候选迁移、`sync_demo`／fixture reset／发布快照、历史工作树清理。
- **未改的既有残留（仅登记）**：本次设计器运行按工具既有设计**保留一张未发布复核草稿**
  `change_set_id=397`（`ready`／1 item／未发布／`created_by_this_run`），供复核使用；
  回滚以真实发布"回滚：表单设计配置"变更集（390／393／396）实现，随后按生效契约回读确认等于基线。
- **写入核对（只读回读）**：受保护草稿 163／190／192／194／233／267／274／276 的 `write_date`
  全部停留在 2026-09-17，本轮未被触碰；233／267／276 的 `ready` 状态维持原样。
- **台账**：保持 **29**，本轮不扣减；852 列表域与约 6 组副本候选继续留台账，不扩范围。

### 8.33.10 状态

批次状态（**该阶段历史口径**）：**G07 集中产品复核完成｜批次验收待收口｜未冻结｜未集成｜未部署**。
台账 **29**；89 入口整体交付未完成。下一步（**该阶段未执行**）：定向反例冻结 → 生成证据准备与预检 →
干净 HEAD 完整指纹 → 一次 Quick → 独立复核 → 外部归档 → Draft PR。
上述「未执行」项已在本批后续阶段执行并闭合，最终口径见 **8.33.13**。

### 8.33.11 收口前自我复核的发现与修正（口径，非产品缺陷）

冻结前对**整批 13 路径差异**做只读复核（不只审最后一次 P4 改动），方法：逐入口重算
`ui.contract.v2` 最终契约、重算 1697／1700 原生 arch 的字段集合增量、并对全部差异做
「被删除断言」扫描（`git diff origin/main...HEAD | grep '^-' | grep assert`）。

**扫描结果**：全批**只删除了 4 行断言**，全部位于 `tests/test_project_salary_product.py`，
且是**改写而非删除**——原 4 行检查「契约 `fields` 里含某字段」，替换为**更强**的一组断言
（`composition_mode == native_semantic_surface`、`sections`／`fields`／`columns` 均不存在、
且该事实在原生 arch 中确实由 `name="..."` 承载）。P4 工具差异**未删除任何断言**（0 行），
新增断言行数随两轮处置变化：阶段身份（`96f0c9bd`）为 **78 行**，含复核处置的候选 `b0e54aa6`
与冻结候选 `324394cc` 均为 **89 行**。口径为**排除本记录文件**的路径限定命令
（本记录自身会引用 `assert` 字样，若纳入则读数自指虚增，`b0e54aa6` 91 行、`324394cc` 92 行，
冻结前 ≠ 冻结后，不可复现，故不作为口径）：
`git diff -U0 5938d6c6..HEAD -- . ":(exclude)docs/ops/iterations/form_structure_consumption_stabilization_20260917.md" | grep -E "^\+" | grep -c assert`；
删除断言始终为**同一 4 行**（改写而非删除，该口径不受上述排除影响）。
**不构成「以降低断言取得通过」。**

**发现（已修）**：本批新增到 1697 原生 arch 的字段实测为 **5 个**（4 个 provenance ＋
货币伴随字段 `currency_id`；字段节点口径见 8.33.12 的 S11 订正，`removed: []`），但
①本记录 8.33.5 原写「其中 4 个 provenance 是本批唯一新增的字段」，
②新增 L2 测试 `test_the_arch_only_added_what_the_retired_bodies_declared` 的原文档字符串写
「只有 4 个是本批未承载过的事实」，二者都把 `currency_id` 漏计，且测试名承诺的
「只新增退役体声明过的事实」当时**未被断言**。

| 项 | 分类 | 首次偏差 | 修正层 | 修正 |
|---|---|---|---|---|
| 新增字段计数 4 vs 实测 5 | 口径 / 证据完整性（非产品缺陷，未影响任何 PASS 结论） | 记录与测试文档字符串按 provenance 记忆计数，漏计同时新增的货币伴随字段 | P4 证据与记录（`tests/test_hr_payroll_native_lowcode.py`、本记录） | 测试补 `ARCH_FACTS_ADDED_BY_THIS_BATCH`（5 项）并断言：新增集合 ⊆ 退役体声明集合、逐项在 arch 中命中、`currency_id` 恰好 1 处且 `invisible`／`readonly`；文档字符串与记录改按实测口径表述 |

**修正未扩大范围**：只订正该批自身的口径与**补齐缺少的断言**（未删除、未放宽任何断言），
未改产品代码、未改台账、未改其它主题。修正后按「输入已变」重跑受影响的 L2 与 L1，
并**重新冻结**（新 HEAD／新 tree／新指纹），再对该 HEAD 运行**一次** Quick。

**冻结回执去向（口径）**：exact-head Quick 回执与外部归档哈希按既有约定写入**外部归档件**
（`identity.json`／`worktree-fingerprint.json`／`review.json`／`summary.md`／`pr-body.md`）与 PR 正文；
按 8.33 既有口径，指纹与回执值**不写入本记录文件**，避免写入本身改变被冻结候选；
正式回填与台账扣减留待合入后的独立台账提交（同 G06 的 `d2997196` 口径）。

### 8.33.12 独立复核（第 1 轮，绑定候选 c4d434f9）

独立只读复核者绑定候选 `c4d434f9ba7e2651ac2a05c13b9813e690e30347`（范围 `5938d6c6..c4d434f9`），
自取数重算，未写任何文件、未重跑门禁；结论 **APPROVE_WITH_MINOR**（`noOpenBlockerOrMajor: true`）。

复核者自测复现的本批核心事实（与本记录一致）：1697 字段集合 `added={currency_id, 4×legacy_*}`、`removed=[]`；
退役体并集按 base 树独立重建为 payroll 49 ＋ payment 17（重叠 9）＝ **57**，与测试常量逐项相等；
`provident_fund_registration` 可见事实 31 → 29（**只**少了 `employee_user_id`／`employee_name` 各 1），
其余 `fact_type` 计数不变；`fact_type` 分组在每个合法类型下**恰有一个可见**、未设类型时**零个可见**；
来源追溯隐藏为合法声明且 4 个 provenance 字段仍声明、`readonly`；全批**无断言被删除或跳过**；
模型级注解未动（无 `action_id`、27 字段）；Quick 回执经受管 `verify` 通过；指纹内存复算与产物 digest 相等。

开放项与处置：

| 发现 | 严重度 | 复核意见 | 处置 |
|---|---|---|---|
| S1–S4、S13 | — | 结构消费、同上下文重复、分组互斥、条件隐藏、858 入口级发布等**均已核实闭合** | 无需处置 |
| S5 | minor | `tests/test_project_salary_product.py` 改写后用 `assertIn('name="%s"' % fact, arch_db)` 做**子串**匹配，严谨度低于节点断言 | **已修**：改为解析 arch 并断言**字段节点**存在（`arch.xpath(".//field")` 的 `name` 集合成员），避免修饰表达式／筛选域／注释中的同名文本误判 |
| S10 | minor | 858／884 的 action context 无 `default_fact_type`，且分组按 `fact_type` 门控 → 新建面在选定类型前**不显示任何分组**（退役体当时是无条件呈现）；该差异**无断言覆盖** | **已修**：新增 L2 `test_the_fact_type_selector_stays_the_reachable_entry_to_every_group`——断言选择器在正文中**恰好声明一次**、**不受任何门控**（无 `invisible`／`readonly`／`groups`）、模型字段 `required=True`，且未设／未知类型时**零分组可见**；即"受门控的事实不失去入口" |
| S11 | nit | 8.33.5／8.33.11 的"字段数 66 → 69"是**记录作用域**（含记录自身的 `name`／`model`／`arch` 节点）；arch 内呈现字段为 63 → 66 | **已修**：两处均标注口径（记录作用域 66 → 69；arch 内呈现 63 → 66），增量与新增集合两种口径一致 |
| S12 | nit | 范围内还含 `d2997196`（G06 收口：台账 31→29 与两处文档），8.33 未点明该改动归属 | **已修**：8.33.3 补"在范围差异内的 G06 收口（非 G07 内容）"说明 |

**第 1 轮另有 3 项开放项**（同属记录口径，核见下）：S7 锚点分组数（8.33.3 的"12 个分组"）、
S8 路径数（8.33.1／8.33.8 的"12"）、S9 断言行数与 L2 测数（8.33.11 的"78 行"、8.33.8 的"34 测"）。

**复核者自陈局限**（保留，不代为消除）：未执行 Odoo 测试／浏览器旅程／L3／Quick，L1–L4 结论读自回执与记录；
库内 id（action 662／166／179／167／168–172、view 1697／1700、menu、契约 79、change set 395／397／390／393／396）
与受保护草稿 `write_date` 回读属库事实，只读复核无法复测；`empty_action_domain` 行数未复测；
`not legacy_document_no` 为表达式求值而非渲染观测；P4 复核为静态。

**第 2 轮**：处置提交产生**新候选**（新 HEAD／新 tree／新指纹），须重新冻结并重跑**一次** exact-head Quick；
绑定新候选的复核结论与回执哈希按 8.33.11 的口径写入**外部归档** `review.json`，不写入本记录文件。

#### 8.33.12.1 第 2 轮复核（绑定候选 b0e54aa6）与记录口径收口

第 2 轮独立只读复核绑定候选 `b0e54aa662b76620872e546910eb454f94394c1e`，只审增量
`c4d434f9..b0e54aa6`，结论 **APPROVE_WITH_MINOR**（`noOpenBlockerOrMajor: true`）：

- **R-S5 闭合**：`test_project_salary_product.py` 已由子串匹配改为解析 arch 的字段节点断言；
  复核者自查 arch 格式（`arch_db.encode()` 先编码再解析，避免 lxml 对含编码声明的 str 报错），
  与既有 payroll 测试同法，未引入新的解析脆弱点。
- **R-S10 闭合**：新增测试确实断言"受门控的事实不失去入口"（选择器声明唯一、无
  `invisible`／`readonly`／`groups`、模型字段 `required=True`、未设／未知类型零分组可见），
  比第 1 轮**更强**（该缺口此前无断言），且与互斥性测试输入不同、不重复。
- **R-S11／R-S12 闭合**：字段计数两口径、范围内 `d2997196` 归属均与本记录一致。
- **R-POS-1 闭合**：增量**只改两个测试文件与本记录**，未触碰任何产品渲染输入
  （`addons/**/views`、`addons/**/data`、`frontend`、`scripts` 的路径过滤差异为空），
  无断言被删除或跳过（删除断言仍为同一 4 行、`skip`／`xfail`／`.only(` 为 0）。
- **R-NEW-1（本轮已修）**：8.33.12 原表漏列第 1 轮的 S7／S8／S9，现已补列于上。

本轮同时收口第 1 轮遗留的 3 项记录口径（均为**文档数字**，非产品事实）：

| 发现 | 实测（本轮自取数） | 订正 |
|---|---|---|
| S7 锚点分组数 | 两个 form 视图带 `data-sc-anchor` 的分组共 **11 个**（1697：11 组中 8 个；1700：4 组中 3 个）；无标题包装组保留 **4 个**（1697 3 ＋ 1700 1） | 8.33.3 由"1697：12 个分组"改为按视图分列的 8／3 与 4 个未动包装组 |
| S8 路径数 | 最终候选相对 `5938d6c6` 为 **13 路径**；接管阶段身份（`bd3df6f7`）为 12 | 8.33.1 区分"接管阶段 12 条"与"最终候选 13 条（第 13 条为 `complexity_budget_report.md`）"；8.33.8 的 L1 行改标阶段身份并补 `b0e54aa6` 重跑 |
| S9 断言与测数 | 新增断言行（**排除本记录文件**口径）：`96f0c9bd` 为 78、`b0e54aa6` 与 `324394cc` 均为 89；全路径口径会因本记录自身引用 `assert` 字样而虚增（`b0e54aa6` 91／`324394cc` 92），冻结前 ≠ 冻结后，故不作为口径；删除断言恒为同一 4 行；payroll 测试类 14 → **15 测** | 8.33.11 改用排除本记录文件的稳定口径并标注阶段；8.33.8 新增"L2-重跑"行（14 测／16 测），并把原 34 测行标为接管阶段身份 |

**第 3 轮**：上述订正产生**新候选**，重新冻结（新 HEAD／新 tree／新指纹）并重跑**一次** exact-head Quick；
绑定新候选的第 3 轮复核结论与回执哈希按 8.33.11 口径写入**外部归档** `review.json`，不写入本记录文件。

#### 8.33.12.2 第 3 轮复核（绑定候选 324394cc）与自指计数收口

第 3 轮独立只读复核绑定候选 `324394cc0302536d2bbd90ca63e3e17fae89a4e8`，只审增量
`b0e54aa6..324394cc`，结论 **APPROVE_WITH_MINOR**（`noOpenBlockerOrMajor: true`）：

- **R-G3-3 闭合**：增量只改本记录文件；对 `addons/**/views`、`addons/**/data`、`frontend`、
  `scripts` 做路径过滤后差异为 **0 路径**，未触碰任何产品渲染输入。
- **R-G3-4 闭合**：增量未删除／跳过任何断言（增量内删除断言 0 行；全批删除恒为同一 4 行改写）；
  唯一的 `skip`／`xfail` 命中来自本记录正文的引用，非真实跳过。
- **R-G3-5 闭合**：8.33.1／8.33.8 已把阶段身份（12 路径）与最终候选（13 路径）分开，
  且 `b0e54aa6` 的 L1 重跑已标为候选绑定，未把未验证写成已验证。
- **R-G3-1（minor，本轮已修）**：8.33.11／8.33.12.1 原把 `b0e54aa6` 称作"最终候选"并记 **91 行**；
  该命令在冻结候选处读数为 **92**（本记录新增行自身含 `assert` 字样），属**自指偏差**，
  冻结前 ≠ 冻结后、不可复现。
- **R-G3-2（nit，本轮已修）**：8.33.3 引用的 `grep -c '^+.*data-sc-anchor'` 未限定路径；
  未限定读数会把测试／契约／脚本与**本记录正文**中的同名字符串一并命中，**随本记录内容变化**，
  因此**已从记录中移除该读数**（不再引用任何未限定值）。分组数 **11** 仅在路径限定于视图文件
  时成立，且该值可复现。

本轮收口方式（**改用不随本记录内容变化的稳定口径**）：

| 指标 | 原口径（自指，不可复现） | 新口径（稳定） |
|---|---|---|
| 新增断言行 | `git diff -U0 5938d6c6..HEAD \| grep -E "^\+" \| grep -c assert` → `96f0c9bd` 78／`b0e54aa6` 91／`324394cc` 92 | 同命令 **加 `-- . ":(exclude)<本记录文件>"`** → `96f0c9bd` 78／`b0e54aa6` 89／`324394cc` **89**（冻结前＝冻结后） |
| 锚点分组数 | `grep -c '^+.*data-sc-anchor'`（不限定路径）→ **不稳定，已弃用**（含测试／契约／脚本与本记录正文的命中，随本记录内容变化） | **路径限定 `-- <views/core/hr_payroll_document_views.xml>`** → 11 |

两项均为**记录口径**（非产品事实、非测试削弱）：删除断言计数不受上述排除影响，恒为同一 4 行；
产品渲染输入在本轮与上一轮增量中均未被触碰。

**第 4 轮**：本轮订正产生**新候选**，重新冻结并重跑一次 exact-head Quick；第 4 轮复核只审
本增量，结论与回执哈希写入外部归档 `review.json`，不写入本记录文件。

#### 8.33.12.3 第 4 轮复核（绑定候选 4b810fa2）与自指计数类终止

第 4 轮独立只读复核绑定候选 `4b810fa2785cc525fb26eb27254e3b6ae98a1c61`，只审增量
`324394cc..4b810fa2`，结论 **APPROVE_WITH_MINOR**（`noOpenBlockerOrMajor: true`）：

- **R-G4-2 闭合**：增量只改本记录文件；`addons/**/views`、`addons/**/data`、`frontend`、
  `scripts` 路径过滤差异 **0 条**。
- **R-G4-3 闭合**：增量未删除／跳过任何测试断言（增量内被误计的那 1 行是记录正文对
  `grep -c assert` 的引用，非测试断言）；全批删除断言仍恒为同一 4 行。
- **R-G4-4 闭合**：本节登记的第 3 轮结论、`reviewedRange` 与 `noOpenBlockerOrMajor` 与复核者
  自取数一致；8.33.8 新增的 L1 行可由 `tmp/g07-evidence/l1-324394cc.log` 佐证；无"未覆盖写成通过"。
- **R-G3-1／R-G3-2 闭合**（复核者自取数复现）：排除本记录文件的断言口径 `96f0c9bd` 78／
  `b0e54aa6` 89／`324394cc` 89／`4b810fa2` 89，即**冻结前＝冻结后**；文档已不再把 `b0e54aa6`
  称作"最终候选"。
- **R-G4-1（minor，本轮已修）**：8.33.3 与 8.33.12.2 仍引用**未限定路径**的锚点读数（写作
  21，其构成被标为"本记录 3"）；该读数会把本记录正文自身的同名字符串计入，随本记录内容变化，
  在冻结候选处已不等于 21，属与 R-G3-1 同类别的**自指偏差**。

本轮收口方式：**不再刷新该读数，而是从记录中移除任何未限定值**（R-G4-1 的处置），使该类问题
**终止**——记录只保留可复现的路径限定值（锚点分组 **11**、断言 **89／删除 4**）。

**该类问题的边界（记录、不再迭代）**：任何"描述包含本记录文件自身在内的整批差异"的计数，
只要被写进本记录，其读数就会因写入而改变，**永远不可能在记录内自洽**。因此本记录**只允许**
引用两类计数：①**路径限定或排除本记录文件**的命令读数；②**某个不可变提交处**测得的阶段值
（该提交内容固定，故可复现）。其余形式的未限定总计**一律不写入本记录**。
本轮与上一轮的实际差异均在**记录正文**内，未改动任何产品渲染输入、测试断言或契约。

**第 5 轮**：本轮订正产生**新候选**，重新冻结并重跑一次 exact-head Quick；第 5 轮复核只审本
增量，结论与回执哈希写入外部归档 `review.json`。

#### 8.33.12.4 第 5 轮复核（绑定最终候选 71546e09）与整批终止

第 5 轮独立只读复核绑定**最终候选** `71546e09e67fec865579a20f7f551985178048e9`，只审增量
`4b810fa2..71546e09`，结论 **APPROVE**（`noOpenBlockerOrMajor: true`，无 open blocker／major／minor）：

- **R-G4-1 闭合**：记录按「**移除而非刷新**」处置——正文不再引用任何未限定路径的锚点读数，
  路径限定读数 **11** 可复现，并把边界规则写入记录（只允许①路径限定／排除本记录文件的命令读数，
  ②**不可变提交处**测得的阶段值）。
- **G5-1（nit，已闭合）**：其余记录内数字（新增断言 89、删除断言 4、锚点分组 11、payroll 测试 15，
  以及 8.33.1 的批内路径计数）与边界规则自洽。
- **G5-2（nit，**open**，登记为「无需修复的残留」）**：8.33.1 的批内路径计数是整批差异总数，
  不属于上述两类形式之一；但路径集合不随记录内容变化，故**可复现**。**按事实登记为 open，
  不写成闭合、不作为缺陷、不触发修复。**

**复核者自陈局限（保留，不代为消除）**：本轮未执行 Quick／L3／Odoo 测试／浏览器门禁，
全部 PASS 与身份结论读自已存在的回执与本地日志；库内 id、模型级契约 79、change set 395／397
与受保护草稿 `write_date` 属库事实，只读复核无法复测；`artifacts/` 为外链目录，
指纹 digest 与 7515 路径未由复核者重算；`tmp/g07-evidence` 日志为未跟踪的本地产物。

**第 5 轮为终止轮**：结论 APPROVE 且无 open blocker／major／minor，记录口径不再迭代。

### 8.33.13 G07 主线集成与台账 29 → 25（2026-09-18）

冻结候选 `71546e09e67fec865579a20f7f551985178048e9`（tree `6c0cbcd9306a61fa72aea51231cade997af7e4de`，
7515 路径完整指纹，exact-head `ci.local.quick` PASS）经 **PR #495** 以 squash 合入 main
`b781e3c241bf42b2ae51c6ac4064c4a1af647a65`；`origin/main^{tree}` 与候选 tree **逐字节一致**
（`mergedAt` 2026-09-18T13:57:52Z，`mergedBy` lidefend）。PR 承载范围为 8.33.1 所列的批内路径与提交
（**不可变提交处的阶段值**），不是单一「工资表单迁移」；其中 `d2997196` 为 G06 收口随本批带入（见 8.33.3）。

该 head 上远端必检项 **9 success／3 skipped／0 fail**。success：`classify`／`frontend_release_gate`／
`merge_policy_gate`／`professional_authorization`／`professional_quality_gate`／`public_guard`／
`public_guard_classify`／`python310_runtime_compatibility`／`release_candidate_gate`；
skipped：`fast`／`classify`（候选检查变体）／`wait_for_candidate_checks`。
合入后 main 的推送运行（run `35353315462`）中 `classify` 与 `merge_policy_gate` 同为 success、`fast` skipped。

台账 **29 → 25**：退役本册 **4 个正式入口条目**（**873 薪资核算清单／874 薪资发放登记／884 社保公积／
858 工资薪酬**，视图 1697／1700），登记于 `uc4G07PublishedAudit`。按**已合入源码**逐项核对：

- 四条入口契约（`project_payroll_productized_form_v1`／`project_salary_payment_productized_form_v1`／
  `social_fund_form_v1`／本批新增的 `hr_payroll_management_productized_form_v1`）只留 `title` ＋
  `composition_mode: native_semantic_surface`（priority 800，各自绑定本入口 action），
  **无 sections／fields／columns**，兼容结构副本已退出；884 的 `fact_authority`／`allowed_fact_types`
  原样保留在 `view_orchestration.context`（退役的是结构副本，不是该入口声明的业务事实范围）。
- **858 的计数边界**：该条目原先引用**模型级** `sc_hr_payroll_document_form_structure_generated_v1`
  （id 79）；本批为它补了**入口级发布**，模型级层不再到达该入口、但仍服务模型。因此 858 按
  **条目退役**计数，**不是**退役模型级层；模型级 79 **未删未改**。
- **不额外计数**：与 1697 共享的 5 个兄弟入口（660／661／662／663／664）**从未登记在本册**，
  其入口级结构副本随本批一并退役，但**不构成额外扣减**（`uc4G07PublishedAudit.bypassConsumers`，
  `counted=false`）；视图 1697（8 个 action 共享）／1700 为共享原生主视图，**不随扣减退役**。

**保留边界（不随本批关闭）**：884／660／661／662／874 记录态 `empty_action_domain`（域内 0 行）、
**未造数据补样本**；663／660／661／662／664 浏览器导航 `NAVIGATION_AUTHORITY_DENIED`（角色边界，
不计产品缺陷、不写成通过）；设计器一次宿主传输中断（`net::ERR_NETWORK_CHANGED`）单独记录、
不改写成「零传输错误」；复核草稿 397 保留；852 列表域与约 6 组副本候选继续留台账。
`nextBatch` 前进到 **G08 上下文办理工作台**（875／877／878，视图 1932／1933／1934），
`sourceMainlineHead` 更新为合入后 main；**G08 未启动**。

本提交为**文档类单职责提交**（台账 ＋ 本记录，路径集合固定为 2）；**未触碰**任何产品代码、契约、
测试或验证工具输入，故不改动 8.33.8 的 L1–L4 结论，也不重跑 Quick。

**本提交自身验证**：L1 `make ci.local.iteration` PASS（16 静态测；变更路径映射为 2 条文档路径、
无 L2 目标，`manualNonZeroL2Required` 因路径未映射而提示，但无产品／测试输入变化，故**无对应 L2 目标可跑**）；
`make ci.generated_evidence.preflight` PASS（生成报告与测试清单全部为当前，含 7 测非零）。
按阶段规则**不在本提交重跑 Quick**：Quick 绑定干净冻结候选，本提交是合入后的文档收口，
其 Quick 回执沿用候选 `71546e09` 的 exact-head 回执；待该提交随下一批 PR 交付时按其候选重新冻结。

状态：**G07 批次验收完成（本批范围）｜主线集成完成（PR #495，squash 同树）｜未部署｜89 入口交付未完成｜台账 25｜G08 未启动**。

---

## 8.34 G08 上下文办理工作台整组原生结构迁移（2026-09-18 结构迁移；2026-09-19 集中复核后二轮＋三轮＋四轮整改，待第四轮产品复核）

> 本节分两轮读完：**8.34.1–8.34.8 为第一轮（结构迁移）记录，其中已被第二轮更正的口径就地标注**；
> **8.34.10 为第二轮（集中产品复核整改 A／B／C／D 四包）**；**8.34.9 为当前状态**。
> 第一轮结论中凡与第二轮冲突处，以 8.34.8 的更正段与 8.34.10 为准。

### 8.34.1 承接与归属

- **承接基线**：`origin/main` = `26d254ade3f153b466f6baa61f84695826443567`（8.33.13 的台账尾项
  commit `e61e275f` 经 **PR #496** squash 合入，`mergedAt` 2026-09-18T14:30:52Z；合并 tree
  `bde8dd68` 与本地提交 tree 逐字节一致）。合入后主线台账 `count=25`、`uc4G07PublishedAudit` 在册、
  `nextBatch.selectedGroup=G08`。
- **本批工作树**：`feature/uc4-g08-context-workspace-native-v1`（一个 worktree 一个写入者，只交付
  **G08 一组**，不混入 G09 或六组副本候选）。
- **相对基线的交付范围 10 条路径**：3 条 P1 入口契约声明 ＋ 3 条 P1 行业原生视图结构 ＋
  1 条新增 L2 测试 ＋ 1 条 L1/L2 注册 ＋ 1 条 P4 只读验证登记 ＋ 1 条本记录（详见 8.34.3）。
  L1 在提交前（`change_state=dirty`）实测 `changedPathCount=10`、`unmappedPathCount=10`：
  这两个计数都表示**本批 10 条路径全部未命中前端增量测试推荐映射**
  （`scripts/verify/frontend_dev_incremental.py`：`unmapped_paths = [path for path in paths if not
  select_targets([path])]`），并按同一份回执置 `manualNonZeroL2Required=true`。它**既不表示
  "没有未映射路径"，也不自动等于门禁失败**：含义只是增量的自动推荐为空，必须**人工选择非零 L2**，
  本批即按 8.34.7 的显式 tag 集合执行。被覆盖的检查逐条列在 8.34.7 的路径覆盖表。
  **未推送、未建 PR、未冻结、未部署。** 批内交付提交相对 `26d254ad` 为 10 路径；
  提交后工作树 `change_state=clean`、L1 复跑 PASS。

### 8.34.2 入口矩阵（L3 运行时实测，`sc_dev_demo`，action／view／menu 为库内真实值）

| 入口 | action | menu | view | 模型 | 分组 | 动作载体 | domain | target |
|---|---|---|---|---|---|---|---|---|
| 班组借/扣款登记 | 875 | 697 | 1932 | `sc.team.loan.deduction.workspace` | 83,84 | 登记借款／登记扣款／查看借扣款台账 | 无 | `current` |
| 往来款登记 | 877 | 699 | 1933 | `sc.current.account.workspace` | 95,96 | 项目借/还公司款、承包人借/还项目款、账户间调拨、查看往来台账 | 无 | `current` |
| 公司&项目退款 | 878 | 700 | 1934 | `sc.company.project.refund.workspace` | 95,96 | 扣款实缴退回、投标保证金退回、合同保证金退回、自筹退回、查看关联台账 | 无 | `current` |

- 三个模型均为 **`TransientModel` 派发工作台**：自身不持有业务事实，表头每个按钮打开的是真正承载
  资金的单据（借款／费用／资金调拨／退款）。三条视图均为 **唯一主视图**（`inherit_id=False`、
  `active=True`、`type=form`、prio 16），三模型互不共享视图。
- **无**任何 action 钉 `view_id`／`view_ids`、无 `domain`、`context={}`、`res_id=0`、`view_mode=form`；
  一模型一 action，**没有旁路消费者**（`_action_values()` 按非模型 `res_model` 派发、`views [(False,'form')]`，
  故本次**未触碰**任何 action 行为，存储的 view 解析保持原样）。
- **旧配置来源**：台账 `legacyConfigurations` 列了 3 条
  （`company_project_refund_workspace_form_v1`／`current_account_workspace_form_v1`／
  `team_loan_deduction_workspace_form_v1`），与库内入口级契约 **id 176／175／173** 一一对应，
  **命名完整、无漏计**（与 G07「清单是命名不全」不同：本组三条就是全部，且**没有模型级契约**）。
  `evidenceStatus` 为 `grouped_from_existing_44_entry_ledger_not_runtime_revalidated`，本批已按运行时复核。

### 8.34.3 修改范围与影响面

| 层 | 文件 | 内容 |
|---|---|---|
| P1 声明 | `data/team_loan_deduction_workspace_contract.xml`、`data/current_account_workspace_contract.xml`、`data/company_project_refund_workspace_contract.xml` | 三条入口契约只留 `title` ＋ `composition_mode: native_semantic_surface`，退役 `entry_semantic_surface` 的 sections／fields／columns 副本；`view_orchestration.context` 的语义声明**原样保留**（`fact_authority: dispatch_only`，875 无附加键；877 保留 `fact_models`／`projection_authority`；878 同）。顶部记录决策与回滚方式（`git revert`，无数据迁移），并注明与 G06 契约 177／G07 契约 884 同一规则 |
| **P1** 结构 | `views/support/team_loan_deduction_workspace_views.xml`、`views/support/current_account_workspace_views.xml`、`views/support/company_project_refund_workspace_views.xml` | 原生 form 的业务分组补 `name` ＋ `data-sc-anchor`（`team_loan_processing_context`／`_note`、`current_account_…`、`company_project_refund_…`）并显式声明 `col`（办理上下文 2／办理说明 1，与退役体声明一致）；第二轮再把 `办理提示` 独立成组（见 8.34.10-B） |
| L1/L2 | `tests/test_context_workspace_native_lowcode.py`（新增，13 测，tag `uc4_native_lowcode`）、`tests/__init__.py` | 见 8.34.7 |
| P4 只读 | `scripts/verify/local_dev_form_lowcode_scope.py` | 新增只读 topic `context_workspace`（875/menu 697、877/menu 699、878/menu 700 三条路由）＋ 样本字段与机制断言登记；复用既有 runner／环境／身份，未另建 fixture、未加写入开关 |

**边界保持**：未触碰 action／menu／ACL／security CSV／模型代码／计算字段；未执行 `sync_demo`／
fixture reset／发布快照／无关 upgrade；**未创造任何业务数据**。

**归属更正（第一轮记录修正）**：上面三份 `views/support/*_workspace_views.xml` 原先记作 **P0 结构**，
是**按载体类型**（XML 视图）误判层级。它们是施工行业标准产品（P1
`construction_industry_standard_product`）在 `smart_construction_core` 内声明的业务表单，
不是平台内核（P0）的机制代码；P0 的判据是"平台机制由谁拥有"，不是"文件扩展名是不是 XML"。
本批逐条更正为 **P1**，并同步更正 8.34.1 与 8.34.7 的同一措辞。第一轮已在册的层级结论其余不变。

### 8.34.3.1 第二轮（集中复核整改）改动范围

| 层 | 文件 | 内容 |
|---|---|---|
| P0 机制 | `addons/smart_core/utils/contract_governance_domain_overrides.py`、`addons/smart_core/utils/contract_governance.py`、`addons/smart_core/handlers/ui_contract_v2.py` | 新增"只声明语义、不改结构"的 override 通道 `native_authority_safe` ＋ `apply_native_authority_domain_overrides()`。原生视图拥有表单结构时通用治理整段跳过，该通道只放行语义声明，避免"迁移到原生权威就静默丢掉入口声明的表单治理"；同时让该声明在**记录面**（无业务表单策略的非 create 路径）也生效。**只有显式登记的语义 override 走这条路，改写结构的 override 仍留在门外** |
| P0 机制 | `addons/smart_core/core/unified_page_contract_v2_assembler.py` | 把 `form_governance` 从源契约搬到 `runtimeContract.governance`，并让原生表单投影**合并** `governance` 而不是整键覆盖（原覆盖会把已声明的语义丢掉，是"标签改不动"的传输层根因） |
| P1 声明 | `addons/smart_construction_core/services/contract_governance_overrides.py` | `context_workspace_form` 登记为 `native_authority_safe`，逐入口声明 `primary_action_label=记录办理上下文` ＋ `collaboration_unavailable_message`（"只用于本次派发，不长期保留…"）。**按模型→标签的显式声明，不是改通用 create 默认值** |
| P1 入口 | `addons/smart_construction_core/core_extension_policy_maps.py` | 按**既有授权路径**（角色导航面 ＋ 菜单自身持组 ＋ 可见性门控的路由生成）对齐入口与派发路由：`project_member` 补 875 入口 ＋ 3 条派发目标路由，`finance` 补 877／878 入口菜单。**未新增机制、未改 ACL、未开放系统设置 887** |
| P1 模型 | `addons/smart_construction_core/models/support/context_workspace_entry_authority.py`（新增）、三个 workspace 模型、`models/support/__init__.py` | 新增 AbstractModel `sc.context.workspace.entry.authority`：把派发返回的 window action 钉到**当前主体路由权威里确实存在**的那个 `menu_id`，并把 `date`／`datetime` 上下文转成 ISO 字符串再交给客户端。查不到路由即**业务文案 fail-closed**，不再把用户丢进导航拒绝页 |
| P1 前端 | `ContractFormPage.vue`、`contractForm/collaborationContract.ts`、`contractForm/useRecordCollaborationPresentation.ts` | 渲染层只认契约声明：`resolveDeclaredFormGovernance()` 读 `runtimeContract.governance.form_governance`，`isDispatchContextGovernance()` 认 `create_flow_mode=transient_dispatch`，据此决定按钮文案与协作面板文案。**不硬编码任何模型名／入口名** |
| L1/L2 | `tests/test_context_workspace_native_lowcode.py`、三个同类测试 | 见 8.34.7 |
| P4 只读 | `scripts/verify/local_dev_form_lowcode_scope.py` | 更正 `dispatch_only` 的表述（不是"临时模型没有记录面"），见 8.34.10-B |

**第二轮边界保持**：未触碰 action／menu ACL 记录／security CSV／系统设置 887；未执行 `sync_demo`／
fixture reset／发布快照；**未创造任何业务单据**（见 8.34.10-A 的写入核对）。

### 8.34.4 用户可见前后差异

- **前**：入口契约另投一层 `entry_semantic_surface` 主体（办理上下文 2 列 ＋ 办理说明 1 列 ＋ 5 字段），
  与原生 form 已声明的同名分组**并存**；节目标识只存在于契约副本里。
- **后**：结构权威只留原生 arch；`办理上下文`／`办理说明` 成为**可寻址的章节身份**
  （`data-form-section-target="node:<anchor>:business-section"`），字段集合、分组标题与列数与退役体一致
  （5 字段、2 列／1 列，运行态实测），动作载体仍在表头。**用户可感知的字段与分组无增无减**，
  差别是同一结构不再有两份声明。
- **回滚**：`git revert` 本批提交即可（无数据迁移、无配置写）。

### 8.34.5 只读代表面（L4-只读，`FORM_LOWCODE_TOPIC=context_workspace FORM_LOWCODE_REPRESENTATIVE=1`）

报告 `artifacts/lowcode-form-loop/browser/representative-report-context_workspace.json`（`ok=true`）：

- `restored=true`、`browser_errors=[]`、`transport_recoveries=[]`、`cleanup_guard={decision:proceed, foreign:[]}`、
  `recovery=[]`、`representative_uncovered=[]`、`representative_blocked=[]`。
- 三条入口**各自**一个 create 面（875／877／878），`presentation_mode=create`；
  实测 **5 字段**＝ `project_id`／`partner_id`／`business_date`／`processing_advisory`／`note`，
  **4 个章节入口**＝办理上下文／办理说明／办理提示／协作记录（第二轮把办理提示独立成组后的重跑值；
  第一轮为 3 个），四个入口 `resolved=true`／`visible=true`，
  `findings` 四类（重复字段／空容器／装饰分组／带标题布局组）**全空**；
  章节列数实测 `template-form-section-grid--columns-2`（办理上下文）与 `--columns-1`（办理说明／办理提示），
  与退役体声明逐项一致。
- 双视口 **1088×900 与 390×844** 的 `section_navigation_press` 均为
  `not_applicable / track_does_not_overflow`（业务章节不足以致轨道溢出，**非通过也非失败**）。
- **第二轮重跑同口径**：`ok=true`、`restored=true`、`browser_errors=[]`、`transport_recoveries=[]`、
  `representative_uncovered=[]`、`representative_blocked=[]`、`cleanup_guard={decision:proceed, foreign:[]}`；
  报告绑定 `candidate=4c8deaf8…`、`dirty=true`（**如实标注工作树为 dirty**，不冒充冻结候选）。
  同批 `sample_state.state=available`（875 `domain_rows=15`／877 `6`／878 `5`），
  即**记录面确有可读样本行**——与 8.34.8-① 的更正一致。

### 8.34.6 配置面与跨入口隔离

- **跨入口隔离（L2 断言 + 运行态只读）**：`test_each_entry_keeps_its_own_native_authority` 固定
  3 个不同模型／3 个不同主视图、且任一入口的生效契约集合**不含**兄弟入口的契约名；
  `test_a_retired_body_no_longer_re_projects_over_the_native_authority` 固定无
  `LEGACY_STRUCTURE_KEY_OVERRIDE`；`test_entry_menus_actions_and_scoping_are_unchanged` 固定 menu→action→view
  绑定、`domain` 为空、`target=current`、分组面保持。只读代表面按入口分别编译契约，未出现跨入口字段或章节。
- **配置面（只读盘点）**：`LOWCODE_CONFIG_INVENTORY=1` 全量 **277** 条契约在册；本组三条
  （id 173／175／176）`status=published`、`active=true`、各自绑定本入口 action、**不钉 view**、
  `declared_context` 与 8.34.3 逐字一致。
- **设计器入口：对本组三入口按实现不注入**（见 8.34.8-③）。因此本批**未跑 G08 设计器闭环**，
  而是沿用 G07 已证的同一套低代码机制（机制输入未变，见 8.34.7 复用理由），**不把未跑写成通过**。
  **第二轮更正口径**：early-return 只证明"实现排除了临时模型"，**不等于已批准的产品边界**；
  合法配置的授权路径与能力缺口按 8.34.10-C 独立核查，本组三入口的合法配置路径是
  **角色导航面 ＋ 菜单持组**（已按此整改并通过运行态回执），**不是配置中心**。

### 8.34.7 分层验证结果

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | **PASS**：16 静态测 0 failed；`change_state=clean`、`changedPathCount=10`、`unmappedPathCount=10`。这两个计数**同义**：本批 10 条路径全部未命中前端增量测试自动推荐映射，因此回执置 `manualNonZeroL2Required=true`，需**人工选择非零 L2**；**不等于"没有未映射路径"，也不是门禁失败**。逐路径的覆盖检查见下方"路径覆盖表" |
| L2 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestContextWorkspaceNativeLowcode,/smart_construction_core:TestTeamLoanDeductionWorkspace,/smart_construction_core:TestCurrentAccountWorkspace,/smart_construction_core:TestCompanyProjectRefundWorkspace'` | **PASS**：**31 测 0 failed 0 error**（第一轮 19 测；第二轮补入角色面／原生权威契约／记录面语义等断言后为 31 测）。过程中一次中间失败为**测试书写缺陷**（Python 字面量写了 `公司&amp;项目退款`，XML 解析后实体已解码），改为 `公司&项目退款` 后复跑全绿 |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1` | **PASS**：exit 0，`[local.dev.demo.authority] PASS`。升级后模块 `state=installed`、`latest_version=17.0.0.168`，与**磁盘 manifest 版本相同**，容器内 `/mnt/source-addons` 三视图文件 md5 与宿主**一致** |
| L3-契约回读 | 运行中服务（HTTP `127.0.0.1:8070`，`sc_test_admin` 会话） | **PASS**：三视图 arch **含 `data-sc-anchor`**；三入口契约 `status=published`、`mode=native_semantic_surface`、`keys=['composition_mode','title']`。**不是只看服务健康**：契约与 arch 均由**运行进程**回读，排除「前端源码一致＝候选一致」的误判（另核对后端加载代码／模块升级状态，见上 L3） |
| L4-只读 | `FORM_LOWCODE_TOPIC=context_workspace FORM_LOWCODE_REPRESENTATIVE=1 make local.dev.form_lowcode.browser` | **PASS**：见 8.34.5，业务指纹未变、`restored=true` |
| L4-设计器 | `FORM_LOWCODE_TOPIC=context_workspace FORM_LOWCODE_DESIGNER=1 make local.dev.form_lowcode.browser` | **不适用（登记，不算通过）**：入口页无「表单设置」，见 8.34.8-③。该次运行在点击「更多操作」前即失败，**未产生任何配置写入**：最新变更集仍为 G07 的 397（`write=2026-09-18 11:17:57Z`），且**不存在**任何 G08 目标草稿 |

**复用理由**：本批未修改任何 L1/L2 输入之外的验证机制（P4 只新增一条只读 topic 登记，未改 runner、
未放松断言），也未修改其他组的契约／视图／测试；G07 的 L2／L3／L4 结果按其输入未变复用，未重跑。

#### 8.34.7.1 `unmappedPathCount=10` 的路径覆盖表（不扩规则、不凑归零）

下表逐条列出本批 10 条路径**由哪一项已执行的检查覆盖**。写法刻意保守：这里只登记"已经跑过、
输入包含该路径"的检查，不新增规则、不宣称计数应当归零。

| # | 路径 | 覆盖它的已执行检查 |
|---|---|---|
| 1 | `data/team_loan_deduction_workspace_contract.xml` | L2 `test_the_native_authority_contract_carries_the_declared_governance`（契约声明经原生权威通道仍随包下发）；L3 契约回读（`mode=native_semantic_surface`）；L4 `configuration_inventory` |
| 2 | `data/current_account_workspace_contract.xml` | 同上 |
| 3 | `data/company_project_refund_workspace_contract.xml` | 同上 |
| 4 | `tests/__init__.py` | L2 本身：模块未注册则该 tag 集合 0 测运行，而 0 测按治理规则即失败，故 L2 的 31 测通过即覆盖 |
| 5 | `tests/test_context_workspace_native_lowcode.py` | L2 四 tag 运行（该文件即被测体） |
| 6 | `views/support/team_loan_deduction_workspace_views.xml` | L2 `test_the_prompt_is_a_section_not_a_fact_position` ＋ `test_the_native_groups_keep_the_declared_section_titles_and_columns`；L3 运行态 `arch_db` 回读；L4 只读代表面（4 章节入口全部 resolve） |
| 7 | `views/support/current_account_workspace_views.xml` | 同上 |
| 8 | `views/support/company_project_refund_workspace_views.xml` | 同上 |
| 9 | `docs/ops/iterations/form_structure_consumption_stabilization_20260917.md` | L1 `baseline_iteration_execution_policy_guard`（`documents=3`，本记录在册） |
| 10 | `scripts/verify/local_dev_form_lowcode_scope.py` | L4 只读代表面本身（该脚本即被执行的登记体；0 测／未注册 topic 会直接抛错） |

**结论口径**：`unmappedPathCount` 只说明"这些路径没有自动推荐映射"，因此本批的覆盖是由上表这些
**已执行**的 L1／L2／L3／L4 检查承担的；**没有为该计数归零而扩造规则**。

### 8.34.8 未覆盖项与剩余阻断（如实登记，不造数据）

1. **记录态（record surface）——第一轮推理已更正：临时模型"可以有记录"且存在合法编辑态**。
   第一轮把结论写成"三个模型均为 `TransientModel`，**不存在**持久记录面"，把
   **"模型是临时模型"** 直接当成 **"记录面不可能存在"**，这一步推理是错的，本轮更正：
   `TransientModel` 照样落库成行、照样可读可编辑，只是会被回收，**它不等于没有记录面**。
   更正后的可核对事实：
   - 运行态实测三个模型**确有可读样本行**（875 `domain_rows=15`、877 `6`、878 `5`，
     只读盘点报告 `sample_state.state=available`），第一轮写的 `sample_state=empty_action_domain`
     是当时域内恰为空时的一次快照，被误当成结构性事实；
   - **合法编辑态同样存在并被观测到**：派发上下文保存后，页面进入
     `/f/sc.team.loan.deduction.workspace/<id>?menu_id=697&action_id=875` 的记录面（见 8.34.10-A/-B 回执）。
   因此本组**不再以"没有记录面"为理由**免除 `record_surface`：本组仍未跑"持久业务记录"的代表面，
   但理由是**本组不为验收制造业务事实**（派发上下文不是业务记录，工资／发放／退款单据一律未造），
   **不是**"模型临时所以记录面不存在"。L2 保留「模型 transient ＋ 该模型无模型级契约」这条**结构断言**，
   但它只固定"工作台自身不持有业务事实"，**不再被用来推断记录面不存在**。
   **未为补样本造任何工资／发放／退款业务数据。**
2. **编辑态动作可达性：治理函数已实测；端到端编辑面仍无合法样本**：表头对象按钮（875 的 3 个、
   877 的 6 个、878 的 5 个）在契约中**已授予**（`actionContract.actionRuleList` 中 `allowed=true`、
   `enabled=true`、`source=native_form_header`，edit／readonly 在位），但在 **create 档位**由平台治理
   规则静态隐藏（`contract_governance_create_profile.py` 给出 `reason_code=CREATE_PROFILE_REQUIRES_RECORD`）。
   该规则只在 `head.interaction_mode == 'wizard'` 时豁免；`interaction_mode` 仅在
   「`action.target == 'new'` 且模型为 transient」时为 `wizard`（`page_assembler.py`），而本组三条
   action 的 `target` 均为 `current`（L2 固定），故运行态取值为 **`page`**。
   **补充执行核对（2026-09-19，受管 local.dev 只读）**：在 `sc_dev_demo`／`sc_test_admin` 下直接执行
   生产模块内的纯治理函数 `mark_record_dependent_native_buttons_hidden_on_create`，对
   `interaction_mode ∈ {page, form, wizard}` × `{create, edit}` 六格逐一取值：`page` 与既有测试已覆盖的
   `form` **输出逐字节相同**（create 档位 `hidden=true`＋`reason_code=CREATE_PROFILE_REQUIRES_RECORD`＋
   `visible_profiles` 由 `[create,edit,readonly]` 收窄为 `[edit,readonly]`＋`requires_record=true`；
   edit 档位不改写，`visible_profiles` 保持三档）；`wizard` 两档均不隐藏。故「`page` 走隐藏分支」
   由**代码推断**升级为**已执行观测**，且该规则**对 edit 档位整体不生效**
   （`is_create_render_profile` 由 `record_id` 决定，`record_id=42` 时返回 `False`）。
   同批回读：模块 `state=installed`、`latest_version=installed_version=17.0.0.168`，容器内
   `contract_governance_create_profile.py`／`page_assembler.py` 的 md5 与宿主**一致**，
   即被执行的正是**运行态加载的同一份代码**。
   第一轮把端到端 edit 档位渲染记为"无合法持久记录可绑定"；**该理由本轮已更正**——记录面存在，
   而且本组自己就会产生合法的临时上下文行，端到端 edit 档位**是可观测的**。第二轮已按真实用户路径
   观测到：保存办理上下文后进入记录面（`/f/…/<id>?menu_id=697&action_id=875`），表头 3／6／5 个
   派发载体**全部出现**（见 8.34.10-A）。因此该条从"未覆盖"改为**已覆盖（第二轮）**。
   **但载体在 create 档位被静态隐藏这件事本身不是本批引入的**：`interaction_mode` 与 `target` 均不由
   本批改动，退役体声明与 `composition_mode` 也不在该治理规则的输入里；本批退役前后该结果一致。
3. **设计器／表单设置入口对本组按设计不注入**：`page_assembler._inject_current_form_settings_action`
   对 transient 模型直接返回（`if not model_rec or model_rec.transient: return`），与契约
   `composition_mode` 无关；因此 875／877／878 在**退役前后都没有**入口级设计器，本组也不存在
   可跑的「预览→发布→刷新→回滚」闭环。**报告为按设计边界（登记项），不记为产品缺陷，也不冒充已验证。**
   由此，`更多操作` 表头收纳（依赖同一 `buttons` 组动作）在本组同样不出现。
   **（第三轮更正，2026-09-19）以上这条"不存在配置闭环"只对"每表单字段策略编辑器"这一项能力成立，
   不作为本组的整体结论**：产品里有两个都叫"表单配置"的能力，另一个是**租户低代码变更集**
   （拥有页面契约的标签／显隐／排序），它在 878 上**确有**可跑闭环，并已在第三轮逐步验证
   （stage → preview → publish → runtime → rollback，见 8.34.11-③）。两项能力必须分开读：
   前者对本组 transient 工作台**按设计关闭**（登记为**能力限制**），后者对本组**可用且已验**。
   因此本条的"设计器不注入"**不得**再被引用为"三个工作台没有合法表单配置路径"。
   **首次偏差与影响面（只读盘点，2026-09-19）**：首次偏差点即该函数的 early-return
   （`page_assembler.py`：`model_rec = self.su_env["ir.model"].search([("model", "=", model)], limit=1)`；
   `if not model_rec or model_rec.transient: return`），它位于管理员与配置 ACL 检查**之后**、
   动作注入**之前**。全量 **277** 条在册契约中目标模型为 transient 的共 **4** 条：
   本组 **173／175／176**（875／877／878，`status=published`）＋**既有非本批 180**
   （`sc.product.system.settings`，action **887**，`status=published`）。
   **口径统一（第一轮两句话互相冲突，本轮按实际变更关系收敛）**：第一轮同时写了
   "875／877／878 退役前后都不支持设计器"与"G08 把受影响入口由 1 条扩到 4 条"，前者说的是
   **存量实现边界**、后者容易被读成**本批引入**，必须区分"本轮**发现／登记**"与"本轮**引入**"：
   - **不是本轮引入**：该 early-return 在本批之前就存在，`model.transient` 的判据不由本批改动；
   - **不是本轮扩大适用范围**：4 条 transient 目标契约（本组 173／175／176 ＋ 既有 180／887）
     **在本批之前就都已存在**——`git show 26d254ad:addons/smart_construction_core/data/
     team_loan_deduction_workspace_contract.xml`（及另两份）证明三条契约在基线上已注册且
     `model` 字段已是 transient 工作台，本批只改 `composition_mode` 与退役体声明，
     **二者都不是该 early-return 的输入**；
   - **本轮确实变化的是"登记面"**：这 3 条入口的边界第一次被本组**明确登记并核对到运行态**，
     于是**在册登记**从 1 条（180／887）扩到 4 条。这是**发现面的扩大，不是影响面的扩大**。
   本批**未把它混入入口迁移**，故偏差范围可界定；结论仍保留"迁移未新增回归"，但**不得据此宣布入口可用**。
4. **未执行项（保持未执行）**：最终 Quick、推送、建 PR、合并、部署、冻结、G09 启动、六组副本候选迁移、
   `sync_demo`／fixture reset／发布快照、历史工作树清理。
5. **写入核对（只读回读）**：受保护草稿 163／190／192／194／233／267／274／276 的 `write_date`
   全部停留在 2026-09-17，本轮未被触碰；G07 复核草稿 **397 保留**（`ready`、未发布）；本轮设计器尝试
   **零配置写入**（最新变更集仍为 397，无 G08 目标草稿）；运行现场（odoo 8070／vite 5174）保持可用。
   第二轮复核期间同样**零配置写入、零业务单据写入**：只产生本组合法的**临时派发上下文行**
   （875 15 行／877 6 行／878 5 行，含前几轮累积），四类业务单据 `created_last_6h=0`（见 8.34.10-A）。
   第三轮口径统一为：**创建／修改了临时上下文记录，未持久化目标业务单据、未修改配置**；"12 小时零新增"
   只作旁证，不替代路径前后核对。第三轮的写入核对见 8.34.11-⑤。

### 8.34.10 集中产品复核整改（第二轮，2026-09-19）

**复核结论（接受）**：结构迁移基本成立，但 G08 作为"办理工作台"的**用户路径尚未闭合**——
三个桌面入口只显示"保存草稿"、看不到借款／扣款／往来／退款入口，且"办理提示"为空占位。
复核**不放行冻结**。本轮按 **A／B／C／D** 四包连续整改，结果如下。

#### 8.34.10-A 办理路径闭合（A 包）

**首次偏差（本轮定位，四层叠加，缺一层都不闭合）**：
1. **载体在 create 档位被静态隐藏**：`contract_governance_create_profile.py` 对 record-dependent 表头按钮
   给出 `visible=false`＋`reason_code=CREATE_PROFILE_REQUIRES_RECORD`。**这是 G06／G07 就存在的既有行为，
   不是本批引入**，但它决定了本组的正确路径只能是"先保存临时上下文，载体才出现"。
2. **入口与派发目标分属不同角色面**：工作台入口菜单与它要派发的目标单据菜单**不在同一角色导航面**，
   于是**没有任何主体同时拥有"打开工作台"与"打开目标单据"两类路由**——办理路径断在入口或断在派发。
3. **治理声明走不到页面**（见 8.34.10-B 的传输根因），页面因此退回通用 create 文案。
4. **派发返回的 window action 没和菜单配对**：客户端要求 action 与"menu↔action"配对，缺配对即
   打不开（历史现象是 `403 PERMISSION_DENIED 用户无权访问菜单 …`）。

**整改（只走既有授权路径，不放开临时模型按钮，不新增机制）**：
- `core_extension_policy_maps.py`：`project_member` 按菜单**自身声明的持组**补 875 入口 ＋ 3 条派发目标路由
  （`menu_sc_contractor_project_borrow`／`menu_sc_deduction_bill`／`menu_sc_finance_project_counterparty_position`）；
  `finance` 补 877／878 入口菜单。路由仍由**当前用户原生菜单可见性**门控生成，财务中心容器依旧留在
  `project_member` 的导航 blocklist 中。**未改 ACL、未放开系统设置 887、未对 TransientModel 按钮做通配放开。**
- **回退记录（如实登记）**：整改过程中曾试过把 875 ＋ contextual 路由授给 `pm`，产生**客户端打不开的路由**
  （`403 PERMISSION_DENIED 用户无权访问菜单 承包人借项目款`），已**整体回退**。原因是 `demo_pm`／
  `sc_project_user` 原生看不到菜单 553／563／372；只有**原生同时可见 697 与三张目标单据**的项目成员主体
  （`demo_pm`／`demo_role_project_user`／`demo_role_project_manager`）能生成成对路由。
- 新增 `sc.context.workspace.entry.authority`：派发返回前把 window action 钉到**当前主体路由权威中确实存在**
  的那个 `menu_id`（`_sc_route_authority()` 取自与客户端同一份 route authority 契约），并把 `date`／`datetime`
  上下文转 ISO 字符串再交给客户端。**查不到路由即业务文案 fail-closed**，不再把用户丢进导航拒绝页。
  角色／发布配置改变时载体随之改变，**无需改代码**。

**验证（真实浏览器路径；只走到目标"未保存表单"为止，未执行任何实际借款／退款／发放）**：

| 入口 | 保存上下文后出现的派发载体 | 载体落点（正式单据列表） | 点"新建"后的未保存表单与承接 |
|---|---|---|---|
| 875 班组借/扣款登记（`demo_role_project_manager`） | 3 个：登记借款／登记扣款／查看借扣款台账 | `/a/804?menu_id=553` | `/f/sc.financing.loan/new`：`project_id=德阳智能制造产教融合项目`、`partner_id=德阳某某周转材料租赁有限公司（示例）`、`document_date=2026-09-19`、`loan_type=借款申请`、`direction=借入资金`、`purpose=承包人借项目款`；金额空、单据号仍为"新建" |
| 877 往来款登记（`demo_role_finance`） | 6 个：项目借/还公司款、承包人借/还项目款、账户间调拨、查看往来台账 | `/a/805?menu_id=554` | `/f/sc.financing.loan/new`：同上，`purpose=项目借公司款登记`，项目／往来单位／日期均承接 |
| 878 公司&项目退款（`demo_role_finance`） | 5 个：扣款实缴退回／投标保证金退回／合同保证金退回／自筹退回／查看关联台账 | `/a/800?menu_id=565` | `/f/sc.expense.claim/new`：`claim_type=扣款退回`、`expense_type=扣款实缴退回`、`summary=扣款实缴退回`，项目／往来单位／日期均承接 |

- **停在未保存表单**：三轮都停在 `/f/<model>/new`，单据号仍是"新建"、金额为空，**未执行任何业务动作**；
  `toast=[]`（无拒绝提示）。
- **纯函数六格验证不再被当作这条路径的替代**：第一轮的 `interaction_mode × render_profile` 六格只证明
  治理函数取值，**不证明用户路径存在**；本轮以 875／877／878 三段端到端回执取代它作为闭合证据。
- **无合法样本一律不造业务数据**：本组**不为截图创建任何工资或发放业务数据**。写入核对（只读回读，
  UTC 近 6 小时窗口）：`sc.financing.loan` 合计 1／新增 0；`sc.expense.claim` 合计 3／新增 0；
  `sc.fund.account.operation` 合计 2／新增 0；`sc.self.funding.registration` 合计 0／新增 0。
  只产生本组合法的**临时上下文行**。

#### 8.34.10-B 临时工作台产品语义（B 包）

1. **"模型临时 ⇒ 记录面不可能存在"的推理已更正**（逐条改写见 8.34.8-①）。`TransientModel` 可以落库、
   有合法编辑态、只是会被回收；本轮已按真实路径观测到记录面（见上表）。
2. **"保存草稿"根因与三层整改**：根因是**原生权威路径把已声明的表单治理整段跳过**——
   `ui_contract_v2` 在 `native_structure` 时把 `governed` 置 `None`（避免第二个结构所有者，这个判断本身是对的），
   但**语义声明**也被一起丢了；随后 `unified_page_contract_v2_assembler` 在原生表单投影里又用
   **整键覆盖** `governance`，把已经搬进 `runtimeContract.governance` 的声明再覆盖掉。三层修复：
   - 机制层：新增 `native_authority_safe` 登记位与 `apply_native_authority_domain_overrides()`，
     **只放行"只声明语义、不改结构"的 override**；改写结构的 override（如 `project_form`）仍在门外。
   - 传输层：`_assemble_ui_contract` 把 `form_governance` 写进 `runtimeContract.governance`，
     `_assemble_native_form_projection` 改为**合并**而不是覆盖。
   - 记录面：无业务表单策略的非 create 路径此前**在治理前直接 return**，本轮在该路径也应用语义声明。
   - 声明层：`context_workspace_form` 逐入口声明 `primary_action_label=记录办理上下文` ＋ 协作面板文案；
     **不改通用 create 默认值**，不波及其他模型。
   实测（真实契约回读，非只看健康）：create 面与记录面**都**携带
   `runtimeContract.governance.form_governance`（`surface=context_workspace`、
   `create_flow_mode=transient_dispatch`），页面按钮均为 **`记录办理上下文`**（不再是"保存草稿"，记录面也不再是"保存修改"）。
3. **协作日志与保存后提示**：两个档位都显示声明文案
   **"办理上下文只用于本次派发，不长期保留；沟通、备注与附件请在打开的正式单据中登记。"**
   ——不再用通用 create 文案"保存草稿或提交生成单据后，可记录沟通…"，也不再在记录面暗示这份上下文会被长期保留。
   前端只认契约声明（`isDispatchContextGovernance()` 认 `create_flow_mode=transient_dispatch`），**不硬编码模型名**。
4. **空的办理提示不占普通事实字段位置**：`processing_advisory` 已从"办理上下文"**事实分组**移出，
   独立为 `办理提示` 组（`name="…_processing_advisory"` ＋ `data-sc-anchor`、`col=1`、字段 `nolabel="1"`、
   `invisible="not processing_advisory"`）；运行态 `arch_db` 三份视图均已回读到该 `invisible`。
   **如实登记一处未实测**：该字段 compute **恒非空**（有建议则列建议，否则输出"办理上下文已完善"），
   因此 `invisible` 是**防御性边界**，本组数据**无法**触发"空值隐藏"的真实渲染；本条不写成"空值渲染已实测"。
5. **L4 只读代表面（重跑）**：三入口各一个 create 面、**5 字段／4 章节**
   （办理上下文／办理说明／办理提示／协作记录），四个章节入口 `resolved=true`、`visible=true`，
   四类 findings 全空，双视口 `section_navigation_press=not_applicable/track_does_not_overflow`。

#### 8.34.10-C 低代码边界（C 包）

> **（第三轮更正／取代，2026-09-19）本轮 C 包答错了问题。** 复核指出：本包结论
> "合法配置生效路径 = 角色导航面 ＋ 菜单自身持组"描述的是**哪些角色能打开哪些入口**，
> 属于**访问控制**；原任务问的是"**标签、显隐、排序**等合法表单配置如何生效"，属于**低代码配置能力**。
> 两者不能互相替代。本包因此**不在第三轮被引用为 C 包已通过**；第三轮的 C 包由
> **8.34.11-③**（租户低代码变更集在 878 的 stage → preview → publish → runtime → rollback 闭环，
> 含三条拒绝面与授权作用域）重新回答。以下内容仅作**授权面事实**留存。

- **首次偏差**：`ui_form_field_policy.py` 与 `handlers/form_field_configuration.py` 对 transient 模型直接拒绝，
  `page_assembler._inject_current_form_settings_action` 同样 early-return。**该 early-return 只能证明
  "实现排除了临时模型"，不能证明这是已批准的产品边界。**
- **授权路径核查（结论：配置中心不是本组的授权路径）**：
  `scripts/verify/baselines/formal_business_product_menu_policy_v1.json`
  （schema `formal_business_product_menu_policy.v1` 锁定，sha256 `80b5c7d5bbfe69dc5bd26588cbea4f40dbed1a205f9831d890bb8394e8a1ad24`，
  两个产品各 89 能力）中，三个工作台入口**在册**（`enabled=true`／`release_state=released`／
  `access_level=public`／`entry_intent=handling`），但 **11 条派发载体菜单中只有 `menu_sc_deduction_bill`（798）在册**，
  其余**不在册**；`release_operator.py` 的 `set_page_enabled`／`update_page_policy`／`promote`／`freeze`／
  `sync_policy`／`approve`／`rollback` **只能对已在册页面切换 `enabled`／`release_state`／`access_level`**，
  **不能新增页面或路由**。
- **因此本组三个正式工作台的合法配置生效路径 = 角色导航面 ＋ 菜单自身持组**（本轮即按此整改，见 8.34.10-A），
  **不是配置中心**。按"合法配置可生效"的原则，本组三入口现在**确实遵守**该原则：角色／发布范围一改，
  入口与载体随路由权威改变，无需改代码（`_sc_pin_entry_authority` 即读该权威）。
- **能力缺口登记**：对"用配置中心为这三个工作台开／关派发载体、调整发布范围"这一诉求，现状是
  **能力缺口**（在册策略不含这 11 条载体，且发布操作符不能新增页面）。**该缺口不由 G08 引入**，
  本组**未把它悄悄混入入口迁移**，也**未顺手开放系统设置 887**。
- **未用 G07 闭环代替本组三入口验证**：G07 的设计器闭环只复用其**机制**，本组三入口的配置面结论
  来自本节的独立核查与 8.34.10-A 的运行态回执。

#### 8.34.10-D 验证口径修正（D 包）

- `unmappedPathCount=10` 的含义与逐路径覆盖表：纠正为"10 条路径未命中增量测试推荐映射，
  需人工选择非零 L2"，**不是"没有未映射路径"，也不自动等于门禁失败**——见 8.34.7 与 8.34.7.1。
- **三份行业原生视图归属由 P0 更正为 P1**：不因载体是 XML 视图就归 P0 平台内核——见 8.34.3。
- **"发现"与"引入"口径统一**：见 8.34.8-③。保留"迁移未新增回归"，但**不得据此宣布入口可用**。

#### 8.34.10-E 运行态候选一致性（按更正后的证据标准核对）

复核指出"Vite 应用源码一致只能证明前端这一侧"，接受该纠正。本轮按**两侧＋升级状态＋最终契约**核对：

| 维度 | 证据 | 结论 |
|---|---|---|
| 前端 | vite dev（`5174`）直接服务工作树源码 | 只证明前端一侧，**不单独作为候选一致依据** |
| 后端加载代码 | addons 以 bind mount（`…/sce-backend-odoo/addons → /mnt/source-addons`，rw）挂入容器；宿主与容器内逐文件 `sha256` 一致（`unified_page_contract_v2_assembler.py`、`ui_contract_v2.py`、`contract_governance_overrides.py`、`core_extension_policy_maps.py`、三份 `views/support/*_workspace_views.xml`） | 运行进程加载的**就是本工作树这份代码** |
| 模块升级状态 | `smart_construction_core` `state=installed`、`latest_version=17.0.0.168`（`write_date` 2026-09-18 18:56:21）；三份视图 `arch_db` 含 `invisible="not processing_advisory"` | 视图改动已随升级落入库内，**不是只改了磁盘** |
| 最终契约 | HTTP `/api/v1/intent` 的 `ui.contract.v2` **响应体**（create 面与记录面）均含 `runtimeContract.governance.form_governance`，并携带全部派发载体 | 以**最终契约**为准，**不以"服务长驻健康"认定候选一致** |

### 8.34.11 集中产品复核整改（第三轮，2026-09-19）

**复核结论（接受，本轮仍不放行冻结）**：办理路径有进展——"记录办理上下文"已取代"保存草稿"，
记录 103 出现五个办理／查询按钮（编辑态确实存在），临时上下文保留期限提示已显示；但**四包不能
全部关闭**：①「办理提示」仍作为独立正文章节与导航项出现；②记录副标题和页签仍是
`sc.company.project.refund.workspace,103`；③上一轮 C 包答的是"哪些角色能打开哪些入口"，**没有**
回答"标签、显隐、排序等合法表单配置如何生效"；④本批已超出纯 XML 迁移，需对新增共享机制与授权
变化做定向复核。本轮按四项集中整改，结果如下。

#### 8.34.11-① 辅助信息层级：办理提示是辅助反馈，不是业务章节

**首次偏差（本轮定位）**：「办理提示」在前两轮是一个带 `data-sc-anchor` 的 native `group`，
因此被章节导航当成本单元的**正文章节**；"协作记录"导航项本身也只指向一段"请去正式单据协作"的
说明，既有标题又无功能。

**整改（复用既有组件，不另造反馈机制）**：
- 三份 `views/support/*_workspace_views.xml` 统一收形，`<sheet>` 现为四段：使用说明
  （`div.alert.alert-info[role=status]`）→ `办理上下文` group（带 `data-sc-anchor`）→
  `办理说明` group → 提交／动作区。
- 「办理提示」**删除 group 与它的 `data-sc-anchor`**，改为非 group 的内联反馈：
  `div.alert.alert-info[role=status] invisible="not processing_advisory"` 内含
  `field processing_advisory readonly=1 nolabel=1`。
- 渲染链（既有机制，未改）：`NativeFormTreeRenderer.vue` 对非 group 节点走
  `resolveNativeTextPresentation`，`kind==='callout'` → `ScInlineState`
  （`native-form-feedback`）；`data-sc-anchor` **只在 group 上发出**，故该提示**不可能**再成为
  章节或导航项。
- **空提示不占位置**：`invisible="not processing_advisory"` 使无内容时不渲染；有内容时按既有
  通用提示规范表达，不再占用普通事实字段位。
- **协作说明并入使用说明**：删除 `_CONTEXT_WORKSPACE_COLLABORATION_MESSAGE` 与"协作记录"章节，
  该说明并入工作台使用说明（同一段 alert）。**正式单据的协作能力不变**：`suppressCollaboration`
  只在派发上下文入口置位（`ContractFormDriverHost` 单点绑定），`ContractFormPage.vue` 的
  `dispatchContextCollaboration` 只在 `transient_dispatch` 治理下生效。
- P4 登记口径同步：`scripts/verify/local_dev_form_lowcode_scope.py` 的 `context_workspace` 注释由
  "三个锚定 group（办理上下文／办理说明／办理提示）"改为"两个锚定 group（办理上下文／办理说明）"，
  并写明提示是**非章节** feedback，且 transient 依旧"有记录、有合法编辑态"。

**测试**：`test_the_prompt_is_feedback_not_a_section`（原 `..._a_fact_position` 已改写为
"不得是章节"）、`test_the_workbench_usage_note_owns_the_collaboration_note`、
`test_the_advisory_fact_stays_readonly`。

#### 8.34.11-② 工作台可读身份与操作说明

**首次偏差（本轮定位）**：记录副标题／页签显示 `模型,id`。根因是 Odoo 17 的 `display_name`
由 `_rec_name` 决定，**且不经过** `name_get()`——只重写 `name_get` 改变不了页签／副标题／面包屑。

**整改**：
- **由 P1 提供可读名，前端不拼接模型特判**：`models/support/context_workspace_entry_authority.py`
  新增 `name`（compute `_compute_sc_context_name`）、`_rec_name = "name"`、
  `_sc_readable_context_name()`、`_sc_join_context_name(project, counterparty)`；三个工作台模型
  各自 override `_sc_readable_context_name()` → `self._sc_join_context_name(self.project_id,
  self.partner_id)`；`name_get()` 仅作兼容保留。页签、副标题与面包屑因此走**既有显示名称机制**。
- **新建页操作说明**：使用说明段明确"先记录办理上下文，再选择办理事项；金额、账户和明细在目标
  正式单据填写"，用户不再需要靠试点"记录办理上下文"猜出下一步。

**测试**：`test_the_record_surface_reads_a_readable_name`。

#### 8.34.11-③ 重做 C 包：表单配置与路由授权分开验收

**复核意见（接受）**：上一轮 C 包的证据是"角色 → 入口"的授权面，属于**访问控制**；它没有回答原
任务的"**标签、显隐、排序**等合法表单配置如何生效"，而后者属于**低代码配置能力**。两者不能互相
替代。本轮按此重做。

**闭环（878 `公司&项目退款`，走既有受管变更集路径，逐步读"交付页契约本身"）**：
`stage → preview → publish → runtime → rollback`，每一步读的都是原生渲染器实际消费的那份
`ui.contract.v2`：

> **第四轮修正口径（本次补正，不重跑）**：下表五步由 `TestContextWorkspaceNativeLowcode`
> **直接调用 handler** 完成，运行在**测试事务内**，应写「**测试事务内执行，未持久化配置变更**」。
> 它证明的是合成、约束与回滚**机制**，**不等同**管理员在**产品界面**完成配置；产品界面路径见
> 8.34.12-③。

| 步骤 | 观测 |
|---|---|
| preview | 标签改写生效（`办理说明（受管表单配置）`）；可选上下文事实被合法隐藏（`visible=false`）；`办理上下文` group 的**显式 order permutation** 被遵守（子节点顺序反转后生效） |
| 约束保持 | 必填上下文事实 `project_id` 仍 `required`；动作载体集合与基线**逐条相同**（配置不得增删派发按钮） |
| publish | `published_content_verified=true`、`runtime_verified=true`；运行态交付契约带上已发布配置 |
| 隔离 | 邻居 875／877 的契约身份**逐字节不变** |
| rollback | 交付契约回到**基线身份**；邻居仍不变 |

**拒绝面（同一授权路径的边界）**：隐藏必填事实 → `CONFIG_REQUIRED_FIELD_HIDDEN`；放宽 readonly
约束 → `CONFIG_BUSINESS_CONSTRAINT_RELAXED`；指向失效目标 → `CONFIG_TARGET_STALE`。三者均被
拒绝并 discard，说明"配置被接受"不等于"配置可以越过业务规则"。

**授权与作用域**：设计权威是**变更集授权组 且 入口面本身**。仅有
`smart_core.group_smart_core_business_config_admin` 而无入口面的 principal，解析该入口原生视图即
raise `unavailable`（入口面必须被解析，不能被假定）；产品已有的
`smart_construction_core.group_sc_cap_business_config_admin` 本身已含这些入口的能力组，故按作用域
的设计者合法可达 878 页面与 preview。**未开放系统设置 887**。

**未闭合能力限制（明确列名登记，不改名通过）**：产品里有两个都叫"表单配置"的能力。本轮闭合的是
**租户低代码变更集**（拥有页面契约，见上表）；另一个是**每表单字段策略编辑器**——其"表单设置"
入口注入到页面中，并对 transient 工作台**在设计上关闭**：入口不注入、`FormFieldPolicySetHandler`
与 `FormCustomFieldCreateHandler` 均拒绝（"临时模型"）。本轮**只在 878 上闭合变更集配置路径**，
另两个入口**只验证隔离**；**每表单字段策略编辑器对三个 transient 工作台不可用，登记为能力限制**，
不写作"合法配置路径已通过"。

**测试**：`test_one_workbench_closes_the_authorized_form_configuration_loop`、
`test_the_configuration_path_refuses_to_relax_a_workbench_constraint`、
`test_the_design_authority_is_bounded_by_the_entry_surface`、
`test_a_transient_workbench_stays_out_of_the_per_form_field_policy_editor`。

#### 8.34.11-④ 本轮新增共享机制与授权变化的定向复核

**(a) `native_authority_safe` 与 governance 合并只允许预期语义**：注册表里声明
`native_authority_safe` 的条目**恰好只有** `smart_construction_core.context_workspace_form`；
该安全通道只允许**新增** `form_governance` 声明，结构键
（`sections`／`fields`／`columns`／`field_slots`／`layout`／`header_buttons`／`actions`／
`button_box`／`view_orchestration`／`containerTree`／`nodes`）与 `fields`／`views` 的输入输出
**逐字节不变**——**不能恢复结构双权威，也不能放宽约束**。运行态另有一条：交付契约同时携带投影的
`view_orchestration` 与声明的 `form_governance`，但 `formStructureAuthority` 仍是
`native_authority`、`structureDiagnostics=[]`，**结构唯一属主未变**。
测试：`test_the_native_authority_pass_runs_only_declared_semantic_overrides`、
`test_the_runtime_governance_merge_keeps_one_structure_owner`。

**(b) 派发 authority 绑定真实可访问的目标菜单**：候选只从主体**原生可见**菜单生成
（`_sc_entry_menu_ids()`）；**多候选**时 `_sc_entry_menu_id(...)` 抛 `UserError`（"多个可打开
入口"）fail-closed，**缺失**返 0（载体不可派发），被 `context_requirements.required_query`
限定的路由不参与派发，**恰好一个**候选才 pin，且 pin 出的菜单必须是当前主体路由面上的那一条。
测试：`test_a_carrier_fails_closed_when_the_authority_offers_several_routes`、
`test_every_returned_carrier_is_pinned_to_the_operators_route_menu`。

**(c) 角色导航授权差异（ACL 未改 ≠ 访问范围未扩大）**：本批**未改任何 ACL**，扩大的是**角色导航
面声明**（`core_extension_policy_maps.py` 的 `ROLE_SURFACE_OVERRIDES`）：

| 主体 | 新增可见入口 | 新增可见路由 |
|---|---|---|
| finance（财务中心） | 877 往来款登记（menu 699）、878 公司&项目退款（menu 700） | 无（11 条派发目标本就在财务导航面） |
| project_member（项目中心） | 875 班组借/扣款登记（menu 697） | 804 承包人借项目款（menu 553）、798 扣款单（menu 563）、714 项目往来台账（menu 372） |

**拒绝反例（冻结轮按实际主体重测后更正，逐条标主体定义，见 8.34.14-⑤）**：finance 导航面
**不含** 875，且 finance 主体对 875 模型的 `create` 被 ACL 拒绝；**只持项目只读、不持财务持组**
的主体拿不到 875 入口菜单、也拿不到载体路由，877／878 建档被 ACL 拒绝；**只持
`group_sc_cap_project_user`**（项目经办、不持财务持组）的主体在 875 上三个载体均以受管业务消息
fail-closed（非 `NAVIGATION_AUTHORITY_DENIED`），877／878 建档即 `AccessError`。
**同时持财务持组的项目主体不是拒绝反例**：fixture `demo_role_project_user`
（project_user＋project_read＋finance_read＋finance_user）实测**拿到**875 的三条载体路由
（553／563／372，`CONTEXTUAL_ROUTE`）且 877／878 建档被 ACL **允许**；其 875 载体在上轮探针中
fail-closed 的原因是**模型侧项目经办守卫**，与路由授权无关。路由由"当前用户原生菜单可见性"
门控生成，因此上述声明**不会**凭空造出主体原本没有的可见性。**登记为开放偏差**：finance 与 875
的持组不一致（875 菜单与模型 ACL 都声明项目中心），本轮不为对齐而把 875 塞进财务导航面。
测试：`test_the_finance_role_surface_grants_the_two_finance_workbenches`、
`test_the_project_role_surface_grants_the_team_loan_workbench`、
`test_a_principal_outside_the_role_surface_is_refused`。

**(d) 14 个派发载体按目标类型覆盖表**（浏览器只走三个代表跳转，其余由定向契约／权限测试覆盖，
不逐按钮重复浏览器旅程）：

| 入口 | 载体数 | fact 目标 | projection 目标 |
|---|---|---|---|
| 875 班组借/扣款登记 | 3（2 fact ＋ 1 projection） | `sc.financing.loan`、`sc.expense.claim` | `sc.finance.project.counterparty.position` |
| 877 往来款登记 | 6（5 fact ＋ 1 projection） | `sc.financing.loan`、`sc.expense.claim`、`sc.fund.account.operation` | 同上 |
| 878 公司&项目退款 | 5（4 fact ＋ 1 projection） | `sc.expense.claim`、`sc.self.funding.registration` | 同上 |
| 合计 | **14（11 fact ＋ 3 projection）** | | |

每个目标都断言：非 transient；属于该入口声明的 `ENTRY_FACT_MODELS`，或正是
`PROJECTION_MODEL`。浏览器走过的三个代表为 875 `action_register_loan`、877
`action_project_borrow_company`、878 `action_deduction_refund`。测试：
`test_every_dispatch_carrier_is_covered_by_its_target_type`。

#### 8.34.11-⑤ 写入口径修正

本批写入口径统一改为：**创建／修改了临时上下文记录，未持久化目标业务单据、未修改配置**。
"12 小时零新增"只能作为**旁证**，不能替代本次路径的前后核对。为此本轮在写入前后都做了核对：

- 受保护草稿（163／190／192／194／233／267／274／276）与 G07 复核草稿 **397 保留**、未被触碰；
  变更集清单在 2026-09-15／16 之前即静止，**本轮无新增配置草稿**（测试与只读代表面均在事务内或
  只读模式下运行）。
- 四类目标业务单据（借款／扣款／往来／退款）**零新增**；临时上下文记录在记录面以"合法编辑态"存在
  （记录 103 的五个办理／查询按钮），但**未执行任何借款、扣款、往来或退款动作**——操作停在
  **目标未保存表单**。

#### 8.34.11-⑥ 本轮分层验证结果

- **L1** `make ci.local.iteration`：**PASS**（16 静态测 0 failed、`change_state=dirty`、
  `changedPathCount=28`、`unmappedPathCount=24`、`manualNonZeroL2Required=true`、`coverage=L1_only`、
  `receipt=none`）；未映射路径的逐条覆盖见 8.34.11-⑥b。
- **L2** 定向类 `TestContextWorkspaceNativeLowcode` 全类（含本轮 5 项 C 包测试）：**PASS**，
  `0 failed, 0 error(s) of 35 tests`；四 tag 整组（`TestContextWorkspaceNativeLowcode` ＋
  `TestTeamLoanDeductionWorkspace` ＋ `TestCurrentAccountWorkspace` ＋
  `TestCompanyProjectRefundWorkspace`）：**PASS**，`0 failed, 0 error(s) of 41 tests`。
- **L3** 模块 `smart_construction_core` `installed`、`latest_version=17.0.0.168`；本轮改动的视图
  XML 经 `local.dev.upgrade` 落入库内（服务重启后加载新注册表）。
- **L4** 只读代表面 `FORM_LOWCODE_TOPIC=context_workspace FORM_LOWCODE_REPRESENTATIVE=1`：
  **PASS**，报告 `artifacts/lowcode-form-loop/browser/representative-report-context_workspace.json`
  `ok=true`、`restored=true`、`browser_errors=[]`、`representative_uncovered=[]`。

**运行态事实（可核对）**：`sc.team.loan.deduction.workspace`／`sc.current.account.workspace`／
`sc.company.project.refund.workspace` 当前 `search_count=0`——临时上下文行**已被回收**，这正好印证
8.34.11-② 与 8.34.8-① 的口径：`TransientModel` 有数据库记录、也有合法编辑态，但**会被回收**，
"临时模型"既不等于"没有记录面"，也不等于"长期保存"。变更集清单最大 `create_date` 为
`2026-09-18 11:17:57`（早于本轮全部执行），**本轮零新增变更集**。

**首次 L4 尝试的一次偏差（如实登记）**：升级后紧接着的第一次 L4 返回 exit 1
（`form lowcode journey changed runtime identity or scoped business data`）。同一环境下**手工重放**
（取 scope 指纹 → 跑同一 `node` 旅程 → 再取指纹）**无任何字段差异**，紧接其后的第二次 L4 亦
**PASS**。

> **第四轮修正口径（本次补正，不重跑）**：早先写作"取 before 指纹时注册表尚未稳定"——这一归因
> **证据不足，撤销**。首次失败后重跑成功只证明**重跑通过**；本轮没有留存首次失败的差异明细，
> 因此**不能**断定首次差异来自注册表未稳，也不能断定环境或产品。可核对的只有：同一环境下
> **手工重放无字段差异**、**第二次 L4 PASS**、以及**后续各轮 L4 均 PASS**。

#### 8.34.11-⑥b `unmappedPathCount` 由 10 变为 24 的逐路径覆盖（不为归零扩造规则）

第三轮 L1 的报告为 `changedPathCount=28`、`unmappedPathCount=24`、`manualNonZeroL2Required=true`。
计数的**含义未变**：24 条路径**未命中增量测试的推荐映射**，需人工选择非零 L2；这**不是**"没有未映射
路径"，也**不自动等于门禁失败**（口径见 8.34.7 与 8.34.7.1）。计数由 10 涨到 24 的原因是第三轮**新增
了 14 条改动路径**，不是规则收紧或覆盖退化。新增的 14 条及其**已执行**的覆盖检查如下：

| # | 新增路径 | 覆盖它的已执行检查 |
|---|---|---|
| 1 | `core_extension_policy_maps.py` | L2 `test_the_finance_role_surface_grants_the_two_finance_workbenches`／`test_the_project_role_surface_grants_the_team_loan_workbench`（角色导航差异与拒绝反例） |
| 2 | `models/support/__init__.py` | L2 全类导入即覆盖（0 测运行按治理规则失败，故 35 测通过即覆盖） |
| 3–5 | `models/support/{company_project_refund,current_account,team_loan_deduction}_workspace.py` | L2 `test_the_record_surface_reads_a_readable_name`；L3 运行态记录面回读 |
| 6 | `models/support/context_workspace_entry_authority.py`（新增） | L2 `test_a_carrier_fails_closed_when_the_authority_offers_several_routes`／`test_every_returned_carrier_is_pinned_to_the_operators_route_menu`／`test_a_principal_outside_the_role_surface_is_refused`；L3 记录面可读名回读 |
| 7 | `services/contract_governance_overrides.py` | L2 `test_the_native_authority_contract_carries_the_declared_governance`／`test_the_native_authority_path_keeps_the_declared_governance` |
| 8–10 | `tests/test_{company_project_refund,current_account,team_loan_deduction}_workspace.py` | L2 四 tag 运行（该三文件即被测体，随 `TestContextWorkspaceNativeLowcode` 同批执行） |
| 11 | `addons/smart_core/core/unified_page_contract_v2_assembler.py` | L2 `test_the_runtime_governance_merge_keeps_one_structure_owner`；L3 最终契约回读 |
| 12 | `addons/smart_core/handlers/ui_contract_v2.py` | 同上（交付契约出口） |
| 13 | `addons/smart_core/utils/contract_governance.py` | L2 `test_the_native_authority_pass_runs_only_declared_semantic_overrides` |
| 14 | `addons/smart_core/utils/contract_governance_domain_overrides.py` | 同上（注册表 `native_authority_safe` 安全名单断言） |

**结论口径**：本表只登记"**已经跑过、且输入包含该路径**"的检查，**没有为让计数归零而扩造映射规则**；
`unmappedPathCount` 仍由人工选择非零 L2 承担。

#### 8.34.11-⑦ 本轮未覆盖项（保持未执行）

最终 Quick、推送、建 PR、合并、部署、冻结、G09 启动、G07 浏览器矩阵重跑、`sync_demo`／fixture
reset、历史工作树清理，**均未执行**。台账保持 **25**（本批不扣减）。
继续对 878 以外的两个入口验证**隔离**而非闭环；每表单字段策略编辑器对 transient 工作台不可用，
作为**已命名的能力限制**保留，等待产品决定是否开放。

### 8.34.12 集中产品复核整改（第四轮，2026-09-19）

**复核结论（接受，本轮仍不放行冻结）**：第三轮的三项整改中，导航层级与可读身份的**机制**已成立，
但复核**实际打开** 878 新建页（桌面 1440 与 390 窄屏）后提出三项：① 提示组件**排版实际失败**
（`建议选择退款方…` 一字一行、顶部使用说明未完整展开），`sections=2、findings=[]` 没有覆盖这些
**可见**问题；② 新建页操作说明与报告口径不一致；③ C 包只证明了**后端闭环**，未证明**用户配置
路径**。另纠正两处证据表述（不重跑）。本轮按三项集中整改，结果如下。

#### 8.34.12-① 提示组件排版阻断：根因与**共享组件**通用修复

**现场（复核可见）**：桌面与 390 窄屏均出现 `建议选择退款方…` **一字一行**的浅蓝色长条；顶部
使用说明在桌面也未完整展开。

**根因（两个叠加，均在共享组件，无退款模型 CSS 特判）**：

- **A．反馈带的内容轨道解析为 0**：`frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue`
  的 `.native-form-feedback__content` 为 `display:grid; inline-size:max-content` 且**未声明显式轨道**，
  单个隐式列因此解析为 0。带内的事实区块**宽度来自网格而非文本**，于是只有约 14px，
  每个汉字单独成行。
- **B．共享告警体既不生长也不占位**：`ScInlineState.vue` 渲染 `TDesignAlert`；库内
  `.t-alert__description` 是普通块、宽度取自内容，其父 `.t-alert__message`／`.t-alert__content`
  为 `flex: 0 1 auto`，消息轨道收缩到描述的 `max-content`。**纯文本**告警因文本有真实固有宽度
  "看起来正常"，而内嵌网格内容时固有宽度为 0，整条被压扁——这正是顶部使用说明在桌面被排成
  单行裁剪的原因。

**修复（两条都是通用消费，非模型特判）**：

- `NativeFormTreeRenderer.vue`：`.native-form-feedback__content` →
  `grid-template-columns: minmax(0, 1fr); inline-size: 100%; max-inline-size: 100%; min-inline-size: 0;`
- `ScInlineState.vue`：新增 `.sc-inline-state :deep(.t-alert__message){min-width:0}` 与
  `.sc-inline-state :deep(.t-alert__description){flex:1 1 auto;min-width:0;width:100%}`。

**修复后实测（三入口 ×桌面 1440／窄屏 390，逐带读宽度、行数与横向裁剪）**：

| 入口 | 视口 | 使用说明带 | 办理提示带 | 文档横向溢出 |
|---|---|---|---|---|
| 875 班组借/扣款登记 | 1440 | 1111×22（1 行） | 1111×36（1 行） | 无（1440/1440） |
| 877 往来款登记 | 1440 | 1111×22（1 行） | 1111×36（1 行） | 无 |
| 878 公司&项目退款 | 1440 | 1111×22（1 行） | 1111×36（1 行） | 无 |
| 875 | 390 | 325×88（4 行） | 325×36（1 行） | 无（390/390） |
| 877 | 390 | 325×88（4 行） | 325×48（2 行） | 无 |
| 878 | 390 | 325×88（4 行） | 325×70（3 行） | 无 |

六个组合的反馈带内容轨道均 `clientWidth == scrollWidth`（无横向裁剪），**无**宽度小于 24px 的
文本叶子（原先为 14px、37 行）。

**为什么"数章节"漏掉它，以及现在如何不再漏**：原断言只统计
`[data-form-section-navigation] button` 的数量与结构重复／空容器，**宽度不是它的观测面**。
本轮在 P4 只读代表面加入机制断言
`scripts/formal_form_representative_journey.mjs` 的 `structureFindings().collapsed_callouts`：
对每个已渲染、宽度 ≥ 240 的 `.native-form-feedback`，带内 ≥ 4 字的文本叶子**不得**窄于 20px，
且内容轨道**不得**横向裁剪；由 `assertStructureResponsibility` 断言为空数组，报告里随
`findings` 输出实测宽度。

**负向对照（证明该检查对本次缺陷敏感）**：在运行页注入两条已退役的声明后，同一测量立即命中
`{"width":1111,"clipped":true,"squeezed":[{"width":14,…}]}`；撤除注入后为空。

#### 8.34.12-② 新建页操作说明与可读身份（**新生成的受管临时记录**实测）

**文案（本轮改写，三个入口统一）**：
> 先记录办理上下文，再选择办理事项。金额、账户和明细在打开的正式单据中填写；沟通、备注与附件也在正式单据中登记。

上一版"填写上下文后选择上方的办理按钮"描述了页面上并不存在的按钮（上方只有「记录办理上下文」），
已删除；`tests/test_context_workspace_native_lowcode.py` 的 `USAGE_NOTE_MARKERS` 同步为这三句。

**可读身份的验证对象是本轮新建的记录，不是失效历史页 103**。由工作台新建页经
「记录办理上下文」生成受管临时记录后，页签、副标题与面包屑读到的都是同一个可读名：

| 入口 | 本轮记录 | 页签／副标题／面包屑 |
|---|---|---|
| 878 公司&项目退款 | 147 | `公司与项目退款办理工作台 · 成本并发隔离测试项目` |
| 877 往来款登记 | 172 | `往来款办理工作台 · 成本并发隔离测试项目` |
| 875 班组借/扣款登记 | 188 | `班组借扣款办理工作台 · 成本并发隔离测试项目 · 演示业主 · 城市建设集团` |

三页正文均**不含** `模型,id` 形态字符串（页面正则扫描 `raw_pairs=[]`）。记录面在保存后随即出现
本入口的派发载体（878：扣款实缴退回／投标保证金退回／合同保证金退回／查看关联台账），
确认"临时模型"确有记录面、确有合法编辑态。

#### 8.34.12-③ C 包重做：管理员在**产品界面**完成配置（不调用 handler）

**正式界面**：配置工作台 `/admin/business-config?root_menu_xmlid=smart_construction_core.menu_sc_root`
（左侧「产品配置」，需 `group_smart_core_business_config_admin` ＋入口面）。

**选择 878 的具体操作**：「选择业务页面」→ 搜索框占位符 `输入页面名称` → 目录行
`公司&项目退款 系统菜单 / 财务中心 · 入口 878 页面类型 表单 配置记录 1/2，作用域匹配 1/2（非页面验收）`
→ 该行「选择」。选中后面板显示 `正在配置 公司&项目退款`、`可设计表单`。

**编辑／预览／发布／刷新／回滚**（全部走界面按钮，逐步记录实际 intent）：

| 步骤 | 界面动作 | 观测 |
|---|---|---|
| 编辑 | 「配置表单与布局」→ `data-bound-form-designer[data-ready=true]`；控件 `选择字段／字段显示名称／字段显示／新分组名称` | 设计器就绪 |
| 存草稿 | 「保存配置草稿」 | `ui.business_config.change_set.stage` ok，变更集 **438**，1 项 |
| 预览 | 「验证并预览」 | `ui.business_config.change_set.preview` ok，返回 preview token |
| 发布 | 「发布配置」 | `ui.business_config.change_set.publish` ok；`contract_id=674`、`version_no=5`、`post_publish_hash` 稳定 |
| 刷新 | 同一标签页打开生效页（应用 token 在**按标签页** `sessionStorage`，故新开标签只会得到登录页） | 生效页读到**配置后的字段标签** |
| 回滚 | 工作台「版本记录」→「恢复上一版本配置」→「确认继续」 | `ui.business_config.contract.versions` → `ui.business_config.contract.rollback`；界面自述 `表单新建态：使用默认配置；产品默认 #176 · v2`，横幅「配置已回滚并发布」 |

**回滚后的运行态核对（本地现场已复原）**：生效页不再含配置标签、仍含基线标签；契约 674
`active=False`（不再生效），产品默认 176 `active=True · v2`，邻居 173／175 `active=True · v2`
且 `write_date` 停在产品默认发布时刻（21:38），**本轮未变**；三入口契约身份与本轮升级后基线
**逐字节一致**：875 `2ee745c5106f…`、877 `29acd5e7262f…`、878 `90ab264ae272…`。

**写入口径（第四轮，如实登记）**：本轮**在产品界面发布并回滚了一次表单配置**
（变更集 437／438，契约 674），并**创建了临时上下文记录**（147／172／188），**未持久化目标业务
单据**。变更集行的状态与契约停用是两条不同的记账：`版本记录`的回滚以**停用契约**记账（674
`active=False`），变更集行保留为审计历史（437／438 仍记 `published`）。第二轮曾用的
「创建／修改了临时上下文记录，未持久化目标业务单据、未修改配置」口径**不再覆盖本轮**。

**875／877 的隔离反例（不重复完整闭环）**：两者只验证隔离——契约 173／175 身份、版本号与生效
状态在本轮全程未变，未产生任何属于它们的配置记录。自定义字段保持**未覆盖**。

#### 8.34.12-④ 两处证据表述修正（本次补正，不重跑）

- **配置闭环写入范围**：第三轮 8.34.11-③ 的五步闭环由 `TestContextWorkspaceNativeLowcode`
  **直接调用 handler**、在**测试事务内**执行，应写「**测试事务内执行，未持久化配置变更**」。
  它证明合成／约束／回滚机制，**不能**替代管理员在产品界面的配置路径（后者见 8.34.12-③）。
- **首次指纹失败归因**：8.34.11-⑥ 原写"注册表尚未稳定"，该归因**证据不足，已撤销**（详见该处
  修正框）：首次失败后重跑成功只证明**重跑通过**。

#### 8.34.12-⑤ 本轮修改范围

| 层 | 文件 | 内容 |
|---|---|---|
| 前端共享组件 | `frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue` | 反馈带轨道改为 `minmax(0,1fr)`；不再按内容收缩 |
| 前端共享组件 | `frontend/apps/web/src/components/design-system/ScInlineState.vue` | 告警体声明占满告警预留宽度（**已被 8.34.13 取代**：该写法依赖 TDesign 内部选择器，已改为项目自有容器机制） |
| P4 验证工具 | `frontend/apps/web/scripts/formal_form_representative_journey.mjs` | 新增 `collapsed_callouts` 宽度／裁剪断言 |
| P1 视图 | `addons/smart_construction_core/views/support/{team_loan_deduction,current_account,company_project_refund}_workspace_views.xml` | 使用说明文案 |
| 测试 | `addons/smart_construction_core/tests/test_context_workspace_native_lowcode.py` | `USAGE_NOTE_MARKERS` 同步 |

第三轮改动（24 条路径）仍在同一分支工作区，未回退。

#### 8.34.12-⑥ 本轮分层验证结果

- **L2**：四 tag 整组 PASS，`0 failed, 0 error(s) of 41 tests`（`TestContextWorkspaceNativeLowcode`
  ＋`TestTeamLoanDeductionWorkspace`＋`TestCurrentAccountWorkspace`＋`TestCompanyProjectRefundWorkspace`）。
- **L1** `make ci.local.iteration`：**PASS**，`change_state=dirty`、`scope=unclassified_by_design`、
  `coverage=L1_only`、`receipt=none`、`changedPathCount=31`、`unmappedPathCount=24`、
  `manualNonZeroL2Required=true`。计数含义与逐路径覆盖见 8.34.11-⑥b：**仍是同一 24 条**，本轮新增的
  3 条路径（两个前端共享组件 ＋ 一个 P4 脚本）**命中**了增量推荐映射，未进入未映射集合，
  因而 `unmappedPathCount` 未变化。本轮仍未为归零扩造规则。
- **L3**：`smart_construction_core` `installed`（`latest_version=17.0.0.168`）；本轮三份视图 XML 经
  `make local.dev.upgrade MODULE=smart_construction_core` 重新入库、服务重启后回读确认：三视图
  均含新使用说明文案，且办理提示为 `invisible="not processing_advisory"` 的非分组内联反馈。
- **L4** 只读代表面 `FORM_LOWCODE_TOPIC=context_workspace FORM_LOWCODE_REPRESENTATIVE=1`：**PASS**，
  `artifacts/lowcode-form-loop/browser/representative-report-context_workspace.json`：
  `ok=true`、`restored=true`、`browser_errors=[]`、`representative_uncovered=[]`、
  `representative_blocked=[]`；三个 surface（875／877／878）status `passed`，各自 create 路线的
  `findings.collapsed_callouts=[]`——**新增的宽度／裁剪断言已进入常跑门禁**。
- **浏览器（本轮定向，非最终 Quick）**：三入口 × 桌面 1440／窄屏 390 排版实测（8.34.12-①）、
  三个新建受管临时记录的可读身份（8.34.12-②）、878 的管理员配置闭环
  `选择 → 编辑 → 存草稿 → 预览 → 发布 → 刷新 → 回滚`（8.34.12-③）。

#### 8.34.12-⑦ 本轮未覆盖项与未执行项

- **未覆盖**：每表单字段策略编辑器对三个 transient 工作台仍不可用（**已命名的能力限制**，
  不改名通过）；875／877 只验证隔离；自定义字段未覆盖。
- **未执行**：最终 Quick、推送、建 PR、合并、部署、冻结、G09 启动、G07 浏览器矩阵重跑。
  **台账保持 25**。
- **交回重点**：用户如何从这三个工作台进入正式办理（8.34.12-②）、合法配置如何作用于页面
  （8.34.12-③，产品界面路径）；授权差异表保留至最终独立复核。

#### 8.34.13-① 复核判定：内部厂商选择器不可冻结，且**既有守卫已经捕获**

第四轮可见效果通过（878 桌面／390 换行正常、新建说明文案准确、临时记录 147 可读名与办理按钮、
配置工作台可选 878 并进入「表单字段与布局」），但源码在
`frontend/apps/web/src/components/design-system/ScInlineState.vue` 新增两条 TDesign 内部选择器：

```
.sc-inline-state :deep(.t-alert__message){min-width:0}
.sc-inline-state :deep(.t-alert__description){flex:1 1 auto;min-width:0;width:100%}
```

`docs/frontend_productization/rendering-detail/official-design-alignment-inventory-v1.json` 的
authority 明确要求 `inherit official defaults; customize only through installed public CSS
variables; internal vendor selectors require removal`，完成规则为
`internalVendorSelectorGapCount=0`。因此该项**未通过**，不能因为视觉修好了就冻结。

**既有守卫无需新造，且本轮实测已经抓到**：`scripts/verify/frontend_inline_state_guard.py` 早已把
`:deep(.t-alert__description)` 列为禁用形态，第四轮版本在该守卫下**直接 FAIL**
（`inline state bypasses the official Alert slot boundary with :deep(.t-alert__description)`）；
它已挂在前端守卫链上（`make/frontend.mk` 的 `verify.frontend.rendering_detail_state.unit`）。
本轮只做两处**收紧**，未放宽任何规则：

- 禁用元组补上复核点名的另一条 `:deep(.t-alert__message)`；
- 新增三条**正向**标记要求（`container-type:inline-size`、`inline-size:100cqi`、
  `grid-template-columns:minmax(0,1fr)`），使"内部选择器依赖"与"项目自有宽度机制"双向都可被守卫识别；
- `scripts/verify/test_frontend_inline_state_guard.py` 增两条用例（内部选择器识别／正向标记必需）。

#### 8.34.13-② 锁定版本 Alert 的公开面核查与**合法**宽度机制

核查锁定版本 `tdesign-vue-next@1.20.5`（`es/alert/alert.mjs`、`props.mjs`、`es/alert/style/index.css`）：

- 公开 props：`close`／`closeBtn`／`default`／`icon`／`maxLine`／`message`／`operation`／`theme`／`title`／`onClose`／`onClosed`；
- 公开 slots：`default`（正文）／`message`（仅在无 `default` 时兜底，落点相同）／`operation`／`title`／`icon`／`close`；
- **公开 CSS 变量：无**。官方样式里正文体的宽度是**硬编码**的 flex 属性而非变量：
  `.t-alert__message{width:100%;display:flex}`、`.t-alert__description{flex:0 1 auto}`；
- `renderDescription()` 恒把 `default` 插槽包进该 flex item，因此**不存在**可用的公开
  prop／slot／CSS 变量让正文体生长。这正是第四轮不得不 `:deep()` 的原因，也是本轮必须换机制的原因。

**合法替代（宽度责任落回项目自有内容容器，全程不触碰厂商内部元素名）**：

1. `.sc-inline-state{container-type:inline-size}` —— 自有根类＋仓库**既有**机制
   （`FormSection.vue`／`ProductListHeader.vue` 等已在用容器查询与 `cq*` 单位）；
2. `.sc-inline-state__description{display:grid;grid-template-columns:minmax(0,1fr);inline-size:100%;max-inline-size:100%;min-inline-size:0;overflow-wrap:anywhere}`；
3. `.sc-inline-state__description::after{content:"";display:block;block-size:0;inline-size:100cqi}` ——
   自有度量元素只声明**最大宽度**，真实宽度仍来自告警带；正文体因此既能占满预留宽度，**又可被
   flex 收缩到恰好可用宽度**（若把 `100cqi` 直接写在正文体上，会因固有宽度变成定值而无法收缩，
   实测溢出 30px、右侧被裁剪，故不采用）。

第四轮的 `.native-form-feedback__content` 原生反馈网格修复（显式 `minmax(0,1fr)` 轨道）**原样保留**，
未回退。

#### 8.34.13-③ 定向检查：四形态 × 桌面 1440／390

用 Vite 根目录临时开发页（**删除后交回，未入库**）挂载真实 `ScInlineState`，四形态实测，
并做「当前实现」与「重新注入两条已退役声明」的 A/B，两组都必须保持不变量：

| 形态 | 桌面 1440 带宽／正文宽／最小文本叶 | 窄屏 390 带宽／正文宽／最小文本叶 | 裁剪 | 操作区 |
|---|---|---|---|---|
| 普通文本 | 1408／1330／1330 | 358／280／280 | 无 | — |
| 网格内容 | 1408／1330／56（事实标签列） | 358／280／56 | 无 | — |
| 带操作区 | 1408／1272／1272 | 358／222／222 | 无 | 42px 可见可用 |
| 错误状态 | 1408／1330／1330 | 358／280／280 | 无 | — |

六组组合文档级无横向溢出（`scrollWidth==clientWidth`），无文本叶窄于 24px，无正文／网格横向裁剪。
A/B 结果：**注入已退役声明前后，四形态的可见不变量全部成立**（差别只在正文体的 flex 占宽，
不影响带宽、换行、操作区与裁剪）。截图：`/tmp/g08-r5-{desktop,narrow}-inline-state.png`。

#### 8.34.13-④ 关键回归证据：先删不补**确实回归**，补齐合法机制后复现第四轮通过态

**第一步（只删内部选择器、不补合法机制）在真实面失败**：`FORM_LOWCODE_TOPIC=context_workspace
FORM_LOWCODE_REPRESENTATIVE=1 make local.dev.form_lowcode.browser` →
`context_workspace action 875 create: a full-width callout must give its copy a definite track`，
实测命中 `{"width":1111,"clipped":true,"squeezed":[{"class":"professional-base-field-control__readonly","width":14}]}`。
⇒ 两条内部选择器在本批**是承重的**，不能只删不补；该失败先于任何"通过"结论被观测到，
未以旧证据顶替。

**第二步（补齐 8.34.13-② 的合法机制）同一门禁 PASS**：
`artifacts/lowcode-form-loop/browser/representative-report-context_workspace.json`：
`ok=true`、`restored=true`、`browser_errors=[]`、`representative_uncovered=[]`、
`representative_blocked=[]`，三 surface（875／877／878）`passed`、各自 create 路线
`findings.collapsed_callouts=[]`。

真实面逐带复测（与 8.34.12-① 第四轮**通过态逐格一致**，即机制更换未改变可见几何）：

| 入口 | 视口 | 使用说明带 | 办理提示带 | 文档横向溢出 |
|---|---|---|---|---|
| 875 | 1440 | 1111x22（1 行） | 1111x36（1 行） | 无（1440/1440） |
| 877 | 1440 | 1111x22（1 行） | 1111x36（1 行） | 无 |
| 878 | 1440 | 1111x22（1 行） | 1111x36（1 行） | 无 |
| 875 | 390 | 325x88（4 行） | 325x36（1 行） | 无（390/390） |
| 877 | 390 | 325x88（4 行） | 325x48（2 行） | 无 |
| 878 | 390 | 325x88（4 行） | 325x70（3 行） | 无 |

#### 8.34.13-⑤ 本轮最小差异

| 层 | 文件 | 内容 |
|---|---|---|
| 前端共享组件 | `frontend/apps/web/src/components/design-system/ScInlineState.vue` | 删除两条 `:deep(.t-alert__*)`；改为自有根类 `container-type` ＋ 自有轨道 ＋ 自有度量元素（`::after`） |
| P4 守卫 | `scripts/verify/frontend_inline_state_guard.py` | 禁用元组补 `:deep(.t-alert__message)`；新增三条正向标记要求 |
| P4 守卫单测 | `scripts/verify/test_frontend_inline_state_guard.py` | 新增两条用例 |
| 生成物 | `docs/frontend_productization/rendering-detail/{component-professionalization,visual-projection,official-design-alignment}-inventory-v1.json` | 随源码变更刷新指纹（**仅 digest 变化，无结构变化**） |
| 文档 | 本文件 | 8.34.13 ＋ 状态 |

#### 8.34.13-⑥ 本轮验证与未执行

- 受影响门禁 `make verify.frontend.rendering_detail_state.unit`：**PASS**（56 测 0 failed；
  `frontend_inline_state_guard` PASS；`official_design_alignment` `internalVendorSelectorGapCount=0`；
  `rendering_detail`／`visual_projection` 生成物一致）。
- 真实面只读代表面：**PASS**（见 8.34.13-④）。
- **未执行（按复核指示）**：配置发布／回滚重跑、后端四 tag、整组业务矩阵、最终 Quick、推送、
  冻结、G09 启动。
- 组件边界结论：**内部厂商选择器依赖已移除，宽度责任落在项目自有内容容器**；本轮只补受影响路径。

### 8.34.14 冻结轮：首跑 Quick 捕获的 P0 门面门禁回归与修复（2026-09-19）

#### 8.34.14-① 首跑 `make ci.local.quick` **失败**（真实门禁回归，非环境／基线问题）

| 项 | 事实 |
| --- | --- |
| 候选 | `c7cb7b75e385907a1d5a9f602ccfa7065f8bdc0b`（冻结前生成物刷新提交，工作区 clean） |
| 失败点 | `scripts/verify/contract_governance_domain_overrides_split_guard.py` |
| 失败输出 | `contract_governance.py missing domain override split token: _domain_overrides.register_contract_domain_override(name, handler, priority=priority)` |
| 分类 | **实现侧（P0 门面）接口扩展**导致既有 P4 结构 token 失配；不是环境缺陷、不是基线／证据缺陷、也不是守卫误判 |
| 首次偏差点 | `addons/smart_core/utils/contract_governance.py` 的 `register_contract_domain_override` 委派行被改写为多行并追加 `native_authority_safe=` 关键字 |

守卫钉住的是结构不变量——**门面只做单行委派、注册表本体住在拆分模块**。本批新增
`native_authority_safe` 参数时把该委派行整体重排，字面 token 因此不再命中，Quick 在链尾
`contract_governance_domain_overrides_split_guard`（`make/ci.mk:910`，链尾第 30 条命令）处
fail-closed 停止（收据未签发）。

#### 8.34.14-② 修复归属：改实现，不改规则

- 把 `native_authority_safe` 的转发拆成**独立委派调用**；默认路径保留守卫钉住的单行委派
  `_domain_overrides.register_contract_domain_override(name, handler, priority=priority)`。
- **未修改** `scripts/verify/contract_governance_domain_overrides_split_guard.py`：token 列表、
  禁用项与 `MAX_GOVERNANCE_LINES=1792` 行预算全部原样保留，**没有**把规则改成迁就实现。
- 行为等价：两种写法在 `DOMAIN_OVERRIDE_REGISTRY` 产出的行字段完全一致
  （`name` / `priority` / `handler` / `native_authority_safe`），仅源码文本变化；因此第五轮
  运行态证据的**行为**结论不受影响，但候选指纹随后更新，运行态报告按 8.34.14-④ 重新绑定。

#### 8.34.14-③ 修复后复验（只补受影响路径）

| 检查 | 结果 |
| --- | --- |
| `contract_governance_domain_overrides_split_guard.py` | **PASS** |
| Quick 链尾 24 项定向守卫／smoke（`construction_core_extension_*`、`ui_contract_v2_responsibility_map`、`v1_1_convergence_status`、`action_view*`、`frontend_page_contract_*`、`frontend_contract_consumer_intrusion`、`frontend_shared_surface_semantic_boundary`、`product_client_action_boundary`、`test_frontend_release_evidence_bundle`） | **PASS**（`tail_guard_failures=0`） |
| L2 `TEST_TAGS="uc4_native_lowcode"` | **PASS** `0 failed, 0 error(s) of 97 tests` |
| `make ci.delivery.freeze.prepare` | **PASS**；生成物仅随行数变化（`contract_governance.py` 1406→1412），无结构变化 |

#### 8.34.14-④ 冻结身份与冻结后的证据绑定口径

- 分支 `feature/uc4-g08-context-workspace-native-v1`；基线 `26d254ad`；**冻结 HEAD 即本记录所在提交**
  （`git log -1 --format=%H`）；冻结时 `git status --porcelain=v1 --untracked-files=all` 为空；
  相对基线改动 **40 条路径**。
- 为保证 `ci.local.quick` 的 exact-head 收据与冻结指纹**同一绑定**，冻结提交之后**不再产生仓库提交**：
  受影响运行态复检（代表面 journey ＋ 后端加载代码／模块升级状态核对）与最终 Quick 的结果，
  记录在**外部归档报告**（`/home/lidefend/workspace/.codex-evidence/workspace-archives/`）与
  `artifacts/lowcode-form-loop/browser/representative-report-context_workspace.json`。
- 台账保持 **25**；未推送、未部署；G08 入口退役的台账核减仍按既定规则**待合入后独立核对**。

#### 8.34.14-⑤ 冻结轮独立复核：授权差异与拒绝反例按**实际主体**重测（含一处记录更正）

**复核方式（只读）**：`odoo shell` 探针直接调用与客户端同一份 route authority 契约
（`IdentityResolver.build_role_surface` → `DeliveryEngine.build` → `route_authority`），
按 `(action_id, res_model)` 统计每个载体的候选菜单数（即 `_sc_entry_menu_ids` 的判据）；
建档能力用 `savepoint` 包裹的**真实** `create` 测量并**回滚**——本轮评审**未持久化任何记录**。
运行态加载代码已核对：`contract_governance.py` 容器内 `sha256=51e7b21d…3ae3d`，与宿主一致；
`DOMAIN_OVERRIDE_REGISTRY` 中 `native_authority_safe` 条目**恰好 1 条**
（`smart_construction_core.context_workspace_form`，priority 30）。

| 主体（`role_code`） | 875 入口 | 877 入口 | 878 入口 | 875 载体 | 877 载体 | 878 载体 |
| --- | --- | --- | --- | --- | --- | --- |
| `project_member`（`demo_role_project_manager`／`demo_role_project_user`） | 可见 | 不可见 | 不可见 | **3／3 配对** | 553／372（无 877 入口，不可达） | 372（无 878 入口，不可达） |
| `finance`（`demo_role_finance` 等 7 个主体） | 不可见**且建档被 ACL 拒绝** | 可见 | 可见 | 3／3 | **6／6 配对** | **5／5 配对** |
| `system_admin`／`business_full`／`business_config_admin` | 不可见 | 不可见 | 不可见 | 0／3 | 0／6 | 0／5（均业务文案 fail-closed，非静默放行） |

**结论**：**14 个派发载体在其归属角色的导航面上 14／14 全部可配对**（finance 11 ＋ project 3），
这比第三轮只登记「目标类型覆盖」更强；且**未新增任何原生菜单可见性**——路由仍由当前用户原生菜单
可见性门控，`create` 仍由模型 ACL 把关。

**两处记录更正（原句把合成主体的行为写成 fixture 主体的行为）**：

1. §8.34.11-④(c) 原写"project **read** principal 既拿不到 875，也拿不到载体路由"。实测 fixture
   `demo_role_project_read` 同时持 `finance_read`，因此**拿到**三条载体路由
   （553／563／372，`CONTEXTUAL_ROUTE`）；它拿不到的是 875 **入口菜单**（该菜单持组为项目经办／
   主管），且三个 workspace 的 `create` 被 ACL 拒绝——即"进不了工作台"，不是"没有载体路由"。
2. §8.34.11-④(c) 原写 `demo_role_project_user`"在 877／878 上被 workspace ACL 挡在建档之前"。
   实测该主体持 `finance_user`，对 `sc.current.account.workspace`／
   `sc.company.project.refund.workspace` 的 `create` **允许**（savepoint 内真实 create 成功并回滚）；
   被 ACL 挡在建档之前的是**只持 `group_sc_cap_project_user`** 的合成主体（L2
   `test_a_principal_outside_the_role_surface_is_refused` 断言）。其 875 三个载体上轮 fail-closed
   的原因是**模型侧项目经办守卫**（`_check_project_operator`：「你不能为当前非本人负责或未关注的
   项目办理班组借扣款。」），不是路由授权缺失——主体只要是该项目经办人，三个载体即可正常配对。

**未变更的结论**：本批**未改任何 ACL**（`git diff --name-only 26d254ad..HEAD` 无 `security/`／
`access` 路径）；扩大的是角色导航面声明，且只对"原生已可见这些菜单"的主体生效。

### 8.34.15 G08 主线集成与台账 25 → 22（2026-09-19）

冻结候选 `e3d4703eb38456cafb8d518f619ed332208b4867`（tree `dc46ed33b7b90d1b58ff9924c5eb4b32c45b79e2`，
7 提交／**40 条路径**，exact-head `ci.local.quick` PASS）经 **PR #497** 以 squash 合入 main
`cefeff1fa48888bc54c60b7d01d144b18a5aaea8`；`origin/main^{tree}` 与候选 tree **逐字节一致**，
相对基线 `26d254ad` 的路径数同为 **40**。合入前该 head 上远端必检项 **9 success／3 skipped／0 fail**：
success `classify`／`frontend_release_gate`／`merge_policy_gate`／`professional_authorization`／
`professional_quality_gate`／`public_guard`／`public_guard_classify`／`python310_runtime_compatibility`／
`release_candidate_gate`；skipped `classify`（候选检查变体）／`fast`／`wait_for_candidate_checks`。
`make pr.merge.local_quick_gate` 以同一 head 的 exact-head 回执**复用**（未重跑矩阵），
`make pr.merge`（squash ＋ `--match-head-commit`）通过。

台账 `docs/ops/iterations/form_structure_compatibility_consumers_v1.json` 扣减 **25 → 22**
（本批在台账内**正好 3 条**：875 班组借/扣款登记（视图 1932）／877 往来款登记（1933）／
878 公司&项目退款（1934）），
退役 action 875／877／878，`count`／`localVerifiedCount`／`mainlineRemainingCount` 同步为 22，
并新增 `uc4G08PublishedAudit`。**按已合入源码逐项核对**：

- 三条入口契约（`team_loan_deduction_workspace_form_v1` 173／`current_account_workspace_form_v1` 175／
  `company_project_refund_workspace_form_v1` 176）只留 `title` ＋
  `composition_mode: native_semantic_surface`，各自绑定本入口 action；**无 sections／fields／columns**，
  兼容结构副本已退出，`structural_form_declarations()` 无声明、`diagnose_structure_ownership()` 不可能
  再为这三条产出 `LEGACY_STRUCTURE_KEY_OVERRIDE`。
- `view_orchestration.context` 的语义声明**原样保留**（三条均 `fact_authority: dispatch_only`；
  877 另保留 `fact_models`／`projection_authority`）——退役的是**结构副本**，不是入口声明的业务事实范围。
- **不额外计数**：三个工作台模型是 `TransientModel` 派发载体，自身不持有业务事实；三条原生主视图
  1932／1933／1934 一模型一视图、是该条目自身的渲染目标，**不随扣减退役**（`uc4G08PublishedAudit.reduction.
  retiredViewMeaning`）；本批新增的是**角色导航面声明**，不是台账消费者（`notDeducted`）。

**保留边界（不随本批关闭）**：每表单字段策略编辑器对三个 transient 工作台不可用（**已命名的能力限制**）；
875／877 只验证隔离、自定义字段未覆盖；系统设置 887 未开放；89 入口整体交付未完成
（`retirementComplete=false`）。

`nextBatch.selectedGroup` 前进到 **G09 用量与履约登记**（871／570／575，视图 1461／1476／1491），
`priorityActions` 同步为 `[871,570,575]`，`sourceMainlineHead` 更新为合入后 main；**G09 未启动**。

本提交为**文档类单职责提交**（台账 ＋ 本记录，路径集合固定为 2）；**未触碰**任何产品代码、契约、
测试或验证工具输入，故不改动 8.34.7／8.34.13 的 L1–L4 结论，也不重跑 Quick：候选的 exact-head Quick
回执属于 `e3d4703e`，本提交的收据由受管合并门禁按 fail-closed 口径产生，**不冒充同一绑定**。

状态：**G08 批次验收完成（本批范围）｜主线集成完成（PR #497，squash 同树）｜未部署｜89 入口交付未完成｜台账 22｜G09 未启动**。

### 8.34.9 状态

状态（**该阶段历史口径**）：**G07 已集成（主线 `26d254ad`，台账 25）｜G08 结构迁移与四轮整改已完成；第四轮集中产品
复核判定「可见效果通过、仅余组件边界」｜第五轮已移除 TDesign 内部选择器、把宽度责任落回项目
自有容器（真实面先复现回归、再复现第四轮通过态）｜**冻结轮首跑 Quick 在链上第 29 项守卫处
捕获 P0 门面门禁回归，已在实现侧修复且守卫未放宽（`make/ci.mk:910`）｜冻结轮独立复核按**实际主体**重测授权差异，更正 §8.34.11-④(c) 两处拒绝反例主体（见 8.34.14-⑤）**｜
**已冻结（冻结 HEAD 即本记录所在提交）**｜
未推送、未部署｜台账保持 25（本批不扣减）｜89 入口整体交付未完成**。

上述「未推送／未建 PR／未部署／台账保持 25」已在本批后续阶段执行并闭合，最终口径见 **8.34.15**。

第五轮状态要点（与 8.34.13 配套）：
- **工作树**：`feature/uc4-g08-context-workspace-native-v1`，基线 `26d254ad`。本轮把第二～五轮成果
  收拢提交；三个临时探针脚本（组件探针页／A-B 脚本／真实面测量脚本）**已删除、未入库**。
- **唯一阻断项处置**：删除 `ScInlineState.vue` 的两条 TDesign 内部选择器，改为项目自有容器机制
  （`container-type:inline-size` ＋ `minmax(0,1fr)` 轨道 ＋ `::after` 度量元素）；守卫随之**双向收紧**
  （禁用 `:deep(.t-alert__message)`／`:deep(.t-alert__description)`；正向要求自有机制三标记）。
- **已跑门禁**：`make verify.frontend.rendering_detail_state.unit` **PASS**（含
  `internalVendorSelectorGapCount=0`）；真实面只读代表面 **PASS**（三 surface
  `collapsed_callouts=[]`，逐带几何与第四轮通过态逐格一致）。
- **本轮写入（如实）**：仅源码／守卫／单测／生成指纹／本文件；**未发布或回滚配置、未创建业务单据、
  未修改业务数据**（运行后输出 `[local.dev.form_lowcode.browser] business fingerprints unchanged`）。
- **未执行**：最终 Quick、推送、建 PR、合并、部署、冻结、G09 启动；配置发布／回滚与后端四 tag
  按复核指示未重跑。
- **台账保持 25**：G08 入口退役核减仍按既定规则待合入后独立核对。
- **交回重点（第五轮）**：内部选择器依赖已消除的**最小差异**、四形态定向检查（桌面／窄屏）与真实面
  逐带复测（8.34.13-③／④），以及守卫双向收紧与"既有守卫已捕获"的事实（8.34.13-①）。

第四轮状态要点（与 8.34.12 配套）：
- **工作树**：`feature/uc4-g08-context-workspace-native-v1`，基线 `26d254ad`，已提交 HEAD `4c8deaf8`，
  **工作区 dirty**（第三轮 24 条 ＋ 第四轮 3 条 = **27 条路径**：26 改 ＋ 1 新增
  `models/support/context_workspace_entry_authority.py`）。第四轮临时探针脚本已全部删除，未入库。
- **已跑门禁**：L1 `make ci.local.iteration` **PASS**（`changedPathCount=31`、`unmappedPathCount=24`、
  `manualNonZeroL2Required=true`、`coverage=L1_only`、`receipt=none`）；L2 四 tag 整组 **PASS**
  （`0 failed, 0 error(s) of 41 tests`）；L3 视图 XML 随 `local.dev.upgrade` 入库并回读确认；L4 只读
  代表面 **PASS**（`ok=true`、`restored=true`、`browser_errors=[]`、`representative_uncovered=[]`、
  `representative_blocked=[]`，三 surface 的 `collapsed_callouts=[]`）。
- **第四轮回答的复核问题**：① 提示排版的**首次宽度丢失点**在**共享组件**（反馈带隐式网格轨道 ＋
  共享告警体未占满预留宽度），已通用修复并加入常跑宽度断言（含负向对照）；② 新建页操作说明改为
  「先记录办理上下文，再选择办理事项……」，可读身份改以**本轮新建**的临时记录 147／172／188 验证；
  ③ 878 的管理员配置路径在**产品界面**打通并**已回滚**（`选择 → 编辑 → 存草稿 438 → 预览 → 发布
  674 v5 → 刷新 → 版本记录回滚`），运行态回到基线。
- **本轮写入（如实）**：在产品界面**发布并回滚了一次表单配置**（变更集 437／438），并**创建了
  三个临时上下文记录**（147／172／188）；**未持久化目标业务单据**。第二轮口径
  「未修改配置」**不再适用本轮**，见 8.34.12-③。
- **未闭合项（明确列名，不改名通过）**：每表单字段策略编辑器对三个 transient 工作台仍不可用，
  登记为**能力限制**；878 之外的另两个入口只验证**隔离**；自定义字段未覆盖。**未开放系统设置 887**。
- **未执行（保持未执行）**：最终 Quick、推送、建 PR、合并、部署、冻结、G09 启动、G07 浏览器矩阵重跑。
- **台账保持 25**：G08 入口退役的台账核减按既定规则**待合入后独立核对**，本轮不动台账。

第三轮状态要点（与 8.34.11 配套）：
- **工作树**：`feature/uc4-g08-context-workspace-native-v1`，基线 `26d254ad`，已提交 HEAD `4c8deaf8`，
  **工作区 dirty**（第三轮 23 改 ＋ 1 新增 = 24 条路径，含 P1 新增
  `models/support/context_workspace_entry_authority.py`）。
- **已跑门禁**：L1 `make ci.local.iteration` **PASS**；L2 `TestContextWorkspaceNativeLowcode` 全类
  **PASS**（四 tag 整组 `0 failed, 0 error(s) of 41 tests`；其中 `TestContextWorkspaceNativeLowcode`
  全类 35 测，含第三轮 5 项 C 包测试）；L3 模块 `installed`／
  `latest_version=17.0.0.168` ＋ 本轮视图 XML 随升级入库；L4 只读代表面 **PASS**（`ok=true`、
  `restored=true`、`browser_errors=[]`、`representative_uncovered=[]`）。
- **本轮回答的两个复核问题**：用户如何从这三个工作台进入正式办理（→ 8.34.10-A ＋ 8.34.11-② 的
  新建页操作说明与可读身份）；合法配置如何作用于页面（→ 8.34.11-③ 的 878 变更集闭环：
  标签／显隐／order permutation 生效，必填与动作不变，邻居逐字节不变，rollback 回基线）。
- **未闭合项（明确列名，不改名通过）**：每表单字段策略编辑器对三个 transient 工作台在设计上关闭，
  登记为**能力限制**；878 之外的另两个入口只验证**隔离**。**未开放系统设置 887**。
- **未执行（保持未执行）**：最终 Quick、推送、建 PR、合并、部署、冻结、G09 启动、G07 浏览器矩阵重跑。
- **台账保持 25**：G08 入口退役的台账核减按既定规则**待合入后独立核对**，本轮不动台账。

第二轮状态要点（与 8.34.10 配套，历史留存）：
- **工作树**：`feature/uc4-g08-context-workspace-native-v1`，基线 `26d254ad`，已提交 HEAD `4c8deaf8`，
  **工作区 dirty**（第二轮 22 条路径：21 改 ＋ 1 新增，其中 24 条未命中增量推荐映射、3 条映射到前端单测目标）。
- **已跑门禁**：L1 `make ci.local.iteration` **PASS**（16 静态测 0 failed、`change_state=dirty`、
  `changedPathCount=27`、`unmappedPathCount=24`、`coverage=L1_only`、`receipt=none`）；
  L2 四 tag **PASS**（31 测 0 failed 0 error）；L3 模块 `installed`／`latest_version=17.0.0.168` ＋
  宿主／容器逐文件 `sha256` 一致 ＋ 最终契约回读；L4 只读代表面 **PASS**（`ok=true`、`restored=true`、
  `browser_errors=[]`、`representative_uncovered=[]`）。
- **未执行（保持未执行）**：最终 Quick、推送、建 PR、合并、部署、冻结、G09 启动。
- **台账保持 25**：G08 入口退役的台账核减按既定规则**待合入后独立核对**，本轮不动台账。

补记（2026-09-18，第一轮，仅文档改动）：8.34.8-② 的「`page` 走 create 隐藏分支」由代码推断升级为
**在受管运行态直接执行治理函数**的观测；8.34.8-③ 补登首次偏差点与影响面。
**该补记中"仍未覆盖端到端 edit 档位渲染"的结论已在第二轮被取代**：记录面经真实路径观测到，
端到端 edit 档位已覆盖（见 8.34.8-② 与 8.34.10-A），该句不再作为当前未覆盖项。
同时，第一轮"G08 把受影响入口由 1 条扩到 4 条"的写法已按实际变更关系收敛（见 8.34.8-③）。

下一步（**未执行**）：集中产品复核（第四轮）→ 按整组页面组织、字段表达、明细操作、导航及配置效果
统一列问题 → 定向修正 → 冻结候选 → 最终 Quick → 独立复核 → 受管 PR。

**交回重点（第四轮）**：① 用户如何从这三个工作台进入正式办理——新建页操作说明（8.34.12-②）与
**新生成的受管临时记录**上的页签／副标题／面包屑可读名（147／172／188）；② 合法配置如何作用于
页面——**管理员在产品界面**的 878 闭环 `选择 → 编辑 → 存草稿 → 预览 → 发布 → 刷新 → 回滚`
（8.34.12-③，含界面入口、控件清单与实际 intent），以及提示排版的共享组件修复与常跑宽度断言
（8.34.12-①）。**不再只报结构树与函数测试通过**，也不再以"数章节"代表排版通过。

**交回重点（第三轮，历史留存）**：受影响页面（8.34.11-① 的辅助信息层级、8.34.11-② 的可读身份与
操作说明）、配置闭环（8.34.11-③ 的 878 五步闭环与三条拒绝面）与授权差异（8.34.11-④ 的两行导航
差异表与三个拒绝反例）。其中 8.34.11-③ 的闭环口径已按 8.34.12-④ 修正为
「测试事务内执行，未持久化配置变更」。

## 8.35 G09 用量与履约登记整组原生结构迁移（2026-09-19）

### 8.35.1 归属与唯一写入者（本批）

| 层 | 唯一写入者（路径） | 说明 |
|---|---|---|
| P1 行业标准产品 | `addons/smart_construction_core/views/core/labor_management_views.xml`、`…/equipment_management_views.xml`、`…/subcontract_management_views.xml` | 原生 arch 承接本组三个模型的业务章节身份（每组 2 个 `data-sc-anchor`，共 6 个），未改任何业务事实、必填、只读或明细列 |
| P1 行业标准产品 | `addons/smart_construction_core/data/labor_usage_form_productization_contract.xml`、`…/equipment_usage_form_productization_contract.xml`、`…/subcontract_register_settlement_form_productization_contract.xml` | 入口级发布转 `native_semantic_surface`（只留 `title` ＋ `composition_mode`）并补 871 的入口级发布；`view_orchestration.context` 原样保留 |
| P1 行业标准产品 | `addons/smart_construction_core/data/view_orchestration_form_section_contract_data.xml` | 三条模型级 sections 契约 `active=False`（纯章节元数据，`fields` 为空） |
| P1 行业标准产品 | `addons/smart_construction_core/tests/test_usage_performance_native_lowcode.py`、`tests/__init__.py` | 新增 17 测（tag `uc4_native_lowcode`） |
| P4 运维交付工具 | `scripts/verify/local_dev_form_lowcode_scope.py`、`frontend/apps/web/scripts/formal_form_representative_journey.mjs` | 只读代表面 `usage_performance` topic 注册 ＋ 只读「表单设置」可用性实测（见 8.35.5） |

本批候选为 **11 条路径**（L1 读数 `changedPathCount=11`，其中 10 条未映射、1 条映射到
`verify.frontend.typecheck.strict`）。**未触碰**其它模块、前端产品代码、契约模型、菜单、动作载体或数据。

### 8.35.2 入口矩阵（L3 运行时实测，`sc_dev_demo`，action／view／menu 为库内真实值）

| 入口 | 菜单 | action | 模型 | 原生主表单 | 台账登记 |
|---|---|---|---|---|---|
| 871 劳务成本登记 | 689 项目中心/劳务成本 | `action_sc_product_labor_cost_v1` | `sc.labor.usage` | **1461** `view_sc_labor_usage_form` | 是（本批 3 条之一） |
| 562 方单 | 504 材料成本/劳务管理 | `action_sc_labor_usage_ticket` | `sc.labor.usage` | **1461**（同一 form arch） | **否（台账 0 次）** |
| 563 零星用工 | 505 材料成本/劳务管理 | `action_sc_labor_usage_casual` | `sc.labor.usage` | **1461**（同一 form arch） | **否（台账 0 次）** |
| 570 机械台班登记 | **692 机械成本 ＋ 509 材料成本/机械设备** | `action_sc_equipment_usage` | `sc.equipment.usage` | **1476** `view_sc_equipment_usage_form` | 是（仅 menu 692 一条） |
| 851 机械台班记录 | 510 材料成本/机械设备 | `action_sc_equipment_usage_shift_user_confirmed` | `sc.equipment.usage` | **1476**（同一 form arch） | 否 |
| 575 分包成本登记 | **693 分包成本 ＋ 518 材料成本/专业分包** | `action_sc_subcontract_register` | `sc.subcontract.register` | **1491** `view_sc_subcontract_register_form` | 是（仅 menu 693 一条） |

- 562／563／851 钉的是各自的 **tree** 视图（2049／2050／2051），表单落到模型主表单，
  因此与 871／570 消费**同一份 form arch**（运行时确认，非推断）。
- 561 劳务用工（`action_sc_labor_usage`）**无菜单、无契约**，不在本批范围内；其章节来源是
  模型级 `entry_semantic_surface` 声明，章节为空是它**自身的既存缺口**，与本批无关。
- 每条 form 都是该模型**唯一**的 active 主表单（`inherit_id=False`）。

### 8.35.3 台账口径与实际影响面的差异（如实登记，不缩范围）

台账 `docs/ops/iterations/form_structure_compatibility_consumers_v1.json` 按**菜单**登记，
本组**正好 3 条**（871/menu 689、570/menu 692、575/menu 693）。实际受影响面是 **8 个消费入口**：

- **共享表单**：1461 被 3 个 action 消费、1476 被 2 个、1491 被 2 个（含 570／575 的第二菜单）。
- **旁路入口从未登记**：562／563 在台账中出现 **0 次**。
- **双菜单载体只登记其中一条**：570、575 各有第二个菜单（509／518）未登记。

本批**按已登记条目扣减**（合入后 22 → 19，独立文档提交），同时把上述 4 条兄弟入口级契约
（227／228／229／233）、旁路入口、双菜单载体与新发现的 3 条生成镜像补登进台账审计字段，
**不扩大扣减范围**。

### 8.35.4 修改范围、前后差异与关键决策

**原生 arch（P1）**：三个 form 各自的第一个概览组补 `name` ＋ `data-sc-anchor` ＋ `string`，
第二个概览组补 `name` ＋ `data-sc-anchor` ＋ `string`，外层包装组补 `name`。新增锚点：

- 1461：`labor_usage_processing_main`「用工主信息」／`labor_usage_labor_amount`「用工与计价」
- 1476：`equipment_usage_identity`「设备与项目」／`equipment_usage_usage_amount`「使用与计价」
- 1491：`subcontract_register_main`「登记主信息」／`subcontract_register_parties_amount`「分包单位与金额」

**计数口径（必须路径限定）**：`git diff -U0 -- <view> | grep -c '^+.*<group .*data-sc-anchor='` ＝ **每文件 2**、
合计 **6**。同一命令用 `grep -c '^+.*data-sc-anchor'` 会读到 **每文件 3**，因为本批在 arch 内写了
**说明注释**、注释文本含 `data-sc-anchor` 字样——**该读数不得用于分组计数**（同 8.33.3 的口径教训）。

**入口级发布（P1，库内 id）**：

| id | 契约 | action | 本批变化 |
|---|---|---|---|
| 682 | `labor_usage_register_productized_form_v1` | 871 | **新增**（871 此前无入口级发布，回落模型级平面） |
| 227 | `labor_usage_ticket_productized_form_v1` | 562 | `50 → 800`；`entry_semantic_surface`（19 个 fields）→ `native_semantic_surface`（只留 `title`） |
| 228 | `labor_usage_casual_productized_form_v1` | 563 | 同上 |
| 230 | `equipment_usage_register_productized_form_v1` | 570 | 同上（12 个 fields → 只留 `title`） |
| 229 | `equipment_usage_shift_productized_form_v1` | 851 | 同上 |
| 232 | `subcontract_register_productized_form_v1` | 575 | 同上（14 个 fields → 只留 `title`） |

**关键决策与依据**：

1. **入口级契约只留 `title` ＋ `composition_mode: native_semantic_surface`**，`view_orchestration.context`
   原样保留，**不手工递增 `version_no`**（U-C3／G07 先例）。
2. **补 871 的入口级发布**：871 此前**没有**入口级发布，消费模型级 `sc_labor_usage_form_sections_v1`
   的平面，渲染的不是本入口的业务任务面（同 G07 为 858 补 `hr_payroll_management_productized_form_v1`）。
3. **优先级 `50 → 800`（本批的关键修正）**：本组入口发布原先排在模型级载体（sections 20／
   p1 facts 88／生成镜像 104–165）**之前**，导致 `resolve_form_structure_governance` 的**最后一个结构
   写入者**是模型级 `entry_semantic_surface` 声明，与运行时实际生效的 native 权威**不一致**
   （G02 用 700、G07 用 700–800，均"入口发布排最后"）。提为 800 后入口的 native 声明成为最后写入者，
   两处解析口径一致；入口发布不携带结构键，故该次序变化**不改变呈现**。三个 XML 顶部各记录该理由。
4. **模型级 sections 契约退役**（`active=False`，库内 154／160／156，priority 20，`fields` 为空）：
   纯章节元数据，同 G02／G03 先例；升级后确认**完全消失**、不再进入 configs。
5. **模型级 p1-facts 契约保留 active**（库内 15／21／17，priority 88）：它们是这三个模型上**唯一**声明
   业务事实 `readonly` 策略的载体，原生 arch 未重述。实测该 `readonly` **确实生效**
   （`_apply_field_display_policy` 把 `readonly=True` 写进 field node）。退役它们需要原生 arch 先承接
   同名策略，**属策略变更而非结构变更**，本批不做（见 8.35.9）。
6. **生成镜像 ×3 保留 active**（库内 86／71／126，priority 121／104／165，`fields`-only 稀疏序注解）：
   同 G06 的 129、G05 的 72、G07 的 79 口径。
7. **233 `subcontract_settlement_productized_form_v1`（576 分包结算）不动**：另一模型、另一原生表单、
   另一台账分组，不在 871／570／575 授权内。
8. **不做 876 类"补入口发布"**：被授权入口全部已解析到 native；其余入口（561／562／563／851）已各有发布。

### 8.35.5 低代码路径：本组实测，不沿用上一批的临时模型结论

上一批（G08）测得「三个临时工作台入口页无『表单设置』」，该结论**只对其自身的 transient 模型成立**
（注入条件含 `ir.model.transient` 判负）。本组三个模型是**普通持久化模型**，因此该结论
**不得**被复用来回答"本组有没有合法低代码路径"；本批按 G09 自己的入口**重新实测**。

- 新增**只读**探针 `assertDesignerEntryAvailability`（`formal_form_representative_journey.mjs`，由 topic 的
  `designer_entry` 开关启用）：打开页头「更多操作」并按有界轮询读取「表单设置」条目，
  **不点击进入**，因此不打开、不暂存、不预览、不发布、不丢弃、不回滚任何变更集。
- 实测结果：**871／570／575 新建页「表单设置」均存在、可见、可操作**（`item_count=1`）。
  该探针曾因"点击后当帧读取"得到过一次 `item_count=0` 的**假阴性**，定位为渲染竞态后改为有界轮询；
  该次假阴性是本轮唯一一次探测偏差，**未产生任何配置写入**。
- **设计器写入闭环（选择 → 编辑 → 存草稿 → 预览 → 发布 → 刷新 → 回滚）本批未执行**：
  它属写入路径（并会按工具既有设计留下一张未发布复核草稿），超出本批"只读范围核对"的授权口径，
  如实登记为未执行项（见 8.35.8），**不以只读可用性代替写入闭环的通过结论**。
  **该状态已在有界复核轮更新**：代表入口 871 已补做合法配置闭环（发布 ＋ 回滚 ＋ 隔离），
  见 8.35.12-②；本段保留为只读轮的历史口径。

### 8.35.6 分层验证结果

| 层 | 入口 | 身份 | 结果 |
|---|---|---|---|
| L1 | `make ci.local.iteration` | 本批 HEAD＋dirty | **PASS**：16 静态测 OK；`baseline_iteration_execution_policy_guard` PASS；`change_state=dirty`、`coverage=L1_only`、`receipt=none`；`changedPathCount=11`、`unmappedPathCount=10`；`next=risk_selected_non_zero_L2_targets_required` |
| L2（本批类） | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='uc4_native_lowcode/smart_construction_core:TestUsagePerformanceNativeLowcode'` | 同上 | **PASS**：**17 测 0 failed 0 error**。过程中 1 例 `ERROR` 与 1 例失败已修后重跑（首偏差见 8.35.7） |
| L2（全组回归） | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='uc4_native_lowcode/smart_construction_core'` | 同上 | **PASS**：**114 测 0 failed 0 error**（G02–G09 全组，证明无跨批回归，非零测试） |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1` | `sc_dev_demo` | **PASS**：exit 0，含 `local.dev.verify_authority` PASS |
| L4（只读代表面） | `FORM_LOWCODE_TOPIC=usage_performance FORM_LOWCODE_REPRESENTATIVE=1 make local.dev.form_lowcode.browser` | 同上 | **PASS**：`ok=true`、`restored=true`、`browser_errors=[]`、业务指纹未变；报告 `artifacts/lowcode-form-loop/browser/representative-report-usage_performance.json` |

**L4 只读代表面明细（8 个已登记入口）**：

- **871／570（menu 692）／575（menu 693）：`create` ＋ `record` 双档位通过**，
  结构责任断言 `duplicated`／`empty_containers`／`decorated_layout_groups`／`titled_layout_groups` **全为空**。
- **章节导航**（1088×900 与 390×844）：871 create＝用工主信息／用工与计价（＋协作记录）、
  record 另含历史审计；570＝设备与项目／使用与计价（＋协作记录，record 另含历史审计）；
  575＝登记主信息／分包单位与金额／登记明细（＋协作记录，record 另含历史审计）。
  每条入口都实测「操作行底 < 导航顶」的分离（如 575 record @390：`actions.bottom=377 < nav.top=390`），
  跳转后目标标题落在视口内；575 record @390 章节轨溢出时有 **10 步**按压序列（含末→首、首→末、
  手动滚动后、轨滚动后）通过，其余档位章节轨不溢出故记 `not_applicable`（**非通过、非失败**）。
- **页签结构**：1461 四个页、1476 三个页、1491 五个页全部激活且带内容，无空页。
- **「表单设置」**：871／570／575 三处新建页均为**存在、可见、可操作**（见 8.35.5）。

**L4 被角色路由权威拒绝的 5 个入口（原写"角色边界／不计产品缺陷"，已按 8.35.12-⑥ 更正）**：

| 入口 | 菜单 | 拒绝原因 |
|---|---|---|
| 562 方单 | 504 材料成本/劳务管理 | `NAVIGATION_AUTHORITY_DENIED` |
| 563 零星用工 | 505 材料成本/劳务管理 | 同上 |
| 570 第二菜单 | 509 材料成本/机械设备 | 同上 |
| 851 机械台班记录 | 510 材料成本/机械设备 | 同上 |
| 575 第二菜单 | 518 材料成本/专业分包 | 同上 |

被授权入口走的是「项目中心/劳务成本」「机械成本」「分包成本」分支（对受管身份
`sc_test_admin` 可达）；上述 5 条走「材料成本/*」分支，运行角色路由权威不含该分支。
**口径更正（见 8.35.12-⑥）**：拒绝只登记为**该角色下未覆盖**；原文"不计产品缺陷"在没有
预期角色依据时**不得**使用，现撤回该定性。这 5 条中 562／563／851 的入口契约与共享原生树
由 L2 的 `ENTRIES`／`RETIRED_SECTION_CARRIERS` 断言覆盖（**声明层**，不是浏览器渲染结论）；
570 的第二菜单 509 与 575 的第二菜单 518 是同一 action 的第二个菜单载体，另无独立断言。

### 8.35.7 过程中的首次偏差（如实登记）

| # | 现象 | 定位 | 处置 |
|---|---|---|---|
| 1 | L2 `test_every_rendered_fact_belongs_to_its_own_model` 报 `ERROR` | 测试辅助 `_arch_field_owners` 把 `fields.Field` 当 dict 用（`(field or {}).get("relation")`），取 relation 时抛 `AttributeError` | 改为 `getattr(field, "relation", None)`；重跑 17 测全绿 |
| 2 | 同测试类早前 1 例失败（1491 呈现中立性） | 1491 的**内联 tree 列**（`sequence`／`work_scope`／`work_content`／`contract_qty`／`unit_name`）属同一 arch 的文档序，pin 未覆盖 | 补入 pin；列归属按 comodel 校验而非表单模型 |
| 3 | 「表单设置」只读探针首次读到 `item_count=0`（假阴性） | 点击「更多操作」后**当帧**读取 DOM，溢出面板尚未挂载 | 改为有界轮询（≤25 次／约 2s）后复测为 `item_count=1`；该次未产生任何配置写入 |

### 8.35.8 未覆盖项与剩余阻断（如实登记，不造数据）

- **562 记录态（`record_surface`）未覆盖**：该 action 域内 **0 行**（模型内 1 行），
  登记为 `state=empty_action_domain`，**未为补样本造数据**。
- **5 条旁路／第二菜单入口未做浏览器复核**（8.35.6 表），原因 `NAVIGATION_AUTHORITY_DENIED`，
  按 8.35.12-⑥ 只登记为**该角色下未覆盖**（不作非缺陷定性）。
- **设计器写入闭环未执行**（见 8.35.5），只完成只读可用性实测；
  **该缺口已在有界复核轮补上**（代表入口 871，见 8.35.12-②）。
- **动作载体（按钮）、字段策略面、共享吸顶与窄屏的其它形状未单独探测**。
- **未执行项（保持未执行）**：最终 Quick（冻结后一次）、推送、建 PR、合并、部署、台账扣减提交、
  89 入口整体交付、历史工作树／分支清理、`sync_demo`／fixture reset／发布快照。
- **台账**：本批提交**不扣减**；扣减（22 → 19）与补登留作合入后的独立文档提交。

### 8.35.9 保留边界（不随本批关闭）

- **三条模型级 p1-facts 契约保留 active**（15／21／17）：承载业务事实 `readonly` 策略。
  退役前提是**原生 arch 先承接同名只读策略**——1491 上有 **11 个纯策略字段**不在原生 arch 上，
  直接退役会**丢失只读口径**（策略变更，不在本批授权内）。
- **三条生成镜像保留 active**（86／71／126）：`noupdate="1"` 的稀疏序注解。若复核要求退役，
  须走精确 ORM `<function>`（G02 先例，且该 function 必须位于**另一个** `noupdate=0` 文件）。
- **233（576 分包结算）未动**；561 劳务用工的既存空章节缺口未动。

### 8.35.10 状态

状态：**自验与冻结门禁通过（本批范围）｜已完成有界复核轮二（身份／角色／工具补验，见 §8.35.13）｜已完成创建态可办理性修复与定向补验（见 §8.35.14）｜独立复核 S1 已修正并已在冻结身份上重绑执行证据（见 §8.35.15／§8.35.16）｜产品复核结论以产品方登记为准｜未集成｜未部署｜89 入口整体交付未完成｜台账 22**。
**G08 主线集成 ≠ 部署 ≠ 89 入口整体交付完成**，本批同理。

**口径更正（历史记录，见 8.35.12-①）**：本段状态行在收口轮之前曾写「G09 批次验收完成」，**已在 §8.35.15 之前的修正中
替换为上方现行状态行**；以本节状态行为本批唯一现行口径，上文括号内不再复述被替换文本。
按 AGENTS.md「Completion Status Boundaries」，`批次验收完成` 只能在 scoped changes ＋ targeted tests ＋
**batch product review** 三者都通过后使用；本批产品复核结论以产品方登记为准，本文件不代述，故不得使用该措辞。

### 8.35.11 冻结前复核补证：退役载体对**所有**消费者的 A/B 只读对比

本批退役三条模型级 sections 契约，最大的复核风险是「是否顺带改变了**别的**消费者（例如无菜单的
561 劳务用工）解析出来的结构」。为此在受管运行态做了一次**只读 A/B 对比**：把已退役的
154／160／156 重新拼回同一 action 的候选契约序列（同优先级＋id 排序），与当前序列分别调用
`resolve_form_structure_governance`，比较结构权威、呈现模式、章节数、字段数与分组数。

| action | 模型 | 当前 | 拼回已退役载体 | 结论 |
|---|---|---|---|---|
| 871／562／563 | `sc.labor.usage` | `native_authority`／`task`／0／20／0 | 同左 | **不变** |
| 561 劳务用工（无菜单） | `sc.labor.usage` | `entry_semantic_surface`／`task`／0／20／0 | 同左 | **不变** |
| 570／851 | `sc.equipment.usage` | `native_authority`／`task`／0／20／0 | 同左 | **不变** |
| 575 | `sc.subcontract.register` | `native_authority`／`task`／0／30／0 | 同左 | **不变** |

- 三条退役载体的 `priority` 都是 **20**，在本组所有消费者上都**早已被** p1-facts（88）与生成镜像
  （104／121／165）压过，因此退役**不改变任何消费者**的解析结果——退役的是"从未成为最后写入者"的
  冗余声明，不是任何入口实际消费的结构。**未删除任何入口仍在消费的结构。**
- 561 的 `entry_semantic_surface` 权威来自它自己的模型级 p1-facts 回落（88），**与本批无关**，
  退役前后一致；561 无菜单、无入口契约，属其自身既存缺口（见 8.35.2）。
- 该对比是**只读**的：只按已退役记录的内存副本重排候选序列，未写回、未激活、未修改任何契约。

下一步（**待执行**）：冻结候选（clean HEAD＋完整指纹）→ **一次** exact-head Quick → 独立复核与
外部归档 → `make pr.push` → draft PR → ready → **仅在明确授权后**合并 → 合入后台账 22 → 19 与补登。

### 8.35.12 有界复核轮（2026-09-19，只补复核缺口，不重跑整批）

授权口径：本轮**只补**集中复核提出的三项缺口（产品复核依据／低代码合法闭环与独立复核／台账与影响面），
**保持候选 `6511134c586320b8c07f1be8aa9d60ecb9d046d3`、PR #499 与运行现场不变**；
**不重跑 Quick、不重跑浏览器矩阵、不扩展产品改动**。冻结门禁（§8.35.11 下一步）已在上一轮完成，
本轮不重复执行。

本轮 dirty 范围（相对候选 commit）：`frontend/apps/web/scripts/formal_form_designer_journey.mjs`、
`frontend/apps/web/scripts/formal_form_lowcode_loop.mjs`、本文件。前两项是**为产出 8.35.12-② 闭环证据**
而做的 P4 工具修正（见 -② 末与 -⑧），三者**均未进入候选**；因此 PR #499 头指针仍为 `6511134c…`。

#### 8.35.12-① 状态口径更正

§8.35.10 与交付摘要中的「G09 批次验收完成」**更正为「自验与冻结门禁通过、待集中产品复核」**。
本批当前可达状态：分层自验通过（L1／L2／L3／L4）＋ 冻结门禁通过（clean HEAD ＋ 完整指纹 ＋
exact-head Quick）；**集中产品复核未完成**。`未集成`／`未部署`／`89 入口整体交付未完成`／`台账 22`
与**G08 主线集成 ≠ 部署 ≠ 89 入口整体交付完成**的边界不变。

#### 8.35.12-② 代表入口 871：合法配置闭环（发布 ＋ 刷新 ＋ 回滚）与现场绑定身份

**工况**：`FORM_LOWCODE_TOPIC=usage_performance FORM_LOWCODE_DESIGNER=1 make local.dev.form_lowcode.browser`
→ **EXIT=0**、`PASS formal designer journey`、`business fingerprints unchanged`。
报告：`artifacts/lowcode-form-loop/browser/designer-report.json`（`ok=true`、`restored=true`、
`candidate=6511134c…`、`change_set_id=487`、`cleanup_guard.decision=proceed`、`recovery_state.released=true`）。
截图：`designer-draft.png`／`designer-preview.png`／`designer-published.png`／`designer-rollback.png`／
`designer-outside-scope.png`。

**闭环路径**：产品界面 → 设计器 → 编辑 → 存草稿 → 预览 → **发布** → 刷新业务面 → **回滚**。
报告 `stages.designer` 五段全 `passed`（`browser`／`publication`／`final_contract`／`workflow`／`isolation`），
`stages.outside_page` 与 `stages.isolation_page` 见 -③。

**授权的 3 条补丁（全部为配置面，不触碰产品代码）**：

| # | 目标（locator） | 期望 | 设置 |
|---|---|---|---|
| 1 | `/form[1]/sheet[1]/group[1]/group[1]/field[5]` | `field` `labor_team` occ.1 | `label = 受管班组` |
| 2 | `/form[1]/sheet[1]/group[1]/group[1]` | `group` `labor_usage_processing_main` occ.1 | `order`（field[1]／[2]／**[5]**／[3]／[4]）＋ `configuration-group:designer`「受管用工配置」成员 field[5] |
| 3 | `/form[1]/sheet[1]/notebook[1]/page[1]/group[1]/field[2]` | `field` `construction_part` occ.1 | `label = 施工部位`、`visible = false` |

**可验证断言**：

- **视觉序生效**：`visual_order.status=passed`，`configured_y=550 < displaced_y=636`；未触碰字段
  `name`／`project_id`／`usage_type` 仍保持原生序。
- **预览结构**：`preview_structure.parent=labor_usage_processing_main`，`configuration-group:designer`
  就位于 `project_id` 与 `usage_date` 之间。
- **发布后业务面**：`usage_performance_business_surface.navigation_target=
  [data-form-section-target="node:labor_usage_processing_main:business-section"]`、
  `hidden_field_present=false`、`hidden_fact_in_contract=true`（隐藏字段在契约中仍是事实、只是不呈现）。
- **回滚生效**：`rollback_page.text` 恢复原生标签（`班组`／`施工部位` 回归、`受管用工配置` 分组消失）。

**现场绑定身份（供浏览器实检）**：前端 `http://127.0.0.1:5174`；登录 `sc_test_admin`（`res.users` id 51）；
库 `sc_dev_demo`；公司 `My Company`(id 1)；解析角色 `system_admin`；compose 项目 `sc-local-dev`；
模块 `smart_construction_core` 17.0.0.168。

| 入口 | 新建页（完整链接） | 记录页（完整链接） | 现场记录 |
|---|---|---|---|
| 871 劳务成本登记 | `/f/sc.labor.usage/new?action_id=871&menu_id=689` | `/f/sc.labor.usage/1?action_id=871&menu_id=689` | `sc.labor.usage` id 1 `S87-LU-001`（`confirmed`） |
| 570 机械台班登记 | `/f/sc.equipment.usage/new?action_id=570&menu_id=692` | `/f/sc.equipment.usage/1?action_id=570&menu_id=692` | `sc.equipment.usage` id 1 `S80-EU-001`（`confirmed`） |
| 575 分包成本登记 | `/f/sc.subcontract.register/new?action_id=575&menu_id=693` | `/f/sc.subcontract.register/1?action_id=575&menu_id=693` | `sc.subcontract.register` id 1 `S85-SREG-001`（`active`） |

（链接为相对根路径，前缀 `http://127.0.0.1:5174`。三条记录是**库内受管样本**：
`create_date=2026-09-07`、`create_uid=1`，**非本轮经 UI 新建**；本轮的写入范围只限设计器配置，
新建页只打开并断言，未提交业务记录，业务指纹未变。570 的第二菜单 509、575 的第二菜单 518
在本角色下被路由权威拒绝，见 -⑥。）

**本次闭环留下的变更集（如实登记，不清理）**：库内 `ui.business.config.change.set`
**487 superseded**、**488 published（回滚发布）**、**489 `ready` 未发布复核草稿**（`create_date=2026-09-19 02:45:58`
（UTC）、`expires_at=2026-09-19 10:45:58`，8 小时窗口；截至本轮仍为 `ready`）＋上一轮
**486 published（回滚）**／**485 superseded**／**483、484 discarded**。其中 489 是受管工具
**按既有设计留下**的复核草稿，会按 8 小时规则**阻断同目标的下一次运行**——如实登记，未手工清理。

**过程偏差**：闭环首两次运行 `EXIT=2` 失败，原因是校验工具把**必填**字段 `work_content` 当作隐藏目标
（产品按设计返回 `CONFIG_REQUIRED_FIELD_HIDDEN`，属**工具缺陷而非产品缺陷**）；改为非必填
`construction_part` 后通过。失败现场已恢复：483／484 为 `discarded`，7 个消费者解析结果未变（见 -③）。
该修正位于 `formal_form_designer_journey.mjs`／`formal_form_lowcode_loop.mjs`，**属工作树范围**（见 -⑧）。

#### 8.35.12-③ 隔离证据（浏览器级 ＋ 契约级）

**浏览器级**（同一 representative 套件，已发布态）：

- 隔离入口取**可达的兄弟入口** `570 机械台班登记 / menu 692`：`stages.isolation_page.status=passed`
  —— 已发布的 871 配置**未泄漏**到该入口（截图 `designer-outside-scope.png`）。
- 越界入口取 `562 方单 / menu 504`：`stages.outside_page.status=navigation_authority_denied`
  （`reason=NAVIGATION_AUTHORITY_DENIED`）—— 以**导航拒绝**登记，原因见 -⑥，**不作为隔离通过证据使用**。

**契约级**（只读，`/tmp/g09/config_ab.py` → `config_ab.txt`）：把已发布的 871 配置载体
（`view_orchestration:sc.labor.usage:form:action:871:view:1461:role:system_admin`，priority 100）
拼回全部 7 个消费者（871／562／563／561／570／851／575）的候选序列后，
`resolve_form_structure_governance` 的**解析结果六项（结构权威／呈现模式／章节数／字段数／标签／分组数）
与 baseline 逐项相同**。差异只出现在**候选载体列表**本身（多出那条已发布配置），
即：`changed=true` 由载体列表引起，**不由解析结构引起**。

**对照前后**：`/tmp/g09/iso_now.json`（闭环前）与 `/tmp/g09/iso_after.json`（闭环后）对 7 个 action 的
`carriers`／`authority`／`mode`／`sections`／`fields`／`labels` 输出 `IDENTICAL`。

**结论**：代表入口的合法配置闭环**不改变**其余消费者的解析结构；「同一入口发布 ＋ 共享视图隔离」
两个方向都有证据，其中浏览器级隔离落在 570（可达），562／563／851／509／518 一侧为**角色路由拒绝**（见 -⑥）。

#### 8.35.12-④ 8 个消费入口的影响面与验证方式（集中复核表）

| # | 正式入口 | 共享视图 | 是否在台账 | 本批配置退役影响 | 验证方式 |
|---|---|---|---|---|---|
| 1 | 871 劳务成本登记（menu 689） | 1461 `view_sc_labor_usage_form` | **是**（本批 3 条之一） | 154 `sc_labor_usage_form_sections_v1` 退役 | L2 17 测 ＋ **设计器闭环**（-②）＋ 只读代表面 create／record |
| 2 | 562 方单（menu 504） | 1461（同一 form arch） | **否（0 次）** | 同 154 | L2 **声明层**断言（`ENTRIES`／`SHARED_FORMS`／`RETIRED_SECTION_CARRIERS`）＋ 导航态实测为**拒绝** |
| 3 | 563 零星用工（menu 505） | 1461（同一 form arch） | **否（0 次）** | 同 154 | 同 562 |
| 4 | 570 机械台班登记（menu 692） | 1476 `view_sc_equipment_usage_form` | **是**（仅 menu 692） | 160 `sc_equipment_usage_form_sections_v1` 退役 | L2 ＋ **浏览器级隔离入口**（-③）＋ 只读代表面 create／record |
| 5 | 851 机械台班记录（menu 510） | 1476（同一 form arch） | **否** | 同 160 | 同 562 |
| 6 | 575 分包成本登记（menu 693） | 1491 `view_sc_subcontract_register_form` | **是**（仅 menu 693） | 156 `sc_subcontract_register_form_sections_v1` 退役 | L2 ＋ 只读代表面 create／record |
| 7 | 575 第二菜单 518 分包登记 | 1491（同一 form arch） | **否** | 同 156 | **无独立断言**（同一 action 的第二菜单载体） |
| 8 | **561 劳务用工**（`action_sc_labor_usage`） | **无可用 form 视图绑定**（`views=[('False','tree'),('False','form')]`，即模型默认视图） | **否** | **不受影响**：154 退役前后解析结果相同 | 只读实读 ＋ A／B（`/tmp/g09/iso_*.json`） |

**对照口径说明（避免两组「7」混用）**：

- §8.35.11 与本页 -③ 的 A／B 覆盖 **7 个 action**：871／562／563／**561**／570／851／575。
- §8.35.3 的「8 个消费入口」是**入口级**计数：871／562／563／570-692／851／575-693／**575-518** ＋ **561**。
- **第 8 个＝561 劳务用工**：**无菜单、无 form 视图绑定、无入口级契约**，`authority=entry_semantic_surface`
  来自它自己的模型级 p1-facts 回落（88）。它**不在**本批「共享原生 form arch」这条路上，
  其空章节是**自身既存缺口**（§8.35.2／§8.35.9）；A／B 证明 154 退役对它无影响。
- 因此「7 个保持不变」只覆盖**声明了 form 视图的入口**；把它当成「本组 8 个入口都已被同一条路径覆盖」
  是错的，561 必须单列。

#### 8.35.12-⑤ 台账与影响面口径更正

上一轮口头报告把「G13／G14 条目完整保留」与「未出现在 22 条中」并列表述，**该写法错误**，现按稳定条目标识更正：

| 对象 | `#498` 前（`cefeff1f`） | `#498` 后（`4b4a47fe`） | 当前工作树 | 结论 |
|---|---|---|---|---|
| 台账消费者条目 `entries` | **25** | **22** | **22** | 仅**删除 875／877／878**，**新增 0**；其余条目逐项未变 |
| `nextBatch.groups` 组索引 | **15**（G01–G15） | **15**（G01–G15） | **15** | G13／G14 **组名未缺失** |
| G13「日常合同与结算」actions | 687／876 | 687／876 | 687／876 | 条目 **687 日常合同**、**876 日常合同结算** 均在 22 条中 |
| G14「台账汇总与保证金」actions | 523／522／646／778 | 同左 | 同左 | 条目 **523 成本归集**、**522 项目盈亏分析**、**646 资金汇总**、**778 投标保证金** 均在 22 条中 |

**正确表述**：G13／G14 的**组名与消费者条目都未缺失**；被 `#498` 扣除的三条（875 班组借/扣款登记、
877 往来款登记、878 公司&项目退款）属于 **G08「上下文办理工作台」**，与 G13／G14 无关。

**本轮新发现（只登记，不改台账）**：`nextBatch.groups` 中 **G08 组索引仍列 `actions=[875,877,878]`**，
而对应消费者条目已随 `#498` 删除——**组索引与条目存在不一致**；同理 G09 组的 `legacyConfigurations`
仍列本批三条 `*_form_sections_v1` 退役载体。两者都属合入后台账审计的输入，本轮**不动台账**。

**核减口径（不变）**：台账 **22 → 19 仅作预期核减**；§8.35.3 已登记的旁路入口（562／563／851、509／518）
与新发现条目**单列补登**，**不与核减混算**；合入后按**实际三个退役消费者**独立审计。

#### 8.35.12-⑥ 路由拒绝口径更正（撤回「不计产品缺陷」）

原文（§8.35.6 旧版）把 5 条 `NAVIGATION_AUTHORITY_DENIED` 入口写成「角色边界／不计产品缺陷」。本轮核清后更正：

1. **该角色下未覆盖**：5 条被拒菜单（504／505／509／510／518）的持组都是
   `SC 基础 - 内部用户`（`group_sc_internal_user`）；现场身份 `sc_test_admin`（user 51）**确实持该组**，
   但其解析角色是 `system_admin`。
2. **角色面本身不含这些入口**：`system_admin` 的 role_surface 为
   `exposure_policy_declared=true`、`discover_installed_capabilities=true`、`menu_xmlids=[]`、
   `primary_menu_xmlids=[]`、`admin_menu_xmlids=[menu_ui_menu_config_policy_business_config]`；
   运行态 `build_route_authority` 在无交付 nav 时 **0 条 primary_actions**（仅有配置面 admin 路由）。
   即：**8 个消费入口在本角色下全部未进入路由权威**，871／570／575 的可达靠**直连路由**（页面级），
   而 5 条旁路／第二菜单入口以**菜单点击**触发，于是表现为拒绝。
3. **没有任何角色声明这 5 个菜单**：`ROLE_SURFACE_OVERRIDES`（P1 角色导航面）里没有
   `menu_sc_labor_usage_acceptance`／`menu_sc_labor_casual_acceptance`／`menu_sc_equipment_usage`／
   `menu_sc_equipment_shift_acceptance`／`menu_sc_subcontract_register` 任一项。
4. **但存在一份「用户确认」的菜单面基线把它们列为正式菜单**：
   `scripts/verify/baselines/user_confirmed_formal_menu_policy_62.json`
   （`locked_reason=user_confirmed_acceptance_surface_do_not_drift`，产品 `construction.standard`）
   的 `menu_groups[4]「construction.物资与分包」` 明确包含 **504 方单／505 零星用工／510 机械台班记录**；
   **509 设备使用登记／518 分包登记**不在该基线内，只出现在场景注册表／物资中心 provider
   （`smart_construction_scene` 的 `equipment.usage`／`subcontract.register` 场景映射）。

**更正后的登记口径**：这 5 条一律登记为**该角色（`system_admin`）下未覆盖**；
**撤回**「不计产品缺陷」定性。同时如实登记依据 4 的口径差异：
**运行态拒绝与一份用户确认的菜单面基线并不一致**，该差异的定性属**集中产品复核**范围，本批不自行结论，
也不据此改产品代码。562／563／851 的入口契约与共享原生树由 L2 的 `ENTRIES`／`SHARED_FORMS`／
`RETIRED_SECTION_CARRIERS` 断言覆盖（**声明层**，不是浏览器渲染结论）；**509／518 无独立断言**。

#### 8.35.12-⑦ 独立复核报告（绑定冻结候选 `6511134c…`）

报告正文：`tmp/uc4-g09-evidence/review-bound-6511134c.md`（与候选身份一起归档）。

**绑定身份**：候选 head `6511134c586320b8c07f1be8aa9d60ecb9d046d3`、tree `9eb84acb153080f35620066231a86c341452b194`、
基线 main `4b4a47fed43799019e7fa449084d87afbeb48de5`；PR #499 base/head 与候选一致，
`MERGEABLE`／`CLEAN`，**5 个 GitHub Actions 工作流的 `head_sha` 全部等于候选 head**（必检 9 pass／3 skipped／0 fail）；
评审线程与 review 均为 **0**；exact-head Quick 回执 `.git/codex/evidence/ci.local.quick/6511134c….json`
（`tree=9eb84acb…`）。

**结论：`REQUEST_CHANGES`**（详见该报告）：存在 1 条 **S1** 与 2 条 **S2** 级发现，均为**本次复核新提出**，
不涉及 S0；且**修复动作只能落在新的提交**上，故当前 head 不宜直接合并。未关闭问题：

- **S1**：**当前 head 仍带着本轮证据推翻的两处口径**（§8.35.6「不计产品缺陷」、§8.35.10「批次验收完成」）。
  更正只存在于**工作树**（未进入候选），因此 PR #499 头指针上的文本仍是错的。
- **S2**：**验收角色单一**。L4 只读代表面与本次闭环全部只用 `system_admin`（`sc_test_admin`），
  而 `.agent/context.yaml` 登记的验收身份是 `business_config_admin`；
  8 个消费入口在**登记验收角色**下的可达性**未被观测**。
  **本轮更新（见 8.35.13-③/-④）**：登记身份在本库无载体、无用户（`environment_defect`）；
  改用库内唯一 `business_config_admin`（`sc_business_admin`，id 6）走真实 `SystemInit` 路径实测，
  **871／570／575 在该角色下同为授权**（`DISCOVERED_PRIMARY_NAV`），
  且配置入口（737／749／110／727／736）为该角色 `ADMIN_ROUTE`。该项由"未观测"变为"已观测"，
  但仍**不构成入口级产品复核**；独立复核须在**新候选**上重新绑定。
- **S2**：**角色口径与用户确认菜单面基线不一致**（-⑥ 依据 4），尚无集中复核结论；
  原「不计产品缺陷」定性已撤回但**尚未在 head 上撤回**。
- **POST_MERGE_FOLLOWUP**：未发布草稿 489 的到期清理；台账 G08 组索引与条目不一致；
  561 无 form 视图绑定的既存缺口；`509／518` 无独立断言。

**声明**：该报告由**实施方自检**完成，**不等于独立第三方复核**，**不能用 Quick 回执替代**；
它绑定的是候选 `6511134c…`，若候选随后变化（见 -⑧），须重新绑定。
**该自检身份不因本轮推进而改变**：8.35.13 同样由实施方完成，**仍标注为自检**；
真正独立于实施者的复核见 8.35.13-⑦ 的收口顺序。

#### 8.35.12-⑧ 本批新增／受影响文件与「需重新冻结」说明

| 层 | 文件 | 状态 |
|---|---|---|
| P1 | `addons/smart_construction_core/data/labor_usage_form_productization_contract.xml` | 在候选内 |
| P1 | `addons/smart_construction_core/data/equipment_usage_form_productization_contract.xml` | 在候选内 |
| P1 | `addons/smart_construction_core/data/subcontract_register_settlement_form_productization_contract.xml` | 在候选内 |
| P1 | `addons/smart_construction_core/data/view_orchestration_form_section_contract_data.xml` | 在候选内（3 条模型级 sections 载体 `active=False`） |
| P1 | `addons/smart_construction_core/tests/test_usage_performance_native_lowcode.py`、`tests/__init__.py` | 在候选内（17 测） |
| P1 | `addons/smart_construction_core/views/core/{labor,equipment,subcontract}_management_views.xml` | 在候选内（6 个 `data-sc-anchor`） |
| P1 | `docs/engineering_convergence/complexity_budget_report.md`、本文件 | 在候选内 |
| P4 | `frontend/apps/web/scripts/formal_form_representative_journey.mjs`、`scripts/verify/local_dev_form_lowcode_scope.py` | 在候选内（只读注册 ＋ 只读探针） |
| **P4** | **`frontend/apps/web/scripts/formal_form_designer_journey.mjs`、`frontend/apps/web/scripts/formal_form_lowcode_loop.mjs`** | **仅在工作树**（-② 的闭环工具修正） |
| — | **本文件 §8.35.12／§8.35.13 与 §8.35.10 更正** | **仅在工作树** |
| P4 | `docs/ops/iterations/form_structure_compatibility_consumers_v1.json` | **仅在工作树**（8.35.13-⑥ 只加注：G08 `indexStatus=historical_source`、G09 `indexStatus=mixed_historical_and_current` ＋ 逐条 `legacyConfigurationStatus`；**count／entries 保持 22**） |

**因此**：候选 commit／PR #499 头指针**未变**（`6511134c…`），但**工作树已不等于候选**。
若要把本轮结论与闭环工具修正纳入交付，必须：`commit` → **重新冻结（clean HEAD ＋ 完整指纹）** →
**一次 exact-head Quick** → 重新归档 → `make pr.push`；**候选一旦改变，-⑦ 的复核须重新绑定**。
在上述动作**获得明确授权前**，不合并、不推送、不清理现场。

> 边界重申：**G09 自验与冻结门禁通过 ≠ 集中产品复核完成 ≠ 部署 ≠ 89 入口整体交付完成**。

### 8.35.13 有界复核轮二：身份、角色与入口核对（2026-09-19；已授权补验＋提交＋更新 PR，**未授权合并**）

授权口径：本轮**只**补集中复核提出的缺口（候选身份矛盾／两个 P4 工具修正的补验／登记角色与入口可达性／
台账索引定性／文档更正），并把结果提交进**新候选**。**不重复 Quick、不重跑浏览器矩阵、不扩展产品改动、
不发布／撤销／删除任何草稿**（含 489）、**不扣台账（保持 22）**、**不合并 #499**。

本轮 dirty 范围（相对候选 `6511134c…`）：两个 P4 工具（-②）、本文件、台账
`docs/ops/iterations/form_structure_compatibility_consumers_v1.json`（-⑥，仅加注不定量）。

#### 8.35.13-① 候选身份：Tree 矛盾已核清，撤回 `c1c8771a…`

上一轮对话记录中出现的 Tree 值 `c1c8771a…` **是错误记录**，以 Git 实际结果为准：

| 事实 | 命令 | 结果 |
|---|---|---|
| 候选 head | `git rev-parse HEAD` | `6511134c586320b8c07f1be8aa9d60ecb9d046d3` |
| 候选 tree | `git rev-parse HEAD^{tree}` | `9eb84acb153080f35620066231a86c341452b194` |
| commit 头部对象 | `git cat-file -p HEAD` 第 1 行 | `tree 9eb84acb153080f35620066231a86c341452b194` |
| index tree | `git write-tree` | 同值（无 staged 差异） |
| `c1c8771a` 命中 | `grep -r c1c8771a tmp/uc4-g09-evidence/ 归档目录 docs/` | **0 命中** |

归档 `archive-receipt.json` **只记 `candidateHead`，不含 tree**，因此不存在"归档绑定了另一个 tree"的事实。
**结论**：`c1c8771a…` 属**上一轮对话中的错误记录**，**任何绑定该值的复核不计入有效证据**；
本轮 §8.35.12-⑦ 及其归档绑定的 **`9eb84acb…` 正确**，-⑦ 候选身份部分**继续有效**（其余结论按 -⑧ 重新绑定）。

#### 8.35.13-② 两个 P4 脚本：测量缺口的修复、断言／草稿归属／清理行为审查与补验

**修改对象**（仅工作树，未进入 `6511134c…`）：
`frontend/apps/web/scripts/formal_form_designer_journey.mjs`（md5 `bb00f2b4149ed9daad1b192eb7e7e2fb`）、
`frontend/apps/web/scripts/formal_form_lowcode_loop.mjs`（md5 `81da4571961704b24dcff1830dc590c9`）。

**修复的测量缺口**（三者都不是产品语义）：

1. **隐藏样本选错字段**：原工具把**必填** `work_content` 当隐藏目标，产品按设计拒绝
   `CONFIG_REQUIRED_FIELD_HIDDEN`——测到的是守卫而不是迁移。改为隐藏**非必填** `construction_part`，
   并把重命名样本定为 `labor_team`（`受管班组`／`受管用工配置`）。**分类：validation_tool_defect**。
2. **用量组缺视觉序与业务面断言**：新增 `visual_order`（`configured_y=550 < displaced_y=636`，
   且未触碰的 `name／project_id／usage_type` 保持原生序）与发布后业务面断言
   （`data-form-section-target` 可点、隐藏字段不进 DOM、契约仍含隐藏事实）。**分类：覆盖率缺口**。
3. **越界入口不可达时的处理**：562 的可见性取决于角色，原工具要求其必须渲染；
   现改为**登记** `NAVIGATION_AUTHORITY_DENIED`（`stages.outside_page` **不再写 `passed`**），
   浏览器级隔离改在**同组可达兄弟入口 570/menu 692** 上做。**分类：validation_tool_defect**。

**断言／草稿归属／清理行为审查（逐行删除审计）**：`git diff -U0 | grep '^-'` 只有 **5 行**——
函数签名行、`identities` 首行、`if (invoiceTopic)` 分派行、末段 `report.stages.outside_page = …passed`
赋值行、调用处传参行。**没有任何既有断言被删除或放宽**；`drafts.delete(reviewOpen.data.token)`、
`designer_draft_ownership.mjs`、`designer_popup_readiness.mjs` 与
`scripts/verify/local_dev_form_lowcode_scope.py` **逐字节未改**（`git diff --stat HEAD -- <这些路径>` 为空）。

**补验（只跑受影响检查，非整批）**：

| 项 | 命令 | 结果 |
|---|---|---|
| 语法 | `node --check` ×2 | PASS |
| 设计器草稿保护单测 | `node …/designer_draft_ownership_test.mjs` | **PASS cases=9** |
| 弹窗就绪单测 | `node …/designer_popup_readiness_test.mjs` | **PASS cases=6** |
| 草稿作用域竞态单测 | `node …/business_config_draft_scope_race_test.mjs` | **PASS cases=9** |
| 既有闭环证据可否复用 | `designer-report.json` mtime `10:46:07` vs 工具 mtime `10:40／10:45` | **由修正后的工具产出**（含 `visual_order.displaced_y`、`isolation_page 570/692`、`outside_page.status=navigation_authority_denied`）→ 复用 |

**草稿保护实测**（只读）：489 `ready`（`write_date == create_date == 02:45:58`，**未被写入**）、
488 `published`、487 `superseded`、486 `published`、485 `superseded`、484／483 `discarded`、397 `ready`
——**全部保持原状**；本轮**未发布、未撤销、未删除**任何草稿。

#### 8.35.13-③ 登记验收身份实测：`business_config_admin` 在本库**不可用**（如实登记）

（**后续更正**：标题的「不可用」指的是**登记夹具载体**在 dev 库缺失——按 `.agent/context.yaml`
的 `acceptance_identity.fixture_only: true`，这是**预期**而非 dev 库缺陷，缺口在**验收运行时未 provision**；
库内另有退役残留账号 `sc_business_admin`（解析角色确为 `business_config_admin`）但无可用凭据，
不得用作验收身份；登记身份的合法取得路径是验收运行时的 `make acceptance.frontend.fixture`——见
§8.35.19-⑩。本节正文保留原文不回填。）

`.agent/context.yaml` 声明 `acceptance_identity`：`login=fixture_role_config_admin`、
`role=business_config_admin`、`carrier=smart_construction_acceptance_fixture.fe_user_config_admin`。

| 检查（`sc_dev_demo`，只读） | 结果 |
|---|---|
| 模块 `smart_construction_acceptance_fixture` | **installed** |
| xmlid `…fe_user_config_admin`（登记值） | **不存在** |
| xmlid `…fe_fe_config_admin`（历史拼写） | **不存在** |
| 用户 `fixture_role_config_admin` | **不存在** |
| 当前库内 `business_config_admin` 用户 | **`sc_business_admin`（id 6）** |

**结论**：登记的验收身份在 `sc_dev_demo` **无载体、无用户**，**无法按声明登录**；
本批此前的浏览器证据使用 `sc_test_admin`（`system_admin`），**与登记角色不同**（§8.35.12-⑦ S2 成立）。
**最小修正范围**：属**环境／验收夹具**问题（`environment_defect`），最小修正是补齐该模块的
fixture 用户与持组载体（P4／环境授权范围内），**不涉及产品代码**；本轮**不实施**，只登记。

#### 8.35.13-④ 角色 → 入口 可达性（走真实 `SystemInit` 代码路径，只读）

方法：在 `sc_dev_demo` 用真实 handler 路径（`SystemInitHandler` → `DeliveryEngine` →
`build_route_authority(role_surface, nav=…)`）对每个身份求**交付态导航权威**，再按 action／menu 命中。
（注：手工只构造 `role_surface` 而不带 `nav` 的探针**会低估**该权威——`system_admin` 实测 89 条，
不带 nav 的探针只给 6 条，故**以 handler 路径为准**。）

| 身份 | 角色 | `primary_actions` | 命中的本组 action |
|---|---|---|---|
| `sc_test_admin` | `system_admin` | 89 | **871／570／575** |
| `demo_full` | `business_full` | 86 | **871／570／575** |
| **`sc_business_admin`** | **`business_config_admin`（登记角色）** | **84** | **871／570／575** |
| `demo_role_project_manager`／`demo_role_project_user` | `project_member` | 7 | 无 |
| `demo_role_pm` | `pm` | 23 | 无 |
| `demo_role_finance`／`demo_finance` | `finance` | 44 | 无 |
| `demo_cost` | `cost` | 4 | 无 |
| `demo_role_owner` | `owner` | 5 | 无 |
| `demo_role_executive` | `executive` | 0 | 无 |
| `sc_contract_read`／`sc_material_read` | `restricted` | 0 | 无 |

**登记角色（`business_config_admin`）的配置入口**（同一路径，全部 `ADMIN_ROUTE` 可达）：
`737/431` 表单配置、`749/445` 字段管理、`110/432` 菜单配置、`727/424` 流程审批配置、`736/430` 人员档案。
三个模型的模型级 ACL 对该身份均为 `read／create／write／unlink = allowed`。

**结论**：三代表入口在**登记验收角色**下**同样是授权的**（`DISCOVERED_PRIMARY_NAV`），
因此 §8.35.12-⑦ 的 S2 中"登记角色可达性未观测"这一项**本轮已观测并消解**；
但**观测不等于入口级产品复核**——浏览器实检仍由产品方执行（§8.35.13-⑦）。

#### 8.35.13-⑤ 62 菜单文件 vs 89 入口范围：权威关系，以及 504／505／510 的预期角色与拒绝原因

| 维度 | 89 入口范围 | 62 菜单面 |
|---|---|---|
| 文件 | `scripts/verify/baselines/formal_business_product_menu_policy_v1.json` | `scripts/verify/baselines/user_confirmed_formal_menu_policy_62.json` |
| `locked_reason` | `full_formal_product_menu_scope_native_authority_do_not_drift` | `user_confirmed_acceptance_surface_do_not_drift` |
| `source` | runtime `ProductPolicyService … enforce_release=True` | `artifacts/menu_baseline/dev_locked_product_policy_62.json` |
| 规模 | **89 menus／89 capabilities**（`construction.standard`＋`preview`） | **60 menus／63 capabilities** |
| 分组 | 工作台／项目中心／合同中心／财务中心／成本中心／会计账务中心／税务中心／报表中心／行政中心／产品配置 | 施工管理／物资与分包／项目中心／合同中心／财务中心／资料证照／人事行政／基础资料／基础设置 |
| 与另一份重叠 | **overlap 15**、`89-only 74` | `62-only 45` |
| 性质 | **当前运行时产品菜单权威**（locked 契约、被 `locked_menu_policy_contract.py`／`product_policy_sync.py`／release guard 消费） | **用户确认的验收面快照**（历史来源；按 `do_not_drift` 锁定，但不是当前消费者集合） |

**本组三条正式入口**：`menu_sc_product_labor_cost_v1`／`menu_sc_product_equipment_shift_v1`／
`menu_sc_product_subcontract_cost_v1` 只出现在 **89** 的「项目中心」组——与运行时（menu 689／692／693）
一致，故**在交付导航权威内**（§8.35.13-④ 已实测）。

**504／505／510 的预期角色与拒绝原因**（本轮定性，**不是**"不计缺陷"）：

| 菜单 | xmlid | 62 基线（历史） | 89 基线 | 运行时父级（实测） | 原生持组 |
|---|---|---|---|---|---|
| 504 方单 | `menu_sc_labor_usage_acceptance` | ✅ 物资与分包，action **964**／menu **779** | ❌ 不在 | 项目中心/材料成本/劳务管理 | `SC 基础 - 内部用户` |
| 505 零星用工 | `menu_sc_labor_casual_acceptance` | ✅ 物资与分包，action **965**／menu **780** | ❌ 不在 | 项目中心/材料成本/劳务管理 | `SC 基础 - 内部用户` |
| 510 机械台班记录 | `menu_sc_equipment_shift_acceptance` | ✅ 物资与分包，action **968**／menu **782** | ❌ 不在 | 项目中心/材料成本/机械设备 | `SC 基础 - 内部用户` |
| 509 设备使用登记 | `menu_sc_equipment_usage` | ❌ 不在 | ❌ 不在 | 项目中心/材料成本/机械设备 | `SC 基础 - 内部用户` |
| 518 分包登记 | `menu_sc_subcontract_register` | ❌ 不在 | ❌ 不在 | 项目中心/材料成本/专业分包 | `SC 基础 - 内部用户` |

- **预期角色依据不存在于当前权威**：上述 5 条在**全部被测角色**（含 `system_admin`、`business_config_admin`、
  `business_full`）的交付导航权威中**均不出现**（既无 action 命中，也无 menu 命中）。
- **62 基线不能作为放宽依据**：62 给 504／505／510 的是 **964／965／968 与 menu 779／780／782**，
  与运行时 **562／563／851 与 menu 504／505／510** **不同**——62 是**另一运行时的验收面快照**，
  **不得因文件名含"用户确认"就据此放宽权限或反推当前应有入口**。
- **登记口径（按授权要求）**：这 5 条一律登记为**该角色下未覆盖**；**不写成通过，也不写成"非缺陷"**。
  运行态拒绝与"用户确认菜单面"的分歧属**集中产品复核**范围，本批不自行结论，也不据此改产品代码。

#### 8.35.13-⑥ 台账索引定性：G08 组索引＝历史来源；G09 旧配置清单＝混合（3 退役 ＋ 5 当前消费者）

本轮**只加注、不定量**（`count` 保持 **22**、`entries` 保持 **22**）：

- **G08「上下文办理工作台」组索引＝历史来源**：`actions=[875,877,878]` 是该组的**准备来源**，
  对应消费者条目已随 `#498` 从 `entries` 删除（25 → 22）；**不得再由该索引调度 G08**。
  其 `legacyConfigurations` 三条（`team_loan_deduction_workspace_form_v1` id 173／
  `current_account_workspace_form_v1` id 175／`company_project_refund_workspace_form_v1` id 176）
  在运行时仍是 `published／active`，但属**已完成批次的退役载体**，不是待办。
- **G09「用量与履约登记」旧配置清单＝混合**：8 条中**只有 3 条**
  （`sc_labor_usage_form_sections_v1` id 154、`sc_equipment_usage_form_sections_v1` id 160、
  `sc_subcontract_register_form_sections_v1` id 156，全部 `active=false`）是本组**实际退役载体**；
  其余 **5 条**（`*_register_productized_form_v1` 两条、`*_p1_form_business_facts_v1` 三条，
  均 `published／active=true`）**是当前消费者**，退役清单**不得**把它们当作退役对象。
- 两者都已在台账中以 `indexStatus`／`indexNote`／`legacyConfigurationStatus` 字段**显式标注**
  （本文件与台账同时进入新候选）。

**核减口径（不变）**：台账 **22 → 19 仅作预期核减**，合入后按**实际三个退役消费者**独立审计；
旁路／第二菜单入口（562／563／851、509／518）与补登条目**单列**，**不与核减混算**。

#### 8.35.13-⑦ 本轮边界、未做项与下一步

- **未做（保持未做）**：浏览器产品实检（**由产品方执行**，见 §8.35.12-② 的链接与现场身份；
  按 -④，登记角色 `business_config_admin` 亦可直达三入口）、集中产品复核结论、合并 #499、
  部署、89 入口整体交付、草稿 489 的到期清理、fixture 补齐、台账扣减提交、工作树／分支清理。
- **未改产品代码**：本轮无 P0–P3 变更；两个 P4 工具与台账／文档为本轮 dirty 范围，
  不存在需要按影响面补验的产品面变更。
- **随后执行**：`commit` → **重新冻结（clean HEAD ＋ 完整指纹）** → **一次新 HEAD 的
  `make ci.local.quick`** → **独立于实施者的复核**（原实施方自检**继续标注为自检，不改名**）→
  外部归档 → `make pr.push` 更新 #499。**合并仍需用户明确授权**；本轮候选身份与指纹在提交后
  写入 `tmp/uc4-g09-evidence/identity.json` 与归档回执，文档不预写自身提交 SHA。
- **风险**：登记验收身份缺失（-③）使"登记角色下的浏览器实检"当前**无法按声明执行**——
  这是本轮**最大残留风险**，也是产品复核前建议先补的环境项。

> 边界重申：**G09 自验与冻结门禁通过 ≠ 集中产品复核完成 ≠ 部署 ≠ 89 入口整体交付完成**；
> **更新 PR ≠ 产品验收通过**。

### 8.35.14 创建态可办理性修复：实施与定向补验（2026-09-19，**实施轮**；冻结／Quick／独立复核／归档／更新 #499 属收口轮，结果见 `tmp/uc4-g09-evidence/`，**未合并**）

**触发**：产品方实际浏览器复核（HEAD `291c6ee7…`）判定 **#499 不通过**——三个新建页可打开，
但"能办理"未被证明：871／570／575 的项目、班组、设备名称、工时、单价等呈只读事实，
项目为空而页面仍提供"提交"；另有三项表达问题（办理提示占业务章节、空"来源追溯"页签、
金额重复标签）。本轮据此实施，并按产品方两点调整执行：**不把所有只读必填字段判成错误**、
**不直接将 575 所有非草稿状态统一锁死**。

#### 8.35.14-① 偏差链定位：首次偏差在「配置策略」

按产品方要求对照 **原生声明 → 模型约束 → 配置策略 → 最终契约 → 控件** 逐层定位（以本地
`sc.labor.usage` 871 新建路由实测）：

| 层 | `usage_type` 的声明 | 结论 |
| --- | --- | --- |
| 原生声明 | `views/core/labor_management_views.xml`：`<field name="usage_type"/>`（本批前**从未**声明只读） | 允许录入 |
| 模型约束 | 本批前 `ScLaborUsage` **没有**事实守卫（`_FACT_IMMUTABLE_FIELDS` 与 `write()/unlink()` 由本批新增），后端对只读策略不作任何声明 | 与原生声明一样不阻断录入 |
| **配置策略** | `sc_labor_usage_p1_form_business_facts_v1`：`{'name':'usage_type','readonly':True}` | **无条件只读 ← 首次偏差（本批前已存在）** |
| 最终契约 | `layoutContract` 节点 `readonly=true`，而 `statusContract.widgetStatus` 为 `readonly=false／required=true` | 契约自相矛盾 |
| 控件 | `data-field-state="readonly"`，无 `input`／`select` 可驱动 | 新建页无法选择用工类型 |

**修复判据（不靠命名猜测）**：模型自己交付的草稿窗口就是"应由用户录入"的定义，原生 arch 用
`readonly="state != 'draft'"` 声明同一窗口。由此得到的跨层不变量为
**『配置策略只读集 ∩ 模型的 `_FACT_IMMUTABLE_FIELDS` ＝ ∅』**，并新增断言固定它
（`test_the_policy_never_locks_a_fact_the_model_treats_as_user_entered`：同时校验
「只读集与守卫集不相交」「`set(guard) - 原生窗口 = ∅`」「用户事实集 − 守卫集 ＝ 依据类事实」）。

#### 8.35.14-② P1 字段策略逐字段分类（15／21／17）

| 载体（模型） | 用户录入（移除无条件只读，交原生 arch 的 `state != 'draft'`） | 保留只读及其来源 |
| --- | --- | --- |
| 15（`sc.labor.usage`） | `project_id`／`usage_type`／`usage_date`／`contractor_id`／`labor_team`／`work_type`／`construction_part`／`work_content`／`worker_qty`／`work_hours`／`price_unit`／`note`／`attachment_ids` | `state`（工作流）／`name`（ir.sequence）／`create_date`（系统）／`recorder_id`（当前用户默认）／`settlement_state`（默认 unsettled）／`amount_total`（compute＋store） |
| 21（`sc.equipment.usage`） | `project_id`／`usage_date`／`supplier_id`／`equipment_name`／`specification`／`uom_text`／`usage_qty`／`usage_hours`／`price_unit`／`note`／`attachment_ids` | `state`／`name`／`create_date`／`recorder_id`／`amount`（compute） |
| 17（`sc.subcontract.register`） | `project_id`／`note`（**仅此两项**） | 镜像／计算／历史事实：`*_display` ×5、`sign_date`、`quantity_total`、`invoice_amount`／`paid_amount`／`unpaid_amount`／`uninvoiced_amount`、`message_attachment_count`、`source_created_by`／`source_created_at` |

**`usage_type` 归属用户录入的理由**：模型守卫集与原生 arch 都已把它声明为草稿窗口事实，且
871（方单）／562（零星用工）两条入口各自按 context 选择它；窗口内默认值只降低录入成本，
不改变归属。修复后 `layoutContract` 节点与 `project_id` 同形（`readonly=false` ＋
`field_compare` 修饰符），交付契约不再自相矛盾。

#### 8.35.14-③ 状态规则：先确定，再落实保护

- **570**：沿用既有草稿／非草稿规则（原生 arch ＋ `ScEquipmentUsage._FACT_IMMUTABLE_FIELDS`＋
  `write()/unlink()` 守卫），**本批未新增任何锁**。如实登记一处残留：570 的 arch 把
  `request_id` 纳入草稿窗口，而其保留守卫**未**冻结该事实，测试以显式期望
  （`residual == {"request_id"}`）固定该差异，供后续调度，不在本批扩大范围。
- **871**：按既有 `action_submit → action_confirm → action_cancel → action_reset_draft` 流程核对
  可编辑范围，由新增的 `_FACT_IMMUTABLE_FIELDS` ＋ `write()/unlink()` 在**离开草稿**（`state != 'draft'`）时
  拒绝事实写入，窗口取原生 arch 的同一口径；`note`／`attachment_ids` 为随时可补的依据类事实，**不**纳入守卫。
  `state` 本身不是业务事实，故另加与 570 同形的受控流转守卫（`_COST_SOURCE_STATE_CONTEXT_KEY` 令牌）：
  否则一次 `write({"state": "draft"})` 就能重新打开窗口，事实守卫形同装饰（见 §8.35.15）。
  同组 **570 的后端窗口仍更窄**（仅在 submitted／confirmed 拒绝），本批按授权不改它，差异以
  `test_the_equipment_usage_window_stays_narrower_and_is_pinned` 固定。
- **575**：`draft／active／closed` 及明细调整规则**仍未确定**，因此**本批不新增任何状态锁、不新增后端守卫**，
  以 `test_the_subcontract_register_post_registration_rule_stays_pending` 固定"无守卫"这一事实，
  防止后续批次把该文件误读为规则已定。**"已登记"不等于"不可修改"**。

#### 8.35.14-④ 同批表达修正

- **办理提示**：`processing_advisory` 由 `<page string="办理提示">` 改为 notebook 之后的
  `div.alert.alert-info[role=status][invisible="not processing_advisory"]`——不占业务章节／导航项，
  空提示整块不显示（不再显示占位 "—"）。三入口（570／575 原生视图，871 继承视图）同口径。
- **空"来源追溯"页签**：删除 871 的空 `<page string="来源追溯">`，并以
  `test_no_empty_notebook_page_is_declared` 固定"不得声明空页签／不得再出现 来源追溯 页签"。
- **金额重复标签**：按产品方要求**先查计算样式再动手**。实测 `.sc-visually-hidden` 生效
  （1×1px、`clip-path: inset(50%)`），截图证据 `shot-price_unit.png` 证实视觉上**只显示一次**
  "用工单价（值）"；`innerText` 中的重复是**无障碍隐藏标签的正常产物**。
  **结论：非缺陷，本批不改共享样式，不删除无障碍语义，不引入 TDesign 内部选择器。**

#### 8.35.14-⑤ 补"可办理"验证（新增，不删既有）

- **前端断言语义修正（P4）**：`assertRequiredFactsAreFillable` 由"必填 ∩ 可填"改为
  **「必需值是否可通过合法路径取得」**：每条必需事实须有 `path = control`（用户可驱动的控件）
  或 `carrier:<默认／计算／序列／工作流>`（只读呈现后由合法载体供给）。同时收紧两点——
  只允许**被策略判为只读**的事实使用 carrier 豁免（防止掩盖缺失控件），且声明的 carrier
  必须命中本面的必需事实。新增第三类交付控件形态 `SELECT_CONTROL`
  （`data-semantic-component="ScSelect"` ＋ `data-option-count` ＋ `data-readonly`，均属本仓设计系统标记），
  并新增 `revealFactOnNotebookPage`（页签承载的事实先切到其所在页再录入，不再记 `not-rendered`）。
- **未保存交互（opt-in `create_entry_probe`）**：三入口分别通过交付控件录入而未提交——
  871：日期经交付日历选取（`2026-09-19 → 2026-08-31`）、`usage_type` 经交付下拉选为「方单」、
  `labor_team`／`worker_qty`／`work_content` 键入；570：日期选取 ＋ `equipment_name`／
  `usage_location`／`operator_name`／`usage_qty`／`usage_hours`；575：`name`／`register_date`／
  `subcontract_scope`。**三项均 `skipped: []`**，且 wrapper 的 before/after 业务指纹一致、
  设计草稿（含 489）未被触碰。
- **后端回滚事务（SAVEPOINT＋ROLLBACK）**：**20/20 OK**——三个策略只读集与期望一致；
  871／570 合法创建、草稿内可改、提交后事实写入被拒、`unlink` 被拒、依据类事实仍可写；
  575 合法创建且无事实级守卫；回滚后三模型记录数不变。
- **既有断言全部保留**：字段完整性、结构同源、角色隔离、`readonly_values`（已确认记录不得暴露可编辑控件）、
  `relations`、`section_navigation` 等**未删除**，本轮只**新增**；受影响兄弟入口只补受影响反例，
  未重跑全系统矩阵。

#### 8.35.14-⑥ 分层验证结果（本轮 dirty 状态）

| 层 | 命令／证据 | 结果 |
| --- | --- | --- |
| L1 | `make ci.local.iteration` | **PASS**（`change_state=dirty coverage=L1_only receipt=none`） |
| L2 本类 | `TEST_TAGS='uc4_native_lowcode/smart_construction_core:TestUsagePerformanceNativeLowcode'` | **PASS 26 测 0 failed 0 error** |
| L2 全组 | `TEST_TAGS='uc4_native_lowcode/smart_construction_core'` | **PASS 123 测 0 failed 0 error** |
| L2 受影响 P0 | `TEST_TAGS='p0_state/smart_construction_core:TestP0StateClosure'` | **PASS 78 测 0 failed 0 error** |
| L3 回滚事务 | `tmp/g09-r4/g09_txn_verify.py`（SAVEPOINT＋ROLLBACK） | **20/20 OK**，回滚后记录数不变 |
| L4 代表面 | `FORM_LOWCODE_TOPIC=usage_performance FORM_LOWCODE_REPRESENTATIVE=1 make local.dev.form_lowcode.browser` | **PASS**：`ok=true`、`restored=true`、`business fingerprints unchanged`，三入口各 `required_facts_locked_by_body=[]` |
| L4 报告 | `artifacts/lowcode-form-loop/browser/representative-report-usage_performance.json` | 871／570／575 均 `passed`（create ＋ record 两路） |

#### 8.35.14-⑦ 未覆盖项与残留（如实登记，不缩范围）

- **路由拒绝仍在（本角色 `system_admin` 下未覆盖，不定性为"非缺陷"）**：562／563／851 走第二菜单
  （504／505／510）与 570／575 走二级菜单（509／518）时返回 `NAVIGATION_AUTHORITY_DENIED`；
  562 记录面另有 `empty_action_domain`（`domain_rows=0`，`business_rows=1`）。三者**均已在报告中显式登记**，
  其预期角色依据仍待**登记验收身份**（`business_config_admin` 在本库无载体、无用户，见 §8.35.13-③）。
- **many2one 选项提交未由门禁驱动**：`project_id` 的**可编辑关系控件**已在三入口实测
  （`editable=1`，`path=control`），合法创建亦由后端事务验证；但驱动其**选项列表点击**在本环境
  可达性不稳定（`retry` 后仍 actionability 超时），故**不纳入**门禁，留作独立探测项，
  避免把工具不稳伪装成产品通过。
- **`work_content` 页签承载**：该项已由 `revealFactOnNotebookPage` 纳入录制；若后续新增页签承载事实，
  同一路径自动覆盖。
- **会话身份**：本轮全部证据的实际会话用户为 `sc_test_admin`（uid 51，显示名 Demo-全能力，
  解析角色 `system_admin`）；"记录人：Demo-全能力"是**字段值**，不作为登录身份证据使用。

#### 8.35.14-⑧ 状态与边界

- **台账保持 22**：本轮**无扣减、无补登**；`22 → 19` 仍仅为**预期核减**，合入后按实际三个退役消费者
  独立审计，旁路入口与补登条目**单列，不与核减混算**。
- **实施轮边界**：本节只记实施轮。冻结、`make ci.local.quick`、独立复核、归档、`make pr.push` 属收口轮，
  其结果写入 `tmp/uc4-g09-evidence/`，不在本节改写；合并 #499、部署、G10、89 入口整体交付、
  草稿清理、工作树／分支清理在本轮均未做且未授权。
- **候选身份**：本节所述产品改动与工具改动产生于**工作树（dirty）**；收口轮冻结后的候选身份、完整指纹与
  归档回执写入 `tmp/uc4-g09-evidence/`，文档不预写自身提交 SHA。
- **证据位置**：收口轮之前在 `tmp/g09-r4/`（`upgrade.log`／`l1-iteration.log`／`l2-usage-class.log`／
  `l2-group.log`／`l2-p0-state.log`／`txn-verify.log`／`l4-representative.log`），属**历史来源、非本候选**；
  收口轮重绑的执行证据（`bound-*.log` 与 `bound-run-receipt.json`）落在 `tmp/uc4-g09-evidence/`。
- **收口轮顺序**：产品方放行（授权继续收口）→ 形成新候选 → **一次 exact-head Quick** →
  **独立于实施者的复核**（实施方自检继续标注为自检）→ 外部归档 → 受管更新 #499。
  产品验收结论以产品方登记为准，本文件不代述。

> 边界重申：**自验与定向补验通过 ≠ 集中产品复核完成 ≠ 部署 ≠ 89 入口整体交付完成**；
> **更新 PR ≠ 产品验收通过**。G09 主线集成不等于部署，也不等于 89 入口整体交付完成。

### 8.35.15 收口轮：独立复核（REQUEST_CHANGES）与 S1 修正（2026-09-19）

**触发**：冻结候选 `1ff5fac1` 的**独立于实施者**的只读复核（不使用实施轮结论作证据）判定
**REQUEST_CHANGES：1×S1＋4×S2**。S1 成立，已按影响范围修正并补验；S2 逐条纠正。原实施轮自检
仍标注为自检，**不**改名为独立复核。

#### 8.35.15-① S1（已修正）：事实守卫可被一次 `state` 写入绕过

- **缺陷**：871 的新事实守卫只在 `vals` 命中事实字段时才看状态，而 `state` 不是业务事实、不在
  `_FACT_IMMUTABLE_FIELDS` 内，且 `ScLaborUsage` 当时没有任何状态流转守卫。于是
  `write({"state": "draft"})` 可以合法地把已提交／已确认记录改回草稿，随后的
  `write({"worker_qty": …})` 必然通过——**事实守卫形同装饰**，与实施轮注释所称「口径与 570 一致」不符
  （570 用 `_COST_SOURCE_STATE_CONTEXT_KEY` 令牌拒绝同类写入）。本批自己的 L3 证据已把该绕过登记为
  通过步骤（`871:state_write_unguarded`），复核据此定位，属**实施轮遗留的正确性缺陷**。
- **修正**（P1 模型层，最小范围）：`ScLaborUsage` 增加与 570／材料验收同形的受控流转守卫——
  `state` 写入必须携带 `_COST_SOURCE_STATE_CONTEXT_KEY` 令牌（`_write_cost_source_state()`），
  四个业务动作（`action_submit`／`action_confirm`／`action_cancel`／`action_reset_draft`）改走该路径；
  令牌常量从 `equipment_management` 复用（与 `material_acceptance.py` 既有做法一致），不新建机制。
- **同批对齐的 S2**：事实窗口由 `state in ('submitted','confirmed')` 改为与原生 arch 同口径的
  `state != 'draft'`。原窗口比 arch 更宽，`cancel` 态在页面上只读、后端却可写。**570 的后端窗口
  仍更窄且按授权未改**，差异以 `test_the_equipment_usage_window_stays_narrower_and_is_pinned` 显式固定。
- **新增负例**：`test_the_labor_usage_state_is_only_advanced_by_a_business_action`（原始状态写入被拒，
  含 `{"state": "draft", "worker_qty": 9.0}` 混合写入；业务动作仍可推进；已确认不得迟取消）；
  既有守护用例扩展「取消后事实不可写／不可删 → 退回草稿后可改」的合法路径。

#### 8.35.15-② S2 逐条纠正（均已落地）

| S2 | 处置 |
| --- | --- |
| 归档目录跨 4 个 SHA（manifest 6511134c／identity 291c6ee7／代表面报告 6511134c／指纹另一 SHA） | 归档重建：同一冻结候选的 identity／manifest／summary／代表面报告／指纹；历史 SHA 工件移入 `history/` 保留，不删除 |
| `formal_form_lowcode_loop.mjs` 的 `dirty: true` 是硬编码字面量，运行报告无法绑定冻结身份 | P4 修正：wrapper 实测 `CANDIDATE_DIRTY`，渲染器读取之；未观测到即按 `dirty`（fail-closed），不再借用未观测的干净声明 |
| 文档把本提交才引入的 `_FACT_IMMUTABLE_FIELDS` 当作修复前既有事实（偏差链表「模型约束」行、契约注释） | 改为如实表述：本批前**没有**事实守卫；判据是原生 arch 的草稿窗口，后端守卫由本批补齐 |
| §8.35.10 的「待集中产品复核」与 §8.35.14-⑧ 的措辞不一致 | §8.35.10 状态行改写为指向 §8.35.14／§8.35.15 的当前事实；产品复核结论一律以产品方登记为准，文件不代述 |

#### 8.35.15-③ 复核已核验为真的部分（不改动）

13／11／2 项只读移除零新增；策略只读集 ∩ 守卫集 ＝ ∅；三个模型唯一只读载体仍是
`p1_form_business_facts_v1`（无第二发散、无越权扩大）；871 守卫多记录 fail-closed、
`note`／`attachment_ids` 豁免、`unlink` **比平台删除策略更严**（平台 `core_extension_policy_maps.py:860`
的 `DRAFT_DELETE_ALLOWED_STATES` 含 `cancel`，模型 `unlink()` 只放行 `draft`，故页面只读窗口与后端删除
窗口在此处并不相同，属**有意更严**而非"一致"）；P4 旧 `contradiction` 断言被新
`unobtainable` 严格包含、`assertReadonlyValues` 反加强、测试文件仅删 2 行 docstring；
575 保留的 14 项只读全为 compute／history；台账 22 未动；表达修正与生成报告刷新合法。

#### 8.35.15-④ 状态与边界

- **本轮未做且未授权**：合并 #499、部署、G10、89 入口整体交付、台账扣减／补登（保持 22）、
  草稿发布／撤销／删除、工作树与分支清理。
- **修正后的候选**必须重新冻结并**在**新身份上重跑一次 exact-head Quick，且独立复核必须绑定同一
  冻结身份——修正前的复核与 Quick 因 HEAD 漂移而失效。
- 边界重申：**独立复核通过 ≠ 产品验收通过**；**更新 PR ≠ 产品验收通过**。

### 8.35.16 收口轮二：冻结身份上的执行证据重绑与 S2 纠偏（2026-09-19）

**触发**：绑定 `f832feec` 的第三次独立（只读）复核判定 **REQUEST_CHANGES：1×S1＋3×S2**。S1 不涉及产品代码
正确性，而是「验证声明未绑定本候选」；本轮按最小处置在冻结身份上重绑执行证据，并逐条纠正 S2。

#### 8.35.16-① S1（已处置）：执行证据与候选身份重绑

- **缺口**：提交信息声称「L2 本类／全组／P0、L3 回滚事务、模块升级 PASS」，但仓内被保留的执行日志属**修正前
  代码**（用例数与提示文案可证），35 步验证器只有脚本、没有执行输出；唯一绑定身份的自动门禁 Quick 是**纯静态**
  门禁，不执行 Odoo 测试。
- **处置**：在同一冻结身份（同一 tree）上重跑 L1／L2 本类／L2 全组／L2 P0／L3 回滚事务／模块升级，逐项落盘到
  `tmp/uc4-g09-evidence/`；`bound-run-receipt.json` 记录每项的 `head`／`tree`／`git status`／命令／结论／
  日志 sha256。**用例数与通过数以该回执为准，本节不复述数字**。
- **口径**：`tmp/g09-r4/` 的旧日志降为**历史来源**，不再作为本候选证据；本文件不预写自身提交 SHA。

#### 8.35.16-② S2 逐条纠正

| S2 | 处置 |
| --- | --- |
| 871 `create()` 可在非草稿态落地事实（570 有守卫、871 没有） | **已修**：`create()` 增加与 570 同形的受控令牌守卫（`_COST_SOURCE_STATE_CONTEXT_KEY`），非 `draft` 入参一律拒绝；新增 `test_the_labor_usage_guard_covers_the_record_creation_entry`（零删除行） |
| 「对已确认记录 `copy()` 是第二条绕过路径」 | **前提部分不成立，已以运行时证据更正**：`state.copy is False`（871／570 两模型实测），`copy()` 不携带 `state`，已确认记录的副本落为**新草稿**且不改动源记录，不构成窗口绕过；该平台行为已在新断言中固定，避免后续调度误判 |
| 归档摘要重新使用被禁用的「批次验收完成」 | 归档 `summary.md` 状态行改为「自验与冻结门禁通过（本批范围）｜产品复核结论以产品方登记为准」 |
| 文档三处残留 | 已逐条更正：§8.35.10 口径段改为**历史记录**并以现行状态行为唯一口径；`:3955` 补平加粗配对；`unlink` 明确为**比平台删除策略更严**并给出 `core_extension_policy_maps.py:860` 依据 |

#### 8.35.16-③ 状态与边界

- **本轮未做且未授权**：合并 #499、部署、G10、89 入口整体交付、台账扣减／补登（保持 22）、
  草稿发布／撤销／删除、工作树／分支清理。
- **残留（如实登记，不缩范围）**：575 登记后修改规则待决（本批保持零守卫，「已登记」不等于不可修改）；
  570 后端窗口窄于 arch（`cancel` 态可写）且 `request_id` 未冻结；`workflow_contract_service.py` 的
  `reopen` 与模型不一致；562／563／851、570@509、575@518 在本角色下路由被拒**仅登记为未覆盖**，
  未定性为「非缺陷」。
- 边界重申：**更新 PR ≠ 产品验收通过**；**独立复核通过 ≠ 产品验收通过**；
  **G08 主线集成 ≠ 部署 ≠ 89 入口整体交付完成**。

### 8.35.17 批次 A：`退回草稿` 声明与后端规则对齐（R2）＋ 570 后端窗口对齐原生 arch（R1）（2026-09-19，**实施轮**；未冻结、未跑 Quick、未更新 #499）

**触发**：§8.35.13-⑦／§8.35.16-③ 登记的残留中，两项被产品方批准纳入批次 A（R1＝570 后端窗口，
R2＝工作流按钮声明）。本轮的判据只有一条：

> **声明了必然拒绝的动作，等于交付一个永远失败的按钮；隐藏模型唯一接受的入口，等于交付一条断路。**

`退回草稿` 映射 `action_reset_draft`，而本组全部模型都**只在「已取消」**接受它。因此「已提交／已登记」
声明它 = 死按钮，「已取消」不声明它 = 没有合法回路。同一动作在**两个面**上被渲染，两处都要与模型的
前置条件一致：原生 arch 的 header（Odoo 原生表单）与工作流契约 `state_actions`（Vue 表单经
`describe_record()` 读取）。

#### 8.35.17-① R2 契约层：7 个模型的声明收口

- `_submit_confirm_profiles`（服务 6 个模型：`sc.equipment.settlement`／`sc.equipment.usage`／
  `sc.labor.settlement`／`sc.labor.usage`／`sc.material.settlement`／`sc.subcontract.settlement`）与
  `sc.subcontract.register` 专用 profile：`submitted`／`active` 去掉 `reopen`，新增
  `cancel: ["reopen"]`，`label_by_action` 补 `reopen: 退回草稿`。
- **口径来源**：这不是新发明的规则，而是同文件 `_in_progress_done_profiles` 早已使用的写法
  （`in_progress` 不声明 `reopen`，`cancel: ["reopen"]`），也是 871 在上一批对齐后的事实行为。
- **未决定的事仍未决定**：575 的登记后修改规则保持待决（见 §8.35.16-③）。本项只把**声明**对齐到
  「已交付规则」（模型 + arch 本来就已经是 `cancel`），未新增任何锁。

#### 8.35.17-② R2 原生 arch 层：同一条动作的 header 表达式

| 表单 | 模型 | 改前 | 改后 |
| --- | --- | --- | --- |
| `view_sc_labor_usage_form`（871／562／563） | `sc.labor.usage` | `state != 'submitted'` | `state != 'cancel'` |
| `view_sc_labor_settlement_form` | `sc.labor.settlement` | `state != 'submitted'` | `state != 'cancel'` |
| `view_sc_equipment_settlement_form` | `sc.equipment.settlement` | `state != 'submitted'` | `state != 'cancel'` |
| `view_sc_material_settlement_form` | `sc.material.settlement` | `state != 'submitted'` | `state != 'cancel'` |
| `view_sc_subcontract_settlement_form` | `sc.subcontract.settlement` | `state != 'submitted'` | `state != 'cancel'` |

570（`view_sc_equipment_usage_form`）与 575（`view_sc_subcontract_register_form`）的该按钮**已经是**
`state != 'cancel'`，本批未改。各 header 的 `action_cancel` 为 `state in ('confirmed','cancel')` 取反，
即草稿／已提交可见，因此交付的回路是 **草稿／已提交 → 取消 → 退回草稿 → 草稿**，无断路。

#### 8.35.17-③ R1：570 后端事实窗口对齐原生 arch

- 权威判据是**原生声明**：`view_sc_equipment_usage_form` 对全部交付事实声明 `readonly="state != 'draft'"`。
- `_FACT_IMMUTABLE_FIELDS` 纳入 `request_id`（arch 早已声明它在草稿窗口内，模型集合此前漏列，即
  §8.35.13-② 记录的残留），`write()` 事实守卫与 `unlink()` 由 `state in ('submitted','confirmed')`
  改为 `state != 'draft'`；文案与 871 同形（`非草稿状态的机械台班事实不可…`）。
  由此 `set(_FACT_IMMUTABLE_FIELDS)` 与 arch 的草稿窗口字段集**逐字段相等**，原残留集由 `{"request_id"}`
  变为 `∅`。
- `unlink` 仍**严于**平台删除策略（`core_extension_policy_maps.py:860` 的 `DRAFT_DELETE_ALLOWED_STATES`
  含 `cancel`，模型只放行 `draft`），与 871 一致。

#### 8.35.17-④ 断言：新增 2 个，翻转 2 个（零删除）

- 新增 `test_the_reset_to_draft_action_is_declared_where_it_runs`（本组）：871／570／575 三个入口逐一
  比对 arch 表达式与契约声明，并把声明的动作**实际执行**（`已提交`／`已登记` 无 `reopen`；`已取消`
  有 `reopen`、`enabled=True`、`method=action_reset_draft`，调用后回到草稿）。
- 新增 `test_reset_to_draft_is_declared_where_the_model_accepts_it`（契约类）：7 个模型逐一断言
  `{state | "reopen" in state_actions[state]} == {'cancel'}` 且 arch 表达式为 `state != 'cancel'`。
- 翻转（原为「固定差异」，现改为「固定已对齐」）：`test_the_equipment_usage_window_matches_the_native_arch`
  （原 `…_stays_narrower_and_is_pinned`）与 `test_the_policy_never_locks_a_fact_the_model_treats_as_user_entered`
  的残留断言（`{"request_id"}` → `set()`）。字段完整性、结构同源、角色隔离、575 待决等断言全部保留。
  （**后续**：§8.35.18-④ 把 `575 待决` 的 pin 改写为「规则已定义」的冻结窗口断言，其余三类保留不变。）

#### 8.35.17-⑤ 分层验证（本轮 dirty 工作树，未绑定冻结身份）

| 层 | 命令标签 | 结果 |
| --- | --- | --- |
| L2 本类 | `uc4_native_lowcode/smart_construction_core:TestUsagePerformanceNativeLowcode` | **30 测，0 failed／0 error**（改前 29 ＋ 新增 1） |
| L2 全组 | `uc4_native_lowcode/smart_construction_core` | **127 测，0 failed／0 error** |
| L2 P0 | `p0_state/smart_construction_core:TestP0StateClosure` | **78 测，0 failed／0 error**（与改前同） |
| L3 回滚事务 | `tmp/g09-r5/g09_txn_verify.py` | **45／45 步通过**（原 40 步；570 残留步骤翻转为「已取消事实写被拒／来源链接写被拒／删除被拒／退回草稿后可写」，残留 0） |
| 模块升级 | `local.dev.upgrade`（`CODEX_NEED_UPGRADE=1`） | PASS（含 `verify_authority`） |

- `test.safe` 是 **no upgrade** 运行：视图 arch 存在库内，故本轮先升级模块再跑 L2，否则 arch 断言会读到旧表达式
  （本轮实测即因此先红后绿）。
- 契约类 `workflow_contract_backend` 在本库有 **8 项既有失败**（`sc.partner.import.review` 不在 registry、
  `sc.expense.claim` 要求已归属公司的有效项目、`sc.receipt.income` 收款归集关系不可见等）。已用**未改工作树**的
  同标签基线运行证明与本次改动无关：基线 `1 failed, 7 error(s) of 24 tests`，本批 `1 failed, 7 error(s) of 25 tests`，
  **失败集合逐项一致**（本批新增的那 1 测通过）。

#### 8.35.17-⑥ 残留登记（**未**纳入本批，如实登记，不缩范围）

同一「模型只在 `cancel` 接受、arch 只在 `submitted` 显示」的死按钮模式，在**未受工作流契约治理**的表单上
仍然存在（先只读核对了各模型 `action_reset_draft` 的前置条件）：

| 表单 | 模型 | 模型接受状态 | arch 可见状态 | 判定 |
| --- | --- | --- | --- | --- |
| `view_sc_equipment_plan_form` | `sc.equipment.plan` | `cancel` | 仅 `submitted` | 死按钮＋无回路 |
| `view_sc_equipment_request_form` | `sc.equipment.request` | `cancel` | 仅 `submitted` | 死按钮＋无回路 |
| `view_sc_attendance_checkin_form` | `sc.attendance.checkin` | `cancel` | 仅 `submitted` | 死按钮＋无回路 |
| `view_sc_subcontract_plan_form` | `sc.subcontract.plan` | `cancel` | 仅 `submitted` | 死按钮＋无回路 |
| `view_sc_subcontract_request_form` | `sc.subcontract.request` | `cancel` | 仅 `submitted` | 死按钮＋无回路 |
| `view_sc_material_purchase_request_form` | `sc.material.purchase.request` | `cancel` | 仅 `submitted` | 死按钮＋无回路 |
| `view_sc_material_inbound_form` | `sc.material.inbound` | `cancel` | 仅 `submitted` | 死按钮＋无回路 |
| `view_sc_material_outbound_form` | `sc.material.outbound` | `cancel` | 仅 `submitted` | 死按钮＋无回路 |
| `view_sc_material_rfq_form` | `sc.material.rfq` | `cancel` | 仅 `submitted` | 死按钮＋无回路 |
| `view_sc_material_rental_plan_form` | `sc.material.rental.plan` | `cancel` | 仅 `submitted` | 死按钮＋无回路 |
| `view_sc_subcontract_price_form` | `sc.subcontract.price` | `inactive` | `!= inactive`（唯一合法态被隐藏） | 死按钮＋无回路 |
| `view_sc_equipment_price_form` / `view_sc_labor_price_form` | `sc.equipment.price`／`sc.labor.price` | `inactive` | `!= draft` | 非合法态可见（价格启停语义，**不可**按 `cancel` 口径改） |

- 这些表单纯属各自模块批次，且**不**由 `workflow_contract_service.py` 声明，纳入本批会扩出可验证边界
  （10＋表单跨 5 个模块，需各自代表面验证）。建议作为**批次 C** 单独立项，逐表单核对前置条件后同形修正。
- 语义**不同**的同名按钮（`sc.plan` 的 `state == 'draft'`、材料验收 `not in ('submitted','rejected')`、
  价格类启停）必须逐个核对模型前置，**不得**批量套用 `cancel` 口径。

#### 8.35.17-⑦ 状态与边界

- **本轮未做且未授权**：冻结候选、`ci.local.quick`、独立复核、外部归档、更新／合并 #499、部署、G10、
  89 入口整体交付、台账扣减／补登（**保持 22**）、草稿发布／撤销／删除、工作树／分支清理。
- **待产品方决断**（**已于 §8.35.18 决断**）：575 `closed` 的 (b1) 提供留痕「重新打开」／(b2) 永久终态——
  §8.35.17 本批零改动；§8.35.18 按 (b1) 实施，并把本节 `575 待决` 的 pin 改写为「规则已定义」。
- 现场：开发库 `sc_dev_demo` 已升级到本轮工作树（arch 变更已落库），三入口可直接浏览器复核；
  **实际浏览器产品复核未做**，故本轮只到「实施＋定向补验」。
- 边界重申：**更新 PR ≠ 产品验收通过**；**独立复核通过 ≠ 产品验收通过**；
  **G08 主线集成 ≠ 部署 ≠ 89 入口整体交付完成**。

### 8.35.18 批次 B：575 `已关闭` 冻结窗口与受控「重新打开」（2026-09-19，**实施轮**；未冻结、未跑 Quick、未更新 #499）

本批次关闭 §8.35.17-⑦ 留下的产品决断：575（`sc.subcontract.register`）在 `已关闭`(`closed`) 之后
**冻结用户录入的登记事实与明细**，并给出受控动作「重新打开」回到 `已登记`(`active`)。之所以取
「受控撤回」而不是「永久终态」：`sc.subcontract.settlement._check_business_anchor`
（`models/core/subcontract_management.py:1427/1433`）接受来源登记 `state in ('active','closed')`，
即 `已关闭` 仍是分包结算的合法来源，因此冻结必须可撤回；但撤回不得改写已被结算引用的事实。

#### 8.35.18-① 冻结窗口：只冻 `closed`，`已登记` 保持可调整

- `models/core/subcontract_management.py:364` 新增类级 `_FACT_IMMUTABLE_FIELDS`（11 项：`project_id`／
  `request_id`／`contract_id`／`register_date`／`start_date`／`end_date`／`subcontract_scope`／
  `subcontractor_id`／`responsible_id`／`currency_id`／`line_ids`）；`:369` `_FACT_IMMUTABLE_STATES = ("closed",)`。
- `:501 write()` 增加后端冻结守卫：`locked = self._FACT_IMMUTABLE_FIELDS & set(vals)` 命中且记录在冻结状态时
  抛 `UserError("已关闭的分包登记不可修改登记事实或明细；请先执行「重新打开」回到已登记状态。")`；
  `sc_skip_subcontract_contract_authority` 内部上下文放行（合同一致性回写）。
  **更正（见 §8.35.20-㉟）**：该放行键当时是**请求上下文可伪造的布尔键**，且放行判定排在冻结判定之前，
  因此「已关闭」冻结窗口可被客户端自带的同名键掀开；现已改为进程内令牌，且冻结判定先于放行判定。
- **明确不采用「所有非草稿状态一律锁死」**：`已登记` 仍是可调整窗口（用户显式排除该口径）。该窗口内的
  事实调整由既有累计数量／累计金额／合同范围／结算授权校验把关（`:986-1170`、`:1266-1400`），
  而不是由状态名代替业务规则。
- `note`／`attachment_ids`／`management_note`／`name` 不入冻结集：记录依据与管理要求，关闭后仍可补写。

#### 8.35.18-② 「重新打开」是独立契约身份，不复用 `reopen`

平台既有 `reopen` 的语义固定为「重置为草稿」（`cancel -> draft`，`action_reset_draft`，标签「退回草稿」，
见 §8.35.17-①），其目标状态、方法与标签都与 575 需要的 `closed -> active` 不同。若复用会让同一动作键在
同一模型上出现两种目标状态，因此另立身份并在契约测试中双向固定：

- `models/support/workflow_contract_service.py:895` `ACTIONS` 新增
  `"reactivate": {"label": "重新打开", "intent": "server.object", "kind": "transition"}`。
- 同文件 `:640` / `:647` / `:654`：`sc.subcontract.register` 的 profile 只在 `closed` 声明 `reactivate`，
  映射方法 `action_reopen`、标签「重新打开」；`reopen` 在该模型的声明未被改动。
- `models/core/subcontract_management.py:725 action_reopen()`：要求 `closed` 入参（否则拒绝）；
  登记明细一旦被结算引用（`line_ids.mapped("settlement_line_ids.settlement_id")` 非空）即拒绝重开，
  指向结算调整——与明细 `unlink()` 的保护同形，保证结算依据不被改写。
- `views/core/subcontract_management_views.xml:276`：header 新增
  `<button name="action_reopen" string="重新打开" type="object" class="btn-primary" invisible="state != 'closed'" groups="smart_construction_core.group_sc_cap_project_manager"/>`。

#### 8.35.18-③ arch 只读表达式：状态窗口，不是字段级全锁

- `views/core/subcontract_management_views.xml:291-297`（`project_id`／`request_id`／`contract_id`／
  `register_date`／`start_date`／`end_date`／`subcontract_scope`）、`:300-302`
  （`subcontractor_id`／`responsible_id`／`currency_id`）、`:308`（`line_ids`）统一为 `readonly="state == 'closed'"`。
- `processing_advisory` 保持 `readonly="1"`（系统生成的办理提示），`note`／附件不带状态表达式。
- 与 §8.35.17-① 同口径：移除的是「用户录入字段的无条件只读」，**保留**计算、镜像与系统生成字段的约束；
  原生视图负责交互约束，事实不可改由 `write()` 守卫承担（后端为事实权威）。

#### 8.35.18-④ 断言：新增 1 个、改写 1 个、改写 2 个既有断言，**零删除**

- 改写 `tests/test_usage_performance_native_lowcode.py:1088`
  `test_the_subcontract_register_freezes_only_after_closing`（原 `…_post_registration_rule_stays_pending`）：
  断言 `_FACT_IMMUTABLE_STATES == ("closed",)`；草稿可写；`确认登记`→`已登记` 后事实与明细仍可写；
  `关闭`→`已关闭` 后事实／明细／锚点写入被拒而 `note` 可写；`重新打开` 回 `已登记` 后事实可写；
  非 `closed` 调 `action_reopen` 被拒；构造结算引用后再 `关闭` 并断言 `action_reopen` 被拒。
  ⇒ 原「规则待决」pin **记为「规则已定义」**：575 不再是「无守卫」表述，而是有明确冻结状态、撤回路径与
  结算引用保护。
- `:604` 新增类常量 `FACT_FREEZE_EXPRESSION`（871／570 `state != 'draft'`；575 `state == 'closed'`）；
  `:733` 与 `:781` 两个既有断言改为按该表逐模型核对（`compared == 3`），并新增
  `set(USER_SUPPLIED_FACTS[model]) - set(guard) == DRAFT_WINDOW_EXEMPT_FACTS ∩ USER_SUPPLIED_FACTS[model]`。
- 新增 `tests/test_workflow_contract_backend.py:91` `test_the_subcontract_register_reopens_only_from_closed`：
  契约层（`reactivate` 仅在 `closed` 声明、method／label 正确、`reopen` 身份未被改动）＋ arch 层
  （按钮唯一、`invisible="state != 'closed'"`、`groups` 含 `group_sc_cap_project_manager`）＋ 运行态
  （`draft`／`active` 不出现 `reactivate`；`closed` 出现且不含 `reopen`，实际执行回 `active`）。
- 字段完整性、结构同源、角色隔离、可办理性（`create` 窗口）断言**全部保留**。

#### 8.35.18-⑤ 分层验证（本轮 dirty 工作树，未绑定冻结身份）

| 层 | 命令／标签 | 结果 |
| --- | --- | --- |
| L1 升级 | `local.dev.upgrade`（`CODEX_NEED_UPGRADE=1`） | PASS（78 modules，`[local.dev.ready] PASS`） |
| L2 本组 | `uc4_native_lowcode/smart_construction_core:TestUsagePerformanceNativeLowcode` | **30 测，0 failed／0 error** |
| L2 成本登记 | `subcontract_cost_registration/smart_construction_core:TestSubcontractCostRegistration` | **1 测，0 failed／0 error** |
| L2 契约类 | `workflow_contract_backend/smart_construction_core:TestWorkflowContractBackend` | 26 测：**1 failed／7 error，与未改工作树基线逐项一致**（新增 1 测通过） |
| L2 P0 | `p0_state/smart_construction_core:TestP0StateClosure` | **78 测，0 failed／0 error** |
| L3 回滚事务 | `tmp/uc4-g09-batchB/g09_txn_verify.py` | **58／58 步通过**（含 17 条 575 新增步骤；rollback 后记录数 0） |
| L4 只读契约探针 | `tmp/uc4-g09-batchB/live-contract-probe.py` | `draft→[确认登记,取消]`／`active→[关闭,取消]`／`closed→[重新打开]`／重开回 `active`；无残留 |

- 契约类失败的 8 项为本库既有环境性失败（`sc.partner.import.review` 不在 registry、费用／扣款单据要求
  已归属公司的有效项目等），已用未改工作树同标签基线（`1 failed／7 error of 24 tests`）证明与本批无关。
- `test_product_reports.py` 的 1 项错误同为既有（夹具以 `state="confirmed"` 植入状态，被批次 A 的 S1 守卫
  拒绝；该文件本批未改）。

#### 8.35.18-⑥ 前端消费面验证（本批新增证据，只读）

前一轮的 L4 探针只覆盖了契约层的动作集合，未覆盖 **前端执行适配器**。本轮补做：把真实
`ui.contract.v2` 交付契约（3 个状态 × 系统身份／项目负责人身份 ＋ 重开后，共 8 份，
`tmp/uc4-g09-batchB/v2-contract/`，SAVEPOINT/ROLLBACK 无残留）喂给真实前端 presenter：

```
decodeContractV2Snapshot → createContractV2Store → presentContractV2Form('edit')
  → collectCanonicalFormActions / buildContractFormActions
  → resolveCanonicalFormActionExecution / validateCanonicalFormActionExecutors
```

| 交付状态 | 解码 | 渲染器 reopen 引用 | 可见 | 执行适配器 | 原生 modifier | workflow 行 |
| --- | --- | --- | --- | --- | --- | --- |
| `draft` | ok | 0 | 0 | n/a | 隐藏 | `submit`／`cancel` |
| `active` | ok | 0 | 0 | n/a | 隐藏 | `complete`／`cancel` |
| `closed` | ok | 1 | 1（`enabled=true`） | `contract-action` | 可见 | `reactivate` |
| 重开后（`active`） | ok | 0 | 0 | n/a | 隐藏 | `complete`／`cancel` |

- `closed` 交付契约上 `validateCanonicalFormActionExecutors` 返回 `null`：
  「重新打开」**不**触发 `CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING`（新增动作键的已知风险点已排除）。
- 非 `closed`：`statusContract.buttonStatus` 对该后端身份给出 `visible=false` /
  `ACTION_NOT_VISIBLE_IN_STATE`，原生 modifier `state != 'closed'` 求值为真（隐藏）。
- 正对照：把原生 `native_locator` 换成未绑定的 `button[9]` 时解析立即返回
  `CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING` ⇒ 上述断言非空洞。
- 证据：`tmp/uc4-g09-batchB/consume-probe.ts`（探针）、`consume-probe.log`（结果）、
  `v2-contract-dump.py` / `v2-contract-dump.log`（契约投影），见 `tmp/uc4-g09-batchB/README.md`。

#### 8.35.18-⑦ 残留登记（**未**纳入本批，如实登记，不缩范围）

| 项 | 事实 | 最小修正范围 | 本批判定 |
| --- | --- | --- | --- |
| `575:state_write_bypass` | 「已关闭且有有效结算引用」的登记上 `write({"state": "active"})` 仍被接受，与 871／570 的 S1 守卫同类缺口 | P1 策略把 575 `state` 设为只读 ＋ `write()`／`create()` 状态守卫，并改掉以 `state=` 植入状态的既有夹具 | **未修**，需在下一轮带夹具改造一起做 |
| 前端 transition 注册表 | `workflowActionAvailability.ts` 的 `knownKeys`／`workflowActionMethodAliases` 未登记 `reactivate`／`action_reopen`，非 `closed` 状态下可用性解析降级为 `unmanaged`（`isWorkflowTransitionMethod=false`、`shouldShowWorkflowAction=true`） | 在该注册表补 `reactivate` 键与 `action_reopen` 别名 | **未改**：该状态下的实际拦截来自交付状态契约＋原生 modifier，后端仍拒绝非法转移（fail-closed）；是否统一语义待产品方决定 |
| `test_product_reports.py` | 既有失败：夹具以 `state="confirmed"` 植入状态被 S1 守卫拒绝 | 改夹具为执行合法转移 | 与本批无关，如实登记 |

（**后续**：§8.35.19-⑧ 记该三项的最新状态——`575:state_write_bypass` 已关闭、`test_product_reports.py` 已修正；
前端 transition 注册表仍未改。本表保留批次 B 当时的判定，不回填。）

**产品口径待确认（非缺陷，取保守口径）**：`action_reopen` 在**任一**登记明细已被结算引用时即拒绝重开，
即使本次想改的是未被引用的其它明细。之所以取该口径：重开动作的用途是「重新取得可编辑性」，后端无法
从状态转移本身判断意图，而平台对结算引用明细的既有保护（`line.unlink()` 拒绝删除）已是「引用即不可改」
的同形口径，故选择 fail-closed 并把出口指向结算调整。若产品方要求「可在被引用记录上重开、但被引用明细
仍不可改」，则需改为**逐行冻结**（`settlement_line_ids` 命中的 `line_ids` 行级只读＋行级写入守卫），
属下一轮范围。

#### 8.35.18-⑧ 状态与边界

- **本轮未做且未授权**：冻结候选、`ci.local.quick`、独立复核、外部归档、更新／合并 #499、部署、G10、
  89 入口整体交付、台账扣减／补登（**保持 22**）、草稿发布／撤销／删除、工作树／分支清理、浏览器矩阵重跑。
- 现场：开发库 `sc_dev_demo` 已升级到本轮工作树，575 三个状态可在浏览器直接复核
  （重点：`已关闭` 态事实只读、「重新打开」按钮、有结算引用时被拒）。
- 边界重申：**更新 PR ≠ 产品验收通过**；**独立复核通过 ≠ 产品验收通过**；
  **G08 主线集成 ≠ 部署 ≠ 89 入口整体交付完成**。

### 8.35.19 批次 C：575 状态写入窗口收口（受控动作之外不可写状态）（2026-09-19，**实施轮**；未冻结、未跑 Quick、未更新 #499）

本批次关闭 §8.35.18-⑦ 登记的 `575:state_write_bypass`。批次 B 交付了 `已关闭` 的事实冻结与受控
「重新打开」，但状态本身仍是可写字段：`write({"state": "active"})` 可以直接掀开冻结窗口，绕过
`action_reopen()` 的三重前置（项目负责人权限、`closed` 入参、结算引用检查），也绕过
`action_register()`／`action_close()` 的业务锚点与明细校验。缺口与 871／570 在 S1 修正前属同一类。

#### 8.35.19-① `state` 不是可填字段：P1 载体与 871／570 对齐

- `data/p1_daily_business_form_orchestration_contract_data.xml`：575 的交付载体
  `sc_subcontract_register_p1_form_business_facts_v1` 的 form `fields` 首位新增
  `{'name': 'state', 'sequence': 10, 'readonly': True}`。871／570 的同一载体早已有此声明，575 是遗漏。
- 交付契约的**三处投影**（布局节点 `children[*]`、`fieldInfo` 描述符、`widgetList[*].fieldDescriptor`）
  在 8 份契约（4 状态 × 系统身份／项目负责人身份）中由 `readonly=false` 全部转为 `true`
  ⇒ `collectWritableValues` 的 `!node.readonly` 过滤与 `nativeStatusbar.readonly`
  两条保存路径都不会再把 `state` 带进保存载荷（见本批 §8.35.19-⑥）。
- 产品含义：575 的状态条与 871／570 一样退化为展示，状态推进只走 header 动作／workflow 行；
  这是「状态由受控业务动作推进」在交付面上的一致表达，不是把表单锁死。

#### 8.35.19-② 后端状态守卫：复用同一个 token，未新造机制

- `models/core/subcontract_management.py` 顶部新增 `from .equipment_management import
  _COST_SOURCE_STATE_CONTEXT_KEY, _COST_SOURCE_STATE_TOKEN`（S1 既有机制，871／570／材料验收共用）。
- `:470 create()`：非 token 上下文且 `any(vals.get("state", "draft") != "draft")` 时抛
  `UserError("分包登记状态只能通过受控业务动作推进。")`——创建入口不能植入已推进的状态。
- `:511 write()`：`"state" in vals` 且非 token 上下文即拒绝；**守卫置于
  内部放行之前**，因为内部放行只用于合同一致性回写事实字段，不应顺带获得状态写入能力。
  **更正（见 §8.35.20-㉟）**：当时只有状态守卫排在放行之前，**事实冻结仍排在放行之后**；
  该顺序缺口已在本轮补齐（冻结判定先于放行判定）。
- `:730/:740/:758/:769/:777`：`action_register`／`action_close`／`action_reopen`／`action_cancel`／
  `action_reset_draft` 的状态写入改为 `self._write_cost_source_state({...})`；`:780` 新增
  `_write_cost_source_state()`（`with_context` 注入 token）。受控动作的语义、前置校验与顺序均未变。

#### 8.35.19-③ 夹具改走合法路径（原「既有失败」随之消失）

- `tests/test_product_reports.py`：夹具原以 `state="confirmed"` 植入 `sc.labor.usage`、以
  `state="active"` 植入 `sc.subcontract.register`，被 S1 状态守卫（§8.35.17-③）拒绝。
  现改为执行**合法转移**：`usage.action_submit(); usage.action_confirm();` 与
  `register.action_register()`。这是批次 B 如实登记的既有失败，本批按「夹具不得绕过交付规则」收口。
- `sc.subcontract.settlement` 仍以 `state="confirmed"` 创建——该模型不在本批窗口内，未改动。

#### 8.35.19-④ 断言：新增、零删除

- `tests/test_usage_performance_native_lowcode.py`：在 `test_the_subcontract_register_freezes_only_after_closing`
  内新增——`create({"state": "active", ...})` 被拒；`write({"state": "active"})` 被拒且状态不变；
  `closed` ＋ 有结算引用时 `write({"state": "active"})` 与
  `with_context(sc_skip_subcontract_contract_authority=True).write({"state": "active"})` **均被拒**且仍为 `closed`。
  **更正（见 §8.35.20-㉟）**：该断言当时**只覆盖 `state`**、未覆盖事实字段，所以没有发现放行键能掀开事实冻结；
  本轮补上「已关闭 + 伪造放行键 + 事实字段」断言。
- 字段完整性、结构同源、角色隔离断言全部保留，**未删除任何断言**，也未把状态守卫写成
  「必填 ∩ 可填」式的窄断言（`name`／日期等有合法生成来源的字段不在守卫范围内）。
- **既有 pin 分类补登（非删除）**：§8.35.19-① 让 575 的 P1 载体新增了 `state` 只读声明，
  `test_the_readonly_policy_keeps_only_facts_with_a_legal_carrier` 的「每个声明字段都必须被分类」不变量
  因此变成红灯（`Items in the second set but not the first: 'state'`）。按该测试自身的口径补登
  `FACT_CARRIERS["sc.subcontract.register"]["state"] = "workflow"` 与
  `EXPECTED_READONLY_POLICY["sc.subcontract.register"] += ("state",)`——与 871／570 已有的同类登记
  （`"state": "workflow"`）一致，**不是放宽断言**：`state` 由工作流供给而非用户录入，`_legal_carrier`
  仍须给出非空来源，用户录入字段仍不得出现在策略只读集中。

#### 8.35.19-⑤ 分层验证（本轮 dirty 工作树，未绑定冻结身份）

| 层 | 内容 | 结果 | 证据 |
| --- | --- | --- | --- |
| L1 | `local.dev.upgrade`（`smart_construction_core`） | PASS（`[local.dev.ready] PASS` ＋ demo authority PASS） | `tmp/uc4-g09-batchC-upgrade.log` |
| L2-1 | 本组入口类 ＋ 报表类 ＋ 分包成本登记类（**最终树**复跑） | 0 failed / 0 error of 32 | `tmp/uc4-g09-batchC-l2-1-final.log`（首轮 `-l2-1.log` 已作废，见下） |
| L2-2 | `TestP0StateClosure` ＋ `TestWorkflowContractBackend`（**最终树**复跑） | 1 failed / 7 error of 104，**与批次 A 基线逐项一致** | `tmp/uc4-g09-batchC-l2-2-final.log`、基线 `tmp/uc4-g09-batchA/l2-contract-class-BASE.log` |
| L2-3 | `smart_core` 两个分包契约类（累计结算 ORM、登记结算授权 ORM）（**最终树**复跑） | 0 failed / 0 error of 66 | `tmp/uc4-g09-batchC-l2-3-final.log` |
| L2-4 | 源码级边界测试（AST 解析 `subcontract_management.py`） | 8 测全过 | `addons/smart_construction_core/tests/test_um_p3_subcontract_register_settlement_authority_boundaries` |

- L2-2 的 1 failed / 7 error **不是本批引入**：错误签名与批次 A 基线用
  `grep -o "ERROR: TestWorkflowContractBackend\.\w*"` 逐项 diff 为**完全一致**的空差集（各 7 条）；
  唯一 1 failed 亦同名（`test_profile_methods_resolve_to_existing_model_methods`）。
- 相比批次 B，`TestProductReports` 的既有失败因 §8.35.19-③ 的夹具修正而**消失**。
- **首轮分层日志属陈旧证据**：`tmp/uc4-g09-batchC-{l2-1,l2-2,l2-3}.log` 的时间戳（18:48／18:49／18:51）
  **早于**本轮 L1 升级日志（18:54），且 `test.safe` 是 no-upgrade 运行 ⇒ 那三份日志取自
  **尚未装载 §8.35.19-① 载体改动的库内契约**，不能代表最终树。按「最终树复跑」处置：三组均复跑
  （`-final.log`），旧日志作废。复跑暴露的正是 §8.35.19-④ 末条那条 pin 分类红灯——
  **该红灯被此前三份「全绿」记录掩盖**，本轮如实登记并修复，不复用陈旧结论。

#### 8.35.19-⑥ L3 回滚事务：64 步全过、`gaps` 清空

`tmp/uc4-g09-batchC/g09_txn_verify.py`（批次 B 脚本的继承版，`tmp/uc4-g09-batchB/` 保留原脚本与原
`l3-txn.log` 作为**修正前**证据，两者不混用）：

- 批次 B：58 步全过，但 `gaps` 含 1 条 `575:state_write_bypass`（如实登记「观察到、未修」）。
- 批次 C：**64 步全过、`failed=[]`、`gaps=[]`**（`tmp/uc4-g09-batchC-txn.log`）。移除 1 条 gap，
  新增 6 步：`575:direct_state_write_refused`、`575:state_write_refused_under_authority_skip`、
  `575:foreign_token_object_refused`、`575:create_non_draft_refused`、
  `575:token_context_state_write_allowed`、`575:state_restored_after_positive_control`。
- **正对照非空洞**：token 上下文里的状态写入仍然成功（`closed → active → closed`），证明上述拒绝是
  **状态闸门**而不是「状态永不可写」的笼统封锁——这正是不采用「前端强行解除只读」的验证依据。
- 全流程在 `SAVEPOINT`／`ROLLBACK` 内完成：`rollback:no_labor_usage_left`／`no_equipment_usage_left`／
  `no_subcontract_left` 均为 0 残留，未创建任何业务样本。

#### 8.35.19-⑦ 前端消费面复算（只读）

用批次 C 重新投影的 8 份真实 `ui.contract.v2`（`tmp/uc4-g09-batchC/v2-contract/`，SAVEPOINT/ROLLBACK）
复算批次 B 的全部消费面断言，并新增状态投影断言：

| 交付状态 | 解码 | `state` 三处投影 | 渲染器 reopen 引用 | 可见 | 执行适配器 | modifier | workflow 行 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `draft` / `active` / 重开后 | ok | `readonly=true` | 0 | 0 | n/a | 隐藏 | `submit`+`cancel` / `complete`+`cancel` |
| `closed` | ok | `readonly=true` | 1 | 1（`enabled=true`） | `contract-action` | 可见 | `reactivate` |

（第二身份已在 §8.35.19-⑩ 的核清中由 `demo_role_project_manager` 更正为 `demo_role_pm`
——前者解析角色是 `project_member`，后者才是 `pm`；用更正后的身份**整体复跑**，上表逐项不变。）

- 前后对照（同一探针、同一记录）：批次 B 契约 `state` 三处投影为 `readonly=false`，批次 C 为
  `readonly=true`，系统身份与项目负责人身份**逐项一致**。
- `closed` 仍为 `validateCanonicalFormActionExecutors → null`（不触发
  `CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING`）；正对照（未绑定 `button[9]`）仍立即返回该错误码。
- 证据：`tmp/uc4-g09-batchC/{v2-contract-dump.py,v2-contract-dump.log,v2-contract/,consume-probe.ts,consume-probe.log}`。

#### 8.35.19-⑧ §8.35.18-⑦ 残留登记的状态更新

| 项 | 批次 B 判定 | 批次 C 判定 |
| --- | --- | --- |
| `575:state_write_bypass` | 未修 | **已关闭**：P1 载体 `state` 只读（§8.35.19-①）＋ `create()`／`write()` 状态守卫（§8.35.19-②）＋ 夹具改走合法动作（§8.35.19-③），三层齐备并有 L3 正／反断言与前端投影对照 |
| `test_product_reports.py` | 与本批无关，如实登记 | **已修正**（§8.35.19-③），L2-1 由「既有失败」转为 32 测全过 |
| 前端 transition 注册表 | 未改，待产品方决定 | **仍未改**：非 `closed` 状态下 `isWorkflowTransitionMethod('action_reopen')=false`、`shouldShowWorkflowAction=true` 的降级事实在本批复算中**逐项重现**；实际拦截仍来自交付状态契约＋原生 modifier＋后端拒绝（fail-closed）。最小改动仍是在 `workflowActionAvailability.ts` 补 `reactivate` 键与 `action_reopen` 别名 |

**产品口径待确认（非缺陷，取保守口径）**：沿用 §8.35.18-⑦ 的记载——`action_reopen` 在**任一**明细已被
结算引用时整单拒绝重开；若产品方要求「可重开但被引用明细行级冻结」，属下一轮范围。

#### 8.35.19-⑨ 状态与边界

- **本轮未做且未授权**：冻结候选、`ci.local.quick`、独立复核、外部归档、更新／合并 #499、部署、G10、
  89 入口整体交付、台账扣减／补登（**保持 22**）、草稿发布／撤销／删除、工作树／分支清理、浏览器矩阵重跑。
- 现场：开发库 `sc_dev_demo` 已升级到本轮工作树；浏览器复核入口 `/f/sc.subcontract.register/1`、
  `/f/sc.subcontract.register/new`（重点：新建页 `state` 不再是可填字段、状态条为展示、
  `已关闭` 态事实只读且「重新打开」可用、有结算引用时被拒）。
- 复核实名口径：登记验收身份为 `business_config_admin`——**登记夹具载体在 dev 库缺失**（环境缺陷），
  合法取得路径见 -⑩；当前会话身份 `sc_test_admin`（解析角色 `system_admin`）**不计作登记验收身份通过**；
  `记录人：Demo-全能力` 是字段值，不等于登录会话用户。
- 边界重申：**更新 PR ≠ 产品验收通过**；**独立复核通过 ≠ 产品验收通过**；
  **G08 主线集成 ≠ 部署 ≠ 89 入口整体交付完成**。

#### 8.35.19-⑩ 登记验收身份核清（2026-09-20 只读复测；修正 -⑨ 的含糊表述）

-⑨（以及批次 B 的 README）把登记身份写成「`business_config_admin` 在 `sc_dev_demo` **不可用**」。
该表述**不准确**，且与 §8.35.13-③/-④ 的既有结论并列时会产生误导。按三层拆开重述，并给出合法取得路径。

**第一层：dev 库 `sc_dev_demo` 的会话身份。**

| 身份 | 解析角色 | 依据 | 结论 |
| --- | --- | --- | --- |
| `sc_test_admin`（uid 51，本次会话） | **`system_admin`** | 持 `base.group_system`；交付 profile 的 `role_precedence` 首位即 `system_admin`（实测 `["system_admin","business_full","business_config_admin","executive","owner","pm","finance","cost"]`） | **不是**登记验收身份（与产品方浏览器观察「当前岗位：系统管理员」一致，属**既定优先级**，非缺陷） |
| `sc_business_admin`（uid 6） | `business_config_admin` | 持 `group_sc_cap_business_config_admin`；库内唯一该角色账号 | **不得**用作验收身份：它是 2026-09-07 已从产品面移除的**退役残留载体**（见 `delivery_context_switch_log_v1.md:8668`），且其密码**不是** demo 凭据（`SC_DEMO_USER_PASSWORD` 哈希校验 `false`；`sc_test_admin`／`demo_full`／`wutao`／`demo_role_project_manager` 均为 `true`） |

**第二层：登记夹具载体在 dev 库缺失——按声明这是**预期**，缺口在验收运行时。**

`smart_construction_acceptance_fixture` **installed**，而
`…acceptance_fixture.fe_user_config_admin`、历史拼写 `fe_fe_config_admin` 与用户
`fixture_role_config_admin` **均为空**（今日复测仍成立）。

**权威依据**（`.agent/context.yaml:76-81`）：

```yaml
acceptance_identity:
  login: fixture_role_config_admin
  role: business_config_admin
  carrier: smart_construction_acceptance_fixture.fe_user_config_admin
  platform_admin_separate: true
  fixture_only: true
```

且 `data_policy.acceptance` 为 `odoo_demo: false`／`demo_fixture: true`／`explicit_guard_required: true`，
而持久 dev 库是 `synthetic_fixture: explicit_only`。⇒ 登记身份**按声明就不应存在于 dev 库**，
dev 库无该用户**与声明一致，不构成 dev 库缺陷**；§8.35.13-③ 的 `environment_defect` 定性应收窄为
「**验收运行时未 provision**，登记角色下的入口级复核尚未执行」。这与产品方所见的
`sc_test_admin`＝`system_admin` 会话同源，两者都不推翻产品结论。

**第三层：登记验收身份的合法取得路径 = 验收运行时，而非 dev 库。**

- fixture 工具 `addons/smart_construction_acceptance_fixture/tools/frontend_productization_fixture.py:967`
  创建 `fixture_role_config_admin`，持 `smart_construction_core.group_sc_role_business_admin`；
  该角色组**蕴含** `group_sc_cap_business_config_admin`（`security/sc_role_groups.xml:22`），
  且 `core_extension_hook_facts.py:19` 把两者并列为 `business_config_admin` 的载体组
  ⇒ 该夹具身份**解析角色确为登记角色 `business_config_admin`**。
- 入口：`make acceptance.frontend.fixture`（`SC_ACCEPTANCE_FIXTURE_PASSWORD` 未设置时自动生成），
  目标库 `FRONTEND_ACCEPTANCE_DB=sc_frontend_acceptance`、前端 `:5175`（`make/runtime_ops.mk:1770` /
  `make/dev.mk:514`）。当前该运行时只有 redis 容器在跑，odoo／db 未起。

**因此**：登记角色下的入口级验收应在**验收运行时**做（fixture 身份 + `sc_frontend_acceptance`），
dev 库（`:5174`）上的复核必须显式标注为 `system_admin` 会话，**不能**替代登记身份结论。
最小解封路径（**P4／环境范围，本轮未执行、仅登记**）：起验收运行时并跑一次
`make acceptance.frontend.fixture`，即得登记角色身份。

**同批修正（我方证据的标签精度，并已重跑）**：批次 B/C 前端探针把 `demo_role_project_manager` 读作
「项目负责人身份」，但交付解析器对它给出的角色是 **`project_member`**（持 `group_sc_cap_project_read`）；
本库真值为 `pm` 的具名会话是 **`demo_role_pm`**（同样持 `group_sc_cap_project_manager`）。
已把 §8.35.19-⑦ 的第二身份改为 `demo_role_pm` 并**整体复跑契约投影与前端消费面**：
`pm_role_code=pm`，`state` 三处投影 8 份全为 `readonly=true`，`closed` 的 reopen
（1 引用／可见／`enabled=true`／解析为 `contract-action`／适配器校验 `null`）与正对照
（未绑定 `button[9]` → `CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING`）**与上一轮逐项一致**
⇒ 结论不依赖被误标的那个会话。

**可复现证据**：`tmp/uc4-g09-batchC/identity-probe.py` / `identity-probe.log`
（只读；离线校验 demo 凭据哈希，不打印口令、不改任何数据）。


### 8.35.20 补验轮：新建态可办理性（交付契约级，2026-09-20；**未冻结、未跑 Quick、未更新 #499、未合并**）

**触发**：产品方浏览器复核在 `291c6ee7` 上给出阻断——「新建页能打开，却尚未证明能办理」。
批次 A／B／C 证明的是**记录态**（字段只读策略、状态窗口、回滚事务），**没有**证明**新建态**下
必需事实确实可获得；本补验只补这一层，**未改产品代码**。

**状态**：工作树仍为 `012c8ad4`（dirty，12 文件；本轮仅新增本文件与 `tmp/` 证据），台账保持 **22**，
#499 保持 **OPEN／未合并**（`headRefOid=012c8ad4…`、`mergeStateStatus=CLEAN`）。

#### 8.35.20-① 方法：直接取交付面真正交给 `/new` 的契约

- `render_profile="create"` ＋ `record_id="new"` 的真实 `ui.contract.v2` 投影；
  4 个入口（871 劳务成本登记、570 机械台班两套入口、575 分包登记）× 2 个身份 = **8 份**；
  全程 `SAVEPOINT → ROLLBACK`，未建业务样本。
- 再把 8 份契约跑**真实前端管线**：`decodeContractV2Snapshot → createContractV2Store →
  presentContractV2Form(store, 'create', {})`，断言落在 presenter 产出的节点上，而不是声明文本上。
- 运行时：注册 dev profile（`sc-local-dev` / `sc_dev_demo`，:8070＋:5174），模块已在本树上于 18:54 升级
  （`tmp/uc4-g09-batchC-upgrade.log`），本轮**未**再升级。

#### 8.35.20-② 结果：8/8 通过

| 契约面 | 模型 | 会话／解析角色 | pageAuth | 项目 | 用户事实可填数 | 空办理提示渲染 | sabotage 对照 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `equipment_usage_register` | `sc.equipment.usage` | `__system__` / **system** | `edit` | 必需·可填 | 10 | 否 | 拒绝（按预期） |
| `equipment_usage_shift` | `sc.equipment.usage` | `__system__` / **system** | `edit` | 必需·可填 | 10 | 否 | 拒绝（按预期） |
| `labor_cost_register` | `sc.labor.usage` | `__system__` / **system** | `edit` | 必需·可填 | 12 | 否 | 拒绝（按预期） |
| `pm-equipment_usage_register` | `sc.equipment.usage` | `demo_role_pm` / **pm** | `edit` | 必需·可填 | 10 | 否 | 拒绝（按预期） |
| `pm-equipment_usage_shift` | `sc.equipment.usage` | `demo_role_pm` / **pm** | `edit` | 必需·可填 | 10 | 否 | 拒绝（按预期） |
| `pm-labor_cost_register` | `sc.labor.usage` | `demo_role_pm` / **pm** | `edit` | 必需·可填 | 12 | 否 | 拒绝（按预期） |
| `pm-subcontract_register` | `sc.subcontract.register` | `demo_role_pm` / **pm** | `edit` | 必需·可填 | 2 | 否 | 拒绝（按预期） |
| `subcontract_register` | `sc.subcontract.register` | `__system__` / **system** | `edit` | 必需·可填 | 2 | 否 | 拒绝（按预期） |

必需事实（真实契约口径）：

| 契约面 | 必需事实 |
| --- | --- |
| `equipment_usage_register` | `currency_id`、`equipment_name`、`name`、`operator_name`、`project_id`、`usage_date`、`usage_hours`、`usage_location`、`usage_qty` |
| `equipment_usage_shift` | `currency_id`、`equipment_name`、`name`、`operator_name`、`project_id`、`usage_date`、`usage_hours`、`usage_location`、`usage_qty` |
| `labor_cost_register` | `currency_id`、`labor_team`、`name`、`project_id`、`settlement_state`、`usage_date`、`usage_type`、`work_content`、`worker_qty` |
| `pm-equipment_usage_register` | `currency_id`、`equipment_name`、`name`、`operator_name`、`project_id`、`usage_date`、`usage_hours`、`usage_location`、`usage_qty` |
| `pm-equipment_usage_shift` | `currency_id`、`equipment_name`、`name`、`operator_name`、`project_id`、`usage_date`、`usage_hours`、`usage_location`、`usage_qty` |
| `pm-labor_cost_register` | `currency_id`、`labor_team`、`name`、`project_id`、`settlement_state`、`usage_date`、`usage_type`、`work_content`、`worker_qty` |
| `pm-subcontract_register` | `currency_id`、`name`、`project_id`、`register_date`、`subcontract_scope` |
| `subcontract_register` | `currency_id`、`name`、`project_id`、`register_date`、`subcontract_scope` |

**结论**：产品方看到的「项目为空且不可填」在交付契约上已不成立——`project_id` 在全部 8 个新建面上
`required=true` **且** `readonly=false`，`state` 在新建面不可填。

#### 8.35.20-③ 断言清单（新增，零删除）

- **A** `project_id`：存在、必需、可填（正是产品方观察到的那个字段）。
- **B** 全部「用户录入」事实在 create 面可填（871 12／570 10／575 2，与
  `USER_SUPPLIED_FACTS` 同口径）。
- **C** `state` 在 create 面**不可填**。
- **D** 每个必需事实要么可填、要么由**具名**服务端载体供给（逐个列出，不做笼统豁免）。
- **E** 新建保存载荷（`collectWritableValues` 在无 `recordId` 时的过滤条件）覆盖全部用户事实。
- **F** 办理提示宿主为 `alert alert-info` / `role=status` 且绑定 `invisible="not processing_advisory"`；
  不变量是**等价**（有内容才渲染、空计算不渲染），见 **-⑨**（本条最初写成「恒隐」，-⑨ 已更正）。
- **sabotage 对照**：把契约副本的 `project_id` 改回 `readonly=true` 后，同一断言**立即失败**
  ⇒ 绿色结果不是空断言。

#### 8.35.20-④ 会话身份口径（避免与「记录人」字段值混用）

- 本次两个身份：odoo shell `__system__`（与 dev 会话 profile 的 `system_admin` 优先级同源）与
  `demo_role_pm`（交付解析器实测 **`pm`**）。
- **未**使用 `demo_role_project_manager`：解析器读它是 `project_member`，不是 `pm`（见 §8.35.19-⑩）。
- `记录人：Demo-全能力` 是**字段值**，不构成登录会话用户；本节的会话身份取自实际渲染环境。

#### 8.35.20-⑤ 本补验**不**证明什么（明确边界，避免过度宣称）

- **不是浏览器旅程**：未做未保存录入、日期控件、联动字段的交互验证，也未点击保存。
- **不是登记验收身份**：`business_config_admin` 的入口级复核仍需验收运行时
  （`make acceptance.frontend.fixture` ＋ `sc_frontend_acceptance`），见 §8.35.19-⑩；本轮未执行。
- **`E` 为仿真口径**：按 `collectWritableValues` 的过滤条件复算，未调用该 composable 本身，也未执行服务端默认值。
- **`name` 的默认值未在本层执行**：871／570 的 `name` 在 create 面 `readonly=true`（序列号载体），
  其取值属服务端默认与 L3／新单实测范围。

#### 8.35.20-⑥ 证据包更正（本轮）

批次 C 证据包 `tmp/uc4-g09-batchC/README.md` 的「8 份契约 × `demo_role_project_manager`」与
「契约投影探针 … `demo_role_project_manager`」两处**与重跑后的实际标签不一致**（重跑用的是
`demo_role_pm`，8 份文件即 `pm-*.json`）。已就地更正为 `demo_role_pm` 并保留其下的「标签精度修正」段，
未回填批次 B 自身的历史证据（批次 B 确系用 `demo_role_project_manager` 跑出）。

#### 8.35.20-⑦ 状态与边界

- **批次状态**：定向补验（新建态可办理性）完成；仍**不是**「批次验收完成」——产品复核未通过前不得冻结候选。
- **主线／部署**：未合并、未部署、台账 **22** 不变（预期核减仅在合入后按实际退役消费者单独审计）。
- **下一步（未执行，等待授权）**：① 产品方在 dev 会话（`:5174`，会话身份 `system_admin`）实际点击
  `/f/sc.labor.usage/new`、`/f/sc.equipment.usage/new`、`/f/sc.subcontract.register/new`；
  ② 如需登记角色口径，起验收运行时跑 `make acceptance.frontend.fixture`（P4／环境范围，需单独授权）；
  ③ 产品复核通过后才：冻结候选 → 一次 exact-head Quick → 独立复核 → 外部归档 → 受管更新 #499。
- **证据包**：`tmp/uc4-g09-creatability/`（`dump-create-contract.py`、`dump.log`、
  `creatability-probe.ts`、`creatability-probe.log`、`creatability-summary.json`、
  `v2-contract-create/*.json`、`README.md`）。


#### 8.35.20-⑧ HTTP 服务路径层复核（浏览器实际收到的字节）

**动机**：-① 走的是**进程内** handler 调用；产品方看到的是**页面**。两层可能不同（-⑨ 正是如此）。
本层沿浏览器自己的路径取同一份契约：dev 前端（Vite，`:5174`）`/api/v1/intent` 代理 →
平台意图层，`login` 意图取 Bearer token，再以 `ui.contract.v2` ＋ `render_profile="create"`
取 871／851／570／575 的新建契约（**只读**：登录读接口 + 合同读接口，未写业务数据）。

- 身份绑定：token 内的 `user_id` 与交付解析器给出的 uid **逐项相等**（`system_admin` uid 51、
  `pm` uid 42），不是「谁登录了」的推断：
```json
{
 "sc_test_admin": {
  "ok": true,
  "has_token": true,
  "token_uid": 51,
  "token_db": "sc_dev_demo",
  "resolved_uid": 51,
  "role_code": "system_admin",
  "uid_binding": true
 },
 "demo_role_pm": {
  "ok": true,
  "has_token": true,
  "token_uid": 42,
  "token_db": "sc_dev_demo",
  "resolved_uid": 42,
  "role_code": "pm",
  "uid_binding": true
 }
}
```
- 一处**调用口径**差异已记入：HTTP 侧**不能**带 `record_id="new"`
  （意图层返回 `INTENT_NOT_FOUND 记录 new 不存在`）；前端新建页正是只发 `render_profile="create"`。
  -① 的进程内探针带了 `record_id="new"` 仍可解析，故两处口径不同、结论相同。
- 结果 **8/8**：`ok=true`、布局已交付、`project_id` 必需且可填、`state` 不可填、`pageAuth=edit`。

| 契约面 | action | 会话／解析角色 | pageAuth | 项目 | 办理提示 | sabotage 对照 |
| --- | --- | --- | --- | --- | --- | --- |
| `equipment_usage_register` | 570 | `sc_test_admin` / **system_admin** | edit | 必需·可填 | 有内容→可见 | 拒绝（按预期） |
| `equipment_usage_shift` | 851 | `sc_test_admin` / **system_admin** | edit | 必需·可填 | 有内容→可见 | 拒绝（按预期） |
| `labor_cost_register` | 871 | `sc_test_admin` / **system_admin** | edit | 必需·可填 | 有内容→可见 | 拒绝（按预期） |
| `pm-equipment_usage_register` | 570 | `demo_role_pm` / **pm** | edit | 必需·可填 | 有内容→可见 | 拒绝（按预期） |
| `pm-equipment_usage_shift` | 851 | `demo_role_pm` / **pm** | edit | 必需·可填 | 有内容→可见 | 拒绝（按预期） |
| `pm-labor_cost_register` | 871 | `demo_role_pm` / **pm** | edit | 必需·可填 | 有内容→可见 | 拒绝（按预期） |
| `pm-subcontract_register` | 575 | `demo_role_pm` / **pm** | edit | 必需·可填 | 有内容→可见 | 拒绝（按预期） |
| `subcontract_register` | 575 | `sc_test_admin` / **system_admin** | edit | 必需·可填 | 有内容→可见 | 拒绝（按预期） |

⇒ 新建态可办理性**不是**进程内幻觉：产品页面实际收到的契约同样给出可填的项目与不可填的状态。

#### 8.35.20-⑨ 更正：办理提示的不变量是「有内容才渲染」，不是「恒隐」

-①／-③ 的 **F** 原写成「空计算下 presenter 解析为不可见 ⇒ 空提示不再渲染」。该结论只在**进程内**那一面
成立（runtimes 下 `processing_advisory` 计算为空）。HTTP 服务路径层交付的却是**非空**内容：

```
871 建议补充劳务单位；建议补充工种；建议补充施工部位；建议补充带班人；建议补充用工单价；建议上传用工依据
570 建议关联来源设备申请；建议补充供应单位；建议补充设备编号；建议补充规格型号；建议上传台班依据
575 建议关联来源分包申请；建议关联分包合同；建议补充履约期间；建议补充管理要求；建议上传分包成本依据
```

此时提示**应当可见**——它是「还缺什么」的办理指引，不是占位符。故不变量修正为
**`办理提示可见 ⟺ 其值非空`**，并已在断言里按等价形式实现（含两侧对照）：

| 面 | 提示值 | 渲染 | 结论 |
| --- | --- | --- | --- |
| 进程内（-①） | 空 | 不可见 | 符合 |
| HTTP 服务路径（-⑧） | 非空（上列指引） | 可见 | 符合 |

产品方在 `291c6ee7` 上看到的「办理提示 —」= **空值仍渲染成占位横线**，本批修的是该等价关系，
而不是「把提示关掉」。**同一条 create 面在两个会话上下文下投影出不同的提示内容**，这也是本层必须存在的理由：
仅凭进程内投影会对产品面作出错误结论。

#### 8.35.20-⑩ 入口族定位更正：从手写 4 入口改为交付清单 7 入口

-①～-⑨ 沿用手写的 4 入口标签（871／851／570／575）。这是**不精确的**：按交付实际，共享这三张表单的入口共
**7 个**，且存在两个此前未被识别的兄弟关系：

| 共享表单 | 模型 | 入口 |
| --- | --- | --- |
| `view_sc_labor_usage_form`（view 1461） | `sc.labor.usage` | a561 劳务用工、a562 方单、a563 零星用工、a871 劳务成本登记 |
| `view_sc_equipment_usage_form`（view 1476） | `sc.equipment.usage` | a570 机械台班登记、a851 机械台班记录 |
| `view_sc_subcontract_register_form`（view 1491） | `sc.subcontract.register` | a575 分包成本登记 |

判据（`entry-family.py`，只读、运行库解析）：action 的 `view_mode` 含 `form`，且**未 pin 表单视图**（无 `view_id` ⇒ 落
primary form；pin 的是 tree 等非表单视图 ⇒ form 仍回退 primary form）。pin 了**表单**的入口另立一面，本轮
`excluded: []`（无此类入口）。原手写表误把「871／851／570／575」当作入口族，也误把「871／562／563」当作共享视图
兄弟；真值见上表。**判据不写成代码就会漂移**，故三层探针统一消费 `entry-family.json`，断言里额外比对
`summary` 的键集与交付清单**逐项相等**（漏采即失败）。

#### 8.35.20-⑪ 全族两层结果：14/14 收齐，代表入口全绿

7 入口 × 2 身份 = **14 份契约**，①②两层各自收齐、结论一致：`ok=true`、`pageAuth=edit`、`project_id` **必需且可填**、
`state` 不可填、`name` 在 871／570／851／561／562／563 上由序列承载（`readonly` 且 `auth=read`）。

| 入口 | 名称 | 可填可见字段（create） | 说明 |
| --- | --- | --- | --- |
| a871 | 劳务成本登记 | 15 | **代表入口**，本批 owning |
| a570 | 机械台班登记 | 16 | **代表入口**，本批 owning |
| a575 | 分包成本登记 | 14 | **代表入口**，本批 owning |
| a562 | 方单 | 15 | 兄弟入口，与 a871 同表单 |
| a563 | 零星用工 | 15 | 兄弟入口，与 a871 同表单 |
| a851 | 机械台班记录 | 16 | 兄弟入口，与 a570 同表单 |
| **a561** | **劳务用工** | **6** | **兄弟入口，新发现阻断（见 -⑫）** |

`sabotage` 对照（把契约副本 `project_id` 改回只读 ⇒ 同一断言立即失败）在三张代表面上都通过，绿色不是空断言。
兄弟入口不冒充代表入口的闭环，只跑全族共用的 A／C／D／F 并给出 `create_payload_size` 作隔离对照。

#### 8.35.20-⑫ 发现：a561 劳务用工新建面**不可办理**（登记，未改）

两层 × 两身份共 4 份契约一致给出：

```
a561  blocking_required = work_content(visible=false, readonly=true)
```

`work_content`（作业内容）在 `sc.labor.usage` 上 `required=True` 且**无默认值**（`default-carrier-probe.py` 实测
`default=<none>`），却在交付面上不可见不可填 ⇒ 该入口新建**无法通过校验**。同表单的 a562／a563／a871 无此问题，
可填可见字段 15 个；a561 只有 6 个。

**首次偏差定位**（原生声明→模型约束→配置策略→最终契约→控件）：

- 原生 arch 与模型约束无异常：`work_content` 在模型上正常可写、`required=True`。
- 偏差在**配置策略层**。用 `field-policy-capture.py` 只读截获投影实际收到的 `field_policies`：
  a561 是**模型全量 58 键**（含 `visible_profiles: ["edit", "readonly"]`，`create` 被排除）；
  a871／a575 只有 5–9 个声明键、无 profile 限制（仅 `source_required`）。渲染 profile 为 `create`，
  于是 a561 的字段被 `auth="none"`＋`visible=false` 落定。
- **已排除的两条路径**（各自实测，避免把成因臆断成「运营手工隐藏」）：`policy-source-probe.py`
  遍历库内全部已发布载体，**没有任何载体**为这些字段声明 `visible: false`；`lowcode-field-policy-probe.py`
  显示 `ui.form.field.policy` 为**空表（0 行）**⇒ 不是存储式的低代码字段配置，而是**投影阶段合成**的策略。
- 成因：a871／a562／a563 各有 **priority 800 的入口级发布**（`labor_usage_form_productization_contract.xml`，
  `composition_mode: native_semantic_surface`），结构权威归原生 arch，模型级平面不再决定呈现；
  **a561 没有入口级发布**，继续消费模型级平面。这与本批为 871 修掉的（§8.35.19 前言所述「871 此前没有入口级发布」）
  是**同一类缺口**，只是 561 未被覆盖。
- **未定性为非缺陷**：未找到「劳务用工必须由来源单据带入作业内容」的规则依据，无预期角色依据可支撑这一隐藏，
  故按**阻断**登记，而不是当作有意设计。

**最小修正范围（本批未实施，交产品方决定）**：在 `labor_usage_form_productization_contract.xml` 为
`action_sc_labor_usage`（561）补一条 priority 800 的入口级发布，形状与既有的 a562／a563 两条记录**完全一致**
（只带 `title` 与 `composition_mode: native_semantic_surface`）。纯声明、无数据迁移、`git revert` 可回滚。
**a561 不在本批授权的 871／570／575 之内，故只登记不改**，符合「若确有权限缺陷，单独给出最小修正范围，
再决定是否纳入本批」。

**该发现是既有事实、非本批引入**：本批工作树 diff **未触碰** `sc.labor.usage` 的任何载体或策略——
`git diff p1_daily_business_form_orchestration_contract_data.xml` 仅含 labor **settlement** 注释改写与
subcontract register 的 `state` 一行；`labor_usage_form_productization_contract.xml` 未被修改（工作树 clean）。
另：产品方观察到的「只读必填」在本轮被拆成 `readonly` 与 `visible` 两组独立标志分别核对，不再混为一谈。

#### 8.35.20-⑬ a575 的 `currency_id`：只读且不可见，但**不是**缺陷

`currency_id` 在 a575 上 `required=true, visible=false, auth=none`，表面与 a561 同症状，但模型上
`required=True, default=lambda self: self.env.company.currency_id.id`（实测 `default=6`）——**必需值有合法来源**，
符合 -③ 断言 **D**「必需值是否可通过合法路径取得」的口径。同口径的还有 `name`（`ir.sequence`）与
`settlement_state`（默认 `unsettled`）。这正是产品方「不能把所有只读必填字段都判成错误」的可执行版本：
判据是**载体实测**，不是字段名，也不是「必填 ∩ 可填」。

#### 8.35.20-⑭ 断言结构调整：新增，零删除

-③ 的 A～F **全部保留**，本轮只**增加**并分层：

| 层 | 覆盖入口 | 断言 |
| --- | --- | --- |
| 全族 | 7 个 | A（`project_id` 必需可填）、C（`state` 不可填）、D（必需值可获）、F（办理提示等价） |
| 代表入口 | a871／a570／a575 | 追加 B（用户事实全部可填**且可见**）、E（保存载荷覆盖）、sabotage 对照 |
| 兄弟入口 | a561／a562／a563／a851 | 只跑全族层，并输出 `create_payload_size` 作隔离证据 |

退出码口径：**代表入口全绿但存在兄弟入口阻断时，故意非零**，并在 stderr 打印
`G09 CREATABILITY FINDING: …`。目的是让 a561 这类阻断**不能被误读成整批绿**；报告 JSON 同时给出
`representative_blocked`（本批 owning 的入口）与 `findings`（含兄弟入口），二者不混算。

#### 8.35.20-⑮ 状态与边界

- #499 **继续暂停合并**；台账保持 **22**；未冻结候选、未跑 `ci.local.quick`、未更新 #499、未动草稿／分支；G10 未启动。
- 本轮**未改产品代码**：新增内容全在证据包 `tmp/uc4-g09-creatability/` 与本文件。
- **仍不是浏览器验收**：未做未保存录入、日期控件、联动与保存点击；`business_config_admin` 的入口级复核仍需
  验收运行时（§8.35.19-⑩）。
- a561 的成因**未做端到端调用链复现**：定位到 `field_policies` 差异与「缺入口级发布」这一结构事实，
  未逐行展开发布解析器。

#### 8.35.20-⑯ a561 修正轮：补入口级发布（实施 ＋ 定向补验，2026-09-20）

产品方放行后，按 ⑫ 登记的**同一个**最小范围实施，改动面只多一条声明。⑮ 的「本轮未改产品代码」是对
⑫～⑮ 那一轮的口径；本轮起该表述不再适用。

**改动（1 条产品声明 ＋ 1 处测试登记）**

- `addons/smart_construction_core/data/labor_usage_form_productization_contract.xml` 追加
  `business_config_contract_labor_usage_work_productized_form_v1`：`action_id=action_sc_labor_usage`、
  `priority=800`、`title=劳务用工`、`composition_mode=native_semantic_surface`，形状与既有
  a562／a563／a871 三条逐字段一致，无数据迁移。
- `addons/smart_construction_core/tests/test_usage_performance_native_lowcode.py`：把 561 纳入 `ENTRIES`
  与 `SHARED_FORMS["view_sc_labor_usage_form"]`，并新增 `ENTRY_RELEASE_ACTIONS` ＋
  `test_every_family_action_owns_an_entry_release`（**新增，零删除**）。该断言按 **action**（不是按模型）
  要求「恰好一条入口级 native 发布、作用域指向该 action、优先级高于其模型级平面」——正是 dry run 认定的成因；
  它是**声明态**的守卫，行为本身由 create 契约探针单独作证，二者不相互替代。

**判据与实测（事务内 dry run → 落声明 → 升级 → 两层重跑）**

| 观测 | 修正前 | 修正后 |
| --- | --- | --- |
| a561 create 的 `field_policies` 键数 | 57（模型全量） | 9（与 a871 逐项相同） |
| `apply_field_policies_to_v2_status` 实际改写可见性的字段数 | 13 | 0 |
| a561 可填可见字段 | 6 | 15（＝a562／a563／a871） |
| 两层断言 | a561 `blocking_required=[work_content]`，退出码非零 | 14／14 两面 `findings=[]`，退出码 0 |
| 其余 6 入口 | a570=16、a575=14、a851=16、a562=15、a563=15、a871=15 | 逐项未变 |

事务内 dry run（把 a563 形状的记录挂到 561，`SAVEPOINT`／`ROLLBACK`，无落库）与升级后的实测给出同一结论，
因此「缺入口级发布 ⇒ 消费模型级平面 ⇒ 必需事实不可见」这条因果**闭合到行为层**（仍**未**逐行跟踪发布解析器）。

**边界**：只补声明，未删策略、未改前端、未动原生 arch；`work_content` 的 `required` 与模型守卫
`_FACT_IMMUTABLE_FIELDS` 均未变，`state` 仍为可见只读；回滚＝`git revert`。

#### 8.35.20-⑰ 入口可达性实测（并更正一处探针口径）

`tmp/uc4-g09-creatability/entry-reachability-probe.py`（新，只读）实测：

| 入口 | 菜单 | 父菜单 active | 导航可达 |
| --- | --- | --- | --- |
| 871 劳务成本登记 | 689 | True | **是** |
| 570 机械台班登记 | 692／509 | True／False | **是**（经 692） |
| 575 分包成本登记 | 693／518 | True／False | **是**（经 693） |
| 562 方单 | 504 | **False** | 否 |
| 563 零星用工 | 505 | **False** | 否 |
| 851 机械台班记录 | 510 | **False** | 否 |
| 561 劳务用工 | **无菜单** | — | 否 |

交付导航只暴露 **871／570／575**，与台账命名的三个入口、与产品方实际打开的三个入口一致。

**更正（假阴性）**：早前 `entry-actions.log` 记录「7 个 action 的 `menu_xmlids` 全为 `[]`」是**错的**，
来自两处口径错误，两处均已修正并在脚本注释留痕：

1. `ir.ui.menu.search()` 在本构建按用户分组过滤——不带 `ir.ui.menu.full_list` 上下文键时只返回 **204／717** 条，
   504／505／509／510／518／689／692／693 因此看似不存在；
2. `ir.ui.menu.action` 读回的是**记录集**（`ir.actions.act_window(561,)`），不是旧存储形态的 `model,id`
   字符串，按字符串比较一条也匹配不上。

凡引用「菜单 689／504／505」的表述，以本表为准。

561 仍是 `sc.labor.usage` 的**模型级集成入口**（`models/support/product_policy_sync.py` 的
`MERGE_BY_CATEGORY_INTEGRATION_ACTION_XMLIDS_BY_MODEL` 指向 `action_sc_labor_usage`），仍解析到同一张原生表单，
故其 create 面仍需可办理；**是否给它菜单属产品决策，本轮不提请、不实施**。
562／563／851 的父菜单 inactive 属既有导航状态，本轮**按原样登记**，不在本批改动范围。

#### 8.35.20-⑱ 受影响检查与状态

| 检查 | 命令／脚本 | 结果 |
| --- | --- | --- |
| 两层 create 断言 | `creatability-probe.ts`（①／②） | 14／14 两面，`findings=[]`、`representative_blocked=[]`，退出码 0 |
| 契约投影策略 | `field-policy-capture.py` | a561 57 → 9 键，`changed_visible` 13 → 0 |
| 记录态回滚事务 | `tmp/uc4-g09-batchC/g09_txn_verify.py` | **64／64**，无失败、无缺口 |
| 受影响测试类 | `TestUsagePerformanceNativeLowcode` | 31 tests，0 failed，0 error |
| 兄弟测试类 | `TestProductReports`／`TestLaborProductCapability`／`TestFormalFormLowcode` | 全通过 |
| 兄弟测试类 | `TestWorkflowContractBackend` | 8 项**预存在**环境性失败，与本轮无关 |

`TestWorkflowContractBackend` 的 8 项在改动前（`tmp/batchB-l2.log`，2026-09-19）即为 `1 failed, 7 error(s)`，
失败点全部落在**构造夹具**上（`费用与扣款单据必须关联已归属公司的有效项目`、
`收款归集关系不存在或当前用户无权访问`、`sc.partner.import.review` 模型不存在、
`SC_GUARD:P0_PAYMENT_STATE_BYPASS_BLOCKED`），无一涉及 `sc.labor.usage`。

**状态与边界**：#499 **继续暂停合并**；台账保持 **22**；未冻结候选、未跑 `ci.local.quick`、未更新 #499、未合并；
未动草稿／分支／工作树；G10 未启动。**本轮仍不是产品验收**：两层断言证明的是**契约面可办理**，
产品方浏览器复核（含登记身份 `business_config_admin` 的入口级复核，见 §8.35.19-⑩）尚未进行。

#### 8.35.20-⑲ 输入未变依据、`reactivate` 前端缺口的独立再判定与现场可用性（2026-09-20 只读）

**① 既有低代码闭环与前端消费证据的「输入未变」依据。** 本轮 dirty 增量按顶层归属只有两处：
`addons/smart_construction_core` **12 文件** ＋ 本文件 **1 文件**；`addons/smart_core/` 与 `frontend/`
均为 **0 文件**（`git diff --name-only HEAD`）。§8.35.12-② 的合法配置闭环运行的是 `smart_core`
变更集机制与 `frontend/apps/web/scripts/*.mjs` 设计器工具，两侧输入**逐字节未变**；前端消费面证据
（§8.35.18-⑥／§8.35.19-⑦）运行的是前端 presenter 源码，同样未变。故按产品方口径
「已有完全适用的证据时给出输入未变的依据即可」复用，**不重跑**闭环与浏览器矩阵。

**② `reactivate` 前端 transition 注册表缺口：独立再判定为不阻断，本轮仍不改。** §8.35.18-⑦／
§8.35.19-⑧ 登记的是**降级事实**（非 `closed` 时 `isWorkflowTransitionMethod('action_reopen')=false`、
`shouldShowWorkflowAction=true`）。本轮补上**后果**（批次 C 探针实测值）：非 `closed` 的 6 份交付契约
（`draft`／`active`／重开后 × 两身份）`contractReopenRows=0`、`visibleReopen=0`、`hiddenByModifier=[true]`；
`closed` 为 `1／1／enabled=true／workflowRows=['reactivate']`。即 `unmanaged` 回退**放行的对象根本不在
交付动作集内**（无物可放），`closed` 态则按 `method` 命中行并解析为 managed。三道拦截中任意一道单独
成立即可阻断：交付状态契约 `visible=false`／`ACTION_NOT_VISIBLE_IN_STATE`、原生 modifier
`state != 'closed'`、后端 `action_reopen` 状态守卫。故**不改共享注册表**；最小改动范围
（补 `reactivate` 键 ＋ `action_reopen` 别名）维持如实登记，待产品方决定语义是否统一。

**③ 现场可用性（只读实测）。** `vite :5174`／`nginx :18081`／`odoo :8070` 与三个入口 `/new` 均返回 `200`；
开发库最后一次升级为 18:24:26，晚于全部产品文件 mtime（最晚为
`data/labor_usage_form_productization_contract.xml` 18:21:50）⇒ **dev 运行时与当前工作树一致**。
复核入口（相对根路径，前缀 `http://127.0.0.1:5174`，`?action_id=…&menu_id=…` 见 §8.35.12-②）：
`/f/sc.labor.usage/new?action_id=871&menu_id=689`、
`/f/sc.equipment.usage/new?action_id=570&menu_id=692`、
`/f/sc.subcontract.register/new?action_id=575&menu_id=693`。
该会话解析角色为 `system_admin`（§8.35.19-⑩），**不构成**登记身份 `business_config_admin` 的入口级复核。

#### 8.35.20-⑳ 独立复核唯一非阻断项（S2-1 `state.copy`）收口（2026-09-20 只读）

- **结论：前提成立，依据在平台层而不在本仓。** `odoo/fields.py:431-434`（Odoo `17.0.0 FINAL`）：

  ```python
  if name == 'state':
      # by default, `state` fields should be reset on copy
      attrs['copy'] = attrs.get('copy', False)
  ```

  同文件 `:300` 是类默认 `copy = True`。该规则**只按字段名 `state` 生效**，所以本仓 `grep copy=False`
  找不到任何依据——这正是 S2-1 所说「缺代码层依据」的成因，它缺的是**平台**依据的引用，不是仓库声明。
- **实测**（`tmp/uc4-g09-creatability/state-copy-probe.py`，SAVEPOINT＋ROLLBACK；残留检查 0／0／0，
  `state-copy-residual-check.{py,log}`）：`sc.labor.usage`／`sc.equipment.usage`／`sc.subcontract.register`
  的 `_fields['state'].copy` 均为 `False`，三模型均**无** `copy()` 覆写；同模型对照组中唯二 `copy=False`
  的是 `state` 与 `company_id`，其余样本字段（含 required／含 default／含 tracking）全为 `True`
  ⇒ 归因是**字段名**，不是 `required`／`default`／`tracking`。`871` 已确认记录的 `copy_data()`
  **不含 `state`**；`copy()` 落在 `draft` 且**未触发** `create()` 守卫（守卫不是承重点，属双重保护）。
- **处置：不加 `copy=False`。** 显式声明在当前平台下与现状逐字等值（`attrs.get('copy', False)` 已给 `False`），
  属**冗余**；而该默认是平台源码中**有意写下**并带语义注释的规则，不是偶然默认值。写入仓库会新增
  `models/core/labor_management.py` 这一本批未涉及文件、扩大改动面，并把平台契约改写为仓库责任。
- 故 S2-1 由「非阻断建议」转为**已收口**（平台依据 ＋ 可复算实测）；下一轮独立复核可直接核对该引文与探针。

#### 8.35.20-㉑ 上轮独立复核「残留风险」清单的现状对照（供下一轮直接核验）

上轮复核（对 `012c8ad4`）列出 4 条残留风险 ＋ S2-1。除通用残留外，其余均已由**当前工作树 delta**
闭合，且多数有具名断言，不是口头声明：

| 上轮残留风险 | 当前 delta 状态 | 具名断言／证据 |
| --- | --- | --- |
| 570 后端窗口窄于 arch（`cancel` 态仍可写）、`request_id` 未冻结 | **已闭合**：`_FACT_IMMUTABLE_FIELDS` 增 `request_id`；`write()` 由 `state in ("submitted","confirmed")` 改为 `state != "draft"` 拒绝 | `test_the_equipment_usage_window_matches_the_native_arch`（断言 `set(_FACT_IMMUTABLE_FIELDS) == arch 的 state != 'draft' 字段集`，**按名断言闭合**）＋ `test_the_equipment_usage_guard_is_retained`；L3 步骤 `570:cancel_fact_write_refused_like_the_arch`／`570:cancel_source_link_write_refused`（64／64） |
| `workflow_contract_service` 的 `reopen` 声明在模型必然拒绝的状态上 | **已闭合**：结算族 `submitted` 去掉 `reopen`、新增 `cancel: ["reopen"]`；对应 arch 同步为 `invisible="state != 'cancel'"` | `test_reset_to_draft_is_declared_where_the_model_accepts_it`（**7 个模型 × 契约 `state_actions` 与原生 arch 两面**，断言 `declared == {"cancel"}` 且方法恒为 `action_reset_draft`）＋ `test_the_reset_to_draft_action_is_declared_where_it_runs`（实跑 `action_cancel` → `action_reset_draft`） |
| 575「登记后」修改规则待决 | **已闭合**（产品方授权口径）：只冻 `closed`，`已登记` 仍可调整 | §8.35.18-①／§8.35.19-①；`test_the_subcontract_register_freezes_only_after_closing` |
| SQL／ops 脚本直写 `state` 绕开 ORM 守卫 | **保留为通用残留**（复核已确认本仓无此类写 `state` 的脚本） | 复核原文；不属本批范围，不因本批新增而扩大 |
| S2-1 `state.copy` 缺代码层依据 | **本批收口**（见 ⑳） | `state-copy-probe.py` / `.log` ＋ `odoo/fields.py:431-434` |

#### 8.35.20-㉒ 登记验收身份与角色面的只读核对（本轮，**未起验收运行时、未升级、未写库**）

**环境**：注册验收 profile=`local` 受管入口只读预检通过 ——
`[acceptance.runtime.preflight] PASS profile=local project=sc-fe-r2-p1-01 db=sc_frontend_acceptance dbfilter=^sc_frontend_acceptance$`，
volumes `sc_fe_r2_p1_01_{db,redis,odoo}`。5175／18082 **未监听**；本轮**只**做只读查询，未执行
`acceptance.baseline.upgrade` / `backend.acceptance.up` / `frontend.acceptance.up`，未 reset fixture，未写库。

**身份实测**（`sc_frontend_acceptance`）：`fixture_role_config_admin` = uid **34**，`active=t`；直授 ＋ 隐含闭包共 **46** 组，
其中含 `SC 能力 - 项目中心只读`(82) 与 `SC 能力 - 业务配置管理员`(105) —— 即**三入口与配置工作台均落在该身份可达面内**。

**编号是运行时局部的（本轮新发现，影响一切"登记身份复核"的入口写法）**：

| 交付入口 | 验收基线 id／menu | dev 运行时 id／menu | xmlid（两库一致） |
| --- | --- | --- | --- |
| 劳务成本登记 | action **871** ／ menu **688** | action 871 ／ menu 689 | `action_sc_product_labor_cost_v1` |
| 机械台班登记 | action **566** ／ menu **691** | action **570** ／ menu 692 | `action_sc_equipment_usage` |
| 分包成本登记 | action **571** ／ menu **692** | action **575** ／ menu 693 | `action_sc_subcontract_register` |

- 仅 871 在两库同值；`570` 在验收基线指向 `sc.subcontract.request`（分包申请）、`575` 指向 `tier.review`（待我审批），
  与 dev 的 `sc.equipment.usage`／`sc.subcontract.register` **不是同一条目**。
- ⇒ 登记身份的入口必须按 **xmlid** 逐运行时重导，**不得**把 871／570／575 当作跨运行时等价地址。

**验收基线陈旧（当前阻断"登记身份浏览器实检"的直接原因）**：`smart_construction_core` 末次写入
`2026-09-10 16:06:52`（`smart_core` `2026-09-10 16:04:18`）；库内版本 **`17.0.0.162`**，
而本候选工作树 `addons/smart_construction_core/__manifest__.py` 为 **`17.0.0.168`** —— 即验收基线
落后本候选 **6 个模块版本**，**不承载本候选**的 XML／低代码记录（版本差是硬依据，不依赖时间戳推断）。
故按声明执行"登记角色浏览器实检"须先经受管 `make acceptance.baseline.upgrade`（`CODEX_NEED_UPGRADE=1`）
把验收基线推进到本候选，再 `backend.acceptance.up` ＋ `frontend.acceptance.up`（5175）。**本轮未执行该升级**，
现场保持未变；该步属**推进共享验收基线**，按授权边界**待产品方确认**（见文末）。

**角色面只读结论（三入口）**：menu 与 action **双双**持 `group_sc_cap_project_read`（＝`SC 能力 - 项目中心只读`）——
`views/menu_product_contract_completion_v1.xml:370/373/374`（三菜单 `groups=…group_sc_cap_project_read`）＋
`security/action_groups_patch.xml:276/291`（对 `action_sc_equipment_usage`／`action_sc_subcontract_register` 用
`(6, 0, [ref('…group_sc_cap_project_read')])` **覆盖** action 组）；dev 运行时实测同值（三 action 组均只含该项）。

- 同一文件内其他"编辑／登记"面用的是 `group_sc_cap_project_user`／`manager`（项目信息编辑、标书管理、质量验收、
  薪资核算清单／发放、班组借扣款登记等）⇒ **把"新建登记"面挂在"只读"能力组上，是角色口径不一致**。
- 按授权**不因组名含"只读"就直接放宽权限**，也**不因新建页能打开就判合格**：本条**登记待产品方决策**，
  最小修正范围（若判为缺陷）＝把三菜单／三 action 的组从 `group_sc_cap_project_read` 调整为项目中心经办能力组，
  并同步 `action_groups_patch.xml` 与菜单声明；**本批不改**，台账不因此变动。

**配置入口**：menu **431**「表单配置」→ action **737** `action_sc_business_config_workbench`
（模型 `ui.business.config.contract`），组＝`Smart Core Business Config Admin | Smart Core Admin | SC 能力 - 业务配置管理员`；
uid 34 持有 105 ⇒ **可达**（dev 与验收基线同构）。

**504／505／510 的拒绝原因是"导航暴露"而非"权限拒绝"（本轮实测补正）**：dev 运行时 menu 504 方单／505 零星用工／
510 机械台班记录**自身 `active=t`** 且持 `SC 基础 - 内部用户`；其**父级 319 劳务管理／320 机械设备 `active=f`**
（另 316 目标与预算、317 动态成本亦 `active=f`）⇒ 不进导航树。按授权仍一律登记为**该角色下未覆盖**，
**不写成通过、也不写成"非缺陷"**（§8.35.13-⑤ 口径不变）。

**可办理性与角色无关（机制层依据，非口头声明）**：`addons/smart_core/utils/contract_governance_form_fields.py:208`
`build_form_field_policies(data, *, contract_required_fields, is_project_form, project_form_profile, to_bool)` —— 入参
**只有契约数据**（`fields`／`field_groups`／`readonly`／必填集合），**不含 `env.user`／组／角色**；
应用端 `contract_governance_form_validation.py`／`enterprise_forms.py` 同样无角色过滤
（其 `group` 键是字段**版式**分组 core／advanced，非安全组）。⇒ 本批 a561 的无条件 `readonly` 收口
**对 `business_config_admin` 等价生效**。

**角色键控低代码面（当前无按角色分叉）**：dev 全库 `view_orchestration:%:role:*` 唯一令牌为 `role:system_admin`，
即 id **695**（`view_orchestration:sc.labor.usage:form:action:871:view:1461:role:system_admin`），`status=published`
但 **`active=false`**；**不存在** `role:business_config_admin` 记录。三入口当前消费者配置为
id 682／230／232（`*_register_productized_form_v1`，`published／active=t`）——即登记角色与 `system_admin`
**回落到同一份角色无关配置**。

**本轮边界**：未提交、未推送、未冻结、未跑 Quick、#499 未更新、台账保持 22、未起／未升级验收运行时、
未改产品代码、未创建业务样本。**待产品方决定**：是否授权推进共享验收基线（`acceptance.baseline.upgrade`）
并起 5175／18082，以取得"登记身份浏览器实检"证据；以及三入口"登记面挂只读能力组"是否判为缺陷。
#### 8.35.20-㉓ 验收运行时已按最小范围推进到本候选，并取得登记身份描述符级证据（产品方已放行）

**受管动作（全部走注册 Make 入口，无手工环境拼装）**

- 先比版本定最小范围：`smart_core` 工作树 manifest `17.0.1.1.12` **＝** 库内值 ⇒ 无需升级；仅 `smart_construction_core` 落后（库 `17.0.0.162` ＜ manifest `17.0.0.168`）。
- `CODEX_NEED_UPGRADE=1 make acceptance.module.upgrade MODULE=smart_construction_core` → **EXIT=0**（日志 `tmp/uc4-g09-creatability/acceptance-baseline-upgrade.log`，77 模块，registry 77.3s；升级前快照 `acceptance-pre-upgrade-state.txt`）。
- `make backend.acceptance.up` → `PASS db=sc_frontend_acceptance port=18082`；`make frontend.acceptance.up` → `PASS mode=development url=http://127.0.0.1:5175 db=sc_frontend_acceptance`。

**推进结果**：`smart_construction_core` **17.0.0.168 ＝ 工作树 manifest**（`write_date 09-20 13:33`）；`smart_core` 仍 `17.0.1.1.12`、`write_date` 保持 `09-10`（未被本步触碰）。

**入口（验收运行时，按 xmlid 重导，不得沿用 dev 的 871／570／575）**

| 入口 | action | menu | 组（menu 与 action 一致） |
| --- | --- | --- | --- |
| 劳务成本登记 | **871** | **688** | `SC 能力 - 项目中心只读` |
| 机械台班登记 | **566** | **691** | `SC 能力 - 项目中心只读` |
| 分包成本登记 | **571** | **692** | `SC 能力 - 项目中心只读` |
| 配置入口 `action_sc_business_config_workbench` | **720** | **417**「表单配置」 | — |

`fixture_role_config_admin`（uid 34）持有 `SC 能力 - 项目中心只读`／`SC 能力 - 业务配置管理员` ⇒ **该身份在验收运行时可达三入口与配置工作台**。**同一 xmlid 在两运行时的行 id 不同**（workbench 在 dev 是 737／431、在验收是 720／417）——再次确证 **DB 行 id 是安装历史产物、只有 xmlid 可移植**。

**“可办理”描述符级实测**（运行时库内配置，`tmp/uc4-g09-creatability/acceptance-readonly-descriptors.txt`）

| 入口 | 字段总数 | `readonly=true` | 只读集合 | 判读 |
| --- | --- | --- | --- | --- |
| 151 劳务成本登记 | 19 | **6** | `state`／`name`／`create_date`／`recorder_id`／`amount_total`／`settlement_state` | 全部为系统生成、默认提供、计算或镜像 ⇒ **用户输入事实（项目、班组、劳务单位、工时、单价等）非只读** |
| 157 机械台班登记 | 16 | **5** | `state`／`name`／`create_date`／`recorder_id`／`amount` | 同口径 ⇒ 项目、设备、使用台时、单价可填 |
| 153 分包成本登记 | 17 | **15** | `*_display` 镜像 5 项、`paid_amount`／`uninvoiced_amount`／`unpaid_amount`／`invoice_amount`／`quantity_total`（计算汇总）、`sign_date`／`source_created_at`／`source_created_by`（来源事实）、`state` | 仅 2 项可写（来源选择方向） |

- **上次产品方观察到的“项目为空却仍只读”在验收运行时已不成立**（151 的 `project_id` 等不在只读集合内）。
- 按授权口径，只读集合中的 `state`／`name`／日期类**只要有合法生成／默认来源就不算阻断**；本批**未**把“必填且只读”一律判错。
- **仍未断言（不得由描述符推断）**：153（575）的“必要事实能否经来源申请／合同路径被完整承接”，属授权工作包 1 的待验项，本轮不结论。

**身份口径与未做项（本轮边界）**

- 本次是**描述符级**证据（运行时库内配置 ＋ 组授权），**不是**浏览器实检。
- **未执行** `make acceptance.frontend.fixture`——它会按 `SC_ACCEPTANCE_FIXTURE_PASSWORD` 重置 fixture 凭据，故本轮**未取得** `fixture_role_config_admin` 的 HTTP 登录会话；验收运行时的**按身份浏览器实检**若要执行，需产品方先授权该凭据重置（另一步、另一次决定）。
- 未提交、未推送、未冻结、未跑 Quick、#499 未更新、台账保持 **22**、未改产品代码、未写业务数据。
- 运行态保持：`sc-fe-r2-p1-01`（db／redis／odoo）、`sc-backend-odoo-acceptance`（18082）、验收前端（5175，development）**在运行**；需要停止时走 `frontend.acceptance.down`／`backend.acceptance.down`。
#### 8.35.20-㉔ 登记身份的 HTTP 登录证据（受管 fixture），以及导航面残留

- 受管执行 `make acceptance.frontend.fixture`（`SC_ACCEPTANCE_FIXTURE_PASSWORD` 于**运行期生成、不落盘**）；
  该入口为 `ensure_fixture` 幂等补齐，作用域仅验收库 `sc_frontend_acceptance`（`guard_frontend_acceptance_scope` ＋
  lifecycle 锁），**未触碰 dev 库与既有草稿（含 489）**。
- `/api/v1/intent` → `login`：**http=200**，`data.user.id=**34**`、`login=fixture_role_config_admin`、
  `name=Acceptance Fixture Business Config Admin`、`company_id=8 "FE Company A"`、`lang=zh_CN`；
  `entitlement.role_code=**internal_user**`、`principal.role_xmlids=**46**`（与 SQL 侧 46 组一致）、
  `session.token` 存在、`Set-Cookie: session_id`。
  ⇒ **登记身份在验收运行时解析为 uid 34 ＋ 46 个角色 xmlid**（含 `SC 能力 - 项目中心只读`／
  `SC 能力 - 业务配置管理员`），**不是** dev 会话所显示的“系统管理员”。
- **残留（未闭合，按实登记）**：以 `session_id` cookie 续调 `session.bootstrap`／`system.init`／`navigation`
  均返回 **401**（登录响应未提供可用于 bootstrap 的 bearer 语义）⇒ **导航面未由本轮探针取得**。
  该证据应由**注册工具** `scripts/verify/menu_governance_m4_browser_audit.mjs`（Playwright＋登录页，
  `ROLES` 已含 `fixture_role_config_admin`）在需要时取得；本轮**不以自建探针冒充**该结论。
  因此“三入口在该身份**导航面**可见”仍只有**组级**依据（§8.35.20-㉓），**无导航面实测**。
- 证据：`tmp/uc4-g09-creatability/acceptance-identity-nav-probe.{py,log}`。
#### 8.35.20-㉕ 575 的合法创建路径（代码级）与三入口“可见性 vs 办理”授权不一致

**575 合法创建路径（模型 `sc.subcontract.register`）**

- `project_id` **required** 且是**普通 Many2one**（非 related／compute）⇒ 在 `draft` 下**可直接录入**；
  `_FACT_IMMUTABLE_FIELDS` 只在 `state == 'closed'` 冻结（`_FACT_IMMUTABLE_STATES = ("closed",)`）。
- **从来源承接**：`create()` 中若给出 `contract_id`，用 `vals.setdefault` 由合同带出
  `project_id`／`subcontractor_id`／`currency_id`；`request_id` 为来源分包申请。
- **默认值**：`register_date`＝当日、`currency_id`＝公司币种、`responsible_id`＝当前用户、
  `name`＝`sc.subcontract.register` 序列（默认“新建”时替换）。
- **空白入口行为**：不选来源时 `project_id` 必填会阻断保存，不产出缺项记录；
  `state` 非 `draft` 一律被 `create()` 守卫拒绝（`分包登记状态只能通过受控业务动作推进`）。
- **首次偏差定位＝无偏差**：原生 arch `readonly="state == 'closed'"` ⇔ 模型 `_FACT_IMMUTABLE_FIELDS`／`("closed",)`
  ⇔ 153 配置描述符（`project_id` **OPEN**、`note` OPEN）。即“项目为空且不可填写”在**当前候选**三层均不成立；
  产品方上次观察属**前一次候选**，本批已收口（仍需产品方在浏览器确认）。
- **仍未断言**：153 描述符只覆盖 17 个字段（`request_id`／`contract_id`／`subcontract_scope`／`register_date`
  等**不在其中**，由原生 arch 呈现）⇒ “来源选择后必要事实正确承接”须以运行时来源路径实测，本轮未做。

**三入口“可见性 vs 办理”授权不一致（本轮新发现，登记待决策）**

| 入口 | 菜单／action 可见性 | 办理按钮门禁 |
| --- | --- | --- |
| 871 劳务成本登记 | `group_sc_cap_project_read` | **无 `groups` 门禁**（提交／确认／退回／取消全开） |
| 570 机械台班登记 | `group_sc_cap_project_read` | 提交＝`project_user`／`manager`；确认台班＝`manager`；退回／取消＝`user`／`manager` |
| 575 分包成本登记 | `group_sc_cap_project_read` | 确认登记／关闭／重新打开／退回＝`project_manager`；取消＝`user`／`manager` |

- 即**同一交付组内**：可见性一律挂“只读”，而办理所需能力**三者各不相同**（871 无、570 部分、575 全部要经理）。
- `fixture_role_config_admin`（uid 34）持 **82 只读＋83 经办＋84 审批＋105 业务配置管理员** ⇒ 三入口**可编辑且可办理**。
- **只读-only 角色**：可打开三入口并在 `draft` 填字段，但在 570／575 **无任何办理按钮**、在 871 却可提交确认 ——
  权限面自相矛盾。
- **最小修正范围（若判为缺陷；本批未改）**：三入口菜单／action 的组由 `group_sc_cap_project_read` 调整为
  `group_sc_cap_project_user`（经办），并为 871 的四个按钮补齐与 570／575 同口径的门禁；
  同步 `views/menu_product_contract_completion_v1.xml`、`security/action_groups_patch.xml` 与三份 core views。
  按授权**不因组名含“只读”或按钮缺失就自行放宽权限**，留产品方裁定。
#### 8.35.20-㉖ 三入口来源承接的 L3 断言收口、金额重复标签的证据更正（2026-09-20）

**1）来源承接：把「来源选择后必要事实正确承接」从代码级提升为回滚事务实测**

§8.35.20-㉕ 登记的「仍未断言」项（153 描述符只含 17 字段，`request_id`／`contract_id`／
`subcontract_scope`／`register_date` 由原生 arch 呈现）现以 `g09_txn_verify.py` 的 **7 条新断言**收口
（**新增，零删除**；64 → **71**，`failed=[]`、`gaps=[]`、收尾 `rollback:no_*_left` 全过）：

| 新断言 | 结论 | 机制／证据 |
| --- | --- | --- |
| `575:source_contract_supplies_context` | 只给 `contract_id` ＋范围＋明细即可建档；`project_id`／`subcontractor_id`／`currency_id` 由合同 `vals.setdefault` 带出 | 实测 `project=427(427)`、`partner=5387(5387)`、`currency=6(6)`，与合同逐项相等 |
| `575:blank_entry_refused_without_project` | 无项目、无合同时**不产出缺项记录** | 平台 `psycopg2.errors.NotNullViolation`（`column "project_id"`） |
| `575:explicit_project_conflicting_with_contract_refused` | 显式字段与合同范围冲突时被拒，**不是**静默以合同为准 | `ValidationError：分包登记显式字段与权威分包合同范围冲突。` |
| `570:source_request_does_not_supply_project` | 来源设备申请**不**补齐上下文（它是来源追溯，不是录入替代） | 仅给 `request_id` 时 `project_id` 必填被库层阻断 |
| `570:matching_source_request_submits` | 项目与来源申请一致时才可提交 | `state=submitted`，`request=25` |
| `570:mismatched_source_project_refused_at_submit` | 项目与来源申请不一致在**提交时**被拒，记录留在 `draft` | `UserError：设备使用登记的项目必须与来源设备申请一致。` |
| `871:blank_entry_refused_without_project` | 871 **无来源单据字段**：正式路径＝草稿窗口内直接录入；空白入口被阻断 | 平台 `NotNullViolation`（`column "project_id"`） |

- 四条「拒绝」类断言的 detail **记录实际异常类**：平台机制（`NotNullViolation`）与业务校验
  （`UserError`／`ValidationError`）分开登记，不把平台行为记成业务规则，也避免只测一种机制。
- 每条尝试在**自有 savepoint**（`cr.savepoint()`）内执行：被拒的 `create` 即便已落到 `INSERT`
  （575 的权威校验发生在 `super().create()` 之后）也不会污染后续断言或收尾计数。
- 由此三条合法创建路径为：**871＝草稿内直接录入**；**570＝先选项目，来源申请只做一致性校验**；
  **575＝选合同即建档，或先选项目再录入**。三者**都不需要**解除任何前端只读。

**2）金额重复标签：引用证据更正，不变量改为可重复断言**

§8.35.14-④ 记的「截图证据 `shot-price_unit.png`」**在当前工作树内不存在**（全仓查找无此文件；
`tmp/` 被 gitignore，佐证不随分支保存）。因此该处「视觉上只显示一次」的**视觉结论降级为未证实**，
不再作为「非缺陷」的依据；文本提取（`innerText` 等）出现重复仍属无障碍隐藏标签的正常产物。

为把该不变量从「一次性截图」改为**可重复**，在既有受管入口
`make verify.frontend.professional_business_value.unit` 的守护脚本中加入三项固定：

- `ScMoney.vue` **必须保留**可访问名称载体（`class="sc-visually-hidden"` ＋ `{{ label }}：`），
  且**不得**在其自身 style 块覆盖该共享类——禁止以删除无障碍语义换版面；
- 共享类 `.sc-visually-hidden`（`styles/product-patterns.css`）**只允许声明一次**，且必须同时保留
  `position:absolute`／`width:1px`／`height:1px`／`overflow:hidden`／`clip:rect(0,0,0,0)`／
  `clip-path:inset(50%)`（均 `!important`）：任一属性丢失即失败，因为那正是「隐藏标签意外可见」的成因；
- 断言**不依赖 TDesign 内部选择器**，只读本仓设计系统自身的类名与共享样式。

改动落在 **P4 守护**（`scripts/verify/frontend_professional_business_value_guard.py` 及其单测），
**未改产品代码、未改共享样式本身**（结构上已满足，故无改动必要）。新增两条 sabotage 对照
（抽掉 `clip-path`、抽掉可访问名称载体各自失败）证明该固定不是空断言；
`make verify.frontend.professional_business_value.unit` ⇒ **PASS**（`families=7`、单测 5/5、`EXIT=0`）。

**3）状态与边界（本轮）**

- 工作树 `HEAD` 仍为 `012c8ad43dde211e6e29f96d609665cfc48d71cb`；**未提交、未推送、未冻结、未跑 Quick、
  未更新 #499、未合并**；台账保持 **22**（22→19 仍只是预期核减）；G10 未启动。
- 本轮**产品代码改动＝0**：改动仅 P4 守护 ＋ 本记录（纯追加），`addons/smart_construction_core` 未动。
- 本记录**不构成产品验收**：金额标签的**视觉**结论、三入口「可见性 vs 办理」的角色门禁裁定、
  导航面实测，仍需产品方在浏览器确认。
#### 8.35.20-㉗ 导航面残留的定性更正：401 是探针缺陷；导航面已按受管方法实测（2026-09-20）

**1）更正：§8.35.20-㉔ 记的「导航面 401 ⇒ 该角色下未覆盖」不成立**

按代码核对，那三条 401 **都不是权限结论**，而是探针的凭证／目标缺陷，必须改判，
不得再当作「该角色看不到导航」的证据：

| 探针当时调用 | 事实 | 判定 |
| --- | --- | --- |
| `session.bootstrap` | 是 **dev/test 专用**的 token 铸造端点（`handlers/session_bootstrap.py`：`ENV` 非 dev/test ⇒ 403；无 `SC_BOOTSTRAP_SECRET` ⇒ 404；secret 不符 ⇒ 401 `invalid bootstrap secret`）。它在验收运行时（`ENV=acceptance`）**必然**不返回导航，与角色无关 | 目标选错 |
| `navigation` | 处理器目录内**不存在**该 intent（导航面只有 `system_init.py`／`menu_configuration.py`） | 目标不存在 |
| `system.init` | 是**唯一的**登录态导航面（`REQUIRED_GROUPS = []`，登录用户可用；`data.navigation.nav` 即交付导航契约） | 目标正确 |
| 三次调用的共同缺陷 | 探针拿到 token 后**没有发送** `Authorization: Bearer`——而 `get_principal_from_token()` 只认 `Authorization` 头或 Odoo session uid，login 走的是 token 而非 session——故 401 文案是 `AUTH_REQUIRED 认证失败或 token 无效` | **凭证未随请求发送** |

⇒ 401 属**认证形态**结果（`AUTH_REQUIRED`），不是 `PERMISSION_DENIED`（403）。
「该角色下未覆盖」的登记撤回，改记「探针未取得，原因＝凭证未随请求发送」。

**2）更正后实测：导航面按批次已接受的同一条方法取得（dev，只读）**

新探针 `nav-plane-probe.py` 沿用 `login → Bearer → intent`（与该批 `http-serve-probe.py` 完全同形），
目标改为 `system.init`；入口集继续消费 `entry-family.json`，菜单身份取自交付台账，**不在探针里重述**。

| 身份 | uid | `nav_meta.role_surface_code` | 导航节点 | a871 | a570 | a575 | a561／a562／a563／a851 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `sc_test_admin` | 51 | `system_admin` | **110** | **served** | **served** | **served** | 不 served |
| `demo_role_pm` | 42 | `pm` | **30** | 不 served | 不 served | 不 served | 不 served |

- 三个登记入口在 `sc_test_admin` 下**确实出现在导航中**，并带回完整父级路径：
  `系统菜单 / 项目中心 / 劳务成本 / 劳务成本登记`、`… / 机械成本 / 机械台班登记`、`… / 分包成本 / 分包成本登记`
  ⇒ 菜单身份与交付台账一致，「能打开」在导航层是可复现的，不是偶发。
- `demo_role_pm` 的 `denied_menu_xmlids` 只有招投标 5 项（`menu_sc_tender_*`／`menu_sc_project_tender`），
  **不含**三个入口 ⇒ PM 的不可见属**未授予**，不是**显式拒绝**；两类原因不可混记。
- 登录响应的 `principal.role_xmlids` 本轮**首次落盘**（`sc_test_admin` 58 项／`demo_role_pm` 25 项），
  补上上一轮「角色 xmlid 只有口头观察、无持久证据」的缺口。

**3）登记角色的**声明面**（取自运行时的 `role_surface_map`，可移植）**

| 角色 | `role_surface_code` | `menu_xmlids` | `primary` | `admin` | `denied` | 三个入口菜单是否在任一桶 |
| --- | --- | --- | --- | --- | --- | --- |
| 业务配置管理员 | `business_config_admin` | 2 | 1 | 6 | 0 | **均不在** |
| 项目经理 | `pm` | 3 | 25 | 0 | 5 | 均不在 |
| 系统管理员 | `system_admin` | 0 | 0 | 1 | 0 | 均不在 |

- 关键口径：`system_admin` 的声明桶几乎为空，却实测服务 110 个菜单 ⇒ 该声明面**不是**穷尽式白名单，
  而是叠加在「基础菜单组门禁」之上的强调／例外声明（`exposure_policy_declared=true`、`deny_all_navigation=false`）。
  因此**不能**由「声明面里没有」推断「看不到」。
- 由此对登记身份（`business_config_admin`，uid 34，46 个角色 xmlid，含 项目中心只读／经办／审批 82／83／84）的
  **推断（非实测）**：三个入口菜单的门禁是 `group_sc_cap_project_read`，uid 34 持该组且未被任何拒绝清单命中，
  **预期可见**。该推断必须由产品方浏览器复核证实，本批**不据此改任何权限**。

**4）仍未闭合**

- 登记身份的**实测**导航面：需在验收运行时按同一方法重跑一次
  （`G09NAV_BASE=http://127.0.0.1:18082`、`G09NAV_DB=sc_frontend_acceptance`、`G09NAV_ROLE=business_config_admin`），
  而验收 fixture 口令**不在工作树内**（运行期生成）。本轮**未**轮换该口令，以免打断产品方正在进行的浏览器复核。
- 三条「可见性 vs 办理」的角色门禁裁定仍待产品方决定（本批未改任何权限）。
#### 8.35.20-㉘ 871 办理门禁与 570／575 的同族不一致：定性、最小修正范围与「未纳入」理由（2026-09-20 只读）

**问题**：同属「成本登记三件套」的 871（`sc.labor.usage`）／570（`sc.equipment.usage`）／575（`sc.subcontract.register`），
在办理动作上的角色门禁是否同口径？本节只做**只读**核定与登记，**未改任何权限、未改任何产品代码**，台账保持 **22**。

**1）交付面：库内 `ir.ui.view.arch` 实测（不是源码阅读）**

| 入口 | 原生表单 | 办理按钮 | `groups=` |
| --- | --- | --- | --- |
| 871 | `view_sc_labor_usage_form` | `action_submit` | **（无）** |
| 871 | 同上 | `action_confirm` | **（无）** |
| 871 | 同上 | `action_reset_draft` | **（无）** |
| 871 | 同上 | `action_cancel` | **（无）** |
| 570 | `view_sc_equipment_usage_form` | `action_submit` | `group_sc_cap_project_user,group_sc_cap_project_manager` |
| 570 | 同上 | `action_confirm` | `group_sc_cap_project_manager` |
| 570 | 同上 | `action_reset_draft` | `group_sc_cap_project_manager` |
| 570 | 同上 | `action_cancel` | `group_sc_cap_project_user,group_sc_cap_project_manager` |
| 575 | `view_sc_subcontract_register_form` | `action_register`／`action_close`／`action_reopen`／`action_reset_draft` | 均为 `group_sc_cap_project_manager` |
| 575 | 同上 | `action_cancel` | `group_sc_cap_project_user,group_sc_cap_project_manager` |

- 871 的四个办理按钮**在 XML 上没有任何 `groups` 门禁**；唯一继承该表单的视图
  （`view_sc_labor_usage_product_advisory_form`）只追加 `办理提示` 区块，**不补门禁** ⇒ 这是该表单的完整交付面。

**2）ACL 行**：570／575 各有 4 行（只读 r／经办 r,w,c／项目审批 r,w,c,u／超级管理员 r,w,c,u）；
**871 只有 3 行**（只读 r／经办 r,w,c／项目审批 r,w,c,u），表面上**缺 `group_sc_super_admin` 行**；
- 但该缺失**无功能影响**：`group_sc_super_admin` 的 `implied_ids` 含 `group_sc_cap_project_manager`
  （实测闭包 57 个组、**传递持有**项目审批组），而 871 的项目审批行本身就是 r,w,c,u ⇒ 只持超级管理员组的用户
  对 871／570／575 三者的 `check_access_rights("write")` **实测均为 True**。故 871 的该缺口属**冗余缺失**，
  **不是**「比兄弟更严」，也不是可用的放宽空间。

**3）组层级**：`只读` ⊂ `经办` ⊂ `审批`（`implied_ids` 实测严格递进）。
⇒ 只读、经办、审批三层里，**经办与审批都持 write**，ACL 层面**无法表达**「经办不得审批」。

**4）行级规则**：871 把 `read/write/create` 的「本人或项目成员」规则挂在**只读**组上；
570／575 把该规则挂在**经办**组上、只读组只有 `read`。当前被 ACL 的 `write=0` 兜住，**无实际提权**，属结构错位。

**5）运行态角色差异（决定性；三个角色均为临时用户，SAVEPOINT 内建自己的草稿后回滚）**

| 入口 | 只读 | 经办（仅 `项目中心经办`） | 审批 |
| --- | --- | --- | --- |
| 871 | 建档即拒（`AccessError`，ACL 无 create） | 建档＋提交 **通过**；**审批 `action_confirm` 也通过** | 通过 |
| 570 | 建档即拒（ACL 无 create） | 建档＋提交通过；审批被拒：`UserError: 只有项目审批人员可以确认机械台班。` | 通过 |
| 575 | 建档即拒（ACL 无 create） | 建档＋提交被拒：`UserError: 只有项目审批人员可以确认分包成本登记。` | 通过 |

- 探针 v1 曾把种子单据建在 `sudo` 名下，`create_uid` 不是被测用户，触发 `ir.rule` 的
  「本人或项目成员」分支，**把行级拒绝伪装成方法级拒绝**；v2 改为「以被测身份建自己的草稿」后该混淆消除，
  差异收敛到方法级门禁本身。两版差异与原因一并留档，避免后续把 v1 的 `top-secret records` 读成门禁结论。

**6）定性**：871 **缺方法级办理门禁**，属**同族口径不一致（缺陷）**。
理由：ACL 与行级规则都无法区分「经办」与「审批」（审批组蕴含经办组、两者都持 write），
570／575 正是用方法级 `_check_project_operator()`／`_check_project_manager()` 补上这一层，871 没有 ⇒
**经办可自审自批**，且只读角色在 871 上看得见办理按钮（570／575 由按钮 `groups` 隐藏）。
**不采用**「ACL 已足够」的解释：ACL 只拦得住**没有 write 的角色**，拦不住**同为经办角色的自审**。

**7）最小修正范围（本轮未实施，待产品方决定是否纳入本批）**

- `models/core/labor_management.py`：新增 `_check_project_operator()`／`_check_project_manager()`
  （与 570／575 同文同形，含 `group_sc_super_admin` 放行）；随后 `action_submit`→经办、
  `action_confirm`→审批、`action_cancel`（`submitted`⇒审批／`draft`⇒经办）、`action_reset_draft`→审批。
- `views/core/labor_management_views.xml` 的 `view_sc_labor_usage_form`：四个按钮补 `groups=`
  （提交／取消＝经办,审批；确认／退回草稿＝审批）。
- 测试：**新增**角色分离断言（经办能提交、不能确认；只读不能提交），
  **保留**既有字段完整性与结构同源断言。
- **不**改 ACL、**不**轮换角色、**不**放宽任何权限；`group_sc_super_admin` 缺行属**冗余缺失**
  （超级管理员组蕴含项目审批组，实测 write 仍为 True，见 §2 更正）与行级规则挂错组
  （当前被 ACL 的 `write=0` 兜住、无实际提权）两项只登记、不在本批处理。
- 影响面：`view_sc_labor_usage_form` 是 **4 个入口共享**的原生主表单 ⇒ 修正会同时作用于所有消费者，
  需在代表入口补验、兄弟入口只补受影响反例。

**8）为什么不纳入本轮的「创建态可办理性」修复**

- 871 的 `confirmed` **不**写入项目成本台账（`_sync_project_cost_ledger` 只存在于 570 的 `sc.equipment.usage`），
  也**不**被劳务结算的台账锚点校验（`ScLaborSettlement._check_business_anchor` 只校验来源的 `settlement_state`）；
- 其可观察后果是报表投影 `models/projection/labor_subcontract_report.py` 把该记录呈现为 `lifecycle_state='confirmed'`。
- ⇒ 风险定级 **中低**（控制面不一致＋报表可见），但**不是**「新建页填不出必要字段」的同类问题，
  故与创建态修复**分开**，本轮**未改**、**未放宽**、也**未**据此扣台账。

**9）证据**

| 文件 | 内容 |
| --- | --- |
| `tmp/uc4-g09-creatability/role-gate-probe.py` | 只读探针（`SAVEPOINT` ＋ `ROLLBACK`，无残留；三个界面桶全量落盘） |
| `tmp/uc4-g09-creatability/role-gate-summary.json` | arch 13 条／ACL 11 条／角色断言 18 条／行级规则 11 条 |
| `tmp/uc4-g09-creatability/role-gate-probe.log` | 原始运行日志（含 `EXIT=0` 与回滚核对 `no residual`） |
| `tmp/uc4-g09-creatability/superadmin-acl-probe.py` / `.json` | 超级管理员组闭包实测：`SC 超级管理员（全能力）`
  传递持有 `SC 能力 - 项目中心审批`；只持该组时三入口 `write` 均为 True（用于更正 §2 的初判） |

- 运行方式：`docker exec -i sc-local-dev-odoo-1 odoo shell -d sc_dev_demo -c /var/lib/odoo/odoo.conf --log-level=error`
  （**必须**带 `-c /var/lib/odoo/odoo.conf`：`addons_path` 里 `/mnt/source-addons` 指向工作树且优先于 `/mnt/product-addons`，
  缺该参数会加载到不含本仓模块的库并使 `sc.labor.usage` 等模型不可见）。
#### 8.35.20-㉙ 871 办理门禁按 §㉘ 的最小范围实施与定向补验（2026-09-20；**产品复核前**）

产品方「同意 继续推进」⇒ 按 §8.35.20-㉘ 给出的最小范围**收紧** 871 的办理门禁。本次**只收紧**：
不动 ACL、不动行级规则、不放宽任何权限、不动菜单与角色、记账台账**保持 22**。

**1）改动（2 个产品文件，其余为测试）**

| 文件 | 内容 |
| --- | --- |
| `models/core/labor_management.py` | `ScLaborUsage` 新增 `_check_project_operator()`／`_check_project_manager()`，与 570 `ScEquipmentUsage`、575 `ScSubcontractRegister` **同文同形**（含 `env.su` 与 `group_sc_super_admin` 放行）；`action_submit`→经办、`action_confirm`→审批、`action_cancel`（`submitted`⇒审批／`draft`⇒经办）、`action_reset_draft`→审批 |
| `views/core/labor_management_views.xml` | `view_sc_labor_usage_form` 的四个办理按钮补 `groups=`（提交／取消＝`project_user,project_manager`；确认／退回草稿＝`project_manager`），与 570 同口径 |

**影响面（必须由产品方确认的一点）**：`view_sc_labor_usage_form` 是 **871／562 方单／563 零星用工／
561 劳务用工 四个入口共享**的主表单 ⇒ 门禁同时作用于这四个消费者。族载体
`labor_usage_form_productization_contract.xml` **不声明任何角色／审批语义**（实测该文件无 `审批／经办／角色／权限` 字样），
因此本次口径取自 570／575 的既有同族标准，而不是某个入口的独立声明。**该口径对 562／563／561 是否同样成立，列为产品复核关注点。**

**2）新增断言（零删除）**

| 文件 | 新增 |
| --- | --- |
| `tests/test_labor_product_capability.py` | `test_the_labor_usage_approval_is_capability_governed_like_its_siblings`（只读建档即拒／经办可提交不可确认／审批可确认，并固定「被拒的审批不得推进状态」）＋ `test_the_labor_usage_return_to_draft_and_cancel_are_capability_governed`（草稿取消＝经办范围内；已提交取消与已取消退回草稿＝需审批能力） |
| `tests/test_usage_performance_native_lowcode.py` | `test_every_workflow_button_declares_its_capability_gate`：三入口的办理按钮 `groups` 必须与它们所调用的模型方法同口径 |

**3）定向补验（受影响检查，非全系统矩阵）**

| 项 | 结果 | 日志 |
| --- | --- | --- |
| 模块升级 | **PASS**（`local.dev.ready` ＋ `local.dev.demo.authority` PASS） | `871-gate-upgrade.log` |
| 焦点类 | **35 测 0 failed 0 error**（`TestLaborProductCapability` 3 ＋ `TestUsagePerformanceNativeLowcode` 32），三个新测**均已实跑** | `871-gate-l2-focused-final.log` |
| 受影响类 | `TestP0StateClosure` 78 测 **0 failed**、`TestProductReports` 1 测 **0 failed**；`TestUserFeedbackBusinessViews` 72 测 **28 failed = 已登记基线集合** | `871-gate-l2-affected.log` |
| sabotage 对照 | 抽掉 871 `action_confirm` 的 `groups` 后新断言 **FAIL**（`[] != ['group_sc_cap_project_manager']`）；恢复后 PASS ⇒ 断言非空转 | `871-gate-sabotage-{upgrade,test}.log`、`871-gate-restore-upgrade.log` |
| 运行态角色探针复跑 | 871 经办审批 **由「通过」变为被拒**：`UserError：只有项目审批人员可以确认劳务成本登记。`；审批通过；570／575 不变；**回滚无残留** | `role-gate-probe.log` |

**4）`TestUserFeedbackBusinessViews` 28 项失败的归因（复用已登记证据，不重跑基线）**

- 该类的 28 项失败是**已在基线态复现过的既有集合**（`uc4_tax_deduction_native_lowcode_20260918.md` §失败归因、
  本文档 §8.14 第 1167 行：把该批产品文件 `git checkout` 回基线并重新 upgrade 后得到**完全相同**的 28 项集合，`diff` 为空）；
  成因为**测试数据漂移**（`发票合同类型必须与发票业务类型一致`／`必须关联已归属公司的有效项目`／`currency_id` 可见性／`legacy_*` 列）。
- 本轮**独立复核该归因仍然成立**：28 项失败断言全部落在 **tree 视图**与 `legacy_*` 列、费用／扣款项目归属、
  currency 可见性、税务中心与自筹退款菜单上；该类**不读取** `view_sc_labor_usage_form` 的按钮
  （例：`test_labor_equipment_subcontract_lists_expose_totals_and_source_type` 只读 17 个 **tree** 的 `arch_db`，
  失败点为考勤 tree 缺 `legacy_fact_type`）。本次两个产品文件与该集合无交集。

**5）未覆盖 / 待产品方裁定**

- 该门禁对 **562／563／561** 三个兄弟消费者的产品语义尚未经产品方确认（见 §1 影响面）。
- §8.35.20-㉘ 登记的另两处不对称（超管 ACL 行＝冗余缺失、行级规则挂错组）**仍未处理**，本次不扩大范围。
- `verify.p1.daily_business_visible_contract.audit` **未跑**：它要求具名审计登录的 HTTP 运行凭据，
  且其断言面是**列表／表单字段与章节**（`missing_list_fields`／`missing_form_fields`／`missing_form_sections`），
  **不含按钮与 `groups`**，与本次改动无交集。

**6）状态口径**：本轮=「实施 ＋ 定向补验完成，**待产品方浏览器复核**」；**未**冻结候选、**未**跑 exact-head Quick、
**未**推送、#499 **未更新**（远端仍 `012c8ad4`）、**未**合并、台账 **22**、G10 未启动。

#### 8.35.20-㉚ 575 明细级冻结闭合：单头冻结的旁路实测与最小修正（2026-09-20；**产品复核前**）

**授权依据**：产品方「同意 继续推进」＋此前指令「若业务规则要求事实不可改，须核对后端写入约束，
**不能仅靠 XML 只读宣称安全**」。本节是该指令的执行结果：先实测，再按**只收紧**补最小守卫。

**1）实测缺口：单头冻结不覆盖明细模型**

只读探针 `tmp/uc4-g09-creatability/575-line-freeze-probe.py`（`SAVEPOINT` ＋ `ROLLBACK`，
显式传 `name` 以免消耗 `ir.sequence`）在**修复前**的实测结果：

| 写入路径 | 修复前 | 修复后 |
| --- | --- | --- |
| `register.write({"subcontract_scope": ...})`（单头事实） | BLOCKED | BLOCKED |
| `line.write({"work_scope"/"registered_amount"/"contract_qty"})` | **ALLOWED** | BLOCKED |
| `line.create`（向已关闭登记补明细） | **ALLOWED** | BLOCKED |
| `line.unlink()` | **ALLOWED** | BLOCKED |
| `register.state` 经 `write()` 直接改 | BLOCKED | BLOCKED |

- 即：`arch` 与单头 `write()` 都已声明「已关闭冻结」，但**明细模型自身**是可写入口——
  `已关闭` 登记的登记金额／数量／明细集合仍能被改写、增补、删除。这正是「XML 只读 ≠ 安全」的实例。
- 副作用实测：修复前该轮次结束时单头冻结已被绕过（`line_unlink` 成功、金额被改写）；
  探针全部在回滚事务内，`residual_after_rollback = 0`，库内无残留。

**2）最小修正（只收紧，不扩冻结集、不改状态机）**

`addons/smart_construction_core/models/core/subcontract_management.py` → `ScSubcontractRegisterLine`：

- 新增 `_sc_check_registers_frozen(registers)`：与单头**同冻结集**（`_FACT_IMMUTABLE_STATES`）、
  **同提示语**（「已关闭的分包登记不可修改登记事实或明细；请先执行「重新打开」回到已登记状态。」）、
  **同内部上下文放行**（`_COST_SOURCE_STATE_CONTEXT_KEY`）；
- 挂到 `create()`（校验目标登记）、`write()`（校验当前登记**与**改挂目标）、`unlink()`。
- **未**改动：冻结集本身、状态机、角色门禁、`draft`／`active` 的可调整性、任何字段或视图。

**3）补验（定向，全部 PASS）**

| 项 | 结果 | 日志（`tmp/uc4-g09-creatability/`） |
| --- | --- | --- |
| 升级 | PASS | `575-line-guard-upgrade.log` |
| 探针复跑 | 单头＋明细 4 条路径全 BLOCKED；`active` 明细写 **ALLOWED**（正例）；内部上下文 **ALLOWED**（受控动作不被自己挡住）；`residual_after_rollback = 0` | `575-line-freeze-probe.log` |
| 焦点类 | `/TestLaborProductCapability,/TestUsagePerformanceNativeLowcode` = **35 测 0 failed 0 error**（扩展后的 `test_the_subcontract_register_freezes_only_after_closing` 实跑通过） | `575-line-guard-l2-focused.log` |
| 受影响类 | `TestSubcontractCostRegistration` ＋ `TestUmP3SubcontractRegisterSettlementAuthorityBoundaries` ＋ `TestP0StateClosure` ＋ `TestProductReports` = **80 测 0 failed 0 error** | `575-line-guard-l2-affected.log` |
| sabotage | 抽掉 `write()` 内的守卫 ⇒ 目标测试 **FAIL**；恢复（`sha256 fa10c937…` 前后一致）后 **PASS** | `575-line-guard-sabotage-test.log`／`575-line-guard-restore-test.log` |

**新增断言（零删除）**：`test_the_subcontract_register_freezes_only_after_closing` 内追加
`line.write`／`line.write`（金额）／`line.create`／`line.unlink` 四条反例 ＋ 「明细未被删除、金额未变」正例。

**4）未纳入／仍待裁定**

- **`active` 明细可调整维持不变**：`已登记` 是分包结算的法定锚点，冻结集**只有** `closed`（与产品方指令一致）。
- 仍待裁定：`closed` 之外是否还需对**已被结算引用**的明细加事实锁——当前只有 `unlink()`（保审计关系）
  与 `action_reopen`（有结算引用即拒）表达该约束，事实字段本身仍可调整。
- §8.35.20-㉘ 登记的另两处不对称（超管 ACL 行＝冗余缺失、行级规则挂错组）**仍未处理**。
- 575 菜单 **518** 与 561 菜单、`reactivate` 前端键、登记身份实测导航面、三条「可见性 vs 办理」门禁裁定
  **均未在本批**。

**5）状态口径**：仍为「实施 ＋ 定向补验完成，**待产品方浏览器复核**」；**未**冻结候选、**未**跑
exact-head Quick、**未**推送、#499 **未更新**（远端仍 `012c8ad4`）、**未**合并、台账 **22**、G10 未启动。

#### 8.35.20-㉛ 871／570／575 权限面四处结构不对称的只读核定：哪一处有实际权限差（2026-09-20）

**授权依据**：产品方「同意 继续推进」＋既有指令「若确有权限缺陷，单独给出最小修正范围，再决定是否纳入本批」。
本节**只做只读核定**，不改规则、不改 ACL、不改前端；`security/**` 与 `frontend/**` 本轮**零改动**。

**1）实测方法**

`tmp/uc4-g09-creatability/readonly-visibility-ab-probe.py`（`SAVEPOINT` ＋ `ROLLBACK`，`residual=0`）：
(a) 只持 `项目中心只读` 的临时用户，读「本人创建、但项目既非其负责也非其关注」的记录；
(b) 同一用户读「项目负责人＝本人」的记录；(c) 只持 `业务配置管理员` 的用户读他人创建的记录。

| 探针项 | 871 | 570 | 575 |
| --- | --- | --- | --- |
| 只读身份读「本人创建但非成员」 | **可见（1）** | 不可见（0） | 不可见（0） |
| 只读身份读「本人负责项目」 | 可见（1） | 可见（1） | 可见（1） |
| 只读身份尝试 `write` | BLOCKED | BLOCKED | BLOCKED |
| 配置管理员读他人记录／写入 | 可见／ALLOWED | 可见／ALLOWED | 可见／ALLOWED |

**2）四处不对称的逐项定性**

| # | 不对称 | 871 现状 | 570／575 形态 | 实测是否有实际差 |
| --- | --- | --- | --- | --- |
| 1 | own-or-member 规则挂载组 | 挂**只读**（`group_sc_cap_project_read`） | 挂**经办**（`group_sc_cap_project_user`） | **有**（与 #2 同因） |
| 2 | 只读缺「仅项目成员」读规则 | 无；只读沿用 own-or-member（含 `create_uid = user.id`） | 有独立 `...by project member` 规则、仅 `perm_read` | **有**：只读可见面偏松（见上表第 1 行） |
| 3 | 超管 `ALL` 行级规则 | 缺（其 `ALL` 规则挂在**审批**） | 有（挂 `group_sc_super_admin`） | 无（超管闭包已持审批 ⇒ 同一 `ALL` 规则生效） |
| 4 | 配置管理员 `ALL` 行级规则 | 缺 | 570 有、575 缺 | 无（配置管理员闭包已持审批＋经办，实测三处一致） |
| — | 超管 ACL 行（`ir.model.access.csv`） | 缺 | 有 | 无（闭包已持审批 ⇒ `write=True`，见 §㉘） |

- 结论：**只有 #1／#2 有可观测行为差**——871 的只读身份能看到「本人创建但已非项目成员」的历史记录，
  570／575 看不到。**不是提权**（写权限三处一致被 ACL 拒绝），是**只读可见面偏松**。
- #3／#4 与超管 ACL 行属**结构不对称**（命名与挂载组不同），实测无权限差；修复它们不产生行为变化，
  但其中「补 ACL 授予行」在语义上是**新增授权**，与「只收紧不放宽」冲突，故**不建议**纳入。

**3）最小修正范围（已写成提案，本轮未应用）**

`tmp/uc4-g09-creatability/rule-align-871.proposed.patch` —— 单文件
`addons/smart_construction_core/security/sc_record_rules.xml`，两处：

1. `rule_sc_internal_labor_usage` 挂载组 `只读` → `经办`，名称对齐为
   `SC Project User - labor usage own or project member`（域**不变**）；
2. 新增 `rule_sc_project_read_labor_usage`（挂 `只读`、仅 `perm_read`、
   域 `['|', ('project_id.user_id','=',user.id), ('project_id.message_follower_ids.partner_id','=',user.partner_id.id)]`），
   与 570 的 `rule_sc_project_read_equipment_usage` 同形。

- **预期行为变化（需产品方确认）**：只读身份不再能看到「本人创建但已非项目成员」的记录；
  经办（继承 own-or-member）与审批（`ALL`）**不变**——经办域与现状逐字相同，故经办路径无回归。
- **未应用原因**：该改动改变**只读可见面**（真实用户可见记录数变化），属产品可见行为，
  超出「实施类」授权范围，须产品方明确纳入。

**4）另发现一处待裁定（前端）**

`frontend/apps/web/src/app/contracts/v2/workflowActionAvailability.ts`：
`knownKeys` 与 `workflowActionMethodAliases()` **均未登记**本批新增的 `reactivate` 键（`action_reopen`）。

- 现状：合同行存在时（`state_actions.closed: ["reactivate"]`）可正常解析；**行缺失／载荷过期**时
  `isKnownTransition` 返回 `false` ⇒ 归为 `unmanaged` ⇒ 前端据 `contractFormPresenter` 第 597 行
  **保持按钮可用**（fail-open），用户点击后才由后端拒绝，而不是显示「当前流程状态不允许执行该操作」。
- 最小修正（2 行，严格收紧）：在 `workflowActionMethodAliases()` 增 `reactivate -> ['action_reopen']`，
  并把 `reactivate` 加入 `knownKeys`。
- **未应用原因**：属前端交付面（`frontend/**`），需 `pnpm lint && typecheck:strict && build` 前端门禁，
  且会扩大本批交付面，须产品方明确纳入。

**5）状态口径**：台账 **22**；**未**合并、**未**冻结、**未**跑 Quick、#499 远端仍 `012c8ad4`、G10 未启动；
`security/**` 与 `frontend/**` 本轮零改动。

#### 8.35.20-㉜ 登记验收身份的导航面闭合：服务端只读解析（2026-09-20；免口令）

**背景**：§8.35.13-③／-④ 与本批多轮均把「登记身份（`business_config_admin`）的实测导航面」
列为未闭合，原因是**缺验收 fixture 口令**（`.env*` 中无 `SC_ACCEPTANCE_FIXTURE_PASSWORD`，
`frontend_productization_fixture.py:20` 明确要求该变量）。
本轮改用**服务端只读解析**闭合：不需要口令，也不占据会话。

**方法**：`tmp/uc4-g09-creatability/acceptance-identity-server-probe.py`（全 `search`／`read`，不写库），
在验收容器 `sc-backend-odoo-acceptance` 上对 `db=sc_frontend_acceptance` 运行
（须带 `-c /var/lib/odoo/odoo.conf`，否则落到本机 socket 而非 `db` 服务）。

**结果（验收库 `sc_frontend_acceptance`）**

| 项 | 值 |
| --- | --- |
| 载体 | **存在**：uid 34 `fixture_role_config_admin`（`Acceptance Fixture Business Config Admin`），`active=True` |
| 解析角色 | **`business_config_admin`** —— 与 `.agent/context.yaml: acceptance_identity.role` 一致 |
| 能力组 | 只读／经办／审批／业务配置管理员 **四项全持** |
| 被服务菜单 | **414** 条（其中带 action 的 358 条） |
| G09 三入口 | 871／570／575 **全部 VISIBLE** |
| 入口路径 | 871 `项目中心 › 劳务成本 › 劳务成本登记`；570 `项目中心 › 机械成本 › 机械台班登记`；575 `项目中心 › 分包成本 › 分包成本登记` |
| 配置入口 | 可见两条：`菜单 417 smart_construction_core.menu_sc_business_config_workbench`（表单配置）／`菜单 418 smart_construction_core.menu_ui_menu_config_policy_business_config`（菜单配置）；另有 `base.menu_grant_menu_access`（菜单项） |

**口径修正（重要）**：此前登记的「登记身份在本库无载体」是**针对 dev 库 `sc_dev_demo`** 成立
（该库无 `fixture_role_config_admin`，只有等价角色 `sc_business_admin` uid 6）；**验收库有载体**。
两者不可混述。其余探测身份对照（同库）：`fixture_role_config_admin_peer` uid 35＝414、
`sc_test_admin` uid 133＝177、`admin` uid 2＝177。

**仍未闭合**：HTTP 面（`:18082` 的 `login → session.bootstrap` 导航树）需要验收口令，
本轮**未**获取、**未**尝试猜测、**未**改动任何口令；该面仍属产品方浏览器复核范围。
`security/**`、`frontend/**`、`fixture` 数据本轮**零改动**。

**状态口径**：台账 **22**；**未**合并、**未**冻结、**未**跑 Quick、#499 远端仍 `012c8ad4`、G10 未启动。

#### 8.35.20-㉝ 按 §㉛ 的最小范围实施：871 行级规则对齐 ＋ 前端 `reactivate` 键（2026-09-20；**产品复核前**）

**授权依据**：产品方「同意 继续」。两项均严格**收紧**（§㉛ 已给出范围与预期行为变化）。

**1）871 行级规则对齐（`security/sc_record_rules.xml`，单文件两处）**

- `rule_sc_internal_labor_usage`：挂载组 只读 → **经办**，名称对齐为
  `SC Project User - labor usage own or project member`（域**逐字不变**）。
- 新增 `rule_sc_project_read_labor_usage`：挂 **只读**、仅 `perm_read`、
  域 `['|', ('project_id.user_id','=',user.id), ('project_id.message_follower_ids.partner_id','=',user.partner_id.id)]`。

**实施坑（重要，已写入代码注释）**：该文件的既有约定是 `groups eval="[(4, ref(...))]"`（**link 追加**语义）。
对一条**已存在**的记录改挂组，`(4, …)` 只会**追加**、旧的 `只读` 仍保留 ⇒ 规则对只读继续生效。
首次实施即命中：升级后探针显示 871 只读仍可见（1），规则组为
`['项目中心只读', '项目中心经办']`。改为 **replace** 语义 `[(6, 0, [ref(...)])]` 后复跑归零。

| 探针项（`readonly-visibility-ab-probe.py`） | 对齐前 | 对齐后 | 570／575 |
| --- | --- | --- | --- |
| 只读读「本人创建但非项目成员」 | 1 | **0** | 0 |
| 只读读「本人负责项目」 | 1 | 1 | 1 |
| 只读 `write` | BLOCKED | BLOCKED | BLOCKED |
| 配置管理员读他人／写入 | 1／ALLOWED | 1／ALLOWED | 1／ALLOWED |
| `residual_after_rollback` | 0 | 0 | — |

**新增断言（零删除）**：`tests/test_labor_product_capability.py` 新增
`test_the_labor_usage_record_rules_match_its_siblings`——固定「经办挂 own-or-member、只读挂仅成员读域」，
并附一条行为反例（只读看不到自己创建但非其项目成员的项目下的记录）。

**定向补验**

| 项 | 结果 | 日志（`tmp/uc4-g09-creatability/`） |
| --- | --- | --- |
| 升级（首次，`(4,…)`） | PASS（但规则叠加，见上） | `rule-align-upgrade.log` |
| 升级（改 `(6,0,[…])` 后） | PASS | `rule-align-upgrade2.log` |
| 焦点类 | `TestLaborProductCapability` **4 测 0 failed** | `rule-align-l2-focused.log` |
| 受影响类 | 6 个类 **116 测 0 failed 0 error** | `rule-align-l2-affected.log` |
| sabotage | 绑定改回 `只读`＋升级 ⇒ 新断言 **FAIL**；恢复（`sha256 33238bfd…` 一致） | `rule-align-sabotage-{upgrade,test}.log`／`rule-align-restore-upgrade.log` |

**2）前端 `reactivate` 键（`frontend/apps/web/src/app/contracts/v2/workflowActionAvailability.ts`，2 行）**

- `workflowActionMethodAliases()` 增 `reactivate -> ['action_reopen']`；`knownKeys` 增 `'reactivate'`。
- 效果：575「重新打开」成为**受合同治理**的迁移；合同无对应行时按钮 **fail-closed**（禁用＋提示），
  不再回落为 `unmanaged` 而保持可点。未新增任何可用动作。

**新增断言（零删除）**：`frontend/apps/web/scripts/canonical_form_presenter_test.ts`（node 断言夹具，已有执行目标）
追加两条：`workflowActionMethodAliases('reactivate') === ['action_reopen']`；空 `availableActions` 下该动作 `enabled === false`。

**补验**

| 项 | 结果 | 日志 |
| --- | --- | --- |
| node 断言夹具 | **PASS cases=170** | 终端输出（`node /tmp/canonical-form-presenter-test.mjs`） |
| sabotage | 撤回键登记 ⇒ **AssertionError**（`actual: []` ≠ `['action_reopen']`） | `frontend-reactivate-sabotage-test.log` |
| 恢复 | **PASS cases=170**（`sha256 1fd348ce…`） | `frontend-reactivate-restore-test.log` |
| `lint:src` | **0 error**（39 条既有 warning） | `frontend-reactivate-lint{,2}.log` |
| `typecheck:strict` | PASS | `frontend-reactivate-typecheck{,2}.log` |
| `build` | **PASS**（27.21s；仅有既有 chunk-size warning） | `frontend-reactivate-build.log` |
| P4 守护自检 | `python3 -m unittest scripts.verify.test_frontend_professional_business_value_guard` **5 tests OK** | `frontend-p4-guard-selftest.log` |

**3）未纳入（本轮仍不做）**

- 871 缺超管 `ALL` 规则／缺配置管理员 `ALL` 规则／缺超管 ACL 行：§㉛ 实测**零权限差**，
  且补 ACL 授予行语义上是**新增授权**，与「只收紧」冲突 ⇒ 保持现状。
- HTTP 面（验收 `:18082` 登录后导航树）仍缺验收口令，未复核（服务端面见 §㉜）。
- 台账 **22**；**未**合并、**未**冻结、**未**跑 Quick、#499 远端仍 `012c8ad4`、G10 未启动。

**4）状态口径**：本轮＝「实施（规则对齐 ＋ 前端键）＋ 定向补验完成，**待产品方浏览器复核**」。

#### 8.35.20-㉞ 产品复核通过后的交付链前置：验收运行时对齐、登记身份登录、摘要交叉核对（2026-09-20；本批范围）

**1）产品复核结果（产品方）**

- 产品方实际浏览器复核在本批范围内**通过**。此前「自验与冻结门禁通过、待集中产品复核」的口径随之失效，
  本批范围改用 **批次验收完成**；主线集成、部署、89 入口整体交付**均未**完成，不因本次通过而改变。

**2）本轮执行的受管动作（两项，均在验收运行时，作用域仅 `sc_frontend_acceptance`）**

| 动作 | 入口 | 结果 | 日志 |
| --- | --- | --- | --- |
| 验收运行时对齐到本候选 | `CODEX_NEED_UPGRADE=1 make acceptance.module.upgrade MODULE=smart_construction_core` | **EXIT=0**；`17.0.0.168`，`write_date 2026-09-20 15:34:11Z`（对齐前 `13:33:49Z`） | `acceptance-realign-upgrade.log` |
| 登记身份可登录 | `SC_ACCEPTANCE_FIXTURE_PASSWORD=… make acceptance.frontend.fixture` | **EXIT=0**；`/api/v1/intent → login` **http=200**，解析 `fixture_role_config_admin` | `acceptance-fixture-login-20260920.log`／`acceptance-identity-nav-probe-after-realign.log` |

- 对齐原因：验收库原先落后工作树约 1.5 小时（dev 于 `15:06:11Z` 升级，验收停在 `13:33:49Z`）。
  若直接用登记身份复核，复核对象是**旧树**，会得到与候选无关的结论。
- 对齐后只读实测：`rule_sc_internal_labor_usage`→「SC 能力 - 项目中心经办」(r/w/c)；
  `rule_sc_project_read_labor_usage`→「SC 能力 - 项目中心只读」(仅 read)；
  三入口对 uid 34 **可见**（平台自身菜单求解 `_visible_menu_ids()`，非自建探针）：
  验收侧 `menu 688 → action 871`、`691 → 566`、`692 → 571`（与 dev 的行 id 不同）；
  事实契约只读集合 `19/6`、`16/5`、`17/15`，与当前候选一致（分包含 `state`）。
- 登记身份（uid 34）在三模型的 `read/create/write/unlink` 全为 YES，但 `search_count = 0`：
  读规则是项目域，fixture 项目不在其 own／follower 集合内 ⇒ **以该身份复核时三入口列表天然为空**，
  这是读域结果、不是缺陷；「打开已有记录／只读反例」只能在 dev（系统管理员）完成。
  该现象登记为**产品裁定项**（登记身份是否需要一条能看见自己经办记录的读路径），**不写入台账**。
- 口令值由执行器显式给出（本机夹具值）；三个监听端口仅 `127.0.0.1`（5174／5175／18082）。
  **未**触碰 dev 库、**未**触碰既有草稿（含 489）。
- 导航面 401 仍属 §㉗ 已定性的**探针缺陷**，本轮不重复该结论。该证据应由注册工具
  `scripts/verify/menu_governance_m4_browser_audit.mjs` 在需要时取得，且**当前不宜运行**：
  它强制 `页面 sourceSha == GIT_SHA`，脏树时该等式只能取 HEAD，等于把脏树绑定成 HEAD（证据不诚实）。
  故留到冻结为 clean HEAD 之后，再按需取导航面证据。

**3）摘要交叉核对：sabotage／恢复证据「输入未变」的依据**

| 记录中的摘要 | 文件 | 当前实测 | 结论 |
| --- | --- | --- | --- |
| `33238bfd…` | `addons/smart_construction_core/security/sc_record_rules.xml` | `33238bfd7de8eb56…` **一致** | §㉝ 的 sabotage／恢复输入未变 |
| `1fd348ce…` | `frontend/apps/web/src/app/contracts/v2/workflowActionAvailability.ts` | `1fd348cec90c16b3…` **一致** | §㉝ 的 sabotage／恢复输入未变 |
| `fa10c937…` | `addons/smart_construction_core/models/core/subcontract_management.py` | `fa10c937fda2e092…` **一致** | §㉚ 的 sabotage／恢复输入未变 |

- 可复跑检查：`tmp/uc4-g09-creatability/evidence-digest-crosscheck.py` → **PASS cases=3**
  （日志 `tmp/uc4-g09-creatability/evidence-digest-crosscheck.log`）。写入 gitignored 路径，冻结指纹不受影响。
- 记录卫生：本轮新增的 1511 行中，40 位 SHA 仅出现 `012c8ad4…`（＝本候选 HEAD，`ancestor-of-HEAD`）；
  无陈旧 Tree／HEAD 绑定；3 个短摘要均为**文件摘要**且与当前字节一致；整批差异无凭据类内容
  （命中项均为 `_COST_SOURCE_STATE_TOKEN` 受控哨兵与正文「token」字样）。

**4）复核辅助件**

- `tmp/uc4-g09-creatability/review-crossref.md`：dev ↔ 验收对照单（入口深链、新建态逐项预期、
  既有记录反例、应被拒操作、已知表达项）。位于 gitignored 路径，**不进入**本候选。

**5）交付链前置**

- `make ci.delivery.freeze.prepare` → **PASS**
  （`candidate=unfrozen next=review_generated_changes_commit_freeze_then_run_quick_once`；日志 `freeze-prepare.log`）。
  生成物变更 3 处，均为本批事实的正确反映：`docs/engineering_convergence/complexity_budget_report.md`
  （`sc_record_rules.xml 3180→3193`、`subcontract_management.py 1738→1829`、`workflow_contract_service.py 1438→1452`、
  `test_usage_performance_native_lowcode.py 1047→1444`、`test_workflow_contract_backend.py` 新增入表、
  告警阈值以上 `95→96`）、`docs/engineering_convergence/split_plan_queue.md`（同上行数位移）、
  `docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json`（`inputDigest` 随前端源码变化）。

**6）状态与未做项**

- 本批范围：**批次验收完成（本批范围，产品复核通过）**；主线集成、部署、89 入口整体交付均未完成。
- 台账保持 **22**；875／877／878 的核减仍按既定规则**待合入后独立审计**，22→19 仍只是**预期核减**。
- **未执行（保持未执行）**：最终 Quick、推送、PR 更新、合并、部署、冻结、G10 启动、浏览器全矩阵重跑。

#### 8.35.20-㉟ 独立复核 S1 收口：合同一致性放行键由「可伪造布尔键」改为「进程内令牌」（2026-09-21）

**1）独立复核结论（绑定 `83f4ba61…`；只读、由实施者之外的复核者执行）**

- 结论 `REQUEST_CHANGES`：1 项 `S1`、0 项 `S0/S2`；另 3 项 `POST_MERGE_FOLLOWUP`（记录卫生类，非代码缺陷）。
- S1 要点：`models/core/subcontract_management.py:520` 的
  `if self.env.context.get("sc_skip_subcontract_contract_authority"): return super().write(vals)`
  排在 `:515` 状态守卫之后、`:524` 事实冻结之前，因此带该键的写入会连带跳过冻结与
  `_sc_validate_subcontract_contract_authority`／`_sc_validate_register_settlement_authority`／
  `_sc_validate_cumulative_registered_amounts`。
- **可达性（复核者提出，本轮独立复验）**：`smart_core` 的 `api.data` 会把请求自带 `context` 合并进 env
  （`handlers/api_data.py:175` `_request_context()` ← envelope／payload／params；`:2357`
  `self.env[model].with_context(ctx)` 后 `write()`），而 `ApiDataHandler.REQUIRED_GROUPS` 只要求
  `base.group_user`。故项目经办角色可自带该键改写**已关闭**登记事实，绕过只允许项目审批人执行的
  `action_reopen`（`:743` 一带）。
- 该缺陷**不是相对 `main` 的回归**（`main` 有放行键、无冻结），而是本批新增控制**未被一致应用**。

**2）最小修正（只收紧，不放宽）**

- `models/core/subcontract_management.py` 顶部新增
  `_SC_CONTRACT_AUTHORITY_CONTEXT_KEY` 与 `_SC_CONTRACT_AUTHORITY_TOKEN = object()`（进程内对象身份）。
- `write()`：**冻结判定先于放行判定**；放行改为身份比较（`is _SC_CONTRACT_AUTHORITY_TOKEN`）。
  伪造的同名布尔键／字符串不再放行。
- 内部合同一致性回写调用点改为注入该令牌。
- **未改动**：冻结字段集、`closed` 为唯一冻结态、`已登记` 可调整窗口、受控动作语义与顺序、结算模型。
- 采用仓库既有姿势（`_COST_SOURCE_STATE_TOKEN`、`_TENDER_GUARANTEE_AUTHORITY_TOKEN`、
  `_TAX_FACT_AUTHORITY_TOKEN`），未新造机制。

**3）验证（新增断言，零删除）**

- `tests/test_usage_performance_native_lowcode.py`：新增「已关闭 ＋ 伪造放行键 ＋ **事实字段**」被拒、
  且事实值不变；原 `state` 断言保留。
- L2 定向：`TestSubcontractCostRegistration`＋`TestUmP3SubcontractRegisterSettlementAuthorityBoundaries`＋
  `TestP0StateClosure`＋`TestProductReports`＋`TestLaborProductCapability`＋`TestUsagePerformanceNativeLowcode`
  → **116 测 0 failed**（日志 `575-flag-token-l2-affected.log`）。
- 破坏性验证（证明断言非空）：把放行键恢复为「真值判定 ＋ 排在冻结之前」，新增断言**失败**
  （`AssertionError: UserError not raised`，日志 `575-flag-token-sabotage-test.log`）；恢复后 `0 failed`
  （`575-flag-token-l2-restore.log`）。
- L3 回滚事务探针（`575-flag-token-probe.py`：SAVEPOINT ＋ ROLLBACK，`residual_after_rollback=0`）：
  伪造布尔键 `True`／`"1"` 改写已关闭事实 → **BLOCKED** 且值未变；内部令牌改写已关闭事实 →
  **BLOCKED**（冻结先于放行）；受控动作 `closed→active` → **ALLOWED**；草稿／已登记事实写入 →
  **ALLOWED**（无过度封锁）；令牌 `json_serializable=false`，请求上下文无法携带。
- 同一探针在**修复前顺序**下运行：伪造布尔键 → **ALLOWED**，事实实际被改写为
  `G09 伪造字符串改写`——证明该缺口真实可利用，且探针能捕获它（`575-flag-token-probe-prefix-sabotage.log`）。
- 运行时对齐：`local.dev.upgrade` 与 `acceptance.module.upgrade` 均 EXIT=0；dev 与验收
  `smart_construction_core` 同为 `17.0.0.168`。

**4）同址同类缺陷：当时登记为「另行裁定」，**后续已纳入本批**

- `:1316 write()` 的 `sc_skip_subcontract_register_authority` 是同形的可伪造布尔键，位于**结算模型**：
  带该键可跳过 `_sc_validate_register_settlement_authority`、
  `_sc_validate_cumulative_registered_quantities`、`_sc_validate_cumulative_settlement_amounts`。
- 该键在 `main` 上即存在（非本批引入），且守卫的是结算授权校验而非本批新增的冻结窗口，故当时按
  「不扩展本批产品改动」处理：**登记为独立缺陷 ＋ 最小修正范围（同形令牌化）**，是否纳入另行裁定。
- 同类候选项：`sc_subcontract_register_authority_batch`（同为布尔上下文键，用于批量创建放行）。
- **裁定更新（见 §8.35.20-㊱）**：上述两个键**已在本批一并令牌化**；本条保留为当时的登记结论（历史来源），
  不再代表当前处置。

**5）状态与口径**

- 本候选新增 1 个提交（模型 ＋ 测试 ＋ 本记录），需**重新冻结、按 exact-head 跑一次 Quick、再做一次独立复核
  与外部归档**，之后才 `pr.push`；**#499 仍不合并、不部署**。
- 台账保持 **22**；22→19 仍只是**预期核减**（合入后按三个退役消费者独立审计）。G10 不启动。
- 四维口径不变：更新 PR ≠ 产品验收；独立复核 ≠ 产品验收；G08 主线集成 ≠ 部署 ≠ 89 入口整体交付完成。

#### 8.35.20-㊱ 同址同形放行键一并令牌化：结算放行键与登记批量放行键（2026-09-21）

**1）裁定与范围（只收紧，不放宽）**

- 把 §8.35.20-㉟(4) 登记为「另行裁定」的两个同形键**纳入本批**：结算放行键
  `sc_skip_subcontract_register_authority`、登记／结算明细批量放行键
  `sc_subcontract_register_authority_batch`。
- 改动面仅 `models/core/subcontract_management.py` 与其静态边界测试；**未改**冻结字段集、
  `closed` 唯一冻结态、`已登记` 可调整窗口、状态机与受控动作顺序、视图、前端、台账。

**2）最小修正**

- 新增 `_SETTLEMENT_AUTHORITY_CONTEXT_KEY`／`_SETTLEMENT_AUTHORITY_TOKEN` 与
  `_REGISTER_AUTHORITY_BATCH_CONTEXT_KEY`／`_REGISTER_AUTHORITY_BATCH_TOKEN`（进程内对象身份）。
- 结算 `write()`：放行由 `context.get("sc_skip_subcontract_register_authority")` 真值判断改为
  `is _SETTLEMENT_AUTHORITY_TOKEN` 身份比较；内部 2 处合同一致性回写调用点改为注入令牌。
- 结算 `create`／`write` 与结算明细 `create`／`write`／`unlink` 的批量放行同样改为身份比较
  （结算明细 3 处、结算 2 处），批量注入点改为注入 `_REGISTER_AUTHORITY_BATCH_TOKEN`。

**3）验证（新增断言，零删除）**

- 静态边界测试 `tests/test_um_p3_subcontract_register_settlement_authority_boundaries.py`：
  原断言「`write` 源含字面键名」改为「含 `is _SETTLEMENT_AUTHORITY_TOKEN`」，
  并新增 `test_internal_authority_flags_are_process_tokens_not_request_booleans`
  （三个键名与 `object()` 令牌均在模块级声明、类体内不得残留按键真值判断、三个令牌互不相同、
  明细三方法均为身份比较）→ `python3` 直跑 **9 测 OK**（`575-batch-key-static-boundary.log`）。
  破坏性验证：把放行判定退回真值判断后该测 **FAILED（2 项）**，恢复后 OK；
  文件 md5 `bf178eccec18107a21bf69b4ff0f532b` 恢复一致。
- L2 定向（与本批同 6 类）：**116 测 0 failed 0 error**（`575-batch-key-l2-affected.log`）。
  说明：该静态类不由 Odoo 用例加载器收集（`Starting …` 计数 0），故其证据为上面的直跑，
  L2 的 116 只覆盖其余 5 类。
- L3 回滚事务探针（`575-batch-key-token-probe.py`；每次尝试**独立** SAVEPOINT ＋ ROLLBACK，
  残留读取前 `invalidate_all()`）：
  - P1 结算放行键：基线 **BLOCKED**（分包结算显式头部字段与完整登记合同范围冲突）→ 伪造 `True`／`"1"`
    **BLOCKED** → 内部令牌 **ALLOWED**。
  - P2a 批量放行键·累计数量（明细 255 数量置 15.0，登记数量 10.0）：基线 **BLOCKED**
    （分包登记明细的有效累计结算数量不能超过登记数量）→ 伪造键 **BLOCKED** → 内部令牌 **ALLOWED**。
  - P2b 批量放行键·跨合同改挂（明细 255 改挂另一合同的登记明细 127）：基线 **BLOCKED** → 伪造键
    **BLOCKED** → 内部令牌 **ALLOWED**。
  - 残留核对：结算 216 相对方 5343、明细 255 数量 6.0、登记明细 142 全部为原值；
    `psql` 直查一致（`sc_subcontract_register_line` 142 = 10.00）。
- **缺口真实可利用（修复前对照）**：同一探针在 `c28fa315` 上运行（`575-batch-key-prefix-probe.py`）
  三项伪造键**全部 ALLOWED**——P1 相对方被实际改写、P2a 数量 15.0 落库、P2b 明细指向另一合同的登记明细
  且结算头部仍留在原合同（关系与头部不一致）；基线仍为 BLOCKED。
- **上一轮 P2「无效判别」的更正**：上一轮把该键的反例打在 `sc.subcontract.register.line` 的 `write()` 上，
  而该掩码只守卫**结算明细**的批量路径，故基线即 ALLOWED、不构成反例；本轮换到结算明细路径后反例成立。
  键的**可达性**不因上一轮探针失效而改变。
- 上一轮记录中的 `residual_contract_qty=11.0` 是 ROLLBACK 后读到的 **ORM 缓存残留**而非库内残留；
  本轮在残留读取前 `invalidate_all()`，并以 `psql` 直查复核为 10.00（原值）。

**4）状态与口径**

- 本候选在 `c28fa315` 之上新增 1 个提交（模型 ＋ 测试 ＋ 本记录），需**重新冻结、按 exact-head 跑一次 Quick、
  再做一次独立复核与外部归档**，之后才 `pr.push`；**#499 仍不合并、不部署**。
- 台账保持 **22**；22→19 仍是**预期核减**（合入后按三个退役消费者独立审计）。G10 不启动。
- 四维口径不变：更新 PR ≠ 产品验收；独立复核 ≠ 产品验收；G08 主线集成 ≠ 部署 ≠ 89 入口整体交付完成。

> 上述「#499 仍不合并、不部署／台账保持 22」已在本批后续阶段执行并闭合，最终口径见 **§8.35.21**。

### 8.35.21 G09 主线集成与台账 22 → 19（2026-09-21）

冻结候选 `3b4106ce3c9c3a05d8fd0ea1406544a757052b03`（tree `4dcb97794d4ca841a119ec8eb32d59cb01398acc`，
相对 `main` 35 条路径，exact-head `ci.local.quick` PASS）经 **PR #499** 以 squash 合入 main
`988e9a87dad3768d1de3358860a904ff618b842c`；`origin/main^{tree}` 与候选 tree **逐字节一致**
（`mergedAt` 2026-09-20T18:02:44Z，本地 2026-09-21 02:02:44）。合并方式 **squash ＋ `--match-head-commit`**
（用户在 2026-09-21 明确授权；`make pr.merge.local_quick_gate` 以同一 head 的 exact-head 回执**复用**，未重跑矩阵）。
合入前该 head 上远端必检项 **9 success／3 skipped／0 fail**：success `classify`／`frontend_release_gate`／
`merge_policy_gate`／`professional_authorization`／`professional_quality_gate`／`public_guard`／
`public_guard_classify`／`python310_runtime_compatibility`／`release_candidate_gate`；
skipped `classify`（候选检查变体）／`fast`／`wait_for_candidate_checks`。交付链前置证据：独立复核 **APPROVE**
（无 S0–S2，`tmp/uc4-g09-creatability/review-independent-3b4106ce.md`）、外部归档 receipt **verified**
（`.codex-evidence/workspace-archives/20260921/uc4-g09-usage-performance-native/3b4106ce…/`，11 文件）。

台账 `docs/ops/iterations/form_structure_compatibility_consumers_v1.json` 扣减 **22 → 19**
（本批在台账内**正好 3 条**：871 劳务成本登记（menu 689／view 1461）／570 机械台班登记（menu 692／1476）／
575 分包成本登记（menu 693／1491）），退役 action 871／570／575，
`count`／`localVerifiedCount`／`mainlineRemainingCount` 同步为 **19**，并新增 `uc4G09PublishedAudit`。
**按已合入源码逐项核对**：

- 三条入口契约（682 `labor_usage_register_productized_form_v1`／230 `equipment_usage_register_productized_form_v1`／
  232 `subcontract_register_productized_form_v1`）只留 `title` ＋ `composition_mode: native_semantic_surface`，
  各自绑定本入口 action，**优先级 50 → 800** 使入口发布成为最后结构写入者；**无 sections／fields／columns**，
  兼容结构副本已退出，`diagnose_structure_ownership()` 不可能再为这三条产出 `LEGACY_STRUCTURE_KEY_OVERRIDE`。
- 退役载体是**模型级 sections 副本**（库内 154／160／156，priority 20，现 `active=false`），**不是**入口声明的
  业务事实范围；三条入口契约的 `view_orchestration.context` 原样保留。
- **不额外计数**：三模型的原生主表单 1461／1476／1491 一模型一表单，且同时是 562／563／851 与第二菜单
  509／518 的渲染目标，**不随扣减退役**（`reduction.retiredViewMeaning`）。
- **退役隔离性**：§8.35.11 的只读 A／B 对 7 个 action（871／562／563／561／570／851／575）重放已退役载体，
  结构权威、呈现模式、章节数、字段数与分组数**全部不变**——三条载体 priority 20，早已被 p1-facts（88）与
  生成镜像（104／121／165）压过，退役的是"从未成为最后写入者"的冗余声明。

**旁路与补登（单列，不与核减混算；`bypassConsumers`，`counted=false`）**：从未登记的旁路入口
562 方单（menu 504／tree 2049）／563 零星用工（505／2050）／851 机械台班记录（510／2051）；
计入条目的第二菜单载体 509（→ action 570）／518（→ action 575）；以及三条从未登记的兄弟入口级契约
227 `labor_usage_ticket_productized_form_v1`（562）／228 `labor_usage_casual_productized_form_v1`（563）／
229 `equipment_usage_shift_productized_form_v1`（851）。扣减范围因此保持 3 条，**未被静默扩大或丢弃**。

**保留边界（不随本批关闭）**：模型级 p1-facts 15／21／17 仍 active（这三个模型上唯一声明业务事实
`readonly` 策略的载体，原生 arch 未重述，退役属**策略变更**）；生成镜像 86／71／126 仍 active（稀疏序注解）；
233 `subcontract_settlement_productized_form_v1`（576 分包结算）未动；561 劳务用工（无菜单、无 form 视图绑定、
无入口契约）的空章节属其**自身既存缺口**；562 记录态 `empty_action_domain`（域内 0 行，未造数据）、
562／563／851／509／518 浏览器**角色路由拒绝**（reachability fact，**不写成通过**）；`retirementComplete=false`。

`nextBatch.selectedGroup` 前进到 **G10 工程过程与资料**（682／867／729／597／527，
视图 1741／1550／1893／1560／1389），`priorityActions` 同步，`sourceMainlineHead` 更新为合入后 main；
**G10 未启动**。G09 组索引就地标记 `indexStatus=historical_source`（不再是当前消费者集），
`legacyConfigurationStatus` 保留逐名分类（只有三条 `*_form_sections_v1` 由本批退役，其余五条仍为当前消费者）。

本提交为**文档类单职责提交**（台账 ＋ 本记录，路径集合固定为 2）；**未触碰**任何产品代码、契约、测试或
验证工具输入，故不改动 §8.35.14–§8.35.20 的 L1–L4 结论；候选的 exact-head Quick 回执属于 `3b4106ce`，
本提交自身的收据由受管门禁按 fail-closed 口径产生，**不冒充同一绑定**。

状态：**G09 主线集成完成（PR #499，squash 同树）｜批次状态：自验与冻结门禁通过；集中产品复核结论以产品方登记为准｜
未部署｜89 入口整体交付未完成｜台账 19｜G10 未启动**。

### 8.36 G10 工程过程与资料：入口发布承接原生结构（2026-09-21；**实施＋分层验证轮**；未冻结、未跑 Quick、未归档、未建 PR、未合并）

**范围与层级**：Formal Product Layer **P1**（施工行业标准产品默认面）；Layer Target 为
`smart_construction_core` 的入口契约、原生视图与测试；标准口径（全部施工部署继承）。**不属** P0
（`smart_core` 不承载行业语义），不属 P2／P3／P4。爆炸半径为本组 5 个入口 action
（682／867／729／597／527）与其兄弟入口（598–601、586、730／731／732）；回滚方式为 `git revert`
（纯声明变更，无数据迁移）。

**机制（这批为什么能真正降低台账计数）**：台账计数的是 `layoutPolicy != container_tree_authority`
的兼容消费者；`ui_contract_v2` 只有在 `governance["form_structure_authority"] == "native_authority"`
时才给出 `container_tree_authority`，而该字段由入口契约的
`composition_mode ∈ {native_semantic_surface, semantic_native_surface}` 决定
（`form_structure_authority.py`）。因此本批不靠"把结构副本挪个位置"，而是让**本入口的发布成为本入口
的最后结构写入者**并声明原生语义面，兼容重组路径对这批 action 不再适用。

**修改范围（候选 15 条路径：代码／契约／测试 13 条 = 11 条改动 ＋ 2 条新增，另加本记录与切换日志 2 条）**：

1. 164 `sc_safety_issue_handling_form_v1`（682）／165 `sc_quality_acceptance_handling_form_v1`（867）
   只留 `title` ＋ `composition_mode: native_semantic_surface`，优先级保持 **900**（高于本模型所有模型级
   载体的最高值 115→154），body（sections／fields／columns）退役。
2. 245 `construction_diary_productized_form_v1`（729）同样退役 body，优先级 **700 → 800**；该记录由
   `<odoo noupdate="1">` 承载，普通 record 不会覆盖，故以
   `<function model="ui.business.config.contract" name="write">` 写同一 `contract_json` 补写。
   升级后实测 `priority=800`、`noupdate=true`、`version_no=2`。
3. **新增** `data/engineering_process_form_productization_contract.xml`（`<odoo noupdate="0">`），为
   **原本没有任何入口发布**的 597（`action_sc_project_document`）与 527
   （`action_project_progress_entry`）发布 `sc_project_document_productized_form_v1`／
   `project_progress_entry_productized_form_v1`（priority 800，只留 title ＋ native_semantic_surface），
   并在 `__manifest__.py` 按位置登记；运行库实测 dbId 777／778。
4. 五个原生表单补 **16 个** `data-sc-anchor` 业务章节（1741→2、1550→4、1893→4、1560→3、1389→3），
   把退役 body 声明的章节身份与字段级只读口径交回原生 arch；`view_sc_safety_issue_form` 的空
   「来源追溯」页（`<page>` 内只有空 `<group>`）随本批移除（同 G09 对 1461 的处理），`hazard_source_id`
   仍由「隐患信息」页承载。计算类分组（质量验收「办理提示」、进度计量「录入口径」、日志尾部「依据类事实」）
   **故意不加锚点**，它们不是可编辑业务章节。
5. **新增** `tests/test_engineering_process_native_lowcode.py`（tag `uc4_native_lowcode`，542 行／17 测试），
   并在 `tests/__init__.py` 登记；测试以"原生 arch 为地面真值"钉住渲染字段集与锚点章节集。

**关键决策：只读实测否决了第一版「退役模型级镜像」计划**。第一版计划按台账 `legacyConfigurations`
逐名退役（含日记镜像 61、文档镜像 104、进度镜像 45），失败点是把"本批计数"误当成"该载体只服务本批"。
冻结态只读 A／B（`sc_dev_demo`，`SAVEPOINT g10_dry_run` ＋ `ROLLBACK TO SAVEPOINT`，
`rollback_residual` 证明 **0 写入**：无新增发布行、245 优先级回到 700、164 仍带 sections）给出的实测：

| action | 归属 | 基线（权威／字段／章节／诊断） | 本批后 |
| --- | --- | --- | --- |
| 682 安全问题闭环 | 本批 | `entry_semantic_surface`／23／4／`LEGACY_STRUCTURE_KEY_OVERRIDE` | `native_authority`／container_tree ／`LEGACY_STRUCTURE_SUPPRESSED_BY_NATIVE_VIEW` |
| 867 质量验收 | 本批 | `entry_semantic_surface`／15／4／— | `native_authority`／container_tree |
| 597 工程资料 | 本批 | `""`／16／0／— | `native_authority`／container_tree |
| 729 施工日志 | 本批 | `entry_semantic_surface`／30／9／`KEY_OVERRIDE` | `native_authority`／container_tree |
| 527 进度计量 | 本批 | `""`／8／0／— | `native_authority`／container_tree |
| 730／731／732 日报表／周报表／月报表 | 兄弟 | `entry_semantic_surface`／23／4／`KEY_OVERRIDE` | **完全不变** |
| 598／599／600／601 资料分页 | 兄弟 | `""`／16／0／—（`compatibility_regrouping`） | **完全不变** |
| 586 进度计量（工作台） | 兄弟 | `""`／8／0／—（`compatibility_regrouping`） | **完全不变** |

被否决的正是"退役日记镜像 61"：61 同时是 730／731／732 的**最后结构写入者**，退役后这三个入口渲染
事实从 **23 降到 14**——即用本组计数去换另一组入口的事实缺失。因此本批只退役**自己条目**的 body，
四个生成镜像（45／61／104／115）与两个日记辅助载体（25 政策载体、148 稀疏字段序）**保持 active**。

**必须守住的回归规则（写进测试）**：**只要某模型级载体仍是同一模型上任一其它 action 的最后结构
写入者，就不得退役**。每个减量只退役自己条目的 body。测试
`test_the_model_wide_carriers_stay_active_for_their_sibling_actions`／
`test_the_diary_auxiliary_carriers_are_retained`／
`test_the_sibling_actions_still_exist_and_reach_their_own_form` 逐条登记该规则，
`test_a_scoped_competing_declaration_is_refused` 证明带 `action_id`／`view_id` 的竞争结构仍按 fail-closed
拒绝（G10 的四个镜像在生成文件中均为模型级、无 action／view 绑定，因此只降级为
`LEGACY_STRUCTURE_SUPPRESSED_BY_NATIVE_VIEW`，不报错）。

**呈现中立性**：`test_the_native_arch_is_presentation_neutral` 钉住每个原生表单的渲染字段集与顺序
（1741→23、1550→15、1893→28、1560→17、1389→9），`test_every_retired_fact_is_still_reachable_from_the_native_arch`
逐项核对退役 body 声明的全部事实：或由原生 arch 渲染，或登记为从未在原生面呈现的迁移来源标记
（`sc.construction.diary.source_origin`，与 G09 丢弃 `legacy_fact_*` 同类），**不允许静默消失**；
`test_no_retired_declaration_referenced_a_missing_fact` 另证退役声明引用的字段在模型中真实存在。

**分层验证结果（如实登记，逐项可复现）**：

- **L0 身份**：`scripts/contract/complete_worktree_fingerprint.py --baseline ec2c56e5…`
  → `status=PASS`，`path_count=7521`，digest `e170424f…`（**文档轮之前的代码态**；冻结轮的完整
  tracked＋untracked 指纹另存并以冻结回执为准，不以此值冒充冻结绑定）。
- **L1 静态**：`make ci.local.iteration` **PASS**（16 项静态测试通过；提交前 `changedPathCount=15`、`unmappedPathCount=15`、`manualNonZeroL2Required=true`——两个计数**同义**，本批 15 条路径均未命中前端增量自动推荐映射，故需**人工选择非零 L2**，不代表门禁失败）；
  `make fe.install.cached` PASS（新建工作树无前端依赖，必须先装）。
- **L1 生成物**：`make ci.delivery.freeze.prepare` **PASS**
  （`component_driver_takeover_inventory PASS required=35 missing=0`、
  `contract_form_split_evidence PASS lines=1905`、`ci.generated_evidence.preflight PASS`）。
- **L2 定向非零测试**：`make local.dev.test`
  `TEST_TAGS='uc4_native_lowcode/smart_construction_core:TestEngineeringProcessNativeLowcode'`
  → **17 tests, 0 failed, 0 error(s)**；整组回归
  `TEST_TAGS='uc4_native_lowcode/smart_construction_core'` → **146 tests（164 统计口径）, 0 failed, 0 error(s)**。
- **L2 守卫**：`verify.form_structure.contract.guard`／`verify.form_view.native_structure.boundary_guard`／
  `verify.view.orchestration_boundary_guard`／`verify.form_view.scope.boundary_guard` 均 **PASS**。
- **L3 运行库**：`make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1`
  → exit 0（含 `local.dev.verify_authority PASS`）；随后只读探针（`sc_dev_demo`）核对：5 条入口发布
  `active=true`／`status=published`／priority 900·900·800·800·800／`composition_mode=native_semantic_surface`／
  **无任何 sections·fields·columns 结构键**／`context` 原样保留；6 条历史载体仍 `active=true`；
  682／867／597／729／527 的 `form_structure_authority=native_authority`、
  `layoutPolicy=container_tree_authority`；730／731／732、598–601、586 与基线逐项一致；原生 arch 锚点数
  2／4／4／3／3，且五个视图 `archSha256` 与该次升级一致。
- **L4 首次 exact-head Quick 失败与整改（如实登记）**：候选 `896226d2` 的 `make ci.local.quick` 在
  `verify.tenant.product_payload_boundary` 失败（`FIXED_CUSTOMER_IDENTIFIERS=2`），两条路径被判定为
  `customer_identity_or_brand_reference`——本记录与切换日志在登记环境缺陷时写了**客户定制仓库的具名
  标识**。整改：改为"客户定制 addon 仓库（不在本仓库边界内）"的通用表述，`make verify.tenant.product_payload_boundary`
  重跑 PASS（`FIXED_CUSTOMER_IDENTIFIERS=0`、`files=7522`），随后 amend 该提交并重跑一次 exact-head Quick；
  失败与整改均保留，**不以失败前的读数充当最终回执**。该失败**不属产品面**，产品代码／契约／页面／测试
  未因此改动。
- **L4 未跑**（如实登记为未覆盖，不写成通过）：本批**未**跑 `FORM_LOWCODE_TOPIC` 浏览器代表面复验
  （不写入通过）；冻结后的 exact-head Quick 回执、独立复核与外部归档属收口轮，结果以冻结回执为准。
- **工作树 `artifacts/` 环境缺陷与整改（如实登记）**：第二次 Quick 在
  `verify.unified_page_contract.v2.web_architecture` 失败——该守卫把报告写到 `artifacts/backend`，而本
  工作树的 `artifacts/` 是**非软链的 root 属主空目录**（主仓库的 `artifacts` 是指向
  `/home/lidefend/workspace/sce-offrepo/artifacts` 的软链），故 `PermissionError`。整改：按主仓库既有
  注册口径把工作树 `artifacts` 换成指向同一共享 artifacts 权威的软链（`artifacts` 属 `.gitignore` 第 106
  行，**不属候选面**，改动后完整指纹 `path_count` 不变为 7521），并复验可写；工作树内已无 root 属主
  路径。该缺陷属**环境一致性**问题，不是产品缺陷，产品代码／契约／页面／测试未因此改动。

**未覆盖项与环境缺陷（登记，不在本批修）**：`make verify.contract.view_structure` 在新工作树失败，
两条根因均为**既存环境缺陷**、已在干净主工作树复现：(a) 工作树 `artifacts/` 非软链且属 `root`，
guard 写 `artifacts/contract` 时 `PermissionError`；(b) 该 guard 期望 `local.clean`／`sc_clean` 的权威指纹
证据，本工作树以 `ec2c56e5` 为基线，故 `baseline_sha`／`scope_manifest_sha256`／`digest`／`branch`
四项比对不匹配。`make verify.user_form.preference.boundary_guard` 失败于
`addons/smart_construction_custom/models/user_preferences.py` 不存在——该模块属**客户定制 addon 仓库**，
不在本仓库边界内。两者**均非本批改动引入**，不修、不隐去，按环境缺陷登记。

**保留边界（不随本批关闭）**：模型级镜像 115（682 自身模型面，其唯一兄弟场景即 682）／104（598–601）／
61（730／731／732）／45（586）与日记辅助载体 25／148 保持 active——退役它们属于**别组的计数**，
且必须先让原生 arch 承接其政策口径（政策变更，非结构变更）；`retirementComplete=false` 不变。

**状态**：**G10 实施与分层验证完成（L0／L1／L2／L3 通过；L4 首轮失败已整改并重跑）｜冻结与 Quick 回执以
收口轮为准｜未归档｜未建 PR｜未合并｜台账 19（本批扣减 19 → 14 属合并后文档单职责提交，沿用 G03–G09 先例）**。

### 8.37 G10 主线集成与台账 19 → 14（2026-09-21）

冻结候选 `f3df441ae57047a010bb39263751a11be58ca51b`（tree `b79e4cfbefdc5a269463bc8ddb5453b0c0a7c424`，
相对 `main` 15 条路径，exact-head `make ci.local.quick` **PASS**，回执绑定该候选完整指纹
`a9625139f2ca30abdf73f897d8277b119ed5ce04e599d51130918c2c149e8963`／`path_count=7521`）经 **PR #502**
以 squash 合入 main `294fa47881f1fd1ab272a55860e5fd1b815110cc`；`origin/main^{tree}` 与候选 tree **逐字节一致**
（`mergedAt` 2026-09-20T21:13:08Z，本地 2026-09-21 05:13:08）。合并方式 **squash ＋ `--match-head-commit`**
（`make pr.merge`），merge 前的本地 Quick 以同一 head 的 exact-head 回执**复用**，未重跑矩阵。
合入前该 head 上远端必检项 **9 success／3 skipped／0 fail**：success `classify`／`frontend_release_gate`／
`merge_policy_gate`／`professional_authorization`／`professional_quality_gate`／`public_guard`／
`public_guard_classify`／`python310_runtime_compatibility`／`release_candidate_gate`；
skipped `classify`（候选检查变体）／`fast`／`wait_for_candidate_checks`。交付链前置证据：独立只读复核
**POST_MERGE_FOLLOWUP**（无 S0–S2，`tmp/g10-evidence/review-independent-f3df441a.md`，只读、未改任何被跟踪文件）。

台账 `docs/ops/iterations/form_structure_compatibility_consumers_v1.json` 扣减 **19 → 14**
（本批在台账内**正好 5 条**：682 安全检查／867 质量验收／597 工程资料／729 施工日志／527 施工进度），
退役 action 682／867／597／729／527，`count`／`localVerifiedCount`／`mainlineRemainingCount` 同步为 **14**，
并新增 `uc4G10PublishedAudit`。**按已合入源码逐项核对**：

- 682／867／729 的入口契约（164 `sc_safety_issue_handling_form_v1`／165
  `sc_quality_acceptance_handling_form_v1`／245 `construction_diary_productized_form_v1`）只留 `title` ＋
  `composition_mode: native_semantic_surface`，各自绑定本入口 action，`view_orchestration.context` 原样保留；
  **无 sections／fields／columns**，`structural_form_declarations()` 对其返回空，
  `diagnose_structure_ownership()` 不可能再为这三条产出 `LEGACY_STRUCTURE_KEY_OVERRIDE`。
- 597／527 **原本没有入口级发布**（只消费模型级镜像 104 priority 142／45 priority 76），本批发布
  `sc_project_document_productized_form_v1`／`project_progress_entry_productized_form_v1`（priority 800，
  action 绑定，只留 title ＋ native_semantic_surface），成为各自 action 的最后结构写入者。
- 245 位于 `<odoo noupdate="1">` 载体，故新声明由同文件尾部
  `<function model="ui.business.config.contract" name="write">` 补写（`contract_json` 与 `<record>` 逐字一致，
  `ref()` 找不到记录即 fail-closed），升级后实测 `priority=800`、`noupdate=true`、`version_no=2`。
- **不额外计数**：五个原生主表单 1741／1550／1560／1893／1389 一模型一表单，且同时是 730／731／732、
  598–601、586 的渲染目标，**不随扣减退役**（`reduction.retiredViewMeaning`）。
- **退役隔离性**：只读 A／B（`sc_dev_demo`，`SAVEPOINT` ＋ `ROLLBACK`，`rollback_residual` 0 写入）重放
  682／867／597／729／527 与 730／731／732、598–601、586：本批五个 action 变为
  `native_authority` ＋ `container_tree_authority`，其余八个 action 的结构权威、呈现模式、字段数与分组数
  **逐项不变**；第一版「退役模型级镜像」计划因日记镜像 61 仍是 730／731／732 的最后结构写入者
  （退役后其渲染事实 23 → 14）被实测否决。

**旁路与补登（单列，不与核减混算；`bypassConsumers`，`counted=false`）**：同模型兄弟 action 730 日报表／
731 周报表／732 月报表（继续消费 61／148／25）、598 安全资料／599 质量资料／600 自检资料／601 归档备案
（消费 104）、586 进度计量工作台（消费 45）；保留载体 45／61／104／115 与日记辅助载体 25／148 逐条给出
`whyNotCounted`。扣减范围因此保持 5 条，**未被静默扩大或丢弃**。

**保留边界与已知限制（不随本批关闭）**：730／731／732、598–601、586 仍在兼容重组路径；G10 后 729 入口的
原生面渲染 **28** 项原生 arch 事实，模型级载体曾贡献的两个**技术踪迹字段**（`source_origin` 迁移来源标记、
`create_date` 系统创建时间戳）不再出现在原生面——退役 body 声明的**业务**事实全部可达（呈现中立性结论不变），
但这两个踪迹字段的归属登记为**遗留项**（独立复核的 POST_MERGE_FOLLOWUP 项之一）；本批**未跑**
`FORM_LOWCODE_TOPIC` 浏览器代表面复验、**无截图证据**（结构交付以 L0–L4 为证据）；两个既存环境缺陷
（`verify.contract.view_structure` 的 `artifacts/` 属主与 `local.clean`／`sc_clean` 指纹期望、
`verify.user_form.preference.boundary_guard` 依赖不在本仓库的定制模块）如实登记、不修；
`retirementComplete=false`。

**过程偏差（如实登记）**：候选 `896226d2` 与 `ea9bd88d` 上各有一次 Quick 失败（客户品牌词命中
`verify.tenant.product_payload_boundary`；工作树 `artifacts/` 属主导致的 `PermissionError`），均在冻结前整改
（文案通用化、工作树 `artifacts` 指向共享权威软链）并重跑；两次失败均未触碰产品面。候选内文档的
「未建 PR／未归档」措辞是**冻结时点**的表述，本节为合并后事实，二者不矛盾但以本节为准（独立复核已把该措辞
登记为 POST_MERGE_FOLLOWUP）。

`nextBatch.selectedGroup` 前进到 **G11 轻表单与管理配置**（860／883／885／727／887／888，
视图 1887／1908／1910／2070／2072／2074），`priorityActions` 同步，`sourceMainlineHead` 更新为合入后 main；
**G11 未启动**。G10 组索引就地标记 `indexStatus=historical_source`（不再是当前消费者集），
`legacyConfigurationStatus` 保留逐名分类（三条入口 body 由本批退役，四条仍为当前消费者）。

本提交为**文档类单职责提交**（台账 ＋ 本记录，路径集合固定为 2）；**未触碰**任何产品代码、契约、测试或
验证工具输入，故不改动 §8.36 的 L0–L4 结论；候选的 exact-head Quick 回执属于 `f3df441a`，
本提交自身的收据由受管门禁按 fail-closed 口径产生，**不冒充同一绑定**。

状态：**G10 主线集成完成（PR #502，squash 同树）｜批次状态：自验与冻结门禁通过；集中产品复核结论以产品方登记为准｜
未部署｜89 入口整体交付未完成｜台账 14｜G11 未启动**。

### 8.38 G11 轻表单与管理配置：入口发布承接原生结构与字段级只读稀疏覆盖（2026-09-21；**实施＋分层验证轮**；冻结／Quick／独立复核／PR 属本轮收口步骤）

**范围与层级**：Formal Product Layer **P1**（施工行业标准产品默认面）；Layer Target 为
`smart_construction_core` 的入口契约、原生视图与测试；标准口径（全部施工部署继承）。**不属** P0
（`smart_core` 不承载行业语义），不属 P2／P3／P4。爆炸半径为本组 6 个入口 action
（860 消息通知／883 岗位管理／885 办公资产／727 流程审批配置／887 系统参数／888 编码规则）与其兄弟入口
（`mail.notification` 的 core「通知」119、`hr.job` 的 core「工作岗位」205、`ir.sequence` 的 core「序列」28）
以及模型级生成镜像 52；回滚方式为 `git revert`（纯声明变更，无数据迁移）。

**机制（这批为什么能真正降低台账计数）**：与 G07／G09／G10 同一条机制。台账计数的是
`layoutPolicy != container_tree_authority` 的兼容消费者；`ui_contract_v2` 只有在
`governance["form_structure_authority"] == "native_authority"` 时才给出 `container_tree_authority`，而该字段由
入口契约的 `composition_mode ∈ {native_semantic_surface, semantic_native_surface}` 决定
（`form_structure_authority.py`）。因此本批让**本入口的发布成为本入口的最后结构写入者**并声明原生语义面，
兼容重组路径对这 6 个 action 不再适用。

**修改范围（候选 16 条路径：代码／契约／测试 13 条＝11 改＋2 新增，另加本记录与切换日志 2 条，以及随
`ci.delivery.freeze.prepare` 刷新的生成物 `docs/engineering_convergence/complexity_budget_report.md` 1 条）**：

1. 860 `mail_notification_form_v1`／883 `product_job_form_v1`／885 `office_asset_form_v1`／
   887 `product_system_settings_form_v1`／888 `product_numbering_rule_form_v1` 只留 `title` ＋
   `composition_mode: native_semantic_surface`，优先级保持 **800**（均已是本模型最高 active 载体），
   body（sections／fields／columns／actions）退役，`view_orchestration.context` 原样保留。
2. **新增** `data/light_forms_configuration_form_productization_contract.xml`（`<odoo noupdate="0">`，在
   `engineering_process_form_productization_contract.xml` 之后登记），为**原本没有任何入口发布**的
   727（`action_sc_approval_policy`）发布 `sc_approval_policy_productized_form_v1`（priority 800）；
   此前 727 只消费模型级生成镜像 52（priority 84、无 action 绑定），结构权威停在 `""`，走兼容地板路径。
3. 六个原生表单补 **16 个** `data-sc-anchor` 业务章节，把退役 body 声明的章节身份交回原生 arch：
   1910→2（消息信息／消息内容）、2070→4（岗位信息／编制信息／岗位职责／任职要求）、1908→3
   （资产信息／使用信息／购置信息）、1887→2（业务规则／系统承载）、2072→3（参数范围／成本台账／运行说明）、
   2074→2（规则标识／编号格式）。办公资产的「备注」「附件」在原生 arch 上是 notebook 页面而非业务分组，
   **故意不加锚点**；887 的 `parameter_scope`／`operation_notice` 补 `readonly="1"`（模型面本就只读，属原生面回填）。
4. **新增** `tests/test_light_forms_configuration_native_lowcode.py`（tag `uc4_native_lowcode`，23 测试），
   并在 `tests/__init__.py` 登记；测试以"原生 arch 为地面真值"钉住渲染字段集、锚点章节集、只读口径与
   退役隔离性。

**关键决策：字段级只读缺口由实测发现，以"稀疏语义覆盖"收口（不是设计时预判）**。退役 body 除结构外还带
**字段级只读口径**，而 `structural_form_declarations()` 把只读视为语义注解、不入结构声明，因此该口径在
`native_authority` 下不再从契约读取，只能由原生 arch 或模型面承载。冻结态只读 A／B 逐节点对比
`UiContractV2Handler` 输出（`sc_dev_demo`，`SAVEPOINT g11_ab` ＋ `ROLLBACK TO SAVEPOINT`，
`rollback_residual` 证明 **0 写入**；探针与结果见 `tmp/g11-evidence/probe_g11_ab.py`／`probe-g11-ab.json`、
`probe_g11_readonly_source.py`、`probe_g11_overlay.py`），实测三处**真实回退**：

| action | 退役 body 声明的只读字段 | 退役后实测回退 | 本批处置 |
| --- | --- | --- | --- |
| 860 | 7（`sc_subject`／`author_id`／`sc_message_date`／`is_read`／`read_date`／`sc_record_name`／`sc_body`） | `author_id`／`is_read`／`read_date`（模型面 `readonly=False` 且原生 arch 无声明） | 稀疏覆盖 **3** 条 |
| 885 | 1（`status`） | `status`（状态条节点无只读声明，模型面 `readonly=False`） | 稀疏覆盖 **1** 条 |
| 888 | 3（`name`／`code`／`company_id`） | 三条的**容器树节点**回退为可写（原生 arch 的 `readonly="1"` 只覆盖部分节点，`ir.sequence` 模型面 `readonly=False`） | 稀疏覆盖 **3** 条 |
| 883／887／727 | — | **0 回退** | 不动 |

处置方式是**稀疏语义覆盖**：在 `contract_json.views.form` 里只放 `fields: [{'name': X, 'readonly': True}, …]`，
每个入口**只列真实回退的字段**（860 只列 3 条，其余 4 条由模型面即可只读，**不重复声明**；885 列 1 条；
888 列 3 条）。这类行不含任何结构键，`structural_form_declarations()` 的 `semantic_keys` 归约会把它判为
语义注解而非结构声明，故不产生 `NATIVE_SEMANTIC_SURFACE_STRUCTURE_CONFLICT`；对照实验实测 authority 仍为
`native_authority`、`presentationMode=task`、`layoutPolicy=container_tree_authority`、`diagnostics` 为空，
且上述字段的只读口径完全恢复（860 七个全为只读、885 `status` 只读、888 三条只读）。

**分层验证结果**：

- **L0 侦察**：基线／视图探针（`tmp/g11-evidence/probe-g11-baseline.json`、`probe-g11-views.json`）确立
  860／883／885／887／888 为 `entry_semantic_surface`、727 为 `""`（兼容地板），并锁定六个原生视图的
  锚点与渲染字段集。
- **L1 生成物**：`make ci.delivery.freeze.prepare` **PASS**
  （`component_driver_takeover_inventory PASS required=35 missing=0`、
  `contract_form_split_evidence PASS lines=1905`、`ci.generated_evidence.preflight PASS`）；
  `docs/engineering_convergence/complexity_budget_report.md` 随刷新由 4393 → 4395。
- **L2 定向非零测试**：`make local.dev.test`
  `TEST_TAGS='uc4_native_lowcode/smart_construction_core:TestLightFormsConfigurationNativeLowcode'`
  → **23 tests, 0 failed, 0 error(s)**；整组回归
  `TEST_TAGS='uc4_native_lowcode/smart_construction_core'` → **189 tests（169 统计口径）, 0 failed, 0 error(s)**。
- **L2 守卫**：`verify.formal_product_field_purity`／`verify.contract.structure_lock`（`domains=14`）／
  `verify.product.configuration_center.wave1.guard`／`verify.tenant.payload_boundary`／
  `verify.contract.page_v1_zero_residue.guard`／`verify.system_init.menu_boundary.guard` 均 **PASS**。
- **L2 域回归（受本批影响的三个域 ＋ 一个含 860 的域）**：只读重跑域 rollout 脚本并与基线逐项 diff——
  collaboration **仅 1 处预期变化**（`form_structure_authority: entry_semantic_surface → native_authority`，
  `presentation_mode` 与 `effective_render_profile` 保持不变）；base_configuration **0 diff**（6 action）；
  administration **0 diff**（8 action）；`frontend_workbench_center_rollout`（含 860）**PASS**（4 action）。
- **L3 运行库**：`make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1` → exit 0
  （含 `local.dev.demo.authority PASS`）；随后只读探针核对六条入口发布 active／published／priority 800／
  `composition_mode=native_semantic_surface`／`context` 原样保留，入口解析为 `native_authority` ＋
  `container_tree_authority`，模型级生成镜像 52 仍 active。

**未覆盖项与环境缺陷（如实登记，不写成通过）**：本批**未跑** `FORM_LOWCODE_TOPIC` 浏览器代表面复验，
**无截图证据**（结构交付以 L0–L3 为证据）。`make verify.contract.view_structure` 在本工作树失败，根因是
该守卫期望 `local.clean`／`sc_clean` 的权威指纹证据，而本工作树以 `ec2c56e5` 为基线，故
`baseline_sha`／`scope_manifest_sha256`／`digest`／`branch` 四项比对不匹配——**本次已在干净主工作树
（`main@ec2c56e5`）复现同样四项失败**，确认属**既存环境缺陷**而非本批改动引入，按 G08–G10 先例如实登记、
**不修**（`make ci.local.quick` 不含该守卫，不阻塞）。`verify.product.menu.governance.m4.closure` 在本工作树与
干净主仓库均因缺少 `artifacts/menu-governance/menu-m4-runtime.REJECTED-wrong-sha.json` 失败，同属既存
环境缺陷。`verify.user_form.preference.boundary_guard` 依赖 `smart_construction_custom/models/user_preferences.py`
（该模块属**客户定制 addon 仓库，不在本仓库边界内**）。

**保留边界（不随本批关闭）**：模型级生成镜像 52（`sc_approval_policy_form_structure_generated_v1`）保持
active——在没有 action 上下文的面上它仍是 `sc.approval.policy` 唯一的结构载体，退役属**别组的计数**；
`retirementComplete=false` 不变。本批不改 ACL／记录规则／菜单可见性，不改模型字段，不改运行环境、数据库或端口。

**状态**：**G11 实施与分层验证完成（L0／L1／L2／L3 通过）｜冻结、exact-head Quick、独立只读复核与 PR 属本轮
收口步骤，回执以冻结与 CI 为准｜未归档｜未建 PR｜未合并｜台账 14（本批扣减 14 → 8 属合并后文档单职责提交，
沿用 G03–G10 先例）**。

### 8.39 G11 主线集成与台账 14 → 8（2026-09-21）

冻结候选 `a740fcf8bb3f381b43aba3a980c880c5fd66d5ae`（tree `6033d7190d352f2cb2edbd2198ca3deefcd87588`，
相对 `main@d96632a2` **16 条路径**、单提交）经 **PR #504** 以 squash 合入 main
`dac2aaf1bd747b12b28ea7d3e0412b7f67895a3a`；`origin/main^{tree}` 与候选 tree **逐字节一致**
（`mergedAt` 2026-09-20T22:57:55Z，本地 2026-09-21 06:57:55）。合并方式 **squash ＋ `--match-head-commit`**
（`make pr.merge`）。候选的 exact-head `make ci.local.quick` 在该 head 上运行并以**运行退出码**为通过判据，
回执绑定 `head=a740fcf8…`／`tree=6033d719…`／`suite=ci.local.quick`／`producer=atomic-ci-local-quick-runner-v1`；
**该回执不含结果字段**，只能证明 Quick 在该 head 上跑过、不能自证通过——这一口径限制如实登记（独立复核已指出）。
合入前该 head 上远端必检项 **9 success／3 skipped／0 fail**：success `classify`／`frontend_release_gate`／
`merge_policy_gate`／`professional_authorization`／`professional_quality_gate`／`public_guard`／
`public_guard_classify`／`python310_runtime_compatibility`／`release_candidate_gate`；
skipped `classify`（候选检查变体）／`fast`／`wait_for_candidate_checks`。交付链前置证据：独立只读复核
**POST_MERGE_FOLLOWUP**（**无 S0／S1／S2**，`tmp/g11-evidence/review-independent-a740fcf8.md`，只读、未改任何被跟踪文件）。

台账 `docs/ops/iterations/form_structure_compatibility_consumers_v1.json` 扣减 **14 → 8**
（本批在台账内**正好 6 条**：860 消息通知／883 岗位管理／885 办公资产／727 流程审批配置／887 系统参数／888 编码规则），
`count`／`localVerifiedCount`／`mainlineRemainingCount` 同步为 **8**，并新增 `uc4G11PublishedAudit`；
`nextBatch.selectedGroup`／`priorityActions`／`sourceMainlineHead` 同步前进（见下）。**按已合入源码逐项核对**：

- 860／883／885／887／888 的入口契约（`mail_notification_form_v1`／`product_job_form_v1`／`office_asset_form_v1`／
  `product_system_settings_form_v1`／`product_numbering_rule_form_v1`）只留 `title` ＋
  `composition_mode: native_semantic_surface` ＋ 原样的 `view_orchestration.context`，各自仍绑定本入口 action、
  priority 800；**无 sections／columns／layout／actions**，`structural_form_declarations()` 对其返回空，
  `diagnose_structure_ownership()` 不可能再为这五条产出 `LEGACY_STRUCTURE_KEY_OVERRIDE`。
- 727 **原本没有入口级发布**（只消费模型级生成镜像 52，priority 84、`action_id` 为空，结构权威停在兼容地板），
  本批发布 `sc_approval_policy_productized_form_v1`（priority 800、`action_sc_approval_policy` 绑定、
  只留 title ＋ native_semantic_surface），成为该 action 的最后结构写入者。
- 字段级只读口径以**稀疏语义覆盖**承接：860 三条（`author_id`／`is_read`／`read_date`）、885 一条（`status`）、
  888 三条（`name`／`code`／`company_id`），每行只有 `name` ＋ `readonly`、不含结构键，故不产生
  `NATIVE_SEMANTIC_SURFACE_STRUCTURE_CONFLICT`；模型面本已只读的字段**不重复声明**。
- **不额外计数**：六个原生主表单 1887／1908／1910／2070／2072／2074 一模型一表单，且仍同时是其自身与兄弟
  action 的渲染目标，**不随扣减退役**（`reduction.retiredViewMeaning`）。

**旁路与补登（单列，不与核减混算；`bypassConsumers`，`counted=false`）**：同模型兄弟 action 119 core「通知」／
205「工作岗位」／28「序列」逐条给出 `whyNotCounted`（原契约按 action 作用域绑定 860／883／888，从未覆盖它们）；
保留载体 `sc_approval_policy_form_structure_generated_v1`（priority 84、无 action 绑定）保持 active——在没有
action 上下文的面上它仍是 `sc.approval.policy` 唯一的结构载体，退役属**别组的计数**。扣减范围因此保持 6 条，
**未被静默扩大或丢弃**。

**保留边界与已知限制（不随本批关闭）**：本批**未跑** `FORM_LOWCODE_TOPIC` 浏览器代表面复验、**无截图证据**
（结构交付以 L0–L4 为证据）；三个既存环境缺陷（`verify.contract.view_structure` 的 `local.clean`／`sc_clean`
权威指纹期望、`verify.product.menu.governance.m4.closure` 缺 `artifacts/menu-governance/menu-m4-runtime.REJECTED-wrong-sha.json`、
`verify.user_form.preference.boundary_guard` 依赖**客户定制 addon 仓库（不在本仓库边界内）**的模块）如实登记、**不修**；
`retirementComplete=false`。

**过程偏差与独立复核项（如实登记）**：候选内 L2 曾有一次**失败后整改**的运行（本地 05:52，容器 UTC 21:52，
`1 failed … of 20 tests`；失败断言为 `Lists differ: ['sc_source_model', 'sc_source_res_id'] != []`，
即当时要求技术踪迹不出现在面上）。该断言已拆分整改：技术踪迹口径移入
`test_the_technical_traces_stay_invisible_and_outside_every_section`，原
`test_every_retired_fact_is_still_reachable_from_the_native_arch` 收窄为业务事实集 `RETIRED_ENTRY_FACTS`。
其后重跑并留档 **23／23**（`l2-g11-class.log`）与**整组 169**（`l2-g11-group.log`，0 failed／0 error）；
**失败运行不隐藏**。
独立复核的 F1–F6 均为非阻断项，其中 F1／F2（只读 A／B 摄于最终覆盖之前、唯一留存的 L2 日志是失败运行）与
F3（727 无 A／B 用例；base_configuration／administration 的 rollout 不含 `form_structure_authority` 键，
byte-identical 只证明菜单／能力与摘要稳定）已由冻结后补测留档：交付态只读覆盖实测
（`probe-g11-overlay-shipped.json`，`residual_restored=true`：860 退役 body 声明的 **7** 个只读字段
——其中稀疏覆盖只声明 **3** 条——以及 885 `status`、888 三条，在交付态实测仍为只读）、
727／883／887 的**渲染级**探针（`probe-g11-render-extra.json`：`native_authority` ＋ `container_tree_authority`，
渲染字段 12／9／3 且 `missing` 为空）；F4（单库单角色探针面，与 G10 同残留）、F5（887 的 `readonly="1"`
回填已在候选内显式声明）、F6（文案措辞）**保持登记、不随本批关闭**。

`nextBatch.selectedGroup` 前进到 **G12 项目立项**（action 724，视图 1503，`legacyConfigurations`
`project_project_form_structure_v1`，risk high），`priorityActions` 同步为 `[724]`，`sourceMainlineHead`
更新为合入后 main；**G12 未启动**。G11 组索引就地标记 `indexStatus=historical_source`（不再是当前消费者集），
并补 `legacyConfigurationStatus` 逐名分类（五条入口 body 由本批退役，模型级生成镜像仍为当前消费者）。

本提交为**文档类单职责提交**（台账 ＋ 本记录，路径集合固定为 2）；**未触碰**任何产品代码、契约、测试或
验证工具输入，故不改动 §8.38 的 L0–L4 结论；候选的 exact-head Quick 回执属于 `a740fcf8`，
本提交自身的收据由受管门禁按 fail-closed 口径产生，**不冒充同一绑定**。

状态：**G11 主线集成完成（PR #504，squash 同树）｜批次状态：自验与冻结门禁通过；集中产品复核结论以产品方登记为准｜
未部署｜89 入口整体交付未完成｜台账 8｜G12 未启动**。

### 8.40 G12 项目立项：入口发布承接原生结构、同域竞争镜像一并退役与浏览器代表面复验（2026-09-21；**实施＋分层验证轮**；冻结／Quick／PR 属本轮收口步骤）

**范围与层级**：Formal Product Layer **P1**（施工行业标准产品默认面）；Layer Target 为
`smart_construction_core` 的入口契约、原生视图与测试，另含一处 **P4 最小扩展**——既有的只读代表面入口
`scripts/verify/local_dev_form_lowcode_scope.py` 登记 `project` topic（复用已注册的 Compose 项目、数据库、
身份与数据权威，只读、不写任何配置，只让一个已交付页面进入既有只读比对范围）。**不属** P0
（`smart_core` 不承载行业语义），不属 P2／P3。爆炸半径：入口 action **724**（menu 379「新项目立项」）、
原生视图 **1503**（`view_project_create_form`）、**同 action 同 view 的生成镜像 46**
（`project_project_form_structure_generated_v1`）、兄弟入口 725（「快速创建项目」，自持视图
`view_project_create_form_quick`）、模型 `project.project`；回滚方式为 `git revert`（纯声明变更，无数据迁移）。

**机制（这批为什么能真正降低台账计数）**：与 G07／G09／G10／G11 同一条机制。台账计数的是
`layoutPolicy != container_tree_authority` 的兼容消费者；`ui_contract_v2` 只有在
`governance["form_structure_authority"] == "native_authority"` 时才给出 `container_tree_authority`，而该字段由
入口契约的 `composition_mode ∈ {native_semantic_surface, semantic_native_surface}` 决定
（`form_structure_authority.py`）。因此本批让**本入口的发布成为本入口的最后结构写入者**并声明原生语义面，
兼容重组路径对 724 不再适用。

**修改范围（候选 8 条路径：代码／契约／测试 5 条＝4 改＋1 新增，另加本记录与切换日志 2 条，以及随
`ci.delivery.freeze.prepare` 刷新的生成物 `docs/engineering_convergence/complexity_budget_report.md` 1 条）**：

1. `views/core/project_views.xml`（1503）补 **4 个** `data-sc-anchor` 业务分组——`current_task`「当前任务」／
   `intake_risk`「立项条件」／`project_create_required`「项目创建（必填）」／`project_create_optional`
   「项目标识（可选）」；原「当前任务」分组内的两个只读字段拆成两个带 key 的分组并**保留 `readonly="1"`**；
   `manager_id` 复述 `string="项目负责人"`。**不增不删任何字段**（渲染字段集保持 12 条不变；本批改变的是
   分组口径——把原先的无标题嵌套分组提为带锚点的业务章节，并把两个只读字段拆成独立分组）。
2. `data/view_orchestration_form_section_contract_data.xml`：入口契约 139
   （`business_config_contract_project_project_form_structure_v1`）只留 `title` ＋
   `composition_mode: native_semantic_surface`（priority **90 → 800**，`view_orchestration.context` 原样保留），
   11 个 sections／54 条 fields／`semantic_anchors` 全部退役；同域竞争镜像 **46** 用既有
   `<function model="ui.business.config.contract" name="write">` 先例一并退役（`active: False`）。
3. **新增** `tests/test_project_initiation_native_lowcode.py`（tag `uc4_native_lowcode`，**15 测试**），
   并在 `tests/__init__.py` 登记；测试以「原生 arch 为地面真值」钉住渲染字段集、锚点章节集、只读口径、
   迁移 label、退役声明不可达与兄弟面（725 自持视图 7 字段）不变。
4. `scripts/verify/local_dev_form_lowcode_scope.py`：登记只读 `project` topic（724／1503／menu 379）与
   `{"section_navigation": True, "record_surface": True}` 两个既有断言电池，使本批的章节身份与 label
   在**交付页面**上被实测，而不是只在契约层被断言。

**关键决策（全部由实测驱动，不是设计时预判）**：

- **1503 无继承扇出**：运行库 `ir.ui.view.inherit_id = 1503` 命中 **0**，仓内 `inherit_id ref=view_project_create_form`
  亦 0 条（台账 `structureRelation=project_create_view_with_inheritance_fanout` 的"扇出"在运行库不成立）。
- **同域竞争镜像必须一并处置**：镜像 46（priority 77、15 字段）与入口 139 **绑定同一个 action 与同一个 view**。
  `SAVEPOINT g12_ab` ＋ `ROLLBACK TO SAVEPOINT` 的 A／B 实测（`rollback_residual` 全 true，证明 0 写入）：
  只退役 139 → **渲染直接不再解析**（`ok=false`），因为 46 成为该 action 的最后结构写入者、
  `diagnose_structure_ownership` 拒绝该 scoped 冲突；退役 139 ＋ 退役 46 body ／ `active=False` → `ok=true`，
  `container_tree_authority` ＋ `native_structured_form`。
- **退役声明与交付面本来就是两套事实**：契约 139 声明 11 个 sections（其中 **9 个无任何字段**）、54 条
  fields（**25 条 `visible:false`**）与 2 个 `semantic_anchors`，而实测渲染容器树实为 **3 个有标题业务组
  ＋ 3 个无标题嵌套组 / 12 个字段**——声明的章节与隐藏字段**从未进入渲染面**。故本批的迁移口径是"原生
  arch 即地面真值"：只把**入口自身声明的**章节身份（`current_task`／`intake_risk`）与**真实回退**的 label
  交回原生 arch，
  9 个无字段章节与 25 个隐藏字段**如实登记为"声明但未渲染"，不补成新面**。
- **唯一 label 差异**：契约声明 `manager_id` 的中文 label 为「项目负责人」，而 arch 未复述 → 页面回落模型自身
  string「项目经理」。已在 arch 复述；**浏览器实测页面上显示「项目负责人」**（见 L4）。

**分层验证结果**：

- **L0 侦察**（只读探针 `tmp/g12-evidence/probe_g12_baseline.py`／`probe_g12_ab.py` → `probe-g12-baseline.json`／
  `probe-g12-after.json`／`probe-g12-ab.json`）：确立 724 的基线权威（`layoutPolicy=business_config_sections`、
  `formPresentationMode=task`、`formStructureAuthority=entry_semantic_surface`）、镜像 46 为**同 action 同 view**
  竞争载体、1503 扇出为 0、兄弟 725 的 7 字段渲染面与 P0 自持视图。
- **L1 生成物**：`make ci.delivery.freeze.prepare` **PASS**（`component_driver_takeover_inventory PASS required=35
  missing=0 bridge_only=0 raw=0`、`contract_form_split_evidence PASS lines=1905`、
  `ci.generated_evidence.preflight PASS all content-bound generated evidence is current`）；
  `docs/engineering_convergence/complexity_budget_report.md` 随刷新由 4395 → **4396**。
- **L2 定向非零测试**：`make local.dev.test`
  `TEST_TAGS='uc4_native_lowcode/smart_construction_core:TestProjectInitiationNativeLowcode'` → **15 tests,
  0 failed, 0 error(s)**（`tmp/g12-evidence/l2-g12-class.log`）；整组回归
  `TEST_TAGS='uc4_native_lowcode/smart_construction_core'` → **184 tests（169 统计口径）, 0 failed, 0 error(s)**
  （`tmp/g12-evidence/l2-g12-group.log`，G02–G11 全组无跨批回归）。
- **L2 守卫**：`verify.formal_product_field_purity`／`verify.contract.structure_lock`（`domains=14`）／
  `verify.contract.page_v1_zero_residue.guard`／`verify.system_init.menu_boundary.guard`／
  `verify.product.configuration_center.wave1.guard`／`verify.tenant.payload_boundary` 均 **PASS**。
- **L2 域回归（只读重跑并与已提交基线逐项 diff）**：**project 域 30 个 action** 全部逐项比对——29 条只出现
  **DB 身份漂移**（本工作树 `sc_dev_demo` 经升级后 menuId／actionId 重编号），724 本身亦**只有身份漂移**
  （本批不改它对外声明的事实面）；**唯一语义差异**为 `action_sc_product_project_edit_v1` 的默认表单视图
  （`project.edit_project` → `smart_construction_core.view_sc_product_project_information_edit_form_v1`），
  属**既存报告陈旧**而非本批改动：该 action 不定 `view_id`（按模型默认表单解析），而引入该原生表单的
  `dbf1e171` 晚于已提交报告 `e76d2a3c` 的生成时点。**base_configuration 域 6 个 action 语义差异 0**
  （`{"status": "PASS", "actions": 6}`）。
- **L3 运行库**：`make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1
  CODEX_MODULES=smart_construction_core` → exit 0（含 `[local.dev.demo.authority] PASS`）；随后只读探针
  （`probe-g12-after.json`）逐项核对：139 active／priority **800**／`composition_mode=native_semantic_surface`、
  镜像 **46 `active=false`**、入口解析为 `native_authority` ＋ `container_tree_authority` ＋
  `presentationMode=task`、`effectiveContracts` 只剩 139、**`diagnostics` 为空**、渲染容器树 4 个锚点与
  12 字段及两个只读字段口径**逐项一致**；交付态未变项（1503 扇出、兄弟 action）与基线 identical。
- **L4 浏览器代表面复验（本批已跑，非未覆盖）**：`FORM_LOWCODE_TOPIC=project FORM_LOWCODE_REPRESENTATIVE=1
  make local.dev.form_lowcode.browser` → **exit 0 / `ok=true` / `restored=true`**；代表面 entry 级
  `status=passed`、创建与记录两条路由的循环全部 PASS，「当前任务」「立项条件」「项目创建（必填）」
  「项目标识（可选）」四个业务章节入口
  与「协作记录」**全部 resolve 且可见**，章节导航在 1088／390 两视口共 **28 次**位置测量无遮挡；
  包装层打印 `[local.dev.form_lowcode.browser] business fingerprints unchanged`（业务配置指纹未变）。
  证据：`artifacts/lowcode-form-loop/browser/representative-report-project.json`、
  `representative-project-724-create.png`、`representative-project-724-record.png`（截图外置于
  `sce-offrepo/artifacts`，并复制入本工作树 `tmp/g12-evidence/` 供交付证据归档）。

**未覆盖项与环境缺陷（如实登记，不写成通过）**：`retirementComplete=false`。四条**既存环境／基线缺陷**
（前三条为 G08–G11 已登记项，本批**不修**）：`verify.contract.view_structure` 的权威指纹期望
`local.clean`／`sc_clean` 证据而本工作树以 `ec2c56e5` 为基线；`verify.product.menu.governance.m4.closure`
缺 `artifacts/menu-governance/menu-m4-runtime.REJECTED-wrong-sha.json`；`verify.user_form.preference.boundary_guard`
依赖**客户定制 addon 仓库**（不在本仓库边界内）的模块。**本批新登记第 4 条**：
`verify.frontend.professionalization.collaboration_domain.runtime` 的组件级单测
`test_notification_contract_is_bound_to_exact_action_and_view` 在**合并后基线**上失败——G11 已把该契约发为
`native_semantic_surface`（＋ 3 条稀疏只读覆盖）而该单测仍断言 `entry_semantic_surface`，属 **G11 遗留的
基线缺陷**（本批未触碰该契约与其测试，按"只修所属层"口径登记不修）；因此本批的**零变化域对照**改用
`base_configuration` 域（6 action，语义差异 0），不以失效的 collaboration 域作对照。

**保留边界（不随本批关闭）**：兄弟入口 725 与其自持视图 `view_project_create_form_quick` 未被本批修改，
7 字段渲染面由单测钉住；725 在治理角色的**交付导航权限**下返回 `NAVIGATION_AUTHORITY_DENIED`，故其浏览器
覆盖由单测而非代表面路由承担（如实登记，不写成代表面通过）。本批不改 ACL／记录规则／菜单可见性，
不改模型字段，不改运行环境、数据库或端口。

**状态**：**G12 实施与分层验证完成（L0／L1／L2／L3／L4 通过）｜冻结、exact-head Quick、独立只读复核、
外部归档与 PR 属本轮收口步骤，回执以冻结与 CI 为准｜未建 PR｜未合并｜台账 8（本批扣减 8 → 7 属合并后
文档单职责提交，沿用 G03–G11 先例）**。
