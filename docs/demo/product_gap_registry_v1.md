# Demo 产品缺口回收登记 v1（2026-10-20）

> 归属原则：demo 层（P4）只消费契约与公开动作，不吸收产品语义。以下缺口在
> P0/P1/P3 各自立项；本线只登记与验证 demo 侧的消费方式。

## 缺口清单

| # | 缺口 | 证据 | 归属 | 状态 | demo 侧处理 |
|---|---|---|---|---|---|
| 1 | 审批动作岗位提示静态 | `payment_request_available_actions.py` 固定 executive | P1 | 待立项 | 不写死，按 `tier.review` 动态投影 |
| 2 | 项目就绪前置不可见 | 付款提交才报资金/结算/账户缺口 | P1/P3 | 待立项 | demo 回读用 manifest 判定，不做前端提示 |
| 3 | 组织负责人不是审批路由 | `manager_id` 仅展示/分组 | P1 | 待立项 | 不在 demo 用组织负责人冒充审批人 |
| 4 | 基线就绪无产品契约 | 无 `baseline.readiness` 投影 | P1/P3 | 待立项 | 已落 P4 只读 manifest/verifier，产品投影另立 |
| 5 | 体验重置语义未分离 | `demo.tenant.reset` 全库重建 | P4 | 已解决 | timer 保持 showcase 全量重建；scoped reset 规划器落地 |
| 6 | demo 作用域不一致 | 27 行公司作用域排除 | P4/P0 | 待立项 | 以 demo duty 精确 db/dbfilter 约束 |
| 7 | 派生数据直接 seed 风险 | R1-02 分类 B/C | P4 | 约束中 | 只造事实，工作台/驾驶舱/指标由事实派生 |
| 8 | seed step 名称不等于数据 | `dictionary`/`project_skeleton` 仅标记 | P4 | 已按回读 | 以真实回读为准（Batch 2/3 运行时回读） |
| 9 | 体验用户角色缺失 | 无 `group_sc_role_experience_user` | P1/P3/P0 | 待立项 | demo 暂用 `experience_users.json` 声明集合，角色落地后消费 `role_surface.role_code` |

### 用户使用基础数据 V1 追加排查（2026-10-20）

| # | 缺口 | 证据 | 归属 | 状态 | demo 侧处理 |
|---|---|---|---|---|---|
| 10 | 就绪检查主要证明记录存在 | 运行时探针以 `search_count > 0` 为主 | P4 | 待立项 | F1/F3/F5 增加字段完整性、公开候选集、角色可见与动作可用断言 |
| 11 | 每日系统事实没有执行器 | `scenario_tick.py` 将 `system_fact` 记为 `unbound` | P4 | 待立项 | F7 绑定公开 intent/action；未绑定则保持未推进 |
| 12 | 角色启动验收覆盖不足 | smoke 只跑 `demo_pm`/`demo_finance`/`demo_audit`，且只断言契约键存在 | P4 | 待立项 | F2/F8 增加业务全功能账号、首屏非空和实际下一步 |
| 13 | 演示数据时间与金额失真 | 多处固定 2025 日期，场景存在 50/100 样例金额 | P4 | 待立项 | F3/F8 以业务日历和金额规则回读，不按文本字符串验收 |
| 14 | 10 日叙事未完整声明 | `business_days=10`，manifest 仅有 D1–D3 步骤 | P4 | 待立项 | F7 补齐可执行 10 日步骤与幂等键 |
| 15 | 模块升级视图校验失败 | `_update_user_groups_view` 报 `action_sc_review_group_authority 对 res.users 无效`，阻断 demo 数据载体（16_bank_accounts.xml）受管加载 | P1/P2/P3 | 待立项 | F3 银行账户数据加载被阻断；先修 owning layer 的 res.users 视图/动作绑定，再 `local.dev.upgrade` 加载并回读 |

## 回收判据

- P1/P3 立项后，demo 层改用对应契约消费，删除任何前端/demo 层特判；
- 每个缺口在 owning layer 有独立批次与验证，不在本线打补丁；
- 体验重置在 #9 落地后，以角色为清理键替换 `experience_users.json` 登录集合。
