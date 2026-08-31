# GitHub 权威仓库到 Gitee 只读镜像

## 固定边界

- GitHub `lidefend/sce-backend-odoo` 是唯一开发、PR、Checks 和 `main` 合并入口。
- Gitee `leegege/sce-product-odoo` 只接收 GitHub `main` 的普通快进镜像。
- GitHub `main` 必须由 active ruleset 保护：必须 PR、`merge_policy_gate`
  分支保护检查、线程解决、禁止删除和非快进，并且没有 bypass actor。
- Gitee→GitHub 的 write Deploy Key、反向镜像和独立 Gitee `main` 合并均被禁止。
- 日常镜像禁止 force push、force-with-lease、删除 `main` 或从 Gitee 反向覆盖
  GitHub。唯一例外是仓库所有者逐次明确授权的历史治理切换，且只能通过
  `make main.cutover.controlled` 使用完整 SHA 精确 lease、仓库外恢复 bundle、
  双远端配对回退和保护规则恢复执行；该例外不授权生产部署。
- 发布裁决前可通过 `make candidate.mirror.gitee` 将 GitHub 已存在的合规候选
  普通快进到 Gitee 同名候选分支，用于双远端 SHA 取证；它不能写入 `main`，
  也不能形成第二开发入口。
- 迁移注记（2026-08-31）：当前制度下，`merge_policy_gate` 负责 GitHub `main`
  的合并资格；`release_candidate_gate` 负责 exact-head 候选发布资格。

## 凭据隔离

```text
GitHub PR + `merge_policy_gate` + review/thread gates
        ↓ 正常合并
GitHub main（唯一权威历史）
        ↓ 精确 SHA + fast-forward only
Gitee main（只读镜像与国内服务器拉取源）
```

镜像同步失败不得阻止 GitHub 的正常治理，但必须报警。同步任务不得持有
GitHub `main` 写凭据，也不得把 Gitee 的任何提交反向写入 GitHub。

## 安装与验证

合并后镜像同步必须先验证 Gitee `main` 是 GitHub `main` 的祖先，再通过受控
Make 入口执行：

```bash
make mirror.main.gitee
```

若祖先检查失败，必须输出 `GITEE_MIRROR_DIVERGED` 并停止；不得 merge、rebase、
cherry-pick 或 force push。国内服务器可从 Gitee 拉取，但部署前必须核对该 SHA
已存在于 GitHub `main`，且部署仍需要独立授权。
