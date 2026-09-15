# 投标中标事实确认与合同承接解耦（2026-09-15）

## 交付摘要

本批从 `main@0eb4776391a31779898d4d17f0317e132b6c4f7a` 开始，在唯一写入分支 `codex/tender-award-fact-confirmation-v1` 上完成“确认中标事实、独立办理合同”的第一批。正式投标入口不再在“确认中标”时静默选择报价金额并创建合同；用户明确选择当前投标的中标开标记录，登记资料依据与税口径后，系统冻结正式中标金额、币种、确认人和确认时间。合同仍由后续独立办理入口按既有合法计价机制承接，本批不建设合同生成动作。

产品页面样板源候选为 `2e5a04195e740a0c22b94dfdcf3db48e41babbdb`；运行闭环使用的产品候选为 `63fd6df8a96721438691bc54600805da03f1c218`，在样板之上只增加通用关系 domain 保真和 `reload` 入口身份修复。受管工具候选为 `945f0b27463181825ebc94ad79f7a6602338bf13`。最终交付 HEAD 在冻结前文档与生成证据提交后另行记录，不用目录短 SHA 冒充最终身份。

## 产品与架构边界

| 层级 | 所有权与修改 | 明确未做 |
| --- | --- | --- |
| P1 行业标准 | `smart_construction_core` 定义中标事实字段、确认约束、正式入口章节与动作；中标记录必须显式属于当前投标且结果为中标 | 不默认税率，不强制投标报价、清单合计与中标金额相等，不创建合同，不修改合同计算 |
| P0 平台内核 | 前端通用关系选择保留原生 occurrence domain，支持父记录 `id` 与安全字面量；`smart_core` 对普通 client reload 保持当前入口 | 不按投标模型或字段名推断，不放宽 action/menu 权威，不建立投标专属渲染器 |
| P4 交付工具 | 复用 `sc-local-dev/sc_dev_demo`，提供批次归属、准备、检查、浏览器旅程和清理；产品候选与工具候选分别绑定 | 不创建 Compose、数据库、端口、卷或凭据；不写真实投标记录 |

Formal Product Layer：P1 + P0 + P4。Standard vs User-Specific：建设行业标准中标事实、平台通用契约保真和受管开发验收，没有 P2 客户特判或 P3 运行时布局配置。

## 用户可见结果

- 正式投标表单保留“基本资料 → 中标事实确认 → 清单明细 → 协作记录 → 历史审计”的完整办理结构；新增章节不会吞掉原有章节或恢复被隐藏的 notebook 页签。
- “中标事实确认”集中显示本次采用的开标记录、资料类型、资料引用/附件、税口径、确认状态以及确认后的金额、币种、确认人和时间；桌面与移动点击定位不受吸顶区域遮挡。
- 只有属于当前投标且结果为中标的开标记录可被选择，不取第一条或最新一条猜测。
- 税口径允许明确登记为含税、未税或未知；未知不会阻止事实确认，也不会触发静默税额计算。
- 确认动作只冻结来源事实，不创建合同。历史已中标但缺少快照的记录显示“来源待核实”，不自动回填。
- 快照确认后，来源开标记录变化不能静默改写正式中标金额；重复请求要么幂等返回，要么因动作已退出当前契约而明确拒绝，均不得改变确认时间或创建合同。

## 金额事实与承接边界

| 事实 | 本批定义 | 样本值 |
| --- | --- | --- |
| 投标报价 `bid_amount` | 对外投标报价事实 | 1200 |
| 清单合计 `amount_total` | 投标清单计算结果 | 1000 |
| 正式中标金额 `award_amount` | 所选中标开标记录在确认时形成的不可静默改写快照 | 900 |
| 合同金额 | 后续合同按自身合法计价机制产生的结果 | 本批不创建合同 |

三项数值允许不同；系统不再使用 `bid_amount or amount_total or 0` 代替中标业务决定。正式中标资料引用、确认人、确认时间、币种和税口径与金额一并形成来源快照。没有资料引用时阻止确认；税口径未知时允许确认事实，但不能据此生成税额。

## 源视图、契约与渲染修复

1. P1 原生视图声明独立 `sc_tender_award_confirmation` 章节及锚点，最终合成结构继续保留基本资料、清单、协作与审计；清单空态和有数据态均跨满业务区域。
2. 关系字段 occurrence 已有 domain `[('bid_id', '=', id), ('result', '=', 'won')]`，但模型级空 domain 一度覆盖该声明。P0 改为 occurrence 声明优先，并在通用解析器中把保留字 `id` 绑定当前父记录，同时保留安全字面量条件。
3. `action_mark_won` 返回普通 `ir.actions.client/reload`。后端曾为其推断不完整入口，导致刷新丢失 `menu_id`；现在普通 reload 保持当前入口，不制造新的导航权威。

## 受管真实闭环

最终成功批次为 `award-20260915h`，使用正式入口 `menu=387/action=594/model=tender.bid`、`sc_test_admin`、`sc-local-dev/sc_dev_demo`。浏览器产品代码绑定 `63fd6df8a96721438691bc54600805da03f1c218`，P4 工具绑定 `945f0b27463181825ebc94ad79f7a6602338bf13`。

| 阶段 | 权威结果 |
| --- | --- |
| 准备 | 投标 105、清单行 40、开标记录 87；1200/1000/900；状态 waiting；合同为空 |
| 确认 | 状态 won；正式中标金额 900 CNY；税口径 unknown；资料引用 `最终报价文件-CODEX-P4-001`；确认人 51；确认时间 `2026-09-15 05:10:03` |
| 重复请求 | HTTP 403 `ACTION_CONTRACT_NOT_AUTHORIZED`，因为确认动作已退出当前 action contract；回读确认时间和 900 快照均不变，合同仍为空 |
| 刷新 | 已确认状态、900、确认人、确认时间只读可见；四个确认输入无可编辑控件，确认动作不可执行 |
| 清理 | 受管投标 105、清单行 40、开标记录 87 及批次 XMLID 删除；复用项目、往来单位不变；最终检查 `existing_batch=false` |

成功证据位于：

- `artifacts/p4-tender-award/award-20260915h-945f0b27/browser/summary.json`
- `artifacts/p4-tender-award/award-20260915h-945f0b27/fixture-post-inspect.json`
- `artifacts/p4-tender-award/award-20260915h-945f0b27/fixture-cleanup.json`
- `artifacts/p4-tender-award/award-20260915h-945f0b27/fixture-final-inspect.json`

前序批次只用于定位 P4 工具或运行装载问题：关系 domain 丢失、操作人不具菜单权限、请求权威层级判断错误、重复请求被契约拒绝、后端进程未重载以及刷新取证竞态。每次失败均在首次偏差修正后使用新批次；已确认且未生成合同的诊断对象先权威回读，再由批次清理入口删除。它们不计为通过旅程。

## 验证分层

Changed paths 涉及 P1 投标模型/视图/契约，P0 通用前端关系契约与后端 reload，P4 受管 fixture/浏览器/Make 文档。风险等级为高：新增业务事实写入与动作行为变化。最早有效层为 L1，随后完成非零 L2、受管 L3 与聚焦 L4；完整 Quick 仅在最终 clean delivery HEAD 运行一次。

| 层 | 结果与口径 |
| --- | --- |
| L1 | `make ci.local.iteration`：16 tests，PASS；`make verify.local.dev.tender_award.unit`：7 个方法，PASS；均不作为 Quick receipt |
| L2 P1 | `test_tender_award_fact.py` 覆盖 9 个方法：明确中标记录、归属/结果拒绝、防重与快照不可变、资料引用、未知税口径、历史不回填、禁止直接改状态、原生章节与正式契约动作 |
| L2 P0 | relation-domain 定向矩阵覆盖父记录 id、安全字面量、unsupported fail-closed 与 occurrence 优先；navigation entry target 12 个纯测试覆盖普通 reload 不推断入口 |
| L3 | `smart_core` 受管增量升级与 `local.dev` authority PASS；随后受管 restart 让常驻后端加载当前 Python 代码 |
| L4 页面 | `artifacts/playwright/tender-award-fact-2e5a0419-structure-recovery/summary.json`：桌面/移动、记录 1/2，`pass=true`、`mutationCount=0`、零错误；产品人工复核确认完整章节、定位与清单全宽 |
| L4 写入 | `make verify.local.dev.tender_award.journey PRODUCT_CANDIDATE_SHA=63fd6df8… P4_TENDER_AWARD_BATCH=award-20260915h`：PASS，3 个受控请求事件，最终清理并回读不存在 |

后端测试数量以实际方法数描述，不把 Odoo setup/teardown 统计行冒充独立业务用例。页面 DOM 与键盘/鼠标检查不等于完整读屏器体验。最终 Quick receipt、完整 HEAD/Tree/指纹和独立复核由冻结候选的仓外证据记录，避免为回填结果再次改变候选。

## 交付边界与后续事项

- 未执行合同生成第二批；没有改变合同明细、合同金额计算、审批、付款、开票或权限体系。
- 未将未知税口径推断为含税/未税，也未批量回填历史中标记录。
- 开标记录附件沿用既有授权能力；没有新建上传协议。
- 本批真实写入仅作用于受管开发 fixture，已精确删除；不代表生产环境写入验收。
- 项目看板、89 个入口审计和合同独立承接是分别治理的后续工作，不并入本 PR。

## 回滚边界

P4 工具依赖 P0 正确传递关系 domain 与 reload 身份，P0 又服务 P1 正式入口；如需回滚，应按 `P4 旅程与 Make 入口 → P0 关系/导航通用修复 → P1 中标事实与视图` 的逆序执行。P1 回滚前必须确认没有下游消费者依赖已确认快照；本批不包含历史数据迁移脚本。
