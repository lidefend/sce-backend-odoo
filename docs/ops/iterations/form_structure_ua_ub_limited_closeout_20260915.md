# 唯一结构机制及首批代表面迁移

交付范围：U-A／U-B 有限收口。不是全系统统一完成。action 777 保持未通过的环境残项；U-C 本批不启动。

## 1. 候选与责任边界

- 统一基线：`9f7bb560917a98b638a6d2a516fe2542634fdff8`。
- 产品审查／最后页面候选：`967ff6f425436c5e8792fddbde0fc3a58060e30b`。
- 产品完整指纹：`9816cfadeac5fa870c0380f033c1155910671d3cd455f76e006ae3c745f116a8`，7461 路径。
- 本次收尾 Formal Product Layer：P4；Layer Target：交付证据、台账及既有 fixture 生命周期；Module：docs、contracts/generated、既有生成报告与受管证据工具。没有新增 P0/P1/P2/P3 产品修改。首轮 Quick 发现的 P4 白名单遗漏仅在守卫和既有测试中恢复。
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

客户宽度、中标确认与既有移动证据绑定产品候选/前后端模块/数据库身份。首轮冻结18ee479c只加入文档及生成证据；随后P4守卫恢复仅改白名单和既有测试，产品源码不变。通过源码树与完整指纹差异证明承接，不能仅按端口识别版本，也不把旧浏览器缓存当新候选。

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

## 7. 首轮 Quick 失败与定向恢复

首轮唯一一次 `make ci.local.quick` 运行在 clean HEAD `18ee479cf61b941f586f23d04bd55e157d4649ea`，在 `frontend_v2_policy_projection_guard` 失败，未产生 receipt。生成预检、密钥/个人数据扫描、历史检查、复杂度和契约结构锁此前通过；后续门禁不能因先前通过而推定完成。

首个失效层为P4守卫登记：`_snake_case_tokens` 同时扫描字段标识符和字符串枚举值，白名单漏列后端Schema及前端decoder已正式声明的 `container_tree_authority`。恢复仅在正式枚举值列表加入该值，保留所有禁止payload别名规则，不改产品Schema、页面或契约行为。

`make verify.unified_page_contract.v2.stable_projection` 已恢复通过；既有测试入口新增1个非零回归，正式值通过而 `raw.container_tree` 和 `root.form_structure_contract` 均被拒绝。独立审查认可此最小P4范围。生成证据随新候选重新准备。

原始Quick失败保留在 `ua-ub-limited-closeout/quick.log`；定向恢复在 `guard-recovery.log`、`guard-recovery-test.log`。**定向恢复不等于Quick通过。** 用户要求本轮一次Quick，因此新候选不自动追加第二次；追加执行需用户确认。action777裁决、fixture清理和53→50不变。

## 8. 下一批

U-C 优先上述四项合同/结算，复用当前唯一机制。先按共享 view1764 处理收入/支出结算，再处理 view1569/1570 的合同入口及其明确 category 来源。保留帮助、字段策略与权限；按批次减少消费者。本批仅登记优先顺序，不追加功能或开始迁移。

## 9. PR #480 远端门禁恢复

远端候选 d0c438f360e661b4ecab4506d9550f2f26887d8d 的 frontend_release_gate（run34965981252）首个失败命令为 `make verify.frontend.scene_component_bridge.guard`，断言仍要求宿主包含 NativeFormTreeRenderer 和 data-native-contract-structure。检查版本为 scripts/verify/frontend_scene_component_bridge_guard.py blob `20a71ee6e40ad1dda4e1e23bc9c2f85e8dc293bb`；基线9f7bb560与该候选均缺这两个宿主标记，守卫版本相同。

实际行为没有丢失：宿主两个任务／工作区分支均使用 CanonicalNativeFormSurface，后者仍将 primary／subordinate、字段 schema、可见性、动作状态、只读事实和事件传给 NativeFormTreeRenderer。正文与导航的绑定、动作权威及权限边界继续存在。P4 修正改为检查这条公开组件接口链，不恢复废弃源码位置、不删除检查。

- Formal Product Layer／Layer Target：P4 验证及测试登记；Module：scripts/verify。新增2个测试实际运行守卫，正例通过，8种断链反例全部拒绝，包括模式、导航、字段可见性、动作转发／状态和从属区节点被替换。
- 第二项独立失败为行数门禁：useRecordActionPresentation.ts=505>500，useRecordPageLifecycle.ts=546>544。相关文件及守卫都来自基线。采取 P0 通用前端等价提取：两个既有提交判定原样移至 contractActionPresentation.ts，场景目标分派原样移至 sceneBlockAction.ts；原接口／函数体／优先级不变，文件分别降至493／527行。保留原上限，未加豁免、压缩空行或改行业页面。
- P0 Why Here：只拆分通用动作呈现与分派职责；Why Not Elsewhere：不把此职责放进P1业务配置或P4脚本，不改字段、章节、权限或存储。Blast Radius：两个通用运行模块的调用边界；定向验证6个提交方法和8个分派场景，包含状态栏优先、空状态回落、route优先、空目标和异常传播。
- professional_quality_gate（run34965981245）最终失败于 `make verify.guard.registry`：统一结构测试的模块式调用未登记，已有candidate前端测试仍误标orphan。精确修正两项生命周期记录；不改变扫描规则，不添加目录级豁免。登记的模块式调用继续由既有Make测试入口执行。
- release_candidate_gate只因前端失败而失败，不另开根因。public_guard和merge_policy_gate在旧候选通过，但新HEAD仍须取得自己的远端结果。

验证节奏：L0绑定完整指纹；L1 `make ci.local.iteration`；L2桥接守卫、2个实际守卫测试／8断链反例、既有contract_header_action单元入口、style_system及guard.registry均通过。初次L1发现新增EOF空行，修正后才继续。P0提取函数体按归一化空白逐字相等证明承接；L3无模块／数据库变化，不重复升级；L4模板和结构不变，复用已批准浏览器证据。L5先生成预检、独立复核、按P4／P0提交边界形成新冻结HEAD，再运行必要的最终Quick和受管PR更新，不能用d0c438旧receipt替代新HEAD。

原始失败、定向结果、函数体等价证明和新指纹归档在 artifacts/form-structure-unification/ua-ub-limited-closeout/。当前文档在新候选冻结前编制，最终Quick与远端结论由对应HEAD receipt和PR检查决定，不预先宣称通过。

用户已澄清最终验证规则：日常轻量验证→修复后定向验证→最终候选Quick→成功证据复用。有明确修复依据时重验不需再次申请授权。本条替代第7节此前对“一次Quick”的解释。

action777继续环境阻断、未通过，兼容台账保持53→50；U-C1四入口任务书已准备，迁移未启动。任何合并仍需必需检查通过、审查意见关闭和最终HEAD证据一致；本轮不执行合并。

### 9.1 共享动作栏守卫的后续恢复

f84a667c449fd180626361fb136d41f0d7f7219e 的本地 Quick 已通过且 receipt 精确匹配，但远端 frontend_release_gate（run34968163107）在 2026-09-15T12:20:58Z 首次失败于 `make verify.frontend.professional_workflow.unit`。断言为 `task and workspace do not share CanonicalActionBar`；守卫 blob `92cc8b17029044b1a49c845fddc084c19b9ee974` 与基线9f7bb560一致。前述桥接及样式检查在这轮已通过，不重复诊断。

该断言仍要求宿主源码包含两次动作栏标签；实际兼容任务路径保留直接动作栏，原生任务和工作台通过共享 CanonicalNativeFormSurface 消费同一 CanonicalActionBar。首个失效层是P4验证工具，产品动作桥接未丢失。

- Formal Product Layer：P4；Layer Target／Module：scripts/verify 专业工作流静态守卫及既有测试。Standard vs User-Specific：通用验证工具。Why Here：修复组件提取后失真的检查位置；Why Not Elsewhere：不修改P0组件或P1声明来迎合旧检查。Blast Radius：只影响该守卫，不修改业务页面、权限或动作执行。
- 最小修复逐一验证任务／工作台的共享表单面输入、兼容任务动作栏、共享面动作栏的 direct／overflow／primary 和 action-ref 转发，以及 header ownership；保留全部其他断言和原Make入口。
- L0完整指纹绑定；L1 `make ci.local.iteration` 通过；L2 `make verify.frontend.professional_workflow.unit` 通过10个模型案例和5个Python测试。新增测试含9种断链反例，覆盖分支丢动作、动作优先级丢失、事件丢转发、绕过页头所有权和组件导入丢失，均必须被拒绝。
- L3／L4按与f84a667c逐文件比对证明产品源码未变，承接其影响分析与既有浏览器证据；本轮不触及数据库、容器或fixture。L5重新生成预检、独立审查、冻结新HEAD后取得新的Quick及远端检查；f84a667c receipt仅保留为旧候选证据。

本条在新候选冻结前记录，最终远端状态以新HEAD对应运行及归档为准。release_candidate_gate的下游失败不增加独立修复范围；professional_quality_gate最终结果另行核对。

### 9.2 审计时间线所有权守卫恢复

303ee222a25581e619b38256715059f4b4aaa695 的本地Quick通过后，远端 run34969767432 于2026-09-15T12:36:59Z 首次失败于 `make verify.frontend.professional_audit.unit`，断言为 `task and workspace do not prevent duplicate audit timelines`。守卫版本 `d05dbab95d5d8a1c443d760bc408e4cb214700b6` 与基线相同；它仍要求show-audit-timeline的true／false都位于宿主。实际旧任务路径由ObjectTaskPage显示审计、协作面板设false；原生共享面由协作面板设true显示审计，结构提取未改变该权威。

P4／scripts/verify仅修两份守卫及既有测试文件，检查真实NativeCollaborationPanel调用的时间线所有权与权威props；不更改P0组件或P1视图来满足旧源码位置。L1迭代通过；L2审计9个模型案例、4个Python测试（新增5种断链反例）通过；同一提取影响的协作调用边界45个模型案例、29个测试通过。其他引用ContractFormDriverHost的守卫已只读核对，无需产品修改。上轮f84a667c专业质量最终通过；303ee222的专业质量单独收齐，不由前端下游失败推断。

本轮所有产品源码相对303ee222保持不变，L3／L4承接既有确定性影响分析，不重复升级、fixture或浏览器矩阵；action777未通过、53→50不变。新增P4修复独立提交、生成预检和独立复核后冻结新HEAD，运行其最终Quick及远端门禁。各旧候选receipt仅用于历史证据。
