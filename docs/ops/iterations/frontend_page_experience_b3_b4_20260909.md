# 前端页面体验：B3 关键事实与 B4 反馈闭环

日期：2026-09-09

状态：本地开发候选验收通过；未执行正式发布、推送或合并

起始 HEAD：`058f8bbace2a5468f786ccac2dfae45b302aac26`

产品候选 HEAD：`c3ab688bbc30e4c278cb00564d8939dde7261802`

## 1. 交付结论

本批只收口付款申请既有旅程的关键事实与详情决策表达，没有推广到其他页面类型。记录 `payment.request/15`（`SHOW-PR-04`）继续贯穿首页、我的工作、付款列表和详情。

移动列表不再按数组前三项机械截取：它消费既有列角色并优先展示 `money`，其余事实仍可展开访问。我的工作每条事项默认只保留一项权威关键事实，完整组合标题不被拆解或推断，项目、公司等辅助事实进入展开区。1440×900 实测完整显示四条事项，前三条均具有记录身份、状态、金额、展开入口和动作。

编辑详情把契约中已具有 `semanticRole=summary` 且类型为 `monetary` 的可写字段投影为独立的“关键办理金额”区域，位于摘要与当前任务之间；移动端不再把长任务提示强制排到摘要之前。390px 和 320px 首屏均可识别 `SHOW-PR-04`、核对金额并找到“提交审批”。风险提示仍使用契约提供的阶段和文字，前端没有据“阻断”字符串改变动作可用性。

B4 增补了展开/收起、列表查询与返回、真实读取失败及重试恢复的候选证据。受控 503 后页面显示单一重试动作并恢复到表单协议成功态 `ok`；业务写请求为 0。

## 2. 语义归属核实

- Formal Product Layer：通用契约消费、响应式事实排序和页面 floorplan 属于 P0；候选证据工具与本报告属于 P4。
- Layer Target：`canonicalFormFloorplan`、`ObjectTaskPage`、`CollectionMobileRecordRow`、`MyWorkApprovalWorkspace`、WorkspaceHome 及既有 local.dev 候选工具。
- Standard vs User-Specific：全部规则基于现有 `semanticRole`、`fieldType`、列 `layoutRole` 与工作事项 `facts`；没有新增建设行业默认值、客户偏好或运行时配置。
- Why Here：P1 付款表单契约已经把申请金额放入 summary 语义，付款列表的金额列也已经提供正式 money 角色。缺口发生在 P0 对“可写 summary monetary”的分区条件和移动卡片的固定切片逻辑。
- Why Not Elsewhere：无需补 P1 契约；没有按 `amount`、标题分隔符、币种符号或中文标签猜测字段，没有改审批、支付、保存或权限规则。
- Blast Radius：所有消费相同正式语义的任务表单和标准移动集合卡；单元门禁验证字段只出现一次、非金额顺序稳定、辅助事实不丢失。后端、数据库、fixture 和业务状态不变。

此前 B1+B2 报告中“当前契约未把申请金额标为 summary、B3 需要 P1 补语义”的判断由本批证据修正：受管 local.dev 的 Contract V2 输入及 `payment_request_form_productization_contract.xml` 均已有该语义。只读模式曾能进入摘要，是因为旧 P0 条件额外要求 `readonly`；编辑模式的同一字段因此落到靠后的核心输入区。

## 3. 实现结果

- Floorplan 新增 `decisionInputNodes`。筛选条件仅为权威 summary 角色、monetary 类型、可编辑且启用；字段从核心/补充区排除，保持同一字段身份且只渲染一次。
- ObjectTaskPage 在摘要后渲染关键办理金额，在其后渲染当前任务；风险区增加明确的警示分隔，不把一般可办理提示与付款阶段阻断混成同一层级。
- 标准移动卡按 `layoutRole=money` 优先，再保持原始稳定顺序；首屏额度仍为三项，全部剩余事实继续由 ScDisclosure 提供。
- 我的工作默认摘要由三项收敛为一项金额事实；标题桌面单行省略、移动两行截断，完整值保留在 `title` 与原始数据中。
- 首页移除金额旁重复的项目和公司摘要，保留完整记录标签、状态与金额，不拆解组合标签。
- 移动查看详情动作使用正式 ScButton 触控尺寸和 `data-semantic-action=open-record`，没有恢复局部原始控件样式。
- 候选工具支持 320/390 宽度、明暗主题、加载完成态、金额事实可见性、展开往返、记录返回、查询恢复和受控读取失败恢复；预期 503 只在精确注入计数内排除，其他浏览器错误仍会失败。

## 4. 验证证据

产品候选完整工作树指纹为 `282910ff3a973cadae07a19c1a98ed8e2ae33f079ff48df25902c7d140452e75`，共 7326 路径。候选绑定注册的 `local.dev`：project `sc-local-dev`、database `sc_dev_demo`、system_admin 用户 51、company 1、前端 `127.0.0.1:5176`、API proxy `127.0.0.1:18081`。

静态与受管检查通过：

- `make verify.local.dev.frontend.quick.gate`（含 strict typecheck、5166 modules build、canonical presenter 142 cases、专业组件/状态/主题与生成清单检查）
- `make verify.frontend.style_system.guard`（hardcoded color refs 0）
- `make verify.local.dev.payment_request.floorplan.readonly`（regions 9、blocked primary 0、mobile overflow 0、business fingerprint unchanged）

冻结 HEAD `c3ab688b` 的浏览器结果：

| 范围 | 结果 |
| --- | --- |
| 1440×900 明色“我的工作” | 完整显示 4 条；记录 15/14/13 各有 1 项关键事实、7 项可展开事实和明确动作 |
| 390px 明色付款列表 | 10 张已检查卡片的 money fact 全部为 primary；其余事实保留；根级横向溢出 0 |
| 列表连续旅程 | 70→0→70；进入记录 15 后返回，`menu_id=559`、`order=id desc`、`list_offset=60` 保持 |
| 390px 明色详情 | summary 顶部 351px、金额区顶部 530px、当前任务顶部 625px，三者均进入 844px 首屏；记录 15；横向溢出 0 |
| 读取失败恢复 | `ui.contract.v2` 受控 503；错误态提供 1 个重试；恢复状态 `ok` |
| 320px 暗色 | 四个样板页主题解析为 dark，根级横向溢出均为 0；详情首屏包含记录、金额和当前动作 |
| 两轮联合结果 | `pass=true`、`mutationCount=0`、`errors=[]`、`failures=[]` |

明色证据位于 `artifacts/playwright/frontend-page-experience-b3-b4-light-390/summary.json`，暗色证据位于 `artifacts/playwright/frontend-page-experience-b3-b4-dark-320/summary.json`，同目录包含桌面和移动截图；artifact 不作为产品源码提交。

## 5. 限制与状态

本批没有执行保存、提交审批、支付、删除、关注或配置发布，也没有写业务数据。真实读取失败通过浏览器路由注入 503 验证前端恢复，不代表后端故障演练。只验证当前 system_admin 会话，没有覆盖其他角色、登录流程或独立移动端。

正式 `verify.frontend.release.local`、独立评审、推送、PR、合并和发布均未执行，因此本报告不声明发布就绪。产品提交可整体回滚且不需要数据库回滚。
