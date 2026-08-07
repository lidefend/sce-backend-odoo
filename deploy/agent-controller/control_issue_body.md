# Codex 长期任务控制台

本 Issue 是本仓库长期 Codex 控制器的唯一双向命令与审计入口。飞书只负责发送通知。

仅允许仓库配置中指定的 GitHub 用户发送以下命令：

```text
/agent start
<目标、约束和验收标准>

/agent status
/agent continue <补充说明>
/agent approve decision-YYYYMMDD-NNN <选择>
/agent reject decision-YYYYMMDD-NNN <原因>
/agent deploy daily <合规来源分支> <完整 40 位候选 SHA>
/agent stop
```

安全边界：

- 评论不会作为 shell 命令执行。
- 日常开发部署必须指定完整提交 SHA；专题分支候选可在合并 main 前部署验收。
- 不支持生产部署、审批、删除或其他不可逆业务操作。
- 凭据、token、webhook 和业务敏感数据禁止写入本 Issue。

详细运维说明见 `docs/ops/long_running_agent_control_v1.md`。
