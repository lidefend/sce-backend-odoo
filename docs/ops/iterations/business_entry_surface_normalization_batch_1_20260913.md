# Batch-1 项目资料办理面交付记录

## 2026-09-23 F0 → F1 当前批次（本节优先于历史验收结论）

目标：自定义前端成为正式业务入口；89 个正式入口均有去向，按职责取得真实操作及权限证据。
基线 `61b8d7121b28d1e1f9126e7c03ab01bce57cee62`；分支
`feature/frontend-business-entry-closure`；产品运行候选为 clean `9b3d65d201ec1198e7c867909b83677570b66d9c`，由 P1 `92885722`、P0 `78367373`、P4 `9b3d65d2` 三提交组成；此后更新三份台账及 P4 发布工具三路径，不改变产品运行证据输入。尚未完成 PR 最终冻结与远端验证。

- 唯一入口矩阵：[frontend_business_entry_acceptance_v1.csv](../../product/frontend_business_entry_acceptance_v1.csv)。复用锁定菜单策略的 89 个稳定 XML ID，关联旧覆盖数据，不重新扫描全仓。旧数字 action/menu ID 不作为当前环境权威。
- 唯一缺口清单：[frontend_shared_foundation_gap_audit_20260909.md](frontend_shared_foundation_gap_audit_20260909.md) 的 F0/F1 当前节；本文件为唯一当前批次记录。历史归档不重写为本轮通过。
- F0 去向：86 项本轮验收（项目资料 F1，其余 F3）；3 项会计入口因旧覆盖表缺少同身份行，明确阻塞 G-F0-02。零无归属、零未经确认排除。旧表额外的 WBS 和旧业务映射不扩大本轮范围。
- 角色列保留后端菜单链与 action group 权威，不能当作登录角色或最终写权限；实际账号、company、ACL、record rule 随每项旅程绑定。`ready/structural/readable_fallback` 仅为历史实现描述，所有业务验收状态起始 `not_run`。
- F1 范围：项目资料进入、查询、名称/日期/说明/责任明细编辑、保存、刷新回读、错误定位、权限拒绝及失败草稿恢复。未保存草稿跨刷新持久化不在承诺范围；保存不推进项目生命周期。

所有权：F0 证据登记与环境恢复属 P4；项目标准规则属 P1 `smart_construction_core`；通用执行属 P0 `frontend/apps/web`。沿 Decoder → Store → Resolver → Runtime → Registry；规则由后端裁决，前端不补业务语义。当前只修真实反例暴露的项目名称校验：P0 编辑提交按契约 required 校验实际提交字段；P1 `project_core.write` 在副作用前拒绝显式空名称。不改 schema、权限、数据库结构或默认路由，不加入前端模型名判断；无须模块升级，受管重启加载 Python。F2 竞态/occurrence 与 F4 美化后置。

本轮文件边界：P0 `saveRecordHelpers.ts`、`valueUtils.ts` 与已有 `create_record_user_journey_test.ts`；P1 `models/core/project_core.py` 与已注册 `test_project_state_transition_validation.py`；P4 既有项目写入 browser `.mjs/.sh`、fixture `.py`、对应单元测试，以及本文、缺口清单、89 项矩阵。风险：共享编辑校验影响所有契约表单；通过非零 required 类型/局部更新反例和项目实测控制影响。回滚按 P0/P1/P4 提交分别回退，测试对象按命名空间清理。

发布阻碍的最小追加范围：P4 `scripts/ops/gitee_formal_pr.py`、`make/codex.mk`、`scripts/verify/test_gitee_formal_pr.py`。现有创建器固定旧CI分支，当前业务候选无法使用；仅将branch/title/body文件参数传入同一身份、ledger和回读链，新专题ledger按分支摘要隔离，旧专题ledger继续沿用。属交付工具而非P0-P3业务规则，不改远端服务、检查、权限、合并或部署。新增文案经环境变量作为shell字面量传递；独立审查发现的直接拼接风险已修，并用实际Make wrapper反例覆盖。该范围不依赖/改变frontend、handler、fixture或runtime，因此携带`9b3d65d2`产品证据，无须重复业务写入。

环境：复用 `local.dev` / `sc-local-dev` / `sc_dev_demo` / `^sc_dev_demo$` / 18081，候选静态前端 5176；数据库角色为隔离持久开发租户，非客户生产、非控制库、非行业目录。filestore 为 `sc_local_dev_odoo_data`，数据库和 Redis 卷沿用 `sc_local_dev_*`。凭据只来自受管 `.env.dev`，不复制、不轮换。测试对象仅 `codex_p4_project_profile_write` 命名空间的 `frontend-f1-20260923`；不重置数据、不创建用户。

### 当前结果索引

2026-09-23用户补充巡检后调整：`fd6fb975076c81ba4d6d61db3b773b9b604e3354`已完成独立复核和推送预演，未推送/未创建PR。新证据暴露F1客户交互阻断，暂停发布和最终收口；继续同分支/同台账迭代，不继承该候选的整体可发布结论。已通过的名称校验与权限结果仍保留原身份，后续按共享依赖影响选择复验。

接续顺序：①F1客户完整任务，先分离查询/选中/明确创建，补输入后blur/ESC/取消不修改、明确选中/创建、查询失败恢复与有效保存；同时修下拉遮挡和焦点自动重开。②紧接处理B02日记账JSON详情阻断，归属F3提前解除入口阻塞，不能以文本控件吞JSON。③F2处理B03通用返回与既有竞态/occurrence，补两种来源路径及取消/离页反例。三个主题顺序执行，不并行美化；新增缺口统一登记G-F1-07/08/09、G-F3-02、G-F2-04。

B01首轮修复（迭代身份`fd6fb975`加19路径dirty）：普通输入/blur/无候选Enter及fallback change不登记创建；只有显式创建产生独立pending意图，真实reload/discard清除，收藏保存不取消。响应式pending投影统一参与hasChanges、字段计数及离页保护。搜索弹窗错误不呈现空态或允许确认旧行，列加载/行查询均有取消代次。复用ScPopover解决祖先层叠，保留焦点恢复并抑制自动重新展开。后端通用搜索不自动纳入原生搜索视图的非存储虚拟过滤器（显式投影/扩展仍保留）；受管日志`/tmp/frontend-f1-relation-diagnostic-20260923.log`确认旧请求由phone_mobile_search短词校验抛UserError。无业务模型特例、无schema/数据库升级。

本轮定向结果：实际关系状态9反例、dirty/离页5反例及原required10/旅程6检查点通过；关系生命周期原12例+搜索失败/乱序/关闭3例+列延迟取消重开1例通过（`/tmp/frontend-f1-relation-state-l2-20260923.log`）。后端38例中新增测试首次缺fake env，补测试依赖后该1例通过，原37例复用（`/tmp/frontend-f1-relation-search-l2-20260923.log`、`/tmp/frontend-f1-relation-search-l2-r2-20260923.log`）。关系呈现/生命周期门禁通过；新增明确清除按钮后同步现有guard期望。受管runner33例通过。首次关系旅程脚本变量重名构建失败已改块级作用域，结果见`/tmp/frontend-f1-relation-intent-l2-r2-20260923.log`。独立复核发现的fallback提交、草稿对象误作代次、失败确认旧行和延迟列污染均已修复；实测仍not_run，准备新候选载体。P4仅在既有runner增加专用对象RELATION_ONLY互斥模式并回读partner_id，不触碰用户管理员会话或草稿。

B01受管复验绑定`ae69871e0cb619d9eab579acee08b7f747ed71b4`，专用批次`frontend-f1-rel-20260923`、项目3928：查询AB后失焦，草稿未修改且写请求为0；随后再次展开失败，整次结果为failed（`/tmp/frontend-f1-relation-browser-20260923/summary.json`），不继承单测通过为验收通过。只读诊断初次聚焦浮层存在，再聚焦aria-expanded=true但浮层DOM缺失（`/tmp/frontend-f1-relation-refocus-diagnostic-20260923/summary.json`）；依赖源码确认关闭动画onAfterLeave在destroyOnClose下卸载容器。恢复变更限定P0 ScPopover可配置挂载策略，默认保持原值，many2one快速关闭/重开保留浮层容器；内容仍由isOpen控制。风险为所有关系选择消费者，不改业务/契约/数据，最早验证L1+关系L2，随后仅复验受影响客户旅程。诊断脚本临时采集已移除；用户管理员草稿未操作。

边界：客户状态和浮层为P0现有ProfessionalMany2oneFieldControl/useRecordFormState/useRelationRuntime及RelationSearchDialog；查询/错误分类为P0 smart_core通用handler，后端拥有搜索/错误语义，前端只执行。会计JSON先核验类型契约来源再决定Resolver/Registry或后端修复；导航沿现有Runtime，不写客户/会计/收款特例。风险覆盖所有many2one消费者，L1语法/静态→L2关系字段/生命周期非零定向测试→受管客户真实旅程；原F1名称/权限证据只在相关输入未变时携带。广泛浏览器矩阵、完整Quick和远端发布在已知前层阻断消除前不运行。

基线运行结果绑定 `61b8d712`；修复后运行结果绑定 `9b3d65d2`，定向测试绑定提交前相同源码及明确 dirty 范围。后续仅文档变化不使产品测试失效。L0/L1/L2 是本地迭代证据，不代表部署或远端 CI。

| 层 | 命令/证据 | 结果 | 归因和下一步 |
| --- | --- | --- | --- |
| L0 | preflight + worktree/HEAD | passed：起始 clean，唯一工作树 | 从 main 精确基线建立专题分支 |
| L1 | `make ci.local.iteration` | passed：16 tests | 推荐器按旧 origin/main 提示 86 个历史路径；本轮不采纳为扩大范围的依据 |
| L2 | `python3 -m unittest scripts.verify.test_local_dev_project_profile_write_fixture` | passed：29 tests | 验收工具原有安全边界 |
| L2 | `make verify.frontend.create_record_user_journey.unit verify.frontend.canonical_form_presenter.unit` | passed：6 旅程检查点；170+10 呈现用例 | `/tmp/frontend-f1-l2-20260923.log`；不替代真实写入 |
| L0 环境 | `make local.dev.ready local.dev.health` | 首次 failed：HTTP 403 | environment_defect：运行容器仍挂载已退役的旧专题目录 |
| L0 恢复 | `make local.dev.up`；`SC_SOURCE_REVISION=<基线完整 SHA> make local.dev.up` | passed | 复用原 project/库/卷，重新挂载当前代码；补齐运行态版本声明，无模块升级 |
| L0 恢复核验 | `make local.dev.health` | passed | `/tmp/frontend-f0-health-20260923.log` |
| L3 载体 | `CANDIDATE_GIT_HEAD=<基线 SHA> CONFIRM_LOCAL_DEV_CANDIDATE_FRONTEND=SERVE_FROZEN_LOCAL_DEV_CANDIDATE make local.dev.candidate.frontend.up` | passed | `/tmp/frontend-f1-carrier-20260923.log`，只构建当前业务验收载体 |
| L0 精确运行身份 | 同上身份参数 `make local.dev.candidate.frontend.health` | passed（首次因版本未声明拒绝，恢复事实见上） | `/tmp/frontend-f1-identity-recovered-20260923.log`；后端源码/版本/库/filestore 同候选 |
| L3 对象准备 | `make local.dev.project_profile_write_fixture P4_PROJECT_PROFILE_MODE=prepare P4_PROJECT_PROFILE_BATCH=frontend-f1-20260923 P4_PROJECT_PROFILE_CONFIRM=PREPARE` | passed | 项目 3919、公司 1、责任明细 26/27；pm1 写 ACL/规则允许；只读账号 ACL 拒绝。`/tmp/frontend-f1-prepare-20260923.log` |
| 批次业务复核 | `local.dev.project_profile_write_browser`，项目 3919 | passed（保存/恢复子范围） | `/tmp/frontend-f1-browser-r2-20260923/summary.json`：网络失败草稿保留、真实重试、完整明细回读与刷新一致；生命周期未变 |
| 清理 | 同批次 `cleanup` → `inspect` | passed | `/tmp/frontend-f1-cleanup-20260923.log`、`/tmp/frontend-f1-after-cleanup-20260923.log`；项目3919及责任明细27/28已清理，批次不存在 |
| 权限子范围 | `PERMISSION_ONLY=1 … local.dev.project_profile_write_browser`，项目3920 | passed | `/tmp/frontend-f1-permission-r2-20260923/summary.json`：user37/company1，实际 role_code=project_member；直接同值 write 403/PERMISSION_DENIED、权威事实不变；精确目标转入NAVIGATION_AUTHORITY_DENIED拒绝页 |
| F0 安装版本 | fixture inspect | passed | `/tmp/frontend-f0-installed-version-20260923.log`：smart_core 17.0.1.1.12、smart_construction_core 17.0.0.168，state=installed，与源码一致 |
| F1 字段反例 | 项目3920清空名称并保存 | failed：product_defect | `/tmp/frontend-f1-counterexamples-20260923/summary.json`：系统编号只读通过；name空字符串却写入成功，触发P0/P1修复。该专用对象已cleanup，见`/tmp/frontend-f1-auth-cleanup-20260923.log` |
| L2 P0 修复 | `make verify.frontend.create_record_user_journey.unit` | passed | 编辑空文本/隐藏已提交字段/关系必填/未修改历史空字段，独立审查又补required boolean=false合法反例；`/tmp/frontend-f1-required-l2-boolean-20260923.log`，10新增用例+原6检查点 |
| L2 P1 修复 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS=<3个完整方法>` | passed（3方法合计） | 首次前缀选择0 tests判失败；精确选择3方法中批量拒绝通过，2方法因Html规范化断言失败；只改测试比较规范化前值，重跑2方法通过。原始日志`/tmp/frontend-f1-name-l2-exact-20260923.log`、`/tmp/frontend-f1-name-l2-html-20260923.log`，不掩盖失败 |
| L2 P4 | `python3 -m unittest scripts.verify.test_local_dev_project_profile_write_fixture` | passed：31 tests | 增加专用对象权限反例模式的越界拒绝测试；原有范围/身份门禁保持 |
| L0/L3 修复后身份 | 同受管入口重启后端与候选前端并 health | passed | `/tmp/frontend-f1-fixed-identity-20260923.log`，源码/载体均 `9b3d65d2`，复用原库与卷 |
| F1 修复后 | `PERMISSION_ONLY=1 … local.dev.project_profile_write_browser`，项目3927 | passed：6场景 | `/tmp/frontend-f1-fixed-counterexamples-20260923/summary.json`：编号只读；必填错误零写请求且草稿可编辑；直接API空名称拒绝且同请求description不落库；改正保存及刷新一致；只读角色直接write403和精确拒绝页。业务校验仍为500/INTERNAL_ERROR，另记G-F1-06 |
| 清理 | `frontend-f1-fixed-20260923` cleanup → inspect | passed | `/tmp/frontend-f1-fixed-cleanup-20260923.log`、`/tmp/frontend-f1-fixed-after-cleanup-20260923.log`；项目3927及责任明细31/32清理，existing_batch=false |
| L2 P4发布 | `make verify.gitee.formal_pr.unit` | passed：11 tests | `/tmp/frontend-f1-pr-publication-l2-literal-20260923.log`；含新专题准确创建/回读、无效元数据拒绝、实际Make字面量传递与保留的不确定写入防重复边界 |
| L5 | 独立复核 / 远端 CI / 合并 | 产品局部、P4追加及15路径公开范围复核passed；CI/合并 not_run | 产品summary SHA256 `4cd9af17796bb0df80adebea19dbd569f23b80f8282ffb8aeacffcb0f21e1c92`；仅允许F1首个局部补丁进入集成，不代表全F1通过 |

高风险写入前已确认对象命名空间、库与公司及原始明细；收尾必须用同批次 `cleanup` 检查引用、清理并 `inspect` 回读。开发实测不升级为目标环境部署验收。

独立复核：已确认P0布尔false不能视空并补反例，P4按钮计数必须绑定精确拒绝页（已修），5个form-only入口不虚构列表职责（已修）。项目原生视图来源可承接；较历史候选变化的decoder/presenter/页头/关系/导航只保留历史观察，不冒称当前验证。新字段校验仅影响保存前置；已有网络错误处理/明细序列化未改，正向原证据保留来源，修复后补实际保存与刷新。

当前状态：F0 范围去向已登记、受管版本核验完成；F1 名称校验、失败草稿恢复、成功回读及权限拒绝子范围已实测，F1全部验收未完成｜未合入｜未部署｜用户验收未完成。剩余F1包括表单级/服务端错误的页面恢复，以及隐藏伴随字段、附件载荷；重复/取消/离页和occurrence反例在F2收敛后回验本任务。初步排期以工作量而非组件数估算：F1补齐上述反例并关闭错误分类；F2至少2个独立机制修复（竞态、occurrence），各需定向反例与项目回归；F3按89项职责逐域排期，3项会计入口先解除身份阻塞，目前不承诺整体完成日期。

[English](business_entry_surface_normalization_batch_1_20260913.en.md)

## 1. 本轮变更

- 目标：关闭项目资料办理面的正式入口、真实保存和网络失败恢复链。
- P1：项目资料字段、日期范围、说明、责任明细及资料保存/生命周期动作边界。
- P0：共享保存错误把浏览器原始 `Failed to fetch` 本地化为可操作的网络错误提示，不含项目模型特例。
- P4：受管 `local.dev` 专用数据生命周期、正式菜单旅程、单次写请求阻断、失败/重试分段报告、实际控件快照和主记录/责任明细权威回读。
- 未完成：浏览器无权角色拒绝反例因既有凭据不可用保留为未覆盖；Batch-2 未启动。

## 2. 影响范围

- 模块：`smart_construction_core`、共享 contract-form 前端、`scripts/verify`、`make/dev.mk`。
- 启动链：仅修复项目经理既有授权菜单的运行时投影，不改变认证或公司上下文。
- contract/schema：不新增 schema，不绕过契约；沿用 `ui.contract.v2` 与 `api.data op=write`。
- 路由：正式菜单使用 `menu 681/action 861`；不把手拼路径作为授权入口。
- 数据：仅操作 `sc-local-dev/sc_dev_demo` 中受管专用批次，未使用项目 2/8 写入。

## 3. 风险与边界

- P0：网络错误文案为共享前端行为；定向测试约束其不泄露原始浏览器错误。
- P1：资料保存不推进生命周期；本次回读保持 `draft`。
- P4：runner 的正常保存和失败恢复期望已分离；恢复 PASS 要求失败前后实际控件值及明细操作一致、主记录及责任明细内容未变、错误元素真实可见；两次浏览器尝试中仅一次到达后端并成功。
- 未覆盖：无权角色浏览器反例。既有后端权限证据继续复用，但不替代该浏览器缺口。

## 4. 验证

- `python3 -m unittest scripts.verify.test_local_dev_project_profile_write_fixture`：PASS，13 项。
- `create_record_user_journey_test.ts` 经仓库现有 esbuild 入口执行：PASS。
- 受管失败恢复：PASS。首次请求被阻断；错误摘要元素真实可见并单独截图；失败前后名称、双日期、说明和责任明细控件快照一致，明细保持新增/修改/删除三类操作；主记录全部涉及字段及责任明细角色、人员、备注均与初始化事实一致。同会话重试业务成功，权威回读与刷新全量一致。
- 预收口 `make ci.local.quick`：在生成报告门禁前的守卫均通过，随后因新增测试导致 test inventory 陈旧而按预期失败；已使用 `make refresh.generated_reports` 对齐。最终 exact-head Quick 由冻结候选的受管 receipt 和独立评审包记录，不在本文预声明结果。

## 5. 产物

- 浏览器摘要：`/tmp/p4-recovery-evidence-0913/summary.json`。
- 可见错误元素截图：`/tmp/p4-recovery-evidence-0913/failure-feedback-visible.png`。
- 失败态整页截图：`/tmp/p4-recovery-evidence-0913/failure-before-retry.png`。
- 成功刷新截图：`/tmp/p4-recovery-evidence-0913/recovery-after-refresh.png`。
- 摘要 SHA-256：`e27df862a76c680f5be2b1016b6ba0ed2888fb4889520bd1760556cd4e91a0ce`。

## 6. 数据处置与回滚

- 批次：`recovery-evidence-0913`；项目 374。
- 清理：PASS，项目与责任明细 `[24,25]` 已由受管入口删除，`clean=true`；后续 inspect 确认批次不存在。
- 回滚：按提交边界反向回退 P4 runner、P0 错误本地化和 P1 入口/页面提交；无需业务数据库回滚。

## 7. 下一步

- Batch-1 已归档。PR #465 最终 HEAD 为
  `73842d9248867599a54f9ce4647381b2ab59ea28`，其后于初始交付候选增加三项审查修正：
  共享字段/P4 runner 缺口关闭、组件接管清单刷新、登录角色与业务角色判定分离。
- 最终 PR HEAD 的 `frontend_release_gate`、`merge_policy_gate`、
  `professional_quality_gate`、`public_guard` 与 `release_candidate_gate` 均为
  `SUCCESS`。GitHub 没有人工 review 记录；独立代码复核与 CI 证据不得表述为
  GitHub 人工批准。
- squash 合并提交为
  `dbf1e171281bd920c39099be7085718c892b10f4`；最终 PR HEAD 与合并提交的 tree
  均为 `2f52649c86587c94e9dfbc1e318538eca41741e2`，产品内容一致。
- Batch-2 另行实施；不再重跑 Batch-1 浏览器保存链。
