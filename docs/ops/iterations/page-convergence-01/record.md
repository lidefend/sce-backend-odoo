# PAGE-CONVERGENCE-01 · 批次记录

状态：active（批次进行中；主线/部署/用户验收均未发生）

## 阶段身份

- 分支：`feature/page-convergence-01`
- 基线：`1640a7e1b19349be6490f6055c26955b4a468853`
- 本轮工作树：分析文档 + 受管 `.agent` 运行元数据；产品代码尚未修改。

## 已完成

- TASK-01 真实基线核对：远程日常服务器身份、页面身份、4 视口截图与 DOM 证据。
- 契约缺口与「合同」卡片缺失的定位；TASK-06 根因定位。
- 目标设计与实施计划定稿（本目录）。

## 未完成 / 下一步

1. ~~修 `dependency.lifecycle_state` 契约缺口~~（已完成代码修复，待运行时验证）。
2. 概览四卡统一（含合同卡片空态）。
3. 基本信息/计划责任六组拆分。
4. 页头层级与操作分组。
5. TASK-06 只读化。
6. local.dev 定向验证 + 远程浏览器验收 + 独立 PR。

## 证据

- 运行身份：`docs/ops/iterations/page-convergence-01/baseline.json`
- 截图：`.runtime/page-convergence-01/baseline/screenshots/`

## TASK-05.1 已实施

- 根因：`hydrate_final_modifier_dependencies` 批量 `record.read(missing)` 中，
  `sc_stage_required_done/total` 计算链触及 pm1 无权限的 `project.funding.baseline`，抛
  AccessError 被整体吞掉，导致 `lifecycle_state` 等所有可读依赖字段一起缺失。
- 修复：改为逐字段读取并单独容错；单个被拒字段 fail-closed，其余可读依赖字段继续水合。
- 载体：`addons/smart_core/core/unified_page_contract_v2_modifier_dependencies.py`
  （P0/P1 通用契约水合层，不写死页面语义）。
- 回归测试：`addons/smart_core/tests/test_ui_contract_v2_boundaries.py`
  `PYTHONDONTWRITEBYTECODE=1 python3 .../test_ui_contract_v2_boundaries.py` → 159 tests OK。
- 待运行时验证：local.dev 升级 smart_core + 候选前端，确认阶段状态与合同卡片恢复。

## TASK-05.1 运行时验证（通过）

- 候选前端 127.0.0.1:5176 绑定提交 `397a3b4da`；本地后端已加载修复。
- 探针（pm1，project 21）结果：`status=200`、`tokenKey=true`、`hasLifecycle=true`、
  `lifecycleValue=in_progress`；`mainData` 从 0 个关键依赖字段恢复，`start_date`、
  `manager_id`、`user_id`、`project_type_id` 均已水合。
- 遗留（进入 TASK-05.2 处理）：`owner_id`（仅存在于概览身份头块，不在标准布局水合闭包）、
  `sc_overview_contract_count`、`sc_project_contract_entry_available` 对 pm1 仍缺失，
  需在四卡收敛时按其权限与空态一并处理。

## 职责边界纠偏（2026-10-30）

- 保留：TASK-05.1、`f334f112` 合同卡片权限隔离、`79fd6010e` 隐藏 fact 字段有界水合。
- 暂停：通用条件子树保留策略与组装器修改。
- 独立诊断：`docs/ops/iterations/page-convergence-01/contract-field-fact-diagnosis.md`。
- 恢复配置驱动收敛：四卡视觉、六组基本信息、计划责任、责任协作、四视口；配置不生成业务事实。

## 方向固定（platform-driven productization）

- 方向记录：`docs/ops/iterations/page-convergence-01/platform-driven-productization-charter.md`。
- 后续迭代以真实业务页面为中心、以现有配置能力为首选、以用户实际体验为验收终点。

## P1-R5 持久化资产与真实请求关联（完成，只读）

- 结论：2288 与 2290 是不同模型（`project.project` vs `project.collaborator`）的运行时契约
  资产，不是同一页面的旧/新版本；项目详情请求命中 2288。
- 2288 持久化 token `031fb909…` 与当前重算 token `5f599729…` 不一致，`get_runtime_source_asset`
  用当前 token 查询 2288 返回 miss；资产匹配与失效机制正常。
- 陈旧内容来源：升级前启动、未随 `local.dev.upgrade` 重启的长驻服务进程，其
  `contract_code_fingerprint()` 按进程缓存，以陈旧指纹/ORM 缓存组装并持久化了旧页头契约。
- 交付：`p1-r5-asset-request-correlation.md`、`p1-r5-asset-request-correlation.json`。
- 下一步 P1-R6：用已重启进程重新组装并三视口浏览器验收，确认页头去重生效。

## P1-R6 三视口 DOM 验收（通过，P1 关闭）

- 后端新契约：`sc-project-overview__header` 字段仅 `project_code / business_nature / user_id /
  manager_id / owner_id / project_type_id / write_date / location`，无 name、无 operation_strategy、
  无 sc-project-title。
- 浏览器三视口（1440/1024/390）：h1 唯一（项目名主标题）；页头无名称/经营方式字段；「项目名称」
  仅项目身份组出现 1 次；「经营方式」仅业务主体与项目属性组出现 1 次；三视口均无横向溢出；控制台
  错误 0。
- 交付：`p1-r6-acceptance.md` + `.runtime/page-convergence-01/p1-r6/` 证据。
- 固化工程标准：模块升级后的运行时验收顺序（升级前快照 → 受管升级 → 确认 DB 视图 → 确认进程加载
  新代码 → 重读运行时指纹/契约身份 → 浏览器验收）。
- 下一步 P2：六组基本信息专业化布局。

## P2 六组基本信息专业化布局（核心完成）

- 实施：六个基本信息 group 的原生列数 `col="4"` → `col="2"`（仅布局声明，字段/分组/权限/顺序不变）。
- 验证链路：`make local.dev.upgrade MODULE=smart_construction_core`（77 模块加载）→
  `make local.dev.restart`（服务进程 09:48:38Z 重启）→ 契约按 `columns=2 / span=12` 输出。
- 四视口（1440/1024/768/390）DOM 验收：六组 2 字段/行（390 单列）；标签宽 137px → 274px（1440）；
  无横向溢出；控制台错误 0；h1 唯一；经营方式=1、项目名称=1。
- 遗留（单列跟进，非六组范围）：页头「项目编号」「· 经营性质」静态文本与只读 facts 字段标签重复
  （`nolabel="1"` 未在只读 facts 路径生效）。
- 交付：`p2-information-layout-design.md` + `.runtime/page-convergence-01/p2/` 证据。
- 下一步 P3：四卡视觉收敛与空态统一。

## P3 四张概览卡片专业化收敛（完成）

- 实施：四卡改为语义 token（`sc-project-card__*`）+ 渲染器 scoped 样式；修正
  `hasRenderableDescendant` 使纯文本权限空态可渲染（合同卡不再被误判为空壳隐藏）。
- 数据边界：合同卡按 `sc_project_contract_entry_available` 呈现权限空态；成本/财务/任务保持
  「数据暂不可用」；无伪造 0；结果 B / 组装器 / 解析器 / ACL / 计算口径未改。
- 四视口（1440/1024/768/390）：4/行、4/行、2×2、单列；无横向溢出；控制台错误 0。
- 定向测试：`verify.frontend.native_text_presentation.unit` PASS（21 cases）；
  `verify.frontend.native_form_structure_responsibility.unit` 为既有失败（`activePageIndex` 断言过期），
  与本轮无关，记为 pre-existing。
- 交付：`p3-overview-cards-design.md`、`p3-overview-cards-implementation.md` +
  `.runtime/page-convergence-01/p3/` 证据。
- 下一步 P4：责任矩阵与协作区域。

## P4 责任矩阵与协作区域（完成）

- 实施：仅一处布局声明——协作资料组 `col="4"` → `col="2"`（项目标签/协作者各半宽）；
  责任矩阵保持 `col="1"` 整行、三列可编辑树不变。
- 验证：四视口无横向溢出、控制台错误 0；责任矩阵空态、关注者动态计数 20、
  附件/评论/活动由现有协作组件完整呈现；契约实测 `协作资料 columns=2 / span=12`。
- 边界：未改 ACL/record rule/业务数据/人员关系/组装器/解析器/结果 B；未新增 CSS/Vue/协议。
- 有数据时的责任矩阵列层级（岗位可识别、责任人强调、说明换行）与协作者/关注者填充态待 P6
  用真实数据最终验收。
- 交付：`p4-responsibility-design.md`、`p4-collaboration-design.md`、
  `p4-collaboration-implementation.md` + `.runtime/page-convergence-01/p4/` 证据。
- 下一步 P5：阶段要求只读前端呈现最终验收。

## P5 阶段要求只读前端呈现（完成）

- 根因：tree-only 只读 act_window 已正确路由 `/a/822`，但 `context={create:false,
  edit:false, delete:false}` 未投射到列表操作入口，导致「新建」误显。
- 修复：仅改 `ActionView.vue`——解析路由 `context_raw`，`canCreateRecord`/`canEditRecord`
  消费 create/edit 显式关闭声明。不新增渲染器、不硬编码模型、不改后端/ACL/组装器/解析器。
- 验证：真实点击后 `data-can-create=false`、`data-can-edit=false`，「新建」消失；5 条记录
  全部 `lifecycle_state=in_progress`；无 400、无向导、控制台错误 0。
- 定向测试：`verify.frontend.collection_action_toolbar.unit` PASS（31 cases + 11 tests）；
  付款申请新建入口不受影响（上下文未声明 create:false）。
- 交付：`p5-stage-requirements-implementation.md`、`p5-stage-requirements-acceptance.md` +
  `.runtime/page-convergence-01/p5-probe/` 证据。
- 下一步 P6：整体产品验收（责任矩阵/协作者填充态、四卡与基本信息视觉衔接、四视口整页回归）。
