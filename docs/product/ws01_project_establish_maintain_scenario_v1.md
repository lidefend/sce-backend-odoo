# WS-01 项目建立与维护 — 工作场景设计（S2-02 首个样板）

状态：设计冻结候选，待 S2-03 架构一致性审查后实施
上游决策：`ARCH-DECISION-011`（能力发布与产品发布分离）
规范与校验：`docs/architecture/work_scenario_spec_v1.md`、`docs/architecture/work_scenario_schema_v1.json`
盘点基线：`docs/architecture` + `S2-01` 只读盘点

## 0. 统一工作场景规范（本文件即首个实例）

| 属性 | 本场景取值 | 权威来源 |
|---|---|---|
| scenario_key | `ws.project.establish_maintain` | 本次设计冻结 |
| scenario_version | `v1` | 本次设计冻结 |
| domain_ref | `smart_construction_core.menu_sc_project_center` | 原生顶级菜单 |
| entry_refs | `smart_construction_core.menu_sc_project_initiation`、`smart_construction_core.menu_sc_project_project` | 原生菜单 |
| actor_refs | `pm`、`project_member`、`business_config_admin`、`owner`（IdentityResolver 规范角色编码 + 对应 `res.groups` XMLID） | 原生 res.groups / 角色目录 |
| goal | 用户能创建项目、维护项目资料、随时查看项目实际信息 | 设计 |
| steps | 见第 1 节六阶段 | 设计 |
| page_scene_refs | `projects.intake`、`projects.list`、`projects.detail` | 已有 Scene Registry |
| capability_refs | 见第 2 节能力引用 | 已发布能力 |
| transition_rules | 见第 3 节 | 设计 |
| completion | 项目保存成功并可在项目台账重新检索到 | 设计 |
| failure_handling | 见第 4 节 | 设计 |
| lifecycle | `draft → published → deprecated → retired` | 复用产品生命周期 |

## 1. 六阶段用户旅程

每个阶段只引用已有能力，不新建执行引擎。阶段是同一工作场景的不同操作阶段，
底层分别引用已发布的创建、读取、更新能力。

| # | 阶段 | 入口 | 用户身份 | 前置条件 | 操作 | 能力引用 | 页面引用 | 成功结果 | 失败处理 | 下一步 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 进入项目管理 | `menu_sc_project_center` | pm/project_member/business_config_admin | 已登录、company 上下文有效 | 打开项目管理域，查看已有项目与可用操作 | `action_sc_project_list` | `projects.list` | 展示项目台账与可执行入口 | 导航拒绝则进入 contract gap 错误态，不回退猜测 | 阶段 2 或阶段 6 |
| 2 | 创建项目 | `menu_sc_project_initiation` | pm/business_config_admin（有创建权） | 原生创建权限通过 | 调用现有项目创建入口，填写原生契约定义的基础信息 | `action_project_initiation` + `project.project` 创建能力 | `projects.intake` | 表单字段按原生契约呈现 | 校验错误原样回显，不夹带 | 阶段 3 |
| 3 | 校验与保存 | 同一创建入口 | 同阶段 2 | 阶段 2 已填 | 使用现有字段校验、关联选择、Onchange、保存和服务端业务规则 | `project.project` 校验/Onchange/保存 | `projects.intake` | 服务端返回保存成功的项目记录 | 权限拒绝/校验失败/网络中断分别按服务端结果恢复 | 阶段 4 |
| 4 | 查看项目 | `menu_sc_project_project`（record 上下文） | 有读权限的角色 | 项目已创建 | 进入项目详情，查看基本资料及关联信息 | `project.project` 读取能力 | `projects.detail` | 展示项目实际信息 | 记录缺失/无权限进入显式错误态 | 阶段 5 |
| 5 | 维护项目 | 同一详情入口 | 有编辑权限的角色 | 阶段 4 可读、编辑权限通过 | 修改可编辑资料，重新读取服务端结果确认变更 | `project.project` 更新能力 | `projects.detail` | 变更落库并回读一致 | 权限拒绝/校验失败恢复原始可编辑状态 | 阶段 4 或阶段 6 |
| 6 | 返回项目工作入口 | `menu_sc_project_project` | 同阶段 1 | 项目存在 | 再次查询、打开项目、继续办理其他业务 | `action_sc_project_list` | `projects.list` | 可再次检索到该项目并打开 | 检索无结果提示，不猜测 | 任意阶段 |

## 2. 能力引用（只引用已发布能力，不复制）

| capability_key | carrier | capability_version | evidence_binding |
|---|---|---|---|
| `project.project` | model:project.project | P1 标准版 | 能力发布指纹（capability_maturity） |
| `project.create` | action:smart_construction_core.action_project_initiation | P1 标准版 | 能力发布回执 |
| `project.list_read` | action:smart_construction_core.action_sc_project_list | P1 标准版 | 能力发布回执 |
| `project.detail_page` | scene:projects.detail | P1 标准版 | 页面场景契约指纹 |

## 3. 步骤间转换声明

```text
from=enter to=create trigger=进入项目立项入口
from=create to=validate_save trigger=点击保存
from=validate_save to=view trigger=服务端保存成功
from=view to=maintain trigger=进入编辑
from=maintain to=view trigger=保存并回读确认
from=any to=return trigger=返回项目台账
```

- 阶段 1→2 以“进入项目立项入口”触发，不自动创建。
- 阶段 2→3 以“保存”动作触发，失败停留在阶段 2。
- 阶段 3→4 只在服务端确认保存成功后触发。
- 阶段 5 的“修改并确认”复用阶段 3 的校验/保存能力，不新建。

## 3.1 入口解析 vs 记录上下文解析（DECISION-S2-05）

共享菜单 `menu_sc_project_project` 必须拆成两个独立解析过程，不能先到先得：

```text
入口解析：点击菜单 -> 原生 menu_id + action_id -> 显式 Entry Binding -> 唯一入口场景
  menu_sc_project_project -> projects.list（列表入口）

记录上下文解析：选择项目记录 -> 真实 model=project.project + record_id -> 显式记录目标规则 -> projects.detail
  projects.detail 只通过 route + record_id + 记录目标规则进入，不通过菜单直接命中
```

- `projects.list`、`projects.ledger` 是入口场景。
- `projects.detail` 是记录上下文场景，必须携带真实 `project.project + record_id`。
- 禁止仅凭 `menu_sc_project_project` 推断进入哪个场景，禁止仅凭 `project.project` 模型推断页面意图。

## 4. 失败处理

| 失败类型 | 处理 | 权威 |
|---|---|---|
| 校验错误 | 服务端返回字段错误，原样呈现，用户修正后重试 | 后端契约 |
| 权限拒绝 | 显式拒绝态，不隐藏入口、不夹带默认值 | 原生 ACL/record rules |
| 网络中断 | 保留已输入上下文，重试时重新读取服务端结果，不本地猜结果 | 前端只消费契约 |
| 记录缺失 | 显式错误态，提示返回项目台账 | 后端返回 |

## 5. 生命周期

复用 `ARCH-DECISION-011` 的产品生命周期：
`draft → published → deprecated → retired`。
本场景的启用/停用/升级只改变“产品发布”层，不改变底层能力发布；能力停用必须
在引用它的所有产品场景完成退役后才允许。

## 6. 验收口径（S2-05 真实验证，不以静态测试替代）

在 daily 真实验收环境以真实角色走通：
创建 → 校验失败恢复 → 保存成功 → 详情查看 → 维护并回读 → 返回台账重新打开，
并证明所有阶段只消费已有 action/intent/model，未新增 Registry、未新增权限判定。
