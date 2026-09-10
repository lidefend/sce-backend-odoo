# 系统状态表达与恢复路径一致性（2026-09-11）

## 边界与基线

- Formal Product Layer：P0 platform kernel product。
- Layer Target：既有前端请求层、登录页、共享状态组件与只读验证工具。
- Standard vs User-Specific：平台通用状态表达和恢复机制，不含施工行业或客户语义。
- Why Here：401 跳转、登录说明、集合/表单/工作区恢复动作均是跨模型前端职责。
- Why Not Elsewhere：不修改认证、权限、令牌、业务契约、低代码配置或业务数据；P4 仅承载盘点、守卫与证据。
- Blast Radius：请求 401、登录后导航、既有状态表面的受影响回归；不自动重放任何写请求。
- 基线：`main@2f246f12ff03b1a69c80b9b5321ff72ed1cf5b51`，完整指纹 `a2d44794dcb0d230b66ecdae366565253c297b37ce3893657c9710c3c3c78714`（7379 paths）。

## 状态—说明—恢复动作—归属—证据矩阵（实施前盘点）

| 页面范围 / 状态 | 真实触发条件 | 现有说明与组件 | 恢复动作 | 源码归属 | 盘点结论与证据 |
|---|---|---|---|---|---|
| 登录 / 加载 | 提交登录且初始化未完成 | `LoginView` + `ScButton.loading`，文案“系统正在登录” | 等待；输入和其他入口禁用 | `views/LoginView.vue` | 已达标；真实公开组件参数已有隔离测试 |
| 登录 / 凭据错误 | 登录请求拒绝或密码类错误 | 表单内独立 `role=alert`，“账号或密码错误” | 修改输入后错误清除并重试 | `views/LoginView.vue` | 已达标；必须与会话过期说明分离 |
| 登录 / 会话过期 | 已登录页面的真实请求返回 401 | 当前仅跳到 `/login?reason=session_expired`，登录页不消费原因 | 当前仅重新登录；原页面地址未保留 | `api/client.ts`、`views/LoginView.vue` | **确认缺口**：原因无说明、无法证明返回原位置；现有 J09 仅证明 URL 不泄露原路径 |
| 集合 / 首次加载与刷新 | 集合请求进行中 | `ProductLoadingSkeleton`；保留内容时显示刷新状态 | 等待；刷新期保留已有内容 | `pages/ListPage.vue` | 已达标；Quick 与既有浏览器矩阵覆盖 |
| 集合 / 空数据 | 无筛选且结果总数为 0 | `ScEmptyState`，说明当前没有记录 | 刷新；有权限时保留新增入口 | `pages/ListPage.vue` | 已达标；不把空数据当错误 |
| 集合 / 无匹配 | 查询或筛选存在且结果为 0 | `ScEmptyState`，说明可调整或清除条件 | 清除查询条件；刷新 | `pages/ListPage.vue` | 已达标；既有搜索清除与旧响应失效证据保留 |
| 集合 / 读取失败 | 集合读取抛出规范化错误 | `StatusPanel` + 产品错误文案 | 重试，一次点击调用一次加载 | `pages/ListPage.vue`、`components/StatusPanel.vue` | 已达标；本批仅做受影响回归 |
| 表单 / 加载与读取失败 | 合同加载中或读请求失败 | 加载骨架 / `StatusPanel` 产品错误态 | 重试并在成功后恢复表单 | `pages/ContractFormPage.vue` | 已达标；既有失败注入已证明恢复后错误态消失 |
| 表单 / 记录不存在 | 404 或缺失记录 | 明确说明记录可能删除或链接失效 | 返回安全页面 | `pages/ContractFormPage.vue`、`views/NotFoundView.vue` | 已达标；不臆造原列表上下文 |
| 全局 / 无权限 | 路由权限守卫或读取返回 403 | `ScErrorState`，“当前角色无权访问” | 返回已授权安全页面 | `router/index.ts`、`views/AccessDeniedView.vue` | 已达标；不修改权限判定 |
| 我的工作 / 加载、失败、空 | 工作摘要请求进行中、失败或无事项 | `StatusPanel` 分别表达加载、失败、空 | 刷新/重试；请求序列与上下文 epoch 排除旧响应 | `views/MyWorkView.vue` | 已达标；既有 Alert 单次重试计数证据保留 |
| 层级工作区 / 无匹配 | 搜索或范围过滤后无可见行 | `ScEmptyState` 区分空结果并显示当前范围 | 清除搜索和/或清除范围 | `components/action/HierarchicalWorksheet.vue` | 已达标；不把契约 domain 排除结果解释为组件故障 |
| 层级工作区 / 读取失败 | 工作表数据源加载失败 | 当前内联错误区域 | 由既有加载路径重试/重新进入 | `components/action/HierarchicalWorksheet.vue` | 保留现状；非本轮确认缺口，不新建状态框架 |

## 已确认实施项

1. 会话过期说明使用登录页既有状态表达，与凭据错误分别呈现，不重复提示技术错误。
2. 原页面不进入登录 URL；仅在当前标签页会话级暂存同源内部路径，并在登录成功后再次经过既有路由权限校验。
3. 多个并发 401 只安排一次登录跳转；不重放导致 401 的请求，更不重放保存、审批或支付。
4. 暂存路径缺失或非法时使用既有安全落点；合法但已失权的路径继续由既有权限守卫显示原因和安全返回入口。硬跳转不承诺恢复未保存草稿。

## 验证计划

- 定向测试：安全路径接受/拒绝、暂存读写与清理、并发 401 单次跳转、会话说明与凭据错误分离、登录失败后不丢恢复目标、登录成功后清理。
- 既有守卫：继续禁止把敏感业务路径放入登录 URL，禁止零测试通过。
- 受管浏览器：使用 `local.dev` 候选和既有失败注入入口，覆盖桌面/移动与明暗主题；记录会话过期提示、安全返回、明确 fallback、零业务写入。
- 未覆盖边界：未保存草稿、写请求重放、跨标签页恢复、发布和真实多角色验收均不计为通过。

## 实施结果

- Batch A / 盘点提交：`98797d3c`。矩阵覆盖登录、集合、表单、我的工作和层级工作区；已达标项保持原实现。
- Batch B / 恢复实现：`472dcd9f`。新增同源内部路径校验、当前标签页会话级暂存、并发 401 单次跳转，以及登录页独立说明。401 不重放原请求，原路径不进入登录 URL。
- 浏览器修正：`48fc398d`。首次候选实测发现成功返回后响应式路由状态已变化，导致暂存值未清理；改为在导航前冻结恢复身份，成功导航后清理。
- 表达修正：`2656ad65`。人工审看发现官方 Alert 默认信息色与项目主题映射组合后对比不足；由既有 `ScInlineState` 适配层消费 `info` 背景、边框和文字 token，未使用页面深层选择器。
- 认证入口边界：`830fb7e3`。普通登录、平台管理员登录、账号激活和密码恢复入口统一拒绝递归会话过期跳转；平台管理员入口不会被降级到普通登录。
- 产品冻结候选：`830fb7e36c30df5c11aae521156f8327771fd04b`。

## 验证证据

| 证据 | 候选 / 条件 | 结果 |
|---|---|---|
| 非零定向模型与守卫 | `make verify.frontend.system_state_recovery.unit` | 历史候选 PASS；安全路径、暂存、非法输入、普通登录与平台管理员登录递归阻止、并发去重共 21 条断言，守卫 4 tests；激活与密码恢复当时仅有静态集合声明，后续补项另见下表 |
| Quick、严格类型与生成清单 | `make verify.frontend.quick.gate`，产品候选 `830fb7e3…` | PASS；受管组件接管、视觉投影和官方设计清单已刷新并通过 |
| 首次浏览器诊断 | `472dcd9f…`，light 1440/390 | FAIL；返回原页成功，但 `storedAfterLogin=/my-work`，归因并修复；不计最终通过样本 |
| 最终明色浏览器 | `830fb7e3…`，5176，light 1440/390 | PASS；2 个样本，单次注入请求、唯一说明、安全返回、清理完成、0 写入 |
| 最终暗色浏览器 | `830fb7e3…`，5176，dark 1088/320 | PASS；2 个样本，单次注入请求、唯一说明、安全返回、清理完成、0 写入 |
| 人工截图复核 | 四张 `*-session-expired.png` | PASS；说明、输入与主操作完整可见，明暗主题对比清楚，320px 无裁切 |

最终摘要：

- `artifacts/playwright/system-state-recovery/830fb7e3/light/summary.json`
- `artifacts/playwright/system-state-recovery/830fb7e3/dark/summary.json`

两份摘要均绑定同一冻结候选；不能合称为全系统业务验收。浏览器仅使用 `sc_dev_demo` 既有只读页面与受控 401 注入，`mutationCount=0`。

## 独立复核补项与最终候选

独立复核指出两处实现/证据不一致：浏览器访问 `window.sessionStorage` 属性本身可能抛错；原说明还把合法但已失权的地址误写成必然进入首页。补项提交 `efab86fe` 只关闭这两处，不修改认证、权限、业务契约、页面布局或业务数据。

- `browserRuntime()` 在受保护区内取得存储；属性访问失败时以 `null` 表示“无恢复目标”，401 仍只安排一次 `/login?reason=session_expired` 跳转。
- `getItem`、`setItem`、`removeItem` 失败继续分别降级为空目标、写入失败和无阻断清理；不重放原请求。
- 登录说明改为“重新登录后将尝试返回原页面；无法访问时显示原因，并提供安全返回入口”，与现有 `access-denied` 路由守卫一致。
- 账号激活与密码恢复入口已补行为测试，不再只以静态集合声明声称覆盖。

| 补项证据 | 候选 / 条件 | 结果与边界 |
|---|---|---|
| 非零定向测试 | `make verify.frontend.system_state_recovery.unit` | PASS；30 assertions、5 guard tests。隔离覆盖存储属性访问失败、读/写/删除失败，以及登录、平台管理员登录、激活、密码恢复四个入口的递归阻止 |
| Quick / strict / build / 官方组件守卫 | `make verify.frontend.quick.gate` | PASS；生成清单同步，无新增组件接管缺口 |
| 明色恢复结果 | `artifacts/playwright/system-state-recovery/efab86fe/light/summary.json`；1440/390 | 6 个路由视口 PASS；授权目标返回 `/my-work`，目标缺失使用既有 `/s/workspace.home`，失权目标进入 `access-denied` 后安全返回；0 写入、errors/failures empty |
| 暗色恢复结果 | `artifacts/playwright/system-state-recovery/efab86fe/dark/summary.json`；1088/320 | 同三类结果共 6 个路由视口 PASS；0 写入、errors/failures empty |
| 候选指纹 | `artifacts/fingerprints/system_state_recovery_candidate_efab86fe.json` | `a5394b784767e82e23bdcd2e2e1c685950b88ce7af91dd4a319bfa2fdfdb103b`，7385 paths |

浏览器证据中的每次受控 401 均计数为 1，登录 URL 不携带原地址，成功登录后暂存均已清除。失权样本实际记录 `reason=NAVIGATION_AUTHORITY_DENIED`，并验证“访问受限”和“返回安全页面”入口；没有修改权限规则。存储不可用属于隔离运行时测试，不冒充真实浏览器环境限制证据。候选服务已停止。

## PR 交付包

状态：`LOCAL_PR_PACKAGE_READY`。`git fetch --prune origin` 后，实时 `origin/main` 与共同基线均为 `2f246f12ff03b1a69c80b9b5321ff72ed1cf5b51`。交付整理源 HEAD `efab86fee1a00822907c5f4a68131fceebf7382b` 相对共同基线为 8 commits、20 paths、729 insertions、23 deletions；全部路径已归类：

| 分类 | 路径数 | 内容与审阅重点 |
|---|---:|---|
| P0 产品前端 | 4 | `api/client.ts`、`sessionExpiredRecovery.ts`、`ScInlineState.vue`、`LoginView.vue`；审阅单次跳转、安全地址、登录说明和共享信息态对比 |
| P4 验证与入口 | 9 | 2 个前端脚本、6 个 Python/浏览器守卫及 `make/frontend.mk`；审阅非零断言、失败注入、路由结果和零写入边界 |
| 生成清单 | 4 | rendering-detail 下四份既有受管清单 |
| 治理文档 | 3 | 目标、阶段报告、上下文日志；本报告同时承载 PR 草稿，不新增重复阶段报告 |
| 未分类 | 0 | 无 `addons/`、contract/schema、数据库、fixture、Compose/profile、acceptance 或发布实现 |

风险分类绑定 `2f246f12…efab86fe`：`lane=HIGH_RISK`、`frontend_mode=full`、`professional_mode=full`、`frontend_full_required=true`、`backend_changed=true`，原因为 `high_risk_path` 与 `unknown_path_fail_closed`。净差异没有后端产品文件；`backend_changed=true` 保留为 fail-closed 结果，不手工降低。

建议 PR 标题：

`fix(frontend): align expired-session recovery outcomes`

PR 正文已整理到 `artifacts/pr_body.md`，内容包括用户可见改善、P0/P4 边界、分候选证据、风险和回滚。`public_guard`、`professional_quality_gate`、`frontend_release_gate`、`merge_policy_gate` 当前均为 `not_run`；push、PR 创建、合并、发布、acceptance、多角色和真实业务写入均未执行，不能预填通过。

交付文档检查中，inventory、links、temp guard 和 contract sync 均 PASS；`verify.docs.product_boundary` 因 `smart_construction_demo` 已在实时 `origin/main` 文档登记但 `addons/` 不存在而 FAIL。完整分支差异不包含该模块或产品边界文档，因此登记为既有独立治理问题，不在本专题删除声明、补建模块或降低断言；`verify.docs.all` 不计通过。

## 结论与遗留边界

本专题的开发阶段目标及独立复核补项完成，交付包已可审查：会话过期原因可见且不与凭据错误混淆，安全返回目标不暴露在 URL；合法且仍有权限时返回原页面，缺失/非法目标使用既有安全落点，合法但失权目标由既有权限守卫显示原因和安全返回入口；存储不可用不阻断登录跳转。集合、表单、无权限、记录不存在与工作区状态盘点未发现需在本批修改的共享缺口。

以下仍是明确未交付项：未保存草稿恢复、写请求自动重放、跨标签页恢复、真实多角色业务验收、发布与 acceptance 环境工作。它们不由本轮结果推导为通过。
