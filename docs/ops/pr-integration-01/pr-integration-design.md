# PR-INTEGRATION-01 · 设计

## 目标

发布准入与合并准入形成不可跳过的闭环：发布前证明本地验证条件，合并前证明远端+本地证据共同满足。

## 准入流水线

定向测试 → Local Quick → `pr.publish.preflight` → `pr.push` → `pr.create` → GitHub CI →
`pr.merge.preflight` → 独立复审 → 合并。

## 发布前准入（pr.publish.preflight）

复用现有验证器：

- 工作树干净。
- 本地 HEAD 精确匹配候选 SHA。
- `local_quick_evidence.py verify`：Local Quick 存在、PASS、candidate SHA 正确。
- `validation_delivery_plan.py`：受影响运行时套件证据齐全、base 一致、未分类路径失败关闭。

`pr.push` 依赖该准入；`pr.create` 重新核验 PR 身份；`pr.merge` 保留原有完整检查。

## 证据分类

- Local Quick：本地工程质量证据。
- Runtime Evidence（list_surface_structure / relation_roundtrip / frontend_presentation 等）：
  真实页面/角色/环境/浏览器行为证据。

两者分别检查，不合并成笼统 PASS。

## 证据持久化

证据绑定 `candidate_sha / base_sha / input_sha256 / verified_at / worktree_identity / suite /
result / evidence_digest`，存共享证据目录；删除临时 worktree 后仍可追溯（绑定 head，不绑定目录）。

实现：共享证据根 = `git rev-parse --path-format=absolute --git-common-dir` + `codex/evidence/`。
该路径由 git 统一解析（单一权威来源），落在主仓库 `.git/` 下，所有 worktree 读写同一位置，
删除 linked worktree 不删除证据；复用仍由 candidate/base/input/digest 校验把关。

## 不适用验证

沿用现有路径分类器：文档变更静态检查；前端工具变更静态契约验证；前端运行时变更浏览器验收；
后端变更后端影响验证；混合变更取并集；未知路径失败关闭。
