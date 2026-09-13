# 合同办理页面信息组织收口（2026-09-14）

English: [contract_handling_page_normalization_20260914.en.md](contract_handling_page_normalization_20260914.en.md)

## 目标与边界

- 唯一产品结果：收入、支出合同正式办理入口能够清楚识别合同、核对基本事实、维护明细，并把说明、附件、履约和追溯信息放在明确层次中。
- 基线：`origin/main@731c7e6d43f64e4f8e764c67880be6943afcee15`；分支：`codex/contract-handling-page-normalization-v1`。
- P1：`smart_construction_core` 提供显式包装入口映射、行业表单章节、字段顺序、可见/只读策略与标签。
- P0：`smart_core` 只做通用显式映射解析和原生约束传递；前端只做通用显式章节保留及“无可呈现内容则不生成导航”。
- P4：定向测试、浏览器证据、交付文档与最终门禁。
- 排除：合同列表、合同变更、结算、付款、保存、审批、权限、金额计算、附件授权扩展、fixture、业务数据修改、综合工作台和低代码。

## 源视图 → 最终契约 → 页面表现 → 首次偏差层

| 正式入口 | 源声明与身份 | 最终契约 | 页面表现 | 首次偏差与修复归属 |
| --- | --- | --- | --- | --- |
| 收入合同 | menu `660`、action `609`、包装模型 `construction.contract.income`；P1 显式绑定 `contract.income` 到底层策略模型 `construction.contract`；原生 form 提供带 `data-sc-anchor` 的业务章节 | `PageAssembler` 先保留直接模型命中；直接未命中时只消费精确 `entry_model + category_code + policy_target_model` 映射，唯一命中才应用。V2 保留策略声明的 create 隐藏和其他模式只读；合同方向类型在 create/edit 可写、readonly 只读 | 身份与基本资料 → 合同范围 → 合同明细与金额 → 说明与附件；查看态另有默认折叠的履约和来源追溯 | 包装模型以前无法取得底层分类策略是 P0 解析能力缺口，权威别名由 P1 提供；明确章节曾被 task floorplan 重新分类是 P0 消费偏差；收入字段分区、列序及合同方向类型策略属于 P1 |
| 支出合同 | menu `661`、action `610`、包装模型 `construction.contract.expense`；P1 显式绑定 `contract.expense`，不复用收入映射 | 同一通用解析器命中支出策略；缺失或多义映射失败关闭。章节身份、profile 可见性、只读及 subordinate 导航角色进入最终契约 | 身份与基本资料先显示供应商/分包方、项目、日期和责任人；支出分类/范围独立；明细金额在说明附件前；履约、来源追溯默认折叠；历史付款承接保留内容但不占主导航 | 支出分区、标签、明细列序和历史付款角色为 P1；空 profile 章节形成死导航为 P0 通用内容判定缺口 |
| 直接模型入口反例 | action 模型与 `sc.business.category.target_model` 直接一致 | 继续优先直接查找，不调用别名猜测 | 原有入口行为不变 | P0 回归保护 |
| 无关联/多义反例 | P1 未声明或声明多个不同目标 | 返回无策略，不选第一个，不遍历父模型，不按模型名后缀猜测 | 不静默串用收入或支出策略 | P0 失败关闭 |

## 页面组织结果

- 页头继续消费既有模式、状态和动作能力；新建态隐藏平台状态，查看/编辑态只读约束不改变状态值或流转。
- 收入、支出均按“身份与基本资料 → 合同范围 → 合同明细与金额 → 说明与附件”组织；履约与来源追溯与合同维护区分。
- 收入原生表单已有的“合同方向类型”恢复到合同范围；新建/编辑可维护、查看只读，不改变字段值或关系模型。
- 明细列以清单名称、计量单位、数量、单价、金额为先，来源中标清单和辅助编码后置；不拼造空名称。
- 普通无锚点布局组仍不显示标题；只有显式业务章节成为主导航。profile 隐藏全部内容时不留死链接，部分字段仍可见或默认折叠但有内容时仍保留导航。
- 历史付款承接保持只读、默认折叠和可访问，但由 P1 声明为 subordinate，不与当前合同办理章节并列。

## 金额与附件待决边界

| 事实 | 当前权威定义与消费者 | 本批结论 |
| --- | --- | --- |
| `amount_untaxed` | 底层合同按 `line_amount_total` 计算的不含税金额；`amount_tax` 按未含税百分比税率计算，`amount_total` 为含税金额；表单、最终合同价及下游履约计算继续消费 | 保留字段、标签和计算，不选择新的主金额 |
| `visible_contract_amount` | `contract_business.py` 定义为 `amount_untaxed` 的 stored compute/inverse 投影，帮助文本为“标准产品合同金额口径”；应收及正式支出展示投影也消费该值 | 与 `amount_untaxed` 同区展示，不因名称相近擅自合并或突出 |
| `attachment_text` | 历史/平台文本载体；收入只保留一次“历史附件文本”，支出保留一次“平台附件文本” | 不迁移、不替换为文件关系 |
| `attachment_ids` | 底层合同已有 `ir.attachment` 多对多；支出原生 form 已有正式字段和 widget，收入原生 form 未证明同等入口授权 | 支出消费既有入口；收入不新增上传入口；正式授权统一另行决策 |

## 验证与证据

| 层 | 入口或证据 | 结果 |
| --- | --- | --- |
| L1 | `make ci.local.iteration` | PASS，16 tests |
| L1/L2 | `make verify.frontend.native_section_navigation.unit` | PASS，包含全隐藏、部分隐藏、默认折叠有内容及 subordinate 反例 |
| L2 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS=contract_handling_page_policy` | PASS，7 methods / Odoo 统计 9 tests；覆盖收入/支出命中、交叉/缺失反例、章节、标签与状态 |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core`；`make local.dev.health` | PASS，复用 `sc-local-dev` / `sc_dev_demo` / 18081，不创建新环境或数据 |
| L4 浅色 | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-handling-expense-candidate-359c1ff9/` | 支出新建/查看/已有草稿编辑及收入新建，覆盖既定 1440/1088×791/390 样本；摘要均 pass、零写入。该目录不包含收入查看态，不以旧证据冒充当前候选覆盖 |
| L4 章节 | 同目录 `section-probe/report.json` | 1088/390 的点击、手动滚动、键盘展开/收起、焦点保留和自然增高通过 |
| L4 深色 | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-handling-final-preflight-359c1ff9/dark-structure-1088-390-v2/summary.json` | 1088×791、390×844 支出新建/查看逐章节定位、中/底部、导航和响应式边界通过；`mutationCount=0`、无错误 |
| L4 只读协作反例 | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-handling-readonly-collaboration-c41ece4a/` | 修复候选 `c41ece4a…` 的收入/支出查看态在 1088×791、390×844 深色样本中均不暴露记录沟通、备注、计划或上传入口；只读历史仍可见；摘要 pass、零写入，完整指纹另存同目录 |
| L4 收入合同方向类型 | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-handling-income-direction-309f1b1e-refreshed/summary.json` | 候选 `309f1b1e…` 在受管运行时刷新后，1088×791、390×844 浅色收入新建均渲染 `contract_type_id`，状态为可见且可编辑；章节旅程通过，`mutationCount=0`、无错误 |
| L5 | `make ci.delivery.freeze.prepare`、最终一次 `make ci.local.quick`、独立复核 | 最终冻结后由仓外 exact-head receipt 和复核报告记录；本文之后不再通过 tracked 总结改变候选 |

一次附加深色手动定位参数在 runner 的可选等待处超时，归类为 `validation_tool_defect`。移除冗余参数后，受管 runner 自带的逐章节点击和稳定态检查通过；没有原样重试失败输入，也没有修改产品或验证工具。

## 已知边界、风险与回滚

- 查看记录的两条合同明细中清单名称、计量单位为源数据空值；本批不造名称、不修记录，非空业务身份显示仍未覆盖。
- 收入草稿编辑态不可用，未以已生效记录 `/f` 冒充；支出只读使用现有生效记录，编辑使用现有草稿且未保存。
- 收入合同方向类型只补验了新建态；编辑态仍受“无可用收入草稿”边界约束，查看态只读由非零契约测试覆盖。
- `359c1ff9` 浅色目录不包含收入查看态；若需要证明后续 P0 只读边界，使用与修复候选绑定的聚焦只读证据，不做整页矩阵结转。
- 未验收真实保存、审批、全角色、合同变更、结算、付款、正式附件授权或金额口径决策。
- P0 风险限定为显式分类映射、原生隐藏约束和章节导航；测试证明策略不串用、缺失/歧义失败关闭、有效章节不被误删，生产 P0 无合同模型特判。
- 回滚顺序：先回退 P0 前端章节消费，再回退 P0 契约映射/隐藏传递，最后回退 P1 支出与收入视图/策略提交；不需要数据库数据回滚。

## 下一步

- 冻结后仅执行一次 Quick、同一 exact-head 独立复核和受管远端交付；候选变化或新增阻断则停止，不用旧 receipt 冒充。
- 金额主口径、收入正式附件入口和非空明细样本作为独立决策/数据前提，不扩展本专题。
