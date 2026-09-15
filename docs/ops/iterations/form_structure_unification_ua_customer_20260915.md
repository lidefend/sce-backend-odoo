# U-A 与首个客户样板：实施记录

## 批次与基线

本批次交付目标是唯一结构机制与首个客户样板；U-B 其余三个代表面和 U-C 尚未验收。
Dashboard PR #476 的 squash `5545e5b3801ea5158852faa30bce278fd1827fe3`与
Tender PR #479 的 squash `9f7bb560917a98b638a6d2a516fe2542634fdff8` 已按主线顺序整合。
本工作树通过 `make workspace.branch.sync-main` 将未发布专题从 `0eb47763` rebase 到 `9f7bb560`，
保留客户章节及退役决策，候选初始 HEAD `c1d7d092c91220e39bfc1a8120892368083084f5`。
未复制补丁；基线完整指纹 `1119a9f5cbd1a9d25411a38ea61afe5e759a6fc4e91b78e1205dd9a0fdb91b8a`。

## 架构边界与顺序

| Formal Product Layer | Layer Target / Module | Standard vs User-Specific / Why Here | Why Not Elsewhere / Blast Radius |
|---|---|---|---|
| P0 | `smart_core` view orchestration、v2 projection、通用 Vue renderer | 平台结构解释与契约消费机制 | 无客户或施工章节特判；影响 native 正文、创建态、语义增强与字段限制 |
| P1 | `smart_construction_core` 客户原生 XML | 行业客户档案基本资料、联系人、账户、备注 | 不改变客户业务模型与事实来源；保留子表、附件、财务字段和动作 |
| P4 | 既有 fingerprint、定向测试、candidate visual-smoke、投影矩阵 | 冲突诊断、源码身份、整页截图与迁移证据 | 不新建 profile、端口、数据库、fixture 或测试入口 |

执行顺序：统一基线 → 契约/schema → 后端解释 → 前端消费 → 定向检查 → 原环境升级 → 冻结浏览器候选 → 客户样板与台账。
`login → system.init → ui.contract` 与 public intent 名称保持；前端仅使用 schema/store 的已声明权威。
风险：共享 P0 渲染机制；兼容路径保留至按入口归零，禁止用首批结果宣称全系统统一。

## 结构来源前后对照

| 环节 | 迁移前 | 本批次 |
|---|---|---|
| 配置解释 | orchestrator 应用一次，handler 再查有效配置并生成分组 | orchestrator 生成内部 normalized projection；handler 只复制已解析结果 |
| 正文结构 | native tree 与 formStructure slots 并存 | native 标记 `layoutPolicy=container_tree_authority`；唯一正文为 `layoutContract.containerTree` |
| 语义元数据 | slots/group/columns 可独立拥有结构 | native slots/fieldRoles 空集合；语义角色在现有树节点上标注，不重新归属字段 |
| 创建态 | 按字段类型、可编辑性分组后进入 native bridge | native floorplan 直接透传同一 primary/subordinate 节点；不拆分集合 |
| 正文与导航 | 部分入口采用不同分组来源 | 同一 canonical native bridge 节点生成正文和链接 |
| 配置冲突 | 简单错误字符串或隐式覆盖 | 配置 id/name、model/action/view、冲突 key、节点路径及竞争所有者；互补语义允许叠加 |
| 原生限制 | 字段策略可能放宽 readonly/required | 增强策略不能放宽原生静态或条件限制 |

客户四章：基本资料（内部业务组保留）、联系人、账户明细、附件与备注。
联系人和银行集合各归属原生 `col=1` 章节；保留 child tree/form、parent context、bank 编辑、附件 widget 与业务字段。
付款、投标配置未整份删除；后续迁移须先提取非结构能力。

## 验证状态与证据

原环境为 `local.dev` / `sc-local-dev` / `sc_dev_demo` / `^sc_dev_demo$`，filestore 为 `sc_local_dev_odoo_data`。
其他固定卷为 `sc_local_dev_db_data`、`sc_local_dev_redis_data`；凭据仅来自主工作树既有 `.env.dev`。
前端候选 5176 通过既有 API 18081；浏览器前必须检查 backend mount、SC_SOURCE_REVISION、模块 tree SHA 和数据库身份。
日常开发证据不是 release/最终发布验收；开发期不运行 Quick。

- L0：基线与各次完整 tracked+untracked 指纹保存到 `artifacts/form-structure-unification/*fingerprint.json`。
- L1：`make ci.local.iteration`；native/orchestration/form contract 三项边界守卫通过。
- L2：`make verify.form_structure_authority_unification.unit`、正文 presenter 与 native navigation 非零定向套件。
- L3：`make local.dev.upgrade MODULE=smart_core,smart_construction_core CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_core,smart_construction_core` 通过；记录 `module-upgrade.log`。
- L3：客户业务字段、迁移字段隔离两项 `local.dev.test`；首次失败见 `customer-module-tests.log`；恢复后 2/2 通过见 `customer-module-tests-recovery.log`。
- L3：真实客户 model/create → normalized 契约测试 1/1 通过；核对四章、关键集合/业务字段可见、原生标签与实际 view。
- L4：客户 1088/390 浏览器、正文契约树和整页截图由冻结后 runner 生成，结果以 `artifacts/form-structure-unification/customer-browser-complete/summary.json` 为准。
- L5：本批次尚未进入完整发布流程；四代表面与全系统统一均未登记通过。

初轮后端测试失败归因：旧 handler 重查/原生 slots 断言与新边界不符；已有测试缺失 field_label 参数。
更新测试夹具消费已解析结果、保留旧兼容场景后通过。投影矩阵原基线遗漏 formPresentationMode 已补齐。
后续纯 P4 证据变更不改变客户 XML、后端模块测试输入；承接证据需记录源/当前完整指纹。

## 消费者与退役条件

正式范围是两个产品共享的 89 个菜单，不能相加成 178。
基线静态载入且 XMLID 去重的 form 配置 254 条：143 entry、110 default、1 native。
配置数量不等于消费者数量。正式菜单静态候选组合：35 无配置、27 default+entry、14 default、12 entry、1 default+entry+native。
运行台账由既有 visual-smoke 读取正式菜单权威，并以当前用户、公司、实际 action 和 normalized form 解析逐项记录；
不把未显示/解析失败/非 form 入口当作已迁移，也不将 API 解析当作浏览器验收。

每行保留 menu、action、actual view、旧配置来源、迁移路径、所依赖兼容逻辑、批次和证据。
U-B 四面及共享反例后，U-C 按消费者清单分组递减；每批合入前更新数量，不得增加无退出条件的兼容分支。
正式范围兼容消费者为零且未决项为零后，删除 legacy slots 重组、旧前端 floorplan 分支及对应测试豁免。
回滚按 P4 证据、P0 机制、P1 视图提交边界逆序恢复；需要视图回退时仍走受管模块升级，禁止手工改库。

## 独立复核修复

1. 角色选择移到 orchestrator，使用 IdentityResolver 解析实际用户；不信任入参角色，也不恢复 handler 配置查询。
2. 付款模型级旧配置的竞争结构被明确诊断为 native view 抑制，仍有效的字段语义保留；此依赖计入 `legacy_configuration_structure_suppression`，不能记作付款完成迁移。native 自身或另一显式 action/view 结构所有者冲突继续失败。
3. 原生 readonly/required/invisible（含条件表达式）不可由字段增强放宽。旧字段策略新增仅限机制调用的原生限制保持参数。
4. normalized provenance 输出 resolvedViewId、resolvedActionId、structureDiagnostics、compatibilityDependencies。菜单清单仅代表指定角色/公司/create 投影；全部角色与 read/edit 尚未验证，禁止据此宣布最终退役。

原生 invisible 数据库反例 1/1 通过（`native-invisible-test.log`）；作用域诊断已覆盖实际整数 action/view carrier 与旧 record proxy。

## 创建态实测收口

浏览器揭示的第二结构路径：handler 创建态再次调用通用 governance，
由 core/advanced 推导字段可见性，造成原生章节存在而字段隐藏。
native authority 现跳过这次通用治理，继续保留显式分类策略、关系能力、原生权限相交，
以及独立的记录依赖按钮保护（wizard 例外）；不恢复字段类型或名称推导的章节。
原生 XML 明确可见的 active 保持可见；它的旧隐藏来自通用名称规则，不是原生权限。
company_type 不再被平台强制改名为“主体类型”，正文使用本次原生 view 的“客户类型”。

证据采集绑定实际新建页的 model 请求，保存请求身份、结构与 widget/container 状态；
台账按相同 model/create 路径采集。早期 action 口径的 49 个依赖只保留为诊断证据，
不作为最终创建路径数量。P4 首轮导航解析失败与客户章节失败保留原日志。

原生 bridge 的可见性也统一为 normalized status：旧 technical/hidden 语义不再二次隐藏原生 view
明确可见的负责人、国家/地区；node.visible=false、readonly 和已移交 header 的状态栏去重仍保持。
兼容分支维持原行为，等待正式消费者归零。对应 presenter/bridge 定向 169 项、navigation 28 项通过。

浏览器 P4 手动滚动现在会在吸顶栏位置变化后重新测量 anchor 并补滚，
不会点击导航或改写选中状态。TDesign 下拉检查使用其实际官方面板容器；
角色 listbox 选择器仍覆盖关系面板。早期失败报告不删除、不冒充通过。
