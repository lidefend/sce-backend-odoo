# 现有业务页面系统化推广与完整交互交付记录

日期：2026-09-09  
状态：开发候选通过 local.dev Quick、定向门禁及代表性浏览器旅程；发布验收暂停  
产品候选：`487b407ec84f1a426404e03b67ec291de3746956`  
产品候选完整指纹：`5521a2d5d32be6c5434a140e648a64ab6cdb4c1a6b3b6fdbb1c31a58e9a9e79e`，7341 路径  
原始产品基线：`3d3975b3d45c1462677df0abcbb5708e4b53e0b1`  
运行环境：受管 `local.dev`，数据库 `sc_dev_demo`，候选前端端口 5176

## 1. 范围与所有权

本批从已冻结付款样板向其他现有页面推广共享集合、表单、反馈与窄屏交互，不新增业务流程或模型专属判断。

- Formal Product Layer：P0 通用前端展示与交互；P4 验证脚本、生成清单与交付证据。
- Layer Target：既有 `ActionView/ListPage/ContractForm` 链路、canonical form renderer、共享 `ScDialog` 及受管 local.dev 浏览器验证。
- Standard vs User-Specific：跨模型通用机制，不包含施工行业字段语义、客户偏好或管理员运行时配置。
- Why Here：缺口发生在规范化表单字段状态投影、响应式布局和共享浮层边界。
- Why Not Elsewhere：后端契约已经提供必填、标签、只读和关系语义；前端不猜字段、不修改业务约束。
- Blast Radius：使用 canonical form 和 `ScDialog` 的现有页面。通过静态守卫、组件/呈现清单、定向测试及材料入库真实旅程证明影响收敛。

明确未执行：acceptance 删除或重建、`.164` 数据处理、release gate、远程推送、PR 创建、审批/支付改动和业务数据写入。

## 2. 页面覆盖盘点

只读盘点以当前 `system.init`、路由、action contract 和 renderer registry 为准：24 条路由、416 个 action、422 个菜单、70 个历史页面表面。历史清单中的部分 route id 已过时，因此代表页面使用当前 authority，而不复用旧 URL。

| 页面类型/变体 | 当前能力 | 本批代表与结论 | 剩余边界 |
| --- | --- | --- | --- |
| 标准集合：桌面表格/移动卡片 | ready | 材料入库 `/a/546?menu_id=494`：查询、零结果恢复、分页/导航、打开详情与返回恢复通过 | 其他模型依赖相同共享链，未逐 action 浏览器穷举 |
| 新建/编辑任务表单 | ready | 材料入库新建 `/f/sc.material.inbound/new?menu_id=494&action_id=546`：必填错误定位、关系选择、Escape 关闭、无写入通过 | 本批未执行真实保存，避免改写 fixture |
| 层级、pivot、graph、activity | ready | registry 与既有门禁覆盖；层级工作区已有前序真实样板 | 本批未重复浏览器验收 |
| calendar、gantt、collection dashboard | readable fallback | 明确保留 fallback，不冒充完整专用体验 | 后续独立产品能力，不在本批扩建 |
| 项目经营指标空集合 | ready empty state | 当前数据为真实空态，不再要求空集合必须出现列头 | 未作为最终两条浏览器旅程之一 |
| 付款样板 | frozen | 未改付款业务表达；受影响共享层由 Quick、canonical/overlay 定向门禁回归 | 本批没有新增付款浏览器证据，沿用冻结候选证据，不混称重验 |

缺口归属：canonical 字段错误未落到实际控件、窄屏表单字段过密和共享对话框越界属于 P0；浏览器断言对空集合、移动披露及嵌套字段宽度的误判属于 P4。未发现需新增 P1 契约字段的证据。

## 3. 实现结果

### 3.1 集合和浏览器旅程推广

- 受管浏览器脚本允许权威空态不渲染列头，并识别共享空查询恢复动作“清除查询条件”。
- 移动事实展开仅在适用页面断言；集合旅程记录查询前后数量、详情记录 ID 和返回恢复结果。
- 材料入库移动卡片默认展示入库数量、金额与项目，剩余 15 项事实仍可展开访问；未加入材料模型分支。

### 3.2 表单交互与反馈

- canonical render state 将既有权威校验错误按字段标签递归映射到表单字段。
- `invalid/errorText` 位于最终 `FormSectionFieldSchema`，实际控件获得错误状态和描述，不只停留在中间 descriptor。
- 保存前缺少项目时，页面提示“请检查以下内容保存前请填写：项目”，焦点与无效字段均为 `project_id`；写入计数保持 0。
- 480px 及以下的可写 canonical 分组改为单列；只读事实网格保持原有紧凑表达。

### 3.3 共享浮层与验证可信度

- `ScDialog` 宽度受视口和既有页面 gutter token 双重约束，保留设计 token authority，没有新增样式体系。
- 320px 暗色实测弹窗宽 292px，390px 明色实测 361px；标题、关闭、结果及底部操作均在视口内。
- 手机字段宽度按最近表单网格 owner 计算，避免嵌套分区被错误判窄；失败时先保存校验证据，再报告失败。

## 4. 验收矩阵

| 候选/环境 | 页面旅程 | 视口/主题 | 核心结果 | 写入/错误 |
| --- | --- | --- | --- | --- |
| `487b407e…` / `sc_dev_demo` | 材料入库集合 | 1440 明色 | 查询→0→清除恢复；记录 1 打开→返回；导航通过 | 0 / 无 |
| 同上 | 材料入库新建 | 1440 明色 | 必填错误定位；关系搜索 26 条；键盘选择与 Escape 通过 | 0 / 无 |
| 同上 | 材料入库集合 | 390 明色 | 卡片信息完整；查询、详情往返、根级无溢出 | 0 / 无 |
| 同上 | 材料入库新建 | 390 明色 | 单列表单；无效字段获得焦点；弹窗宽 361px | 0 / 无 |
| `487b407e…` / `sc_dev_demo` | 材料入库集合 | 1440 暗色 | 与明色同一连续旅程通过 | 0 / 无 |
| 同上 | 材料入库新建 | 1440 暗色 | 校验和关系选择通过 | 0 / 无 |
| 同上 | 材料入库集合 | 320 暗色 | 卡片、动作与分页可访问；根级无溢出 | 0 / 无 |
| 同上 | 材料入库新建 | 320 暗色 | 字段最小实测 180px；弹窗宽 292px；交互通过 | 0 / 无 |

浏览器证据：

- `artifacts/playwright/frontend-existing-pages-487b407e-light-390/summary.json`
- `artifacts/playwright/frontend-existing-pages-487b407e-dark-320/summary.json`

两份 summary 均为 `pass=true`、`mutationCount=0`、`errors=[]`、`failures=[]`，且绑定同一产品候选与数据库。浏览器实际执行的是两条代表旅程；未运行分支没有计为 PASS。

## 5. 门禁与生成证据

- `make verify.local.dev.frontend.quick.gate`：PASS，最终产品源码与生成清单一致。
- `verify.frontend.typecheck.strict`：PASS。
- page pattern reference parity：PASS，11 tests，15 surfaces。
- collection navigation controls：PASS。
- professional workflow：PASS。
- overlay lifecycle：PASS，10 tests。
- canonical form presenter：PASS，143 cases。
- component driver inventory：required=35、missing=0、bridge_only=0、raw=0。
- rendering detail：164 surfaces、0 gaps；visual projection 与 official design alignment 均 PASS。

四份受影响 inventory 通过既有 Make 生成器刷新，未手工修改摘要。零测试、跳过和浏览器空错误日志均未单独作为通过依据。

## 6. 提交与回退

产品候选由以下本地提交组成：

1. `c2197f38` 集合与表单代表旅程覆盖。
2. `1b0891b2` canonical 校验状态初始投影。
3. `480c76cc` 校验失败证据保留。
4. `324a2e9b` 校验状态落到实际 canonical 控件。
5. `279ddb30` 嵌套手机字段按 owner 测量。
6. `487b407e` 共享对话框窄屏边界约束。

无数据库写入，因此产品回退只需按相反顺序撤销上述提交并重新运行受影响门禁；不需要数据回滚。浏览器 artifact 和本报告可保留作历史证据。

## 7. 退出结论与限制

本批达到开发候选退出条件：代表性集合与表单页面在桌面、390px 明色和 320px 暗色中形成查询、查看、返回、校验、关系选择和异常反馈的完整只读/无写入旅程；共享改动没有引入模型专属语义。

以下结论仍严格保留：

- 浏览器未执行真实保存；单次写入、防重复与保存后权威回读由既有 create-record 定向测试覆盖，不冒充本批真实数据库写入验收。
- 当前会话是系统管理员，不代表多角色授权通过。
- 付款样板保持冻结，本批只做受影响共享层回归，没有新增付款浏览器验收。
- performance、独立移动端、fallback renderer 产品化均未纳入。
- 这是 local.dev 开发候选，不是 PR/CI、release gate 或发布通过结论。

文档提交会晚于产品候选；最终仓库 HEAD 与上述产品候选不同属于 P4 交付记录变化，浏览器证据仍精确绑定 `487b407e…`。
