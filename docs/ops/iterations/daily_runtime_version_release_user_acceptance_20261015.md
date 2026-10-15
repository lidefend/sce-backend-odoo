# Daily Runtime — 版本发布与用户视角验收（2026-10-15）

Goal: `DAILY-RUNTIME-VERSION-RELEASE-AND-USER-ACCEPTANCE-20261015`
Run: `.agent/runs/DAILY-RUNTIME-VERSION-RELEASE-AND-USER-ACCEPTANCE-20261015/run.json`
Branch: `release/daily-runtime-version-release-20261015`
Baseline: `ba7577c212b81468491942e972ea28bd64345ebd`（PR #664 合并后的 `main == origin/main`）
Rebind: 2026-10-15 所有者接管后，本 run 沿用同一记录与证据索引改绑到 `fix/data-ownership-visibility-recovery-20261015`，
基线更新为 `10bf72ef4bb060556bd2844598b58f9806392d34`；下面各章节以出现时的实际 HEAD 标注，不复用旧 HEAD 的结论。

## 身份书写口径（2026-10-16 补记）

本记录及其 run 写于 2026-10-16 之前，正文当时写的是被服务客户的具体数据库名、应用角色、
compose 项目与容器、数据卷、存储与备份命名空间、客户仓库、客户模块名、租户 key 及法律主体名。

按产品仓库边界规则（`verify.tenant.product_payload_boundary`），这些具体身份不得留在会随产品交付给
每个客户的树里，因此本次只做**书写口径替换**：具体值改写为 `<...>` 占位引用。**当时的结论、失败、
时间、计数与证据一律未改写**，也因此这份记录现在**不能**被读成"当时就已经写成通用占位符"。

原文（含具体值）原样保存在受控外部证据区：

`.runtime/agent-runs/DAILY-RUNTIME-VERSION-RELEASE-AND-USER-ACCEPTANCE-20261015/product-boundary-identity-relocation-20261016/original-records/`

`identity-bearing-files.tsv` 列明受影响文件与当时内容，`SHA256SUMS` 可校验原文件。

占位符对照：`<customer-tenant-db>` 为职责 `customer_tenant_dev` 的数据库；`<customer-tenant-app-role>`、
`<customer-tenant-compose-project>`、`<customer-tenant-db-container>` / `<customer-tenant-odoo-container>`、
`<customer-tenant-data-volume>`、`<customer-tenant-backup-namespace>`、`<customer-tenant-backup-set>`、
`<customer-tenant-uat-db>` 同名前缀以此类推；`<customer-module>` 为其客户模块，`<tenant_key>` 为其租户 key，
`<customer-repository>` 为其客户仓库，`<customer-payload-id>` 为其载荷 id，`<customer-legal-entity>` 为其法律主体。
具体值的权威来源是职责声明与 `ops_root` 下的受管实例文档，不是本文。

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
  `smart_construction_custom` 17.0.2.0.0 and the customer module `<customer-module>` 17.0.2.8.0. Companies:
  1 <customer-legal-entity>, 2 Demo Secondary Company, 21 FE Company A, 22 FE Company B. Registrations declare
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
`sc_demo` <- `sc-backend-odoo-dev-odoo-1`, `<customer-tenant-uat-db>` <-
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

The customer repository `<customer-repository>` is clean at `bfbc736`. Its manifest declares
`tenant_key=<tenant_key>`, `module_version=17.0.2.8.0`, `install_mode=customer_database_only`,
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
- Customer development duty: unbound. A <tenant_key> tenant database does exist
  (`<customer-tenant-uat-db>`) but on a **separate cluster**
  (`system_identifier 7667092793767399462`) served by its own stack, at older revisions (`smart_core`
  17.0.1.1.1, `<customer-module>` 17.0.2.3.0, no registration table). Policy section 7 requires
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
   tenant `<tenant_key>`, environment `dev`, database `<customer-tenant-db>`, application role
   `<customer-tenant-app-role>` (independent credential, no cluster management rights), exact filter
   `^<customer-tenant-db>$` with database enumeration off, compose project `<customer-tenant-compose-project>`, and a
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
`sc_platform_core`, named the customer development database `<customer-tenant-db>`, and required
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

### Step C-2 — `<customer-tenant-db>` created

| Fact | Observed |
|---|---|
| compose project / container | `<customer-tenant-compose-project>` / `<customer-tenant-db-container>` |
| data volume | `<customer-tenant-data-volume>` |
| cluster system identifier | `7696799327921901606` |
| application role | `<customer-tenant-app-role>` — LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE |
| database | `<customer-tenant-db>`, owner `<customer-tenant-app-role>` |
| privileges | `REVOKE CONNECT ... FROM PUBLIC`; CONNECT granted only to the application role |
| stored settings | `ODOO_DBFILTER=^<customer-tenant-db>$`, `LIST_DB=false`, `NGINX_PORT=18090`, `ODOO_PORT=18091` |
| storage namespace | filestore `<customer-tenant-db>`, session `<customer-tenant-db>`, backup `<customer-tenant-backup-namespace>` |

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
已完成到「职责已按声明建成并留证」的程度：`sc_platform_control` 与 `<customer-tenant-db>` 各自拥有独立
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
  DAILY_RUNTIME_TENANT_CUSTOMER_REPOSITORY=/home/lidefend/workspace/<customer-repository> \
  DAILY_RUNTIME_TENANT_SHA=bfbc736c51d987777b50c465261ece1d8d22f008
```

```
PASS  mode=apply
path    /opt/sce/tenant-addons/daily/bfbc736c51d987777b50c465261ece1d8d22f008
digest  e0a3210da88ea49b1af16d6c037081289a97a39f7fb602d67192c25bf67dd7a6
modules <customer-module>
        <customer-module>_core035_mvp
        <customer-module>_history_attachments
        <customer-module>_legacy
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
docker restart <customer-tenant-odoo-container>                                          returncode 0
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
ir_config_parameter sc.tenant.bound_tenant_key = <tenant_key>     (the client post_init hook ran)
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

The owner ruled that `<customer-tenant-db>` may not take its first business-data write without a paired
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
(`<customer-tenant-app-role>`) while the isolated drill uses the drill's own role.

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

backup          paired_backup_pass=true  <customer-tenant-backup-namespace>/<customer-tenant-backup-set>

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
`<customer-tenant-db>`; the customer module's own versioned migration
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
sc_demo                     : platform_release_db=sc_demo, bound_tenant_key=<tenant_key>,
                              released+active = construction.standard:daily-navigation-standard-10bf72ef4bb0,
                                                construction.preview:daily-navigation-preview-10bf72ef4bb0
<customer-tenant-db>      : platform_release_db=<none>, bound_tenant_key=<tenant_key>, 快照 0 条,
                              sc_product_policy = platform.standard / platform.preview / construction.standard / construction.preview,
                              <customer-module> installed
sc_platform_control         : platform_release_db 无, 快照 0 条
```

**判定：`platform_release_db` 是“租户本地版次快照载体”，不是平台发布权威。** 因此把它绑定到客户
开发库是符合先例语义的；控制面不持有版次，也不得承载。**租户持有自己库里的生效快照，不等于租户取得
平台发布权**——入口只允许 duty 自己声明的版次，且只写本库。

本轮登记（顺序 1 要求的目标身份与影响集合）：

| 项 | 值 |
|---|---|
| 目标库 | `<customer-tenant-db>`（职责 `customer_tenant_dev`） |
| 租户 | `<tenant_key>`（`sc.tenant.bound_tenant_key` = `<tenant_key>`） |
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
platform_parameter : PASS   value = <customer-tenant-db>
snapshot           : PASS   snapshot_id = 1
                            version = daily-navigation-standard-10bf72ef4bb0
                            policy_menu_count = 90 = snapshot_menu_count
preview_page_count : 0      未自动扩 construction.preview
```

权威回读：carrier = `<customer-tenant-db>`，恰 1 条 released+active 的 `construction.standard`。

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

**只读实测事实**（`<customer-tenant-db>`）：

```
res_users : 1 __system__(inactive) / 2 admin(active,internal) / 3 default(inactive)
            4 public(shared) / 5 portaltemplate(shared)
importer  : smart_core.group_smart_core_tenant_payload_importer (id 19) 成员 = 0
```

即：租户库内**没有**专用的非管理员内部用户，`base.user_admin` 是当前唯一可解析的
`external_xmlid`——而它恰是所有者裁定要排除的通用 admin。

**两个待所有者给定的输入（其余准备工作已就绪）**：

1. 专用操作员身份的**承载层**：由平台按声明在启用载荷接口的库上生成，
   还是由客户模块 `<customer-module>`（客户仓库工作区）声明租户服务账号。
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
identity_key: smart_core.svc_tenant_payload_operator_<tenant_key>
login: svc-tenant-payload-operator-<tenant_key>
tenant_key: <tenant_key>
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

### 独立复核（只读 B 线，2026-10-15）

复核对象：`85dbd5a7` / `c01e121e` / `deccb08f`，基线 HEAD `fa13aada`。复核执行体只做只读
`git`/`sed`/`grep`，未修改文件、未写库、未触达远端、未执行任何 `make` 目标。

**判定：`APPROVE_WITH_NOTES`——无 S1 阻断、无 S2 需修。**

已确认正确（摘要）：

- 组闭包是严格白名单 `required ⊆ groups ⊆ required∪implied`，不是“不在禁止列表即通过”。
- 无审批不停机路径；空审批人、异 operator、异摘要、非 approved、超窗、非正 `access_id` 全部拒绝；
  入口已删除 `--approved-by`。
- 审批主体被机制性限制为独立 `security-admin` 且非请求人；该检查在**真实运行路径**上生效
  （`provision()` 调用 `policy.validate_authorization`，其中的 `requested_by != approved_by` 生效）。
- 创建无管理员组、无密码、单公司、幂等、拒绝接管；撤销只回收 importer 组并保留账号与审计关联。
- 声明契约字段与策略常量一致，无漂移；demo 不再直写终态、不用 `sudo/uid1` 或私有 token。
- 分层落实：机制在 P0 `smart_core`（纯策略层零 `odoo` 依赖），租户差异在职责声明，执行/回读在 P4。

S3 观察（记录为后续项，不作为本批阻断）：

1. `tenant_payload_operator_policy.py:235` 只校验 `subject_checksum` 格式，不与载荷等值比较；
   等值绑定由入口与载荷运行器承担。
2. `platform_database_registry.py:454` `_active_access` 用 `limit=1` 且无显式 `order`；
   多条同时段已批准记录时选择不确定（只会 fail-closed，不减安全）。
3. `daily_runtime_duty_operator_grant.py:518` `assert_approval` 自身未单独复核
   `requested_by != approved_by`（由策略层承担）。
4. 审批人权限只校验“审批时刻”，后续不再回读其是否仍持 `SECURITY_ADMIN_GROUP`。
5. 本候选内没有临时凭据/会话失效的可验证实现（账号无密码、无 apikey），需运行时证据确认。

复核执行体同时标明无法在本环境验证、只能推断的点：真机 `base.group_user` 传递闭包内容、
审批停机的实际触发、撤销后凭据失效、demo 合同链端到端（L3/L4）。

---

## 2026-10-15（续）：统一入驻的登记解卡 —— 平台数据库登记受管入口

### 交接时的唯一卡点

`make daily.runtime.duty.operator_grant.remote_provision` 返回：

```
odoo.exceptions.ValidationError: DBGOV1_DATABASE_NOT_REGISTERED:<customer-tenant-db>
```

根因链：`provision()` → `_assert_governed_principal()` → `_assert_governance_principal()` →
`_resolve_entry(db_name)`；而审批投影 `_approved_access_projection` 在**平台控制库**
`sc_platform_control` 上执行 `_resolve_entry(<customer-tenant-db>)`，该库
`sc.platform.database.registration` 为 **0 行**。

也就是说：登记入口 `scripts/ops/platform_database_register.py` 早已存在且自带 fail-closed
校验，但**缺少受治理的日常运行时绑定** —— 没有人把“控制面 / 目标 / 集群身份”解析出来，
所以任何日常 duty 都无法进入平台登记。这是**平台登记缺失**，不是生命周期机制缺陷。

### 本轮落地（P4 传输层，不新增任何身份或权限）

新增 `scripts/ops/daily_runtime_duty_database_registration.py` 及其 31 项定向测试，并把
不可变工具树白名单与 Make 受管入口补齐：

| 事项 | 落实方式 |
|---|---|
| 目标库 / 用途 / 租户 / dbfilter | 全部取自 `config/ops/daily_runtime_database_duties.v1.json` 职责声明 |
| 环境角色 / 数据库策略 | 取自平台自身词汇表 `addons/smart_core/security/data_space_provisioning.py`，从本入口自身不可变树加载 |
| 生命周期状态词表 | 取自 `addons/smart_core/security/database_governance.py` |
| 控制面 | 明确**不作为数据空间**登记，直接拒绝 |
| 唯一写入路径 | 不可变的 `platform.database.register`，在控制职责自身渲染栈内执行；容器内以只读挂载 `/mnt/scripts` 加载，并回传源码摘要与本树比对，拒绝容器旧副本 |
| 幂等 | 仅允许安全方向：完全一致复用且不写；身份不符即停机，登记身份永不被接管或改写 |
| 只读性 | `readback` 独立进程执行并自证 `writes=0`，登记断言在全新事务中完成 |

Make 入口：`verify.daily.duty.database_registration`（31 项）、
`daily.runtime.duty.database_registration.remote_install/remote_readback/remote_register`。

本轮还修掉一个真实顺序缺陷：`readback` 动作原先在证明“状态未移动”之前就对第二次读回做深度断言，
导致状态漂移时抛出的是内容错误而非“状态被改变”。修在归属层，没有放宽断言。

### 权威回读（写前 / 写 / 写后）

| 阶段 | 事实 |
|---|---|
| 写前 | `sc.platform.database.registration` 0 行、`sc_platform_database_operation` 0 行、`sc.platform.maintenance.access` 0 行；readback 报 `registered=false, writes=0`；入口摘要 `8ad05369…` 与本树一致 |
| 写入 | `operation_id=1`，entry `platform.database.register`，`execution_id=e6aa707444f34f6084484abc516ab1ec`，`status=passed`、`commit_state=committed`、`initial_state=declared`，除声明事实外不带任何环境 |
| 写后 | `<customer-tenant-db>｜customer｜<tenant_key>｜customer_production｜database_per_customer_tenant｜^<customer-tenant-db>$｜declared`，`grants_business_data_scope=false`，`maintenance_access_count=0`，审计恰好 1 条 `register`（`from_state` 空 → `to_state=declared`） |
| 幂等 | 再次 `register` 报 `created=false`、`entry_report.reused=true`，审计仍是 1 条 → 复用路径确实不写 |

写入量级：平台控制集群内 **1 行登记 + 1 行审计**，追加式。

### 新的暂停点：比裁定预期更早，且更有理由

登记解卡后 `provision` 的失败原因已换成**预期的审批缺口**：

```
BLOCKED the platform control database holds no approved, in-window maintenance
access for this duty: the lifecycle refuses to fabricate one
```

关键事实：`APPROVAL_REQUIRED_ACTIONS = ("provision", "grant")`，且
`tenant_payload_operator.provision()` 在**创建任何东西之前**就校验授权。
因此暂停点在 `provision` 之前，而不是裁定预期的 `grant` 之前：

> 服务身份不能先于它将承载的审批而存在。

这**不是**要修的缺陷，机制不放松：伪造 `sc.platform.maintenance.access`、拿通用 `admin`
当审批人、让 `provision` 跳过审批，三者都属于所有者明令禁止的“绕过守卫”。

控制面现状（只读）：`res_users` 仅 `__system__`(停用) / `admin`(活跃、内部、即被禁止的通用管理员) /
`default` / `public` / `portaltemplate`；`smart_core.group_smart_core_security_admin`（组 id 16）**0 成员**。
→ 不存在可核验的独立审批主体。

### 依赖审批的只读动作

- `make daily.runtime.duty.operator_grant.remote_readback`**不需要审批**，已执行并留下审批前基线：
  `operator=null`、`importer_group_member_count=0`、`bound_tenant_key=<tenant_key>`、
  已发布版次 `construction.standard / daily-navigation-standard-10bf72ef4bb0`、
  `required_group_closure_xmlids` 与交接记录一致。
- `make daily.runtime.duty.payload.remote_plan` 当前被拒（`TPV1_IMPORT_OPERATOR_IDENTITY_NOT_UNIQUE`，
  实际条件是声明的 operator 身份未解析为活跃内部用户）。因此该计划**不是**“不依赖审批的只读计划”，
  本轮不宣称它通过。

### 待办（阻塞项，唯一）

> **请所有者提供正式审批账号（或通过现有认证入口完成批准），并给出要绑定的授权依据。**

审批记录须同时绑定：目标租户 + 数据库 `<customer-tenant-db>`、操作员身份
`smart_core.svc_tenant_payload_operator_<tenant_key>`、能力 `migrate`、载荷摘要
`f1adc6fb17b516d42492fe42229df0cce65956ea113978a19243c0de57ec1ed4`、有效期；
且审批人必须是**独立于请求人**、持有 `smart_core.group_smart_core_security_admin` 的主体。

审批到位后：`remote_provision` → 回读新身份 → `remote_plan` → `remote_grant` →
`remote_import` → `remote_verify` → 对账（12386 与 6322/29/6035、金额、来源关系、附件、归属、
合法用户可见 / 越权不可见）→ `remote_revoke` → B 线独立复核 → 主线集成。

### 状态边界

**批次验收完成（登记传输层 + 登记事实）**；主线集成 / 版本发布 / 产品交付**均未完成**。

### 结果索引登记

新入口已登记为 `daily_duty_database_registration_tool → verify.daily.duty.database_registration`，
并入本次结果索引；原始日志保留在 `.runtime/agent-runs/…/daily_duty_database_registration_tool.log`，
回执哈希绑定原日志。该条目与既有的 `daily_duty_operator_grant_tool`、`daily_duty_recovery_tool`
一样，因本 run 的环境类别是 `runtime` 而按设计读作 `stale`
（`runtime evidence requires authoritative environment readback`）——
这是**设计预期**，不是工具失败，也没有为让它读作 `reusable` 而放宽守卫。

`make ci.local.iteration`：`PASS change_state=dirty scope=unclassified_by_design coverage=L1_only`，
`outside_scope=[]`。

### 补充事实：审批记录本身目前没有生产创建入口

在核对“所有者如何真正完成批准”时发现，`sc.platform.maintenance.access` 在本树中**只有模型内部的**
`_request_access()` / `_approve_access()` 两个写入方法：

- 没有 ops 入口、没有 handler、没有 intent、没有菜单、没有表单视图；
- `addons/smart_core/security/ir.model.access.csv` 对
  `sc.platform.database.registration` 与 `sc.platform.maintenance.access` 只给
  `smart_core.group_smart_core_security_admin` / `smart_core.group_smart_core_admin` **只读**（1,0,0,0），
  写入被刻意限制在受治理方法内。

因此当前能产生审批记录的路径只有：受治理主体的运维 shell 提请求 + 独立的安全管理员身份批准。
而 `smart_core.group_smart_core_security_admin` 目前 0 成员，连批准人都没有。

**这不被静默“补一个入口”**：新增审批入口或写权限属于新的平台能力，超出所有者本轮“不要扩大范围”的裁定。
必须先由所有者裁定“审批如何产生”（受治理入口，或明确限定范围的 P4 shell 程序 + 独立真实批准人），
`provision` 才可能继续。

## 独立复核 S2 收口（2026-10-15）

B 线只读复核 `5f5c4dae..4450e674` 结论 `APPROVE_WITH_NOTES`，其中一条 **S2 必须先修**：

登记的「控制库写入」没有测试接线，且既有断言指向相反目标。生产在
`scripts/ops/daily_runtime_duty_database_registration.py:491` 用
`register_command(control, base, …)`，而用例
`test_the_register_command_carries_only_declared_facts` 传的是 `duty`
并断言 `-d == duty["database"]`。把生产的 `control` 误写成 `duty` 时 31 项测试
仍全绿，会把登记写进客户库、且是从客户库内部去写。

### 修复（只动本入口与其定向测试）

- **反例下移到接线层**：新增用例捕获 `execute()` 真正交给 `run_script` 的三条命令，
  断言三次 shell 的 `-d` 都是 `CONTROL_DATABASE`，且唯一写入声明的
  `PLATFORM_DATABASE_REGISTER_DB` 是 `CUSTOMER_DATABASE`、绝不是控制库。
  形状用例改传 `control`，保留「shell 库 ≠ 声明库」的双半不变量。
- **消除双重事实**：register 脚本模板改为绑定 `REGISTER_ENTRY_MODULE`
  （`%(module)s`），原先被复核指出的死常量不再空转，模板与声明也不可能再漂移。
- **分支顺序对齐**：register 分支现在**先证明未写入路径没有移动状态，再解释结果**，
  与 readback 分支的既有纪律一致。
- **替换名不副实的用例**：`test_a_half_written_registration_is_refused`
  原先含空转 `wraps` 补丁且与另一个用例重复，改为真正的
  「未写入却移动即拒绝」反例。

### 反例验证（临时注入缺陷 → 确认失败 → 还原）

| 注入 | 结果 |
|---|---|
| `:491` 的 `control` 改成 `duty` | 接线层用例 FAILED（`-d` 变成 `<customer-tenant-db>`） |
| 删除 `after != before and not created` | 移动反例 FAILED（未抛错） |

### 证据

- `make verify.daily.duty.database_registration` → **33 项 OK**（原 31 项 + 2 项接线/绑定用例，1 项改写）。
- `make ci.local.iteration` → `PASS change_state=dirty coverage=L1_only`。
- 修复提交 `932adae9`。

### 仍未关闭（S3，已登记、不阻断）

`grants_business_data_scope is not False` 恒真守卫；`mode/writes` 为同模板常量
（真正自证只读的是 before/after 比较）；`tool_identity` fail-open；复用路径会把
非 `declared` 状态也报成 `reused`；栈挂载断言只是字面量包含；Make 的 reason 仍经 shell 展开。
离线复核无法核验的运行时事实、`${SC_PRODUCT_ROOT}` 实际展开、容器内脚本是否等于本树摘要、
ssh 写性，仍需在运行时受管回读中体现。

---

## 待办：请所有者提供正式审批账号（当前暂停点）

> 已被下一节取代：所有者已指名 `lidefend` 作为授权人，且审批入口与安全管理员 bootstrap 均已交付。
> 本节保留为当时的事实记录（暂停时确实没有入口、没有可核验批准主体），不再表示当前状态。

本轮所有者裁定（选择 A）已授权统一受管入驻机制创建专用导入服务账号，并明确
`APPROVED_BY` 不能是 AI 助手、不能由新建服务账号自批、不能拿任意 `admin` 顶替。
但**审批事实本身目前没有生产创建入口**，且没有任何可核验的独立批准主体：

- `sc.platform.maintenance.access` 只有模型内部 `_request_access()` / `_approve_access()`；
- 无 ops 入口、无 handler、无 intent、无菜单、无表单视图，ACL 对两个模型只给安全管理员只读；
- `smart_core.group_smart_core_security_admin` 当前 **0 成员**；
- 控制面唯一活跃内部用户是被所有者禁止作为审批人的通用 `admin`。

因此 `provision` 在**创建任何东西之前**就被拒绝（不是 `grant` 之前），机制不放松：

```
BLOCKED the platform control database holds no approved, in-window maintenance
access for this duty: the lifecycle refuses to fabricate one
```

**请所有者二选一：**

1. 提供一个**可核验的正式审批账号**（须独立于请求人、持 `smart_core.group_smart_core_security_admin`），
   并说明本轮授权如何绑定为该审批的依据；或
2. 通过**现有认证入口**完成批准。

同时需裁定「审批如何产生」：新建受治理入口（新平台能力），还是明确限定范围的
P4 shell 程序 + 独立真实批准人。**在这两项落实前，不再触发任何写路径。**

获批后按既定顺序继续：
`remote_provision` → 回读新身份 → `remote_plan` → `remote_grant` →
`remote_import` → `remote_verify` → 对账 → `remote_revoke` → B 线独立复核 → 主线集成。

---

## 2026-10-16：P0 维护授权入口 + 安全管理员身份 bootstrap（本节取代上一节的暂停前提）

上一节的暂停结论建立在两个前提上：**审批事实没有生产创建入口**、**平台没有可核验的
独立安全管理员身份**。本轮所有者裁定补齐这两项，并指名 `lidefend` 作为授权人。
下面记录实际交付与证据；**暂停的原因从「机制缺失」变成「尚未执行批准」**。

### 交付

| 层 | 交付物 | 边界 |
|---|---|---|
| P0 入口 | `addons/smart_core/controllers/platform_maintenance_access_controller.py` | `GET /api/ops/maintenance/access` + `POST .../request\|approve\|reject\|revoke\|expire` |
| P0 模型 | `addons/smart_core/models/platform_database_registry.py` | 决策人由服务端 `self.env.user` 求出并校验独立性；状态机仍是唯一写入者 |
| P0 治理词表 | `addons/smart_core/security/database_governance.py` + `data/tenant/database_strategy.v1.json` | 新增 `MAINTENANCE_ACCESS_OPERATIONS = (provision, grant)`；声明必须相等 |
| 消费链 | `security/tenant_payload_operator_policy.py`、`tenant_payload_operator.py`、`scripts/ops/daily_runtime_duty_operator_grant.py` | `validate_authorization(action=...)`：capability ≠ grant，导入批准不能隐含允许创建账号 |
| 身份 bootstrap | `scripts/ops/platform_security_admin_bootstrap.py`（入口）、`scripts/ops/daily_runtime_platform_security_admin_bootstrap.py`（宿主传输器） | 只建立/验证实名安全管理员；**不批准任何申请**，不获得客户业务数据 |

关键约束（防止把审批变成可伪造的输入）：请求体里出现
`approved_by/approved_by_id/requested_by/requested_by_id/state/valid_from/valid_until`
一律**拒绝**（`MAINTENANCE_ACCESS_SERVER_OWNED_FIELD`），不是忽略；审批、拒绝、撤销、过期的
决策人只能是被服务端验证过、且与请求人不同的 `smart_core.group_smart_core_security_admin`。
授权记录绑定：请求人、独立批准人、目标租户与数据库、operator 身份、载荷摘要、
**操作集合**、有效期、原因与决策说明。

### 入口层暴露并修复的传输缺陷

新增入口第一次运行即暴露：`get_trace_id(headers)` 在原控制器与既存
`controllers/platform_ops_controller.py` 中都被**无参调用**，于是任何响应（包括拒绝信封）
在序列化前就抛 `TypeError`，客户端拿到的是 HTML 错误页。两处改为用实时请求头投影，
并新增用例断言「发出的 `X-Trace-Id` 必须被回显」。同时拒绝信封现在直接给出治理错误码
（`DBGOV1_*` / `DATABASE_GOVERNANCE_*` / `MAINTENANCE_ACCESS_*`），调用方按码分支而不是匹配文案。

### 验证（层级 / 命令 / 非零计数）

| 层 | 命令 | 结果 | 日志 |
|---|---|---|---|
| L2 入口 | `make verify.smart_core.platform_maintenance_access.orm` | **15 项 0 failed / 0 error** | `.runtime/agent-runs/DAILY-RUNTIME-VERSION-RELEASE-AND-USER-ACCEPTANCE-20261015/maintenance-access-decay-20261016/L2-rerun-20261016.log`（**重跑**：本表先前记的 12 项出自 01:17 的 `L2-http-entry.log`，而该测试文件在 `e75d3713` / `a52ba6d3` 又新增 3 个用例，旧日志只是过期，不是计数写错） |
| L2 模型 | `make verify.local.dev.platform_database_governance.orm` | **26 项 0 failed / 0 error** | 同上 `L2-rerun-20261016.log`（**重跑**：先前 24 项同样早于 `a52ba6d3` 新增的 2 个用例） |
| L2 关系链 | `make verify.smart_core.tenant_payload_operator.orm` | **20 项 0 failed / 0 error** | 同上 `L2-rerun-20261016.log`（用例集合未变，重跑的计数与旧日志一致） |
| L1 静态 | `verify.platform.security_admin.bootstrap` / `verify.daily.duty.operator_grant` / `verify.daily.duty.database_registration` / `verify.daily.duty.recovery` / `verify.daily.duty.payload` / `verify.platform.database.governance.guard` / `verify.smart_core.tenant_payload_operator.policy` | 见下（S3-1 更正） | 同上 + `.../maintenance-access-review-s2-20261016/` |
| L1 控制器 | `make verify.controller.boundary.guard` | PASS（delegate / allowlist / route / report / baseline 全部随新路由 PASS） | — |

覆盖点（下列各项由 `make verify.smart_core.platform_maintenance_access.orm` 覆盖；其中"独立性"
只能在**模型层**被观测到——HTTP 层到不了那条规则，因为当前唯一平台管理员 `admin` 不持有安全管理员组，
在角色闸门处即被拒）：批准前**确实零写入**（`_approved_access_projection` 为 `None`）、批准后投影覆盖、
非法决策字段拒绝、无角色拒绝、自批拒绝（`INDEPENDENT`，模型层）、无关主体不可读账本、未认证拒绝、
`migrate` 必须声明操作集合、拒绝/撤销由独立身份做出、过期清理由安全管理员独占且幂等、
已决策记录不可重复决策、`X-Trace-Id` 回显。

### 反例验证（注入缺陷 → 必须失败 → 还原）

| 注入 | 结果（**当前 15 用例集合**，`c572ffd5`） |
|---|---|
| `_trace_id()` 退化为无参 `get_trace_id()` | `0 failed, **20 error(s)** of 15 tests` |
| 入口角色闸门关闭 | `**4 failed** of 15`（恰为四个入口层角色用例；模型层仍独立拦住写入） |
| 从 `FORBIDDEN_BODY_FIELDS` 删除 `state` | `**2 failed** of 15` |

三次注入后均还原，`sha256sum -c` 逐字节一致，入口回到 15/15 全绿
（控制组 `0 failed, 0 error(s) of 15 tests`）。日志：`.../maintenance-access-decay-20261016/falsify-refresh-20261016.log`。

**计数口径**：入口集合在 `e75d3713` / `a52ba6d3` 由 12 扩到 15，因此本表按**当前集合**重跑，
先前记录的 14/4/2 是 12 用例版本上的观测，已被本表取代——不保留"版本绑定的旧比例"作为当前强度。

### 计数口径更正（S3-1）

记录曾写 `verify.platform.security_admin.bootstrap = 34`、`verify.daily.duty.operator_grant = 39`，
取的是**单个脚本的数**，不是目标自身输出的合计。按目标真实输出更正：

| 目标 | 目标自身输出 | 合计 | 来源日志 |
|---|---|---|---|
| `verify.platform.security_admin.bootstrap` | `test_platform_security_admin_bootstrap` 31 项 + `test_daily_runtime_platform_security_admin_bootstrap` **44** 项 | **75 项 OK** | `.../maintenance-access-decay-20261016/required-tests-counts-20261016.log`（44，非 41） |
| `verify.daily.duty.operator_grant` | `scripts/verify/test_tenant_payload_operator_policy.py` 39 项 + `scripts/ops/test_daily_runtime_duty_operator_grant.py` **42** 项 | **81 项 OK** | 同上 `required-tests-counts-20261016.log`（第二模块 41→42：本批新增幂等用例） |
| `verify.smart_core.tenant_payload_operator.policy` | 单模块 | **39 项 OK** | `required-tests-counts-20261016.log` |
| `verify.controller.boundary.guard` | route / allowlist / delegate / report / baseline | **PASS** | — |

非零性不受影响；受影响的只是记录精确度。表中两处先前低估（72 / 78）都是同一类错误：
**取子脚本的数当目标合计**，或**在子模块新增用例后没有重取**。

### B 线独立复核与处置（复核 HEAD `eacd5441`）

结论：**无 S1**；两处 S2（需修）、九条 S3（观察）。本轮处置：

- **S2-1：复用路径未绑定实名，且未对额外组 fail-closed。** 复用既有账号前比对
  `identity["name"] != request["name"]`（`PLATFORM_SECURITY_ADMIN_EXISTING_IDENTITY_MISMATCH`）；
  把"禁止列表反向"改为**组闭包白名单**：允许集合 = `base.group_user` +
  `smart_core.group_smart_core_security_admin` 在**本环境**中的 `trans_implied_ids` 闭包，
  任何闭包外成员即拒绝（`..._EXISTING_IDENTITY_HAS_UNRELATED_GROUPS`）。闭包从环境读取，
  因此不依赖"哪个模块 imply 哪个组"的硬编码；任一声明组缺失时闭包为**不可判定集合**，
  回读直接拒绝（`ALLOWED_GROUP_MISSING`），而不是"什么都不允许所以都通过"。
  传输层同步断言回读的 `name` 与闭包。
- **S2-2：`has_customer_business_data_scope` 是恒假断言，作为证据永不触发。** 不再引用
  `platform_admin.has_customer_business_data_scope`（该函数的窄语义是"管理员身份本身不推导业务范围"，
  恒返回 `False`，被当作"该身份没有业务数据范围"的证明即空转）。回读改为报告**真实事实**：
  `group_ids`、`group_xmlids`（没有 `ir.model.data` 的组按 `#id` 报告，不再静默丢弃）、
  `groups_outside_allowed_closure`，并以闭包为空作为该断言的证据。
- S3-1 计数失真：见上表更正。
- S3-2 文档状态失真（写成"尚未提交"）：更正为已在 `8f26ffd7` / `9b6324c0` 提交。
- S3-5 500 分支外泄内部异常文本、`PermissionError` 未映射：500 不再回传异常文本；
  `PermissionError` 纳入治理拒绝（400 + 治理码）。
- S3-7 `NAME` / `EVIDENCE` 未做字符集校验：入口新增 `NAME` 权威正则，`EVIDENCE` 放宽为
  "允许中文、禁止 `"` `'` `` ` `` `$` `\` `;|<>&()` 与控制字符"（真实姓名可能是中文，
  ASCII-only 正则会挡住所有者输入，而字符白名单又会放过载荷破坏字符）；两个远端 Make 目标
  在建立 ssh 连接前按同一字符策略拒绝会破坏载荷的输入。
- S3-9 `validate_authorization` docstring 漂移：更正为"必填关键字参数"。

登记不修（附理由，避免被读成遗漏）：

- **S3-3** `_request_access(requester_id=)`：生产调用点只有模型自身与 ORM 测试，产品入口用
  `self.env.user.id`，当前无可达绕过；属"可指定任意请求人"的潜在面，登记为下一步收口。
- **S3-4** grant 执行器未复检有效期窗口：窗口已由 `_active_access` 的 SQL 域与 policy 双重保证，
  该执行器自检属纵深；在链路首次真实执行前增加时间解析闸门会引入误拒风险，登记待链路验证后补。
- **S3-6** 决策入口 `csrf=False` + 会话回退：批准身份的凭据尚未建立，"决策只接受 bearer 主体"
  还是"为会话主体启用 CSRF"必须与凭据发放方式一并决定，登记为同一项收口。
- **S3-8** 允许只批一种操作的 `migrate` 申请：既定语义就是"批准可窄、执行必拒"
  （窄批准在 `grant` 处以 `AUTHORIZATION_OPERATION_NOT_COVERED:grant` 停机）；若在批准处强制
  `{provision, grant} ⊆ operations`，会挡住合法的"仅重新授权"场景。

### 下一步（唯一暂停点已变为「执行批准」）

1. `make daily.runtime.platform.security_admin.bootstrap.remote_readback`（预期控制库尚无安全管理员）；
2. `...remote_bootstrap`，`SC_CONFIRM_PLATFORM_SECURITY_ADMIN_BOOTSTRAP=BOOTSTRAP_DECLARED_PLATFORM_SECURITY_ADMIN`、
   `PLATFORM_SECURITY_ADMIN_LOGIN=lidefend` + 真实姓名/证据引用，然后回读身份
   （安全管理员恰好一次、无存储密码、**闭包外的组为空**、维护账本行数不变）；
3. 以平台管理员创建维护申请（`capability=migrate`、operator `smart_core.svc_tenant_payload_operator_<tenant_key>`、
   摘要 `f1adc6fb…1ed4`、operations `[provision, grant]`），由 `lidefend` 通过入口批准；
4. `remote_provision` → 回读 → `remote_plan` → `remote_grant` → `remote_import` → `remote_verify`
   → 对账（12386 / 6322／29／6035，金额、来源关系、附件、归属）→ `remote_revoke` → B 线独立复核 → 主线集成。

**状态边界**：本条为**批次代码与定向/静态验证完成**（B 线复核已返回并对 S2/S3 处置完成，见上）；
批次验收、主线集成、版本发布、产品交付**均未完成**。本轮改动已提交：`8f26ffd7`（维护授权入口）、
`9b6324c0`（安全管理员 bootstrap）、`eacd5441`（登记）；复核处置为后续提交。

---

## S3 收口与首次实跑（2026-10-16，`e75d3713` / `5ddb3596`）

### S3 全部在责任层关闭

| 编号 | 处置 |
|---|---|
| S3-1 | `readback` 从模块常量 `ALLOWED_GROUP_XMLIDS` 解析种子，不再内联重复；常量被生产代码消费，种子与报告的闭包不会漂移 |
| S3-2 | `make/daily_candidate.mk` 的姓名/证据长度上界改为入口自身的上界（2-80 / 10-200），本地可以放行的值不再宽于入口；Make 目标单测断言收窄后的模式 |
| S3-3 | 注释不再声称守卫先于所有插值：Make 会先展开本文件，只有撇号在 ssh 连接前拦截，其余破坏字符一律由入口从 argv 权威拒绝 |
| S3-4 | 控制器只在异常以受治理码发声时把 `PermissionError` 按拒绝回答（400 + 治理码），其余按服务器错误（500）且不回显内部文本；补 400/500 两条传输用例 |
| S3-5 | 两条反例在冻结树重跑并逐字节还原（`sha256sum -c`）：删闭包拒绝 → `test_a_readback_of_a_widened_identity_is_refused` 1 failed of 31；静默丢弃无 xmlid 组 → `test_a_group_without_an_external_id_is_still_a_membership` 1 failed of 31 |
| S3-6 | 入口随 `allowed_group_closure_ids` 一并报告 `allowed_group_closure_labels`；传输器拒绝"只有 ids 没有成员"的闭包并在回执中带出两者；首次真实回读的闭包为 `base.group_user`、`base.group_no_one`、`smart_core.group_smart_core_user`、`smart_core.group_smart_core_security_admin`，不含行业或客户业务角色 |

### 首次实跑发现的真实缺陷（`5ddb3596`）

第一次真实驱动该入口时，`readback` 分支**从未把声明的 login/name/evidence 送入一次性容器**，
读回报告的 `declared_login` 为空，与声明不符，于是**一次诚实读取被拒绝**
（`the identity read covers another login than the declared one`）。机制此前只被 hermetic 单测覆盖，
没有任何一层端到端验证过。

处置：新增只承载声明的 `readback_environment(entry, request)`；确认值、输出路径与执行号留在写路径。
补两条单测（readback 环境必须声明身份；丢失声明的 readback 被拒绝），反例为把该环境改成空
（`test_the_readback_environment_declares_the_identity_it_asserts` 1 failed of 43）。

### 已执行的部署与 bootstrap

| 步骤 | 命令 | 结果 |
|---|---|---|
| 部署一 | `make daily.runtime.candidate.bundle_sync` | PASS，`5f5c4dae → e75d3713`，`origin_main_mutated=false` |
| 部署二 | 同上 | PASS，`e75d3713 → 5ddb3596` |
| 回读 | `...security_admin.bootstrap.remote_readback` | ok、writes 0：`lidefend` 不存在，安全管理员成员 0，维护账本 0 行；闭包如上 |
| bootstrap | `...remote_bootstrap`（含声明确认值） | ok：`lidefend` uid 6，active、非 share、组恰为闭包内四个，闭包外为空，`is_security_admin=true`，`has_stored_password=false`，writes 1 |

**部署事实**：日常产品树 `/opt/projects/repos/sce-product-odoo` 当时落后分支 9 个提交，
首次回读因此以 `ModuleNotFoundError` 失败——duty stack 挂载的是**产品树**（`SC_PRODUCT_ROOT/scripts → /mnt/scripts`），
不是不可变工具树；候选必须先部署，入口才可被驱动。

### 新的唯一暂停点：审批人凭据

批准维护申请需要一个能通过**产品入口**认证的 `lidefend` 主体，但：

1. bootstrap 按既定语义**不存密码**，账号没有交互凭据；
2. 平台控制容器**未设置 `ENV ∈ {dev,test,local}`**，dev/test 的 `session.bootstrap` 引导通道在该容器上关闭；
3. 运行中的控制面 Odoo 仍服务 `SC_SOURCE_REVISION=10bf72ef`，本分支新增的决策路由尚未挂载。

两项待所有者裁定（不得用直接改模型、伪造批准、复用 `admin` 或放宽机制替代）：

- **A**：新增一条受管的一次性交互凭据（由声明的受管步骤签发、经产品 HTTP 入口使用、用后清除），
  并执行发布面收敛以挂载新控制器；
- **B**：由所有者本人以其交互登录完成批准。

**状态边界**：S3 批次与首次实跑（回读 + bootstrap）已完成并留证；**批准、operator provision、
载荷 plan/grant/import、对账、撤权、复核与主线集成仍未开始**。批次验收、主线集成、版本发布、
产品交付**均未完成**。

## 2026-10-16：裁决第 2 项的真实未完成点（证据引用绑定）

复核所有者裁定“授权记录至少绑定请求人、独立批准人、目标租户与数据库、操作集合、有效期、原因及证据引用”
时发现：前六项已绑定，**第七项（证据引用）并不存在**。记录里没有任何字段承载“本次授权依据哪一条决定”，
于是一次批准的语义只能靠外部叙述，账本单独一行读不出它凭何成立。这是裁决第 2 项的真实缺口，
不是新能力扩展。

### 交付（P0，`smart_core`）

| 层 | 改动 |
|---|---|
| 治理词汇 | `security/database_governance.py` 新增证据引用词汇与 `validate_maintenance_evidence()`：非空、10–200 字符、单行、拒绝会打断 ssh 载荷的字符（与身份 bootstrap 的 `--evidence` 同一套约束，避免两套方言） |
| 模型 | `sc.platform.maintenance.access` 新增 `evidence_reference`（请求时声明，之后只读）；写入、`_write_state` 读回、查询投影三处都携带它 |
| 入口 | 产品入口 `/api/ops/maintenance/access/request` 转递 `evidence_reference` |
| 常量归并 | `models/platform_database_registry.py` 原本重复声明 `SECURITY_ADMIN_GROUP` 字面量（同一 addon 内第二份），改为从 `security/platform_admin.py` 单一来源导入。属边界卫生修复，不新增能力、不改变行为 |

### 验证（层级 / 命令 / 非零计数）

前置：新列需要一次受管升级 `make local.dev.upgrade MODULE=smart_core CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_core`
（PASS；未升级时用例如实报 `column "evidence_reference" ... does not exist`）。

| 层 | 命令 | 结果 |
|---|---|---|
| L2 (HTTP) | `make verify.smart_core.platform_maintenance_access.orm` | **0 failed, 0 error of 15 tests**（原 14，+1） |
| L2 (ORM) | `make verify.local.dev.platform_database_governance.orm` | **0 failed, 0 error of 26 tests**（原 24，+2） |
| L1 | `make verify.controller.boundary.guard` | PASS |
| L1 | `make verify.platform.database.governance.guard` | PASS，17 tests OK |

### 反例验证（注入缺陷 → 必须失败 → 逐字节还原）

| 注入 | 结果 |
|---|---|
| 去掉 `_create_access_request` 里的证据校验 | `test_a_maintenance_request_must_cite_the_authority_it_rests_on` 5 个 subtest FAIL |
| 入口不再转递 `evidence_reference`（传空串） | HTTP 套件 10 处 FAIL |

两轮注入后均以 `sha256sum -c before.sha256` 逐字节还原（5 个文件全部 OK）。

**边界**：本节只关闭裁决第 2 项的缺口，不改状态机语义、不改批准独立性、不新增入口。
**唯一暂停点不变**：批准执行仍需所有者裁定审批人凭据路径（A/B）。批次验收、主线集成、版本发布、
产品交付均未完成。

## 2026-10-16：duty 凭据采纳层收口（demo 应用重启死循环，`5e12f313`）

本次是第一次三库 plan 之后的第二次回读暴露的真实缺陷。**它不是栈定义写错，而是这个 duty 接管了一个它并未创建的集群。**

### 现象与根因

| 事实 | 值 |
|---|---|
| nginx / db 容器 | `running` |
| odoo 容器 | `restarting`，日志 `FATAL: password authentication failed for user "odoo"` |
| duty 声明、渲染 env、custody、模块状态 | 全部一致 |

`sc_demo` 与其 `odoo` 角色早于本 duty 存在：角色口令留在 `sc_dev_db_data` 卷内，无法从集群回读。
duty 于是为该角色**新渲染了第二个口令**，应用便以自身数据库拒绝的密码反复重启——其余所有回读仍然报健康。

探针另有一层陷阱：`pg_hba` 对 `local`/`127.0.0.1` 是 `trust`，容器内直连**任何口令都会 AUTH_OK**，
只有走容器网络地址（demo = `192.168.32.2`）才构成认证事实。

### 交付（P4，`config/ops` + `scripts/ops`）

| 层 | 改动 |
|---|---|
| 声明 | demo 新增 `credential_source`（`env_file=/opt/projects/repos/sce-product-odoo/.env.dev`、`key=DB_PASSWORD`、`reason`、`owning_task=DAILY-RUNTIME-DEMO-APP-ROLE-01`）；这正是声明已登记为 `frontend_build_env_file` 的同一台日常 dev 环境文件。platform_control / customer_tenant_dev 未新增配置，未新增模型特判 |
| 校验 | `_validate_credential_source`：`shared_bootstrap_role` 必须声明 `credential_source`，`to_be_created` 禁止声明；`env_file` 必须是绝对文件路径且落在 duty 命名空间与本仓库 checkout 之外；`key` 必须属 duty 秘密材料；`reason`/`owning_task` 必填；拒绝未知键 |
| 单一解析点 | `credential_source()` / `declared_application_credentials()`：采纳的凭据同时用于凭据交付与 plan 探针；`duty_credentials` 采纳时同步写 `DB_PASSWORD` 与 `DB_MAINTENANCE_PASSWORD`；回执新增 `credential_adopted_from` / `credential_adopted_key` |
| 认证即独立事实 | `container_network_address()` + `application_credential_facts()`：经容器网络地址以采纳口令 `psql SELECT 1`，口令只走进程环境（`-e PGPASSWORD`）、不进 argv；plan 新增断言 `declared_application_credential_authenticates_the_cluster` |

### 验证（层级 / 命令 / 非零计数）

| 层 | 命令 | 结果 |
|---|---|---|
| L1 | `make verify.daily.runtime.database.duty` | **117 tests OK**（原 100，+17），0 failed |
| L2（修复前） | `daily.runtime.database.duty.plan` | demo **FAIL**：`declared_services_are_running`、`application_container_reads_the_declared_runtime_environment` |
| L3 | 受管 refresh（`SELECTION=demo` + `DECLARATION_DIGEST=3ebb2e19…`） | demo **PASS**；容器重建后 `ENV=dev`/`SC_ENVIRONMENT=dev`/`DB_USER=odoo`，`DB_PASSWORD` 已对齐，odoo/db/nginx 全 **healthy** |
| L2（修复后） | 同上（三库全选） | **三库全 PASS**，`declaration_failures=[]`，deployment_binding PASS |

凭据回读（plan 报告内）：三库 `authenticated: true`；demo `from_source: true`，`source=/opt/projects/repos/sce-product-odoo/.env.dev`。
运行时只读回读：`18081/web/login → 200`；`/api/ops/tenants → 403`（产品 JSON，非 500）；`18082/api/ops/maintenance/access → 403 PERMISSION_DENIED`（路由可用）；
odoo 日志 `base already installed; skip bootstrap`。

证据目录：`.runtime/agent-runs/DAILY-RUNTIME-VERSION-RELEASE-AND-USER-ACCEPTANCE-20261015/duty-credential-adoption-20261016/`
（`plan-adoption.json` / `apply-refresh-demo.json` / `plan-after-refresh.json`）。

### 登记但不属本轮

- `DAILY-RUNTIME-DEMO-APP-ROLE-01`：demo 仍是 `shared_bootstrap_role`，为它建立独立应用角色会改写 live dev 凭据，需独立授权。
- 维护授权执行链路（签发凭据 → 以 `lidefend` 批准 → operator provision → plan/grant/import/verify → revoke/clear）尚未开始。

**状态边界**：批次验收（duty 凭据采纳层）可声明；**主线集成、版本发布、产品交付均未完成。**

## 2026-10-16 受管 duty 模块升级阶段（upgrade）

### 现象与根因

维护授权链路要在目标环境落地，需要先把控制库的模块升到部署树版本，但仓库内**没有任何受管入口**能做这件事：

- 控制库 `sc_platform_control` 的 `smart_core` 停在 `17.0.1.1.14`，部署树源码为 `17.0.1.1.15`；
- 因此 `sc_platform_maintenance_access` 表缺 `evidence_reference` 列，而维护授权要求批准时必须绑定证据引用；
- 现有 `refresh` 明确**只重渲染栈、不重写 schema**（`make/codex.mk` 的注释与 `refresh_refusal` 都如此），`initialize` 只服务 `service_face=to_be_initialized` 的 duty。

所以这是授权链路之后的真实阻塞，不是便利缺口。这一层不引入任何产品侧特判，也不改声明。

### 交付

| 关注点 | 实现 |
|---|---|
| 阶段与令牌 | `PHASES` 增加 `upgrade`；`PHASE_CONFIRMATIONS` 显式登记 `(SC_CONFIRM_DAILY_RUNTIME_DUTY_UPGRADE, UPGRADE_DAILY_RUNTIME_DUTY_DECLARED_MODULES)`。`main()` 对未列出阶段回退到创建令牌，不显式登记就会让 `upgrade` 接受 `PROVISION` 令牌而被读成创建 |
| 拒绝表 | `upgrade_refusal`：拒绝 `to_be_created`、`service_face != initialized`、集群未运行、`base` 未安装、无声明模块的 duty |
| 恢复点先于改写 | `capture_duty_recovery_point`：在该 duty **自己声明的** `storage.backup_namespace` 下落 `pg_dump -Fc --no-owner`（0600），算 `sha256`，并用**自身集群**的 `pg_restore --list` 验证可列；未验证成功即拒绝进入改写 |
| 只改声明集合 | `upgrade_declared_modules`：只用 `-u` 升级声明模块集（不取命令参数，避免把 `-u` 变成偷偷安装）、`--without-demo=all`；成功后 `docker restart` + `compose up -d --wait odoo` 并回读模块状态——报告一次服务进程尚未加载的升级是主张，不是观察 |
| 断言 | `evaluate` / `plan_verdict` 新增 `a_verified_recovery_point_precedes_the_upgrade`、`the_declared_module_upgrade_completed`，只在 `upgrade` 阶段出现 |
| Make 入口 | `daily.runtime.database.duty.upgrade`（`guard.prod.forbid` + `verify.daily.runtime.database.duty`，要求 upgrade 自有令牌 + `SELECTION` + 已评审声明摘要） |
| 台账登记 | 该零引用运维入口登记为 `ops_runbook` / `platform-team`；基线按守卫文档的 reviewed-batch 重写路径重测，**仅** `max_targets_zero_reference 785→786`、`recorded_targets_defined 2334→2335`、`recorded_targets_unreached_from_anchor 2165→2166`，身份集只多这一项 |

### 验证（层级 / 命令 / 非零计数）

| 层 | 命令 | 结果 |
|---|---|---|
| L1 | `make verify.daily.runtime.database.duty` | **123 tests OK**（原 117，+6：`upgrade_refusal` 全拒绝矩阵、upgrade 自有令牌、恢复点先于改写且经 `pg_restore --list` 验证、只 `-u` 声明集合、升级断言仅在 upgrade 阶段、`verdict()` 支持 `upgrade=`） |
| L1 | `make verify.verification.lane_coverage` | **PASS**（72 tests OK），仅上述三项计数按登记增长 |

`render_remote_program` 渲染可 `compile`、无残留 marker；`upgrade_refusal` / `capture_duty_recovery_point` / `upgrade_declared_modules` 各仅 1 处定义；`make -n daily.runtime.database.duty.upgrade` 展开到 `--apply --phase upgrade`。

### 边界

阶段实现与台账登记已提交（`f3ceb6cf`），但**尚未在目标环境实跑一次 upgrade**；维护授权链路本身仍未开始。

## 2026-10-16 安全管理员凭据落盘机制修复（credential-entry）

### 现象与根因

维护授权链路已推进到“签发 `lidefend` 一次性交互凭据”这一步，但签发在**真实运行**中失败，且留下了一个不可用状态：

| 事实 | 值 |
|---|---|
| 首次签发结果 | 失败，但账号口令已 `commit` |
| 后续 `remote_readback` | `has_stored_password: true`、`maintenance_access_rows: 0` |
| 再签发 | `_identity_guard` 以 `ALREADY_ISSUED` 拒绝 |

两条独立缺陷：

| 缺陷 | 说明 |
|---|---|
| 落盘目标不可写 | 旧入口把凭据写到 `/mnt/artifacts/...`。该目录是 `${SC_PRODUCT_ROOT}/artifacts` 的 bind mount，宿主属主 `ci:ci`、权限 `2755`；容器内 Odoo 以 `odoo(101)` 运行，**没有写权** |
| 顺序错误 | `_run_issue` 先 `env.cr.commit()` 提交口令，再 `_write_credential_file()`。写文件失败后，口令已提交却无人知晓，而入口又拒绝重新签发——环境被锁死在一个“有口令但没人知道”的身份上 |

本地 dev 容器在同一位置复现同一缺陷，说明这是**通用机制缺陷**，不是日常服务器的偶发环境问题。

### 交付（P4，`scripts/ops`）

| 层 | 改动 |
|---|---|
| 落盘位置 | `DEFAULT_OUTPUT` / `OUTPUT_ROOT` 改为 `/var/lib/odoo/credentials`：`/var/lib/odoo` 是 duty 自己的数据卷，runtime 账号拥有、无 group/world 可读，只有宿主管理员可从外部到达 |
| 先验目标 | 新增 `_assert_output_writable()`（建目录 + `os.access(W_OK)`），在**任何账号写入之前**执行；不可写即 `PLATFORM_SECURITY_ADMIN_CREDENTIAL_OUTPUT_UNWRITABLE` |
| 先落盘后提交 | `_run_issue` 改为先 `_write_credential_file()` 再 `env.cr.commit()`；commit 失败时 `_remove_credential_file()` 清掉那份没人能用的副本 |
| 挂载表回读 | `inspect_odoo_container` 新增 `mounts`（destination → type/source/name/rw），把容器路径映射到宿主路径，**不另立第二份声明** |
| 签发即回读 | carrier 新增 `credential_host_path()` / `credential_file_fact()` / `assert_credential_file()`：issue 必须回读到 `present + mode 600`，clear 必须回读到消失；`assert_entry_result` 断言入口写出的路径就是声明的路径 |
| 回读而非自证 | carrier 以刚回读的挂载表把容器路径映射成宿主路径，再回读文件自身的 mode/属主/大小：入口自称已写出而实际未落盘、或副本不是 operator-only，都会被拒绝而不是被报告 |

### 验证（层级 / 命令 / 非零计数）

| 层 | 命令 | 结果 |
|---|---|---|
| L1 | `make verify.platform.security_admin.credential` | **48 tests OK**（原 43，+5：受管目录唯一、失败写入不留凭据、目标先备好、不可写目标在任何落盘前被拒、凭据文件先于账号提交落地、不可写即不提交） |
| L1(peer) | `make verify.daily.duty.payload` | **26 tests OK**（`mounts` 回读改造） |

### 边界

这是**边界治理发现的基线缺陷修复**，不是 payment/runtime 业务能力扩展。签发凭据不等于批准：授权台账在签发前后行数断言不变，入口本身也断言 `approves_maintenance_access is False`。

### 追加修复：clear 无法到达“无凭据”状态

真实驱动 `remote_clear` 时暴露第二个缺陷：`res.users.write({"password": False})` 抛
`TypeError: secret must be unicode or bytes, not bool`。

| 事实 | 值 |
|---|---|
| 语义 | `res.users.password` 是 compute + inverse：无论写什么，inverse 都会 `ctx.hash()` 后落库 |
| 后果 | `False` 在哈希库内直接炸；写 `''`（Odoo 自身账号删除路径的写法）会存下**空口令的哈希**，列仍非空，读回仍是 `has_stored_password=true` |
| 单元测试 | 假 `_User.write` 只记录不校验，所以 43/48 全绿也从未证明 clear 能生效 |

修复：新增 `_clear_stored_credential()`，用 `UPDATE res_users SET password = NULL` 把列恢复成**创建时的状态**，
`invalidate_recordset(["password"])` 使 ORM 不再从旧哈希作答；`token_version` 是普通存储字段，仍走 ORM 在同一事务内递增。

反例：假环境现在按真实语义拒绝非字符串口令（回归到 ORM clear 即失败），并模型化“写 `''` 之后列的哈希仍非空”。

| 层 | 命令 | 结果 |
|---|---|---|
| L1 | `make verify.platform.security_admin.credential` | **50 tests OK**（原 48，+2：clear 经 SQL 到达无凭据态且不动凭据文件、被弃用的 ORM 写法确实不可用） |

## 2026-10-16 维护授权真实跑通 + 下游三条声明 + 载荷交付缺口

所有者裁决（2026-10-16）把 `lidefend` 定为授权人，并把维护授权定位为 **P0 产品能力**，不得用一次性 shell 代替。
本节记录该裁决的四项要求在真实环境的落地结果。阶段身份：`HEAD=d92d75e8` 加显式 dirty 范围（迭代期口径）。

### 一、授权链路走产品 HTTP 入口

| 阶段 | 入口 | 结果 |
|---|---|---|
| 申请 | `POST /api/ops/maintenance/access/request`（`admin`，平台管理员） | PASS：`access_id=1`、`state=requested`、`requested_by=admin`、`approved_by` 空、`capability=migrate`、`db=<customer-tenant-db>`、`authorized_operations=[provision, grant]`、`operator=smart_core.svc_tenant_payload_operator_<tenant_key>`、`subject_checksum=f1adc6fb…` |
| 审批 | `POST /api/ops/maintenance/access/approve`（`lidefend`，安全管理员） | PASS：`state=approved`、`approved_by=lidefend`、窗口 `2026-10-15 20:43:20 → 2026-10-16 08:43:20`（UTC，即北京时间 08:43:20 到期） |
| 查询 | `GET /api/ops/maintenance/access` | 200、`count=1`、`state=approved` |

裁决要求的七项绑定中，请求人、独立批准人、目标租户与库、操作集合、有效期、原因、证据引用全部落库；
`evidence_reference` 在申请时声明、之后不可写。

### 二、真实环境反例

| 反例 | 结果 |
|---|---|
| 自批拒绝 | `403 PERMISSION_DENIED`：申请人 `admin` 批自己的行被入口先拦 |
| 无角色拒绝 | `403 PERMISSION_DENIED`（同上，本例与自批在入口层同源） |
| 未认证拒绝 | approve / read 均 `403 PERMISSION_DENIED` |
| 服务端自有字段 | `400 MAINTENANCE_ACCESS_SERVER_OWNED_FIELD:approved_by,state`：请求体命名裁决人或状态被**拒绝**而非静默忽略 |
| 重复执行 | `400 DBGOV1_MAINTENANCE_ACCESS_NOT_REQUESTED:approved`，前后台账行不变 |
| 审计不可伪造 | 命名裁决人的请求体被拒；申请人本人无法裁决；台账 `requested_by` / `approved_by` 在所有被拒调用前后均未变化 |
| 目标替换 | 受管入口 `make daily.runtime.duty.operator_grant.remote_provision` 用**非批准摘要**驱动 → `BLOCKED: the approved access is bound to another subject than this run`；入口先读授权并断言全部绑定，再执行生命周期命令，因此拒绝发生在任何写入之前 |
| 证据引用词典 | 证据引用含被禁传输字符 → `400 DATABASE_GOVERNANCE_MAINTENANCE_EVIDENCE_INVALID_CHARACTERS`，台账仍为 1 行，拒绝即零写入 |
| 窗口过期（窗口外） | 06:11:20 回读台账：`access_id=3` 仍为 **`approved`**（证明是**窗口**而不是撤销使它失去覆盖）→ 06:11:22 受管入口同主体重跑 → `BLOCKED: the platform control database holds no approved, in-window maintenance access for this duty: the lifecycle refuses to fabricate one`（exit 2，**写入前**拒绝） |
| 窗口内对照（A 侧） | 05:13:24 同一受管入口在同一行窗口内运行 → `exit=0`、`created=false`、`writes=0`、`approval_access_id=3`；与上面的窗口外拒绝构成同一行上的 A/B |
| 过期清理 | 06:11:32 `POST /api/ops/maintenance/access/expire` → `200 count=1 expired=[(3,'expired')]`；台账回读 `['revoked','rejected','expired','revoked','revoked']`——过期行由**受审清扫**迁移，不是就地改写 |

**诚实限制**：HTTP 层无法单独观测“独立性”规则——当前唯一平台管理员 `admin` 不持有安全管理员组，
因此在角色检查处就被拒，到不了 `DBGOV1_MAINTENANCE_APPROVER_MUST_BE_INDEPENDENT`。
该规则本身由 `make verify.smart_core.platform_maintenance_access.orm`（15 tests OK）覆盖。

证据：`.runtime/agent-runs/…/maintenance-access-approval-20261016/approval-flow.log`
（sha256 `3ad626ffcb314ad893b3e71831598a08cd2ae9a5f9b3f72761305e5d818b5a2b`）、
`.runtime/agent-runs/…/maintenance-access-decay-20261016/decay-flow.log`、
窗口 A/B 与清扫：`.runtime/agent-runs/…/maintenance-access-decay-20261016/out-of-window-20261016.log`
（窗口内对照侧见同目录 `control-provision.log`，`tool_sha=3aac7395…`；窗口外侧 `head=70a89a03…`，
两者之间唯一改动是 grant 守卫的幂等分支，不在审批闸门上）。

### 三、操作员消费方缺陷修复（提交 `d92d75e8`）

首次真实跑 `provision` 暴露的是**消费方**缺陷，不是机制缺陷：

| 项 | 事实 |
|---|---|
| 根因 | 回读把 `required_group_closure_xmlids`（声明组的平台自身传递闭包）作为事实发布，消费方却用两元素硬白名单 `{base.group_user, importer}` 比对账号的**有效**组集合。`res.users.groups_id` 存的是有效集合（直接组 ∪ 隐含闭包），机制自己刚创建的账号永远无法满足该白名单 |
| 后果 | `provision` 在写事务内已提交身份，随后后置断言失败 → 报 `BLOCKED` 却已写入；且账号一旦存在，之后所有动作（含只读 `readback`）都在 before 断言处失败 → **入口永久死锁** |
| 修复 | 改为按已发布闭包判定：`{base.group_user} ∪ {声明 importer 组} ∪ 已发布闭包 ∪ 声明组`；未发布闭包时**拒绝**而非放宽；并补正向断言（声明要求的组必须实际持有） |
| 验证 | `make verify.daily.duty.operator_grant` → **81 项 OK**（`test_tenant_payload_operator_policy` 39 + `test_daily_runtime_duty_operator_grant` 42；该子模块在 `d92d75e8` 由 39 增到 41，本批再 +1 个幂等用例，见 S2-2） |
| 反例 | 改回两元素白名单 → 3 failures + 3 errors；恢复后 `sha256sum -c before.sha256` OK |

### 四、下游三条声明（授权之后）

| 声明 | 入口 | 结果 |
|---|---|---|
| 生效版次 | `make daily.runtime.duty.edition_release.remote_publish` | **PASS**：`snapshot_id=2`、`version=daily-navigation-standard-b80841059b19`、`state=released`、旧快照转 `superseded`、`snapshot_effective_page_count=90`、`policy_menu_count=90`；`smart_core.platform_release_db` 仍为 `<customer-tenant-db>`（租户持有生效快照，未取得平台发布权） |
| 操作员身份 | `…operator_grant.remote_provision` | **PASS 且幂等**：`created=false`、`writes=0`、`approval_access_id=1`、uid 6、无口令、无原生 API Key、非 data operator |
| 窄授权 | `…operator_grant.remote_grant` | **PASS**：仅新增 `smart_core.group_smart_core_tenant_payload_importer`，`membership 5→6`、`writes=1`、`importer_implied_xmlids=[]` |

### 五、载荷交付缺口：`TPV1_CUSTOMER_ADAPTER_INCOMPATIBLE`

`make daily.runtime.duty.payload.remote_plan` 在授权与授权之后各失败一次：
第一次 `TPV1_IMPORT_OPERATOR_AUTHORIZATION_MISSING`（预期，授权尚未建立）；
第二次 `TPV1_CUSTOMER_ADAPTER_INCOMPATIBLE`（真实阻断）。

定性前先读了三个权威来源（只读）：

| 权威 | 事实 |
|---|---|
| 载荷 | `<customer-payload-id>`，`customer_module_version=17.0.2.7.0`，`source_version=authorized-odoo17-snapshot-v1`，`payload_checksum=f1adc6fb…` |
| 已交付客户模块 | `/opt/sce/tenant-addons/daily/bfbc736c…/<customer-module>`，`__manifest__.py` 与 `customer_module_manifest.json` 均为 **17.0.2.8.0** |
| 已安装模块记录 | `<customer-tenant-db>` 内 `ir_module_module.<customer-module>` = `installed` / **17.0.2.8.0** |
| 适配器来源 | `customer_delivery_config.py:39` 把 `customer_module_version` 从模块自身 `customer_module_manifest.json` 投影出来，所以适配器声明与模块版本**构造上一致** |
| 其它载荷 | 载荷库内其余载荷均声明 17.0.2.6.0 / 17.0.2.7.0；**没有任何载荷声明 17.0.2.8.0**；已交付树只有 `40b67f99`（17.0.2.6.0）与 `bfbc736c`（17.0.2.8.0） |

**裁定：载荷过期，机制正确。** 两个校验都不冗余：`_validate_adapter` 绑定「模块代码 ↔ 载荷」，
`_assert_customer_module` 绑定「已安装模块记录 ↔ 载荷」，三者必须一致。当前租户实际运行的版本没有任何对应载荷，
放宽适配器等于让产品接受一份针对**从未在此交付过的模块构建**编写的载荷。

- **归属**：载荷生产、签名与版本对齐属**用户模块（P2/P4 载荷交付）**。产品仓库不另建客户专用回填，也不放宽适配器。
- **下一步**：在 `customer_module_version=17.0.2.8.0` 下重新出包并重新签名（或由模块声明其仍接受的载荷模块版本范围），
  然后用**新摘要**重新申请一次维护授权——当前授权绑定 `f1adc6fb…`，且窗口 08:43:20 到期。

**登记未修**（本轮不扩大）：

1. `superseded_payload_status` 由生产载荷携带，但 `addons/`、`scripts/` 下**没有任何消费点**；
   它想表达的效力实际由模块的 `rejected_payloads`（`payload_id` + `payload_checksum` + `reason_code`）实现，两者词汇不同。
2. `schemas/tenant_delivery/customer_payload_manifest.schema.json` 声明 `additionalProperties: false`，
   但生产载荷携带该 schema 之外的键，而运行时校验器只强制具名键、不拒绝未知键——**已发布 schema 与执行中的 schema 已漂移**。

### 六、本轮复核处置（S2-1 / S2-2 / S3）

复核对象：`3aac7395` 加本工作区改动。结论：**无 S1**；两条 S2（需修）、六条 S3（观察）。

**S2-1：证据计数低于源码 —— 修法是重跑，不是改数字。**

| 项 | 事实 | 处置 |
|---|---|---|
| 过期原因 | 三个 L2 结果出自 01:17 的日志，而 `test_platform_maintenance_access_http.py` / `test_platform_database_governance_orm.py` 在 `e75d3713`、`a52ba6d3` 又各加了用例（+3 / +2）。**过期的是证据，不是写错的数字** | 三个 L2 目标在**同一候选**上重跑：`L2-rerun-20261016.log` → 入口 15、模型 26、关系链 20，逐项 `0 failed / 0 error` |
| 口径错误 | `bootstrap` 记 `31+41=72`（实为 `31+44=75`）、`operator_grant` 记 `39+39=78`（实为第二模块 41，含本批 +1 幂等用例后为 42 → **81**）。两处都是**拿子脚本的数当目标合计**或没随子模块增长重取 | 按目标自身输出重取：`required-tests-counts-20261016.log`；本文件计数表与 `run.json` 同步 |
| 附带影响 | 反例表的三行（`14 error(s) of 12` / `4 failed of 12` / `2 failed of 12`）是**按当时 12 用例集合**测得的版本绑定观测 | 已就地加注：数值不再是当前集合的比例，但每行都是真实触发的失败，守卫不空转的结论不变 |

**S2-2：操作员 grant 幂等缺陷 —— 守卫自相矛盾。**

| 项 | 事实 |
|---|---|
| 根因 | `assert_lifecycle` 用**声明**去比一次**幂等重跑**的结果：账号已持 importer 组时生命周期回 `changed=false`、`added=∅`，被判"加了声明未命名的组"→ 机制把自己锁死（真实账号上观测到）|
| 自相矛盾 | 同一段守卫先接受 `changed=false`，随后又要求 `added` 必须非空 |
| 修复 | 按报告的 `changed` 分支：`changed=true` 才与声明比对（越界仍拒绝）；`changed=false` 只要求**有效集合没有增长** |
| 用例 | 新增 `test_a_grant_already_in_place_adds_nothing`：幂等重跑必须接受；`changed=false` 但集合变宽必须拒绝 |
| 验证 | `make verify.daily.duty.operator_grant` → **81 项 OK**（第二模块 42） |

**S3 处置**：S3-1（`window_ab` 的三个阶段已全部由实测取代：窗口内对照 PASS、窗口外在被拒时该行**仍为 `approved`**、
过期行由受审清扫迁到 `expired`）、
S3-2（独立性规则补"（模型层）"限定）**本轮关闭**；S3-3（闭包自描述上限）、S3-4（`_active_access`
取一行可能误拒）、S3-5（私有 `_request_access(requester_id=…)`）、S3-6（非数字入参 500 应为 400）
**登记待办**，理由逐条写入 `run.json` 的 `review_s2_closure_round3_20261016.S3_disposition`。

### 七、本轮收尾（窗口 A/B、操作员回读、凭据清理）

| 项 | 事实 | 证据 |
|---|---|---|
| 窗口 A/B | 同一产品创建的行 `access_id=3`（1 小时窗口）：窗口内 05:13:24 `remote_provision` PASS（exit 0、writes 0、消费该行）；窗口外 06:11:22 同主体被拒，且拒绝时该行**仍为 `approved`** | `control-provision.log`、`out-of-window-20261016.log` |
| 过期清扫 | 06:11:32 `POST /api/ops/maintenance/access/expire` → `count=1 expired=[(3,'expired')]`；台账 `['revoked','rejected','expired','revoked','revoked']` | 同上 |
| 操作员回读 | 受管 `remote_readback`：`writes=0`、`is_importer=false`、importer 成员数 0、无隐含闭包；持有组仅 `base.group_user` 的内部用户闭包；`has_stored_password=false`、无原生 API Key、非 data operator；生效版次仍为 `snapshot_id=2` | `readback-post-revoke.log` |
| 一次性审批凭据清理 | 受管 `credential.clear`：`writes=1`、`has_stored_password` true→false、凭据文件 `present=false` 且已移除；`group_ids` 与安全管理员身份不变（uid 6）、`groups_outside_allowed_closure=[]`；台账 5 行**保留**（撤销的是"能力"，不是"审计"） | `credential-clear.log` |
| 运行身份与权限边界 | `/opt/projects/secure/daily-runtime-duties/`：目录 `drwx------ root ci`，四个文件均 `-rw------- root root`；平台控制库凭据目录已空（`credentials/` 无文件） | 只读 `ls -la` 输出 |

**边界**：清理之后**没有**可用的一次性审批凭据，因此本轮不可能再发生新的批准。这是意图内的状态：
载荷已过期、进口无法进行，临时能力必须收回，而责任记录（账号、组、台账行）全部保留。

### 八、阶段口径

可声明：**批次验收**（授权链路与下游两条声明的产品能力已按受影响集合验证）。
**未完成**：主线集成、版本发布、产品交付。载荷未入库，因此客户开发租户的数据对账（12386 / 6322 / 29 / 6035）与业务闭环验收尚未开始。
