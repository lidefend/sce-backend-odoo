# 前端页面体验：G0 门禁收口与 B1+B2 付款旅程

日期：2026-09-09  
状态：本地开发候选验收通过；未执行正式发布、推送或合并  
起始 HEAD：`0fef6ba993d21015f0cdfb9cc69a8c4195c24751`  
G0 提交：`e030139ab09291301dfd841a4681c24be87f4264`  
B1+B2 产品提交：`d08065ce6ecfb1346b4ad05fca3f47d854797560`

## 1. 交付结论

本批按“G0 独立门禁清理 → B1+B2 连续旅程”完成。G0 未提高阈值、增加豁免或改变 token authority：Toolbar 回到既有 token，ScTable 的翻页符号改用正式 SVG 图标，表单动作运行时通过注入既有路由查询职责降至 617 行，样式门禁恢复通过。

B1+B2 以付款申请记录 `payment.request/15`（`SHOW-PR-04`）为统一样板：首页、我的工作、付款列表及详情均绑定同一记录身份。我的工作把金额和关键业务事实压缩为首行摘要，审计及辅助事实进入可展开区；1440×900 首屏可完整扫描 3 条事项。付款列表提高标识、名称和关系列的可读下限，长值保留完整 title；390px 卡片显示 3 项关键事实，其余事实可展开，并使用独立的 44px 查看详情动作。

列表连续旅程已验证：70 条记录 → 无结果 → 清除恢复 70 条；从第 4 页打开记录 15 再返回，`menu_id=559`、`order=id desc`、`list_offset=60` 全部保持。未提交审批、支付、保存或配置动作，浏览器写请求计数为 0。

## 2. 架构与边界

- Formal Product Layer：通用展示、响应式、列表导航与状态证据属于 P0；验证脚本和本记录属于 P4。
- Layer Target：既有 WorkspaceHome、MyWorkApprovalWorkspace、ListPage/CollectionRowCell、移动记录卡、表单动作组合和 local.dev 候选视觉入口。
- Standard vs User-Specific：平台通用的事项摘要、列角色宽度、渐进展开和返回状态，不新增建设行业规则或客户偏好。
- Why Here：改动只消费已有 `facts`、`field_group`、`display_role`、money metadata 和路由查询状态。
- Why Not Elsewhere：没有拆解拼接标题、猜测币种/精度、改变契约 schema、付款审批或支付机制，也没有写入 P1/P2/P3 数据。
- Blast Radius：首页任务摘要、我的工作卡片、标准集合桌面列和移动卡片、只读验证工具；后端、fixture、数据库及运行 profile 不变。

## 3. G0 独立收口

提交 `e030139a` 包含且仅包含三个既有阻断的修复：

- ActionSurfaceToolbar 移除局部高度变量声明，移动搜索框消费既有触控目标 token。
- ScTable 上一页/下一页使用 ScIcon 的 `arrow-left` / `arrow-right`。
- `useRecordFormActions.ts` 接受 ContractFormPage 已有的 `designerRouteQueryText`，移除重复职责；文件由 622 行降为 617 行。

`make verify.frontend.style_system.guard` 通过：phase0 token 分类 131，hardcoded color refs 0。没有修改 619 行 ratchet、加入例外或以删除空行代替职责收敛。

## 4. B1+B2 实现

- 新增纯展示模块 `productMyWorkPresentation.ts`，金额只使用契约提供的 value、symbol、currency、digits；无元数据时维持已有缺省行为，不推导业务币种。
- 首页和我的工作共享该格式化入口；记录 ID 和状态作为稳定证据属性输出。
- 我的工作每条展示 3 项关键事实并保证现有 money fact 进入紧凑摘要；其余 5 项事实保留在 ScDisclosure 中。
- MyWorkView 的 `data-state` 与真实 loading/error/ready/empty 状态绑定，加载态不再冒充 ready。
- 标识、描述、关系列的自适应下限分别为 168、192、144px；普通文本、主标识和关系标签均可取得完整值。
- 移动列表卡从整卡按钮改为语义 article + 独立查看详情按钮，避免交互嵌套；首批事实与其余事实都保留契约 key。
- local.dev 候选工具等待 Home/MyWork 的真实完成态，并记录事项密度、同记录 ID、查询空态恢复、返回查询状态及移动事实完整性。

验证工具发现一项基线缺陷：`frontend_my_work_approval_guard.py` 仍引用已不存在的 `_acceptance` 菜单 XMLID；当前与起始 HEAD 的后端权威均为 `smart_construction_core.menu_sc_user_payment_apply`。本批仅修正验证锚点，不改后端契约。

## 5. 验证证据

产品提交 `d08065ce` 的完整工作树指纹为 `24dde286c1011294c394e1a47aa24ad2d6dc7aa116b2d590bc1569db7dc62df2`，共 7325 路径。候选使用注册的 `local.dev`：project `sc-local-dev`、database `sc_dev_demo`、账号 `sc_test_admin`、前端 `127.0.0.1:5176`、API proxy `127.0.0.1:18081`。

已通过的入口包括：

- `make verify.frontend.style_system.guard`
- `make verify.frontend.typecheck.strict`
- `make verify.frontend.page_identity`
- `make verify.frontend.page_pattern_reference_parity.unit`
- `make verify.frontend.state_dashboard.unit`
- `make verify.frontend.collection_mobile_record_row.unit`
- `make verify.frontend.collection_navigation_controls.unit`
- `make verify.frontend.my_work_approval.guard`
- `make verify.frontend.professional_workflow.unit`
- `make verify.frontend.overlay_lifecycle.unit`
- `make verify.frontend.theme_profile.unit`
- `make verify.frontend.scene_component_bridge.guard`
- `make verify.frontend.shared_surface_semantic_boundary.guard`
- frontend candidate build（5166 modules）

联合视觉检查覆盖桌面 1440×900 与移动 390×844，最终结果 `pass=true`、`mutationCount=0`、`errors=[]`、`failures=[]`：

| 页面/旅程 | 结果 |
| --- | --- |
| `/` 与 `/s/workspace.home` | 加载完成后均包含记录 15；等价外壳通过；横向溢出 0 |
| `/my-work` | 记录 15/14/13 在 1440×900 首屏完整可见；每条有身份、状态、3 项关键事实、展开入口和动作 |
| `/a/809?menu_id=559&order=id desc&list_offset=60` | 记录 15 打开成功；返回保持菜单、排序和页码；70→0→70；桌面/移动溢出 0 |
| `/f/payment.request/15?menu_id=559&action_id=809` | 桌面/移动均加载真实记录 15；任务 floorplan 密度检查通过；横向溢出 0 |

证据位于 `artifacts/playwright/local-dev-candidate-visual-smoke/summary.json` 及同目录截图。artifact 不作为产品源码提交。

## 6. 限制、后续与回滚

本批没有运行审批、支付和保存动作，也没有重验其他角色、暗色主题或 320px；因此结论是 B1+B2 本地候选通过，不等于正式 `verify.frontend.release.local` 或发布就绪。

移动详情的首屏包含记录身份、状态与当前任务，但申请金额没有被当前表单契约标为 `summary`，仍位于核心申请信息区域。按边界纪律，本批不按字段名复制或提升该值；若 B3 要求金额进入详情首屏，需要 P1 提供权威 semantic role，再由 P0 通用 floorplan 消费。

G0 可独立回滚 `e030139a`；B1+B2 可独立回滚 `d08065ce`。两者均不涉及数据库、fixture 或付款业务状态。下一批可在该权威语义依赖明确后进入 B3/B4；推送、PR、发布和合并仍需另行授权。
