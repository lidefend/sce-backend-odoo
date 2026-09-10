# Draft PR：收口共享表单结构、响应式表达与全局组件能力

## Summary

本 PR 完成共享表单表达阶段：统一查看态/录入态结构、章节导航、响应式容器、字段网格、明细与协作层次，并通过 TDesign 1.20.5 公开 ConfigProvider 收口主题与减少动画的应用级生命周期。

范围只包含通用前端产品、对应验证工具、生成清单和治理文档；不包含业务契约、权限、业务动作、数据库/fixture、acceptance 环境恢复、发布工具或官方图标资源。

## User-visible improvements

- 表单页头集中身份、状态和操作，正文、关系明细、辅助信息、协作记录形成清晰层次。
- 材料入库默认首屏可到达明细；合同桌面明细可横向比较，移动端保留有标题卡片。
- 320/390 宽度下正文、字段、真实控件和章节栏完整收缩；仅声明的明细表格允许横向浏览。
- 章节入口名称与实际内容一致，多关系集合不串位，隐藏章节策略不变。
- 文本、关系、日期、金额和多行控件共享列线、外框和行基线；查看态与录入态均保持一致。
- 页头、正文、明细和协作区的背景、边界及间距各有唯一责任组件，减少重复套框和深层样式补丁。
- 登录、业务和嵌入页面共享根级主题能力，系统主题与减少动画变化可以动态恢复。

## Architecture and ownership

- Formal Product Layer：P0 通用前端机制；P4 仅承载验证、生成清单和交付文档。
- Layer Target：`frontend/apps/web` form renderer、page header/pattern、design-system bridge、theme runtime；`frontend/packages/ui` 公共 primitive 出口。
- 启动链仍为 `login → system.init → ui.contract`；未修改 contract/schema、public intent、default route、权限或业务写语义。
- 章节身份、顺序与显隐沿用既有契约配置，本专题不新增配置入口。共享几何只负责对齐、收缩和阅读宽度，不替代契约内容。
- Dialog/Drawer 的嵌套关闭、焦点和滚动保护继续由共享生命周期接管；Select 请求竞态继续由关系消费者处理；DatePicker 使用官方行为；Table 只保留必要的横向浏览边界接管。

## Complete diff identity

- Base branch：`main`
- Audited base/merge-base：`3c3c7bdef2dac3dfdfa06488c7e731ce1e565ce9`
- Independently reviewed product/evidence candidate：`c442f731adb6cd23e3adc77811c1c895f137a5fe`
- Delivery-preparation HEAD：`fc7433b6284d539d9486a551ca635771f00071af`
- Exact PR head：在 push/create 前从 clean worktree 重新读取，不在本草稿预填。

交付整理前完整差异为 73 commits / 72 paths；分类为 36 个产品前端、18 个验证工具、5 个生成清单、13 个治理文档，0 个未分类路径。本交付提交纳入后为 74 commits / 74 paths，其中治理文档增至 15；push/create 前必须重新核对。

## Verification

Local evidence already completed:

- `make verify.frontend.quick.gate`：PASS，包含严格类型、production build、官方组件守卫及非零定向测试。
- 真实公开 ConfigProvider：31 项测试 PASS；普通、异步、Teleport 消费者完成 normal→reduce→normal，局部配置保持。
- 原联合页面矩阵：候选 `07758bd7`，light 1440/390 + dark 1088/320，36 samples PASS，mutation/errors/failures 0。
- 补证矩阵：候选 `c442f731`，system 1088/320，8 samples PASS，mutation/errors/failures 0。
- 独立复核：源码与留存证据 PASS；复核者未重新启动浏览器或重跑测试。

这两组浏览器结果分别登记，不能合称“最终候选 44 个样本全部重跑”。完整证据索引见 `docs/ops/iterations/frontend_form_expression_stage_delivery_package_20260910.md`。

## Diagnostics retained

- 材料关系空结果：实际 `api.data/list` 请求使用权威 domain `[(id, =, -1)]`，HTTP 200、0 records、无 error；分类为数据前提不足，不是组件故障。
- 材料集合查询：旧脚本误把语义容器身份歧义当作控件缺失；改为绑定唯一可见 search input 后，桌面/移动查询与清除恢复通过。
- 合同层级查询：实现是当前工作区内的客户端 `visibleRows` 过滤；旧脚本使用全局等待选择器。绑定当前工作区根后，桌面/移动的 1→0→1 记录循环通过。

## PR/CI state

- 当前没有远端分支对应 PR；`make pr.status` 显示无关联 PR。
- 风险分类：`HIGH_RISK`，`frontend_mode=full`、`professional_mode=full`，并按 fail-closed 报告 `backend_changed=true`；不得手工降级。
- Required exact-head checks：`public_guard`、`professional_quality_gate`、`frontend_release_gate`、`merge_policy_gate`。
- 上述 CI 当前均为 `not_run`；本草稿不预填通过。
- `release_candidate_gate` 未运行且不属于本次 draft PR 创建条件。

## Not included

- 不新增或调整契约、字段、权限、业务动作、金额口径或隐藏章节。
- 不覆盖多角色、真实保存/审批、非空材料关系选择、acceptance、历史升级兼容或发布验收。
- 不重建 acceptance，不运行 fixture，不操作数据库，不推送 Gitee。
- 官方图标资源采用作为后续独立批次处理。

## Risk and rollback

- 完整差异有 73+ commits，应按产品前端、验证工具、生成清单、治理文档四组审查，不能只看最后四项补证。
- 产品整体可以回退到共同基线 `3c3c7bde…`；细分阶段可以按结构→层级→响应式→导航→对齐→全局能力的逆序提交边界回退。
- 文档交付包可独立回退，不涉及数据库、契约或环境恢复。

## Delivery status

`READY_FOR_DRAFT_PR_AUTHORIZATION`。这不等于 merge-ready 或 release-ready；push、create、ready、merge 和 release 分别处理。
