# WS-01 项目建立与维护 — 工作场景设计（S2-02 首个样板，事实修订版）

状态：设计冻结候选，待 S2-03 架构一致性审查后实施
上游决策：ARCH-DECISION-010、ARCH-DECISION-011（S2-01..07）
规范与校验：`docs/architecture/work_scenario_spec_v1.md`、`docs/architecture/work_scenario_schema_v1.json`

## 0. 能力身份来源说明

能力目录 `docs/product/capability_catalog_v1.json` 已过期（42 条、`main_action.intent` 统一为通用
兜底 `ui.contract`、`status` 全部 ready、`maturity_fingerprint` 全部缺失），不作为本设计的能力身份依据。
本设计以代码中的真实事实为准：具体 intent handler、原生 `ir.actions.act_window`、模型与 Scene Registry。
能力目录的修订是独立任务，见 `work_scenario_conflict_report.md`。

## 1. 定义总表

| 属性 | 本场景取值 | 权威来源 |
|---|---|---|
| scenario_key | `ws.project.establish_maintain` | 设计冻结 |
| scenario_version | `v1` | 设计冻结 |
| domain_ref | `smart_construction_core.menu_sc_project_center` | 原生顶级菜单 |
| entry_refs | 见第 2 节入口解析表 | 原生菜单/action |
| actor_refs | 见第 3 节角色表 | IdentityResolver 规范角色编码 + res.groups |
| goal | 用户能创建项目、维护项目资料、随时查看项目实际信息 | 设计 |
| steps | 六阶段，见第 4 节 | 设计 |
| page_scene_refs | `projects.intake`、`projects.list`、`projects.detail` | 现有 Scene Registry |
| capability_refs | 见第 5 节能力引用 | 真实 intent/action/model |
| transition_rules | 见第 6 节 | 设计 |
| completion | 项目保存成功并可在项目台账重新检索到 | 设计 |
| failure_handling | 见第 7 节 | 设计 |
| lifecycle | 见第 8 节（区分三层版本） | ARCH-DECISION-011 |

## 2. 入口解析（DECISION-S2-05，解决共享菜单矛盾）

共享菜单 `menu_sc_project_project` 拆成两个独立解析过程，不做先到先得：

| 操作 | 入口身份 | 解析结果 |
|---|---|---|
| 进入项目管理 | Domain（`menu_sc_project_center`） | 项目管理入口 |
| 打开项目列表 | Menu + Action（`menu_sc_project_project` + `action_sc_project_list`） | `projects.list` |
| 打开某个项目 | Record Target（`model=project.project` + `record_id`） | `projects.detail` |
| 返回项目列表 | 原列表上下文（`list_context`） | `projects.list` |

- `projects.list`、`projects.ledger` 是入口场景。
- `projects.detail` 是记录上下文场景，必须携带真实 `project.project + record_id`，不通过菜单直接命中。
- 阶段 4 的入口是 Record Target，不是 `menu_sc_project_project`。

## 3. 角色表（actor_refs，DECISION-S2-07）

| role_code | 规范角色 | res.groups XMLID |
|---|---|---|
| `pm` | 项目经理 | `smart_construction_core.group_sc_cap_project_manager` |
| `project_member` | 项目成员 | `smart_construction_core.group_sc_cap_project_user` |
| `business_config_admin` | 业务配置管理员 | `smart_construction_core.group_sc_cap_business_config_admin` |

注意：能力目录的 `required_roles` 使用 `project_manager/construction_manager/owner_manager` 等第三套编码，
需收敛到上表 IdentityResolver 规范编码 + res.groups XMLID（见冲突报告）。

## 4. 六阶段用户旅程

| # | 阶段 key | 入口 | 能力引用 | 页面引用 | 成功结果 | 下一步 |
|---|---|---|---|---|---|---|
| 1 | enter | `domain: menu_sc_project_center` | `action_sc_project_list` | `projects.list` | 展示项目台账与可执行入口 | 2 或 6 |
| 2 | create | `menu+action: menu_sc_project_initiation + action_project_initiation` | `project.initiation.enter`（intent） | `projects.intake` | 表单按原生契约呈现 | 3 |
| 3 | validate_save | 同 create 入口 | `project.project`（校验/onchange/保存） | `projects.intake` | 服务端返回保存成功的项目记录 | 4 |
| 4 | view | `record_target: project.project + record_id` | `project.project`（读取） | `projects.detail` | 展示项目实际信息 | 5 |
| 5 | maintain | 同 view 入口 | `project.project`（更新） | `projects.detail` | 变更落库并回读一致 | 4 或 6 |
| 6 | return | `list_context` | `action_sc_project_list` | `projects.list` | 可再次检索到该项目并打开 | 任意阶段 |

## 5. 能力引用（真实事实，身份与执行载体分离）

| capability_key | provider_type | provider_ref | 真实执行载体 | qualification |
|---|---|---|---|---|
| `project.initiation.enter` | odoo_intent | `project.initiation.enter` | handler `project_initiation_enter.py` + `action_project_initiation` + `project.project` | 以产品发布 release_state 为准 |
| `action_sc_project_list` | odoo_action | `smart_construction_core.action_sc_project_list` | 原生 act_window + `project.project` | 同上 |
| `project.project` | odoo_model | `project.project` | 模型读取/写入能力（detail 表单 + onchange/校验） | 同上 |

- `projects.detail` 是页面场景（`page_scene_refs`），不是原子能力。
- `capability_key` 必须等能力目录修订后，再与目录 `capability_key` 对齐；当前以真实 intent/action/model 为身份。
- `evidence_binding` 复用 `capability_maturity.maturity_fingerprint`；能力目录目前无指纹，需在目录修订时补齐。

## 6. 步骤间转换

```text
from=enter to=create trigger=进入项目立项入口
from=create to=validate_save trigger=点击保存
from=validate_save to=view trigger=服务端保存成功（携带真实 record_id）
from=view to=maintain trigger=进入编辑
from=maintain to=view trigger=保存并回读确认
from=any to=return trigger=返回项目台账
```

## 7. 失败处理

| 失败类型 | 处理 | 权威 |
|---|---|---|
| 校验错误 | 服务端返回字段错误，原样呈现，修正后重试 | 后端契约 |
| 权限拒绝 | 显式拒绝态，不隐藏入口、不夹带默认值 | 原生 ACL/record rules |
| 网络中断 | 保留已输入上下文，重试时重新读取服务端结果，不本地猜结果 | 前端只消费契约 |
| 记录缺失 | 显式错误态，提示返回项目台账 | 后端返回 |

## 8. 生命周期（三层版本分离）

| 版本类型 | 身份 | 变化触发 |
|---|---|---|
| 场景定义版本 | `scenario_version`（v1） | 步骤/入口/能力组合变化 |
| 能力版本 | capability_key 的发布版本 + 资格状态 | 能力实现或资格变化 |
| 产品快照版本 | 产品发布快照版本 | 场景/能力/角色组合发布 |

## 9. 验收口径（S2-05 真实验证）

在 daily 真实验收环境以真实角色走通：
创建 → 校验失败恢复 → 保存成功（带真实 record_id）→ 详情查看 → 维护并回读 → 返回台账重新打开，
并证明所有阶段只消费已有 intent/action/model，未新增 Registry、未新增权限判定、未虚构能力回执。
