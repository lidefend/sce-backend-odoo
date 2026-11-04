# 工作场景统一规范 v1

状态：S2-02 设计产物，待 S2-03 审查
上游决策：ARCH-DECISION-010（事实层唯一权威）、ARCH-DECISION-011（能力发布与产品发布分离）

## 1. 定位

工作场景是“能力资产的组合组织方式”，不是新的业务执行引擎，也不是新的权限系统。
它把一个用户工作目标（goal）拆成可执行步骤（steps），每步只引用已发布能力
（capability_refs）和已存在页面场景（page_scene_refs），并声明适用角色（actor_refs）。

## 2. 定义结构

| 属性 | 类型 | 必填 | 说明 |
|---|---|---|---|
| scenario_key | string | 是 | 稳定身份，如 `ws.project.establish_maintain` |
| scenario_version | string | 是 | 场景定义版本，如 `v1` |
| domain_ref | string | 是 | 所属主要业务域，指向原生顶级菜单 xmlid |
| entry_refs | string[] | 是 | 正式入口引用，指向原生菜单/action xmlid |
| actor_refs | string[] | 是 | 适用角色，指向原生 res.groups / 角色目录 code |
| goal | string | 是 | 用户工作目标，一句可验证描述 |
| steps | step[] | 是 | 工作步骤，见 step 结构 |
| page_scene_refs | string[] | 是 | 页面场景，指向现有 Scene Registry 的 scene_key |
| capability_refs | capability_ref[] | 是 | 原子能力，指向已发布能力 |
| transition_rules | transition[] | 是 | 步骤间转换声明 |
| completion | string | 是 | 完成条件，可验证 |
| failure_handling | failure_rule[] | 是 | 失败恢复声明 |
| lifecycle | string[] | 是 | 产品生命周期状态序列 |

### step 结构

| 属性 | 必填 | 说明 |
|---|---|---|
| key | 是 | 阶段稳定标识 |
| label | 是 | 阶段名称 |
| entry_ref | 否 | 该阶段入口（原生菜单/action） |
| actor_refs | 是 | 可进入该阶段的角色 |
| preconditions | 是 | 前置条件 |
| operations | 是 | 用户实际可执行操作 |
| capability_refs | 是 | 对应已有模型/action/intent |
| page_scene_ref | 否 | 对应已有 Scene Contract |
| success_outcome | 是 | 成功结果 |
| failure_handling | 是 | 失败恢复 |
| next_steps | 是 | 成功后可选下一步 |
| acceptance | 是 | 如何证明该阶段真实运行 |

### capability_ref 结构

| 属性 | 必填 | 说明 |
|---|---|---|
| capability_key | 是 | 已发布能力稳定标识 |
| carrier | 是 | 原生 model / action_xmlid / intent |
| capability_version | 是 | 引用能力版本，禁止未发布/已退役 |
| evidence_binding | 是 | 能力发布指纹 / 验证回执引用（DECISION-S2-04） |

## 3. 三条硬约束

1. `capability_refs` 只能引用已发布、未退役能力；不得复制业务逻辑。
2. `page_scene_refs` 只能引用现有 Scene Registry 页面场景；不得另造页面。
3. `actor_refs` 只能引用已有角色与授权事实；不得在场景中定义权限。

## 4. 十条禁止事项

1. 不得新增第二套 Menu Registry。
2. 不得新增第二套 Page Scene Registry。
3. 不得复制 Capability Registry。
4. 不得创建独立于 Odoo 的权限判定。
5. 不得在前端硬编码业务域、角色和场景归属。
6. 不得通过中文名称、菜单关键词推断业务关系。
7. 不得复制现有模型、Action、Intent 和字段定义。
8. 不得为了场景化重写现有前端运行时。
9. 不得修改已确认业务事实来迎合场景设计。
10. 不得用静态测试代替真实用户旅程验收。

## 5. 生命周期

复用产品生命周期：`draft → published → deprecated → retired`。
场景停用/升级只改变产品层；底层能力停用必须在所有引用场景退役后进行。
