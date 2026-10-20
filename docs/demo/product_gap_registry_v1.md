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

## 回收判据

- P1/P3 立项后，demo 层改用对应契约消费，删除任何前端/demo 层特判；
- 每个缺口在 owning layer 有独立批次与验证，不在本线打补丁；
- 体验重置在 #9 落地后，以角色为清理键替换 `experience_users.json` 登录集合。
