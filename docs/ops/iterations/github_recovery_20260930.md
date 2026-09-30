# GitHub 恢复集成 — 2026-09-30

唯一进度索引：`.agent/runs/GITHUB-RECOVERY/run.json`，原始日志 `.runtime/github-recovery/`。

## 身份与范围

GitHub main `de9a230d3faab18dd60a219f445f932a8af9d7f5`；Gitee main `23f11f426880585ca307544545c9bf9c01245b42`。
祖先核验 0/199 无分叉。当前历史恢复工作树 `sce-backend-odoo-agent-resume-github-recovery`，分支 `fix/github-history-recovery`。
P4 候选 `44429fd706c065aa0660c4cd87c91c5fba162f1e` 已完成并冻结只读，指纹 `025366d4f1df6d13e8db43c7675942f6a46fab9a1a428e0351c3644f7d7f5b10`；不清理或改写。
原产品工作树另有后续文档提交 `382d37e35`，恢复批次不修改它。同一时间保持一个产品写入工作树和一个恢复工作树。

Formal Product Layer=P4；Layer Target=远端仓库集成；Module=已有 Git/Make/PR 流程；
Standard vs User-Specific=通用交付操作；Why Here=历史与远端身份治理；Why Not Elsewhere=不改变产品契约、业务数据或运行时权限。
Blast Radius=GitHub 候选分支与受保护 PR。先集成已进入 Gitee 的历史，再接官方接管与 P4 候选，不将后续 187 个提交混入历史补齐。

GitHub ruleset `19364379` active，零 bypass；保留 public_guard/merge_policy_gate/professional_quality_gate/frontend_release_gate，strict base 与 PR 强制开启。
GitHub/Gitee 访问与认证正常；现有 PR #522 单独保留，待按提交关系判断是否已被历史覆盖，不自动关闭。

## 验证顺序

L0 轻量身份；L1 iteration、生成证据只读检查；L2 历史责任测试复用与新增恢复工具定向测试（如需工具修复）；
先解决便宜层阻断，再 prepare/freeze/一次 exact-head Quick、独立与公开范围复核，最后受保护 PR 的四项远端检查。
不执行数据库升级、fixture、浏览器旅程或部署；本批为仓库恢复，运行验收证据不被重新包装为当前通过。
原历史基线尚无新 P4 的 agent.run 工具，因此此阶段使用既有 goal/run 记录；不为恢复历史提前混入未集成的后续产品代码。

## 状态

历史恢复：验证中。后续官方接管与 P4：pending。回滚：尚未远端写入；发布后保留分支和原始历史，通过受保护回退 PR 处理，不强推。


## 前置检查与恢复

- `make ci.local.iteration` 通过；旧基线工具仍按 origin/main 给出 286 路径建议，仅作本次历史范围观察，不重复按模型验收。
- `make verify.pr.push.unit verify.codex.agent_controller` 通过（15+36）；无实际远端写入。
- 生成报告 8 项全部 current。组件清单首次因新工作树无依赖失败，执行受管 `make fe.install.cached`，639 包来自既有缓存、0 下载、frozen-lockfile/ignore-scripts，锁文件不变；恢复后组件 7 项通过。
- 历史表单拆分文档仍记 1901 行，实际为 1918；`make refresh.contract_form_split_evidence` 只更新两处数字并通过，不改产品源码、不变更复杂度限制。
- 公开扫描使用 `--scope all --auto-trusted-base`，无可信主线回执时走 full；实现包含 `git rev-list --objects --all` 的历史 blob，不仅 HEAD 树。覆盖范围大于本次 199 提交。
- 镜像主机只读回读：timer inactive/disabled；service failed/static、MainPID=0。未启停服务。
- 独立历史复核已确认拓扑、workflow、保护规则无新增阻断；正式放行仍待公开扫描完成、冻结 Quick 与新 PR 的当前源/目标检查。

- 公开扫描已通过：secret=0、personal=0，21 项已登记精确 blob 误报；覆盖所有可达 refs 的历史对象，包括本次新增历史。
- `ci.delivery.freeze.prepare` 通过；审阅差异只有原拆分文档两处行数修正及本批 3 个记录文件。
- 复杂度基线 11 项、契约结构 14 域和 page-v1 零残留守卫通过。
- 公开扫描后新增内容仅本批状态说明、路径/SHA 与行数；产品源码、扫描工具、历史 blob 均未变化。原历史扫描证据保留；后续远端仍对新 SHA 执行必需检查。

- `make verify.frontend.typecheck.strict` 通过（完整 vue-tsc + strict 配置）。冻结后 Quick、PR 与 CI 尚待执行，回执留既有运行目录，不伪造已完成状态。
