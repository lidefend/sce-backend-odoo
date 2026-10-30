# PR-INTEGRATION-01 · 端到端发布演练验收

结论：共享 Quick 回执已真实跨越本地 Quick、发布预检、受管推送、PR 创建、GitHub CI 与合并预检
六个阶段，身份链一致，演练成功。

## 身份链

local HEAD = Quick receipt candidate = remote branch SHA = PR HEAD = `9b04f88d...`；base `1640a7e1b...`。

## 六阶段结果

| 阶段 | 结果 |
| --- | --- |
| Local Quick | PASS，回执写入共享公共 git 目录 |
| publish.preflight | PASS，回读并 VERIFIED 共享 Quick 回执，无 runtime blocker |
| managed push | PASS，远端 SHA 回读一致 |
| managed create | PASS，PR #782 创建，HEAD 回读一致 |
| GitHub CI | PASS（professional_quality/gate、merge_policy_gate、public_guard、backend 全套件等全绿） |
| merge.preflight | PASS（`ready_for_existing_gates`，共享证据再次复用） |

## 治理修复清单（演练期间暴露并修复）

- 测试清单 CSV / summary 同步。
- 复杂度报告、split plan queue 同步。
- `scripts/verify/registry.yaml` 登记新增测试脚本。
- `pr.publish.preflight` recipe 续行修复。
- 分类器精确路径：`scripts/ops/local_quick_evidence.py` → `governance_static`（不扩大目录豁免）。

## 测试 PR

PR #782 已通过受管流程关闭，未合并、未部署。
