# G7 立项准备（高风险写入与场景发布）

> 状态：立项准备（呈报决策稿，未获批前不构成实施授权）
> 阶段定义：总控计划 §7——G7 = 高风险写入与场景发布；进入条件 = 权限、并发、审计已落地；退出条件 = 真实角色、历史配置、五视口与回退通过
> 编制日期：2026-09-06（G6.1/G6.2 图表专题收口后，main=e3b6671b）

## 1. 为什么现在做 G7 立项准备

G6 已收口两个批次（PR #436 / #437）：图表能力全链（契约→注册表→intent 降级链→
四态组件→懒加载体积预算）+ 4 个真实 chart + 2 个驾驶舱图表块。G6 阶段的定位是
「获批能力的只读/异步实现」，只读路径已实证。G7 要进入的是**写入密集能力**，
按 §7 进入条件与 §16 必签节点要求，立项前必须完成进入条件审计与切片呈报。

## 2. G7 进入条件审计（现状）

| 进入条件 | 现状 | 证据 | 结论 |
| --- | --- | --- | --- |
| 权限 | ACL + 组模型全链已实证；无权访问→结构化空态是设计降级语义（非缺陷） | G6.2 E2E 三视角（成控/财务/合同）在 payment.request / payment.ledger / sc.general.contract 上的 ACL 拒绝→空 series→空态渲染 | **已落地** |
| 并发 | 无统一幂等键/ETag/版本策略基建；存在可复用先例：BOQ 导入向导 digest 绑定模式（ADR-004 §决策 3 引用） | grep 全库无 idempotency 统一基建；boq import wizard 既有 digest 限额模式 | **未达标**（G7 首切片前须模式化） |
| 审计 | `sc.audit.log` / `sc.scene.audit.log` / `sc.capability.audit.log` 模型已存在且 core 多处挂接（fund_account_operation / quality_management / tax_deduction_registration 等）+ scene 治理服务挂接 | models/support/audit_log.py + 各 core 模型引用；但均为超管级 ACL（Round13 论证），业务写动作审计模式未统一 | **部分达标**（模型在，业务写动作挂接模式待定式） |
| 异步 job | `sc.ops.job` 框架已在 smart_core 落地（subscription / platform_ops_controller 消费） | ADR-004 §决策 3 直接引用既有 job 框架，不新建队列 | **已落地** |
| 验收基础 | 五视口（G3.3-B 已收口）、demo 隔离栈、角色旅程矩阵 guard、回退纪律（feature flag / kill switch 契约 §14） | wave3 backlog + demo runbook v1 | **已落地** |

## 3. 能力路线盘点（G5 状态盘点）

| ADR | 能力 | 状态 | 对 G7 的含义 |
| --- | --- | --- | --- |
| ADR-002 | ECharts 图表引擎 | **Accepted**（2026-09-05，预算口径已修订） | G6 已实现（只读）；drill actions 属只读派发，非高风险写入 |
| ADR-003 | Gantt renderer | Proposed（**本期否决**，P1 任务数据契约不存在） | 不进入 G7；重开条件已锁定 |
| ADR-004 | Excel 引擎与安全边界 | **Proposed（待批准）** | 批准后：G6 式只读/job 实现（导出裁剪/导入预览）；**replace/update 危险导入模式 = G7 首个真实高风险写入切片** |
| ADR-005 | PDF 引擎与隔离边界 | **Proposed（待批准）** | 批准后：G6 式 job/预览实现；水印/签章权威属后端，写入面小 |
| ADR-006 | Editor format 与净化 | **Proposed（待批准）** | 批准后：G6 式受限编辑实现；**sanitize-on-save 写入 = 高风险写入切片** |

## 4. 高风险写入候选切片（按落地距离排序）

1. **Excel 导入 replace/update 模式**（G7 首切片推荐）
   - 落地距离最近：BOQ 服务端导入已闭环（G2/G3）、job 框架已有、xlsxwriter 零新增供应链、digest 限额模式可直接演化为幂等基座
   - 高风险点：`replace`/`update` 批量改写既有数据 → 专用权限、确认摘要、幂等、审计四件套（ADR-004 §决策 4）
2. **Editor 受限富文本写入**
   - 依赖 ADR-006 批准；sanitize-on-save + 受控附件引用；并发版本（§6.8 要求）直指 G7 并发缺口
3. **BOQ 内联编辑（前端 patch → 服务端权威重算）**
   - P1 业务写入最典型场景（§6.4：前端不在本地形成金额事实）；10k 行并发冲突验收是硬门槛
4. ~~Gantt 拖拽写入~~：ADR-003 本期否决，不排期

## 5. G7 前必须补齐的基建缺口

| 缺口 | 建议方案 | 归属 |
| --- | --- | --- |
| 幂等键/并发版本统一基建 | 以 BOQ digest 模式为蓝本提炼统一「写动作幂等契约」（intent 携带幂等键 + 服务端去重窗口），先在 Excel 导入切片落地，Editor/BOQ 编辑复用 | P0 runtime + 后端 intent |
| 业务写动作审计定式 | 沿用 sc.audit.log 模型，为业务写 intent 定义统一审计挂接模式（谁/何动作/何对象/变更摘要/幂等键），不新造审计模型 | 后端 |
| 高风险写入专用权限组 | replace/update 导入、Editor 启用等按 §14 走独立 feature flag + kill switch + 专用组，不并入既有业务组 | 后端安全 |

## 6. 建议路径（呈报决策）

```text
决策点 1（本次）：B 轨 ADR 批准
  ├─ 推荐：先批准 ADR-004（Excel）→ G6 式只读/job 实现（一个 PR 批次）
  │        → replace/update 危险模式作为 G7 首切片立项
  ├─ 备选：ADR-004/005/006 三项同时批准（并行三线，共享 §13 单写入者约束下排队合入）
  └─ 备选：暂不批准 B 轨，转 Post-GA 长尾旅程覆盖（gap.role_journey_longtail_coverage）

决策点 2（ADR 批准后）：G7 立项正式化
  ├─ 幂等基建 PR（独立小批次，Excel 切片前合入）
  └─ G7 首切片 PR（Excel replace/update，含审计四件套 + 五视口 + 回退验收）
```

## 7. 决策结果（2026-09-06，用户批准）

1. **ADR-004（Excel）批准为 Accepted**（决策 1–6 全部生效）；ADR-005（PDF）与
   ADR-006（Editor）维持 Proposed，B 轨其余能力仍冻结待批。
2. 采用「先 ADR-004 单线」路径：G6.3 批次（Excel 只读/job 实现）先行，
   幂等基建 PR 在 G7 首切片前合入。
3. **G7 首切片确认 = Excel replace/update 危险导入模式**（ADR-004 决策 4 范畴），
   在 G6.3 合入后正式立项。

执行批次：G6.3（G6.3-A 审计 → G6.3-B 后端实现 → G6.3-C E2E/门禁/PR 收口）。

## 8. G6.3 执行记录（Excel 只读/job 实现先行）

- **G6.3-A 审计结论**：BOQ 导入向导既有 digest 冻结/复核模式可复用；sc.ops.job
  为纯记录模型（无执行框架，状态经 `/api/ops/job/status` 暴露）；容器运行时
  xlsxwriter 3.0.2 / openpyxl 3.1.5 / defusedxml 0.7.1 已存在——**供应链零新增**。
- **G6.3-B 实现**（ADR-004 决策 1/2/3）：
  - 契约 `contracts/domain/boq-export.yaml` v1（只读导出投影，registry 登记，
    结构指纹 domains 10→11）；
  - 服务 `services/boq_export_service.py`：列级权限裁剪（成控组全列 / 项目只读
    裁金额列且 cropped_columns 明示）、xlsxwriter 惰性导入（桩环境可测纯函数）、
    行上限 5000；
  - handler `handlers/boq_export_request.py`（intent=project.boq.export.request）：
    search 语义防版本枚举侧信道，五级结构化降级（MISSING_PARAMS /
    VERSION_NOT_FOUND / EXPORT_EMPTY / EXPORT_TOO_LARGE / EXPORT_ERROR）；
  - 落档：ir.attachment（sudo 建档挂版本记录）+ sc.ops.job（job_type=boq.export，
    status=done + result_json）；
  - 三处同步纪律齐备（handler / intent 注册表 234 行 / split guard pinned intent）；
  - 桩测试 11 例全绿 + `make verify.boq.export.capability` 挂入 ci.local.quick。
- **G6.3-C E2E**（dev 栈，探针 tmp/g63_boq_export_e2e.sh，须带 X-Odoo-DB 头）：
  成控视角 13 列全量导出（attachment+job 落档断言）/ 项目只读视角 10 列
  （cropped_columns=[price,imported_amount,amount] 明示）/ EXPORT_TOO_LARGE
  （10k 行版本）/ VERSION_NOT_FOUND / MISSING_PARAMS / 持久层双确认（sc_ops_job
  + ir.attachment）——六路径全绿；`make ci.local.quick` 全绿（约 8m20s）。
- **遗留**：`make contract.registry.export` 因 10 个 native-view 类契约未登记而
  失败——干净 main 同样失败（既有问题，contract-registry.json 停留在 PR #277），
  与本批次无关，未处理。
- **下一步**：G6.3 PR 合流后，G7 首切片（Excel replace/update 危险导入模式）
  正式立项；幂等基建 PR 先行合入。

