# 后端契约职责边界

## 目标

后端契约层必须先回答“谁是事实权威、谁只是投影、谁可以覆盖谁”，再允许写代码或写数据。低代码配置、行业标准版、特定用户偏好、平台内核不能混用同一套隐含规则。

产品边界必须先于实现边界判断。正式产品归属见 `docs/product/formal_product_boundary_v1.md`；本文件只定义落到后端契约和运行时写入后的技术规则。

## 正式产品归属

| 正式产品 | 当前载体 | 后端契约职责 |
| --- | --- | --- |
| 平台内核产品 | `smart_core` | 提供契约、配置、版本、发布、回滚、审计和通用装配机制 |
| 施工行业标准产品 | `smart_construction_core` | 发布施工行业默认模型、菜单、表单、列表、搜索、审批和业务分类 |
| 特定用户产品 | 仓外私有 `sce_customer_<tenant_key>` 模块 | 发布客户确认的菜单、表单、字段、角色、初始化数据和用户偏好投影 |
| 低代码配置产品 | 配置工作台和运行时配置表 | 保存管理员显式配置，并通过版本、审计、回滚覆盖默认配置 |
| 运维交付工具 | `scripts`、迁移、runbook | 迁移、修复、重放和验证；不能成为长期事实权威 |

## 分层

| 层级 | 载体 | 职责 | 禁止事项 |
| --- | --- | --- | --- |
| L0 平台内核 | `addons/smart_core/core`、intent envelope、认证、路由、基础契约协议 | 提供稳定协议、调度、权限与基础投影能力 | 写行业业务规则、写特定用户偏好、承载客户字段顺序 |
| L1 契约基础设施 | `ui.business.config.contract`、`ui.form.field.policy`、`ui.menu.config.policy`、contract assembler | 保存和合并配置，声明 source authority 与覆盖顺序 | 通过前端兜底猜测业务语义；用文件名后缀临时决定权威 |
| L2 行业标准版 | `smart_construction_core` 数据、模型、菜单、行业默认表单/列表/审批 | 发布行业通用默认配置和业务对象 | 承载单一客户偏好；覆盖用户运行时配置 |
| L3 用户模块 | 仓外私有 `sce_customer_<tenant_key>` 模块 | 承载特定用户/企业的默认体验和上线初始化 | 直接修改平台内核；伪装成低代码用户即时配置 |
| L4 低代码运行时配置 | 配置工作台保存的表单、列表、菜单、审批配置 | 承载用户管理员在界面上的显式调整 | 修改业务事实；绕过版本、审计和作用域 |

## 偏好、有效策略与页面装配职责（2026-10-16，所有者明确）

运行时契约仍是前端唯一产品输入。后端实现必须分开事实解析、有效策略投影与页面物化，
不能把最终页面对象作为权限或个人偏好的事实来源。以下为收口目标；当前实现缺口及验证状态
记录于 `.agent/runs/MAIN-SCHEDULED-CI-CLOSEOUT-20261016/run.json`，本节不代表已实现。

| 边界 | 必须负责 | 不得负责 |
| --- | --- | --- |
| HTTP／意图调度 | 认证、请求作用域、准入、选定执行器、事务与响应 | 为轻量读取预先装配页面，按呈现结构推断权限 |
| 原生／发布配置事实解析 | 确定模型、动作、显式视图、原生视图族、配置版本和声明来源；提取字段及关联声明 | 把生成了哪些 widget、是否构造 form 当作业务事实 |
| 有效策略投影 | 按实际主体、公司、字段权限及声明约束计算有效列、允许偏好操作、核心字段与关联访问限制 | 依赖页面渲染树，复制一套行业或客户默认值 |
| 偏好存储／有效偏好 | 读取当前用户精确作用域的值；由共享策略校验、裁剪并形成有效偏好；写入同样受约束 | 调用整页 UI handler、生成搜索弹窗、扩大可见或可办范围 |
| 页面契约装配 | 消费同一事实与有效策略，生成声明的布局、组件和交互；必要时携带有效偏好 | 再定义偏好策略或从页面外观反推授权 |
| 前端 | 执行声明的结构、策略和有效偏好，保持交互与并发请求身份一致 | 补默认策略、用角色重排布局、通过个人偏好恢复无权列 |

依赖方向为“原生/发布配置事实 → 有效策略 → 页面契约或有效偏好”。原生视图可以声明
字段权限修饰和关联行为；这不意味着必须先生成完整渲染树才能提取这些声明。
`requested_surface` 与动作声明的视图族必须分开表达。禁止用伪造空 form 占位、
`views.form` 是否存在或组件生成结果维持策略分支；P1 的列表/表单治理应消费明确的
源事实及适用面，不能将行业判断下沉到 P0。

轻量策略投影不是第二权威：必须复用同一来源解析、覆盖顺序、权限约束和策略计算。
未知扩展依赖须显式登记并迁移，不能忽略后宣称等价。策略缺失或计算失败必须返回
可诊断失败，不允许吞异常后返回空策略并按“默认允许”继续。个人偏好只影响已声明
可调整的展示属性，不能改变模型权限、记录规则、字段权限及数据请求必要字段。

验收必须同时证明：有偏好与无偏好、过期列、锁定列、动态列、配置变化、账号/公司切换、
项目/往来单位专用治理及关联权限拒绝；偏好读取不再调用完整页面装配；真实 HTTP
计时与 SQL 成本降低。单付款列表相等、仅缓存命中或删除输出字段均不足以收口。

## 运行时覆盖顺序

### 视图、布局与权限职责（2026-10-13，所有者明确）

低代码布局的能力范围、容器坐标、呈现映射及拒绝条件统一见
`native_view_reuse_frontend_spec_v1.md` §14.4。低代码编辑布局声明，后端合成唯一运行时结构；
编辑权限与布局发布作用域分离，不能通过角色配置重新引入另一套布局。

**角色是授权维度，不是布局选择维度。** 本节收紧下方历史配置矩阵中“角色作用域”的含义：
角色可以限定权限策略，不能据此发布另一套表单结构。代码存在 `role_key` 筛选机制，不等于
产品已经授权角色布局；不能把这种配置选择称为权限裁剪。

| 阶段 | 权威与职责 | 禁止混用 |
| --- | --- | --- |
| 模型基础／默认视图 | P1/P2 模块声明模型的原生基础视图及继承；未指定动作视图时，P0 按明确的模型默认规则解析并记录来源 | 模型基础视图不一定是默认候选，更不一定是动作实际使用的视图；不能仅凭 model 相同替代入口验收 |
| 动作选定视图 | 动作绑定的 view、类型与上下文确定入口基线；同模型不同动作可以明确绑定不同视图 | 动作已绑定专用视图时，不能退回基础视图，或以登录角色重新选布局 |
| 合成后的布局声明 | P1 行业标准、P2 客户确认配置、P3 管理员已发布配置按合法来源合成；P0 解析、验证并记录选中配置与结构权威 | 角色或权限不能决定模板、章节、字段顺序、分栏／跨度；配置选择与权限限制不是一个覆盖顺序 |
| 权限投影后的运行契约 | P0 按实际账号、公司、ACL、记录规则、字段组及业务状态施加访问、可见、可用与只读限制 | 不得扩大权限、另造业务分区或改写布局规则；不得为保持结构向客户端暴露无权字段数据或受限元信息 |
| 实际页面 | 前端以官方组件执行最终契约，消费同一结构及权限；统一响应式机制独立于角色 | 不解析角色选模板，不按可见字段数推导业务布局，不为缺失布局参数补默认或夹取范围 |
| 验收证据 | P4 绑定上述每阶段身份，分别断言结构和权限，并观察实际组件行为 | 默认视图通过不代表动作视图通过；不同记录／版本／有效模式的截图不能证明角色导致布局变化 |

固定入口、动作视图、记录、公司、配置版本和有效渲染模式后，角色变化不得改变布局声明。
合法隐藏可使可见内容减少，但应保留可见节点的声明身份、相对顺序、所属分区及宽度规则；
不得借此添加新的“任务区”、改主副栏比例或自动重组业务信息。设备响应式、显式业务状态条件、
已授权个人视觉偏好须分别标明来源，不能伪装成角色布局。

`requestedRenderProfile=edit` 只是请求；实际有效模式可能受状态或写权限限制转为 readonly。
此时必须报告模式转换及原因，不能把 edit 与 readonly 的组件表现当作“同编辑态不同角色布局”。

角色作用域中的结构性配置必须在 P0 配置发布／解析边界拒绝或显式诊断，并回到原声明层纠正；
不能静默忽略、让前端兜底，或删除合法 ACL 以强行使两份页面相同。此项是目标约束，
现有 `role_key` 机制的实现审计与门禁仍以当前运行台账的未闭合项为准，文档修正不构成实现通过。

同入口跨账号核验必须保留完整字段 occurrence、父节点、顺序、标题、类型、columns/span，
另列权限状态和关联动作；不能删掉全部字段后只比较结构哈希。实际命中配置的 id、版本和
作用域也须比较。当前付款申请两个账号的一致结果只证明该实例，不代表所有模型或角色。

以下顺序仅适用于允许覆盖的展示属性，不是覆盖业务约束的通用流水线。来源按可信维护者、授权、作用域及版本识别，不按XML/JSON/数据库格式识别。`user_preference_projection` 表示客户模块发布的长期偏好，不等于普通用户个人偏好。完整规则如下。

### 配置权责矩阵（2026-09-16）

| 配置对象 | 维护者 | 作用域 | 允许修改的属性 | 覆盖规则 | 生效阶段 | 版本／回滚 | 最终消费者 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 业务与安全定义：模型、校验、ACL、记录规则 | 有权限的产品研发及受管模块发布者 | 租户数据库、模型、公司、角色、记录与状态 | 字段类型、计算、业务必填、权限、状态流转与动作授权；须走对应业务变更流程 | 服务端强约束；页面配置只能收紧可收紧项，不能放宽或改写业务事实 | 受管安装／升级后，读写及动作执行时再校验 | 模块版本及受管迁移；回退须评估数据兼容，不由配置回滚代替 | ORM、权限引擎、动作执行器；合成器读取约束 |
| 产品默认：原生视图、行业页面与入口配置 | 产品研发 | 产品／模块、模型、action、view、状态 | 默认章节、布局、标签、字段排列及已有动作呈现 | 保证无客户配置时完整可用；可配置属性接受合法上层覆盖 | 安装／升级及请求合成 | 模块版本；只退役明确重复默认，不覆盖租户配置 | 后端配置合成器 |
| 客户受管扩展／长期偏好 | 客户确认后由受管客户模块维护者发布 | 租户及声明的公司、入口、状态；角色仅作授权作用域 | 授权布局、标签、分组、顺序和显示策略；结构不随角色选择，业务扩展另走模型边界 | 在可配置属性上覆盖产品默认，服从业务约束及管理员显式配置 | 客户模块安装／升级及请求合成 | 客户模块版本与可重放投影；不是普通用户个人设置 | 后端配置合成器 |
| 租户低代码：正式配置源与版本 | 授权企业／实施管理员 | 租户、公司、action、view、页面状态；角色仅作授权作用域 | 声明可配置的标签、显隐、顺序、分组、布局、条件展示和企业锁定策略；结构不随角色选择，引用受管扩展字段及合法动作 | 允许的展示属性覆盖默认／客户偏好；同层同目标不兼容修改拒绝；不能获得新数据／动作权限 | 保存为草稿；同引擎预览；发布后进入正式合成并失效相关缓存 | 契约版本、审计、快照；回滚恢复完整定义、作用域及合成结果，不回滚业务数据或删除扩展字段数据 | 后端合成器；设计器编辑源，不能编辑运行契约 |
| 个人偏好：`sc.user.view.preference` 等 | 当前用户本人 | 本人、当前允许的公司／入口范围 | 显式开放的列宽、密度、展开状态、列顺序等个性化项 | 白名单属性内生效，服从企业锁定；不覆盖业务布局、权限或其他用户设置 | 本人会话／页面加载；影响结构时须进入同一合成边界 | 本人偏好保存／重置；不冒称企业配置发布或全局回滚 | 通用渲染器的个人化接口；结构属性由后端合成 |
| 运行时契约：唯一有效页面描述 | 后端引擎生成，无独立人工维护者 | 当前租户、公司、用户／角色、入口、记录状态及配置版本 | 不可作为独立配置源编辑 | 是合成与校验结果，不再次参与覆盖，不从结果反向制造新默认 | 正式请求与受控预览使用同一引擎 | 绑定输入版本／缓存身份；恢复配置后重新合成，不维护第二份页面版本 | 通用渲染器、正文、导航及预览 |
| 设计体系：tokens、主题、组件变体、响应式规则 | 设计体系与通用组件维护者；用户仅选开放主题选项 | 产品主题、组件、设备／视口与本人主题偏好 | 字号、颜色、间距、密度、视觉变体、响应式表现 | 只影响视觉表达；不能改变业务分组、字段事实、权限或动作授权 | 前端构建及主题／视口变化 | 设计资源代码版本、个人主题重置；不混入业务配置版本 | 通用渲染器与设计体系组件 |

#### 按属性合成与校验

- **布局／标签／顺序／分组**：在授权配置范围内按默认、客户受管偏好、管理员配置合成。普通用户个人偏好是独立白名单，不能因命名相近进入客户模块权威层。
- **可见性**：可收紧展示，但不可扩大字段读取权限或绕过原生条件。无权字段不得通过配置重新出现；隐藏也不构成数据安全控制。
- **只读／动作／删除**：业务只读、状态限制、ACL与记录规则不能放宽；展示只读可收紧。动作只能引用已有授权能力。
- **必填**：模型／业务必填不可取消；配置增加的展示要求须单独标明。隐藏后缺少合法默认或其他填写路径的办理页应拒绝发布，不能只验证JSON格式。
- **金额／状态／计算事实**：只从服务端模型与记录取得，页面配置不参与赋值或计算口径。
- **冲突／锁定**：不同节点或属性允许共存；同优先级同目标不兼容修改明确诊断，不能按ID、版本号或读取顺序静默选胜者。管理员锁定限制个人化属性。
- **目标身份**：使用稳定节点和字段occurrence身份。目标失效拒绝并提示；不能猜测迁移到同名字段。XML也可能承载客户扩展，数据库JSON也可能承载产品默认，格式不是权威依据。
- **可信上下文**：后端核验来源、维护者、发布权限、租户／公司／角色／入口／页面状态。客户端source、role或company声明不构成授权。

#### 分层验收状态

分别记录“配置已保存”“配置已发布”“最终契约已验证”“页面行为已验证”。内容哈希和发布状态仅证明持久化正确。
验收必须同时证明无重复权威／未经声明覆盖、合法配置生效、越界拒绝、作用域隔离、回滚恢复、正文与导航消费同一有效树；`compatibilityDependencies=[]` 不能单独证明低代码通过。
旧路径迁移台账与低代码链路状态分开。当前实施仅闭合正式表单链路，不新建配置平台，不迁移全部配置存储，不扩大为菜单／列表／审批重构。

本矩阵是已批准的目标规则，不表示现有实现已全部符合。实现差距及定向验证统一记录于 `docs/ops/iterations/uc2_material_native_migration_20260916.md`。

`ui.business.config.contract` 允许多个契约共同作用，但必须按后端统一分类排序：

1. `generated_industry_baseline`：生成的兜底行业基线。
2. `industry_standard_configuration`：行业标准版正式配置。
3. `user_preference_projection`：用户模块发布的偏好投影，例如三栏、不分 tab、菜单拆分。
4. `tenant_lowcode_configuration`：用户管理员通过低代码界面保存的显式配置。

同一层先按声明的作用域精度及priority确定允许覆盖的展示属性；同级同目标不兼容修改拒绝。version/id只用于版本身份与诊断，不得决定冲突胜负。业务与安全属性始终执行上文独立约束规则。

## 写入规则

- 低代码表单字段顺序、显隐、分组必须写入正式 view orchestration，并带 `view_orchestration.context.source = smart_core.lowcode.*`。
- 低代码菜单可见性、排序、父级调整必须写入 menu orchestration，并带 `menu_orchestration.source = smart_core.lowcode.menu_config`。
- 菜单配置面板的可配置范围必须以当前产品导航 `menu_ids` 为边界；`ui.menu_config.panel.get` 必须返回最终运行态导航树 `runtime.tree`，前端展示树只能消费该后端事实。`ir.ui.menu` 业务根全量子树只能作为后端候选素材，不能作为用户可见配置树口径；缺少 `runtime.tree` 时前端必须失败关闭，禁止回退到 `session.menuTree`、AppShell 渲染结果或原生父子树。
- 低代码审批启用、审批方式、审批步骤编排属于行业审批运行时策略，写入 `sc.approval.policy` / `sc.approval.step`，不写入表单或菜单契约；`source_authority` 必须声明 `lowcode_boundary = approval_policy`、`policy_source = sc.approval.policy`。
- 低代码“新增菜单”只创建运行时菜单入口和菜单配置策略，满足管理员即时调整；长期交付菜单必须沉淀到 L2 行业模块或 L3 用户模块。
- 低代码写入意图的 `source_authority` 必须声明 `lowcode_boundary` 和 `contract_source`，让审计能从响应元信息直接识别边界。
- 用户模块表单偏好必须写入租户模块命名空间下的 `view_orchestration.context.source`；即便契约名称是 `view_orchestration:*`，分类器也必须把它归入 L3 用户偏好投影。
- 用户模块可以写入偏好投影，但必须带客户包声明的 source，不能冒充低代码配置。
- 行业标准数据只能给默认结构和默认策略，不能处理特定用户看面。
- 运行时页面装配器不得给配置对象自身注入通用表单设计入口；审批、菜单、字段策略等对象使用专用配置面板。
- 通用 `api.data.write` / `api.data.create` 写代理不得写运行时配置模型；`ui.business.config.contract`、`ui.form.field.policy`、`ui.menu.config.policy`、`sc.approval.policy`、`sc.approval.step` 等必须走专用配置入口。
- 前端只消费后端契约和专用配置意图，不承担“判断哪一层覆盖哪一层”的职责。

## 低代码全域边界

低代码产品边界不是单一菜单配置问题，必须把表单、列表/搜索、菜单、审批、版本快照、覆盖扫描作为同一个 L4 运行时配置域验收。`scripts/verify/lowcode_config_boundary_guard.py` 是低代码全域边界总闸，必须在 `verify.business_config.unit` 和正式发布链路中执行。

| 能力 | 事实权威载体 | 允许配置内容 | 禁止回退/越界 | 必须验收 |
| --- | --- | --- | --- | --- |
| 菜单配置 | `ui.business.config.contract:menu_orchestration`，兼容镜像 `ui.menu.config.policy` | 产品导航内菜单可见性、排序、父级、用户新增菜单 | 不得从 `ir.ui.menu` root subtree 重新暴露历史验收、迁移核对、系统配置或平台治理菜单；可配置范围以产品导航 menu_ids 为准 | `verify.business_config.low_code_menu_navigation_alignment`、`verify.user_menu.reachability.guard` |
| 表单配置 | `ui.business.config.contract:view_orchestration.views.form`，兼容镜像 `ui.form.field.policy` | 字段显隐、标签、顺序、分组、布局、新增字段 | 不得保存 `legacy_lowcode_draft`；不得绕过 action/view/role 作用域；不得把运行时配置模型开放到通用表单设计器 | `verify.business_config.low_code_runtime_consistency`、`verify.business_config.low_code_group_matrix`、`verify.business_config.low_code_layout_runtime` |
| 列表与搜索配置 | `ui.business.config.contract:view_orchestration.views.tree/search` | 列表列、搜索字段、分组、筛选和默认展示方式 | `sc.user.view.preference` 只属于 `ui_only` 个人偏好，不能成为业务配置事实权威；配置端字段和办理面字段必须一致 | `verify.business_config.list_config_boundary`、`verify.business_config.low_code_acceptance` |
| 审批配置 | `sc.approval.policy`、`sc.approval.step` | 审批启用、模式、步骤、角色和条件 | 不得写入表单/菜单契约；不得绕过 `source_authority.lowcode_boundary = approval_policy` 与 `policy_source = sc.approval.policy` | `verify.business_config.approval_runtime`、`verify.business_config.low_code_acceptance` |
| 配置版本管理 | `ui.business.config.contract`、`ui.business.config.contract.version` | 发布、版本列表、快照导出、快照对比、回滚 | 不得把前端草稿、浏览器状态或个人偏好当作可回滚版本；回滚只恢复正式契约快照 | `verify.business_config.snapshot`、`verify.business_config.low_code_acceptance` |
| 配置能力边界 | `low_code_business_config_capability_matrix_v1.json`、coverage gate、boundary guards | 全量可配置范围、覆盖状态、缺口原因和补齐入口 | 不得新增低代码能力而不登记 carrier、authoring intent、runtime consumer、acceptance；不得只靠页面呈现作为边界证明 | `verify.business_config.guard_inventory`、`verify.business_config.coverage`、`verify.business_config.unit` |

低代码全域边界的统一规则：

- 每个写入口必须声明 `source_authority`，且能区分 `lowcode_boundary`、`contract_source` 或 `policy_source`。
- L4 低代码配置只覆盖运行时看面和运行时策略，不写业务事实。
- L2 行业默认、L3 用户偏好、L4 租户低代码必须按统一覆盖顺序合并，不能由前端自行判断。
- 配置端看到的字段、菜单、审批对象，必须能在业务办理面或运行时策略解析器中找到同一事实来源。
- 新增低代码能力必须同时更新 capability matrix、后端边界文档、`lowcode_config_boundary_guard.py` 和正式验收链路。

## 迭代动手前检查

每次涉及表单、列表、菜单、审批、用户偏好、契约保存时，必须先回答：

1. 这次改动属于哪一个正式产品：平台产品、行业标准产品、用户产品、低代码配置产品，还是运维交付工具？
2. 这次改动属于 L0/L1/L2/L3/L4 哪一层？
3. 写入的权威表是什么？是否只是投影？
4. 是否会覆盖用户管理员已经通过低代码保存的配置？
5. 是否需要 source authority 或 `view_orchestration.context.source`？
6. 是否有运行时配置对象误进入通用表单设计器？
7. 是否需要浏览器验证配置端和业务端两条链路？

没有回答边界，不进入实现。

产品边界判断规则：

- 通用机制进入 `smart_core`；不得带施工行业或客户语义。
- 施工行业默认进入 `smart_construction_core`；不得承载单一客户偏好。
- 客户确认且需要重放的体验进入仓外私有客户模块；不得冒充低代码即时配置。
- 管理员在界面保存的即时调整进入低代码运行时配置；若确认长期生效，必须再沉淀到用户模块或行业模块。
- 一次性修复、迁移和验收进入脚本或 runbook；不得作为长期事实来源。

## 当前后端防线

- `smart_core.utils.backend_contract_boundaries` 统一维护运行时配置模型、契约分类和覆盖排序。
- `ui.business.config.contract._effective_view_orchestration_contracts()` 只使用统一排序函数决定生效顺序。
- 低代码字段配置和契约保存入口自动补齐 `view_orchestration.context.source`。
- `PageAssembler` 通过统一边界函数屏蔽配置运行时模型的通用表单设置入口。
- `scripts/verify/backend_contract_boundary_guard.py` 扫描后端直接写 `ui.business.config.contract`、低代码运行时策略表与审批运行时策略的入口；新增写入点必须先进入白名单并说明边界。
- 如需沉淀审计结果，可设置 `BACKEND_CONTRACT_BOUNDARY_GUARD_REPORT=...`，守卫会把同一份 JSON 报告写入指定文件。
- 守卫报告必须带 `schema_version`；当前版本为 `1.0`。
- 守卫报告中的 `writer_boundary_count` 表示写入边界角色数；`writer_file_count` 表示唯一文件数。同一 handler 同时写契约镜像和运行时策略时，会计入多个边界角色。
- 守卫报告中的每条 writer 必须带 `category`：`business_config_contract`、`lowcoding_policy_runtime` 或 `approval_policy_runtime`。
- 新增扫描类别必须新增 `BOUNDARY_RULES` 规则项，不能在 `build_report()` 中复制独立扫描分支。
- 表单配置写入意图的 `source_authority` 必须带 `lowcode_boundary = form_config` 和 `contract_source = smart_core.lowcode.form_field_policy`。
- 菜单配置写入意图的 `source_authority` 必须带 `lowcode_boundary = menu_config` 和 `contract_source = smart_core.lowcode.menu_config`。
- 菜单配置读取意图必须受当前产品导航边界约束；不能把历史验收、迁移核对、系统配置或平台治理菜单从 root subtree 重新暴露为“可配置菜单”。
- 审批配置写入意图的 `source_authority` 必须带 `lowcode_boundary = approval_policy` 和 `policy_source = sc.approval.policy`。
- 用户模块偏好 source 优先于契约名称分类，防止 `view_orchestration:*` 用户偏好被误判为 L4 低代码配置。

## 当前允许直接写契约表的入口

| 文件 | 层级 | 边界 | 预期 source |
| --- | --- | --- | --- |
| `addons/smart_core/model/ui_business_config_contract.py` | L1 | 契约基础设施自身：`contract_infrastructure` | n/a |
| `addons/smart_core/handlers/form_field_configuration.py` | L4 | 表单低代码运行时配置：`form_lowcode_runtime_config` | `smart_core.lowcode.form_field_policy` |
| `addons/smart_core/handlers/menu_configuration.py` | L4 | 菜单低代码运行时配置：`menu_lowcode_runtime_config` | `smart_core.lowcode.menu_config` |
| `addons/smart_core/handlers/business_config_change_set.py` | L1/L4 | 统一可逆配置变更集原子发布与批次回滚：`atomic_lowcode_change_set_publish` | `ui.business.config.change.set` |
| `addons/smart_construction_core/models/support/formal_list_contract_sync.py` | L2 | 行业正式列表契约投影：`industry_formal_list_contract_projection` | `smart_construction_core.formal_settlement_list_contract_sync` |
| `addons/smart_construction_core/hooks.py` | L2 | 行业安装期契约来源状态规范化：`industry_install_contract_source_status_normalization`；必须通过契约模型写入口生成不可变版本 | `smart_construction_core.post_init_lowcode_source_status` |

## 当前允许直接写审批运行时策略的入口

| 文件 | 层级 | 边界 | 预期 source |
| --- | --- | --- | --- |
| `addons/smart_construction_core/handlers/approval_policy_configuration.py` | L2/L4 | 行业审批策略低代码配置：`approval_policy_runtime_configuration` | `smart_core.lowcode.approval_policy` |
| `addons/smart_construction_core/services/product_system_parameter_change.py` | L2/L4 | 受管参数变更集的审批模式映射：`governed_system_parameter_approval_mode` | `sc.product.system.parameter.change` |

## 当前允许直接写低代码运行时策略的入口

| 文件 | 层级 | 边界 | 预期 source |
| --- | --- | --- | --- |
| `addons/smart_core/handlers/form_field_configuration.py` | L4 | 表单字段低代码策略配置：`form_field_policy_runtime_configuration` | `smart_core.lowcode.form_field_policy` |
| `addons/smart_core/model/ui_form_custom_field_wizard.py` | L4 | 自定义字段同步表单策略：`form_custom_field_policy_creation` | `smart_core.lowcode.form_field_policy` |
| `addons/smart_core/handlers/menu_configuration.py` | L4 | 菜单低代码策略配置：`menu_config_policy_runtime_configuration` | `smart_core.lowcode.menu_config` |
| `addons/smart_core/handlers/business_config_change_set.py` | L1/L4 | 仅在统一变更集事务内发布菜单策略：`atomic_menu_change_set_publish` | `ui.business.config.change.set` |

新增直接写 `ui.business.config.contract` 的入口必须先更新本表和 `scripts/verify/backend_contract_boundary_guard.py`，并说明为什么不能通过现有 handler 或用户模块承载。
新增直接写 `sc.approval.policy` / `sc.approval.step` 的入口必须先更新本表和 `scripts/verify/backend_contract_boundary_guard.py`，并说明为什么不能通过审批配置 handler 承载。
新增直接写 `ui.form.field.policy` / `ui.menu.config.policy` 的入口必须先更新本表和 `scripts/verify/backend_contract_boundary_guard.py`，并说明为什么不能通过现有表单/菜单配置 handler 承载。
L2 行业默认策略入口只能发布默认看面，不能覆盖 L4 用户管理员在低代码界面保存的运行时配置。

（2026-10-13 更正）行业产品菜单默认策略已迁出低代码运行时模型：`addons/smart_construction_core/models/support/product_policy_sync.py` 现在把锁定契约文件`data/formal_business_product_menu_policy_v1.json` 投影到 P1 产品事实模型 `sc.product.policy`，不再写 `ui.menu.config.policy`；该写入入口已从 `backend_contract_boundary_guard` 白名单退役。租户侧低代码菜单策略仍然只能由 `smart_core` 的菜单配置边界写入。

## 动作提示的单事实源（2026-10-13 所有者确认）

原生模型、字段、视图及动作元数据优先。业务能否办理由同一原生事实与业务 guard 决定；
提示配置不得再次编写同义 blocked 条件或独立计算授权。配置是编辑、发布和差异载体，
只能引用该事实并声明动作关联、触发、展示或确认，最终合成为同一份契约。P0 通用消费
不得增加业务判断，P1 内容不得同时散落在 XML alert、Python profile 和前端提示逻辑。
该约束是本轮收敛目标，当前部分 action_guidance 实现尚未通过验收。

Native model/field/view/action metadata is the primary and sole fact authority.
Business eligibility and its guard share one decision source. Configuration is an
editing and publication carrier, not a parallel eligibility evaluator. Interaction
metadata references that fact and declares action association, trigger, display
and confirmation; the compiler emits one final contract. This is an owner-approved
constraint, not evidence that the current partial implementation has passed.

产品默认提示交互必须在 P1 原生模型/视图/动作元数据中完整成立，不能要求额外配置后产品才可用。P2/P3 只能在产品开放范围覆盖并合成同一份元数据。付款业务风险默认软提醒，既有 `sc.payment.force_block_all` 与 `sc.payment.force_block.<reason_code>` 可显式改为硬阻断；权限、状态转换与对象完整性不变量不属于风险开关。
Product defaults are complete in native P1 model/view/action metadata. Optional customer configuration only composes permitted overrides into that same metadata. Payment risk advisories default to soft confirmation through the existing force-block policy; authorization and lifecycle invariants remain hard constraints.

## Product facts, release records and effective navigation (2026-10-13)

Product facts define the available product: native Odoo menu/action/view identities, labels, hierarchy, ordering and permissions; P1 metadata selects the formal product entries and declares additional product semantics. Module-owned native facts must be referenced, not copied into independently editable ops lists. P2/P3 overrides are explicit facts with a scope and provenance; user/role ACL evaluation does not independently rearrange the product.

Release records bind a product-fact version to a build and target environment, its install/upgrade state and release receipt. A release snapshot is a derived record of that version, not another editable product catalogue. Legacy `release_state` fields in menu-policy projections do not authorize ops scripts to redefine names, groups or membership. A mismatched release snapshot must be diagnosed as a version/activation mismatch, never treated as an intentional product-menu removal.

Effective user navigation is the selected product version intersected with actual user/company access plus explicit authorized overrides. This iteration has an additional no-loss requirement: every existing actor/company's visible stable menu identity remains present and reachable, with original names, hierarchy, relative order and targets preserved; quick creation and menu configuration may add entries only for authorized actors. More total entries cannot compensate for a missing old entry.

The unified source becomes the formal baseline only after deterministic projections, clean installation, upgrade, effective navigation comparison and affected browser interactions pass against the frozen candidate. Source-level equality alone is not product acceptance.

### 原生事实优先修正（2026-10-13 所有者进一步确认）

收敛顺序从模型、视图与权限开始：模型字段及业务约束由所属模型声明；布局、字段顺序与动作选定视图由原生视图和动作声明；访问能力由原生 groups、ACL、record rules 与字段权限决定。产品元数据只引用这些事实并补充原生载体未表达的产品语义，不能重复定义或覆盖已有事实。

本仓库可维护的模块，产品标准缺陷必须在所属模块源码修复。不得以 P3 配置、运行时修复脚本、发布清单或前端补丁长期替代源码修正。只有依赖外部模块且不具备直接修改其源码条件时，才允许经明确归属的原生继承或适配接入；接入记录必须声明源模块、原因与影响范围，保持原生权限约束。解析不到 XMLID 本身不构成外部接入资格。

用户主动低代码定制仍是独立产品能力，必须有明确作用域和来源；它不承担修复标准产品缺陷的职责。角色权限只裁剪可见、可办与只读，不重新生成布局。模型默认视图、动作指定视图、继承后的有效视图及权限裁剪结果分别记录，不得互相冒充。

### 标准版、预览版与实验退役（2026-10-13）

标准版保留原有 90 个正式产品菜单身份并接受后续正式晋级；预览版包含正式集合及尚未正式发布的真实产品能力，数量无 92 上限。两版引用同一原生模型、动作、视图与权限，不复制业务实现。产品条目显式声明 `released` 或 `preview`，同步器不得将预览状态改写为正式状态；正式晋级与环境部署分别留证。

开发实验、路线图占位和临时验收载体不因可访问就成为预览产品。真实产品能力不能因父菜单曾被停用而被丢弃；须核查停用声明、动作及 domain/context、有效视图、权限和实际办理结果。相同模型不等于重复能力，相同动作也需核对入口上下文。处置按保留、归并、退役逐项记录依据，原有正式入口及业务数据不因清理而删除。源码清单与中间预览数量均不是正式验收结论。

显式声明 `menu_groups` 的产品版本拥有封闭的产品导航集合，包括显式空集合。原生菜单事实与角色暴露声明只能裁剪授权，不能追加集合外入口；管理员角色名不能替代原生菜单、动作或模型权限。实际导航生成后，`PRIMARY_NAV` 与 `ROLE_HOME_ACTION` 的入口及目录授权须与交付结果相交，未交付的角色声明进入既有显式拒绝分区。独立声明的 `ADMIN_ROUTE` 和 `CONTEXTUAL_ROUTE` 保留其独立权限核验，不因此进入产品侧栏或改变版本集合。未提供产品菜单声明的原生诊断预览不构成正式版本产品证明。

## 统一数据事实与授权边界（2026-10-13 所有者确认）

本节定义正式目标边界，不代表当前所有模型已经接入。执行状态和原始证据仅登记于
`.agent/runs/FE-CONTRACT-RUNTIME-02/run.json`。现有数据库架构政策仍为租户隔离唯一权威，
本节不授权跨租户共享业务数据库，也不把普通产品发布策略当作业务数据授权。

### 五个正交维度

| 维度 | 唯一职责与载体 |
| --- | --- |
| 归属身份 | 复用 `sc.tenant.company.registration` 的租户／公司绑定。业务根记录归属明确，子记录沿原生关系继承；不以创建人、名称或 XMLID 推断。 |
| 数据用途 | 注册事实声明 `customer`、`demo` 或 `test`。客户身份与非客户身份双向隔离，未知归属不放行。 |
| 共享层级 | 明确声明公司内、行业内、平台级；共享是可见范围，不转移所有权、不授予修改权、不覆盖用途边界。 |
| 业务范围 | 原生公司授权、项目授权及明确的业务范围共同约束记录。当前公司／项目筛选不是授予权限。 |
| 操作权限 | 复用能力模型、原生 ACL 和记录规则；允许发现功能、读取模板不等于允许读取客户数据或执行客户业务操作。 |

有效业务权限必须同时满足上述适用维度。组规则可以在既定上限内合并业务授权，
不能通过 OR 扩大归属、用途或公司边界。产品系统管理员仅能访问获准 demo/test 空间；
普通客户业务身份仅能访问获准 customer 空间。明确授权的测试身份可带业务角色以验证功能，
但不因此取得 customer 空间。技术超级用户与数据库运维属于单独受管的维护边界。

### 数据类别与共享

- **客户业务事实**：项目、合同、交易、人员业务档案、办理记录等。必须有归属；
  公司内共享不取消项目和操作约束。不允许仅修改一个共享标记就跨租户公开。
- **公司参考数据／偏好**：归属明确的公司字典、模板和低代码成果。由公司授权控制，
  demo/test 中的参考数据仍属于非客户空间，不能流入正式客户查询。
- **行业公共产品资料**：行业字典、标准、模板、规范等；由 P1 原生事实声明，按现有版本发布机制交付。
  客户私有扩展不因名称相同或行业相同自动进入共享集合。
- **平台公共产品资料**：跨行业的公共字典、基础定义和模板；由 P0 原生事实声明。
  租户配置权限不包含改写平台公共源的权限。
- **认证／运行元数据**：身份、会话、路由、版本等按其原有最小权限读取，不能借认证所需的
  联系人身份例外读取该联系人的客户业务字段。`company_id=False` 不表示平台共享。

公共产品资料能够被正式和测试环境共同引用，是因为其明确的产品资料性质和发布授权，
不是因为放宽了 customer/demo/test 业务数据隔离。真实业务数据拟作为共享资料时，必须通过
另行授权的脱敏／提取／审核与发布形成独立资产；不得直接改写原业务事实的归属或用途。
共享范围调整、授权撤销、停用和版本回滚必须使缓存失效，并保留原有业务引用的追溯。
跨租户共享通过版本化产品包或显式交换，不建立跨库 ORM／外键，不把客户明细同步到平台目录。

### 原生模型准入

准入覆盖完整已安装模型注册表，不以行业菜单、视图、是否已有 `company_id` 为范围边界。
根模型、关系模型、明细、SQL、共享资料、认证元数据以及 transient 的业务读写均需覆盖；
abstract 模型声明的机制必须在其具体消费者中验证。每个维度必须明确为自身事实、继承关系、
受控公共资料或有理由的不适用，缺失声明不等于不适用，也不等于允许访问。
不要求所有模型重复保存五套字段，但必须能从原生声明解析出唯一授权依据。

实施遵循最小改造原则（所有者确认）：完整注册表是检查范围，不是逐模型重写任务。
已有原生公司规则、父关系和 ACL 能正确覆盖的模型保留原机制；仅补归属缺失、
共享未声明、关联不一致和越权绕过点。技术模型与向导复用自身或调用来源的权限，
不强制增加业务归属字段；公共基础资料不重复保存客户／测试用途标记。
不得另建平行权限引擎，也不得为统一字段外观改变已有模型的事实所有者。

源模型先于投影收口：根事实须能独立表达合法业务归属；项目为可选业务范围时，不能令
无项目公司业务失去公司归属。创建、复制、导入、换父和关联写入均需证明归属一致，
派生模型从实际业务父记录继承，不能从审批模板、当前操作者或任意环境默认值补推断。
历史未知数据不通过模块升级自动归入当前公司，须保留拒绝边界并由受管迁移核实。

每个可访问模型必须具有可审计的分类和实际规则：

1. 根记录：声明原生归属关系；缺失归属拒绝业务访问，新建不能从不可靠上下文推断授权。
2. 明细／委托继承：声明唯一父归属；换父、复制、导入与派生写入不能跨越数据空间。
3. 附件／消息／活动：沿原业务记录鉴权；附件自身可见、sudo 取得元数据不构成业务授权。
4. 共享字典／认证身份：显式声明类别、共享层级和字段边界，不以空公司代替声明。
5. SQL 投影：从来源保留公司、归属及项目维度后分组；原表 record rule 不自动保护 SQL。
   无法证明分区正确的汇总不得作为可交付结果，不能给混合汇总行事后任选归属。
6. 查询、计数、搜索联想、聚合、导出、直链、文件下载和业务方法使用同一授权事实；
   业务服务不得用 sudo 绕过原调用者的边界。

规则位于所属模型／原生权限事实。P0 提供统一机制；P1 定义行业模型和行业共享资料；
P2 承载客户确认的数据基线与偏好；P3 只编辑其获准的原生事实，不能扩大自身数据权限；
P4 负责受管导入、夹具、迁移和验证，不成为长期权限事实源。

### 完成条件

- 模型覆盖清单没有未分类、无归属证明或无规则的业务入口；不能用几个代表模型通过替代全量覆盖。
- 纯管理员、管理员叠加业务角色、正式业务身份、明确测试身份分别通过允许与拒绝用例。
- 同用途内跨公司／跨项目拒绝，正式与测试互相拒绝，未注册／停用／伪造身份拒绝。
- 公司、行业、平台共享分别验证可见与可维护权限；未发布、撤销和越权扩大共享均拒绝。
- 导出、SQL 聚合、附件、关联重绑、派生写入、并发注册和缓存撤销有实际反例。
- 缺口按同一运行记录追踪；后端声明、契约消费、实际行为三段一致后才能收口。

### 页面源只装配一次（2026-10-16）

`ui.contract` 的菜单入口返回 `subject=menu` 与 `entry` 引用；只有这类声明需要
V2 解引用。动作、模型、视图入口已经经过页面装配、权限裁剪和治理，V2 必须直接
消费其产物，不得因为顶层 `model` 或辅助 `entry` 再次执行模型装配。
动作请求的显式 `view_id` 必须在首次动作分发中传入，由原生视图身份校验验证；
不允许依靠第二次装配补齐丢失的输入。完整页面保留动作域、上下文、视图选择及策略，
菜单解引用保留菜单、动作、目标视图和认证 locale。源语义变化同时更新源缓存命名空间，
避免仅更新最终缓存版本后继续消费旧源。

这一约束不授权删除关联权限、原生 form 策略依赖或按用户角色猜测所需视图。
关系弹窗投影和复制成本仍需独立取证与优化，不能用一次路径改善宣称整个平台达标。

首版参数 `approval_mode` 的写入复用参数变更集的权限、值域、影响预览、审计和回滚快照；
仅映射 `payment.request` 策略的模式与启用状态，不编辑审批步骤。通用审批配置 handler
不能替代参数变更记录及其 previous-value 回滚语义，因此登记上述精确服务路径为独立写入边界。
