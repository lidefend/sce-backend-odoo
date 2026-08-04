# 长期 Codex 协作控制器 v1

[English](long_running_agent_control_v1.en.md)

## 目标

本控制器让仓库所有者通过 GitHub 或已绑定的飞书应用机器人调度长期任务，
并通过飞书及时接收开始、失败、决策、完成和安全拒绝通知。GitHub 保留审计入口；
飞书自定义机器人发送通知，企业自建应用机器人通过官方 SDK 长连接接收严格命令。

## 架构与边界

- Formal Product Layer：P4 运维交付工具。
- Layer Target：本地自治任务控制与通知编排。
- Affected Module：`scripts/ops`、`deploy/agent-controller`、`make/codex.mk`。
- 不修改平台、行业、客户模块或业务接口。
- 控制器只接受配置的 GitHub 登录名发布的严格 `/agent` 命令。
- 评论内容永远不会作为 shell 命令执行。
- 每个仓库同时只运行一个 worker，并由文件锁保护。
- worker 使用 `workspace-write` 与 `approval_policy=never`；决策通过结构化结果退出，
  而不是扩大权限。
- 自动部署只支持 `daily <完整 SHA>`，生产部署没有命令入口。

Codex 官方非交互模式支持 JSONL 事件、结构化输出以及按 session id 恢复，控制器
据此保存 checkpoint。长期运行仍保留原有 sandbox 和仓库规则，不因后台执行扩大授权。

## GitHub 命令

在专用控制 Issue 中使用：

```text
/agent start
<目标、约束和验收标准>

/agent status
/agent continue <补充说明>
/agent approve decision-YYYYMMDD-NNN <选择>
/agent reject decision-YYYYMMDD-NNN <原因>
/agent deploy daily <完整 40 位 main SHA>
/agent stop
```

`/agent stop` 只发送 SIGINT 请求安全停止，不会自动升级成 SIGKILL。

## 飞书直接命令

在完成本机用户与会话绑定后，可在应用机器人单聊中使用：

```text
状态
开始 <任务目标、约束和验收标准>
继续 <补充说明>
批准 decision-YYYYMMDD-NNN <选择>
拒绝 decision-YYYYMMDD-NNN <原因>
停止
部署日常 <完整 40 位 SHA>
```

桥接服务不直接执行消息，而是通过受控 Make 入口将等价 `/agent` 命令写入 GitHub
Issue。GitHub 登录名、控制器命令解析和单 worker 租约继续构成第二层授权边界。

## 一次性配置

1. 通过受控入口创建专用 GitHub Issue，并记录输出的 Issue 编号：

```bash
make agent.controller.issue.create \
  AGENT_CONTROLLER_GITHUB_REPOSITORY=lidefend/sce-backend-odoo \
  AGENT_CONTROLLER_ISSUE_CREATE_CONFIRM=CREATE_AGENT_CONTROL_ISSUE
```

2. 在飞书群中添加自定义机器人，启用签名校验，保存 webhook 和签名密钥。
3. 安装本地用户服务：

```bash
make agent.controller.install \
  AGENT_CONTROLLER_INSTALL_CONFIRM=INSTALL_LOCAL_AGENT_CONTROLLER
```

4. 编辑权限为 `0600` 的配置文件：

```text
~/.config/sce-agent-controller/controller.env
```

必须填写：

- `AGENT_GITHUB_CONTROL_ISSUE`
- `AGENT_GITHUB_ALLOWED_SENDER`
- `AGENT_FEISHU_WEBHOOK_URL`
- `AGENT_FEISHU_WEBHOOK_SECRET`

5. 依次验证并启动：

```bash
make agent.controller.config.check
make agent.controller.notify.test
make agent.controller.enable \
  AGENT_CONTROLLER_ENABLE_CONFIRM=ENABLE_LOCAL_AGENT_CONTROLLER
```

若需要退出本地登录会话后仍持续运行，再显式启用该用户的 systemd linger：

```bash
make agent.controller.linger.enable \
  AGENT_CONTROLLER_LINGER_CONFIRM=ENABLE_AGENT_CONTROLLER_LINGER
```

安装并启用飞书应用机器人桥接服务：

```bash
make agent.feishu_bridge.install \
  AGENT_FEISHU_BRIDGE_INSTALL_CONFIRM=INSTALL_FEISHU_AGENT_BRIDGE
make agent.feishu_bridge.config.check
make agent.feishu_bridge.enable \
  AGENT_FEISHU_BRIDGE_ENABLE_CONFIRM=ENABLE_FEISHU_AGENT_BRIDGE
```

运行用户必须已经完成 `gh auth status` 和 `codex login`。配置文件及 webhook 禁止
提交到仓库、Issue、PR 或日志。

## 运维

```bash
make agent.controller.status
make agent.controller.logs
make agent.controller.disable \
  AGENT_CONTROLLER_DISABLE_CONFIRM=DISABLE_LOCAL_AGENT_CONTROLLER
```

状态和证据位于：

```text
.runtime/agent-controller/state.json
.runtime/agent-controller/events.jsonl
.runtime/agent-controller/runs/<task-id>/
```

控制器首次启动会把当前 Issue 评论作为历史游标，不会执行旧命令。启动完成后再发送
第一条 `/agent start`。

## 飞书依据

实现采用飞书官方自定义机器人 `bot/v2/hook`、UTF-8 JSON 和可选 HMAC-SHA256
签名。自定义机器人只具备群通知能力，不能作为本版本的双向命令入口。
