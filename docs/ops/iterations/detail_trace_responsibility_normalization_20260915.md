# 明细操作与追溯职责收口（2026-09-15）

## 交付摘要

本批以 `origin/main@f8dcd8f650025f57b9ffcf8eff51adc0e4d92f68` 为基线，在唯一写入工作树和分支 `codex/detail-trace-responsibility-v1` 上完成三项相互配合的结果：

1. 付款申请的结算来源只在“付款依据”保留主编辑位置，已付/未付金额只在“履约与追溯”承接；嵌套明细中的来源列保持不变。
2. 共享 x2many 操作文案跟随最终命令语义：持久化 O2M 子记录删除显示“删除”，M2M 关系移除显示“解除关联”，未保存新行只取消本地草稿；原生 `delete="0"` 继续禁止删除。
3. 修复正式收款申请入口在渲染前丢失 `formPresentationMode`，并补齐原生 x2many 能力到最终策略的收紧式传递。前端 Schema 继续 fail-closed，不放宽枚举、不使用模型特判。

产品源候选为 `ca5a2e0f685cc3584390b5ff0d962810befbf116`，Tree `64c2c512ad1507f0cf5ca7313d795cb1a650c40f`，完整工作树指纹 `5227b6dd75077795a25c0b8ee9f6c4721d0e4da6f05477b76ddfa406ca047cf3`。最终交付 HEAD 将在本文、PR 草案及生成证据提交后冻结。

## 产品与架构边界

| 层级 | 本批职责 | 明确未做 |
| --- | --- | --- |
| P1 | `smart_construction_core` 声明付款依据、追溯字段 occurrence 与原生 x2many 能力 | 不改金额、审批、权限、保存协议或业务数据语义 |
| P0 | `smart_core` 通用契约合成和原生能力保真；共享前端按最终 relation operation 呈现操作 | 不按付款模型/字段名猜测，不改变 O2M/M2M 命令协议，不绕过 Schema |
| P4 | 在既有 `local.dev/sc_dev_demo` 生命周期内补受管 M2M 合成样本、一次保存、权威回读和复位 | 不创建数据库、端口、卷、凭据或通用 fixture 平台，不修改真实人员权限 |

Formal Product Layer：P1 + P0 + P4。Standard vs User-Specific：建设行业标准付款页面声明、平台通用契约/渲染能力与交付验证；没有 P2 客户特判或 P3 低代码布局覆盖。

## 用户可见结果

- 付款申请办理字段有唯一主编辑位置；追溯区只读呈现历史和执行事实，不再出现第二套结算来源编辑控件。
- 持久化 O2M 行的待保存删除、撤销删除和最终保存语义清楚；未保存新行取消时不生成数据库删除命令。
- M2M 附件显示“解除关联”。取消/放弃会恢复关系；保存只移除关联，附件对象本身仍存在。
- 原生 `delete="0"` 同时约束桌面行操作、批量入口和移动操作；允许的内联编辑仍可用。
- 收款申请正式入口不再因空字符串 presentation mode 在表单渲染前失败。

## 正式入口契约失败归因

正式路径为菜单 360“收款申请” → action 690“收款申请” → `payment.request` → 表单视图 1759。业务配置 209 为已发布的 `entry_semantic_surface`，并按 action 精确绑定。

| 跳点 | 修复前 | 修复后 |
| --- | --- | --- |
| 入口声明 | action 690 精确命中 `entry_semantic_surface`；没有要求全局 task 默认 | 不变 |
| 后端合成 | `_form_structure_governance` 选中 entry authority，却没有同步设置 `form_presentation_mode` | entry semantic 有有效 sections 时确定为 `task`；native/无匹配配置仍为 `workspace` |
| 最终响应 | `sourceAuthority.governance_source.formPresentationMode=""`，与结构自身推导的 task 不一致 | 统一通过 `form_structure_presentation_mode` 归一，治理来源和最终结构一致 |
| 前端校验 | 正确拒绝空字符串，因而在表单渲染前停止 | 继续只接受 `task | workspace`，合法值正常解码；未放宽校验 |

首次偏差位于 `addons/smart_core/handlers/ui_contract_v2.py::_form_structure_governance`，不是删除控件。修复没有按模型名推断，没有遍历父模型，也没有把未知入口默认为 task。

表单恢复后又暴露一个独立的通用保真缺口：原生树 `editable="bottom" create="false" delete="false"` 已进入 `tree.capabilities`，但 `subview.policies` 只消费了 delete，错误保留 `can_create=true`。解析器现将 `inline_edit/can_create/can_unlink` 分别与原生 `inline_edit/can_create/can_delete` 做 tighten-only 交集。

记录 10 的权威原生声明实际是：允许内联编辑、禁止新增、禁止删除。因此本批验证“编辑保留，新增和删除均不可用”；不会为了满足泛化描述而恢复源码明确禁止的新增。

## M2M 受管样本与真实协议

正式消费者选择 `payment.request.attachment_ids`：菜单 559 / action 809“付款申请”，字段类型 `many2many`，关联 `ir.attachment`，保存权威为 `payment.request.write`。样本沿用 `smart_construction_demo.payment_request_floorplan_demo_record` 的既有 reset 生命周期，只增加由同一 seed 明确拥有的合成附件 `smart_construction_demo.payment_request_floorplan_demo_attachment`。

本次旅程在记录 999 / 附件 16878 上运行：

- 1088×791 与 390×844 分别执行“解除关联 → 放弃”，两次均为零 write，关系恢复。
- 唯一一次真实保存对 `payment.request` 发出一笔 write，实际 `attachment_ids` 协议为 `[[3, 16878]]`；验证记录实际协议，不以该形状反推或修改产品实现。
- 权威回读：记录 999 的 `attachment_ids=[]`，附件 16878 仍存在且保持原 `res_model/res_id`。
- 受管 reset 后基线恢复为记录 1000 / 附件 16879，关系存在。前后完整候选指纹逐字节一致。

## 验证结果与证据

Changed paths 涉及 P1 付款视图、P0 契约/共享 relation renderer、P4 fixture 和验证入口。风险等级为中高，最早有效层为 L1；开发期只执行受影响的非零 L2/L4，完整 Quick 留在最终 clean HEAD。

| 层 | 结果 | 准确口径 |
| --- | --- | --- |
| L1 | `make ci.local.iteration` PASS | 16 tests；不生成 receipt |
| L2 P0 | ui contract presentation、native x2many capabilities、detail collection/adapter guards均非零通过 | 新增生命周期守卫实际执行 1 个方法；不是 3 次业务执行 |
| L2 P1/P4 | 付款最终视图方法、fixture ownership 三个方法及失败补项方法通过 | Odoo setup/teardown 计时行不算独立业务用例 |
| L3 | `smart_core` 受管增量升级、local.dev restart/health PASS | 仅既有 `sc-local-dev/sc_dev_demo/18081` |
| L4 付款/O2M | 621 字段归属、未保存新行取消、持久化删除/撤销/取消及 fixture 复位复用既有同实现证据 | 不重写 621，不重复保存旅程 |
| L4 delete=0 | 收款记录 10，1088×791/390×844，零写入 | 允许内联编辑；无新增/删除入口。旧摘要误取最后一个关系契约，不能作主契约 authority 证据 |
| L4 M2M | action 809/menu 559，记录 999；桌面/移动取消恢复及一次真实保存 PASS | 关系解除，对象保留，最终 reset；零浏览器错误 |

冻结准备首次生成复杂度报告后，单独运行 owning guard 准确发现 `ui_contract_v2.py` 为 4317 行、超过既有 4312 行责任预算，因此在 Quick 前停止。恢复没有抬高预算：删除 entry semantic 分支中与既有投影 helper 重复的赋值，并在返回结构处直接调用同一 `form_structure_presentation_mode`；文件回到 4312 行，guard、精确 presentation 方法（实际 1 个方法）及 L1 16 项均通过。一次错误的宿主包调用在测试收集期因缺少 Odoo 模块失败，实际执行 0 个方法，明确不计入覆盖。该等价职责收敛不改变 relation 命令、fixture、浏览器 DOM 或数据库输入，`ca5a2e0f…` 的 M2M L4 结果按确定性影响分析结转到最终候选。

证据位置：

- 付款字段归属：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/detail-trace-payment-621-20f61533/summary.json`。
- 未保存 O2M：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/detail-trace-unsaved-o2m-621-20f61533/summary.json`。
- 持久化 O2M：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/detail-trace-o2m-lifecycle-20f61533/introduce-summary.json` 与 `remove-summary.json`。
- delete=0：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/detail-trace-delete0-receive10-7f7b5af5/`；只复用截图、零写入和控件结果，不复用其错误选择的主契约摘要。
- M2M exact-head：`artifacts/playwright/local-dev-payment-attachment-m2m-journey/browser-summary.json`、`authoritative-after-save.json`、`authoritative-after-reset.json` 与前后 fingerprint。

## 风险、边界与回滚

- 未执行付款审批、付款登记、会计写入、全角色或生产数据旅程；未对记录 10 或 621 保存。
- M2M 唯一真实保存只作用于登记的 demo fixture，结束后已按初始化基线复位。
- action 690 的旧截图摘要存在关系契约误选，已明确降级，不用其 sourceAuthority 字段证明主表单契约。
- P4 旅程依赖 P0 契约与 relation semantics。回滚顺序为 P4 fixture/旅程 → P0 原生能力与命令表达 → P1 occurrence 调整；不要只撤一侧后继续交付。
- 当前无已知产品阻断。最终交付仍需生成证据预检、clean exact-head Quick 和最终身份复核。
