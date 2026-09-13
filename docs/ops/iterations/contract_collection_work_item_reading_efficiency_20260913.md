# 合同集合与工作事项阅读效率（2026-09-13）

## 目标与边界

- 唯一产品目标：收入合同主身份在集合正常阅读起点可见；“我的工作”在 1088 等中等宽度保持类型、标题、金额和主动作清楚。
- P1 范围：`smart_construction_core` 收入合同原生 tree 的既有字段顺序。
- P0 范围：共享工作事项卡片的通用响应式布局。
- 不做：模型事实、契约 schema、权限、路由、保存、审批、综合工作台、低代码及业务数据改动。

## 源配置 → 契约 → 渲染映射

| 页面 | 源配置 | 最终契约 | 渲染消费 | 首次偏差与归属 |
| --- | --- | --- | --- | --- |
| 收入合同集合 | `view_construction_contract_income_tree` 将 `subject` 放在状态、日期、归档、发包人、项目之后；action 同时声明 `tree_column=subject` 与 `presentation_mode=source_order` | `PageAssembler` 按 `columns_schema` 原顺序输出 `config.sheet.columns`，并保留 `subject` 的 220px 宽度 | `HierarchicalWorksheet` 直接消费 `sheet.columns`；1088 未横向滚动时标题位于可视区之后 | P1 源列表顺序首先偏离“主身份优先”；P0 未重排业务列 |
| 我的工作 | `PaymentRequestWorkItemService` 明确输出 `business_type`、`record.label`、money fact 和 contract-provided action tier | `ProductMyWorkWorkspace` 类型及 `productMyWorkPresentation` 保留上述身份、金额和动作层级 | `MyWorkApprovalWorkspace` 的旧四列主区会压缩类型；首轮中宽规则又把卡片正文改成单列并给操作栏 `width: 100%`，共享 Space 子项继承该宽度后逐项换行 | P0 通用工作事项布局首次改变可读性；无 P1 字段或契约缺口 |

## 实施步骤

1. P1：只将收入合同 `subject` 移到 tree 第一列，并增加最终 contract 列顺序断言。
2. P0：保持类型标签不可拆字、唯一主事实占满摘要槽；纠正中宽单列和操作栏全宽规则，按“类型/状态 → 标题/金额 → 展开/动作”组织三层，并让操作同行、窄屏自然换行；增加静态守卫。
3. L1：运行 `make ci.local.iteration`、收入合同 profile 非零定向测试、My Work 静态守卫和前端严格类型检查。
4. L3/L4：只有 P1 增量升级成功后，使用既有 `local.dev` 样本做 1088 定向页面检查；产品通过后才冻结并进入一次 Quick。

## 基线与既有证据

- 基线：`e9f78ff079817ebcd6154e77e872cefbaf62bf81`。
- 完整工作树指纹：`3aef44591a704d588fb9fb48f12a34d8d7fa5b37dcb3e2977281d64db931871c`（7424 paths）。
- 既有 1088 暗色证据 `07758bd7…` 显示收入合同未滚动时标题位于项目列之后；“我的工作”类型标签逐字竖排。自该证据到本基线，My Work 目标源码未变；收入合同链仅替换了树展开图标，不改变列顺序或宽度。该证据只用于复现与影响分析，不冒充当前候选验收。

## 风险与回滚

- 风险：P1 列顺序会影响收入合同所有标准部署；P0 中宽布局会影响所有正式 My Work 事项。
- 控制：不删字段、不改变值和动作；P1/P0 分开提交，定向反例覆盖共享表面。
- 回滚：先回退 P0 布局提交，再回退 P1 视图提交；不需要数据库数据回滚。

## 分层验证进度

| 层 | 入口 | 结果 |
| --- | --- | --- |
| L1 | `make ci.local.iteration` | PASS；16 tests |
| L1 | `make verify.frontend.my_work_approval.guard`、`make verify.frontend.typecheck.strict` | PASS |
| L2 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS=my_work_backend` | PASS；20 tests，既有 3 项审计模型跳过不属于本批失败 |
| L2/L3 | 合同 profile 首次运行后识别到安装视图仍为旧 XML；随后经显式声明的 `local.dev.upgrade` 增量升级 | 升级 PASS；`sc-local-dev/sc_dev_demo` 权威身份 PASS |
| L2 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS=contract_execution_component_profile` | 升级后 PASS；5 个测试方法，Odoo 统计 7 tests，零失败 |
| L2 | `make verify.frontend.hierarchical_worksheet.unit`、`make verify.frontend.state_dashboard.unit` | PASS；分别包含 18 个 Python tests + 15 个交互 cases，以及 24 个 Python tests + My Work 展示纯函数 cases |
| L4 | 首轮 1088 只读产品检查 | 部分通过；收入合同通过并冻结。My Work 虽消除了类型竖排，但折叠卡约 270px 高、动作逐行分离，产品复核未通过；该证据不再作为 My Work 验收结论 |
| L1 | My Work 密度纠正后的 `make ci.local.iteration`、专项守卫、严格类型检查 | PASS；迭代守卫 16 tests，专项守卫及类型检查通过；Quick 未重跑 |
| L4 | `ed36ba45…` My Work 有限补验 | PASS；1088×791 折叠态完整显示 2 张事项卡；1440×960 无大块空白；390×844 标题、金额和动作自然换行。1088/1440 使用键盘、390 使用触屏完成展开与收起，完整身份匹配，三组摘要均为零写入、零错误、零根页面横向溢出 |
| L5 准备 | `make ci.delivery.freeze.prepare` | PASS；1366 项测试清单、7 项组件清单测试、35 个必需适配点、1866 行表单拆分证据均为当前内容；生成差异只更新组件接管清单输入摘要 |

首次合同定向运行的失败归因为升级前安装视图过期；升级改变了该环境前提，之后同一目标通过，因此不是对未变化失败的重复重试。完整 Quick、fixture reset、release snapshot 和浏览器矩阵均未在开发期运行。

L4 启动前曾被 `/tmp/sc-local-dev-candidate-frontend.pid` 的旧身份阻断：它绑定已删除工作树 `/home/lidefend/workspace/sce-backend-odoo-batch2a-personnel-auth`、旧 HEAD `23225efbb8bf5bb8b0276af7ec016eb5e5614612` 和仍存活的 5176 静态服务。经单独授权后，清理前逐项核对 PID 文件权限、工作树路径、HEAD、进程命令、进程组和端口监听，仅终止该旧进程并删除对应 PID 文件；没有修改治理工具、其他前端、数据库、工作树或端口配置。

清理后，同一产品 HEAD `4c806807028b3276c470d634df277f02ece90cb5` 的受管候选前端启动成功。2026-09-13 22:08:00 +08:00 生成的摘要位于 `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-work-reading-efficiency-4c806807-dark-1088/summary.json`；桌面截图为 `desktop-my-work.png` 与 `desktop-income-contract-workspace.png`。人工复核确认收入合同未滚动时首列为“合同标题”，该部分冻结保留；My Work 截图则显示折叠卡约 270px 高，1088×791 首屏只能完整显示一条，因此产品结论被撤回。其原因是中宽规则把正文改为单列，并将共享 Space 操作栏设为全宽，使继承宽度的操作项各占一行。本批只解冻 My Work 的 P0 布局；旧 390 样本及旧 Quick receipt 均不冒充新布局证据。

P0 密度纠正候选 `ed36ba45d285f0bce77c2579c260dae6f5443d69`（完整指纹 `b7c0522328d18e6d98fce8c4735c62f78c0b8872043337b0957ed5b56e133473`，7427 paths）已完成有限补验。1088 折叠样本经人工复核通过；1440 浅色与 390 浅色实际截图确认阅读关系稳定。既有 `exerciseFactDisclosure` 在 1088/1440 以键盘 Enter 展开、Space 收起，在 390 以触屏展开/收起，并验证完整标题与折叠标题一致；所有摘要 `pass=true`、`mutationCount=0`。焦点环由公共 `ScButton` 的 `:focus-visible` 规则承接，未点击或触发“提交审批”。证据目录为：

- `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-work-reading-efficiency-ed36ba45-dark-1088-my-work`
- `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-work-reading-efficiency-ed36ba45-light-1440-390-expanded-check`
- `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-work-reading-efficiency-ed36ba45-dark-1088-390-expanded-check`

一次尝试将表单专用“批量展开后字段对齐截图”选项用于 My Work 时，载体在证据生成前退出；归因为验证工具适用范围错误，未形成可用证据，也未原样重试或修改 P4 工具。正式展开/收起结论只采用上述既有 My Work disclosure 能力。下一步只做生成证据预检、文档提交、最终 HEAD 一次 Quick 与同头独立复核；合同旅程、保存链、fixture 和业务写入继续不运行。
