# RC 候选原子流程 v1

[English](release_candidate_atomic_flow_v1.en.md)

## 目标

日常 RC 候选只需要一次人工授权和一个仓库入口：

```bash
ENV=dev make release.candidate VERSION=1.0.0-rc.5
```

入口在干净的专用发布工作区内自动完成：

1. 通过受控 `main.sync` 同步 GitHub `main`；
2. 冻结完整 commit SHA、tree、`VERSION`；
3. 验证 GitHub/Gitee `main` 一致及 required checks 全部成功；
4. 创建无 alternates、仅含 `main` 的独立 source repository，绑定完整
   commit/tree 后先执行 RH010；
5. 从该 clean source repository 构建不可变候选镜像；
6. 导出并重载镜像归档；
7. 执行 Trivy 漏洞/secret 扫描并生成 CycloneDX SBOM；
8. 生成机器可读 `release-report.json` 和简短 `release-summary.txt`。

成功报告包含：

```text
CANDIDATE_READY=true
PUBLISHED=false
DEPLOYED=false
```

`CANDIDATE_READY=true` 只表示本地不可变候选通过全部 pre-publication
门禁，不代表镜像已推送、tag 已创建、Release 已发布或生产已部署。

## 身份和失败语义

- pre-publication 扫描绑定本地不可变 image ID；不得伪造 registry digest。
- `release-report.json` 同时绑定 commit、tree、版本、工具合同摘要、归档摘要、
  重载 image ID、前端摘要、安全扫描和 SBOM。
- 每次真实运行先创建碰撞安全的 `attempt_id`，报告、阶段日志、clean source
  repository 和输出都位于
  `artifacts/release/candidates/<version>/attempts/<attempt-id>/`。
- 报告与 `latest.json` 索引均使用原子写入。`latest.json` 只是指针，不是唯一
  证据；指针更新失败不会损坏已完成 attempt。
- `retry` 总是创建新 attempt，可绑定新的源码、tree 和工具合同，并通过
  `retry_of_attempt_id` 关联旧失败；旧 attempt 的报告和日志不移动、不截断、
  不追加、不改写。
- `resume` 只恢复显式指定的同一 attempt，且 version、source SHA、tree、
  工具合同、source repository 与 workflow/schema 身份必须完全一致；不匹配
  时 fail closed 且不修改旧证据。
- 已 `CANDIDATE_READY=true` 的版本不会静默新建候选。同一版本的旧单目录失败
  证据可被只读识别为 legacy attempt，但不会原地迁移或改写。
- source repository 禁止 shared/reference clone、alternates 和调用者对象复用；
  准备、身份与 RH010 失败分阶段记录，且不以 gc/prune 修复。
- 同一版本使用非阻塞文件锁串行化；不同版本和不同 attempt 的目录互不覆盖。

## 对外影响边界

以下动作不属于 `release.candidate`，仍需独立人工确认和受控入口：

- registry push；
- 正式 git tag；
- GitHub/Gitee Release；
- provenance/attestation 发布和签名；
- 生产部署。

现有 `release.candidate.publish` 与生产部署入口不会被原子候选流程调用。
