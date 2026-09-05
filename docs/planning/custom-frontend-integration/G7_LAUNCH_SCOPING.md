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

## 9. G7-INFRA 执行记录（统一写动作幂等基建，G7 首切片前置）

- **审计结论（G7-INFRA-A）**：api_data_write 三 handler 走 `utils/idempotency.py`
  的审计投影查重（search 有并发竞态）；my.work.complete_batch 是唯一业务写
  intent 先例；依赖方向 smart_construction_core → smart_core，基座须落 smart_core。
- **实现（G7-INFRA-B）**：
  - 模型 `sc.idempotency.record`（smart_core v17.0.1.1.12）：(company, actor,
    idempotency_key) 部分唯一索引做 DB 层并发仲裁；status
    inflight/done/failed；result_json 存可重放响应；审计轨迹权威仍是
    sc.audit.log，去重权威切到本模型；
  - utils：`claim_write_idempotency`（mode: claimed/takeover/replay/conflict/
    in_flight/new）+ `complete_write_idempotency`（savepoint 包裹 write，
    result 经 `_json_safe_result` 净化）；
  - my.work.complete_batch 试点接入：SOURCE_AUTHORITY.idempotency_authority
    更新为 "sc.idempotency.record + sc.audit.log"；同键同指纹重放、同键异指纹
    409、跨主体（actor+company）隔离；
  - 契约 `contracts/domain/write-idempotency.yaml` v1（registry 登记，结构指纹
    domains 11→12）；reason code 新增 REASON_IDEMPOTENCY_IN_FLIGHT；
  - 桩测试 18 例（含两个线上踩坑回归钉子）+ 既有 3 例边界测试。
- **E2E（G7-INFRA-C，dev 栈，探针 tmp/g71_idempotency_e2e.sh）**：六路径全绿
  ——首次执行落档 / 同键同参重放（replay_from_record_id>0）/ 同键异参 409
  IDEMPOTENCY_CONFLICT / 跨主体隔离 / 持久层双确认（result_json 落库、
  actor/company 盖章）/ 冲突不覆写原记录。
- **线上排障沉淀（两个深坑，均已加回归钉子）**：
  1. Odoo `env.get()` 对已注册模型返回**空记录集**，空记录集 `bool()` 为 False
     ——模型存在性判定必须用 `is None`（既有 audit 通道守卫同病，一并修复）；
  2. 该 Odoo 构建 `fields.Datetime.now()` 返回 **datetime 对象**（非字符串），
     含 datetime 的 payload 写 `fields.Json` 抛 TypeError；且 Odoo write 逐字段
     进缓存延迟 flush，异常前已进缓存的字段仍随事务提交落库，留下
     「done 无 result」残行致后续同键误判冲突——complete 侧 JSON 净化 +
     savepoint 原子包裹双修复。

## 10. G7.1 执行记录（Excel replace/update 危险导入首切片）

- **实现四件套（G7.1-B 落盘）**：
  - `handlers/boq_dangerous_import.py`：双 intent（`boq.batch.dangerous.import`
    preview/execute 同入口，mode 区分）；flag gate（kill switch
    `sc.boq.dangerous_import.enabled`，默认关）+ 令牌确认（preview 返回
    confirm_token，execute 重算比对防 TOCTOU）；
  - `services/boq_dangerous_import_service.py`：replace（整批 unlink 重写）与
    update（code 匹配增量改）两种危险模式；缺失侧不造点纪律沿用 G6.1；
  - 契约 `contracts/domain/boq-dangerous-import.yaml` v1（registry 登记，
    结构指纹 +39 行）；数据文件 `data/boq_dangerous_import_params.xml`
    （noupdate kill switch 种子）；
  - 桩测试 29 例全绿；`make verify.boq.dangerous.import.capability` 挂入
    ci.local.quick 依赖链（py_compile 四文件 + 桩测试直跑）。
- **E2E（G7.1-C，dev 栈，探针 tmp/g71_boq_dangerous_import_e2e.sh）**：三轮
  迭代 22/22 全绿——P0 开关缺失+无组双拒；P1 开开关后无组仍拒；P2 授权后
  preview 干跑（readonly/无业务写）→ 令牌漂移拒 → replace 执行（批次落库
  +行数断言）→ 幂等重放（同键同指纹直接返回首次结果，不重复写）→ update
  匹配（qty 3→5）→ 审计/批次证据≥2；P3 开关回退双 intent CAPABILITY_DISABLED
  且数据不变；P4 清理（撤销组+删参数行）。
- **设计缺陷发现与修复（本切片最重要产出）**：原实现「令牌重算 → claim」
  导致响应丢失后的字面重试必然 CONFIRM_TOKEN_MISMATCH（首次执行后 DB 已变，
  重算令牌漂移），幂等重放通道形同虚设。修正为「claim 前置 → 解析 → 令牌
  重算 → 执行」：指纹绑定**客户端提供的 confirm_token + file_digest**（免解析
  即可计算），原样重试命中 replay 分支直接返回首次结果；令牌重算仅对首次
  执行生效——漂移即 TOCTOU 防护语义，与重放通道互不冲突。claim 后降级路径
  （parse error/empty/ambiguous/token mismatch）统一 `_release_failed` 释放
  幂等行为 failed（允许接管重试）。
- **踩坑沉淀（四则）**：
  1. 向导 `_parse_file` 的 CSV 分支仅 `include_details=True` 返回 4 元组
     （rows/uoms/skipped/detail），`False` 返回 3 元组——handler 必须与向导
     action_preflight/action_import 同口径，否则 `PARSING 解包崩溃`；
  2. intent 中间件在 `run()` 里对 is_write() 为真的 intent（preview 也被判写）
     先执行 `enforce_required_groups` 再进 handler flag gate——无组用户在开关
     关闭时看到的是 PERMISSION_DENIED 而非 CAPABILITY_DISABLED，E2E 断言须
     接受二元组；
  3. `has_group`（ormcache 按 worker 进程）与 `ir.config_parameter.get_param`
     同样被缓存——psql 直插授权/开关后必须 `docker restart` odoo 才对 HTTP
     worker 生效；
  4. noupdate=1 数据文件里的 `<function set_param>` 在模块升级模式被跳过
     （G7-INFRA 已知坑复现），kill switch 须探针自行 psql 插入。
- **遗留（预存环境漂移，非本切片引入）**：dev 栈模块级联升级时
  smart_construction_demo 的 cost_demo.xml 本位币断言失败（dev 公司本位币 USD
  而 demo 种子按 CNY 语境写约束）——core 模块事务已按模块分段提交
  （17.0.0.158 + 权限组落库），直接重启 odoo 继续验证即可。

