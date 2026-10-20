# Demo 迭代线总体计划 v1

> 状态：Batch 0 计划冻结，后续按批次实施。
> 分支/基线：`feature/demo-iteration-line-20261020` @ `13b0395db4da63147b3f9c311a4bb5d060dc6a4e`
> 关联：[基线就绪排查](demo_baseline_readiness_v1.md)、[系统演示脚本](system_demo_v1.md)、
> [场景目录](scenarios.md)、[真实核心链](r1-02-realistic-core-chain.md)、
> [组织主数据](r1-04-organization-master-data.md)、
> [Demo Showcase 治理](../audit/demo_showcase_governance.md)、
> [Demo 隔离租户运行手册](../ops/demo_isolated_tenant_stack_runbook_v1.md)。

## 1. 目标

把 demo 从“静态记录集合”升级为：

1. **基线就绪**：公司、组织、主数据、审批、项目和资金前置可用；
2. **角色接力**：每个角色登录后看到自己今天该办的事；
3. **真实办理**：合同、结算、付款、付款登记、台账由正式动作推进；
4. **持续运行**：服务器按业务日历推进事实，用户每天看到系统在真实变化；
5. **可验证**：API、数据回读、浏览器角色验收和审计证据一致；
6. **可清理**：体验用户产生的数据可定时清理，demo 基线不被误删。

## 2. 先纠正一个关键边界

**体验重置不是 demo 重置。**

- `experience reset`：清理体验用户操作产生的记录、编辑、附件、审批、消息、会话；
- `demo scenario tick`：推进 demo 自身的业务日历，产生新的事实和新的角色任务；
- `demo baseline reset`：仅在需要回到基线版本或维护时执行，不能每天覆盖 demo。

当前仓库的 `deploy/demo-tenant/scems-demo-tenant.timer` 在 04:00/16:00 调用
`make demo.tenant.reset`；`scripts/demo/tenant_lifecycle.sh reset` 会停止 nginx/odoo、
清理 filestore、执行 `demo.reset` 并重放 release seed。这是**全库基线重建**语义。

因此 Batch 5 必须先核对：

1. 该 timer 指向的是“体验租户”还是“demo 主租户”；
2. 体验用户是否与 demo 基线在同一数据库/公司；
3. 是否存在会话级/体验公司级的增量隔离；
4. 重置前后 demo 基线指纹是否保持不变。

在身份未确认前，不修改 timer，也不把 `demo.tenant.reset` 当作体验清理入口。

### 体验隔离方案

| 方案 | 做法 | 优点 | 代价 |
|---|---|---|---|
| A. 会话级副本（推荐） | 用户首次办理时把 demo 案例复制为体验会话副本；所有操作落在副本 | 基线绝不被改，清理简单 | 需要 P4/P1 提供案例复制与来源绑定 |
| B. 体验公司/项目 | demo 基线公司只读；体验用户在自己的公司/项目内操作 | 复用现有公司作用域 | 需要数据权限和菜单隔离 |
| C. 独立体验租户 | 独立数据库/租户，按基线快照恢复 | 隔离最彻底 | 新增环境和凭据权威，需单独授权 |
| D. 全库重建 | 直接重置整个 demo 库 | 实现简单 | 会破坏 demo 连续性，不能作为每日体验清理 |

计划默认采用 A；若现有环境已是 C，则保留 C 并补基线指纹校验。B 作为兼容路径。
D 只允许用于隔离的体验租户或显式维护窗口。

## 3. 设计原则

1. **基线先行**：G0–G4 未就绪，不进入合同/结算/付款交易数据。
2. **一个主案例**：一个项目、一个合同、一个结算、一个付款链，多个角色接力。
3. **状态快照**：同一主链保留“待提交、待审批、已批准、已付款、已完成”等真实切片。
4. **事实自动推进，决策留给人**：进度、材料到货、发票、风险、日报可由系统产生；
   审批、确认、驳回、付款确认必须由对应角色完成。
5. **不直接写状态**：只调用模型公开动作或 intent；不伪造审批历史。
6. **不 seed 投影**：工作台、驾驶舱、成本台账、经营指标由事实派生。
7. **产品缺口回产品层**：审批岗位投影、项目就绪提示、组织审批路由等属于 P0/P1/P3，
   不在 demo 层写死。
8. **可回滚**：每个批次有独立提交边界、验收命令和回滚路径。

## 4. 总体架构

```text
G0-G6 基线就绪
  → Demo Case Manifest（主案例/快照/角色任务/审批链）
    → 种子准备（只准备起点，不写终态）
      → API / UI 业务链验证（真实角色、真实动作）
        → Demo Scenario Tick（按业务日历推进事实）
          → 角色收件箱 + 每日简报
            → 体验用户操作
              → Experience Reset（只清理体验增量）
                → 下一日继续
```

## 5. 分批计划

| 批次 | 目标 | 范围 | 完成判据 | 回滚 |
|---|---|---|---|---|
| Batch 0 | 基线排查 + 总体计划 + run 登记 | `docs/demo`、`.agent`、批次记录 | 文档门禁、ledger 单测、L1 通过 | 回退本批文档与 run |
| Batch 1 | 基线就绪 manifest + verifier | P4 `scripts/verify`、`docs/demo` | 离线夹具覆盖 ready/partial/blocked；非零测试 | 删除 verifier 与 manifest |
| Batch 2 | 基础数据补齐 | `demo_addons/smart_construction_demo/data`、`seed/steps` | G0–G4 对目标公司/项目 `missing=[]` | 回退种子文件与 XMLID |
| Batch 3 | 黄金业务链 + 角色快照 | demo 场景数据、金额/日期、审批链 | 跨记录金额/日期/状态自洽；角色可见 | 回退场景 XML/seed |
| Batch 4 | API 场景驱动与验证 | P4 `scripts/verify`、intent 调用 | 真实角色四级审批、幂等、负例通过 | 删除 driver/断言 |
| Batch 5 | 日推进 + 体验重置分离 | `smart_construction_demo`、`deploy/demo-tenant` | 3 日压缩时钟、心跳、基线指纹不变、体验增量清零 | 停用新 timer，恢复旧配置 |
| Batch 6 | 角色 UI 验收 + 产品缺口收口 | 浏览器验收、P1/P3 修复分批 | 每角色有真实任务、每日变化可见、无技术泄漏 | 回退 UI/验收与对应产品提交 |

Batch 2 起每个批次都必须先通过前一批的验收；Batch 5 不得在 Batch 4 未通过时启动。

## 6. 日运行设计

### 6.1 三条时间线

- **真实时间**：Asia/Shanghai，业务日切分以公司时区为准；
- **业务日历**：施工 7 天/办公 5 天可配置；
- **Demo 叙事线**：Day 1..N，按 step 推进，不等同于自然日。

### 6.2 Step 契约

每个 step 至少声明：

```text
scenario_id, business_date, day_index, step_key, sequence,
actor_mode, actor_role, intent_or_action, params,
precondition, expected_state, idempotency_key, status, result, evidence
```

`actor_mode` 取值：

- `system_fact`：系统可自动产生的事实（日志、到货、发票、风险、提醒）；
- `role_draft`：系统为角色准备草稿，但不提交；
- `role_decision`：只生成待办，绝不自动审批/确认；
- `showcase_history`：仅用于独立的历史展示轨道，不进入体验主线。

### 6.3 定时任务

| 任务 | 建议时间 | 作用 | 约束 |
|---|---|---|---|
| `demo.scenario.tick` | 每日 07:30 | 推进一天的事实与角色待办 | 幂等；不自动审批；不重建基线 |
| `demo.daily.digest` | 每日 18:00 | 生成当日经营简报 | 只读事实；不写业务状态 |
| `experience.reset` | 04:00/16:00 或会话结束 | 清理体验用户增量 | 只删体验数据；基线指纹不变 |
| `demo.baseline.reset` | 按维护窗口 | 回到基线版本 | 需显式确认；不与体验重置混用 |

### 6.4 幂等与失败处理

- 唯一键：`scenario_id + business_date + step_key`；
- 业务调用：`request_id` / `idempotency_key` / `trace_id`；
- 失败分类：`product_defect`、`baseline_evidence_defect`、`environment_defect`、
  `validation_tool_defect`；
- 连续失败暂停 scenario，不自动降级为“跳过审批”；
- 审批逾期只升级提醒/活动，不自动通过；
- 心跳缺失 24 小时告警。

### 6.5 体验重置边界

重置必须覆盖：

- 体验用户新建的业务记录；
- 对基线记录的编辑（恢复原值）；
- 体验附件、消息、活动、通知、会话；
- 体验审批实例与审批日志；
- 体验用户上传的文件与临时导入批次。

重置必须证明：

- demo 基线记录数量/指纹不变；
- 基线审批历史不变；
- 体验增量清零；
- 无跨公司/跨租户残留。

## 7. 可演示的 10 日业务线

| Day | 系统自动产生的事实 | 留给用户的真实任务 | 预期状态 |
|---|---|---|---|
| D1 | 立项通过、WBS/BOQ 发布、合同草稿 | 合同经办：提交合同 | 合同待审批 |
| D2 | 材料计划、施工日志、进度草稿 | 项目负责人：审批合同 | 合同进入下一级 |
| D3 | 采购订单、材料到货、验收草稿 | 物资：确认验收 | 入库/成本事实 |
| D4 | 进度计量、成本归集 | 成本：确认进度 | 结算依据形成 |
| D5 | 结算草稿、发票登记 | 结算经办：提交结算 | 结算待审批 |
| D6 | 结算审批推进、资金基线检查 | 财务：提交付款申请 | 付款待审批 |
| D7 | 付款申请到达项目/财务/管理层 | 各角色：审批 | 付款已批准 |
| D8 | 付款登记草稿 | 财务：确认付款 | 已付款 |
| D9 | 台账、合同累计付款、成本更新 | 项目经理/财务：查看异常 | 经营指标更新 |
| D10 | 日报/周报、风险提醒 | 管理层：处理风险 | 进入下一周期 |

如果用户未处理审批，系统继续产生运营事实，但审批保持待办并升级提醒；不自动替用户完成。

## 8. 产品缺口与归属

| 缺口 | 证据 | 归属 | 处理 |
|---|---|---|---|
| 审批动作岗位提示静态 | `payment_request_available_actions.py` 固定 executive | P1 | 从当前 `tier.review` 动态投影 |
| 项目就绪前置不可见 | 付款提交才报资金/结算/账户缺口 | P1/P3 | 项目页“办理前检查” |
| 组织负责人不是审批路由 | `sc_demo_organization_bindings.xml` 注释 | P1 | 明确策略或实现组织审批 |
| 基线就绪无产品契约 | 当前无 `baseline.readiness` | P1/P3 | 后端投影 + 前端消费 |
| 体验重置语义未分离 | `demo.tenant.reset` 全库重建 | P4 | 新增 scoped experience reset |
| demo 作用域不一致 | 27 行公司作用域排除 | P4/P0 | 固定 demo 公司/角色/数据空间 |
| 派生数据直接 seed 风险 | R1-02 分类 B/C | P4 | 只造事实，派生投影 |
| seed step 名称不等于数据 | `dictionary`/`project_skeleton` 仅标记 | P4 | 以真实回读为准 |

## 9. 本线不做

- 不在 demo 层实现产品业务语义；
- 不直接写 `state`、不伪造审批历史、不使用 admin/superuser 办理业务；
- 不自动审批体验主线的待办；
- 不 seed 工作台、驾驶舱、成本台账、经营指标等派生投影；
- 不新建数据库、租户、Compose project、端口、卷或凭据；
- 不触碰生产/客户数据；
- 不用全库重建替代体验增量清理。

## 10. 完成判据

1. G0–G4 对目标公司/项目 `ready`，无隐藏前置；
2. 主链从合同到付款台账可追溯，金额/日期/状态自洽；
3. 四级审批按真实岗位推进，API 与 UI 结果一致；
4. 每个角色登录后至少有一个真实可办任务；
5. 日推进连续 3 天压缩演练通过，无重复记录、无自动审批；
6. 体验重置后 demo 基线指纹不变、体验增量清零；
7. 浏览器验收无技术词泄漏、无越权可见、无阻断错误；
8. 产品缺口已回到 P0/P1/P3 立项，不在 demo 层打补丁。

## 11. 下一步

Batch 1：实现只读 `baseline.readiness` manifest/verifier（P4），先在离线夹具上证明
G0–G6 的 ready/partial/blocked 判定，再接入 demo 种子与体验重置门禁。
