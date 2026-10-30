# PAGE-CONVERGENCE-01 · 实施计划（TASK-04/05/06）

## 0. 分层声明

- Formal Product Layer：P1（建筑行业标准产品面）。
- Layer Target：`smart_construction_core` 项目概览视图与字段声明；前端仅消费通用契约渲染。
- 不改：ACL、record rule、角色、业务数据、财务/进度计算字段。

## 1. 实现顺序（按证据优先级）

### A. 契约缺口 `dependency.lifecycle_state`（P1，先行）

- 定位 `view_project_overview_form` 中所有依赖 `lifecycle_state` 的原生条件
  （阶段状态字段、查看阶段要求/去补齐资料等按钮的 `invisible`、阶段要求 widget）。
- 在后端契约声明/组装层补齐 `lifecycle_state` 依赖声明，使前端可求值。
- 验收：页面不再抛 `ContractGapError`；阶段字段显示「在建」；「合同」卡片按权限渲染空态。

### B. 概览卡片统一（P1，后端视图 + 契约）

- 载体：`addons/smart_construction_core/views/core/project_overview_views.xml`。
- 保证四卡对业务角色均可渲染；`sc_project_contract_entry_available=false` 时显示「当前账号
  发布范围未提供项目合同列表入口」，不允许整卡消失。
- 统一卡片标题/数值/单位层级（前端通用组件已有卡片/stat 组件，优先复用）。

### C. 基本资料六组拆分（P1，后端视图）

- 载体：同上视图的 `<group>` 结构，把「基本信息」「计划与责任」拆为六组并保持 `col=4` 两列。
- 保持字段 xmlid、groups、readonly 属性与 `data-sc-anchor` 语义锚点。

### D. 页头层级（前端通用组件）

- 载体：`frontend/apps/web/src/components/product-page-header/ProductPageHeader.vue` 与其调用方。
- 面包屑由菜单树提供；身份区去重由契约字段输出驱动，不在前端写死字段名。

### E. TASK-06 查看阶段要求只读化（P1，后端方法）

- 现状：`project_core.py: action_view_stage_requirements` 创建临时向导
  `sc.project.stage.requirement.wizard`，pm1 无向导 create 权限 → 403。
- 方案：复用只读 `sc_get_stage_requirements(limit)`；改为返回只读展示，不创建临时记录。
- 落地：后端新增/改为返回只读 `ir.actions.act_window`（目标模型 `sc.project.stage.requirement.item`，
  只读 tree，domain 按 `lifecycle_state` 过滤），或在动作呈现层把该 object action 映射到
  `sc_get_stage_requirements` 的只读 Vue 查看入口。
- 验收：正常查看阶段要求；无权限时明确提示；不产生业务记录；返回详情正常。

## 2. 验证阶梯

- L1：`make ci.local.iteration` + 受影响 py/xml 语法与契约守卫。
- L2：`verify.frontend.project_detail_summary.browser` 等已有定向入口（若输入未变可复用）。
- L3：仅当改动后端视图/方法时，`local.dev.upgrade`（`CODEX_NEED_UPGRADE=1`）后 smoke。
- L4：本地迭代浏览器观察受影响页面；最终冻结候选再跑完整视口矩阵。
- 最终：Quick、独立复核、`make pr.push`（本任务不自动合并/部署）。

