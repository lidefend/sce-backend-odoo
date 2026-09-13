# 本地 CI 分层效率收口

## 目标与边界

- Formal Product Layer：P4 ops delivery tool。
- Layer Target：`make/ci.mk` 的本地迭代与最终 Quick 编排，以及基线迭代策略守卫。
- 目标：让日常内循环拥有明确、秒级、不会偷偷升级为全仓门禁的 L1 入口；最终交付门禁语义不降低。
- P4 主体不改 P1、数据库、runtime profile、浏览器矩阵、CI required checks 或发布流程。最终远端
  门禁稳定性验证暴露出的 P0 明细关系候选预加载缺陷，按下述最小共享修复单独登记。

## 两条车道

### 日常迭代

1. HMR/源码修改后运行 `make ci.local.iteration`。
2. 阅读该入口输出的前端 L2 建议；建议仅来自路径映射、不会执行测试或生成证据。按声明风险选择覆盖影响面的一项或多项已登记非零 L2 定向测试，例如：
   `make local.dev.test MODULE=smart_construction_core TEST_TAGS='<affected_tag>'`。
3. 只有模块装配、权限、数据语义或页面运行态受影响时，才进入对应 `local.dev.*` L3/L4。
4. 首个失败出现即停，只修责任层，只重跑该失败链和受影响项。

`ci.local.iteration` 只承担 L0/L1：写分支约束、策略自守卫和 diff whitespace 检查。策略守卫强制它
不得依赖全仓 page-residue、legacy credential、complexity、全历史 secret/personal-data、repository
history、前端全量 typecheck/build、浏览器、acceptance 或 `ci.local.quick`；这些检查继续保留在冻结
候选的 Quick 或受影响 L2 中。该入口不生成 exact-head receipt，不能冒充交付证据。

入口对工作区作两类状态声明：clean 输出 `change_state=clean`；任意 tracked/untracked 改动都输出
`change_state=dirty scope=unclassified_by_design`。相关改动与未知路径都不会被它自动宣称为已覆盖，
同时由 `frontend_dev_incremental.py --plan-worktree` 汇总相对 `origin/main` 的已提交改动和当前
tracked/untracked 改动，输出 `recommendation_only` 的已登记前端目标。模板消费者和 UI 包主题改动均会
建议 `verify.frontend.primitive_adapter.unit`；未知或非前端路径仍明确要求人工选择非零 L2。必须由执行者
实际运行并记录建议中的适用目标，数量不机械固定；检查失败直接非零退出。该入口不能
替代最终 Quick 或 PR CI。

### 冻结交付

clean delivery HEAD 冻结后才运行一次 `make ci.local.quick`。该入口继续包含完整历史、安全、
契约、前端 build/typecheck 和治理门禁并生成 exact-head receipt。Quick 中原先在依赖图完成
`verify.frontend.typecheck.strict` 后又在 recipe 直接执行一次的重复工作被移除；lint 与 typecheck
改为普通 Make 依赖。严格类型检查的唯一 Quick 链为
`ci.local.quick.run → verify.unified_page_contract.v2 → verify.unified_page_contract.v2.frontend_static → verify.frontend.typecheck.strict → pnpm typecheck:strict`；没有删除门禁。

### 生成证据冻结前预检

冻结顺序固定为：完成产品与测试 → 完成交付文档 → 运行 `make ci.delivery.freeze.prepare` →
审阅生成差异 → 提交并冻结 HEAD → 检查候选身份 → 一次完整 Quick。

`ci.generated_evidence.preflight` 聚合三类内容绑定检查，并置于 `ci.local.quick.run` 的昂贵历史、
类型和构建检查之前：

- `ci.generated_reports.guard`：测试清单/摘要、模块依赖、复杂度及其 split queue 等既有派生报告；
- `verify.frontend.component_driver_takeover.unit`：绑定 P0/P1 前端生产源、ownership、bridge 和锁定组件版本；
- `verify.contract_form_split_evidence`：绑定 `ContractFormPage.vue` 当前行数。

检查根据真实内容计算，不用提交类型或人工路径表猜测影响。失败只报告需要刷新的证据并非零退出；
Quick 不自动改 tracked 文件。对应刷新入口为 `make refresh.generated_reports`、
`make refresh.frontend.component_driver_takeover.inventory` 和
`make refresh.contract_form_split_evidence`，其中 ContractForm 行数刷新会在规范标记缺失或重复时拒绝改写。
`ci.delivery.freeze.prepare` 按此顺序聚合三个刷新入口并立即执行只读预检；`pr.push` 只复用该预检，
若内容陈旧则在任何远端访问前停止并指回冻结前准备，不再自动刷新 tracked 文件。
预检不生成 receipt，不能冒充 Quick；Quick receipt 仍只绑定最终 clean HEAD/tree，receipt 保存在 Git
元数据外，禁止再为记录 receipt 修改提交而形成自失效循环。

## 验收

- 基线策略非零单元必须同时证明轻量入口的必需项和禁止项。
- `make ci.local.iteration` 的 dry-run/实际运行不得出现被禁止的重型入口，并应输出 L1-only、
  非零 L2 handoff 与不执行测试的前端目标建议。
- Quick 结构检查必须保留 lint/typecheck 依赖，并禁止 recipe 中重复直接调用 typecheck。
- 生成证据预检必须位于完整 Quick 的重型依赖之前，并覆盖三类内容绑定检查；冻结前准备负责刷新，
  `pr.push` 只读验证且不得调用刷新入口，这两条边界由非零行为测试约束。
- 日常迭代只做定向测试与耗时观察；冻结候选按交付规则运行一次完整 Quick，并绑定 exact-head
  receipt，不把该成本回灌到 HMR 内循环。

## PR 门禁稳定性补项

- `form_open` 性能样本必须在 ActionView 列表状态达到 `ok/empty` 后开始；`loading` 可见不能作为
  计时起点，避免把上一段列表加载误计入表单打开时间。绝对预算、相对回归比例和样本下限不变。
- “关系候选不得预加载”的计数在进入目标表单前等待有界静默窗口，再冻结基线；目标表单出现的
  真实候选请求仍会使断言失败，不通过固定 sleep 或忽略请求制造通过。
- 远端运行证明 `X2ManyRelationRenderer` 会在可见行 scope 初始化时、未发生用户交互即枚举
  `construction.contract` 候选。该首次失效点属于 P0 共享 renderer，而非 P4 计数误差：scope 变化
  现在只失效旧选项，仅在对应弹层真实打开时重新查询；已选关系沿用记录携带的权威 `[id, label]`
  本地显示。影响面限定为 one2many 中 many2one 候选加载时机，不改变权限、domain 或保存语义。
