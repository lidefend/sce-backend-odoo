# RC 发布事务合同 v1

[English](release_publication_transaction_v1.en.md)

## 目标

已通过 `release.candidate` 的候选只能通过以下受控入口发布：

```bash
ENV=dev make release.publish \
  VERSION=1.0.0-rc.5 \
  CANDIDATE_ATTEMPT_ID=<candidate-attempt-id> \
  EXPECTED_SOURCE_SHA=<candidate-full-40-char-sha> \
  EXPECTED_PUBLICATION_TOOL_SHA=<current-main-full-40-char-sha> \
  EXPECTED_LIVE_MAIN_SHA=<current-main-full-40-char-sha>
```

该命令具有 registry、GitHub/Gitee tag 和 GitHub Release 外部写入，必须先取得
一次明确的对外发布授权。它不会部署生产。

## 证据边界

- 候选 attempt 的 report、manifest、archive、SBOM、日志和摘要永不修改。
- 发布使用独立的
  `artifacts/release/candidates/<version>/publications/<publication-attempt-id>/`。
- `publication-plan.json` 冻结候选创建时的双远端/checks、候选报告、manifest、
  archive、SBOM、镜像内容、candidate source SHA/tree、当前发布工具
  SHA/tree/合同、预期实时 main 及全部外部目标。
- `publication-report.json` 原子记录状态变化和已验证的远端身份。
- `publications/latest.json` 只是原子索引，不是唯一发布证据。

旧的 `immutable_candidate_publish.sh` 已拒绝直接执行；
`release.candidate.publish` 仅兼容转发到上述新合同。

## 预检与执行顺序

任何外部写入前必须一次性通过：

1. candidate ready 与全部固定哈希；
2. 候选创建时 GitHub/Gitee main 均等于 candidate source，且 required checks
   证据仍为成功；
3. 发布时 GitHub/Gitee main SHA/tree 相同、精确等于
   `EXPECTED_LIVE_MAIN_SHA`，并且 candidate source 位于其 first-parent 历史；
4. 发布工具工作树干净，其 HEAD/tree 精确等于实时 main，工具合同摘要匹配；
5. 本地镜像内容身份；
6. registry version/source tag 不存在；
7. GitHub/Gitee Git tag 不存在；
8. GitHub Release 不存在；
9. 同版本发布锁和路径安全。

发布工具合并导致 `main` 前进不会改写或废弃已冻结候选。tag、镜像 digest、
Release、archive 和 SBOM 始终绑定 candidate source；当前 main 只用于证明发布工具
身份、双远端一致性和 candidate 的受控祖先关系。

随后依次执行：

1. 推送两个镜像 tag，读取并比对 registry digest，再按 digest 拉取并验证 image ID；
2. 创建同一受控 annotated tag 并推送 GitHub/Gitee，读取 peeled commit 验证；
3. 创建 GitHub prerelease，重新读取并验证 tag、source、publication attempt 和 digest；
4. 所有远端身份一致后才写入 `PUBLICATION_COMPLETE=true`。

## 恢复和幂等

registry、Git tag 和 Release 不构成全局原子事务。失败不会自动删除或移动任何
远端对象。恢复必须显式指定原 publication attempt：

```bash
ENV=dev make release.publish \
  VERSION=<version> \
  CANDIDATE_ATTEMPT_ID=<candidate-attempt-id> \
  EXPECTED_SOURCE_SHA=<candidate-sha> \
  EXPECTED_PUBLICATION_TOOL_SHA=<tool-sha> \
  EXPECTED_LIVE_MAIN_SHA=<live-main-sha> \
  PUBLICATION_ATTEMPT_ID=<publication-attempt-id>
```

恢复前会重新核对全部固定身份。已完成阶段先从远端验证，匹配时跳过写入；冲突时
fail closed。完成的同版本重复调用不会重复发布。

## 外部边界

该入口不执行生产部署、不连接生产数据库、不删除分支，也不通过删除 tag 或镜像
进行自动回滚。生产部署仍需要单独明确授权。
