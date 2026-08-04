# Long-running Codex Collaboration Controller v1

[中文](long_running_agent_control_v1.md)

## Goal

The controller lets the repository owner dispatch long-running work from GitHub
or a bound Feishu app bot and receive start, periodic progress, stalled-task,
failure, decision, completion, and security-rejection notifications in Feishu.
GitHub remains the audit channel.
The custom bot sends notifications while the enterprise app bot receives strict
commands over the official SDK WebSocket.

## Architecture and boundaries

- Formal Product Layer: P4 operations delivery tooling.
- Layer Target: local autonomous task control and notification orchestration.
- Affected modules: `scripts/ops`, `deploy/agent-controller`, and `make/codex.mk`.
- Platform, industry, customer modules, and business APIs remain unchanged.
- Only strict `/agent` commands from the configured GitHub login are accepted.
- Issue text is never evaluated as a shell command.
- A file lease limits each repository to one worker.
- Workers use `workspace-write` and `approval_policy=never`; decisions are
  returned as structured terminal results instead of expanding permissions.
- Automated deployment only supports `daily <full SHA>`. No production command
  exists.

The controller uses Codex non-interactive JSONL events, structured output, and
session-id resume checkpoints. Background operation does not widen the sandbox
or repository authorization boundaries.

## GitHub commands

Use these commands in the dedicated control Issue:

```text
/agent start
<outcome, constraints, and acceptance criteria>

/agent status
/agent continue <additional context>
/agent approve decision-YYYYMMDD-NNN <choice>
/agent reject decision-YYYYMMDD-NNN <reason>
/agent deploy daily <full 40-character main SHA>
/agent stop
```

`/agent stop` sends SIGINT for a safe stop and never escalates automatically to
SIGKILL.

## Direct Feishu commands

After binding the local user and conversation, use the enterprise app-bot chat:

```text
状态
进度
开始 <outcome, constraints, and acceptance criteria>
继续 <additional context>
批准 decision-YYYYMMDD-NNN <choice>
拒绝 decision-YYYYMMDD-NNN <reason>
停止
部署日常 <full 40-character SHA>
```

`状态` and `进度` are immediate local read-only queries. They return elapsed
time, event counts, recent activity, the latest stage, and decision state without
creating a GitHub comment. Commands that change task state still submit the
equivalent strict `/agent` command to the GitHub control Issue through a governed
Make target. GitHub identity, controller parsing, and the single-worker lease
remain a second authorization boundary.

## One-time setup

1. Create the dedicated GitHub Issue through the governed entry point and record its number:

```bash
make agent.controller.issue.create \
  AGENT_CONTROLLER_GITHUB_REPOSITORY=lidefend/sce-backend-odoo \
  AGENT_CONTROLLER_ISSUE_CREATE_CONFIRM=CREATE_AGENT_CONTROL_ISSUE
```

2. Add a Feishu custom bot to a group, enable signature verification, and save
   its webhook and signing secret.
3. Install the user service:

```bash
make agent.controller.install \
  AGENT_CONTROLLER_INSTALL_CONFIRM=INSTALL_LOCAL_AGENT_CONTROLLER
```

4. Edit the mode-`0600` file
   `~/.config/sce-agent-controller/controller.env` and set the control Issue,
   trusted sender, webhook, and signing secret.

By default, the first progress heartbeat is sent after 120 seconds, subsequent
heartbeats every 300 seconds, and a stalled-task alert after 600 seconds without
new events. Override these values with `AGENT_PROGRESS_INITIAL_SECONDS`,
`AGENT_PROGRESS_INTERVAL_SECONDS`, and `AGENT_PROGRESS_STALE_SECONDS`.
5. Validate and enable:

```bash
make agent.controller.config.check
make agent.controller.notify.test
make agent.controller.enable \
  AGENT_CONTROLLER_ENABLE_CONFIRM=ENABLE_LOCAL_AGENT_CONTROLLER
```

To keep the user service alive after the local login session ends, explicitly
enable systemd linger for that user:

```bash
make agent.controller.linger.enable \
  AGENT_CONTROLLER_LINGER_CONFIRM=ENABLE_AGENT_CONTROLLER_LINGER
```

Install and enable the Feishu enterprise app-bot bridge:

```bash
make agent.feishu_bridge.install \
  AGENT_FEISHU_BRIDGE_INSTALL_CONFIRM=INSTALL_FEISHU_AGENT_BRIDGE
make agent.feishu_bridge.config.check
make agent.feishu_bridge.enable \
  AGENT_FEISHU_BRIDGE_ENABLE_CONFIRM=ENABLE_FEISHU_AGENT_BRIDGE
```

The service user must already pass `gh auth status` and have a valid Codex
login. Never place the configuration or webhook in Git, an Issue, a PR, or logs.

## Operations

```bash
make agent.controller.status
make agent.controller.logs
make agent.controller.watch
make agent.controller.disable \
  AGENT_CONTROLLER_DISABLE_CONFIRM=DISABLE_LOCAL_AGENT_CONTROLLER
```

`make agent.controller.watch` refreshes a local read-only console every two
seconds. Installed environments can also run `sce-agent-watch`. `Ctrl+C` exits
the viewer without stopping the task.

State and evidence are stored under `.runtime/agent-controller/`. On first
startup, existing Issue comments become the history cursor and are not
executed. Send the first `/agent start` only after the ready notification.

## Feishu basis

The implementation follows the official `bot/v2/hook` custom-bot endpoint for
signed UTF-8 notifications and the official SDK WebSocket for enterprise
app-bot message events. The custom bot remains outbound-only; the app bot is
the bound command channel.
