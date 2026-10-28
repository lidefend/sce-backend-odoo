# FEPC-10：协作消息作者与正文

状态：实施中；独立 PR 待审，不合并、不部署。

基线：GitHub main `27de8c2769d4c02a6e1076ad3f60fb9aa9f77e17`。PR #759 修正提交 `b62657dee68bc43c213bcd9973a7249ee887dfbb` 必需门禁均通过，合并方式待确认。本分支不包含审计 PR 的工具变更。

范围：P0 通用前端消息契约消费；P4 定向测试。后端 `chatter.timeline` 已独立声明 `message.author_name`、`body`，本轮不修改声明。排除 F1、空状态、关注者、标题、业务数据与权限。

作者只消费服务端字段；缺少可选作者字段时保持空字符串，不推测人名。正文只消费 body，空正文不以标题替代。不改变时间格式、顺序、消息类型、回复及权限判断。

证据来源：[FEPC-09 四条原始消息投影](https://github.com/lidefend/sce-backend-odoo/blob/1214b9ce88c42875436a71340f7dd6d2eea3a126/docs/ops/iterations/fe-presentation-convergence-01/fepc-09/message-author-evidence.json)。运行时基线沿用该审计，源码验证不代表已部署，不重新认证。

验证结果以 `.agent/runs/FEPC-10/run.json` 为单一索引。先记录回归测试失败，再实施最小修复。

## 声明 → 消费 → 行为

- 声明：`addons/smart_core/handlers/chatter_timeline.py` 独立返回 `message.author_name` 与正文；`frontend/apps/web/src/api/chatter.ts` 的作者字段可选。
- 消费：`professionalCollaborationModel.ts::parseMessageEntry` 原先从正文按冒号/中点截取作者，并用标题填补空正文；现直接消费上述字段。
- 展示：`ProfessionalCollaborationTimeline.vue` 原有作者、正文、时间绑定保持不变；真实 SFC 与设计系统组件经 SSR 和离线 Chromium 渲染验证。
- 缺少作者：空字符串，不以正文、meta、typeLabel 或标题替代。无作者不是权限推断，也不修改可选字段契约。

## 定向结果

| 检查 | 结果与边界 |
| --- | --- |
| 测试先行 | 修改解析器前失败：期望 OdooBot，实际为备注；原始日志 `.runtime/fepc10-red.log` |
| 消息模型 | 新增79条断言通过，含四条历史样本、中文/英文冒号、中点、多行、空正文、缺作者、输入不变及回复能力 |
| 实际组件 SSR | 7条消息、6项集合断言通过：作者/正文/时间/类型/回复/删除权限 |
| 离线 Chromium 147 | 7条消息、10项断言通过；回复事件返回原 key；正文作为文本；0请求、0控制台错误 |
| 协作守卫 | 32项测试通过 |
| 协作授权边界 | 58项测试通过 |
| 严格类型检查 | 通过 |
| L1 | `make ci.local.iteration` 通过 |

测试中仅四条作者/正文配对来自历史证据，其余 envelope、权限和补充格式为明确的合成测试数据。不会把离线组件结果当作目标 Demo 已修复或 Windows 全页面验收。时间顺序以输入序列保留，未改变后端排序；真实网络回复写入未执行。

## 范围与回滚

产品差异仅一个解析函数，删除正文猜作者和标题补正文逻辑；未改消息记录、契约、排序、类型、回复、权限及其他展示候选。测试复用现有 Make 入口，以 COLLABORATION_MESSAGE_BROWSER=1 选择离线浏览器模式，无新服务、端口、数据库、认证机制。回滚只需回退本 PR；不涉及数据恢复。

最终 Quick、远端门禁和独立 GPT 复审以候选 SHA 为准。此记录不宣称主线集成或部署完成。

首次 Quick（7b6233f2a191d85dd96f3485c2b3b0ed18d3c3d0）因新增浏览器入口未引用而被验证车道覆盖守卫拒绝。已移除该多余入口，将同一浏览器检查并入既有协作测试入口；不改守卫或冻结基线。产品代码和样本未变，重新验证受影响入口与最终 Quick。

## 合并接续

用户已明确授权 Squash 合并。审计 PR #759 已合并为 `d733dbb25f973e5a0d1087df6d88717ee0762f27`；本分支通过受管同步入口追加该 main，不重写历史。原始功能与离线测试保持不变。最终合并还需当前候选 CI、Quick 及交付规则要求的 `list_surface_structure` 运行时证据；CI 摘要不能替代该证据。旧列表证据输入指纹不匹配，不复用。当前验收后端挂载于已合并 PR #741 的工作区，需要通过既有隔离验收入口恢复候选绑定；不触碰 Demo 数据，不部署。
