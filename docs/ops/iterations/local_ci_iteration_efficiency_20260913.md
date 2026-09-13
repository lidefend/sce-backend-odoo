# 本地 CI 分层效率收口

## 目标与边界

- Formal Product Layer：P4 ops delivery tool。
- Layer Target：`make/ci.mk` 的本地迭代与最终 Quick 编排，以及基线迭代策略守卫。
- 目标：让日常内循环拥有明确、秒级、不会偷偷升级为全仓门禁的 L1 入口；最终交付门禁语义不降低。
- 不改 P0/P1 产品、测试断言、数据库、runtime profile、浏览器矩阵、CI required checks 或发布流程。

## 两条车道

### 日常迭代

1. HMR/源码修改后运行 `make ci.local.iteration`。
2. 按声明风险选择覆盖影响面的一项或多项已登记非零 L2 定向测试，例如：
   `make local.dev.test MODULE=smart_construction_core TEST_TAGS='<affected_tag>'`。
3. 只有模块装配、权限、数据语义或页面运行态受影响时，才进入对应 `local.dev.*` L3/L4。
4. 首个失败出现即停，只修责任层，只重跑该失败链和受影响项。

`ci.local.iteration` 只承担 L0/L1：写分支约束、策略自守卫和 diff whitespace 检查。策略守卫强制它
不得依赖全仓 page-residue、legacy credential、complexity、全历史 secret/personal-data、repository
history、前端全量 typecheck/build、浏览器、acceptance 或 `ci.local.quick`；这些检查继续保留在冻结
候选的 Quick 或受影响 L2 中。该入口不生成 exact-head receipt，不能冒充交付证据。

入口对工作区只作两类声明：clean 输出 `change_state=clean`；任意 tracked/untracked 改动都输出
`change_state=dirty scope=unclassified_by_design`。相关改动与未知路径都不会被它自动宣称为已覆盖，
必须由执行者按风险选择一项或多项非零 L2，数量不机械固定；检查失败直接非零退出。该入口不能
替代最终 Quick 或 PR CI。

### 冻结交付

clean delivery HEAD 冻结后才运行一次 `make ci.local.quick`。该入口继续包含完整历史、安全、
契约、前端 build/typecheck 和治理门禁并生成 exact-head receipt。Quick 中原先在依赖图完成
`verify.frontend.typecheck.strict` 后又在 recipe 直接执行一次的重复工作被移除；lint 与 typecheck
改为普通 Make 依赖。严格类型检查的唯一 Quick 链为
`ci.local.quick.run → verify.unified_page_contract.v2 → verify.unified_page_contract.v2.frontend_static → verify.frontend.typecheck.strict → pnpm typecheck:strict`；没有删除门禁。

## 验收

- 基线策略非零单元必须同时证明轻量入口的必需项和禁止项。
- `make ci.local.iteration` 的 dry-run/实际运行不得出现被禁止的重型入口，并应输出 L1-only 与
  非零 L2 handoff。
- Quick 结构检查必须保留 lint/typecheck 依赖，并禁止 recipe 中重复直接调用 typecheck。
- 日常迭代只做定向测试与耗时观察；冻结候选按交付规则运行一次完整 Quick，并绑定 exact-head
  receipt，不把该成本回灌到 HMR 内循环。

## PR 门禁稳定性补项

- `form_open` 性能样本必须在 ActionView 列表状态达到 `ok/empty` 后开始；`loading` 可见不能作为
  计时起点，避免把上一段列表加载误计入表单打开时间。绝对预算、相对回归比例和样本下限不变。
- “关系候选不得预加载”的计数在进入目标表单前等待有界静默窗口，再冻结基线；目标表单出现的
  真实候选请求仍会使断言失败，不通过固定 sleep 或忽略请求制造通过。
