# 测试基线可复现整改 执行交接记录 2026-10-25

## 一句话状态

系统性整改"测试基线不稳定"已推进两个独立批次。第一批（地基+门禁）已合并进 main；
第二批（内核确定性锚点+套件指纹）已推 PR 待 CI/合并。剩余最后一步是把套件指纹
对账接入 Quick 执行计划（L3.1 集成）。

## 仓库与工作树

- 仓库根：/home/lidefend/workspace/sce-backend-odoo
- 当前工作树：/home/lidefend/workspace/sce-backend-odoo-entry-validation
- 当前分支：codex/test-baseline-incremental-reuse
- 远端 origin：https://github.com/lidefend/sce-backend-odoo.git
- gh 配置：GH_CONFIG_DIR=/home/lidefend/.config/gh-new-account

## 已完成（已合并）

PR #733 已 squash 合并进 main，合并提交 4f6236aa。分支 codex/test-baseline-reproducibility。

- L1.2 台账稳定 ID：T-ASSET-{index} 改为路径哈希派生，增删资产不再整体重排。
- L1.1 独立可丢弃测试库 profile：make local.test.test MODULE=... TEST_TAGS=...，
  在 sc_test 库装 smart_construction_seed（无 demo）后跑测试。
- L2.1 确定性门禁 make verify.test.determinism。
- L2.2 隔离门禁 make verify.test.isolation。
- 两个探针已接进 ci.local.quick.run。

## 进行中（待 CI/合并）

PR #734，分支 codex/test-baseline-incremental-reuse，head a25a9fbbc（3 笔提交）：

- 47e975b77 L1.3：内核确定性锚点 test_contract_assembly_determinism.py。
- c80aeb14e L3.1 基础：quick_suite_fingerprint.py + manifest + 单测。
- a25a9fbbc 新 tag contract_assembly_determinism 登记。

CI 四项必需检查待跑；全绿后按受管入口合并。

## 下一步精确动作（剩余工作）

唯一剩余：L3.1 集成。把 quick_suite_fingerprint.py 的指纹对账接进
scripts/ops/local_quick_evidence.py 的 sharding 计划，使 Quick 只跑受影响套件
（指纹未变且 ledger 成功则 REUSE），并回写 outcome 到 .runtime/evidence-scope/。

## 关键机制事实（接手必读）

### 合并流程（GitHub PR）

- 推分支：make pr.push。
- 合并：PR=<n> EXPECTED_HEAD=<40位SHA> PR_MERGE_METHOD=squash GH_CONFIG_DIR=... make pr.merge。
- 必须用环境变量传 PR/EXPECTED_HEAD，不能用 make 命令行覆盖（否则 MAKEOVERRIDES
  被 Quick 证据权威拒绝）。
- 合并前本地 Quick 由 pr.merge.local_quick_gate 执行；有精确 head 回执则 REUSE，
  否则 fail-closed 兜底跑一次全量 Quick（约 7 分钟）。

### 四套注册表墙（每新增脚本/测试/目标都要闭合）

1. 守卫注册表 make verify.guard.registry（scripts/verify/registry.yaml）。
2. 测试覆盖注册表 make verify.test.coverage.registry（YAML + JSON 快照）。
3. 车道覆盖基线 verification_lane_baseline.json（--write-baseline）。
4. 车道 dispositions + exemptions（owner/basis/reason，reason_code 必须命中 review_policy 键）。

### local.test 可丢弃测试库

- make local.test.prepare/up/down/test MODULE=... TEST_TAGS=...
- project sc-local-test，库 sc_test，dbfilter ^sc_test$，SC_ENVIRONMENT=test
- LOCAL_TEST_MODULES ?= smart_construction_seed

## 环境注意

- .env.local.test 已生成，但 sc-local-test 容器/卷尚未实际启动（未跑过完整 local.test.test 全链路）。
- .env.local.clean 在主仓库缺失，重建 clean profile 是破坏性操作，需单独确认。

## 交接状态

- 批次验收：第一批完成；第二批（PR #734）代码完成、CI 待跑。
- 主线集成：第一批完成；第二批待合并。
- 版本发布 / 产品交付：未开始。
