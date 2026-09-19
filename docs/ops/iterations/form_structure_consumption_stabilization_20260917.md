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

状态：**自验与冻结门禁通过、待集中产品复核（本批范围）｜已完成有界复核轮二（身份／角色／工具补验，见 §8.35.13）｜本轮新候选由提交后回执记录（原候选 `6511134c586320b8c07f1be8aa9d60ecb9d046d3` 已被本轮提交取代）｜未集成｜未部署｜89 入口整体交付未完成｜台账 22**。
**G08 主线集成 ≠ 部署 ≠ 89 入口整体交付完成**，本批同理。

**口径更正（见 8.35.12-①）**：本段原写「G09 批次验收完成」，现更正为「自验与冻结门禁通过、待集中产品复核」。
按 AGENTS.md「Completion Status Boundaries」，`批次验收完成` 只能在 scoped changes ＋ targeted tests ＋
**batch product review** 三者都通过后使用；集中产品复核尚未完成，故不得使用该措辞。

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
