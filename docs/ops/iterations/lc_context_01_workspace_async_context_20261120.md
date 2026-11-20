# LC-CONTEXT-01：低代码工作台读取上下文与安全续办

Base/main: `d10d2b42d747c89be39abb89dac25bd6051812eb`

Branch: `feature/lc-context-01-workspace-async-context-20261120`

## 产品结果

用户切换公司、角色或业务页面后，低代码工作台只能展示、编辑和提交当前配置对象的内容。旧请求不得重新打开编辑器、改变编辑基线、覆盖错误或 loading，也不得继续基于旧内容发起后续写入。

## 层级与作用域

| 项目 | 声明 |
| --- | --- |
| Formal Product Layer | P0/P4 |
| Layer Target | 通用低代码工作台前端读取归属；受影响行为测试与增量选择 |
| Module | `frontend/apps/web`、`scripts/verify`、`make/runtime_ops.mk` |
| Standard vs User-Specific | 平台通用机制 |
| Why Here | 异步污染发生在共享前端消费层；后端已经拥有公司、页面和目标角色裁决 |
| Why Not Elsewhere | 不在后端复制前端请求序号，不用后端补偿掩盖晚到响应，不改审批业务语义 |
| Blast Radius | 目录扫描、列表/分析读取、版本读取与恢复、审批读取与多步保存、上下文切换清理 |

## 验证边界

本轮只执行前端消费、纯契约和增量选择测试。ORM、模块基线、模块升级、fixture、浏览器矩阵、部署和 `verify.business_config.full_acceptance` 不在本轮范围。

## 执行记录

- Owner preparation: branch and run registered on main `d10d2b42d`; prior post-merge bookkeeping commit `f7919c689` is carried by the branch history and will ride this product candidate.

## 实现结果

- 新增通用 `contextRequestOwner`，以全局 `contextEpoch`、公司、认证角色、目标配置角色、model/action/view/viewType 和读取族序号判定请求归属。
- 三类目录扫描共享一个请求族，旧响应不再修改 `coverageScan`、当前行、错误或 loading。
- 列表/搜索与分析读取分别绑定请求族；旧响应不得改写字段、编辑基线、面板或焦点，未完成有效读取时禁止暂存旧内容。
- 版本读取和回滚确认均绑定原配置对象；确认期间对象变化时不会向新对象发送恢复请求。
- 审批读取与多步保存绑定父页面、目标模型和当前上下文；第一步等待期间切换上下文时不会继续第二步。
- 公司、角色或页面变化后，旧 `catch`/`finally` 不再覆盖新错误或新 loading；组件销毁也会使请求失效。
- 列表与分析编辑提示统一为“保存到待发布变更；草稿预览用于核对效果；统一发布后正式页面生效”。
- 审批成功读取保存独立 read ticket；`approvalEditorReady`、保存入口和确认后的续办均验证同一 ticket，旧草稿不能在新 epoch 下重新绑定。
- 列表/搜索、分析与审批共享一个 `editor-open` 顺序；审计、编辑基线、面板与焦点只在当前响应仍是最后一次打开意图时安装。
- 审批保存开始后，业务读取 ticket 与保存 ticket 决定两项写入和回读是否继续；`editor-open` 只控制呈现。用户切到列表或分析不会跳过第二步审批步骤写入，也不会让旧保存抢回面板或显示旧成功提示。

## 增量与验证接线

- `frontend_dev_incremental` 将本轮工作台读取路径精确映射到 `verify.business_config.unit`，审批编辑器映射到 `verify.business_config.approval_targets.unit`。
- 两个目标接入具备锁定 Node/pnpm 依赖的 `verify.frontend.pr.unit` 与 `verify.frontend.release.unit`，没有放入无 `node_modules` 的 `contract_only_checks`。
- 验证面基线通过专用入口重写；6 个新增远端工具脚本已登记，审批目标陈旧处置已移除，未登记、陈旧和缺失项均为 0。

## 验证结果

- `business_config_context_race`：12 组受控异步场景通过，覆盖共享 busy 归属、A/B 目录竞态、A→B→A、同对象双请求、旧失败、列表/分析与审批两个方向的跨面板旧回包、新面板未保存修改、无效读取暂存、版本确认切换、有效版本标签与稳定暂存。
- 审批目标：后端 26+8 项及前端 17 个案例通过；包含读取后 epoch 变化禁止保存、确认前绑定后上下文变化禁止续办、旧审批回包不抢回面板、稳定保存正例，以及第一步写入期间打开列表或分析仍完成原保存。
- `verify.frontend.pr.unit`：完整标准前端聚合入口通过，实际包含两个 business-config 行为目标。
- `make ci.local.iteration`：12 个受影响目标通过；最终修订实际重跑 6 个变化输入并复用 6 个未变通过目标。无 ORM、浏览器或 full acceptance 目标。
- `ci.delivery.freeze.prepare`：通过，生成证据与源码输入一致。

ORM、模块基线、模块升级、fixture、浏览器矩阵、部署和 `verify.business_config.full_acceptance` 未执行。

## 主线集成

- PR：#947
- 候选 HEAD：`8b4a0039b38c6fb9913448bd896a571b1bd4013a`
- Base：`d10d2b42d747c89be39abb89dac25bd6051812eb`
- Squash 合并提交 / 当前 main：`80f98fa25deea70f658ffecd93b0668103928c85`
- 候选树：`4f27a5a434beba68c0e236839251c4f84d91a60c`
- 合并树：`4f27a5a434beba68c0e236839251c4f84d91a60c`

四项必需检查均在候选 HEAD 上成功，候选与主线源码树一致。本批次与主线集成为完成状态；版本发布和产品交付验收未执行。
