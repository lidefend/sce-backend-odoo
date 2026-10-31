# 85 · Phase 4H-02B Autonomous Progress

## Verdict

READY_WITH_CONSTRAINTS（自主执行部分推进，四项规则仍 NOT_VERIFIED）

## 本轮完成

### PC-010：Git 历史证据已采集

- 从 Git 历史物化 before/after 快照（`303ebd630^` 与 `303ebd630` 的
  `project_views.xml`），经 Collector 标 VERIFIED。
- 提交记录证明项目身份投影演化：
  - `8bd832066`：`user_id` 标签“项目负责人”→“你的项目角色”，`manager_id`
    “项目负责人”→“项目经理”。
  - `303ebd630`：去重 `manager_id` / `project_code` / `user_id` 的多处投影，
    并恢复 `last_update_status` 只读渲染。
- Guard：PC-010 仍 NOT_VERIFIED（trusted=2，sufficient=0）。缺口收窄为
  “源码级身份演化已证明，运行视图 1776/944 的 occurrence_index 与
  before/after 映射仍缺失”。

### PC-007：DOM 观察脚本已建立，取得一条运行时边界事实

- 新增 `scripts/verify/project_detail_composition_dom_observation.mjs`。
- 运行结果：登录成功（`fixture_role_config_admin`）；但
  `/a/590`、`/a/652` 返回
  `access-denied?reason=NAVIGATION_AUTHORITY_DENIED`，`ContractFormPage`
  未渲染。
- 事实：config_admin 不能经通用 `/a/:actionId` 路由直达这两个入口，必须走
  真实菜单入口 + 具体项目记录。
- PC-007 仍 NOT_VERIFIED：尚未取得最终 DOM 的 legacy/native 节点数证据。

### PC-008 / PC-009：未执行，保持 NOT_VERIFIED

- PC-008：多角色 fixture 身份已确认存在，但未运行双身份权限对比。
- PC-009：无既有 `old_consumer_regression` 测试，需新增并运行。

## 证据统计

| 规则 | evidence VERIFIED | Rule 状态 |
| --- | --- | --- |
| PC-007 | 2 SOURCE_STATIC | NOT_VERIFIED |
| PC-008 | 0 | NOT_VERIFIED |
| PC-009 | 1 SOURCE_STATIC | NOT_VERIFIED |
| PC-010 | 2 HISTORICAL_REFERENCE | NOT_VERIFIED |

Evidence VERIFIED 与 Rule PASS 未混淆。

## 下一步（待调度）

1. PC-007：沿真实菜单入口（项目中心 → 项目 → 打开表单）用具体 record_id
   观察 DOM，读取结构来源属性与 legacy/native 节点数。
2. PC-008：用 pm 与 partner_manager / system_admin 执行只读权限对比。
3. PC-009：新增旧消费者只读回归测试并运行。
4. PC-010：从运行视图 1776/944 提取 occurrence_index 并建立 before/after 映射。

## 边界

只读；未改业务代码、认证配置、ACL、用户角色、数据库、assembler、Guard 规则；
未删 Legacy fallback、未迁移页面、未重建 Candidate。工作树未提交改动保留。
