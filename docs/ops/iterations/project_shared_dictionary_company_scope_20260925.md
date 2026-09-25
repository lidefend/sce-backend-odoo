# 项目共享字典不再按 project_ids 推断公司范围（标签显式创建可见性修复）

## 身份与边界

- 基线 `827fad4bd927c8be22bf940d24937bb2c07f4796`（实时 Gitee main）。本记录随代码提交，非冻结发布候选。
- Formal Product Layer: P0。Layer Target: `smart_core` 记录上下文/业务范围域（`core/project_context.py` 的 `_company_scope_domain`）。
- 归属理由：把模型字段误读成公司边界属于平台范围推断错误，不属于前端渲染、动作 domain、工作表域或客户模块配置。
- Blast Radius：`_company_scope_domain` 的 `project_ids` 分支此前只被 `project.tags`、`project.task.type`、
  `project.task.type.delete.wizard` 命中（三个模型都无 `company_id`）。改动只取消这一处推断，不触及
  `company_id`、`project_id.company_id` 分支。
- 未新增环境、未新增备份、未重建数据库；本地只跑定向检查，完整 CI 交远端 PR。

## 根因

`_company_scope_domain()` 在模型声明 `project_ids`（`project.project`）且无 `company_id` 时返回
`[("project_ids.company_id", "=", company)]`。但 `project_ids` 是 Odoo 原生的"使用/共享"关系，不是所有权：

- `project.tags` 有全局唯一名称，`_name_search` 用 `project.context['project_id']` 只做"最近使用"排序并带 fallback；
- `project.tags` 没有 `company_id`，**也没有任何 `ir.rule`**（ACL 按用户组授权读/写/建），
  `project.task.type` 只有 `user_id` 相关规则，同样没有公司规则。

因此平台层凭空造出一条公司边界，把尚未挂到本公司项目的记录（含刚创建的标签）全部隐藏。

## 修复前实测（目标环境 `1.95.85.92:18081`，DB `sc_demo`，部署 `827fad4b`）

只读探测 + 一次创建后回滚（`/tmp` 探针，归档见下）：

| 对象 | 结果 |
|---|---|
| `business_scope_domain(project.tags, company_id=1)` | `[('project_ids.company_id', '=', 1)]` |
| `project.tags` 总数 / 该域可见 | 12 / **11** |
| `project.task.type` 总数 / 该域可见 | 7 / **0** |
| 新建标签（`project_ids=[]`）在该域可见 | **0**（去掉域后可见 1） |
| `project.tags` 是否有 `company_id` / `ir.rule` | 否 / 无 |
| `payment.request` 域（未受影响） | `['|', ('company_id','=',1), ('project_id.company_id','=',1)]` |

`project.task.type` 0/7 说明舞台选择器在同一域下同样恒空；新建标签 0 可见正是"新建标签后搜不到、面板
持续提供创建入口并重复创建"的直接原因。

## 修复

- `addons/smart_core/core/project_context.py`：删除 `project_ids` 公司推断分支并写明依据；
  共享字典回到由模型自身 ACL / 记录规则治理，公司归属模型继续走 `company_id` 分支。
- 无需前端改动：控件继续使用官方 Select 的候选与创建入口，未添加本地缓存假选项。

## 验证

- 定向单测：`python3 addons/smart_core/tests/test_project_context_boundaries.py` → 23 OK（新增
  共享字典不被公司约束、公司归属模型仍按 `company_id` 收敛两条断言）。
- 工具单测：`python3 -m unittest scripts.verify.test_local_dev_project_profile_write_fixture` → 43 OK。
- 轻量静态：`make ci.local.iteration` → PASS（`coverage=L1_only`）。
- 受管浏览器（`M2M_ONLY=1 PROJECT_ID=4065`，tool `02a5ae28`，served build `147bc5d7`）：
  **23/23 PASS**，其中本轮新增：
  - `m2m_create_option_is_offered_for_an_unknown_name`：无精确匹配时面板只给创建入口，
    `search_term` 与受管查询一致（HTTP 200）。
  - `m2m_create_option_creates_and_selects_the_record`：唯一写模型为 `project.tags`，
    `vals.name` 命中关键词，未写 `project.project`，权威 `tag_ids` 保持不变（草稿态）。
  - `m2m_created_tag_is_authoritative_in_the_relation_query`：同一受管查询下新建标签**被精确召回**，
    创建入口行数 **0**（修复前此处恒为 0 条选项 + 1 条创建入口）。
  - `m2m_created_tag_saves_and_reads_back`：保存 → 刷新回读 `tag_ids` 与草稿一致
    （`[30,32,33]`，其中 33 为 UI 新建）。
- 修复后本地探针：`project.tags` / `project.task.type` 域为 `[]`，新建标签在范围内可见 1；
  `payment.request` 公司域保持不变。

## 证据与清理

- 归档目录：`artifacts/ci/handoff-20260925/target-acceptance-827fad4b/tag-create-visibility/`
  （目标环境修复前缺陷探针、本地修复后域探针、23 场景 summary 及其 sha256、两张截图、
  夹具 prepare/cleanup/inspect 回执、身份与角色/公司上下文）。
- 夹具回收：`deleted_carrier_id=4066`、`deleted_tag_ids=[30,31,32]`、`deleted_marker_tag_ids=[33]`
  （UI 新建标签无 XMLID，按批次标记前缀回收）、`deleted_responsibility_ids=[59,60]`；
  二次回读 `clean=true` 且 `existing_batch=false`、`tags=[]`。未操作用户草稿或既有数据。

## 状态分层

- 批次验收完成：是（本专题范围内，本地候选 + 定向测试 + 受管浏览器闭环）。
- 主线集成完成：否（未推送、未创建 PR、未远端 CI）。
- 版本发布完成：否。
- 产品交付完成：否。
- 保持未验证：非空 JSON 展示、BOQ 前端权限场景、显式创建能力（除本专题标签创建外）；
  附件 404 仍为"未复现"。
