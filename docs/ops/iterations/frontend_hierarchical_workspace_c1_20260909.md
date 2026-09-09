# 前端层级工作区 C1 对齐

日期：2026-09-09

状态：C1 本地候选验收通过；未执行正式发布、推送、PR 或合并

起始 HEAD：`178df07bcdb8cabba19648e35a2deb4de5f3314d`

浏览器冻结产品候选 HEAD：`ea971cea500590a0686155b698ded828a6d7a1d3`

生成清单收口 HEAD：`8d3c67694e5b69acba713b2b2ff500737e4ee1a2`

## 1. 交付结论

本批以收入合同 46 条数据作为层级页面类型样板，完成“作用域选择 → 查询 → 选中 → 详情 → 打开记录 → 返回”的连续体验。筛选为 0 条时，旧选中记录、旧金额和“打开记录”均不再残留；清除查询后恢复当前作用域内数据并建立合理选中。

320/390px 不再以隐藏导航树的方式丢弃层级能力。移动端提供可触屏的当前范围入口和抽屉式层级选择，可辨识、切换和清除范围，44px 触控高度消费既有正式 touch-target token。桌面两处分隔条保留鼠标拖动，并支持方向键及 Home/End 调整，暴露完整的 ARIA 数值范围。

同一记录 15 贯穿列表、右侧详情和打开后的记录页。返回层级工作区后，查询 `审核通过`、范围 `S69 支付台账演示项目`、选中记录 15 和表格内部横向滚动 96px 均恢复。详情金额由契约 descriptor 的币种和精度元数据驱动，显示 `¥1,200,000.00` 等权威格式，没有在前端猜字段或币种。

付款样板保持冻结。受影响共享表达的回归确认记录 15（`SHOW-PR-04`）在桌面和 390px 列表仍显示 `¥50.00`，根级横向溢出为 0。

## 2. 分层与边界

- Formal Product Layer：层级页面交互、通用契约元数据传递和格式化属于 P0；候选验证器、Make 入口、生成清单与本报告属于 P4。
- Layer Target：`smart_core` page assembler 的通用字段 descriptor、Web `HierarchicalWorksheet`、层级交互纯函数、受管候选浏览器验证。
- Standard vs User-Specific：通用平台机制。收入合同只是现有真实页面代表，不新增建设行业默认值、客户偏好或低代码配置。
- Why Here：缺口发生在通用层级 renderer 对现有作用域、结果集、字段 descriptor 和路由返回上下文的消费方式。
- Why Not Elsewhere：无需修改收入合同业务模型、原生视图、审批动作或业务状态；未用 P1/P2 配置弥补前端交互缺口。
- Blast Radius：使用 `HierarchicalWorksheet` 的层级集合，以及 assembler 输出的通用字段元数据。后端单元测试、层级 TS 用例、完整 frontend Quick 和付款列表真实浏览器回归共同证明约束。

## 3. 实现结果

- 可见结果变化时统一校正 selected record；空结果清除详情和记录入口，恢复结果后选择首个有效记录。
- 空结果使用正式空态，并提供清除查询/范围的恢复动作；不将旧详情冒充为当前结果。
- 移动端增加当前范围按钮和层级抽屉；“全部收入合同”可清除作用域，当前选择在按钮、标题、结果集间一致。
- 导航与详情 separator 支持键盘步进、最小/最大值、`aria-controls`、`aria-valuenow` 及焦点样式。
- 表格真实内部滚动容器在打开记录前捕获，组件重新激活后于稳定帧恢复，避免失活钩子覆盖已捕获状态。
- assembler 将既有 `digits`、`currency_field` 传到层级列和详情字段，并读取所引用的币种字段；前端复用共享 monetary formatter。
- 新增 15 个层级交互断言，后端 assembler 相关套件共 18 个测试；候选视觉工具把 C1 旅程加入正式非写验证。

## 4. 验证证据

生成清单收口 HEAD 的完整工作树指纹为 `a4a1582cc04547edf9797e4b6ba9988ac0fe04f2d93113f9da01f803ec8550f4`，scope manifest `f271009bb0f42550fbcfcf9df547b655d59a94a8c941854c61bd30fe2f00c693`，共 7328 路径；baseline 为起始 HEAD。浏览器产品候选与后续收口 HEAD 的差异仅为生成的 component-driver inventory，无运行时代码差异。

候选复用受管 `local.dev`：project `sc-local-dev`、database `sc_dev_demo`、前端 `127.0.0.1:5176`、API proxy `127.0.0.1:18081`。`smart_core` 通过 `make local.dev.upgrade MODULE=smart_core` 增量升级，未手工拼装 Compose、数据库、端口、凭据或 fixture。

静态与门禁：

- `make verify.frontend.hierarchical_worksheet.unit`：PASS；后端 18 tests、前端 interaction 15 cases，domain-tab assertions PASS。
- `make verify.frontend.typecheck.strict`：PASS。
- `make verify.frontend.style_system.guard`：PASS；hardcoded color refs 0。
- `make verify.frontend.quick.gate`：PASS；strict typecheck、5166 modules build、组件/状态/主题/生成清单门禁全部完成。

同一产品候选的真实浏览器结果：

| 范围 | 结果 |
| --- | --- |
| 初始与作用域 | 初始 46 条；选择 `S69 支付台账演示项目` 后 1 条，选中记录 15 |
| 0 条一致性 | 结果 0、选中行 0、打开入口 0、正式空态 1；详情只显示选择提示 |
| 查询与恢复 | 清除后恢复 1 条及记录 15；随后查询 `审核通过` 保持选中 15 |
| 详情与金额 | 金额均含 `¥` 和两位精度；打开记录 ID 与选中 ID 均为 15 |
| 返回状态 | query、scope、selected ID 全部一致；表格 scrollLeft `96 → 96` |
| 桌面键盘 | 导航 `260 → 276 → 200`；详情 `210 → 226 → 420`；焦点落在当前 separator |
| 390px 明色 | 范围选择/切换/清除通过；触控入口 44px；根 overflow 0 |
| 320px 暗色 | 同一完整旅程通过；主题解析 dark；根 overflow 0 |
| 付款共享回归 | 桌面/390px 记录 15 均为 `¥50.00`，overflow 0 |
| 三组证据 | `mutationCount=0`、`errors=[]`、`failures=[]` |

证据文件：

- `artifacts/playwright/frontend-hierarchical-workspace-c1-light-390/summary.json`
- `artifacts/playwright/frontend-hierarchical-workspace-c1-dark-320/summary.json`
- `artifacts/playwright/frontend-hierarchical-workspace-c1-payment-regression/summary.json`

相同目录含桌面和移动截图；artifact 不作为产品源码提交。候选工具第一次运行准确暴露 42px 触控高度，修正组件包装层的 scoped selector 后，在新冻结候选上重新完整执行并达到 44px；失败运行未计入 PASS。

## 5. 限制与发布状态

本批没有创建、编辑、保存、提交、审批、支付、删除、关注或配置发布，没有修改业务数据、fixture、数据库角色、运行 profile 或端口。仅验证当前 `sc_test_admin` / system administrator 会话；未覆盖其他角色、认证旅程、独立移动端或其他层级业务流程。

正式 `verify.frontend.release.local`、独立评审、`make pr.push`、PR、合并和发布均未执行，发布状态仍为 `verification_pending`。C1 可作为已收口的页面类型样板；C2 配置与异常页面推广不属于本批，也未开始实施。
