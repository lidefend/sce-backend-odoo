# 测试基线可复现性整改设计 v1

## 1. 问题（已诊断，证据见 2026-10-25 会话）

基线不可复现，根因分四类：

1. 输入未冻结：206 个 TransactionCase + 8 个 HttpCase 在本地跑持久 demo 库
   （`sc_dev_demo` + `SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1`），CI 用隔离
   `sc_suite_ci` + `SC_ENVIRONMENT=test`。两层数据库身份不一致，本地结果不是
   可复现基线。
2. 输出非确定：`docs/engineering_convergence/test_inventory.csv` 用位置序号 ID
   `T-ASSET-{index:03d}`（`scripts/ci/generate_test_inventory.py`）。增删一条资产即
   整体重排（实测删 2 个脚本产生 1294 插入 / 1519 删除）；且该序号被
   `scripts/audit/verification_lane_dispositions.json` 与 planning 文档以文本引用，
   序号漂移会静默指向别的资产。
3. 无可复现门禁：没有确定性/隔离的机器可检查证明，flaky 无 quarantine。
4. 全量无借用：`make ci.local.quick` 只给三个受管扫描接了祖先增量，测试矩阵
   （纯单元 + 静态守卫 + 前端 build/lint/typecheck）每次全跑。

## 2. 目标：可复现基线契约

同样的输入产出同样的输出，失败可归因到代码 / 环境 / flaky 三类之一。满足这条
之后，增量复用才有意义。

## 3. 系统方案（三层，依赖有序）

### 地基：输入冻结 + 输出归一化

- L1.1 统一 ORM 测试数据库身份：新增受管 disposable 测试库 profile（对齐 CI 的
  `sc_suite_ci` / `SC_ENVIRONMENT=test`），本地 ORM 测试不再跑 demo 库。
- L1.2 台账稳定 ID：`test_inventory.csv` 的 `T-ASSET-*` 从位置序号改为内容派生
  （路径 SHA），增删资产不再整体重排。
- L1.3 契约组装内核权威输入 fixture 化：model/view/permission 的确定性输入显式
  冻结，不与 live 库状态耦合。

### 门禁：可复现性证明

- L2.1 确定性探针：同一受管命令跑 N 次，断言 canonical 输出逐字节一致。
- L2.2 隔离证明：随机顺序执行结果一致。
- L2.3 flaky quarantine：已隔离 flaky 不进门禁，且计数可见。

### 增量：受影响集合复用

- L3.1 把 `scripts/ops/evidence_scope.py` 的输入指纹 → 受影响集合机制扩展到
  后端 / 静态测试套件，Quick 只跑受影响集合。
- L3.2 契约快照显式 diff 确认，不再靠提交钩子自动刷新后静默入库。

#### L3.1 具体机制（待实现）

Quick 的套件清单是 `make/ci.mk` 里 `ci.local.quick.run` 的 prerequisites，由
`local_quick_evidence.py` 的 sharded lane 复现。把每个套件声明成一个
`evidence_scope.units.v1` unit：

1. 套件清单：新增 `scripts/ops/quick_suite_manifest.json`，每一项是
   `{suite: "<target>", command: [...], inputs: [<path/glob>...]}`。inputs 用
   显式路径，不允许目录级通配。
2. 指纹：`sha256(command + 排序后的每个 input 文件内容)`。命令本身也是输入
   （同一 target 换配方即失效），避免“改了脚本却复用旧结果”。
3. 计划：`local_quick_evidence.py` 生成 units 文档，交给 `evidence_scope.py`
   对账；指纹未变且 ledger 记录为成功的套件 REUSE，其余 RUN。
4. 台账：`.runtime/evidence-scope/` 记录每套件的指纹与 outcome；只允许
   `passed/checked/declared/reused` 被沿用，失败套件永不静默复用。
5. 冻结 identity 绑定：unit 指纹之外，套件的受管运行身份（`sc_test` 库、
   环境、候选顺序）也进 `identity`，身份变则全部失效。

目标是：只加测试文件 / 只删脚本 / 只改文档时，Quick 不再重跑整个矩阵，
只跑声明输入真正变化的套件。

## 4. 实施顺序

1. L1.2（台账稳定 ID，已落地）。
2. L1.1（ORM 测试数据库身份，受管 profile，需单独授权确认）。
3. L2.1 + L2.2 + L2.3（可复现性门禁）。
4. L1.3 与 L3.1 + L3.2 同步推进（fixture 化是增量复用的前提）。

每层一个批次，不跨层，不把“补一个注册表条目”当成整改。
