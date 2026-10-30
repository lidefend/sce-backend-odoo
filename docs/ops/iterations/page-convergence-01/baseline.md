# PAGE-CONVERGENCE-01 · TASK-01 基线

生成时间：2026-10-30 Asia/Shanghai

## 1. 运行基线（真实日常开发服务器）

| 事实 | 值 |
| --- | --- |
| 日常开发服务器入口 | http://1.95.85.92:18081/t/demo |
| 部署源码 SHA | `1640a7e1b19349be6490f6055c26955b4a468853` |
| 本地 `main` HEAD | `1640a7e1b19349be6490f6055c26955b4a468853`（一致） |
| 数据库 | `sc_demo`（duty=demo，namespace_id=ns_000000000002） |
| 前端构建指纹 | `8f7cc076e0d9510feb2ea8b713cf45ea9aee0941c73cb46feea243bcb81d0012` |
| 产品版本 | `1.0.0-rc.20` |
| 环境 | demo（tenant 面） |
| Odoo 版本 | 17（仓库上下文 `addons`，容器镜像 `odoo17-odoo`） |

本地 `local.dev`（`127.0.0.1:18081`，库 `sc_dev_demo`）运行的是旧 SHA
`63fb6ecb946b6fe6466f4cb340119491a5d9bd2f`，不是本轮真实基线，只作为本地迭代车道使用。

## 2. 工作区与分支

- 仓库根：`/home/lidefend/workspace/sce-backend-odoo`
- 基线时分支：`main`，工作树干净（`git status --porcelain=v2` 为空）
- 本轮分支：`feature/page-convergence-01`（自 `main` 创建，尚未有提交差异）
- 权威远端：`origin` = https://github.com/lidefend/sce-backend-odoo.git；`gitee-mirror` 仅镜像

## 3. 样板页身份

项目详情页的真实产品入口是「项目台账」记录页，不是原生 `project.edit_project` 默认表单。

| 项 | 值 |
| --- | --- |
| 菜单 | `smart_construction_core.menu_sc_project_project`（项目台账，menu res_id=382） |
| 动作 | `smart_construction_core.action_sc_project_list`（action res_id=588，`view_mode=tree,kanban,form`） |
| 表单视图 | `smart_construction_core.view_project_overview_form`（project.project.form.sc.overview） |
| 前端路由 | `/r/project.project/{id}?action_id=588&menu_id=382` |
| 代表记录 | id=10，城北新区安置房项目（在建阶段），`lifecycle_state=in_progress` |
| 业务账号 | `pm1`（张建国，uid=10，项目经理，项目负责人） |

后端另有只读入口 `action_sc_project_overview` 与默认 `project.edit_project` 继承表单
（`view_project_form_sc_core` + `view_project_form_sc_profile_layout`）。本轮以
`view_project_overview_form` 为唯一样板，不动其余入口的字段语义。

## 4. 当前页面结构（pm1 / id=10，桌面 1440px 实测）

自上而下：

1. 页头：主标题「城北新区安置房项目（在建阶段）」；状态区「查看」；操作区「返回 / 更多操作」；
   顶部有「项目中心 / 项目台账」菜单标签，页面内部无面包屑。
2. 概览身份区（`sc-project-overview__header`）：名称、项目编号、经营方式、经营性质、
   你是：项目负责人（项目管理员）、项目经理、业主单位、项目类型、上次更新日期、项目设置。
3. 阶段区：当前阶段（项目状态）；立项审批状态；「查看阶段要求」按钮（仅 draft 可见）。
4. 你现在最该做的事（next actions）。
5. 项目当前状态（概览）：**实测只渲染出成本 / 财务 / 项目任务三张卡片，「合同」卡片未出现**。
6. 基本信息：项目名称、项目编号、客户、项目类型、经营方式、项目地点、业主联系人、主合同编号、公司。
7. 计划与责任：单据日期、项目周期、计划开工日期、计划竣工日期、项目负责人、项目经理、成本负责人、资料负责人。
8. 责任矩阵：`responsibility_ids`（当前空态「暂无可展示记录」）。
9. 项目说明：description。
10. 协作资料：标签、合作者。
11. 系统追溯：分析账户、来源录入人、来源录入时间（默认折叠）。
12. 协作日志：沟通/备注/安排计划、关注者（19）、协作附件、消息与活动、评论。

## 5. 实测关键发现

### 5.1 契约缺口（P0/P1）

浏览器控制台出现两次：

```text
ContractGapError: 原生条件契约不可求值：dependency.lifecycle_state
```

来源为已部署前端 bundle `index-AXoDMlz5.js` + `contractStrictMode-CkpdmxBM.js`。后果可观测：

- 阶段区「当前阶段」字段值渲染为空（数据实际为 `in_progress`，页头徽标显示「在建」）。
- 概览区「合同」卡片整体缺失（后端字段 `sc_project_contract_entry_available=false`，前端
  契约未能把「合同」卡片及其空态渲染出来，只剩成本/财务/项目任务三卡）。

该缺口是页面信息层级失真的首要原因，应先于纯视觉调整处理。

### 5.2 字段值与页面呈现不一致（待核实为渲染/契约问题）

pm1 通过后端读 id=10 得到的值：

- `start_date=2026-10-28`，但页面「计划开工日期」显示「-」。
- `manager_id=张建国(uid10)`、`user_id=张建国(uid10)`，但页面「项目经理」「项目管理员」显示「-」。
- `owner_id=德阳市城市某某建设投资集团有限公司`、`project_type_id=基础项目类型`，页面显示「-」。

说明：真实字段值与页面呈现存在明显缺口，不能在视觉层“补值”，必须定位契约字段声明/消费。

### 5.3 头部信息重复与层级

- 页面内无面包屑，仅菜单标签「项目中心/项目台账」。
- 标题区「名称」字段与页头主标题重复表达同一项目名。
- 「项目编号」在身份区和基本信息区重复出现。
- 经营方式在身份区与基本信息区重复出现。

### 5.4 责任矩阵与协作记录

- 「责任矩阵」当前为空态；负责人/协作/关注者分属不同数据关系，当前视觉层级不足。
- 关注者当前 19 人（历史观察值，不作为写死值）。

## 6. 证据位置

- 截图：`.runtime/page-convergence-01/baseline/screenshots/project-10-{1440x900,1024x768,768x1024,390x844}.png`
- 结构化 DOM：同目录下 `project-10-*.json`
- 汇总：`.runtime/page-convergence-01/baseline/capture-summary.json`

（`.runtime/` 为忽略的运行时证据区，不入库。）

