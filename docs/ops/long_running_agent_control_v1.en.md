# Long-running Codex Collaboration Controller v1

[中文](long_running_agent_control_v1.md)

## Goal

The controller lets the repository owner dispatch long-running work from a
dedicated GitHub Issue on GitHub Mobile and receive start, failure, decision,
completion, and security-rejection notifications in Feishu. GitHub is the only
two-way command and audit channel. The Feishu custom bot is outbound-only.

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

The service user must already pass `gh auth status` and have a valid Codex
login. Never place the configuration or webhook in Git, an Issue, a PR, or logs.

## Operations

```bash
make agent.controller.status
make agent.controller.logs
make agent.controller.disable \
  AGENT_CONTROLLER_DISABLE_CONFIRM=DISABLE_LOCAL_AGENT_CONTROLLER
```

State and evidence are stored under `.runtime/agent-controller/`. On first
startup, existing Issue comments become the history cursor and are not
executed. Send the first `/agent start` only after the ready notification.

## Feishu basis

The implementation follows the official `bot/v2/hook` custom-bot endpoint,
UTF-8 JSON, and optional HMAC-SHA256 signature flow. A custom bot only sends
group notifications and is intentionally not a two-way command channel here.
