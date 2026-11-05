# 项目运行逻辑与长期演进方向登记

登记日期：2026-11-05。所有者要求：把运行逻辑分析作为后续迭代的长期方向；本轮只登记，不启动产品实现。

## 证据身份与适用范围

- **原分析源码基准**：`fe719728b99cae761d50eb14eabcefc4df307adf`（main，包含 PR #810）。本文第 1–14 节归档所有者提供的源码分析，不能改称为对后续提交的完整复审。
- **来源**：本次会话中所有者提供的完整分析正文；[详细稿索引](https://chatgpt.com/library?file_id=libfile_3802ac5d2eb08191a36d7f0a2867b79d&account_id=personal)。登记时未读取该附件，正文之外的内容不作已核对声明。
- **证明范围**：源码调用关系和职责边界；原分析没有重新执行产品数据库验收。计划项、源码存在、CI 通过、部署成功和用户业务验收分别记录。
- **登记时远端 main**：`54bed83383ee2e03773141430bdd6d50ca4f932b`，包含已合并的 PR #811。原分析中“尚未合并 #811”是当时事实，不能作为当前状态。
- **持续入口**：[长期目标](../../.agent/goals/RUNTIME-FACT-PRESENTATION-EVOLUTION.yaml)、[方向决策](../../.agent/decisions/runtime-fact-presentation-evolution.yaml)。长期目标为 planned；本次登记完成不等于这些目标已实现。

## 1. 系统整体职责

| 部分 | 实际职责 |
| --- | --- |
| Odoo | 注册模型、字段、视图、动作和菜单；执行 ORM、权限、业务方法与事务 |
| 行业模块 | 实现建筑业务能力、行业事实和规则，组织入口并贡献平台扩展 |
| Smart Core | 根据事实、配置、身份和上下文生成导航、页面及操作执行契约 |
| Vue 前端 | 解码契约、选择公共组件、呈现页面、管理交互并请求后端执行 |

后端决定业务事实与执行依据，前端消费这些依据，业务结果最终由服务端决定。启动、导航、页面结构、业务记录、按钮、工作台、场景交付有各自链路，不能用一条“页面契约链”代替全部机制。

## 2. 安装模块与平台消费

Odoo 按标准模块机制加载 Python 模型及继承、XML/CSV 等数据，建立注册表和数据库记录。平台消费这些已存在的事实：

- `app.model.config` 的生成逻辑读取 `Model.fields_get()`；`app.view.config` 承载原生视图解析投影。
- Handler 通过 `INTENT_TYPE` 及别名注册；行业扩展贡献启动事实、Intent、能力和页面语义。
- 通用页面不要求每个模块单独开发 Vue 页面，但模块安装并不证明所有交互可交付；还需发布、授权、企业启用、契约表达及组件支持。

依据：[Handler 注册](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/addons/smart_core/core/handler_registry.py#L35)、[行业扩展](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/addons/smart_construction_core/core_extension.py#L1099)。

## 3. 浏览器与后端的请求链

典型请求：

```json
{"intent":"ui.contract.v2","params":{"op":"action_open","action_id":123}}
```

`intentRequest` 补充身份、跟踪及业务上下文 → HTTP POST `/api/v1/intent` → `intent_dispatcher` 校验入口、认证、Intent 权限和上下文 → `intent_router` 查 Handler、注入 Odoo 环境 → Handler 调用平台服务/业务模型 → 返回成功或失败、数据、元信息及 trace → 前端消费结果。

浏览器与后端已经通过 HTTP 跨进程通信。本地或远端不改变原理，但网络、代理、租户选择、部署版本会影响实际运行。

依据：[请求入口](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/frontend/apps/web/src/api/intents.ts#L131)、[HTTP Dispatcher](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/addons/smart_core/controllers/intent_dispatcher.py#L312)。

## 4. 登录与初始化

登录返回 Bearer token、用户、允许公司、principal 和启动指示。通常继续 `system.init`，部分启动分支涉及 `session.bootstrap`。初始化聚合产品、角色、公司、业务上下文、导航、路由授权与工作台；前端 session 校验完整性，Router 在就绪后才放行业务入口，请求层也限制初始化前的业务调用。

**登录成功、初始化成功、某项业务可用是三个不同条件。**

## 5. 中心—场景—入口导航

链路：原生菜单/动作与产品策略 → 用户、公司及启用过滤 → 最终授权导航 → 行业 Hook `project_authorized_nav_with_env()` → 中心场景投影 → 前端统一组件。

| 内容 | 原分析确认的来源 |
| --- | --- |
| 原生入口中心归属 | 沿 `ir.ui.menu.parent_id` 查业务根直接子节点 |
| 中心身份 | 稳定菜单 XMLID |
| 中心名称和排序 | 原生菜单记录 |
| 业务根外入口中心归属 | `ir.ui.menu.sc_product_center_id` |
| 导航场景身份、名称、启停、排序 | `sc.product.scenario` |
| 场景与入口关系、意图、顺序 | `sc.product.scenario.entry` |

输出 `tree.centers`；意图为辅助标签。无有效场景绑定的已授权入口在中心下直接展示。场景可跨中心，一个入口只能绑定一个场景。

AppShell 使用 `ProductScenarioNavigation`，统一消费搜索、展开持久化及当前入口。投影异常显示错误态，不切回旧侧边栏。中心数量由配置和授权决定；十个中心、91 个入口只是特定验证样本，不是全用户、全数据库固定常量。

依据：[投影](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/addons/smart_construction_core/services/scenario_surface_projection.py#L414)、[前端消费](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/frontend/apps/web/src/layouts/AppShell.vue#L169)。

## 6. 尚未统一的事实来源

导航组织读取 `sc.product.scenario/entry`；企业业务启用过滤仍读取 `scenario_product_surface.json`，把入口映射到业务场景，再结合企业启用状态限制授权入口。

因此，JSON 对导航组织已是初始化种子，但对整个系统尚未完全退为导入导出格式，它仍参与运行期启用判断。[公司路由范围过滤](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/addons/smart_construction_scene/models/product_policy.py#L9)是关键核对点。

`sc.scene / sc.scene.tile / sc.capability` 的场景页面、能力及编排，与导航的 `sc.product.scenario` 不等同。后续统一的是维护权威和显式关联，不预先裁定把不同用途强行合成一个模型；重命名、移动导航场景不能顺带授予或撤销业务能力。

## 7. 页面契约如何生成

`loadActionContractV2(actionId)` 和 `loadModelContractV2(model, options)` 是两种寻址入口，共同进入 `loadContractV2 → ui.contract.v2 → decodeContractV2Snapshot → createContractV2Store`。

后端按原生表单投影、`UiContractHandler` 通用页面、场景契约来源分支处理。通用链经过 `ActionDispatcher / PageAssembler`，聚合字段、视图、搜索、权限、动作、工作流、校验和业务配置；V2 assembler 组装，行业 normalizer/finalizer 扩展，最后归一化返回。

页面契约是运行时投影，不是逐模块人工维护完整页面 JSON。

依据：[V2 客户端](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/frontend/apps/web/src/app/contracts/v2/client.ts#L117)、[后端装配](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/addons/smart_core/handlers/ui_contract_v2.py#L1197)。

## 8. 业务配置如何生效

`ui.business.config.contract` 保存模型、视图类型、Action、View、角色、公司、优先级、启停、发布状态、版本及内容。运行时选择已启用、已发布、模型匹配、公司或全局适用、Action/View/角色适用且通过运行期校验的配置。它具备快照、摘要、草稿预览和版本恢复机制。

数据库 JSON 字段可通过正式维护入口进入权限与发布体系，不等于要求人工编辑仓库 JSON 文件。

依据：[实际选择](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/addons/smart_core/model/ui_business_config_contract.py#L707)。

## 9. 前端如何呈现及其支持边界

前端校验契约及版本，标准化字段、组件、状态、动作和数据源，按页面语义选择 Renderer，按语义或 `componentKey` 解析公共组件，再绑定记录数据并处理输入、查询、分页、关系选择、反馈、刷新与导航。

集合页使用 `ActionView` 及公共 Runtime；表单由 `ContractFormPage`、`ContractFormNativeCanvas`、`NativeFormTreeRenderer` 等消费后端结构。

`calendar`、`gantt`、`dashboard` 在原分析的集合 Renderer 注册表中仍明确降级为可读记录视图，不应称为完整专门交互。[Renderer 注册表](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/frontend/apps/web/src/app/renderers/actionSurfaceRendererRegistry.ts#L33)。V2 允许历史兼容页面分类，不能由“使用 V2”推定正式页面组合迁移已完成。

## 10. 契约与业务数据

| 通道 | 职责 |
| --- | --- |
| 页面契约 | 结构、字段语义、数据源、状态、可执行动作 |
| 数据接口 | 查询、读取、默认值、创建、修改业务记录 |
| 操作接口 | 提交、审批、支付等业务执行 |

职责分开不意味着每次必有两个 HTTP 响应。只读表单的 `mainData` 覆盖全部所需字段时可直接消费，否则另行读取。新建表单取得权威默认值，并通过原生 onchange 往返计算依赖值、状态和警告。

依据：[表单数据生命周期](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/frontend/apps/web/src/pages/contractForm/useRecordPageLifecycle.ts#L328)。

## 11. 保存与业务按钮

保存：公共表单校验 → 字段值和关系命令 → 数据写入接口 → 服务端字段政策、作用域、并发与 ORM 校验 → 保存 → 刷新/导航。异步保存归属保护防止旧页面响应污染后来打开的记录。

按钮：契约声明动作 → `execute_button` 或专用 Intent → 服务端重新确认当前记录动作授权 → 权限、作用域与业务条件检查 → 模型方法 → 执行效果。不能提交任意方法名调用；[execute_button](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/addons/smart_core/handlers/execute_button.py#L314)会重新获取动作契约。

显示按钮、允许进入页面、允许执行业务分别校验。

## 12. 业务逻辑与可配置规则

`payment.request.action_submit()` 仍在 Python 中完成权限、资金/结算范围锁、提交前置条件、明细资金检查、状态变更、审计及审批启动；审批规则通过 `sc.approval.policy / sc.approval.step` 配置。行业工作流仍有 `PROFILE_BY_MODEL`，页面 finalize Hook 仍有 Python 语义处理。

当前事实是：**代码实现业务能力，配置组织和选择可配置规则，契约表达，公共 Runtime 消费与调用。**“日常业务调整尽量通过事实配置完成”是演进目标，不是已经普遍实现的事实，也不要求把事务、不变量、安全边界和复杂算法改成任意配置。

依据：[付款提交](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/addons/smart_construction_core/models/core/payment_request.py#L3286)。

## 13. 事实维护推进状态（原分析基准）

| 领域 | 状态 |
| --- | --- |
| 中心、菜单及外部中心归属 | 原生模型/数据库字段维护 |
| 导航场景及入口关系 | 模型维护，初始化标记保护删除不被升级补回 |
| 业务配置契约 | 数据库维护、发布与版本化 |
| 审批规则 | 已有政策与步骤模型 |
| 菜单升级保护 | 指定模块、指定菜单 XMLID 范围；不是任意菜单全部保护 |
| 企业启用的入口归属 | 仍依赖 JSON |
| 产品锁定目录 | 仍有 JSON、摘要及源编译一致性校验 |
| 业务执行、部分页面语义 | 仍包含 Python 实现 |

已有策略不再被同步覆盖，不等于整条链已脱离文件约束；同步仍加载锁定契约并验证身份、引用。[锁定来源](https://github.com/lidefend/sce-backend-odoo/blob/fe719728b99cae761d50eb14eabcefc4df307adf/addons/smart_construction_core/services/locked_menu_policy_contract.py#L357)。

## 14. 两条长期主线

**事实维护贯通**：对已实现能力，把日常组织和规则调整逐步收敛到有权限、版本和发布机制的模型记录，消除重复手工维护的入口归属与发布事实。代码种子、可编辑记录、已发布快照、用户实际授权须有明确转换和边界。

**公共表现层独立优化**：在既有契约不变时改进颜色、间距、字体、公共组件、焦点、反馈和交互。字段归属、业务分组、权限、动作含义变化必须回到所属后端声明。公共 UI 优化不携带新的业务特判或前端兜底。

方向是贯通已有机制，而不是默认再增加能力登记层、另一套配置事实或每模块手写页面契约。

## 后续事实补记（不得回填为原分析结论）

| 后续事件 | 已有证据及范围 | 尚不能推定 |
| --- | --- | --- |
| PR #811 合并 | 主线 `54bed83383ee2e03773141430bdd6d50ca4f932b`；当前候选四项必需 CI 通过；35 项受管 ORM 通过 | 全产品业务验收完成；普通 PR 等同完整候选发布 |
| 日常开发环境部署 | demo/platform 两入口回读上述 SHA，构建及模块升级完成 | 旧维护配置与发布快照天然一致 |
| 所有者批准一次性导航重置 | demo/sc_demo 重置后发布快照 21/22 与发布 guard 通过；标准版 released 91，预览版 released 91 + preview 40；中文名称394项一致；17场景/79绑定；入口66项检查通过 | 91/10等样本数量是平台硬约束；数据模型或发布流程的长期冲突已根治 |
| 一次性工具留存 | 本地分支 `fix/daily-menu-code-reset-20261105`，提交 `622a0359ad9989c3fba00c80c24c82822216d870`；执行证据位于该仓库 `.runtime/daily-menu-reset/` | 工具已合并 main；生产或客户环境已授权同样重置 |

一次性演示重置是所有者明确授权的操作，不是常规部署策略；不作为以后丢弃用户配置、跳过迁移或取消备份的一般授权。运行态补记来自本会话前序操作，本登记不重复数据库验收。`.runtime` 文件为本机证据，不能当作克隆仓库后一定存在的跟踪文件。

## 迭代路线与验收门槛

以下为待拆分执行的路线，不是已排期的实现承诺。每轮以当时精确源码/部署身份重新确认影响面，沿用既有目标，避免并行建设另一套事实源。

| 编号 / 顺序 | 可独立验收的结果 | 所属层及依赖 | 最低验收行为 |
| --- | --- | --- | --- |
| RFE-01 / 首轮 | 场景、入口、企业启用的权威关系清单与迁移方案 | P1 `smart_construction_core` / `smart_construction_scene`；通用机制确需变化才进 P0；复用既有 scene/my-work 目标 | 列清 JSON 所有运行期读者、模型记录及稳定关联；明确导航重组与业务启用各自语义；设计兼容与回退，不直接把显示分组当授权分组 |
| RFE-02 / 最高实现优先 | 企业启用过滤消费唯一受管事实，导航/路由/直接调用一致 | 依赖 RFE-01；P0 机制 + P1 行业声明 + P3 维护 | 用真实 ORM 验证公司切换、撤销、缺失状态拒绝、跨公司拒绝；改名/移动/归档/删除绑定及升级保持；展示重组不得意外增权 |
| RFE-03 / 与 RFE-02 协调 | 初始化默认、维护、发布快照及回退形成一致流程 | P0 发布机制、P1 默认声明、P2 客户配置、P4 部署接线 | 正常升级保留维护；发布预检给出可解释差异；新快照与选定有效策略一致；旧快照不可改写；当前用户导航及直接动作拒绝用例通过；演示重置只可显式调用 |
| RFE-04 / 可先并行规划 | 公共 UI 表现与交互的独立迭代 | 前端通用 renderer/component 层；遵守 P0 契约边界 | 选定真实集合页/表单做桌面移动端、键盘焦点、加载/错误/保存反馈验证；业务契约与权限不变，声明缺失仍显式报错 |
| RFE-05 / 后续按收益选一项 | 已有业务能力中的一个规则配置闭环 | P1 能力与规则、P3 编辑；按用户稳定差异决定是否 P2 | 对选定规则证明编辑→发布→契约→真实执行；有正反例、审计和版本回退；保留服务端事务及业务不变量；不同时重写所有业务 |
| RFE-06 / 按具体产品需求 | Renderer 支持缺口与历史页面迁移逐项闭合 | 前端公共层 + 必要后端声明 | 明确选中 calendar/gantt/dashboard 哪一种及真实交互范围；未实现者仍如实标注降级；一项验收通过才改变支持声明，不凭 V2 标签宣布全迁移 |

RFE-01 的交付应是一份可评审的“事实→编辑→发布→消费→授权”映射和首个最小改动范围。RFE-02 与 RFE-03 共同消除事实与发布冲突；RFE-04 的纯表现改进不必等待后端全部配置化。下一轮应先选择一个可独立验收的结果，不同时扩展六条实现线。

### 每轮复核问题

1. 本轮改变哪一个权威事实或公共表现行为？当前源码与运行态身份是什么？
2. 该事实由谁维护、如何发布、有哪些读者？是否还有文件/数据库/前端重复决定同一语义？
3. 正常升级是否保留维护？是否会把展示调整误当成授权变化？
4. 哪些定向测试确实执行，哪些依赖未覆盖？不以零收集、旧 SHA 或样本计数代替证明。
5. 结果分别属于批次、主线、部署还是用户验收哪一层？不能由登记或代码存在推导完成。

本文件不替代 `AGENTS.md`、既有契约边界与受管交付入口，不新增部署或数据重置授权。

## 后续裁定：第一批三态入口控制

所有者于 2026-11-05 明确：删除场景关联是配置缺失，导航及服务端入口均应拒绝；只有显式豁免才能继续中心直连。第 5 节保留原提交的历史事实，不再作为新实现规则。第一批范围与兼容迁移见 [场景事实同源](scenario_fact_authority_20261105.md)。
