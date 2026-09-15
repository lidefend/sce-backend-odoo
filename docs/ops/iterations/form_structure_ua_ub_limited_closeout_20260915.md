# 唯一结构机制及首批代表面迁移

交付范围：U-A／U-B 有限收口。不是全系统统一完成。action 777 保持未通过的环境残项；U-C 本批不启动。

## 1. 候选与责任边界

- 统一基线：`9f7bb560917a98b638a6d2a516fe2542634fdff8`。
- 产品审查／最后页面候选：`967ff6f425436c5e8792fddbde0fc3a58060e30b`。
- 产品完整指纹：`9816cfadeac5fa870c0380f033c1155910671d3cd455f76e006ae3c745f116a8`，7461 路径。
- 本次收尾 Formal Product Layer：P4；Layer Target：交付证据、台账及既有 fixture 生命周期；Module：docs、contracts/generated、既有生成报告与受管证据工具。没有新增 P0/P1/P2/P3 产品修改。
- Why Here：归档验收结论、生成内容绑定证据和清理本批合成数据属于交付治理；不得在前端、行业模型或运行配置中补偿传输错误。
- Blast Radius：文档与派生报告；数据库只清理精确归属的本批合成投标及其两条子记录。不改页面、字段、存储、金额规则、权限、启动链或 public intent。
- 最终文档/生成证据提交的 HEAD 和完整指纹由 `artifacts/form-structure-unification/ua-ub-limited-closeout/` 的冻结记录与 exact-head Quick receipt 绑定。本文在最终提交前编制，不预先声称未来 Quick 成功。

## 2. 实际交付

### 唯一结构机制

`layoutContract.containerTree` 是正文结构和导航的同一载体。配置在 orchestration 边界选择一次，native 路径不由后续 handler、projection 或前端重新解释业务结构。`formStructureContract` 保留派生语义元数据；允许不冲突的语义增强，结构冲突定位到配置、入口和具体键/节点。

原生 invisible、readonly、required 及入口权限仍具有约束力。前端仅忠实消费结构，处理响应式、折叠、通用组件与反馈。已修复通用空集合标签列占宽、AutoComplete 事件桥接丢值；没有客户/项目模型 CSS 特判或权限放宽。

### 首批代表面

| 代表面 | 已核验结果 |
|---|---|
| 客户 56 | 基本资料、工商信息、联系方式、账户与财务明确分组；联系人和账户空集合全宽；导航定位正常。保留各字段权威和存储，不重跑创建/保存旅程。 |
| 付款 | 原生章节及语义增强分工明确，保留可选明细、金额绑定和共享入口的能力隔离；旧结构配置不参与正式付款样板。 |
| 投标 149 | 五个一级业务章节；购买/踏勘/审查/开标/保证金归入过程区，附件及备注归入资料区；内部组 subordinate；开标结果中文标签。正文与导航同树，既有中标快照、选择/确认/回读/防重证据保留。 |
| 项目看板 | 保持只读；861 编辑入口保持可编辑；空集合全宽。 |

用户已实际桌面复核客户与投标；本轮投标五章节、过程导航、中文列名、清单/开标/协作内容通过，未修改数据或执行确认。移动端复用既有 390 证据。本次没有重新跑七场景矩阵。

投标原始 runner 预期漏列既存“历史审计”，原 summary 为 failed 并保留。独立审查从源码提取完整 4279 字符布尔表达式，对原始 1088/390 观测离线复算，原预期 false、仅补审计项后 true；未删减其他断言、未重跑浏览器。

## 3. 独立交付审查与 action 777 裁决

独立审查者 `/root/frozen_review` 在上述产品 HEAD/指纹上检查完整基线差异和现有证据，没有修改代码、数据库、远端或重复运行测试。结论：**无可行动 S0–S2 代码阻断，允许进入有限收口**。

审查确认：

- Presenter 从 containerTree 生成正文；native floorplan 保留原树，navigation 只收 primary。
- 投标 8 个内部组显式 subordinate，不升一级导航。
- 原生权限不放宽；全 tender_views.xml 的 220 处字段/按钮属性多重集保持，唯一批准差异为 result.string。主投标 form 单独统计为 83 处。
- 旧配置结构在首批迁移面退出，保留非结构语义与有台账的兼容路径。

**action 777：environment_blocked，不阻断本次有限代码交付，仍阻断“该入口完整通过”的声明。**

理由：主契约实际 HTTP 200，绑定 action 777 / view 1530 / container_tree_authority，兼容依赖为空；清单、开标、协作三项后续请求在 UTC 11:04:47.030—11:04:47.066 报 ERR_NETWORK_CHANGED，无 HTTP 响应或响应 trace，不能据此认定后端根因或权限问题。同模型同 view 1530 的 action 594 当前双视口完整结构/导航/开标加载证据，以及既有中标事实与事件桥接定向证据，支持共享结构代码交付；不替代 777 的独立完整读取验收。

Quick 即使通过，也不改变上述未通过状态和裁决。环境定位另行处理；本批不重试相同探针、不停启历史容器、不绕过产品规则。

## 4. 六项身份与兼容台账

| 入口 | action / menu | actual view | 状态与来源 |
|---|---|---|---|
| 收入合同 | 609 / 660 | 1569 | 正式创建态通过，category 8 / contract.income，仍兼容 |
| 支出合同 | 610 / 661 | 1570 | 正式创建态通过，category 10 / contract.expense，仍兼容 |
| 收入结算 | 781 / 664 | 1764 | 正式创建态通过，category 12 / settlement.income，仍兼容 |
| 支出结算 | 782 / 665 | 1764 | 正式创建态通过，category 13 / settlement.expense，仍兼容 |
| 表单配置 | 737 / 431 | 不适用原生 form ID | 专用 /admin/business-config 工作台通过，响应 view_id=0 原样保留 |
| 数据权限 | 886 / 709 | 1904 | 现有记录 445 编辑态通过；create=false，business_config_sections，兼容单列 |

四项合同/结算来源是 sc.business.category.form_policy_json；实际 view 来自运行契约中的原生设置动作目标，不以默认值补齐丢失的 category provenance。

原口径 **49→46，减少3**；四项漏计单独校正为 **53→50**。独立集合差分复核成立。计数严格限定管理员/公司1/model-create；数据权限编辑态等其他状态覆盖单列，不能推出全角色/公司/状态已迁移。

[50 个明确消费者和 U-C 优先组](form_structure_compatibility_consumers_v1.json) 保留46项旧证据与4项本次核验的来源，不重扫89项。某条兼容重组路径的正式消费者清零且其他状态覆盖完成后，删除对应逻辑和测试豁免；现在不满足退役条件。

## 5. Fixture 收尾与运行证据承接

运行使用既有 sc-local-dev / sc_dev_demo / ^sc_dev_demo$ / sc_local_dev_odoo_data，前端5176→后端18081，凭据经受管入口解析，未新建环境。

用户批准按既有生命周期收尾。受管 `local.dev.tender_award_fixture` 对 namespace codex_p4_tender_award、batch ub-structure-20260915 先 inspect，确认 bid149/line47/opening119 精确归属，900/CNY/confirmed且 contract_id=null；随后 cleanup 返回 deleted=true、clean=true，最后 inspect 返回 existing_batch=false。

**记录149及其两条子记录现已清理，不再作为在线复核地址。** 已确认事实、网络失败现场、截图和 trace 以归档证据保留，不反向改写确认事实；客户/付款/项目既有记录与历史环境未清理。今后如需业务 fixture，应重新走已登记生命周期，不能假设旧ID可复用。

客户宽度、中标确认与既有移动证据绑定产品候选/前后端模块/数据库身份。最终提交只加入文档及生成证据；通过源码树与完整指纹差异证明承接，不能仅按端口识别版本，也不把旧浏览器缓存当新候选。

## 6. 门禁、证据与回滚

- L0：审查前产品 HEAD/完整指纹已独立重算；最终冻结另存 fingerprint-final.json。
- L1/L2：复用对应产品源指纹上的非零定向测试；文档/派生报告只走其生成与预检，不重跑领域确认/浏览器矩阵。
- L3：复用已完成的受管模块升级；本轮无模块代码变化，不重复升级。
- L4：上述实际页面证据承接，777 未通过单列；fixture 精确清理已完成。
- L5：先 `make ci.delivery.freeze.prepare` 刷新并预检，审阅生成差异后一次最终提交；clean HEAD 上执行一次 `make ci.local.quick`。最终结果以同 HEAD receipt 与独立 delta 复核为准，Quick 不替代场景裁决。

证据根目录：

- artifacts/form-structure-unification/ub-acceptance-resume/：首批代表面与能力隔离。
- artifacts/form-structure-unification/ub-two-gaps/：宽度、选择/确认/回读/防重。
- artifacts/form-structure-unification/ub-tender-hierarchy-identities/：层级、六身份、777、135/135 trace匹配。
- artifacts/form-structure-unification/ua-ub-limited-closeout/：独立审查、fixture收尾、生成预检、冻结指纹、Quick日志/receipt和承接证明。

回滚：按现有受管交付恢复相应 P0/P1 代码提交及成对前后端候选，必要时使用受管模块升级；不改真实业务数据。fixture清理不通过反向篡改已确认事实回滚，重建必须走其受管prepare且使用新实际ID。

## 7. 下一批

U-C 优先上述四项合同/结算，复用当前唯一机制。先按共享 view1764 处理收入/支出结算，再处理 view1569/1570 的合同入口及其明确 category 来源。保留帮助、字段策略与权限；按批次减少消费者。本批仅登记优先顺序，不追加功能或开始迁移。
