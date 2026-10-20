# Demo 迭代线 Batch 1（基线就绪 manifest + verifier，2026-10-20）

## 0. 身份与边界

- 分支：`feature/demo-iteration-line-20261020`
- 基线：`13b0395db4da63147b3f9c311a4bb5d060dc6a4e`（HEAD 已含 Batch 0 与两项基线遗留前置收口）
- Formal Product Layer：P4（demo delivery tooling）
- Layer Target：`scripts/verify`、`make/dev_test.mk`、`docs/demo`
- Module：`smart_construction_demo`（只读消费）、`scripts/verify`、`docs/demo`
- Standard vs User-Specific：demo_delivery_tool
- Why Here：就绪判定是 P4 交付工具；manifest 是交付清单，不承载产品语义。
- Why Not Elsewhere：产品规则与守卫归 P0/P1/P3；verifier 只按声明的 hard/conditional
  与 presence 事实分类 ready/partial/blocked/not_applicable，不回写业务规则。
- Blast Radius：仅新增只读 verifier/manifest/单测与一个离线 Make 目标；不改数据库、
  服务、产品代码或前端。

## 1. 变更

- 新增 `scripts/verify/baseline_readiness_manifest.json`：G0–G6 就绪清单，每项声明
  `key` / `kind`（hard|conditional）/ `authority` / `owner_layer` / `repair_hint`。
- 新增 `scripts/verify/baseline_readiness_verifier.py`：只读评估
  `ready` / `partial` / `blocked` / `not_applicable`；缺声明或未观察键 fail-closed。
- 新增 `scripts/verify/test_baseline_readiness_verifier.py`：10 个离线单测，覆盖
  ready/partial/blocked/not_applicable 与非法输入、重复键。
- 新增 Make 目标 `verify.demo.baseline_readiness.unit`（`make/dev_test.mk`）。
- 更新 `docs/demo/demo_baseline_readiness_v1.md`、`docs/demo/demo_iteration_line_v1.md` 下一步。

## 2. 验证

- `python3 -m unittest scripts/verify/test_baseline_readiness_verifier.py`：10 tests OK（非零）。
- 收口前重跑：`make verify.demo.baseline_readiness.unit`、`make verify.docs.all`、
  `make verify.agent.ledger.unit`、`make ci.local.iteration`。

## 3. 风险与回滚

- 风险：manifest 的 hard/conditional 分类若与产品实际守卫不符，会误导就绪结论；
  `authority` 字段指向产品层，Batch 2 接入真实种子回读时须以回读为准。
- 回滚：删除 verifier/manifest/test 三文件，撤销 `make/dev_test.mk` target 与文档改动。

## 4. 下一批

Batch 2：基础数据补齐，使 G0–G4 对目标公司/项目 `missing=[]`；用本 verifier 消费
demo 种子回读产出 ready/partial/blocked 观测。
