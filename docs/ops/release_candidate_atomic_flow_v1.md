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
4. 构建不可变候选镜像；
5. 导出并重载镜像归档；
6. 执行 Trivy 漏洞/secret 扫描并生成 CycloneDX SBOM；
7. 生成机器可读 `release-report.json` 和简短 `release-summary.txt`。

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
- 报告使用原子写入；失败时记录 `failed_stage`、退出码、错误和对应日志路径；
  重试前会把上一份失败报告归档到 `failures/`，不会覆盖事故证据。
- 相同版本、源码、tree 和工具合同重试时，已验证的构建产物才会被复用；
  扫描失败不会强制重建镜像。任一身份或工具合同变化均 fail closed。
- 相同版本若对应不同源码，流程 fail closed，不覆盖既有候选证据。
- 同一版本使用非阻塞文件锁串行化；并发调用立即失败，不会共享或覆盖候选目录。

## 对外影响边界

以下动作不属于 `release.candidate`，仍需独立人工确认和受控入口：

- registry push；
- 正式 git tag；
- GitHub/Gitee Release；
- provenance/attestation 发布和签名；
- 生产部署。

现有 `release.candidate.publish` 与生产部署入口不会被原子候选流程调用。
