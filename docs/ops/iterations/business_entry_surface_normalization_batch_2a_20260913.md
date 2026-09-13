# Batch-2A 人员资料与授权维护边界收敛

[English](business_entry_surface_normalization_batch_2a_20260913.en.md)

## 1. 产品边界

- Formal Product Layer：P1 建筑行业标准产品。
- Layer Target：`smart_construction_core` 中 `res.users` 的 action-scoped
  人员档案、数据权限列表/表单/搜索配置，以及既有项目成员授权的受管写入适配。
- Standard vs User-Specific：两类办理职责属于行业产品的标准入口表达，不是客户特例。
- Why Here：人员档案与数据权限都是既有正式入口，本批只重组各入口的编辑职责。
- Why Not Elsewhere：不改 P0 renderer，不改 ACL、record rule、组成员、运行时低代码配置，
  不用 P4 脚本承载长期产品语义。
- Blast Radius：仅 `action_sc_runtime_user_management/menu_sc_runtime_user_management`
  与 `action_sc_product_data_permission_v1/menu_sc_product_data_permission_v1`，及两入口共用的
  `sc.project.member.assignment` 写入路径。
  89 个正式入口只是静态盘点范围，不代表 89 个页面需要修改；名称差异也不自动构成缺陷。

## 2. 角色承接结论

| 事实 | 核查结果 | 本批处理 |
|---|---|---|
| 人员档案入口 | 业务配置管理员、平台管理员可进入 | 权限保持不变 |
| 数据权限入口 | 行业配置管理员可进入 | 权限保持不变 |
| 角色继承 | 行业配置管理员继承业务配置管理员；反向不成立 | 不能把授权编辑能力只迁到数据权限 |
| 人员范围 | 两入口均操作 `res.users`，共享 `sc_runtime_company_maintainable` 公司范围 | 不宣称覆盖无账号员工 |
| 角色事实 | `sc_user_role_group_ids` 与 `sc_user_permission_group_ids` 都映射同一可分配 `res.groups` | 单一事实源，不复制授权数据 |
| 项目事实 | 两入口都使用 `sc.project.member.assignment` | 单一事实源，不复制项目授权 |
| 账号创建 | 受管创建要求明确初始密码；主公司与允许公司保持一致，并初始化内部用户组 | 机制与权限不变 |

承接风险真实存在：部分业务配置管理员能在原人员维护入口维护授权，却没有数据权限入口。
在没有“收回原能力”或“扩大数据权限入口”产品决策前，本批不迁移这些权限。人员档案保留
“授权维护（兼容入口）”，数据权限继续作为行业配置管理员的专门授权入口。

运行时菜单投影定向用例进一步确认：仅持有业务配置管理员组的事务用户可见“人员档案”、
不可见“数据权限”；仅显式赋予行业配置管理员组的事务用户因既有继承关系可见两者。因此
“数据权限”当前不能无损承接全部原授权维护者，本批不自行修改权限。

## 3. 实施结果

- 人员维护正式标题统一为“人员档案”，列表优先姓名、联系方式、部门、岗位和在职状态。
- 人员档案表单把人员资料作为主体，并把头像/档案、登录/账号、授权兼容维护分组。
- 登录账号、账号启停、密码、主公司和允许公司没有因职责拆分消失；`company_id` 保持
  “主公司”，`company_ids` 保持“允许公司”，没有将主公司降级为普通标签。
- 数据权限保留只读人员身份，并集中编辑主/允许公司、业务权限角色和项目成员授权。
- 两个 action 都继续绑定各自专用 tree/form/search view；共享 `res.users` 公共视图未改。
- 原受管 `res.users.write` 会过滤页面提交的项目成员 one2many 命令，形成“可编辑但不保存”。
  本批将该命令从提权的用户字段写入中剥离，以当前管理员身份调用既有
  `sc.project.member.assignment` ACL 与公司记录规则；新增行必须指定当前操作者可读的有效项目。
- 已建立授权的 `project_id` 固定：缺省或与原项目一致时可更新备注、停用和重新启用；更换或清空
  项目均在服务端拒绝。更换项目只能通过“停用旧授权、再新增目标项目授权”办理，两个页面同时把
  已有行的项目控件设为只读。
- 授权命令在普通人员字段写入前完整预校验，非法授权与同批人员资料修改整体回滚；新建人员若
  携带内联授权则明确提示“先保存人员，再维护项目成员授权”，不再静默丢弃。
- 未改 P0、ACL、record rule、组继承、菜单授权以及账号创建、启停和密码机制。

## 4. 分层验证

- L1 静态：业务入口 ownership guard 7 项、administration wave1 guard 1 项、
  configuration wave1 guard 1 项全部通过；XML、Python 编译与 diff check 通过。
- L2 非零定向：`data_permission_surface` 5 个方法 / 7 条 Odoo 统计通过，其中新增运行时菜单可见性反例；
  `runtime_user_management` 23 个方法 / 25 条 Odoo 统计通过。测试覆盖入口角色继承非对称、
  同模型/同范围、专用视图、只读身份、兼容授权控件，以及资料安全 payload 不携带
  账号、公司、角色或项目授权字段；另覆盖新增缺项目拒绝、A→B/清空项目拒绝且 follower 事实不变、
  同项目备注与停启、人员资料与非法授权整体回滚、新人员内联授权拒绝、跨公司项目记录规则拒绝、
  跨人员拒绝和物理删除拒绝。
- L3 受管运行态：产品修复提交 `a890edd2f8556ce5f6e424db6039cab234aebf14`
  对应的 `smart_construction_core 17.0.0.165` 增量升级与 authority verification 通过。
  一次旧 P4 guard 在当前模块集引用不存在的 `sc.legacy.user.profile`，未作为本产品失败，
  也未扩大为历史工具修复。
- L4 只读浏览器：候选
  `ab8827aa50d8339d5d5c777123771b14e178de0a`，`sc-local-dev/sc_dev_demo`，
  桌面 1440 与移动 390。系统管理员 `system.init` 下发人员档案
  `menu 430/action 736`、数据权限 `menu 709/action 886`；两列表均从真实记录
  `res.users/39` 打开对应表单，契约 HTTP 200、真实字段显示、无页面/控制台错误。
  `demo_readonly` 未收到两项 route authority，访问均以
  `NAVIGATION_AUTHORITY_DENIED` 拒绝。所有摘要 `mutationCount=0`。

首条列表记录 `res.users/3` 是 `Default User Template`，不属于人员办理对象；通用 runner
默认选择它时表单未进入 ready。改为同列表可见的真实人员 39 后通过，因此没有将模板记录
误判为产品入口缺陷，也没有修改等待时间或产品代码。

## 5. 证据与未决项

- 两入口列表到表单：
  `artifacts/playwright/batch2a-personnel-auth-readonly-record39/summary.json`。
- 两入口表单分组截图：
  `artifacts/playwright/batch2a-personnel-auth-forms/summary.json` 及同目录截图。
- 无权角色反例：
  `artifacts/playwright/batch2a-personnel-auth-denied/summary.json`。
- 浏览器产物为工作树本地、不进入 Git 的运行证据；最终文档 HEAD 的 Quick 另行绑定。
- 浏览器证据绑定较早的只读 UI 候选；后续 `a890edd2…` 修改 P1 授权写入适配、已有行项目只读表达和定向测试，
  未改已复核的页面结构，因此未重复菜单、主题或视口矩阵。
- 本次 S1 修复所要求的“新增授权 → 保存回读 → 停用 → 重新启用 → 刷新”写入旅程尚未执行。
  仓库当前只有项目资料专用写入 fixture/runner；通用候选浏览器入口明确为只读，且现有人员 39
  不是可写验收对象。基线规则禁止业务批次临时拼装人员 fixture、数据库写入或浏览器入口，因此
  在获得独立 P4 受管人员验收对象生命周期与写入 runner 前，不以真实账号或临时脚本绕过。
- 待产品决策：是否收回业务配置管理员在人员档案中的授权维护能力，或扩大数据权限入口。
  在决策前，兼容授权页签是能力无损边界，不是最终字段互斥承诺。
- 无账号人员不在本批 `res.users` 范围内，另行登记员工档案覆盖缺口。

## 6. 回滚

回退本批 P1 视图、契约表达、受管项目授权写入适配、定向测试和文档提交即可。没有 schema、权限或业务数据迁移，
不需要数据库数据回滚；已增量升级的 XML 可由回退版本再次受管升级恢复。
