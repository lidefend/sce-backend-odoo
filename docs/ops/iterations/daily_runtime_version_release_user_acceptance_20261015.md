# Daily Runtime — 版本发布与用户视角验收（2026-10-15）

Goal: `DAILY-RUNTIME-VERSION-RELEASE-AND-USER-ACCEPTANCE-20261015`
Run: `.agent/runs/DAILY-RUNTIME-VERSION-RELEASE-AND-USER-ACCEPTANCE-20261015/run.json`
Branch: `release/daily-runtime-version-release-20261015`
Baseline: `ba7577c212b81468491942e972ea28bd64345ebd`（PR #664 合并后的 `main == origin/main`）
Rebind: 2026-10-15 所有者接管后，本 run 沿用同一记录与证据索引改绑到 `fix/data-ownership-visibility-recovery-20261015`，
基线更新为 `10bf72ef4bb060556bd2844598b58f9806392d34`；下面各章节以出现时的实际 HEAD 标注，不复用旧 HEAD 的结论。

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

## Three-database closure on the daily development server — stage identity and step 1

Owner ruling 2026-10-15 extends the goal: on the daily development server, close the duties of the platform
control database, the demo database and one customer development business database, unify the onboarding
mechanism across demo and customer tenants, and complete product acceptance. This is not a formal production
release. The earlier blanket "no new database/profile/credentials" note is superseded for this server only; the
concrete target identity, recovery conditions and governed entries still have to be established first. The
authoritative record is run.takeover_20261015.three_database_closure.

### Step 1 mechanism: tenant topology, not just database identity

The database identity inventory answered the cluster question (which databases exist, which role owns them,
which filestore namespace each resolves to). It deliberately says nothing about what each database carries, and a
name is not evidence. A new governed read-only entry,
`make daily.runtime.tenant.topology.inventory`, now answers the tenant question from the runtime itself: per
database it reads the module registry, the companies, the tenant registrations with their declared
`data_purpose`, and the per-company row counts for the declared business model set — including rows no company
owns. It never writes a business row; `--report` writes only a local file.

Two invariants are checked mechanically because they must hold whatever the operator later binds: a database that
installs the platform kernel without the industry product line must carry no business rows, and every company that
owns rows must appear in that database's tenant registry with an explicit purpose.

### Step 1 observation (HEAD 10bf72ef, read-only)

- Cluster: `postgres`, `sc_demo`, `sc_odoo`, `sc_platform_core`. The only login role is `odoo`, and it carries both
  superuser and createdb. Each database resolves to its own filestore namespace. `dbfilter=^sc_demo$`,
  `list_db=false`.
- `sc_demo`: 81 installed modules, including `smart_core` 17.0.1.1.14, `smart_construction_core` 17.0.0.171,
  `smart_construction_custom` 17.0.2.0.0 and the customer module `sce_customer_baosheng` 17.0.2.8.0. Companies:
  1 四川保盛建设集团有限公司, 2 Demo Secondary Company, 21 FE Company A, 22 FE Company B. Registrations declare
  company 1 as `demo` and companies 21/22 as `test`.
- `sc_platform_core`: 64 modules, `smart_core` 17.0.1.0 only, no `sc.tenant.company.registration` table, no
  business rows. It exists but is not yet a functioning control plane.
- `sc_odoo`: 11 modules, no product line, no registration, one bootstrap company.
- Business volume lives in exactly one database. `sc_demo` carries 60,715 rows across the declared set
  (`payment.request` 34,897 + `construction.contract` 12,672 + `project.project` 927 owned by company 1, 25 rows
  by companies 21/22, and 12,194 `payment.ledger` rows owned by no company at all).

The decisive fact is a mixing finding, not a naming one: the customer company's real business volume lives inside
`sc_demo` while that company's registration declares `data_purpose='demo'`. "The demo database" is therefore not
yet a pure demo database, and the customer development duty has no bound target. Both are recorded as blockers
rather than resolved by assumption.

### Step 1 correction in the ownership probe (mechanism, not numbers)

The ownership probe previously measured the declared anchor with a single `(anchor, '=', False)` leaf. Odoo
translates that leaf into a predicate on the joined segment, so for a dotted anchor such as
`project_id.company_id` every row whose head relation is empty was silently dropped — even though the installed
ceiling rule carries an explicit `(project_id, '=', False)` branch and therefore treats that row as an unset
owner. The operative measurement now decomposes the anchor into head-missing plus joined-owner-null, reconciles
that sum against the raw left-join scan per model, and records the dotted-leaf translation as a checked fact so a
future engine change is reported rather than absorbed. Per-principal effective visibility uses the same
two-part set.

The corrected read-only probe reports 10/10 assertions PASS and reproduces the owner's ruling figures exactly:
`unset_owner_rows` 76,521 (of which 76,112 are in the active universe), `visibility_loss_rows` 50,284,
`shared_visible_rows` 26,237, and zero rows carried as "not measured against a principal". The visibility loss is
`payment.ledger` 12,194, `payment.ledger.allocation` 12,194, `sc.hr.payroll.document` 10,960,
`sc.document.admin.document` 9,274, `sc.dashboard.cockpit.fact` 3,750 and `sc.office.admin.document` 1,912.
These stay classified as unresolved historical attribution: not proven-hidden, and not auto-assigned.

### Status

Mechanism acceptance for step 1 (identity and tenant topology) is complete at this stage identity. Code
integration, daily deployment, full mechanism acceptance and product acceptance are all still open, and no
delivery conclusion is claimed. Next: align with the user-module executor on customer source mapping and
versioned migration, then prepare and verify a recovery point for the affected databases and filestore, then bind
the three duties with exact role/filter/filestore identity before the first database write.

### Step 1 mechanism: routing and cluster-ownership inventory

The tenant topology entry answers what each database carries, but it cannot prove that a database is served by
exactly one application instance, that each instance filters to exactly one database, or that two live
postmasters are not writing the same cluster directory. A new governed read-only entry,
`make daily.runtime.routing.inventory`, answers that from container metadata and the cluster catalog only. Its
unit entry is `make verify.daily.runtime.routing.inventory` (11 tests, OK). The entry never writes a business
row; `--report` writes only a local file.

Eight assertions run mechanically: `cluster_databases_observed`, `application_instance_declares_a_database`,
`application_instance_filter_is_exact`, `single_serving_instance_per_database`, `published_host_port_unique`,
`one_live_postmaster_per_cluster_data_volume`, `instance_data_volume_distinct`, and `inventory_is_read_only`.

A tool defect was corrected while building it: Docker lists one published port twice when a service binds both
IPv4 and IPv6 on the same host port, which the first cut mis-flagged as a duplicate. The check now dedupes by
(container port, host port) and carries a regression test for that shape.

### Step 1 router observation (HEAD 10bf72ef, read-only)

Six instances are observed. Four of them serve a database with an exact filter:
`sc_demo` <- `sc-backend-odoo-dev-odoo-1`, `sc_tenant_baosheng_uat_core035_20260727142732_46a327` <-
`sc-core035-mvp-daily-20260727142732-46a327-odoo-1`, `sc_release_rehearsal` <- `sc-release-rehearsal-ingress`,
and `sc_user_data_rehearsal` <- `sc-user-data-rehearsal-odoo-1`. Every application instance declares a database
and every declared filter is exact, so `instances_without_exact_filter` is empty. The duty gap is on the other
side: `sc_odoo` and `sc_platform_core` have no serving instance at all.

The run FAILS on exactly one assertion: `one_live_postmaster_per_cluster_data_volume`.
`sc-backend-odoo-dev-db-1` and `sc-backend-odoo-prod-db-1` both run and both mount the same Docker volume
`sc_dev_db_data` at `/var/lib/postgresql/data`. They report the same `postmaster.pid` (pid 1, mtime
2026-09-24T08:28:55Z) and the same `pg_control_system()` system identifier `7597381856873586726`, and both can
query the same catalog (`postgres`, `sc_demo`, `sc_odoo`, `sc_platform_core`). The second postmaster comes from
another checkout under `/opt/projects/repos/sce-backend-odoo` (compose project `sc-backend-odoo-prod`, local
modified `docker-compose.yml`); only its `db` and `redis` services run.

This is a real defect, not a tool artifact, and the assertion is kept at FAIL. Resolving it is an environment
mutation (which stack is authoritative, and a governed stop entry for the other), which this batch's
authorization does not cover and no governed entry provides. It is recorded as a blocker rather than papered
over or fixed by weakening the assertion.

### Step 1 recovery point (L1)

A paired backup of the affected database and filestore was taken through the governed continuity entry
(`backup_set_id = sc_demo-20261015T062043Z-849c0c54`, `paired_backup_pass: true`). An isolated restore drill
restored that set into temporary resources and compared sentinels:
`isolated_restore_pass`, `database_restore_pass`, `filestore_restore_pass` and `sentinel_comparison_pass` are
all true, temporary resources were removed, and egress stayed internal. The continuity contract binds `sc_demo`
only; `sc_platform_core` (no business rows, rebuildable from source) and the not-yet-created customer database
have no paired recovery point. Because neither is written yet, this is not a pre-write data-loss risk, but the
governed contract must be extended before the first write to either.

### Step 1 user-module alignment (read-only)

The customer repository `sce-customer-baosheng-odoo` is clean at `bfbc736`. Its manifest declares
`tenant_key=baosheng`, `module_version=17.0.2.8.0`, `install_mode=customer_database_only`,
`company_provisioning=payload_create_and_register`, `payload_required=true` and
`uninstall_policy=fail_closed`, with versioned migrations already present. On the product side,
`smart_core.tenant_payload_import` resolves company scope from four declaration paths and fails closed with
`TPV1_COMPANY_SCOPE_MISSING` when none applies; `data_space_provisioning` explicitly does not implement a
customer onboarding channel. The customer source mapping, versioned migration and new-data import repair
therefore belong to the user module, and this repository must not grow a parallel customer-specific backfill.

### Authorization coverage

The owner widened this batch to build and verify three duty-separated databases on the daily development
server, without a formal production release. The earlier blanket note that no database, profile or credential
may be created is superseded for this server only. The concrete target identity, recovery conditions and
governed entries still have to be established first, and demo and control duties must not gain cross-model
writes to reach a terminal state.

### Status

Mechanism acceptance for step 1 (identity, tenant topology and routing) is complete at this stage identity.
The routing entry reports one genuine FAIL: a duplicate postmaster on the shared cluster volume. Code
integration, daily deployment, full mechanism acceptance and product acceptance all remain open, and no delivery
conclusion is claimed. Next: resolve the duplicate-postmaster decision with the owner, then bind role, exact
filter, filestore and tenant key for the three duties and build the governed provisioning entry the closure
needs before creating only the missing customer development database.

### Step 2 identity binding (policy section 11 preparation, read-only)

Section 11 forbids a database write until the target role, exact filter, filestore and tenant are
resolved, so each duty's identity was bound from declarations plus observed runtime facts before any write.

Declared sources read: policy section 2 declares `PLATFORM_CONTROL_DATABASE=sc_platform_control`;
`docs/adr/ADR-001-single-database-colocated-platform-core.md` records the historical single-runtime
colocation and policy section 1 keeps it valid only for existing environments, requiring a separate
migration task to leave it; `addons/smart_core/core/platform_database_contract.py` resolves the platform
database from `ir.config_parameter smart_core.platform_release_db` and safely colocates with the current
database on non-production when unset; `frontend/apps/web/src/services/dbContext.ts` plus
`scripts/verify/daily_dev_acceptance_env_guard.py` bind the platform-admin entry to
`VITE_PLATFORM_ADMIN_DB=sc_platform_core`; and
`addons/smart_core/data/tenant/database_strategy.v1.json` is the single strategy declaration.

Duty bindings as observed:

- Platform control duty: not a functioning control plane. `sc_platform_core` exists (64 modules,
  `smart_core` 17.0.1.0, no `sc.tenant.company.registration` table, no business rows) but no instance serves
  it, so the platform-admin entry cannot resolve. The policy-declared `sc_platform_control` does not exist.
- Demo duty: `sc_demo` served by `sc-backend-odoo-dev-odoo-1` with exact filter `^sc_demo$`; the governed
  onboarding plan declares role `platform_internal_demo`, `tenant_key sc-demo-main` and registered companies
  1 (demo) / 21 / 22 (test). It also carries the customer tenant volume, so the duty is not yet pure.
- Customer development duty: unbound. A baosheng tenant database does exist
  (`sc_tenant_baosheng_uat_core035_20260727142732_46a327`) but on a **separate cluster**
  (`system_identifier 7667092793767399462`) served by its own stack, at older revisions (`smart_core`
  17.0.1.1.1, `sce_customer_baosheng` 17.0.2.3.0, no registration table). Policy section 7 requires
  dev/uat/prod separation, so that UAT database cannot be the customer development environment; a new one
  has to be created.
- Unbound leftovers: `sc_odoo` and `sc_platform_core` have no serving instance, and the only login role is
  the superuser/createdb role `odoo`, so policy section 6's independent tenant role and filestore do not
  exist yet.

Reusable mechanisms already in the repository, so the closure reuses rather than reinvents:
`make daily.runtime.data_space.onboard` (`.plan`) is already parameterised by `--database/--role/--tenant-key`
and is the per-database onboarding entry for all three duties;
`scripts/ops/platform_database_lifecycle_apply.py` already implements
`provision/activate/suspend/resume/retire/abandon` with fail-closed connection effects, one audit row per
operation and a control-plane cutoff refusal, but its governed runtime binding (profile wrapper plus the
`PLATFORM_DATABASE_MAINTENANCE_CONFIG` identity for the daily cluster) is still pending, so no governed entry
can yet create or suspend a daily database; `make platform.database.rehearsal.*` provisions only isolated
rehearsal databases; and the core035 daily stack plus
`docs/audit/um_p3/um_p3_core_035_s07a_environment_handoff_v1.json` is the reusable shape for an isolated
per-tenant environment (dedicated project, own volumes, expiry, exact destroy policy).

### Step 2 duplicate-postmaster confirmation (read-only)

The routing entry's single FAIL was re-confirmed directly rather than taken on trust. Both containers report
inode `935335` for `/var/lib/postgresql/data/global/pg_control` with identical md5
`cd5d0e6b1a307cc5c992c936315ae1d9`, and identical `postmaster.pid`. They are nevertheless two separate
cluster owners: `pg_postmaster_start_time()` is 2026-09-24 08:28:55 in the dev container and 2026-09-18
09:48:20 in the prod container, each runs its own postgres with checkpointer and walwriter, and
`pg_current_wal_lsn()` has diverged (dev `5D/24BFEB68`, prod `48/CF3ADD8`). The dev application container
resolves service `db` to `192.168.32.2` and its database container shows three remote clients, while the prod
database container shows only local backends, so the prod container has no application consumer.

The orphan still owns the same data directory, so a restart, crash recovery or shutdown checkpoint from it
would run against a stale control file. That is an environment mutation, not a code defect, and no governed
entry provides it, so it stays a blocker. The recommended ruling is to stop and disable only the leftover
`sc-backend-odoo-prod` db/redis pair, leaving `sc-backend-odoo-dev-db-1` as the single postmaster of
`sc_dev_db_data`.

### Status

No database was created, suspended or retired, no container was stopped, and no credential was created or
persisted; only container metadata, catalog facts and repository declarations were read. Three owner rulings
are now the gate for the write phase: the platform control duty target, the customer development environment's
exact identity, and the duplicate-postmaster cleanup. After that the governed runtime binding for
`platform_database_lifecycle_apply.py` is built, each duty's section 11 table is bound, and only the missing
database(s) are created through the governed entry.

## Owner ruling and Step A: governed retirement of the leftover stack

### Owner ruling 2026-10-15 (authority for this round)

Dispose of the shared-PGDATA two-instance risk **before** continuing the three-database build; existing
passing tests cannot cover a runtime risk. The three previously open decisions are now ruled:

1. **Platform control duty — create a new `sc_platform_control`.** Do not edit the policy to reuse the
   colocated database. Independent role, credential, filestore, session space and exact route; only
   control-plane dependencies; no customer business content. `sc_platform_core` stays a to-be-disposed
   historical asset — not deleted, not migrated automatically. `VITE_PLATFORM_ADMIN_DB`, the acceptance
   declarations and the guards must move to the new authoritative binding **in one change**, never as two
   drifting dialects.
2. **Customer development environment identity** (registered as a pending build, not created):
   tenant `baosheng`, environment `dev`, database `sc_tenant_baosheng_dev`, application role
   `sc_tenant_baosheng_dev_app` (independent credential, no cluster management rights), exact filter
   `^sc_tenant_baosheng_dev$` with database enumeration off, compose project `sc-tenant-baosheng-dev`, and a
   dedicated filestore/session/backup namespace. The existing UAT database stays independent: it must not be
   renamed into the development database, and the ruling grants **no authority to copy its data**.
3. **Legacy db/redis retirement is approved, the plain `docker stop` approach is not.** Immediate and fast
   shutdown differ in what they write and how they recover, so a routine stop is not a risk-free operation
   while two instances share one directory. The stop method must follow the reviewed PostgreSQL version,
   process topology and container stop signal.

Not granted: approval of any un-reviewed low-level stop command, and any authority to stop a real production
service — if the recheck found a production consumer the disposal path would have stopped and reported.
The executor's order becomes: double-writer disposal → data health and recovery verification → three-database
identity registration and build → user-module migration → unified onboarding and isolation verification →
product acceptance.

### Step A — the governed retirement entry

The disposal is a P4 mutation with its own entry, not an ad-hoc command:
`make daily.runtime.legacy_stack.retire.{plan,apply}` plus `make verify.daily.runtime.legacy_stack.retire`,
declared in `config/ops/daily_runtime_retired_stacks.v1.json` (the same declaration the routing inventory
now consumes through `--retired-stacks`). The plan is read-only; `apply` additionally requires the exact
confirmation token **and** the digest of the reviewed plan, so only the reviewed commands execute.

The reviewed stop method follows the ruling instead of `docker stop`:

| Container kind | Method | Why not the natural command |
|---|---|---|
| postgres | `docker kill --signal=SIGQUIT` — documented **Immediate Shutdown** | `docker stop` sends the container's `StopSignal`, and both database containers declare `SIGINT`, which PostgreSQL documents as **Fast Shutdown**: the orphan would write a shutdown checkpoint into the WAL the surviving live postmaster is using |
| redis | `docker kill` (SIGKILL) | a graceful Redis shutdown performs RDB/AOF persistence work inside the shared volume |

Applied (plan digest `95d44e1a704b58df064087961bdbdb9fbc1f5ab860b56cc6a5bbf0cb390f164b`):
`docker update --restart=no` on all four containers, then `docker kill --signal=SIGQUIT
sc-backend-odoo-prod-db-1` (exit 0; log `received immediate shutdown request ... database system is shut
down`) and `docker kill sc-backend-odoo-prod-redis-1` (exit 137). Evidence was frozen on the host **before**
the first state change at `/opt/projects/backups/daily-runtime-legacy-retire/20261015T065842Z` (26 files plus
`manifest.json` with hashes: container inspect, logs, volume inspect, data-directory stat/find, compose
content, survivor probes). The legacy `docker-compose.yml` was renamed to
`docker-compose.yml.retired-20261015T065842Z` (reviewed sha256 `d6e72b6b4c1f…`).

Nothing was destroyed: no container, volume or WAL file was removed and `pg_resetwal` was not run. After the
change `prod-db-1` is `exited 0`, `prod-redis-1` is `exited 137`, and `prod-odoo-1`/`prod-nginx-1` remain
`created` (they had never been started); every retired container now has restart policy `no`.

### Step A — guard post-condition defect found and fixed

Re-running the read-only plan after the retirement **blocked**, which is a defect in the entry rather than a
new risk: `declared_postgres_is_not_the_newest_writer` needed two distinct writer start times to compare, but
the stopped orphan contributes no cluster facts, so only the survivor remained and comparability could not
hold. The guard now also accepts its literal post-condition — the declared postmaster is not running and is
not reported as a writer, while **every other owner of the shared cluster is live and reported** — and still
refuses when the survivor's facts are unreadable, so "already retired" can never be read from an unreachable
survivor. Two tests were added (20 in total); no assertion was removed. The plan now reports `status PLAN`
with `failing_guards []`, leaving only the four idempotent `remove_automatic_restart_path` steps.

### Step A — verification and anti-recurrence readback

| Check | Result |
|---|---|
| `make verify.daily.runtime.legacy_stack.retire` | 20 tests, OK (nonzero) |
| `make verify.daily.runtime.routing.inventory` | 17 tests, OK (nonzero) |
| `make daily.runtime.legacy_stack.retire.plan` | `PLAN`, `failing_guards []`, digest `534c710a27c034…` |
| `make daily.runtime.routing.inventory DAILY_RUNTIME_EXPECTED_SHA=10bf72ef…` | `PASS`, 0 failed assertions, `remote_head 10bf72ef…` |
| key assertions | `one_live_postmaster_per_cluster_data_volume` PASS · `retired_stack_is_not_running` PASS (`running_retired []`) · `single_serving_instance_per_database` PASS · `instance_data_volume_distinct` PASS · `inventory_is_read_only` PASS |
| anti-recurrence (host readback) | four retired containers `restart=no`; live postmaster owners of `sc_dev_db_data` = `[sc-backend-odoo-dev-db-1]`; no `docker-compose.yml` in the legacy checkout; no systemd unit or cron entry references it |

These are iteration-stage runtime observations, not a frozen candidate or a Quick receipt.

### Step A — the retirement itself executed one cross-instance write

The disposal removed the shared writer, but it also proved why the owner refused a routine stop: immediately
after the orphan shut down, the **surviving** `sc-backend-odoo-dev-db-1` restarted once
(`restarts=1`, `started_at 2026-10-15T06:58:46Z`, exit 0, healthy):

```
06:58:46.217 [1] LOG: could not open file "postmaster.pid": No such file or directory
06:58:46.217 [1] LOG: performing immediate shutdown because data directory lock file is invalid
06:58:46.851 [1] LOG: starting PostgreSQL 15.17 ... database system was interrupted; last known up at 2026-10-15 06:24:28 UTC
06:58:47.875 [29] LOG: database system was not properly shut down; automatic recovery in progress
06:58:47.891 [29] LOG: redo starts at 5D/24BFEA80 ... redo done at 5D/24BFEB30
06:58:47.910 [27] LOG: checkpoint starting: end-of-recovery immediate wait ... checkpoint complete ... distance=0 kB
06:58:47.924 [1] LOG: database system is ready to accept connections
```

Both postmasters shared one `postmaster.pid` inside the shared PGDATA; when the orphan exited it removed or
replaced that file, the survivor found its lock file invalid, self-terminated with an immediate shutdown and
restarted, performing one crash recovery plus an end-of-recovery checkpoint on the shared directory.

The survivor is up (`pg_is_in_recovery()=f`, `pg_postmaster_start_time() 2026-10-15 06:58:46.865829+00`,
live LSN `5D/24BFEC18`, `select 1` → 1), but its **data health is not assumed**. Step B must verify the error
log, readability, applicable consistency checks and a restore drill before any database write, and must state
explicitly whether the double-write window left damage.

### Status

批次状态：Step A（双实例风险处置）已完成并复核——退役经受管入口执行、证据冻结、随后置守卫通过、
防复发路径已清除；退役期间幸存实例发生的一次崩溃恢复已取证并登记为 Step B 的首要输入。**尚未**完成
Step B（数据健康与恢复验证），因此三库建设、用户模块迁移、统一入驻与产品验收均未开始，本批次不构成
主线集成完成或产品交付完成。

### Step B — data health and recovery verification of the surviving cluster

Step B exists because the retirement itself executed one crash recovery against the shared data directory, so
the survivor's health could not be assumed. Every probe below is read-only except the governed isolated
restore drill, which runs in temporary resources and never touches the live cluster.

**Cluster identity.** `system_identifier 7597381856873586726` (unchanged), PostgreSQL 15.17, live
`database.uuid = c838b4b6-4cd6-11f1-9590-82245e4e7b62` — equal to the value recorded in the pre-incident
recovery-point manifest and the sentinel contract. `pg_postmaster_start_time()` stays
`2026-10-15 06:58:46.865829+00` and `RestartCount` stays 1 across every probe, so nothing restarted again.
`pg_control_checkpoint` shows the 06:58:47 end-of-recovery checkpoint and `pg_control_recovery` reports no
recovery in progress. Settings: `data_checksums=off`, `fsync=on`, `full_page_writes=on`, `wal_level=replica`,
`archive_mode=off`, `logging_collector=off`, `log_destination=stderr`.

**Error-log review.** The container's whole log (54,271 lines / 41.7 MB, from the 2026-09-24 start through
the 06:58:47 ready line) contains **zero** PANIC, corruption, invalid page/block, WAL write/fsync/rename
error, disk-full, out-of-memory or terminated-server-process entries. Exactly one crash recovery exists in
the entire history — the 06:58:46 one caused by this retirement — and the
`invalid record length at 5D/24BFEB68: wanted 24, got 0` line is the normal end-of-WAL marker that terminates
redo, not damage. The 10 `FATAL` and 50 `does not exist` matches are connection-level noise from other
profiles (`odoo`, `sc_dev_demo`, `sc_dev_sample`, `sc_clean`, roles `sc_demo_odoo`/`postgres`, unrelated
relations); the 48 `checksum` matches are false positives on the `sc_ui_base_contract_asset.asset_hash`
column. Limitation: `log_destination=stderr` with `logging_collector=off` means history lives only in the
docker json-file driver, currently complete for this container's lifetime.

**Readability — full logical read of every database.** `pg_dump -Fc` of each database, streamed to `wc -c`
and discarded: `sc_demo` **650,398,584 bytes in 102.2 s**, `sc_odoo` 1,073,795 bytes, `sc_platform_core`
5,152,782 bytes, all exit 0 with **zero stderr bytes**. Every heap and TOAST page was read back without a
single read or consistency error, and the `sc_demo` dump size is *byte-identical* to the 650398584 bytes the
pre-incident recovery-point manifest recorded at 06:22:24Z.

**Sentinel comparison against the pre-incident recovery point.** The recovery point
`sc_demo-20261015T062043Z-849c0c54` was captured 36 minutes **before** the crash recovery, so its recorded
table counts are a pre-incident snapshot. Live counts are equal in every sentinel table:
`res_company 4=4`, `res_users 140=140`, `project_project 931=931`, `construction_contract 12677=12677`,
`payment_request 34913=34913`, `ir_attachment 609394=609394`, `ir_module_module 704=704` — no decrease
anywhere.

**Recovery capability.** `make daily.candidate.continuity.remote_restore_drill
DAILY_CANDIDATE_SSH_HOST=sc-root
DAILY_CONTINUITY_BACKUP_DIR=/data/backups/daily_candidate/sc_demo-20261015T062043Z-849c0c54` re-passed with
`isolated_restore_pass`, `database_restore_pass`, `filestore_restore_pass` and `sentinel_comparison_pass`
all true, `temporary_resources_removed: true`, `network_egress: internal_only`, 295 s. The entry validates
the manifest, artifacts and checksums before restoring, so this also re-proves the recovery point's own
integrity. Post-drill readback: no container, volume or network carries the `sc.daily-continuity` label, and
the live cluster is untouched.

**Declared gaps (carried forward, not hidden).**

- `data_checksums=off`, so `pg_stat_database.checksum_failures` has no value and there is no page-checksum
  evidence; enabling checksums requires an offline cluster rewrite and is out of scope.
- Index-structure verification through `amcheck` requires installing the `amcheck` extension inside the
  business database, i.e. a schema write to `sc_demo`; it was deliberately not performed, so index
  verification is limited to the access paths the dump and sentinel comparisons exercise.
- The 2026-09-18 → 2026-10-15 double-write window cannot be replayed page by page; the verdict rests on the
  absent corruption errors plus the three independent read-side results.
- The governed continuity contract is bound to `sc_demo` alone; `sc_odoo` and `sc_platform_core` still have
  no paired recovery point, which remains a precondition for the first write to them.

**Verdict: PASS.** No evidence of damage from the double-write window or the recovery. The survivor is
readable, identity-stable and restorable, and the Step B gate that blocked database writes is released for
the already-covered duty, with the declared gaps carried into Step C.

### Status

批次状态：Step A（双实例风险处置）与 Step B（数据健康与恢复验证）均已完成并留有可复核证据；Step B 判定
PASS，阻断数据库写入的门已解除（仅对已覆盖恢复点的职责）。三库身份登记与建设（Step C）尚未开始——其
前置是 `platform_database_lifecycle_apply.py` 的受管运行时绑定与每库政策第 11 节判定表。本批次仍不构成
主线集成完成或产品交付完成。

## Step C — three-database identity registration and build

### The owner ruling this step executes

The owner ruled that the daily development server separates three duties: a platform control database, the demo
database and one customer development business database, with the same onboarding mechanism for demo and
customer tenants. The owner explicitly selected a **new** `sc_platform_control` rather than reusing
`sc_platform_core`, named the customer development database `sc_tenant_baosheng_dev`, and required
`VITE_PLATFORM_ADMIN_DB`, the acceptance declarations and the guards to consume the new binding **in one
change** — never as two dialects. The UAT database stays independent and the ruling grants no authority to copy
its data. No formal production release is authorized here; ADR-001 and the production single-database topology
stay in force.

### The duty declaration is the authority, and a missing value is a stop

`config/ops/daily_runtime_database_duties.v1.json` declares one duty per line: a role, a database, an exact
anchored filter, an environment, a compose project, a data volume, a storage namespace and one route, plus the
policy section 11 determination table that must exist before the first write. `scripts/ops/daily_runtime_duty_stack.yml`
renders one stack shape for all three duties, and
`scripts/ops/daily_runtime_database_duty.py` (Make: `verify.daily.runtime.database.duty`,
`daily.runtime.database.duty.plan`, `daily.runtime.database.duty.apply`) is the only entry that may create one.

The design keeps two properties from the 2026-10-15 incident from being reintroduced:

- the cluster bootstrap role and the application role are **different identities** (`POSTGRES_USER` is the
  maintenance role; Odoo connects as the separate application role), because a cluster whose bootstrap superuser
  is also the application role can never satisfy policy section 6;
- every duty names its own volumes, so one data directory has exactly one writer and two postmasters can never
  mount the same PGDATA.

Every rendered environment value is read back and compared with the declaration, and a missing value is a
fail-closed stop rather than a fallback: a silent fallback is exactly how one database ends up served by another
duty's environment. A duty declared `to_be_created` is the only shape the entry may mutate; an existing duty is
observed and never re-rendered or restarted.

### Step C-1 — `sc_platform_control` created

| Fact | Observed |
|---|---|
| compose project / container | `sc-platform-control-dev` / `sc-platform-control-dev-db-1` |
| data volume | `sc_platform_control_db_data` (`/var/lib/docker/volumes/sc_platform_control_db_data/_data`) |
| cluster system identifier | `7696799124996268070` |
| application role | `sc_platform_control_app` — LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE |
| database | `sc_platform_control`, owner `sc_platform_control_app`, UTF8 from `template0` |
| privileges | `REVOKE CONNECT ... FROM PUBLIC`; CONNECT granted only to the application role |
| stored settings | `ODOO_DBFILTER=^sc_platform_control$`, `LIST_DB=false`, `NGINX_PORT=18082`, `ODOO_PORT=18083` |

Receipt: `.runtime/final-acceptance/daily-deployed/database-duty-apply-platform_control.json`
(declaration digest `c4afe125…`, apply plan digest `51ffaea3…`, compose `1a5ca02d…`). An out-of-band read-only
probe — not the entry's own report — re-read the container labels, mount, `datacl` (`PUBLIC` holds TEMP but not
CONNECT), `pg_roles` attributes and the application role's ability to connect, and agreed on every point.

Only the `db` service of this duty stack was started (by design). `sc_platform_control` is **not** initialized:
it carries no module and no tenant registry, and no Odoo instance serves it, so it cannot serve the
platform-admin entry yet.

### Step C-2 — `sc_tenant_baosheng_dev` created

| Fact | Observed |
|---|---|
| compose project / container | `sc-tenant-baosheng-dev` / `sc-tenant-baosheng-dev-db-1` |
| data volume | `sc_tenant_baosheng_dev_db_data` |
| cluster system identifier | `7696799327921901606` |
| application role | `sc_tenant_baosheng_dev_app` — LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE |
| database | `sc_tenant_baosheng_dev`, owner `sc_tenant_baosheng_dev_app` |
| privileges | `REVOKE CONNECT ... FROM PUBLIC`; CONNECT granted only to the application role |
| stored settings | `ODOO_DBFILTER=^sc_tenant_baosheng_dev$`, `LIST_DB=false`, `NGINX_PORT=18090`, `ODOO_PORT=18091` |
| storage namespace | filestore `sc_tenant_baosheng_dev`, session `sc_tenant_baosheng_dev`, backup `/data/backups/daily-tenant-baosheng-dev` |

Receipt: `.runtime/final-acceptance/daily-deployed/database-duty-apply-customer_tenant_dev.json`
(apply plan digest `a6bd0df2…`). The existing UAT database was not read, renamed or copied: this duty was
created empty and its customer addon root is still the empty runtime addon root, so no customer module is
installed here yet.

`make daily.runtime.routing.inventory` was re-run after both clusters were added and still passes host-wide:
`one_live_postmaster_per_cluster_data_volume`, `instance_data_volume_distinct`,
`single_serving_instance_per_database`, `published_host_port_unique` and `retired_stack_is_not_running` are all
true across 6 instances, and `sc_odoo` / `sc_platform_core` remain the declared unserved databases.

### Step C-3 (partial) — the platform-admin binding is now checked, and the drift is reported not hidden

`VITE_PLATFORM_ADMIN_DB` is a frontend **build-time** value: the duty nginx, the Odoo process and the browser
never read it. Rendering it into a duty env file would have created a decorative second copy of the platform-admin
authority that can silently disagree with the bundle users actually load. The entry therefore reads the file the
frontend build consumed (`frontend_build_env_file`, `/opt/projects/repos/sce-product-odoo/.env.dev`) and reports it
as a **deployment-wide** fact, judged by its own verdict
`frontend_build_env_names_the_declared_platform_admin_database`. It is deliberately *not* a per-duty assertion, so
a duty created exactly as declared is never reported as a failed creation because an explicitly sequenced switch
is still pending.

The real state is therefore visible rather than smoothed over: the duty plan is **FAIL** with every duty showing
**zero failed assertions**, and the single failing item is

```
declared: sc_platform_control
observed: sc_platform_core   (/opt/projects/repos/sce-product-odoo/.env.dev)
```

The switch has deliberately **not** been executed, and no two dialects exist today: the host build input and
`scripts/verify/daily_dev_acceptance_env_guard.py` both still read `sc_platform_core`, so repository and host
agree, and the disagreement is between the ruled target and the current declaration — reported as a FAIL.

Two reasons the switch waits:

1. It must move the build input, the acceptance declaration and the guards **in one change**, and only the
   governed frontend build entry rebuilds the served bundle. Flipping the input while the served artifact still
   inlines the old value would recreate exactly the two-dialect state the owner forbade.
2. `sc_platform_control` carries no module yet, so it cannot serve the platform-admin entry; the bundle rebuild
   is what actually moves that entry, and it should move onto a control plane that can answer.

### Status

批次状态：Step A（遗留栈受管退役）、Step B（幸存集群数据健康与恢复验证）与 Step C 的三库身份登记与建设
已完成到「职责已按声明建成并留证」的程度：`sc_platform_control` 与 `sc_tenant_baosheng_dev` 各自拥有独立
集群、独立数据卷、独立应用角色、精确 filter、独立路由与存储命名空间，且都通过受管 plan/apply 回执加一次
带外只读复核确认。`demo` 职责仍按声明的 gap（共享 bootstrap 角色）如实描述，duty 入口不会渲染或重启它。

仍未关闭：控制面尚未初始化（`sc_platform_control` 无模块、无租户登记、无服务实例）；平台管理面权威绑定
仍需「一次改动」切换到 `sc_platform_control` 并重建已服务的打包产物，切换前 duty plan 会如实 FAIL 在
这一项上；三库均未做生命周期登记；用户业务库尚未安装产品线与用户模块、尚未执行受管迁移。本批次仍不
构成主线集成完成、版本发布完成或产品交付完成。

### Step C-4 — the created duties are written back into the declaration

The declaration is the authority this entry judges the world against, so a duty that now exists must
say so. Right after the two duties were created the declaration still carried
`custody.role_compliance=to_be_created` with `database_present=false`, which the entry itself
describes as a shape that is legitimate *only until the observed facts are written back*. Left
unwritten it is stale in the dangerous direction: the next `--apply` would try to create a duty that
is already serving, and the read-only plan would report the world as disagreeing with a declaration
nobody had updated.

The values written back are the apply receipts' own observations, not values re-queried or invented:

| Duty | `role_compliance` | `database_present` | `database_role_present` | `cluster.system_identifier` |
|---|---|---|---|---|
| `platform_control` | `compliant` | true | true | `7696799124996268070` |
| `customer_tenant_dev` | `compliant` | true | true | `7696799327921901606` |
| `demo` | `declared_gap` (unchanged) | true | true | `7597381856873586726` |

The `demo` duty is deliberately left as a declared gap: the shared bootstrap role really is still a
superuser that can create databases, and the entry's `declared_gap_is_still_open` assertion fails if
that stops being true.

This exposed a test defect worth naming: eight decision-layer tests and the `observation_matching`
helper read the shipped declaration and assumed it still contained a `to_be_created` duty, so the
write-back broke them for the wrong reason — they were testing the shipped file's transient state
rather than the creation path. They now ask for that state explicitly through `prospective()`, and
`observation_matching()` models all three declared shapes. No assertion was weakened or removed.
Two invariants were added instead:

* a duty whose cluster identity is already recorded may not still be declared `to_be_created`;
* a `compliant` duty must declare its database and its role present.

Test count `55 -> 57`, all green.

Re-running the read-only plan against the host now reports exactly one failing item:

```
status: FAIL
platform_control     failed_assertions: []   declared_custody: compliant
demo                 failed_assertions: []   declared_custody: declared_gap
customer_tenant_dev  failed_assertions: []   declared_custody: compliant
declared: sc_platform_control
observed: sc_platform_core   (/opt/projects/repos/sce-product-odoo/.env.dev)
```

This is a `FAIL` on purpose and is not smoothed over. The platform-admin binding is deliberately not
switched yet: `sc_platform_control` still carries no module, no tenant registry and no served Odoo
instance, so the served bundle would name a control plane that cannot answer. The switch moves the
build input, the acceptance declaration and the guards in one change and is sequenced after the
control plane can serve — which needs a governed entry that starts a duty's `odoo`/`redis`/`nginx`
services and installs **its declared** control-plane minimum module set. That module set is a
product/governance decision, so it gets declared rather than improvised by an ops tool.

### Step C-5 — the control plane is initialized, and the platform-admin authority moves with it

Step C-4 left exactly one failing item on purpose: the deployment-wide platform-admin binding. It
could not be switched before the control plane could answer, and the control plane could not answer
before a governed entry could bring up its application face and install its declared module set. That
entry now exists as `make daily.runtime.database.duty.initialize` (`--phase initialize`), and it is the
only phase allowed to touch a duty that already exists.

Two real defects were found by running it, and both are the kind that report a partial write as no
write at all:

**A — the entry waited for a consequence of the step that had not run yet.** It brought up
`db redis odoo nginx` in one `up -d --wait`. The application's health means "the route answers", and an
uninitialized duty's route cannot answer, so the wait could never be satisfied: the initialization was
being used as its own precondition. The first host run timed out at 300s and the payload was lost to an
uncaught `TimeoutExpired`. The entry now starts the declared services in the order their own facts
allow (cluster waited for, application started, declared modules installed, route last) and reads a
duty that raised back instead of dropping it, so one failing duty cannot hide a later one.

**B — the duty owned its database and still could not initialize it.** The application role owned
`sc_platform_control` and was refused `CREATE TABLE public.…`. On this PostgreSQL 15 cluster `public`
is owned by `pg_database_owner`, and `has_schema_privilege(sc_platform_control_app,'public','CREATE')`
measured **false**; every other custody fact reported the duty as healthy. The entry now states the
application's access explicitly instead of relying on a mechanism it cannot observe, re-asserts it
before installing, reads the privilege back for the duty's own database, and **fails closed** on
`application_role_can_create_in_its_public_schema` for any served face.

Result of the governed initialize:

```
phase                 initialize
duty                  platform_control   failed_assertions: []
initialize.returncode 0
route.returncode      0
modules               smart_core -> installed
running services      db, nginx, odoo, redis
installed industry    []            (platform_control_face_carries_no_industry_module)
public_schema_create  true
```

The overall receipt status is `FAIL` **only** because the deployment-wide binding was still on the old
database at that instant. That binding was then switched in one change — the served build input, the
acceptance guard, the sample-env prepare and the topology inventory all now name `sc_platform_control`
— and the governed frontend build was extended so it cannot lie about it: it derives the declared
database from the same duty declaration, writes that build input **before** the build (afterwards would
leave the new authority declared while the old bundle is served), reads back that the built artifact
actually **bakes** it, and rolls the declaration back if the build or the readback fails.

```
make daily.runtime.frontend.build
  platform_admin_written  true
  platform_admin_baked    true
  fingerprint             23e9f516c4f415428075eec70ddc457ebb7193dc8aff63a26d103a3df73bad22
  entry_asset             index-CBpDOhLc.js

make daily.runtime.database.duty.plan
  status                  PASS
  declaration_digest      52ac5ad164594e4d4231c715e4cbcfa76dce953670b3fce31851dbcd91d7c2ab
  platform_control        failed_assertions: []
  demo                    failed_assertions: []
  customer_tenant_dev     failed_assertions: []
  binding                 sc_platform_control observed == declared

make daily.runtime.routing.inventory
  status PASS   failed_assertions []   instances 7
```

The declaration write-back that followed records the observed face, not a guess:
`platform_control.custody.service_face` is now `initialized`, while `customer_tenant_dev` stays
deliberately `cluster_only` with a reason — its product line and user module belong to the customer
module's own governed migration, not to this entry.

Test count `82 -> 84` for the duty entry and `10 -> 21` for the frontend build entry, all green. The
two new duty tests assert the one thing the old readback could not see: a served face whose application
cannot create in its own `public` schema fails closed, and a cluster-only face is never asked for one.

Not closed by this step: no duty has a platform-model lifecycle registration yet (the platform model
owns registration and the lifecycle adapter still lacks a daily runtime binding); the customer
development duty carries no product line, no user module and no migration; `sc_demo` still mixes the
customer tenant volume with demo/test purposes; the three Step B gaps remain preconditions for the
first write to `sc_odoo` or `sc_platform_core`. **This is 批次验收完成 for the control-plane slice. It is
not 主线集成完成, 版本发布完成 or 产品交付完成.**

## Step D — delivering the customer module tree, and the gap that made it necessary

### The gap Step C left standing

`config/ops/daily_runtime_database_duties.v1.json` declares a `customer_addons_root` for the customer
tenant duty, and the whole repository carried **no governed entry that could put a customer tree on the
daily host**. The tree is P2 content owned by the customer delivery repository, so populating it from
`/opt/projects/repos/sce-product-odoo` would make the product repo the owner of customer content. Step
C-5 therefore wrote the duty back as `cluster_only` *on purpose*: a served face needs a reviewed
module source, and no reviewed source existed.

### The entry

`scripts/ops/daily_runtime_tenant_addons_deliver.py` delivers **one exact customer commit's** `addons/`
tree into `/opt/sce/tenant-addons/daily/<commit>`. It is the daily sibling of the already-registered
`/opt/sce/tenant-addons/acceptance` namespace and keeps the same shape: one directory per exact
commit, carrying a `TENANT_SHA` marker, read-only.

Three properties are fail-closed rather than best-effort:

- **Exact source.** The source must be one commit of a *clean* worktree. A branch name, a dirty tree or
  an unreadable commit is a stop, because "what we installed" has to survive as an identity that can be
  rebuilt later.
- **Write-once, content-addressed.** A destination that already carries the same marker and content is
  an idempotent no-op (`writes: 0`); a destination with a different identity is a stop, never an
  overwrite, so a released tree cannot be silently replaced under a duty already serving from it.
- **One digest implementation.** The tree digest computed inside the destination must equal the digest
  of the archive that was sent, and both sides run the *same* reviewed implementation
  (`TREE_DIGEST_SOURCE`), so "the host has the reviewed tree" is a measurement, not an assumption. It
  ignores `__pycache__`, `*.pyc` and the `TENANT_SHA` marker itself.

`make/codex.mk` carries three entries: `verify.daily.runtime.tenant.addons` (py_compile + unit tests),
`daily.runtime.tenant.addons.plan` (read-only) and `daily.runtime.tenant.addons.deliver` (`--apply`,
guarded by `SC_CONFIRM_DAILY_RUNTIME_TENANT_ADDONS=DELIVER_EXACT_DAILY_RUNTIME_TENANT_ADDONS`).

### The delivery

```
SC_CONFIRM_DAILY_RUNTIME_TENANT_ADDONS=DELIVER_EXACT_DAILY_RUNTIME_TENANT_ADDONS \
make daily.runtime.tenant.addons.deliver \
  DAILY_RUNTIME_TENANT_CUSTOMER_REPOSITORY=/home/lidefend/workspace/sce-customer-baosheng-odoo \
  DAILY_RUNTIME_TENANT_SHA=bfbc736c51d987777b50c465261ece1d8d22f008
```

```
PASS  mode=apply
path    /opt/sce/tenant-addons/daily/bfbc736c51d987777b50c465261ece1d8d22f008
digest  e0a3210da88ea49b1af16d6c037081289a97a39f7fb602d67192c25bf67dd7a6
modules sce_customer_baosheng
        sce_customer_baosheng_core035_mvp
        sce_customer_baosheng_history_attachments
        sce_customer_baosheng_legacy
```

A read-only `plan` against the same commit now reports `PASS` with the same digest and the same four
modules, and the destination's writable-path set is empty. The `plan` run against `40b67f99…` earlier
was a report-layer readback of a *different* tree and never wrote anything.

Unit verification: `make verify.daily.runtime.tenant.addons` — **21 tests OK** (source validation,
archive module set, digest ignore/change, the remote program reusing the same digest implementation,
six verdict counter-examples, and the command layer).

### What this does **not** close

The delivered tree is a **source identity only**. The customer duty is still `cluster_only`: no product
line, no customer user module and no governed migration have run. `sc_demo` still mixes the customer
tenant volume with demo/test purposes, no duty has a platform-model lifecycle registration, and the
Step B gaps remain preconditions for the first write to `sc_odoo` or `sc_platform_core`.

**This is 批次验收完成 for the tenant-addons delivery slice. It is not 主线集成完成, 版本发布完成 or
产品交付完成.**

## Step D — the customer duty's initialization failed, and the defect that caused it

The first `--phase initialize` for `customer_tenant_dev` **failed** (`initialize.returncode = 255`):

```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "pg_type_typname_nsp_index"
DETAIL:  Key (typname, typnamespace)=(ir_actions, 2200) already exists.
```

### Root cause: two initializers in one fresh database

`scripts/odoo-entrypoint.sh` makes the application container its own initializer: when
`public.ir_module_module` is absent or `base` is not installed, it runs
`odoo -i base --without-demo=all --stop-after-init` and only then `exec`s the server. The duty entry,
however, started the application with a plain `up -d` (deliberately: the application's health is a
*consequence* of the declared module set, so waiting for it before installing would wait forever) and
then immediately ran `docker exec <odoo> odoo -i <declared modules>`.

So both processes built the Odoo base schema in the same database at the same time. The duty was left
**half initialized**: `ir_module_module` existed with 677 rows, `base` was `uninstalled`, every declared
module was `uninstalled`, and `public` carried 200 types and 399 relations of partial DDL.

### Fix: one initializer at a time, and prove it

`await_base_bootstrap(duty)` now runs between `start_services` and `install_modules`:

* it waits for the container's **own** bootstrap to finish, read back from the cluster
  (`ir_module_module` → `base` state) and from *this startup's* log statements (everything after the
  last `[entrypoint] render odoo.conf` line, so a restart is never mistaken for a finished attempt);
* a finished attempt that did **not** install `base` is retried **once** by restarting the container —
  safe exactly because the previous attempt is over, and refused while one is in flight;
* a second finished failure is reported, not looped, and the entry fails closed.

`install_modules` carries a second, independent guard: it refuses to install into a database whose
`base` is not installed, so a timed-out wait can never hand the duty to the installer anyway.

The wait bound and poll interval travel in the payload (`bootstrap_timeout`, `bootstrap_poll`,
defaults 1800 s / 15 s) so the boundary is exercised by the test suite rather than asserted by reading.
`make verify.daily.runtime.database.duty` — **96 tests OK** (12 new: ordering, in-flight attempts are
never restarted, one restart only, and no install without `base`).

### The retry that closed it (no database was reset)

```
bootstrap.attempts[0]  base_state=uninstalled  entrypoint_finished=true  attempt_failed=true  -> restart
docker restart sc-tenant-baosheng-dev-odoo-1                                          returncode 0
bootstrap.attempts[1]  entrypoint_finished=false                                      -> wait
bootstrap.ready          true                state=installed
initialize               returncode 0        modules installed, registry loaded in 117.220s
route (nginx)            healthy             nginx_host_port 18090
status                   PASS                failed_assertions []
```

Re-running the container's own bootstrap completed the schema the collision had left half built; the
partially initialized database was **repaired in place**. Nothing was dropped, no `pg_resetwal`, no
writedown of a copy taken from a running instance.

Independent read-only readback (not the entry's own report):

```
base_state=installed   declared_installed=11/11   public relations=5455   types=1748
ir_ui_menu=724         res_users=5   res_company=1
ir_config_parameter sc.tenant.bound_tenant_key = baosheng     (the client post_init hook ran)
containers: nginx/odoo/redis/db all running (healthy)         curl :18090/web/login -> 200
odoo log: 0 ERROR/CRITICAL lines in the last 300
second entrypoint run: "base already installed; skip bootstrap"   (the fix, end to end)
```

The declaration's `custody.service_face` was then written back from `to_be_initialized` to
`initialized`, and `make daily.runtime.database.duty.plan` reports **PASS for all three duties**
(`platform_control`, `demo`, `customer_tenant_dev`) with `plan_digest f4b891ed…`.

### What this does **not** close

The duty is now a served, initialized face — **not** a migration. The product line and the customer user
module are installed from the delivered read-only tree, but no historical data has moved: Step D proper
(the customer module's own versioned migration, `historical_payment_migration_policy.expected_records=12386`)
and the Step E/F isolation and product acceptance remain open.

**This is 批次验收完成 for the customer duty initialization slice. It is not 主线集成完成, 版本发布完成 or
产品交付完成.**

## Step D precondition — the customer duty's paired recovery point

### Why this had to come before the migration

The owner ruled that `sc_tenant_baosheng_dev` may not take its first business-data write without a paired
recovery point. The existing data-continuity tool could not provide one: it hard-coded `sc_demo`, its
containers, its volume, its filestore root and its backup root, so the only database it could ever
capture was the demo.

Taking that point by hand-assembling a `pg_dump` plus a `tar` of the filestore was not acceptable:
a recovery point that nothing validates, binds or can restore is not a recovery point, and the repository
rule is that runtime identity has exactly one owner and one governed entry per write.

### The tool now resolves identity from the duty declaration

`scripts/ops/daily_candidate_data_continuity.py` no longer contains any database name, container name,
volume name, role name or backup path. Every runtime identity comes from
`config/ops/daily_runtime_database_duties.v1.json` — the same single authority the duty plan already
consumes:

```
database, database_role, dbfilter, compose_project,
database_container, odoo_container, database_volume, odoo_data_volume,
filestore_scope, backup_root(backup_namespace), environment_id, tenant_key
```

The contract may only carry assertion configuration. If it restates an identity the declaration owns and
the two disagree, the load fails with `identity mismatch: <field>` rather than choosing a winner. Table
and column names for the relationship sentinel are declared too (`relation_sample`), replacing the
hard-coded `payment_request.project_id/contract_id`, and live reads now use the duty's application role
(`sc_tenant_baosheng_dev_app`) while the isolated drill uses the drill's own role.

`scripts/ops/daily_runtime_tenant_recovery_contract_v1.json` is the customer duty's contract, and four
governed entries carry it end to end:

```
make daily.runtime.duty.recovery.remote_baseline
make daily.runtime.duty.recovery.remote_backup           CONFIRM_DAILY_CANDIDATE_BACKUP=BACKUP_DAILY_CANDIDATE_PAIRED_STATE
make daily.runtime.duty.recovery.remote_validate         DAILY_DUTY_RECOVERY_BACKUP_DIR=<dir>
make daily.runtime.duty.recovery.remote_restore_drill    DAILY_DUTY_RECOVERY_BACKUP_DIR=<dir> CONFIRM_DAILY_CANDIDATE_RESTORE_DRILL=RESTORE_ISOLATED_COPY
```

Confirmations are read from the environment, `--backup-dir` must match the duty's directory pattern, and
the remote tool tree is installed from one immutable commit — so the entries refuse a dirty worktree.

### A binding defect was found and fixed before the capture

The new entries named `DAILY_DUTY_RECOVERY_TOOL` as the contract JSON and never passed `--contract`.
That is two defects in one line: `python3 <contract>.json` cannot run at all, and the tool's default
contract is the **demo** one — so the moment someone corrected the program name, the entry would have
silently captured `sc_demo` while reporting success for the customer duty. The variable now names the
tool, `DAILY_DUTY_RECOVERY_CONTRACT_PATH` names the duty contract, all four entries pass `--contract`
explicitly, and a guard asserts both facts so the binding cannot drift again.

### The capture, in order

```
baseline        database_writes=0        database_uuid 30c898b8-c877-11f1-a7d9-4e1f45d0ec9d
                filestore 384 files      content digest 32ccfc95…
                res_company=1 res_users=5 project_project=0 construction_contract=0
                payment_request=0 ir_attachment=461 ir_module_module=677

backup          paired_backup_pass=true  /data/backups/daily-tenant-baosheng-dev/sc_tenant_baosheng_dev-20261015T095006Z-653a3119

validate        backup_status=complete   pair_stable_during_capture=true
                database=pg_restore_list_passed   filestore=tar_list_passed
                database.dump    1d4a6dd8dd099ac0e4deb997f35bf1f0c44cd11140cdb152fb634e26b1cdad1c
                filestore.tar.gz 2830d83d658b21eca57e27142a1d30e89112f9995ebf153c0d474b8ceb0239b5

restore-drill   isolated_restore_pass   database_restore_pass   filestore_restore_pass
                sentinel_comparison_pass temporary_resources_removed=true   29s   network_egress=internal_only
```

Independent read-only readback on the daily host, not the entry's own report:

```
sha256sum -c SHA256SUMS  -> database.dump OK, filestore.tar.gz OK, manifest.json OK
drill residue after the run: 0 containers and 0 volumes matching daily-continuity-drill
backup directory 0700 root:root, every artifact 0600 root:root
```

`payment_request_relation_sample_digest = d41d8cd98f00b204e9800998ecf8427e` is the MD5 of an empty
string: the customer database has no `payment_request` rows yet. The relationship sentinel is legitimately
empty and only `restore-drill` compares it, so the drill still proves the restore matched.

### What this does **not** close

A recovery point is a precondition, not migration. No historical data has moved into
`sc_tenant_baosheng_dev`; the customer module's own versioned migration
(`historical_payment_migration_policy.expected_records=12386`) has not run; Step E isolation verification
and Step F product acceptance are still open.

**This is 批次验收完成 for the customer duty recovery-point slice. It is not 主线集成完成, 版本发布完成 or
产品交付完成.**

## Step D entry: the duty payload runner, and the live re-check the owner ruling asks for

The owner ruling of 2026-10-15 puts the shared-PGDATA disposal **before** the three-database build and
requires the disposal to rest on runtime facts rather than on passing tests. Both halves were re-checked
read-only at HEAD `413ee7ce` instead of being taken from the earlier record:

| Check | Result |
|---|---|
| `make verify.daily.runtime.legacy_stack.retire` | 20 tests, OK (nonzero) |
| `make verify.daily.runtime.routing.inventory` | 17 tests, OK (nonzero) |
| `make daily.runtime.legacy_stack.retire.plan` | `PLAN`, `failing_guards []`, digest `534c710a27c034…` — only the four idempotent `remove_automatic_restart_path` steps remain |
| `make daily.runtime.routing.inventory DAILY_RUNTIME_EXPECTED_SHA=10bf72ef…` | `PASS`, 0 failed assertions, `remote_head 10bf72ef…`, `sc_odoo` and `sc_platform_core` still unserved |

So the disposal still holds: one postmaster owns each cluster data directory, the retired stack is not
running and cannot come back on its own. These are iteration-stage observations, not a frozen candidate.

### The entry Step D needs

`scripts/ops/daily_runtime_duty_payload.py` runs one signed payload action (`plan`, `import`, `verify`)
inside a declared duty's **own** rendered definition, as that duty's own application user, so the filestore
it writes stays owned by the identity the live application runs as. It is the daily-runtime counterpart of
the already-committed `scripts/ops/production_acceptance_payload_runtime.py` and reuses the product's own
`scripts/tenant_payload/odoo_action.py`, so it adds no privilege:

* the operator authorization is still the narrow `smart_core.group_smart_core_tenant_payload_importer` group;
* the maintenance capability is the same same-process proof the production acceptance runner already uses,
  not a data-level permission;
* only a duty declared `data_purpose=customer` may receive a payload, and ownership is never defaulted;
* the remote bundle is the existing immutable `daily.candidate.continuity.remote_install` tree — the entry
  and the action script were added to that one list, and the guard that derives every shipped module from
  the shipped tools' own imports now covers both.

`plan` additionally proves it wrote nothing: `database_write_count=0`, `filestore_write_count=0`, and the
database digest and protected business counts identical before and after.

`make verify.daily.duty.payload` — 25 tests, OK (nonzero).

### What actually blocks Step D, read back live

Two facts were re-read read-only from the customer duty cluster rather than trusted from an earlier note:

```
sc_edition_release_snapshot released+active construction.standard = 0
sc_tenant_payload_import_batch = 0
importer group res_id 19, admin in group = 0, admin active = 1
```

Consequences, in the product's own words:

* `provision_operator.py` refuses with `TPV1_PLATFORM_SNAPSHOT_CONTRACT_MISMATCH` until exactly one released
  `construction.standard` snapshot exists **in that database**;
* `odoo_action.py` refuses with `TPV1_IMPORT_OPERATOR_AUTHORIZATION_MISSING` until the operator is in the
  narrow importer group.

And the mechanism gap behind it: the only governed entry that publishes the daily product-edition snapshot
is `release.daily_product_navigation.snapshot`, and it is hard-coded to `DB_NAME=sc_demo`. A tenant duty
therefore cannot register the released edition it runs, the narrow operator grant cannot be issued, and the
tenant's own versioned migration cannot start.

The fix belongs to P4 ops tooling that resolves its identity from
`config/ops/daily_runtime_database_duties.v1.json`; the snapshot record itself must stay owned by the
existing platform delivery service, never a direct insert. Nothing was published, granted, staged, planned
or imported in this step.

**This is 批次验收完成 for the Step D entry slice. It is not 主线集成完成, 版本发布完成 or 产品交付完成.**

---

## Step D-1/D-2 — `platform_release_db` 语义核对与版次发布入口声明驱动化

### 顺序 1：`platform_release_db` 真实语义（只读核实，不改产品校验）

先看先例，再看活体读回，两边一致：

| 依据 | 证据 | 结论 |
|---|---|---|
| `scripts/release/configure_colocated_platform_core.py` | `PLATFORM_RELEASE_DB_MUST_MATCH_CURRENT` / `EXISTING_PLATFORM_RELEASE_DB_CONFLICT` | 参数必须等于**当前库** |
| `scripts/release/initialize_colocated_platform_snapshot.py` | 前置要求 `PLATFORM_RELEASE_DB` == 当前库，且经 `EditionReleaseSnapshotService` 发布，从不直接插表 | 记录由平台交付服务写，入口不越权 |
| `scripts/ops/production_acceptance_clone_runtime.py::rebind_platform_release_database` | 把隔离恢复克隆重绑到**自己** | 参数指向“承载生效快照的库” |

活体读回（本会话只读复核）：

```
sc_demo                     : platform_release_db=sc_demo, bound_tenant_key=baosheng,
                              released+active = construction.standard:daily-navigation-standard-10bf72ef4bb0,
                                                construction.preview:daily-navigation-preview-10bf72ef4bb0
sc_tenant_baosheng_dev      : platform_release_db=<none>, bound_tenant_key=baosheng, 快照 0 条,
                              sc_product_policy = platform.standard / platform.preview / construction.standard / construction.preview,
                              sce_customer_baosheng installed
sc_platform_control         : platform_release_db 无, 快照 0 条
```

**判定：`platform_release_db` 是“租户本地版次快照载体”，不是平台发布权威。** 因此把它绑定到客户
开发库是符合先例语义的；控制面不持有版次，也不得承载。**租户持有自己库里的生效快照，不等于租户取得
平台发布权**——入口只允许 duty 自己声明的版次，且只写本库。

本轮登记（顺序 1 要求的目标身份与影响集合）：

| 项 | 值 |
|---|---|
| 目标库 | `sc_tenant_baosheng_dev`（职责 `customer_tenant_dev`） |
| 租户 | `baosheng`（`sc.tenant.bound_tenant_key` = `baosheng`） |
| 版次 | 仅 `construction.standard`，`version_prefix=daily-navigation`，期望版本 `daily-navigation-standard-<SC_SOURCE_REVISION 前12位>`；`construction.preview` **不自动扩** |
| 代码版本 | 分支 `fix/data-ownership-visibility-recovery-20261015`，基线 `main/origin/main = 10bf72ef`；产物源 `SC_SOURCE_REVISION` 由职责 env 提供 |
| 影响集合 | `config/ops/daily_runtime_database_duties.v1.json`、`make/daily_candidate.mk`、`scripts/ops/daily_runtime_duty_payload.py`（纯重命名复用）、新增 `scripts/ops/daily_runtime_duty_edition_release.py` 与其测试 |

### 顺序 2：入口改为声明驱动

新增 `scripts/ops/daily_runtime_duty_edition_release.py`（动作 `readback` / `publish`）：

* 身份**全部**来自 `config/ops/daily_runtime_database_duties.v1.json`；工具内不含任何 duty 数据库/容器/
  卷字面量（有测试强制）。
* 拒绝：未声明 duty、不安全名、`data_purpose=platform_control`、无 `edition` 块、carrier 非
  `effective_release_snapshot`、空/非法 `allowed_product_keys`、非法 `version_prefix`。
* 只允许 duty 自己声明的版次（客户库仅 `construction.standard`）。
* 发布在 duty 自身渲染定义里 `docker compose run --rm --no-deps -T`（不加 `--user`），把不可变工具树的
  `scripts/release/` 以 `:ro` 挂载，stdin 喂 `configure_colocated_platform_core.py` →
  `initialize_colocated_platform_snapshot.py`，由**既有** `EditionReleaseSnapshotService` 落记录。
* `readback` 独立进程执行，自证 `writes: 0`；校验 database 一致、carrier 不指向别库、tenant 绑定不指向
  别租户、两份既有 JSON 收据必须 PASS 且绑定本 duty。
* Demo 原路径 `release.daily_product_navigation.snapshot`（`make/dev.mk`）保持不变。

配置侧：`demo` 与 `customer_tenant_dev` 各加 `edition` 块；顶层加 `edition_release_note`（写明载体语义
判定与“租户无平台发布权”）及指向本文件的 `edition_release_note_authority`。

唯一拒绝结果（无有效版次、无导入授权）**是正常保护**，不修改产品校验去消除它。

### 定向验证（非零，迭代阶段）

| 入口 | 结果 |
|---|---|
| `make verify.daily.duty.edition_release` | 45 tests, OK |
| `make verify.daily.duty.payload` | 25 tests, OK |
| `make daily.candidate.continuity.test` | 28 tests, OK |
| `make ci.local.iteration` | `PASS`（dirty, L1 only） |
| `make agent.run.resume` | `resolved`, `outside_scope []` |

**这是 批次验收完成（顺序 1/2 切片），不是主线集成完成 / 版本发布完成 / 产品交付完成。**

### 顺序 3：客户开发库发布声明允许的版次（已完成）

在受管工具安装后执行 `remote_publish`（`DAILY_DUTY_EDITION_DUTY=customer_tenant_dev`、
`PRODUCT_KEY=construction.standard`）：

```
platform_parameter : PASS   value = sc_tenant_baosheng_dev
snapshot           : PASS   snapshot_id = 1
                            version = daily-navigation-standard-10bf72ef4bb0
                            policy_menu_count = 90 = snapshot_menu_count
preview_page_count : 0      未自动扩 construction.preview
```

权威回读：carrier = `sc_tenant_baosheng_dev`，恰 1 条 released+active 的 `construction.standard`。

重试幂等已验证：第二次发布两份收据均为 `changed:false` / `idempotent:true`，
`release_state_digest` 前后一致（`a6fcaacd5df619ce…`）。

### 顺序 4（准备）：专用导入操作员窄授权入口

**问题**：`scripts/ops/daily_runtime_duty_payload.py` 之前把导入操作员身份硬编码为
`base.user_admin`。所有者裁定：必须通过既有入口授权**专用**导入操作员，最小权限、精确租户范围、
可撤销，**不默认给通用 admin 加组**。因此该身份属于职责声明的事实，入口不得自带字面量。

**改动**：

* 新增 `scripts/ops/daily_runtime_duty_operator_grant.py`（动作 `readback` / `grant`），身份全部来自
  `config/ops/daily_runtime_database_duties.v1.json` 的 duty 声明；仅接受 `data_purpose=customer`、
  有 `tenant_key` 且声明了 `payload_operator` 块的 duty（`carrier=narrow_import_grant`、
  `identity_type=external_xmlid`、合法 `identity_key`、`tenant_key` 一致、非空 `authorization_basis`、
  `customer_modules`、`contract`）。
* 契约强校验：`direct_grant_targets==[importer]`、传递闭包必须为空、
  `required_existing_groups==["base.group_user"]`、期望直接/生效新增精确相等、无未声明新增、
  `grant_scope_version=3`、`expected_company_scope>=1`，且任何集合中都禁止出现
  `smart_core.group_smart_core_data_operator`。
* 授权在 duty 自身渲染定义里 `docker compose run --rm --no-deps -T`（不加 `--user`）执行
  `scripts/tenant_payload/provision_operator.py`；前后各做一次只读回读并比对（含
  `data_operator_added is False`）。
* **空审批人直接拒绝**，不伪造审批身份。
* `daily_runtime_duty_payload.py` 移除 `base.user_admin` 字面量，改由声明解析；未声明则停机，不 fallback。

**当前 fail-closed 状态**：本仓库声明**尚未**添加 `payload_operator` 块，因此入口 readback 返回
`BLOCKED: duty customer_tenant_dev declares no payload_operator block`。这正是测试断言的行为，属于
**正常保护**——不修改产品校验去消除它。

**只读实测事实**（`sc_tenant_baosheng_dev`）：

```
res_users : 1 __system__(inactive) / 2 admin(active,internal) / 3 default(inactive)
            4 public(shared) / 5 portaltemplate(shared)
importer  : smart_core.group_smart_core_tenant_payload_importer (id 19) 成员 = 0
```

即：租户库内**没有**专用的非管理员内部用户，`base.user_admin` 是当前唯一可解析的
`external_xmlid`——而它恰是所有者裁定要排除的通用 admin。

**两个待所有者给定的输入（其余准备工作已就绪）**：

1. 专用操作员身份的**承载层**：由平台按声明在启用载荷接口的库上生成，
   还是由客户模块 `sce_customer_baosheng`（客户仓库工作区）声明租户服务账号。
2. `APPROVED_BY` 必须绑定**可核验的真实审批主体及授权依据**；所有者已明确禁止填所有者本人或伪造审批人。

### 定向验证（非零，迭代阶段）

| 入口 | 结果 |
|---|---|
| `make verify.daily.duty.operator_grant` | 19 tests, OK |
| `make verify.daily.duty.payload` | 26 tests, OK |
| `make verify.daily.duty.edition_release` | 46 tests, OK（输入未变，复用） |
| `make daily.candidate.continuity.test` | 28 tests, OK（输入未变，复用） |
| `make ci.local.iteration` | `PASS`（两个新文件已登记进 run scope，`outside_scope` 为空） |

**这是 批次验收完成（顺序 1/2/3 + 顺序 4 准备切片），不是主线集成完成 / 版本发布完成 / 产品交付完成。**

## Step D 顺序 4 定案：选择 A——由统一受管入驻机制创建专用导入服务账号

所有者裁定：**导入操作员的身份由统一受管入驻机制创建，用户模块不承担平台操作员的创建。**
这条同时否掉了前两个待定输入中的第 (1) 项，并把第 (2) 项收窄为“审批主体必须是可核验的真实主体”。

### 固定的执行要求（本轮据此实现）

- **P0** 负责通用账号生命周期与授权机制，**职责声明**承载租户差异，**P4** 负责执行与回读。
- 使用**独立服务身份**：无管理员组，限定目标租户与公司，只赋予既有导入机制所需权限。
- 凭据走**现有受管方式**生成与保管，不进入源码、报告或对话，**不默认开放交互式登录**。
- 创建必须**幂等**；遇到同名但身份不匹配的账号必须**拒绝接管**。
- 导入完成后**撤销临时导入权限**、使临时凭据或会话失效；**保留账号及其审计关联**，不删除责任记录。
- `APPROVED_BY` 必须绑定**已验证的真实所有者或正式审批主体**；不得由新建服务账号自批，也不得把任意
  `admin` 当作审批人。所有者本轮授权可作为**审批依据**，但不能代替审批主体身份。

### 已交付（P0 机制）

| 交付物 | 职责 |
|---|---|
| `addons/smart_core/security/tenant_payload_operator_policy.py` | 纯决策层，不 import odoo：拒绝无管理员组、拒绝接管、拒绝伪造审批 |
| `addons/smart_core/security/tenant_payload_operator.py` | ORM 层：`provision` / `grant_import_scope` / `revoke_import_scope` / `read_operator` / `assert_import_operator` / `_group_closure_xmlids` |
| `addons/smart_core/tests/test_tenant_payload_operator_lifecycle.py` | 落库效果与非接管反例 |
| `scripts/verify/test_tenant_payload_operator_policy.py` | 纯层反例 |
| `addons/smart_core/models/platform_database_registry.py` | 维护授权绑定 `operator_identity_key` + `subject_checksum`，并新增只读投影 `_approved_access_projection` |
| `make verify.smart_core.tenant_payload_operator.policy` / `.orm` | 定向 L2 / L3 入口 |

身份判定不再靠“字段名对得上”，而是**组闭包**：候选必须持有必需组，只能持有声明闭包内的组
（`groups | trans_implied_ids`），出现任何未声明的组（例如 `base.group_partner_manager`）即**拒绝接管**；
凭据事实取 `has_stored_password`；缺少 `tenant_key` 绑定是 fail-closed 停机。

### 已交付（声明 + 入口）

`config/ops/daily_runtime_database_duties.v1.json` 的 `customer_tenant_dev` 现在声明 `payload_operator`：

```yaml
carrier: unified_onboarding_service_identity
identity_type: external_xmlid
identity_key: smart_core.svc_tenant_payload_operator_baosheng
login: svc-tenant-payload-operator-baosheng
tenant_key: baosheng
company_xmlid: base.main_company
import_capability: migrate
grant_scope_version: 3
```

入口 `scripts/ops/daily_runtime_duty_operator_grant.py` 从声明解析身份，**不再接受 `--approved-by`**；
它把本次运行绑定到平台控制库的 `sc.platform.maintenance.access`（`operator_identity_key` + `subject_checksum`，
经 `_approved_access_projection` 只读取出），**没有覆盖本次运行的批准记录就停机**，因此不会伪造审批人。

### 审批身份核查（只读，结论：当前不可核验）

只读探测平台控制库 `sc_platform_control`：

```
res_users          : 1 __system__(inactive) / 2 admin(active) / 3 default(inactive) / 4 public / 5 portaltemplate
group_smart_core_security_admin : 0 成员
sc_platform_maintenance_access  : 0 行
```

`_approve_access()` 要求审批人持有 `smart_core.group_smart_core_security_admin` 且**不是请求人**；
当前平台控制库**没有可核验的独立审批主体**，而唯一活跃的内部用户正是所有者禁止用作审批人的通用 `admin`。

→ 因此 `grant` 步骤在任何写入之前**暂停**，待办：

> **请所有者提供正式审批账号（或通过现有认证入口完成批准），并给出要绑定的授权依据。**

审批记录须同时绑定：目标租户、数据库、操作员身份、权限范围、载荷摘要、有效期。

### 顺序 4 之前可以推进的部分（不依赖审批）

1. 提交分层候选 → `make daily.runtime.candidate.bundle_sync` 把候选投递到日常运行面；
2. `make daily.runtime.duty.operator_grant.remote_readback`（只读，不得写入）；
3. `make daily.runtime.duty.operator_grant.remote_provision` + 回读（受管创建）；
4. `make daily.runtime.duty.payload.remote_plan`（只读计划）。

### 定向验证（非零，迭代阶段）

| 入口 | 结果 |
|---|---|
| `make verify.smart_core.tenant_payload_operator.policy` | 36 tests, OK |
| `make verify.smart_core.tenant_payload_operator.orm` | 18 tests, 0 failed / 0 error |
| `make verify.daily.duty.operator_grant` | 38 tests, OK |
| `make verify.daily.duty.payload` | 26 tests, OK |
| `make verify.demo.lifecycle.unit` | 30 + 5 + 30 tests, OK（demo 声明与动作座位链的结构校验） |
| `make ci.local.iteration` | `PASS`，`outside_scope` 为空 |

**这是 批次验收完成（选择 A 的机制与声明切片），不是主线集成完成 / 版本发布完成 / 产品交付完成。**
