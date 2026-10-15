# Daily Runtime — 版本发布与用户视角验收（2026-10-15）

Goal: `DAILY-RUNTIME-VERSION-RELEASE-AND-USER-ACCEPTANCE-20261015`
Run: `.agent/runs/DAILY-RUNTIME-VERSION-RELEASE-AND-USER-ACCEPTANCE-20261015/run.json`
Branch: `release/daily-runtime-version-release-20261015`
Baseline: `ba7577c212b81468491942e972ea28bd64345ebd`（PR #664 合并后的 `main == origin/main`）

## Objective

1. 把目标 daily runtime（`sc-root:/opt/projects/repos/sce-product-odoo`，`ENV=dev`，
   DB `sc_demo`，自定义前端）从当前 `eae0c1c0` 沿受管 main 车道精确推进到当前主线
   `ba7577c2`，恢复服务端前端、服务端 source_revision、发布面并回读身份。
2. 以真实用户身份对已部署版本执行用户视角验收：89 项正式业务入口矩阵
   （入口职责、权限边界、关键写入），并抽验付款申请写入闭环。

## Scope / exclusions

In scope: run/goal 记账；daily runtime 代码面、服务端前端、发布面；`sc_demo` 上的
只读用户验收；验收暴露在归属层的缺陷（如有）。

Explicitly excluded: 弱化任何 ACL/字段权限/断言；新建环境或凭据授权；既存历史残留
（`verify.contract.lint` 49 项、`res.users` 断言漂移、demo seed 与 #525 文档状态守卫冲突、
`span→deliverySpan` 迁移、账号清理 P2 ENV-IDENTITY-CLEANUP）；`PAYMENT-REQUEST-CHAIN-ALIGNMENT`
候选未经授权不得并入主线。

## Status

- [x] R: 把 daily runtime 精确推进到 `ba7577c2` 并回读服务身份。PASS。
      - 发布前远端 runtime 仓库 preflight `verify.daily_dev.runtime_repo.clean` PASS
        （`mode=main branch=main head=eae0c1c0`，customer addons 只读挂载 PASS）。
      - `daily.runtime.main.bundle_sync`：`old_sha=eae0c1c0` → `source_sha=ba7577c2`，
        `normalized_from_candidate=false`，`bundle_sha256=7f07c68bbe40c5152538fc1d51701dd1963ea4d4fc4553e2803c076ce28af0ad`，
        `upstream=origin/main`。
      - `daily.runtime.source_revision.align`：`previous_revision=eae0c1c0` → 服务端
        `source_revision=ba7577c2`，`restarted=true`，`rolled_back=false`。
      - `daily.runtime.frontend.build`：在已部署 HEAD 重建服务端前端，`rebuilt=true`，
        `fingerprint=e88ee704aad5e2d3c306b64f93ff71baf0c0d8367b657df559e0d56687a274c5`，
        `entry_asset=index-BuKwbLKS.js`。
      - `daily.runtime.published_face.converge`：`guard_status=PASS`，`login=wutao`；
        `construction.standard` 快照 118（released 90 / gate 90）、
        `construction.preview` 快照 119（released 90 / preview 39 / gate 129）；
        `upgrade_mode=reused`（`smart_core` 模块树与上次已验证升级逐字节一致）。
      - 服务端 `http://1.95.85.92:18081/api/runtime-version` 回读：
        `source_revision=git_sha=ba7577c212b81468491942e972ea28bd64345ebd`，
        `database=sc_demo`，`environment=dev`，`product_version=1.0.0-rc.20`，
        `frontend_build_sha256=e88ee704…`。
- [x] U1: 89 项正式业务入口矩阵（只读）。PASS。
      - `artifacts/frontend-business-entry-matrix/daily-ba7577c2-full/summary.json`：
        `ok=true`、`completeness=complete`、`entries=89`、`problems=[]`、
        `console_errors=[]`、`served_revision=ba7577c2`、`login=wutao`。
      - 发布面 90 叶子 / 89 action 叶子的口径差异已治理：第 90 项
        `smart_construction_core.menu_sc_workspace_home` 由 scene 交付、无 action，
        已在 `config/frontend/role_surface_exposure_declarations_v1.json` 的
        `non_action_delivery_entries` 显式登记，并由
        `verify.frontend.role_surface_exposure_declaration.guard` 约束
        「验收宇宙 89 + 非 action 交付入口 1 == 发布面 90」。
- [ ] U2: 付款申请写入闭环（付款申请 / 日常合同 / 项目启停三条 lane）。

### U2 根因（2026-10-15，只读定位）

付款申请写入 lane 在展开「按明细填写」后停机：

```
表单页面打开失败：契约缺少合法声明
formStructure.relation_entry.page_size(outflow_line_ids)
```

抓取同一会话的 `ui.contract.v2`（`finance` 账号、记录 36192、action 780）后核实：
缺失**不在后端契约生产者**。`fieldInfo.relation_entry` 与
`componentConfig.relationEntry` 两处都携带整数 `page_size=20`（同页
`options_limit=80` / `options_search_limit=40` 亦齐备）；仅 Odoo 原生
`widget_options.relation_entry` 这一历史别名不含该键。

真正缺陷在**前端消费路径未接线**：`payment.request` 的 `presentationMode=task`，
表单经 `ObjectTaskPage → CanonicalFormNodeRenderer → canonicalFieldToFormSection`
渲染，而该投影从未输出 `one2manyPageSize`；`one2manyPageSize` 当时只在
native 形态（`formSection.mapper`）被投影。渲染层按「声明缺失即停机」消费，
因此停机。

结论：不新增前端默认值、不改后端契约，只补齐 canonical 形态的同源声明投影。

（本文件在批次推进过程中持续更新。）


### 2026-10-15 接管收敛（未冻结，未交付）

身份：`release/daily-runtime-version-release-20261015`，HEAD
`e12e75eaa5bdcfe5b01dfe14b89cb201fac60023` 加 run.json 登记的未提交范围。
原执行器改动保留；root 为唯一写者，两个 B 执行器只读复核。结果与原日志路径以
`.agent/runs/DAILY-RUNTIME-VERSION-RELEASE-AND-USER-ACCEPTANCE-20261015/run.json`
为唯一索引。

- P0 数据库登记：修复原生审计前态、最后操作和计数回读，原生生命周期获取行锁。
- P4 数据库适配器：先授权和原生状态校验，再改变连接准入；切断准入后终止连接；
  失败恢复准入。会话锁覆盖提交及独立审计/物理回读；提交未知不盲目回滚或重放。
  回执取本次审计快照，区分操作已提交但回执失败。恢复连接准入不代表恢复被终止的事务。
- P4 Demo 场景加载器：移除跨模型私有 token 和默认 sudo 办理，显式声明动作席位，按实际待审实例
  使用公开审批入口。奖金补专职业务配置席位；项目成员事实在办理之前准备。
  S65 成本与 S70 资金台账由真实来源动作生成并绑定 XMLID，冲突拒绝，不伪造来源。
  S69 通过结算审批及付款登记产生支付事实。合同、质安、行政、资金操作、风险及工作台
  种子通过公开动作到达展示状态；普通账户/价格有效状态与原生可编辑审查结果不冒称审批。
- S00 BOQ 改用版本化 CSV，成本员调用原生预检及导入，生成版本、批次、明细、摘要及审计；
  不手填导入成功快照。旧伪造批次与真实摘要不一致时拒绝复用，不能直接升级后宣称重建通过。
- S67 实验场景/伪快照与 S76 旧兼容引擎退出默认 RELEASE_SCENARIOS，仍保留显式样例入口；
  不自动启用旧工作流，不修改正式产品菜单及功能定义。

验证仅覆盖变化依赖：数据库适配器 45 项、数据库治理 17 项、Demo 生命周期 26 项、
BOQ 输入 5 项、既有本地生命周期工具 36 项纯测试通过。真实 ORM 已证明数据库审计
2 项、非 sudo 物资链/拒绝 root 2 项、BOQ 原生导入及幂等 1 项。后两次 ORM 使用
既有 `sc-local-dev / sc_dev_demo`，事务测试不是全新 Demo 重建，不是物理停库验收。
未变化的 P0 审计测试及物资链结果按输入差量复用，不重跑浏览器矩阵。

部署影响：新增 Demo 模型包装方法无新增表/字段；新 Demo 席位和 XML 需要受管模块/种子
重放。既有假批次与生成 XMLID 冲突必须走受管新建/重建或另行审计迁移，禁止绕过校验。
没有运行升级、重建、真实停库、发布、推送或合并。

待办：完成独立差量复核；独立平台控制库及获准目标/集群身份尚无当前受管绑定，已向所有者
提交是否纳入建设范围的问题；答案前不执行物理生命周期动作。随后按批准范围组织冻结候选的
受管全新 Demo 验收、目标环境角色与写入闭环及发布门禁。当前不能签发批次全部完成、
主线集成完成、版本发布完成或产品交付完成结论。

本次补充复核发现正式加载后的 `seed/steps` 是另一条补种链，前述场景加载器通过不能替代
该链验收。已修复 `load_full.sh` 选择正式 release 集合，避免重新加载 S67/S76；补种审批
统一委托实际 pending review 驱动，去掉任取审核人、fallback 及五处直接审批回调。
重复的结算推进合并为 `advance_settlement`，经办提交、经理完成，均明确非 sudo 身份；
保留末态断言。B 线只读复核未发现该增量新增确定缺陷。

补充验证：公开包装入口拒绝普通调用者 1 项（4 个包装方法）、驾驶舱实际成本员创建及重复
执行 1 项 ORM 通过。最新定向源测试为 Demo 27 + BOQ 5、本地生命周期 36 项通过；
旧 cockpit 测试曾要求 sudo/token 清除而失败，现重绑声明角色并反向禁止 token/sudo，
原失败日志保留在 run 索引。最新 L1 通过；未因此重复数据库测试或浏览器矩阵。
这些结果不证明补种完整流程已通过。

仍必须按顺序修复：投标直接终态及中标依据；合同直接 confirmed、付款/采购 sudo 办理；
未知公司归属推断；文档办理角色；BOQ 原生导入发布和 WBS/成本计划正式生成。
不删除补种能力冒充完整、不恢复 sudo 或私有回调兜底。它们是当前重建与冻结的代码前置阻断。

### 补种链续修：投标、合同、付款和资料（同一 dirty 候选）

P4 所有权不变，未修改 P1 产品守卫。投标由声明项目经办创建 prepare，走提交/等待/落标
动作；中标建立明确开标资料并调用确认中标，旧 won 缺权威快照与冲突来源拒绝。
合同由合同经理先建草稿和明细，再确认及消费实际待审实例；补齐标准合同审批组到既有
合同经理的映射。既成投标/合同不覆盖业务内容，但目前只验证明细存在，不宣称全值一致。
资金基线使用实际财务经理，缺公司归属直接拒绝。结算、采购、付款分别使用对应业务席位；
删除补种自动清理草稿的路径。付款共用驱动补齐原生支持的 rejected 重提状态。
资料及附件改用同一非 sudo 项目经办，组织成员先准备，既成文档不再产生无用附件。

B 线发现的合同审批席位遗漏及驳回重提回归均已修复。最新 L1 通过；L2 为
27 + 5 + 11 = 43 项纯测试通过，含动作顺序、中标来源冲突、幂等、禁止终态 create、
审批未完成拒绝、合同席位、草稿/驳回公开重提。结果是编排代码验证，不能代替 ORM 权限
和全新安装验收。原数据库/P0、未变 BOQ 原生导入等证据未重复执行。

本次读取当前 `.agent/context.yaml` 确认 local.dev 已声明为 realistic/no-demo；
不能凭历史 Demo 事务测试结果授权新的 Demo 重放。未修改环境、升级或重建数据库。
仍须修复 showroom/项目/BOQ/WBS 等剩余链，随后解析隔离验收库的明确角色、身份及
filestore，通过既有受管入口验证。平台控制库范围授权仍未得到单独答复。
未冻结、未提交、未部署，批次整体及产品交付均未完成。


### 整体续收口：补种源码收敛与两条原生 ORM 链（2026-10-15）

候选仍为 `e12e75eaa5bdcfe5b01dfe14b89cb201fac60023 + dirty`，未冻结。
P4 Demo 编排收敛：项目、展厅、BOQ/WBS、正式产品示例和工作台使用声明业务角色；
手工 BOQ 明确录入原生分析，不伪造导入快照；成本计划调用公开生成动作并保留分析来源；
WBS 正常创建建立计划，同值重放不发起编辑。共享项目阶段同步旧步骤退役且不再写入。
付款提示示例从新草稿合同走正式确认，不复制已确认合同状态；取消使用正式动作。
新增会计能力 Demo 席位只引用既有产品权限，尚未在当前数据库重放。

验证结果统一记录在 run：L1 `make ci.local.iteration` 通过；纯测试当前有效集合为
27 + 5 + 18 = 50 项。补种测试变化后只执行18项，未重复不变的27和5项。
新 ORM 两例在受管 `local.dev.test` 执行，结果 **2 tests，0 failed，0 errors**：
普通成本经理的手工分析→BOQ发布→成本计划，金额1200、分析来源与成本树、重复明细身份均验证；
WBS 正常创建→计划发布→同值重放保持身份，变更仍由原生守卫拒绝。测试事务回滚，无模块升级。
B 线独立检查源码与原日志确认上述范围成立，不代表完整种子链通过。

纠正上一节环境结论：`AGENTS.md` 明确 local.dev 为持久 Demo 特性库，优先于
`.agent/context.yaml` 的冲突描述，因此受管事务 ORM 测试可执行；不据此自动重建持久库。
`make local.dev.verify_authority` 实际通过（模块、财务身份/组、公司币种与税率）。
原始日志 `/tmp/sce-whole-orm-iteration.log`、`/tmp/sce-whole-seed-unit.log`、
`/tmp/sce-whole-supplemental-final.log`、`/tmp/sce-whole-native-chains-orm.log`、
`/tmp/sce-whole-demo-authority.log`，均引用原件，不复制新证据包。

剩余验收：完整 release 与补种首次串联、所有补种角色读取权限、新角色 XML 重放、
付款提示示例合同确认及重复执行。独立平台控制库与目标库的受管绑定仍未落实，未执行物理停库。
批次整体未验收完成；主线集成、部署和用户验收均未完成。未运行 Quick、推送、合并或发布。


### 付款软提醒真实链与审批席位闭合（2026-10-15）

同一 P4 dirty 候选，未改 P1 权限。新增事务用例从源 XML 重放新增 Demo 席位，
真实执行 guidance 首次创建与重复执行。发现并区分三类问题：
1. 测试工具 XML 输入缺文件名、诊断读取身份未绑定当前主体，已修复工具；
2. 运行库业务分类规则缺源码已有的“无审批策略”分支；回读分类10、策略公司False，
   合同经理 allowed/data company 均为[1]，不属于角色权限不足。测试精确重放源规则后通过此点，
   事务回滚意味着永久升级缺口仍在；
3. 实际合同审核模板需合同经办、经营、项目负责人、成控及管理层，原 Demo 映射不完整。
   合同经办绑定现有 ct1；经营新增仅持原生经营角色的 Demo 席位，成控绑定现有成本经理。
   项目准备包括声明的办理/审批席位，保留原生 can_review 和所有记录规则。

基础 XML 会新增用户或替换其组，故 load_base_seed 在载入后、场景业务动作前调用既有
数据空间登记机制，并在登记完成后 commit；不手工赋数据隔离权限。纯测试从正式两类合同
模板推导所需审批组，另验证 XML→登记→commit 顺序，当前 supplemental 19 项通过。
原27项生命周期/5项BOQ及之前2项BOQ/WBS ORM未变化的函数路径不重复执行；旧结果仍限原范围。

`/tmp/sce-guidance-enrolled-orm.log`：1 test，0 failed，0 errors。
实际新建合同经正式审批 confirmed，创建人为合同经理；付款申请由业务发起人建立并保持draft；
原生 guidance blocking=False、requires_confirmation=True；二次执行复用合同/客商/付款ID。
用例使用现有 S69 来源和资金基线，不是全新安装证明。所有写入事务回滚。
L1通过 `/tmp/sce-guidance-enrollment-iteration.log`；19项纯测试通过
`/tmp/sce-guidance-enrollment-unit.log`。失败原日志、归因和恢复事实统一保存在run索引。

下一步先准备受管运行时恢复条件，升级并回读过期源声明，再经既有入口重放用户及完整补种链。
未运行永久XML修补、数据库重建、主线合并、部署或发布；整体仍为verification_pending。


### 受管空库重建与逐场景续跑（2026-10-15）

按所有者允许调整/重置开发验收数据的既有授权，复用固定 local.dev 身份，未创建新环境。
升级前通过 `make local.dev.snapshot` 留存 `artifacts/local-dev/snapshots/20261015T031821Z`，
哈希回读匹配，数据库dump 10768826字节，附件归档1805个成员全部属于sc_dev_demo。
行业模块升级首先因升级适配器未透传Demo标识被拒绝；补齐固定local.dev声明及通用脚本透传，
36项工具测试与独立复核通过，未放宽guard。第二次升级遇旧BOQ假导入摘要冲突，两次失败后
权威回读均通过；因此转为既有 `local.dev.rebuild_demo`，不篡改旧导入依据。

重建正式产品、Demo模块安装、税基线、Demo权威检查已通过，但完整release加载在S69停止。
这不是完整重建PASS。数据库内容身份已经改变：此前ORM结果只保留为历史代码切片证据，
不能作为新库当前验收；源文件未变的纯测试可以沿用。

S69实际失败逐层归因：结算经办/审批项目成员未准备；结算审批缺真实采购订单。
现声明必要成员，创建真实钢材批次采购，公开确认并审批，关联结算后提交，资金先激活，
再完成付款审批和付款登记生成的台账。已成功受管加载，原日志 `/tmp/sce-s69-purchase-chain.log`。
B线指出采购复用只比金额不充分，已增加唯一性、公司、项目、明细产品核验；既成来源冲突
拒绝回退修改。仅重验受影响S69一次，`/tmp/sce-s69-source-reuse.log`通过。

S70原假设“付款执行生成资金台账”错误，正式付款执行生成payment.ledger。
现另建金额120万的独立收款申请，走审批→收款登记received→原生treasury_ledger_id→对账；
不动S10原500万draft申请，不制造资金流水。`/tmp/sce-s70-receipt-chain.log`受管加载通过。

S71全部依附已退役S67实验场景，并人工写验证pass、发布及审计记录；按所有者实验能力退役
口径退出正式RELEASE_SCENARIOS，保留诊断源码但不作为正式Demo事实或验收通过。产品菜单
及原生审计能力未删除。纯测试锁定S67/S71/S76不进入正式集合。

剩余集合从RELEASE_SCENARIOS声明AST、已提交完成边界S70推导，仅续跑其后14项。
S72、S73已通过，其他运行结果以run索引和原场景日志为准；不重置数据库、不重跑前序成功场景。
最新源码门禁 `/tmp/sce-release-boundaries-iteration.log`、52项纯测试
`/tmp/sce-release-boundaries-unit.log`通过。新持久来源回读用例等待场景写入结束后串行运行。
整体仍未冻结、未主线集成、未部署到日常服务器、未完成用户验收。

### S80/S89 原生整改闭环续跑

P4 / smart_construction_demo：正式产品的状态守卫、ACL和记录规则不变。四条整改链以XML输入事实为唯一源，由项目经办提交和登记整改，项目经理录入复验结果；原生create产生状态和审计。Demo入口限定安装主体、明确问题与子记录身份，冲突重放拒绝覆盖。B只读复核发现函数须处于noupdate=0，已修复后才运行。

S77、S78、S79完成加载；S80第一次在草稿整改守卫失败，修复后进一步发现物资经办未加入项目。按S80/S86已有动作声明补齐项目成员，不扩角色权限。该失败与重试记录在run原索引；S80/S89/S86为受影响集，前序通过场景复用。52项pure定向与L1已通过；真实闭环和独立持久化来源回读仍待完成。S75没有直接源文件，加载成功不能代替汇总投影验收。

整改真实闭环及独立回读已通过：S80/S89加载成功；`demo_loaded_chains`三项中付款/收款与guidance首次通过，整改重放因test.safe未转发Demo环境标志失败，仅修工具后重跑整改1项通过。初次class-only选择0项按失败保留，不算证据。整改断言核验四问题closed、两席位create_uid、提交/申请复验/闭环原生审计actor、幂等与冲突拒绝、普通用户种子入口拒绝。

P4 supplemental身份修复：用户角色组替换后走既有native enrollment；最终demo_90同时要求目标账号非sudo可读已知付款/项目。S88假legacy来源改为manual并删不存在迁移来源字段；保留正式审批/登记链和原生SQL台账。当前54项Demo纯测试、36项工具测试、L1通过；剩余S85/86/87/88/90按精确集合串行加载。工作区仍dirty，未冻结或发布。

S85已通过：请假/用章补同源部门；薪酬申请人对齐实际发起席位，保留“只办自己的单据”记录规则。S86保证金的旧财务执行映射不具模型写权，改项目经办提交、实际审批、原生确认；随后租赁结算付款确认暴露单一物资角色缺合同/付款读取。经B核查不存在合适既有普通席位，按正式可分配角色组合新增Demo租赁核对席位（物资员＋受限财务），没有改P1角色或权限。必须保留“单一物资角色不能因此宣称全链可用”限制。新增ORM反例保持原物资账号合同读拒绝；新增席位不持有全产品或业务配置管理权限。S87劳务用工同样改显式提交/实际审批后确认，避免依赖无审批策略。57项纯测试与L1通过，运行继续精确剩余集。

### Supplemental stage preparation correction

At HEAD e12e75eaa5bdcfe5b01dfe14b89cb201fac60023 plus explicit dirty P4 Demo scope, first seven supplemental steps passed. Project preparation failed first on the progress actor (corrected to declared cost-manager seat), then on absent sender email. Demo user source now declares reserved synthetic emails. Terminal stage samples are finalized only after their business facts; native project actions and closure guards remain authoritative. The finalizer refuses incompatible paths rather than reopening or silently passing.

Affected inputs and keys are recorded in the existing run supplemental_resume.stage_correction. L1 passed; 62 focused pure tests passed. B read-only review found no new definite blocker. Full-profile replay idempotence remains unproven; only unfinished steps will run. No browser matrix, snapshot or full rebuild is repeated. Runtime acceptance and physical database lifecycle remain incomplete.

### Current local closure readback

The fresh local Demo chain has now completed all 16 registered supplemental steps, incrementally, including real terminal project actions and final non-sudo sample visibility checks for wutao/demo_full. Earlier completed scenes and steps were reused; no second full rebuild or browser matrix was run. Supplemental tender targets now consume the declared sample stage, pending bids advance through public actions, and settled outcomes cannot be rewritten. Settlement creation/lines/submission use the existing business initiator; stage closure uses the existing composite project manager. No product ACL or financial closure guard was weakened.

Current candidate remains HEAD e12e75eaa5bdcfe5b01dfe14b89cb201fac60023 plus dirty scope. Latest L1 passed, 64 focused pure tests passed, current database Demo action ORM 7/7 and platform governance ORM 10/10 passed. Local services were restored/restarted; health and Demo authority checks passed. Original logs and commands are indexed in run.takeover_20261015.current_local_closure and supplemental_resume, not copied into a second result table. B read-only source reviews found no new definite blocker in these corrections.

This closes local Demo source/replay blockers, not overall delivery. Physical database suspend/resume still lacks an independent registered control-plane and target binding; ORM tests do not prove those external effects. Full-profile replay idempotence, frozen candidate review, mainline integration, daily target deployment and full user product acceptance are not claimed. Freeze/Quick/publication remain pending while that required runtime blocker is open.

### Proposed physical lifecycle rehearsal — not created or authorized

Owner decision required: add one isolated P4 platform database rehearsal environment. Exact proposed identity and acceptance/recovery checklist live in run.takeover_20261015.physical_rehearsal_proposal. Proposed project: `sc-platform-db-rehearsal`; independent control DB: `sc_platform_control_rehearsal`; disposable target: `sc_tenant_lifecycle_rehearsal`. Each has its own DB role, exact filter and filestore namespace; no host ports or existing development volumes. Control installs only minimal platform dependencies and contains no construction/customer business data. These are proposals, not registered runtime facts.

After confirmation: implement and test governed prepare/preflight/register/apply/readback/recover/cleanup entries, establish exact runtime identity, then prove suspend with a real target-role session, fresh connection refusal and independent control availability; prove resume with a fresh target-role connection and native audit readback. Preserve evidence and restore target admission on assertion failure; resolve uncertain commits by exact audit ID. Existing local.dev and daily environments are excluded. Database architecture policy section 13 and baseline execution rules require explicit new environment authority; a general continuation does not identify the missing runtime scope.

### Request-bound database operation evidence

B review found that the old fixed receipt path could retain a previous success after a failed attempt. P4 now shares an atomic, locked pending/pass/fail receipt writer with execution ID/request matching. Native P0 operation JSON audit stores reason and execution ID in the same transaction; the adapter compares the independent committed audit before emitting success. Failure evidence records external effects and admission-only compensation without claiming restoration of terminated transactions. Every pending receipt is explicitly unknown and forbids automatic replay, including after process termination. The future governed wrapper must provide the scripts package path, fresh execution identity and strict receipt consumption; it is still not implemented or authorized as a physical runtime entry.

49 adapter tests and 17 governance tests passed; L1 and focused compile/diff checks passed. B issued limited source PASS. The affected native audit ORM pair is recorded in the existing run result index. Existing Demo chain evidence is unchanged. The explicit isolated environment scope question remains pending; no new database, role, credential or physical lifecycle operation has been performed.

### Authorized isolated physical lifecycle closure

The owner approved the previously proposed isolated scope. P4 now declares the fixed project/control/target identity, independent credentials and three volumes, with no host ports and no customer records. This supersedes the pending-authorization statements above; existing daily and local.dev environments were not modified by this rehearsal.

Actual PostgreSQL suspend/resume passed against cluster 7696745268391657510: one existing target session terminated, new connections refused during suspend, independent control remained available, and fresh target connection succeeded after resume. Native audit IDs 1/2/3/5/6 match five success receipts. Failed initial suspend and injected post-cutoff failure remain failed receipts, with admission-only recovery; terminated transactions are not restored. The final readback independently matches each request against current declaration and persisted native audit, verifies unprivileged application roles, bilateral database access denial, and an empty target.

Original commands, JSON paths, failure classification and continuation reuse are indexed only in run.takeover_20261015.physical_rehearsal_execution. Latest L1 and 11 environment plus 49 adapter tests passed. B limited independent review passed. P0 audit ORM and Demo evidence are reused because their inputs did not change. No broad browser acceptance or second physical cycle was run.

Governed cleanup passed; read-only project-label inventories found no remaining containers, volumes or network. Original evidence remains readable outside removed volumes; private authority is not exported. This closes the isolated physical lifecycle blocker, not real tenant application installation, mainline integration, daily deployment or complete user product acceptance. Candidate remains dirty at e12e75eaa5bdcfe5b01dfe14b89cb201fac60023 pending finalization.

Final source review found three legacy experimental steps still reachable via explicit selection/all, despite exclusion from demo_full. Retired payment_ledger_p1 (SQL approval/private ledger creation), phase2_payment_request_demo and phase2_settlement_order_demo (sudo business creation/arbitrary project fallback), including their source bodies and registration. Formal S69 and demo_full remain unchanged. Focused supplemental tests 30/30 and L1 passed; run records affected keys and original logs. Existing formal-chain runtime evidence is reused, while source inventories are regenerated after deletion. No claim that every historical optional seed or full-profile repeated replay has been accepted.
