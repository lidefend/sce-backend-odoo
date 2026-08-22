# TDesign Admin 升级台账

更新时间：2026-08-21

本轮复核状态：已完成消息入口剩余能力、共享 Contract normalized store、权限门禁、Pivot 行列矩阵、x2many 行补丁、Calendar/Gantt/Activity 交互、批量审批确认、场景权限表达式和配置快照差异；本轮继续补齐后端管理员身份优先判定、Scene Block Registry、视图能力协商诊断、Contract 结构校验和旧端业务配置 Intent SDK。下表中的“已实现首轮”不等于 Odoo 等价验收通过，仍需结合真实 Contract、角色和数据范围验收。

## 目标

TDesign Admin 作为智能施工业务前端，保持 Odoo 原生后台的业务结果、权限、状态和动作语义，同时提供更适合业务用户的工作台和页面体验。

本台账只记录前端升级范围，不修改 Odoo 模型、ACL、Record Rule、数据库结构或正式后端接口。

## 当前已具备

| 能力 | 当前状态 | 主要实现 |
|---|---|---|
| 登录、退出、账号切换 | 已完成 | token、system.init、动态路由、退出清理 |
| 公司、项目、经营方式 | 已完成基础链路 | BusinessContextSwitcher、业务上下文快照 |
| 动态菜单 | 已完成基础链路 | navigation_v1、动态路由、路由权限校验 |
| Contract 版本协商 | 已完成首轮 | `src/runtime/contract` |
| 列表 | 已完成首轮 | 列、筛选、分组、分页、排序、导出、列偏好 |
| 卡片、看板 | 已完成基础运行时 | Action surface registry |
| Pivot、Graph、Calendar、Gantt、Activity | 已完成首轮运行时 | `AdvancedViewRuntime.vue`，仍需真实 Contract 对照验收 |
| 详情、新建、编辑 | 已完成 | 右侧抽屉、脏数据保护、409 冲突 |
| modifier、onchange、domain | 已完成基础语义 | `modifier.ts`、关系选项联动 |
| 附件、Chatter、活动、关注者 | 已完成常用能力 | RecordDrawer |
| 业务按钮、状态、权限 | 已完成首轮 | Contract action/status/model rights |
| 消息中心 | 已完成基础页面 | 会话、消息读取、发送、已读 |
| 场景页 | 已完成基础运行时 | 指标、待办、预警、快捷入口、表格、看板 |
| 配置治理 | 已有页面 | 菜单、业务、表单字段、发布操作台 |

## 本轮新增升级

| 能力 | 实现 | 说明 |
|---|---|---|
| 管理员身份来源 | 已升级 | 优先消费 `user.is_platform_admin`、`role_surface`、后端 capabilities 和 `route_authority.admin_actions`；固定 XMLID 仅保留兼容兜底，不再只依赖登录名。 |
| Scene Block Registry | 已升级首轮 | 新增 `sceneBlockRegistry.ts`，场景先解析注册表再渲染；未知或缺失 Block 输出 `SCENE_BLOCK_KIND_NOT_REGISTERED/SCENE_BLOCK_KIND_MISSING`，不静默降级成错误类型。 |
| 高级视图能力协商 | 已升级首轮 | Pivot/Graph/Calendar/Gantt/Activity 根据 Contract renderer/data source/维度配置判定 ready 或 fallback，并显示 reason code。 |
| Contract 结构诊断 | 已升级首轮 | 解码器校验布局、状态、动作、数据和运行时段落的基本形状，并报告 schema hash/source revision 缺失；legacy 只警告，兼容性错误才阻断。 |
| 业务配置 SDK 覆盖 | 已补齐 | 新端统一 SDK 新增旧端仍在使用的 list_search、analysis、form audit、lowcode、contract save/publish、mutation audit Intent。 |

## P0：必须优先补齐

### 1. 消息入口统一

当前顶部铃铛调用 `mail.notification`，消息中心调用 `global.message.*`。两者都是真实接口，但未统一未读数和消息类型。

已完成：

- 铃铛同时汇总业务通知和全局会话未读数；
- 通知点击后根据 `sc_source_model/sc_source_res_id` 打开记录路由，站内消息进入指定会话；
- 会话页支持服务端分页、30 秒刷新和当前会话未读清零；
- 发送失败显示错误并提供重试按钮；
- 登出、切换账号后停止轮询并清空消息状态。

仍需真实验收：通知打开记录是否能按每个动态菜单上下文恢复正确抽屉 Contract。

验收：创建一条 `mail.notification` 和一条 `global.message` 后，铃铛数量、通知列表、会话未读数一致；点击业务通知可以进入对应记录。

涉及接口：`listNotifications`、`global.message.inbox`、`global.message.conversations`、`global.message.send`、`global.message.read`。

### 2. 高级视图 Contract 等价

当前高级视图已经优先读取 Contract 声明的数据源和 `api.data` 服务端分组/聚合结果；Calendar/Gantt/Activity 的完整 Odoo 语义仍未完成。

已完成首轮：

- Pivot/Graph 按 Contract 维度请求 `grouped_rows/aggregates`；
- 前端当前页计算明确保留为 legacy fallback；
- 未注册渲染器显示 `reason_code`。

已实现首轮：

- Pivot 支持 Contract 配置的行维度、列维度和矩阵列；
- Calendar 支持月份切换并使用本地日期键；
- Gantt 拖拽按源任务持续时间计算新起止时间并调用真实写入；
- Activity 支持完成、取消、改期入口。

仍需真实模型验收：

- Pivot 的行维度、列维度、聚合函数、展开层级和组内分页；
- Graph 的 series、measure、dimension、图表类型和 legend 配置；
- Calendar 的开始/结束时间、颜色字段、全天事件和月份切换；
- Gantt 的依赖关系、分组、里程碑、进度、时间尺度和拖拽权限；
- Activity 的活动类型、负责人、截止日期、完成/取消动作；
- 服务端 `dataContract` 聚合数据优先，前端 rows 只作为明确 legacy fallback；
- 不支持的组件必须显示 `requestedRendererKey/activeRendererKey/reasonCode`。

验收：同一 action 在 Odoo 原生、SC Web、TDesign Admin 中维度、总数、汇总值、状态和可执行动作一致。

### 3. 表单关系字段高级交互

当前 many2one/many2many 已支持 Contract 权限、动态 domain、onchange、快速新建和打开关联；one2many 仍是基础明细编辑。

已实现首轮：

- one2many 明细支持 many2one/many2many 嵌套列；
- 行级 modifier、domain 和 onchange patch 回写；
- Contract normalized store 统一索引字段、动作和按钮状态。

仍需真实模型验收：

- many2one 快速创建、打开关联记录、最近记录和显示名回显；
- many2many 标签删除、批量搜索、快速创建和关联记录打开；
- one2many 行级 Contract、行内 modifier、行级 onchange 和嵌套关系字段；
- domain 支持 `context`、`parent`、公司/项目上下文和多层关系路径；
- 关系选项加载取消、分页、缓存和竞态保护；
- 关系字段权限禁止时不能通过快速创建绕过。

验收：切换项目后，客商、合同、成本、结算等关联下拉只显示当前权限和上下文范围；保存后 x2many 命令结果与 Odoo 一致。

### 4. 动作和审批语义

当前按钮已经支持 Contract intent、allowed、disabled、buttonStatus、危险确认和原因；审批历史/下一节点已可读取 workflow Contract 展示。

已实现首轮：

- 审批/危险动作二次确认和原因必填；
- 批量动作按 Contract 动态生成并确认；
- workflow history、next node 和拒绝状态展示；
- `write=false` 时不渲染变更动作。

仍需真实模型验收：

- 动作确认、原因填写、批量选择和危险操作二次确认；
- 审批流转前置条件、当前节点、下一节点、拒绝原因和审批历史；
- action 返回的 `target`、`navigation`、`notification`、`reload`、`close` 统一执行；
- 幂等键、重复点击保护、409 冲突和动作结果 trace 展示；
- 行动作、批量动作和表单动作统一走 action registry；
- 状态栏、字段 readonly、按钮 visible/enabled 使用同一状态计算器。

验收：提交、审批、驳回、撤回、完成等动作在权限允许和禁止两种账号下结果一致，禁止动作不能只靠隐藏按钮实现。

## P1：业务等价补齐

### 5. 场景运行时

- 支持完整 Zone、Block registry、页面权限表达式和数据依赖错误隔离；
- 支持 `kanban_board`、复杂工作区、记录区块、关系区块和页面级工具栏；
- 每个 block 记录 active renderer、fallback reason 和 trace；
- 场景恢复建议使用统一 `SuggestedActionBar`。

### 6. Contract 严格解析和恢复

- 对 pageInfo、layout、data、action、status、runtime 做 schema 级校验；
- legacy contract 明确记录降级，不静默猜字段或视图；
- 校验 schemaVersion、schemaSha256、sourceRevision 和生命周期信息；
- 统一错误 envelope、401、403、409、429、5xx、超时和可重试状态；
- 正式接入 `meta.intent_catalog`，自动检查接口登记、调用和未知 intent。

### 7. 配置治理

- 菜单配置：复制、拖拽排序、父级调整、角色范围、版本比较、审计、回滚；
- 表单字段配置：分区、Notebook、嵌套分组、拖拽排序、实时预览、发布、回滚；
- 业务配置：变更集、校验、预览、覆盖率扫描、审批策略、发布历史；
- 发布操作台：快照、历史动作、受控菜单、受控能力和回退确认。

### 8. 我的工作和首页

- 根据 `model/action_id/record_id/menu_id` 自动解析目标；
- 支持批量完成、失败重试、后端排序和分页；
- 首页指标、待办、风险、快捷入口完全读取工作台 Contract；
- 空状态、权限状态、异常状态和恢复动作统一展示。

## P2：质量和交付

### 9. 自动化质量门禁

- 建立 `ApiCapabilityRegistry` 与 `meta.intent_catalog` 差异检查；
- 21 个角色的菜单、读、写、审批、禁止动作测试；
- 项目、合同、采购、付款、结算、审批端到端流程；
- 列表、看板、表单、x2many、附件、Chatter、导出验收；
- 三套主题、暗黑、中文、响应式和退出换账号流程；
- `npm run test`、覆盖率、浏览器控制台和网络错误门禁。

### 10. 发布和回退

- 正式构建明确产物目录和版本号；
- TDesign Admin 与旧 SC Web 的 Nginx 静态目录明确区分；
- 保留旧前端镜像和回退配置；
- 发布前生成 Contract 能力报告、API 覆盖报告和页面等价报告。

## 推荐实施顺序

1. 统一消息未读和消息入口；
2. 完成高级视图 Contract 数据源和服务端聚合；
3. 完善关系字段、动态 domain 和 x2many；
4. 完善审批动作、确认、结果处理和权限状态；
5. 完成场景 Zone/Block 运行时；
6. 完成配置治理发布生命周期；
7. 建立角色和接口自动化验收；
8. 最后切换正式 Nginx 入口。

## 切换条件

只有当 P0/P1 项目达到“已对接、已验证”，并且不存在静态 mock、未知接口、未实现按钮、权限绕过、控制台阻断错误时，才允许把正式入口切换到 TDesign Admin。
