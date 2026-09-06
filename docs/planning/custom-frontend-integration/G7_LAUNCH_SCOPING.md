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

## 11. G7.2-A 立项审计（BOQ 内联编辑，§4 切片 3）

> 审计日期：2026-09-06（G7.1 合流后 main=b95bbc0f）。切片 2（Editor 富文本）
> 依赖 ADR-006 批准（仍 Proposed，冻结），切片 3 为排序中下一无阻塞项。

### 11.1 可复用面（落地距离近的核心依据）

- **金额重算链完全服务端权威**（models/core/boq.py）：`amount`（compute
  store recursive，boq.py:489-503，imported_amount 优先、父节点聚合子项）+
  `amount_leaf`（:505-520）+ version `total_amount`（:73-78，聚合自行触发）
  ——qty patch 后整链自动重算，**模型无任何 onchange**，前端不形成金额事实
  的 §6.4 约束天然满足。
- **写 handler 定式可直接套用**（boq_dangerous_import.py）：REQUIRED_GROUPS
  组闸 → kill switch → 参数 → 版本状态闸（仅 draft/validated 可写，:245）→
  `is_boq_frozen()` 拒绝 → claim/complete 幂等（G7-INFRA 基建）→ savepoint
  原子执行 → sc.audit.log before/after。
- **ORM 层兜底已存在**：line.write 守卫（boq.py:583-598，quantity 在
  snapshot_fields，published/superseded 禁改）+ line.unlink 守卫
  （:634-650，冻结抛 P0_BOQ_FROZEN）+ version.write 守卫（:137-147）。
- **前端调用形态**：writeRecordV6（api/data.ts:313，带 request_id/
  idempotency_key/if_match 乐观锁参数）可作提交通道参考。
- **ACL 现成**：project.boq.line / version 上 cost_manager 全权、
  **cost_user 读写改无删**（ir.model.access.csv:121-126）——常规单行编辑
  与 replace/update 批量重写不同风险级，无需专用新组（待决策确认）。

### 11.2 缺口（需新建）

1. **专用写 intent**：通用 api.data.write 白名单不含 project.boq.line 且
   组不对口（core_extension_policy_maps.py:815-823）→ 需新建
   `project.boq.line.patch` 类 intent；
2. **前端 BOQ 明细表格不存在**：现有 BOQ 前端仅导入预检只读卡片
   （BoqImportPreviewPanel.vue，data-readonly="true"）；ScTable.vue 为
   TDesign 语义封装，**无可编辑 cell**——前端是本切片最大增量；
3. **行级并发基线缺失**：无行写版本号/digest 字段，需借「请求携带
   expected 基线值 + version 状态闸 + claim 幂等」组合，或引入 ETag；
4. **交互规则未定**：qty 编辑是否仅限 draft/validated 版本（dangerous
   import 有此闸，常规向导路径只查 frozen——口径需统一）。

### 11.3 呈报决策点

1. **批次切分**：后端先行（intent+幂等+审计+E2E 探针验证全链，前端编辑
   cell 下一批次）vs 前后端同期一个 PR；
2. **可编辑字段范围**：首期仅 quantity vs 含 price/uom/name；
3. **并发基线**：expected 基线值比对（轻量）vs if_match ETag（重）vs
   仅版本状态闸（最轻，10k 行并发验收口径待定）；
4. **权限组**：复用 cost_user/cost_manager（推荐，单行常规写）vs 新建
   专用组。

## 12. G7.2 执行记录（BOQ 行内联编辑后端先行，2026-09-06）

> 决策结果：四项呈报全部按推荐批准——后端先行 / 首期仅 quantity /
> expected 基线值 / 复用 cost_user。切片 2（Editor）仍冻结待 ADR-006。

### 12.1 实现四件套（G7.2-B 落盘）

- `handlers/boq_line_patch.py`：intent `project.boq.line.patch`（单阶段
  协议，区别于危险导入两阶段确认——单行单字段常规写，expected 基线已
  承担并发防护，无需 preview 干跑）；流程 = 参数校验（claim 前不占幂等
  行）→ 行加载（LINE_NOT_FOUND）→ 版本状态闸（VERSION_NOT_MUTABLE，
  仅 draft/validated）→ 冻结拒绝（BOQ_FROZEN）→ claim 幂等（复用
  G7-INFRA 基建 + G7.1 层序修正定式：claim 前置，指纹绑定 line_id +
  expected/new quantity + idem_key，原样重试命中 replay）→ 基线比对
  （BASELINE_MISMATCH 释放 failed，round(6) 容差）→ QTY_BELOW_DONE
  预检 → savepoint 内 `line.write({"quantity": ...})` → after 投影
  （DB/ORM 重读权威）→ complete → 审计 before/after。无 kill switch
  （回退面 = 版本状态闸 + ORM write 守卫 + ACL + intent 不注册即不可达，
  写入范围仅 quantity 单字段）。REQUIRED_GROUPS=[cost_user, cost_manager]
  OR 语义；ACL_MODE=record_rule。
- `services/boq_line_patch_service.py`：纯函数层（normalize_quantity /
  quantity_baseline_matches round(6) / qty_below_done / build_audit_payload）；
- 契约 `contracts/domain/boq-line-patch.yaml` v1（registry 登记，domains
  12→13，含 idempotency_ordering 决策语义段）；
- 桩测试 17 例全绿（复用 G7.1 桩基建：_FakeDatetime 自引用 + _PatchedClaim
  注入 + _FakeLine._recompute 模拟服务端 compute 链）；make 目标
  `verify.boq.line.patch.capability` 挂入 ci.local.quick 依赖链。
- 三处同步齐备：core_extension_intent_handlers.py（导入+mapping）+
  split guard（MAX_INTENT_HANDLER_LINES 245、HANDLER_MODULES 桩、
  intent 清单）+ make/ci.mk。

### 12.2 E2E（dev 栈，探针 tmp/g72_boq_line_patch_e2e.sh，23/23 全绿）

P0 viewer 无组 PERMISSION_DENIED（中间件层）→ P1 参数/查找/状态闸
（LINE_NOT_FOUND / VERSION_NOT_MUTABLE / MISSING_PARAMS×2 /
INVALID_QUANTITY）→ P2 基线漂移拒绝且无业务写 → P3 QTY_BELOW_DONE →
P4 imported_amount 权威语义（qty 变 amount 跟来源合价）→ P4b psql 清
imported_amount 后完整服务端重算（qty 8→9，amount 27，version total 42，
DB 直读断言）→ P5 字面重试命中 replay 不重写 → P6 同键异指纹
IDEMPOTENCY_CONFLICT 且无写 → P7 审计事件 → P8 基线恢复（含
imported_amount 条件恢复）。

### 12.3 踩坑沉淀（四则）

1. **WRITE_INTENT_TOKENS 共三处须同步**：中间件按 token 集判 is_write()
   → 决定是否预检组——"patch" 不在集内时无组用户直穿 ORM ACL（返回
   PATCH_ERROR 而非 PERMISSION_DENIED）。三处 = `core/intent_operation_
   policy.py`（运行时）+ `tools/intent_write_guard.py`（REQUIRED_GROUPS
   静态守卫）+ `tools/intent_acl_mode_guard.py`（ACL_MODE 静态守卫），
   首轮漏了第三处；
2. **REQUIRED_GROUPS 须写字面量列表**：`= list(WRITE_GROUPS)` 是 AST
   Call 节点，静态守卫 _literal 解析为 None → 判「无 REQUIRED_GROUPS」
   违规；
3. **psql numeric 定宽格式 vs python 字符串比较**：psql 返回 `27.00`、
   python `round()` 输出 `27.0`，字符串不等——DB 断言须数值容差比较
   （awk num_eq）；
4. **imported_amount 来源合价是模型权威口径（非 bug）**：amount compute
   「有 imported_amount 优先取之，否则 qty×price」——qty patch 后 amount
   不变是正确行为，探针须拆「权威语义验证」与「清后重算验证」两段。

### 12.4 门禁

- 回归：intent_acl_mode_guard（130 handlers / 48 write / 0 违规）+
  intent_write_guard（0 违规）+ test_write_idempotency_claim（18 例）+
  桩测试 17 例 + split guard PASS；
- `make ci.local.quick` 全绿（EXIT=0，仅存量 eslint warning）；
- refresh.generated_reports 已刷（contract_structure_fingerprint.json +
  complexity_budget_report.md）。

## 13. G7.2-FE 执行记录（BOQ 明细表格 quantity 可编辑列，2026-09-06）

> 后端先行（§12）落地后的前端切片：HierarchicalWorksheet 工作表
> quantity 列可编辑（双击进入 → 改值 → Enter 提交 / Esc 取消），
> 服务端权威重算 + expected 基线并发防护全链路打通。

### 13.1 实现四件套

- `frontend/apps/web/src/api/boqLinePatch.ts`（75 行）：intent 调用层，
  `patchBoqLineQuantity` 发 `project.boq.line.patch`（params 携
  line_id / expected_quantity / new_quantity / idempotency_key），
  ApiError 归一 reasonCode（BASELINE_MISMATCH 等）；
- `frontend/apps/web/src/app/presentation/boqLinePatch.ts`（205 行）：
  presentation 纯函数层——编辑会话状态机
  （begin/edit/saving/error，`BoqLinePatchSession`）+
  `parseDraftQuantity` / `validateDraftQuantity`（NO_CHANGE /
  INVALID_QUANTITY）+ `isBoqLinePatchEditableRow`（仅 item 行）+
  `isBoqLinePatchAllowedViewport`（<960px 紧凑视口禁用编辑）+
  `buildBoqLinePatchIdempotencyKey`（`boq-line-patch:<line_id>:<ts>:<rand>`）
  + 成功/错误文案（`describeBoqLinePatchSuccess` /
  `describeBoqLinePatchError`）；
- `HierarchicalWorksheet.vue` renderPatchCell：编辑 cell（ScInput 数字态
  + error alert + aria 标注）；commit 成功 → 整表权威 reload + success
  notice（4s 自动消失）；BASELINE_MISMATCH → cell 内 alert + 页面级
  status notice 双层提示 + `refreshPatchBaseline`（静默整表 reload +
  会话基线同步为服务端最新值，草稿保留供基于最新值重试）；blur 即提交；
- `hierarchicalWorksheetDataSource.ts`：`editable_fields?: string[]`
  配置声明（后端 config 未注入时前端回退默认 quantity 写入面）；
- 单测 `frontend/apps/web/scripts/boq_line_patch_model_test.ts`（138 行 /
  37 断言，esbuild 打包 node 跑）挂 `verify.frontend.boq_line_patch.unit`
  → 入 ci.local.quick 依赖链（make/frontend.mk + make/ci.mk）。

### 13.2 浏览器 E2E 冒烟（dev 栈，pm1 会话，fetch 插桩验证信封）

- **Happy path**：双击 qty cell（5.00）→ ScInput 自动 focus → 改 9 →
  Enter → 请求 `{"line_id":16429,"expected_quantity":5,"new_quantity":9,
  "idempotency_key":"boq-line-patch:16429:..."}` → 响应 ok=true
  （quantity 5→9、version_total_amount 重算、idempotent_replay=false、
  审计 meta 齐全）→ 整表 reload → cell 9.00、编辑态关闭；二次编辑
  9→12 成功，notice「已更新：工程量 12 / 合价 15（服务端权威重算）」；
- **PERMISSION_DENIED**：无组用户提交 → cell 内 error alert
  「当前角色无工程量编辑权限」（编辑态保留）；
- **BASELINE_MISMATCH**（服务端经 XML-RPC 并发改 quantity=33 后提交
  expected=12）→ HTTP 500 信封 `error.code=BASELINE_MISMATCH`、message
  「工程量基线不一致：该行已被并发修改（expected=12.0，实际=33.0），
  请刷新后重试」、`suggested_action=reload_and_retry` → UI 双层提示
  （cell alert + 页面 status notice「该行已被并发修改，请基于最新
  工程量重新提交。」）→ 整表静默 reload（cell 33.00）→ 会话基线同步
  为 33 → 重新进入编辑基线=33 → 重试提交 20 成功
  （quantity_before=33.0 → quantity_after=20.0，reason_code=DONE）。

### 13.3 踩坑沉淀（四则）

1. **TDesign Input 无 keydown 事件声明**：ScInput 桥接的
   `onTDesignKeydown` 读 `context.e` 拿不到真实键盘事件（兜底
   `new KeyboardEvent('keydown')` 无 key）→ Enter/Esc 永不触发。修复：
   keydown 监听移到 `.patch-cell-editing` 外层 div（原生 DOM 冒泡），
   ScInput 仅承担输入职责；
2. **dotted domain 记录规则联动**：工作表 sheet_domain 含
   `version_id.state`（点路径）时 Odoo 应用关联模型
   `project.boq.version` 的记录规则——pm1 非 project manager 亦非
   follower → 查询恒 0 行（非点路径 domain 不受影响）。dev 栈补
   mail_followers 解决；产品层是既有 gap.role_journey_longtail_coverage
   范畴（cost 角色菜单旅程不含清单明细菜单，sc_cost_mgr 须 pm1 代跑）；
3. **agent-browser × TDesign**：坐标 click 不触发 t-menu__item 导航，
   须 eval 派发 bubbles MouseEvent 到 `li[data-navigation-key]`；TDesign
   select 类组件 fill 不可用，文本输入走 ref；agent-browser 须 Windows
   侧运行（WSL 侧连不上守护进程）；
4. **wsl.exe 命令行引号吞噬**：含引号 / `$()` / heredoc 的 bash -c
   内联命令会被 wsl.exe 破坏——复杂逻辑一律 Write 脚本到 WSL 侧 tmp/
   再 `wsl.exe -- bash <脚本>`（本轮多次复发，写 g72fe_* 脚本族规避）。

### 13.4 结构性矛盾（Open gap，非阻断）

action 534（清单明细工作表）sheet_domain 仅查 `published` 版本行，而
patch 仅允许 draft/validated 版本——正常 domain 下前端编辑入口打不到
任何可 patch 行（两者不交集）。本轮冒烟靠 DB 临时放宽 sheet_domain
（收口前已恢复 published-only）。**待后续切片决策**：工作表 domain
演进（如按版本状态 tab 切换 draft/validated 工作面）或视图层显式版本
选择器；在此之前 G7.2-FE 编辑入口在演示流程中不可自然触达。

### 13.5 dev 栈数据遗留（有意保留）

- pm1（partner 16）补德阳项目 mail_followers（id=4012）——记录规则
  project member scope 依赖 follower；
- pm1（uid 6）加入 cost_user 组（res_groups_users_rel gid=101）——
  pm1 顶栏岗位本即「项目经理 / 成本管理」双岗，兼成本写权限合理；
- line 16429 quantity 终值 20（冒烟数据，dev 栈无害）。

### 13.6 门禁

- `verify.frontend.boq_line_patch.unit`（37 断言）+ typecheck:strict +
  dist-dev 重建（36.9s）全绿（tmp/g72fe_fix_verify.sh）；
- refresh.generated_reports + takeover inventory 重刷（含
  HierarchicalWorksheet.vue digest 变更）；
- `make ci.local.quick` 全绿。

## 14. G7.3 执行记录（工作表数据域 tab：修复 §13.4 结构性矛盾，2026-09-06）

### 14.1 实现四件套

- **后端 assembler 透传**（page_assembler.py
  `_inject_native_hierarchical_worksheet`）：sheet config 新增
  `domain_tabs`，从 context `hierarchical_worksheet.sheet_domain_tabs` 透传
  （条目校验：key 非空去重、domain 必须 list、label 缺省回退 key；
  非法条目剔除）；
- **XML 契约种子**（boq_views.xml action 534）：`sheet_domain_tabs` 两 tab——
  `published`（已发布版本，domain 同原 sheet_domain，**默认**）与
  `editing`（编制中版本，`version_id.state in ['draft','validated']`，
  承载 G7.2 编辑入口）；
- **前端纯函数**（新模块 `hierarchicalWorksheetDomainTabs.ts`，零运行时
  import 保持 node 单测可 esbuild 直跑）：`resolveWorksheetDomainTabs`
  （规范化容错）+ `applyWorksheetDomainTab`（按 key 合成 domain，不变异
  原 config；无效 key 回退默认 domain——旧契约兼容）；dataSource
  re-export；
- **组件集成**（HierarchicalWorksheet.vue）：grid toolbar 渲染
  `role=tablist` 状态 tab（`section-tab` 外观复用详情 tab 样式）；
  `reloadWorksheet` 统一走 `applyWorksheetDomainTab`（含 G7.2 patch 成功
  后整表 reload——tab 语境自动继承）；`selectDomainTab` 换域权威重载并
  复位编辑会话/选中态（防悬空行）；loading 期禁点防抖。

### 14.2 浏览器 E2E 冒烟（dev 栈，pm1 会话，fetch 插桩验证信封）

1. 默认「已发布版本」tab：selected 且共 0 条（德阳版本为 draft，
   published 视图为空——修复前「编辑入口不可达」的根源语义正确呈现）；
2. 切「编制中版本」：selected 且共 3 条（draft 行），tab 往返切换正常；
3. **editing tab 下编辑链路闭环**：双击 qty cell（20.00）→ 改 21 → Enter →
   响应信封 `version_state: "draft"`、`quantity_before=20.0 → after=21.0`、
   `reason_code=DONE`、幂等键与审计 meta 齐全 → 整表 reload 后 cell
   21.00。**§13.4 结构性矛盾就此闭合**：G7.2 编辑入口在正常 domain 下
   自然触达。

### 14.3 踩坑沉淀（两则）

- **单测 bundle 依赖链**：纯函数放 dataSource 模块会被 esbuild 拖入
  api/client 链（`import.meta.env` 在 node 报错）——纯函数独立模块
  （type-only import）是该项目 node 单测的前置纪律；
- **assembler 桩测试跑法**：`test_page_assembler_view_orchestration_versions.py`
  自带 odoo mock 须**以文件方式直跑**（`python3 <file>`）；经包路径
  `python3 -m unittest addons.smart_core.tests...` 会触发 tests/__init__.py
  链式 import 真 odoo 而失败。

### 14.4 门禁

- assembler 桩测 17 例 + 前端 domain tab 单测（含容错/兼容断言）+
  既有 worksheet 交互单测回归 + typecheck:strict 全绿（tmp/g73_verify.sh）；
- 上栈：`-u smart_construction_core`（XML context 上 DB）+ 容器重启
  （assembler 新代码）+ dist-dev 重建（33.8s）；
- refresh.generated_reports + takeover inventory 重刷 +
  `make ci.local.quick` 全绿。

## 15. G7.4-A 执行记录（项目概况受限富文本编辑后端先行，ADR-006 首切片，2026-09-06）

### 15.1 前置：ADR-006 批准（Editor canonical format 解冻）

ADR-006（docs/adr/ADR-006-editor-format-and-sanitization.md）翻 **Accepted**
（用户批准决策 1–7 全部生效）：canonical format = restricted_html
（p/h1-h3/ul/ol/li/strong/em/b/i/table 子集/a/br + 受控属性）；
净化 = **nh3==0.3.7 服务端白名单**（bleach 2026-06 停维护）、
sanitize-on-save 一次入库、max_length=20000 契约下发；并发 = G7-INFRA
claim/complete 幂等定式 + **摘要基线**（sha256 hex[:16]，正文可达 20k
字符不传全文，替代 G7.2 的数值基线）；治理 = G7.1 kill switch 模式。
依赖注入 = requirements-odoo.txt 钉版
（`nh3-0.3.7-cp38-abi3-manylinux_2_17_x86_64.whl` dev 容器 Py3.10 实测可装）。

### 15.2 实现五件套 + 三处同步

- **service 纯函数**（overview_rich_text_patch_service.py）：白名单常量、
  `sanitize_overview_html`（延迟 `import nh3`，缺依赖抛 RuntimeError →
  fail-closed）、`overview_digest`/`baseline_matches`/`content_over_limit`/
  `flag_enabled`（仅认 1/true/yes/on）、`build_audit_payload`（摘要+长度，
  不落全文）；
- **handler**（overview_rich_text_patch.py，intent
  `project.overview.rich_text.patch`）：kill switch gate → 参数/长度校验
  （claim 前）→ sanitize（claim 前）→ 项目加载 → claim 幂等 → 摘要基线
  比对（漂移→`_release_failed`）→ savepoint write → after 投影
  （content_after/digest/length/sanitized_input_changed）→ complete → audit；
- **字段**：`project.project.overview_html = fields.Text`——**刻意不用
  fields.Html**（ORM Html 自带 sanitize 会形成第二净化权威，违背 ADR-006
  「nh3 唯一服务端权威」）；
- **组/开关**：`group_sc_cap_rich_text_editor` 专用组 +
  `rich_text_editor_params.xml`（noupdate ir.config_parameter
  `sc.rich_text_editor.enabled=false`，G7.1 同款 fail-closed）；
- **契约**：overview-rich-text-patch.yaml v1（identity=
  expected_overview_digest，八条错误码映射）；
- **三处同步**：handlers/*.py + core_extension_intent_handlers.py
  （导入+mapping）+ split guard（HANDLER_MODULES+行数预算 249+pinned
  intent）；WRITE_INTENT_TOKENS 三处（运行时+两个静态守卫）天然覆盖
  "patch" 令牌（G7.2 已加）。

### 15.3 测试与 E2E

- 桩测 21/21（sys.modules 假 odoo/smart_core 链 + `_PatchedClaim` 幂等
  分支 + 假 nh3 可注入内容变换验证 sanitized_input_changed）；
  intent_write_guard（131 handlers）+ intent_acl_mode_guard + split guard
  全 PASS；挂 ci.local.quick（verify.overview.rich.text.patch.capability）；
- **E2E 15/15 全绿**（tmp/g74_overview_rich_text_e2e.sh，pm1 编辑主体）：
  无组+flag 关→PERMISSION_DENIED（中间件组检查先于 handler kill switch，
  G7.1 纪律）/ 授组+flag 关→CAPABILITY_DISABLED / 缺参/超长/项目不存在 /
  成功（script 与 javascript: 剥除、mailto 保留、sanitized_input_changed）/
  replay / 同键异指纹 409（error.code=INTERNAL_ERROR +
  reason_code=IDEMPOTENCY_CONFLICT，G7.2 信封复验）/ BASELINE_MISMATCH +
  基线刷新重试闭环 / 审计 / flag 再关 / 数据还原。

### 15.4 踩坑沉淀（四则）

- **E2E 编辑主体的 ORM ACL**：富文本编辑组不含 project.project 写权限
  （allowed: 业务配置管理员/项目中心审批/项目中心经办/Project
  Administrator）——ORM ACL 守卫按设计拦截（PATCH_ERROR 整体回滚）；
  探针选 pm1（自带项目中心经办/审批）+ 授专用组，admin 仅作 XML-RPC
  管理操作（XML-RPC admin 密码=.env.dev 的 ADMIN_PASSWD，demo 用户密码
  =SC_DEMO_USER_PASSWORD，两者不同）；
- **授组使旧 token 失效**：Odoo 对 res.users 的 write（改 groups_id）
  会使用户会话缓存失效——E2E 授组后必须重新 login，否则全线
  AUTH_REQUIRED；
- **XML-RPC execute_kw 参数形状**：args 是位置参数列表——set_param 须
  `["key", "value"]` 两个位置参数（`[[key, value]]` 会把 [key,value] 当
  单个参数传，报 missing 'value'）；res.users.write 同理 `[[uid], {vals}]`；
  dev nginx（18081）不暴露 /xmlrpc/2，XML-RPC 走 odoo 直连 8070；
- **探针自身幂等**：E2E 幂等键固定字面量会在 1h 窗口内与上轮运行残留
  的 sc.idempotency.record 冲突（replay 不落库→基线错位连锁 FAIL）——
  键必须带 `RUN=$(date +%s)` 后缀（G7.2 探针既有纪律的再现）。

### 15.5 门禁

- 上栈：requirements nh3 装入 dev 容器 + `-u smart_construction_core`
  （overview_html 列/组/kill switch 参数上 DB；noupdate 数据文件在 -u
  升级时不重放——参数缺席=fail-closed 语义正确，与 G7.1 一致）；
- refresh.generated_reports（complexity report scanned 4288→4292，新文件
  均在预算内）+ `make ci.local.quick` 全绿。

## 16. G7.4-B 执行记录（项目概况受限富文本编辑器前端，ADR-006 前端切片，2026-09-06）

### 16.1 前端组件五件套 + 注册接线

- **RestrictedHtmlEditor.vue**（`src/components/editor/`）：受限工具栏
  （加粗/斜体/一级~三级标题/正文段落/无序/有序列表/插入链接）+
  contenteditable 编辑区 + 实时字符计数（读 props.modelValue，
  max_length 契约下发）；指令走受控 execCommand 白名单，
  **不引入第三方 editor 依赖**（ADR-006 canonical=restricted_html 的
  受限投影，ADR-002 同款「不加重运行时」纪律）；
- **BlockRichTextOverview.vue**（`src/components/page/blocks/`）：查看态
  （v-html 渲染服务端已净化内容 + can_edit 双闸投影「编辑」入口）/
  编辑态（编辑器 + 保存/取消 + 保存中/错误态）会话状态机；保存走
  `project.overview.rich_text.patch` intent（expected 基线透传服务端比对）；
- **presentation 纯函数层**（`src/app/presentation/overviewRichTextPatch.ts`）：
  块数据规范化（envelope/裸 data/缺字段回退）、session 状态机、draft
  长度预校验、契约错误码→人话文案——只 import type，桩测可
  esbuild+node 直跑；
- **api 层**（`src/api/overviewRichTextPatch.ts`）+ **客户端预净化**
  （`src/utils/sanitizeRestrictedHtml.ts`：超长/白名单外标签客户端先行
  拦截；服务端 nh3 仍是唯一净化权威）；
- **注册**：pageBlockRegistry 挂 `block_type=rich_text_overview`。

### 16.2 后端读投影块接线（block.fetch + enter 契约）

- **project_overview_builder.py**（services/project_dashboard_builders/）：
  overview 块运行时 builder——一次性携带 content/overview_digest/
  max_length/can_edit（编辑面板免二次 fetch）；can_edit = kill switch
  flag + `group_sc_cap_rich_text_editor` 双闸（fail-closed，仅控制前端
  入口显隐，写路径权威校验仍在 handler，纵深防御）；state=empty 是
  合法空态（overview_html 空）；
- project_dashboard_service 注册 builder + scene profile 挂块
  （`block.project.overview`）；
- **hook facts entry_blocks**（core_extension_hook_facts.py）：
  ProjectDashboardSceneOrchestrator 的 entry_blocks **首位**插入
  `("overview", "项目概况", "deferred")` → BaseSceneEntryOrchestrator
  .build_entry 生成 enter 契约 blocks stub + runtime_fetch_hints →
  scene_contract_standard_v1.page.blocks。**stub 用短名 `overview`**，
  完整块 key 仅出现在 block.fetch 运行时 payload（探针须按短名断言）。

### 16.3 测试与验证

- 桩测：test_project_overview_builder.py **8/8**（含 enter 契约接线钉子：
  entry_blocks 含 overview、标题「项目概况」、block_fetch_intent、
  alias_map 不含 overview）；overview_rich_text_model_test.ts 全过
  （挂 ci.local.quick：verify.frontend.overview_rich_text.unit）；
- E2E：g74b_overview_block_e2e.sh **8/8**（deferred→fetch→投影→can_edit
  双闸→错误码全链路）；g74b_scene_enter_check.sh PASS（三处契约位置
  均含 overview：data.blocks / runtime_fetch_hints.blocks /
  scene_contract page.blocks）；
- typecheck:strict 通过；eslint 0 errors（1 个 vue/no-v-html 警告，与
  仓库既有 v-html 组件一致——内容由服务端 nh3 净化 + 客户端预净化）；
- **浏览器冒烟**（agent-browser，pm1 授组开闸）：驾驶舱「项目概况」块
  渲染 → 编辑态工具栏/计数正常 → 输入后保存解锁 → 保存成功提示
  「内容已保存（服务端净化后落库）。」→ 内容回读渲染闭环 → 数据还原
  （overview_html 置空）+ flag 关 + 撤组关门。

### 16.4 踩坑沉淀（四则）

- **canSubmit dirty 判定陷阱**：组件 `draft` ref（v-model 逐键实时更新）
  与 `session.draft`（beginEdit 快照）分离——dirty 判定必须比较实时
  draft 与 baselineContent；比较 session 快照恒等 → 保存按钮永不解锁
  （浏览器冒烟抓出的真实集成 bug，桩测覆盖不到 v-model 实时性）；
- **enter 契约探针按短名断言**：entry stub 与 runtime_fetch_hints 用短名，
  完整 block key 只在 block.fetch payload——搜完整 key 恒 0 会误判
  「未接线」；确认接线须解包实际响应三处位置；
- **宿主 D:\user\wsl.localhost 是过期镜像副本**：D 盘 9 月 5 日的完整
  独立文件树（含 .git），非 ext4 联接——文件编辑必须走权威 UNC
  `\\wsl.localhost\Ubuntu-24.04\...`，否则改动落旧树、WSL 侧不可见
  （本切片曾因此出现「Edit 成功但 grep 不到」的假象）；
- **P0/P1 原生交互元素禁令（frontend_release_gate 实测拦截）**：
  component-driver takeover inventory 守卫
  （test_completion_rule_cannot_hide_unassessed_raw_behavior）要求
  rawBehaviorSurfaces 恒空——P0/P1 生产源码不得出现原生
  `<button>/<input>/<select>/<textarea>/<table>/<dialog>/<details>`
  与 window.confirm/alert/prompt（首版 RestrictedHtmlEditor 工具栏用
  原生 button + window.prompt 取链接、BlockRichTextOverview 用原生
  button 内联动作，被 CI 拦下）；修法=工具栏/内联动作换 ScButton
  （size=small variant=ghost），链接输入换 ScDialog+ScInput 对话框
  （选区跨对话框保留：开框前 cloneRange 存 Range，确认时 focus+
  removeAllRanges+addRange 恢复后再 execCommand createLink）；
  本地复现：python3 scripts/audit/generate_frontend_component_driver_
  takeover_inventory.py 后看 rawBehaviorSurfaces 是否为空（该守卫不在
  ci.local.quick，只在远端 frontend_release_gate——首版被拦正因本地
  门禁盲区）；
- **Sc 根类不得拥有视觉铬（frontend_primitive_adapter_guard）**：放在
  ScButton/ScInput/ScDialog 等原语根元素上的自定义 class，其 scoped CSS
  不得含 border/background/border-radius/box-shadow/outline/color
  （含 border-color/color 变体）——悬停/禁用视觉由原语变体自带；本地
  门禁盲区同上（verify.frontend.quick.gate 不在 ci.local.quick，且本地
  node 版本不支持 --experimental-strip-types 跑不了整个 quick.gate，
  须单独跑 python3 scripts/verify/frontend_primitive_adapter_guard.py）；
- **agent-browser Windows 直调**：bash 传 POSIX 路径会被 node 当相对
  当前盘符解析（MODULE_NOT_FOUND）——须 node.exe + Windows 风格路径调
  bin/agent-browser.js；交互 ref 页面重载后全部失效须重新 snapshot -i；
  离屏元素先 scrollintoview 再 click。

### 16.5 门禁

- refresh.generated_reports（complexity scanned 4292→4299，新文件均在
  预算内）+ generate_frontend_component_driver_takeover_inventory.py
  单独重跑（新增前端组件入册，CI frontend_release_gate 查它）+
  `make ci.local.quick` 全绿。
