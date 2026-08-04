#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"
repo_root="$(git rev-parse --show-toplevel)"
branch="$(git branch --show-current)"
user_home="$(getent passwd "$(id -u)" | cut -d: -f6)"
config_dir="${user_home}/.config/sce-agent-controller"
config_file="${config_dir}/controller.env"
lib_dir="${user_home}/.local/lib/sce-agent-controller"
bin_dir="${user_home}/.local/bin"
unit_dir="${user_home}/.config/systemd/user"
unit_file="${unit_dir}/sce-agent-controller.service"
bridge_unit_file="${unit_dir}/sce-agent-feishu-bridge.service"

if ! [[ "${branch}" =~ ^(feature|fix|refactor|audit|release|codex)/.+$ ]]; then
  echo "[agent-controller] denied branch=${branch}" >&2
  exit 2
fi
test "${repo_root}" = "$(pwd)"
if ! [[ "${repo_root}" =~ ^/[A-Za-z0-9._/-]+$ ]]; then
  echo "[agent-controller] repository path contains unsupported characters" >&2
  exit 2
fi

load_config() {
  test -f "${config_file}" || {
    echo "[agent-controller] missing ${config_file}" >&2
    exit 2
  }
  mode="$(stat -c '%a' "${config_file}")"
  if [[ "${mode}" != "600" && "${mode}" != "400" ]]; then
    echo "[agent-controller] config must use mode 0600 or 0400 (actual=${mode})" >&2
    exit 2
  fi
  while IFS='=' read -r key value || [ -n "${key}" ]; do
    [[ -z "${key}" || "${key}" == \#* ]] && continue
    if ! [[ "${key}" =~ ^AGENT_[A-Z0-9_]+$ ]]; then
      echo "[agent-controller] invalid config key: ${key}" >&2
      exit 2
    fi
    export "${key}=${value}"
  done < "${config_file}"
}

case "${action}" in
  install)
    test "${AGENT_CONTROLLER_INSTALL_CONFIRM:-}" = "INSTALL_LOCAL_AGENT_CONTROLLER" || {
      echo "[agent-controller] exact install confirmation is required" >&2
      exit 2
    }
    install -d -m 0700 "${config_dir}"
    install -d -m 0755 "${lib_dir}" "${unit_dir}" "${bin_dir}"
    install -m 0644 scripts/ops/agent_progress.py "${lib_dir}/agent_progress.py"
    install -m 0755 scripts/ops/codex_agent_controller.py "${lib_dir}/codex_agent_controller.py"
    install -m 0755 scripts/ops/codex_agent_watch.py "${bin_dir}/sce-agent-watch"
    codex_bin="$(command -v codex)"
    gh_bin="$(command -v gh)"
    test -x "${codex_bin}"
    test -x "${gh_bin}"
    sed "s|@@REPOSITORY_ROOT@@|${repo_root}|g" \
      deploy/agent-controller/sce-agent-controller.service.in > "${unit_file}"
    chmod 0644 "${unit_file}"
    if [ ! -f "${config_file}" ]; then
      install -m 0600 deploy/agent-controller/controller.env.example "${config_file}"
      sed -i "s|^AGENT_REPOSITORY_ROOT=.*|AGENT_REPOSITORY_ROOT=${repo_root}|" "${config_file}"
      sed -i "s|^AGENT_STATE_ROOT=.*|AGENT_STATE_ROOT=${repo_root}/.runtime/agent-controller|" "${config_file}"
      sed -i "s|^AGENT_CODEX_BIN=.*|AGENT_CODEX_BIN=${codex_bin}|" "${config_file}"
      sed -i "s|^AGENT_GH_BIN=.*|AGENT_GH_BIN=${gh_bin}|" "${config_file}"
      echo "[agent-controller] created ${config_file}; set Issue and Feishu values before enable"
    fi
    systemctl --user daemon-reload
    echo "[agent-controller] INSTALL PASS unit=${unit_file}"
    ;;
  check)
    load_config
    python3 scripts/ops/codex_agent_controller.py config-check
    ;;
  notify-test)
    load_config
    python3 scripts/ops/codex_agent_controller.py notify-test
    ;;
  enable)
    test "${AGENT_CONTROLLER_ENABLE_CONFIRM:-}" = "ENABLE_LOCAL_AGENT_CONTROLLER" || {
      echo "[agent-controller] exact enable confirmation is required" >&2
      exit 2
    }
    load_config
    python3 scripts/ops/codex_agent_controller.py config-check
    systemctl --user enable --now sce-agent-controller.service
    systemctl --user --no-pager --full status sce-agent-controller.service
    ;;
  disable)
    test "${AGENT_CONTROLLER_DISABLE_CONFIRM:-}" = "DISABLE_LOCAL_AGENT_CONTROLLER" || {
      echo "[agent-controller] exact disable confirmation is required" >&2
      exit 2
    }
    systemctl --user disable --now sce-agent-controller.service
    ;;
  linger-enable)
    test "${AGENT_CONTROLLER_LINGER_CONFIRM:-}" = "ENABLE_AGENT_CONTROLLER_LINGER" || {
      echo "[agent-controller] exact linger confirmation is required" >&2
      exit 2
    }
    loginctl enable-linger "$(id -un)"
    loginctl show-user "$(id -un)" -p Linger
    ;;
  feishu-install)
    test "${AGENT_FEISHU_BRIDGE_INSTALL_CONFIRM:-}" = "INSTALL_FEISHU_AGENT_BRIDGE" || {
      echo "[agent-controller] exact Feishu bridge install confirmation is required" >&2
      exit 2
    }
    install -d -m 0755 "${lib_dir}" "${unit_dir}"
    python3 -m venv "${lib_dir}/venv"
    "${lib_dir}/venv/bin/pip" install --disable-pip-version-check \
      -r deploy/agent-controller/requirements-feishu.txt
    install -m 0644 scripts/ops/agent_progress.py "${lib_dir}/agent_progress.py"
    install -m 0755 scripts/ops/feishu_agent_bridge.py "${lib_dir}/feishu_agent_bridge.py"
    sed -e "s|@@REPOSITORY_ROOT@@|${repo_root}|g" \
      -e "s|@@PYTHON_BIN@@|${lib_dir}/venv/bin/python|g" \
      deploy/agent-controller/sce-agent-feishu-bridge.service.in > "${bridge_unit_file}"
    chmod 0644 "${bridge_unit_file}"
    systemctl --user daemon-reload
    echo "[agent-controller] FEISHU BRIDGE INSTALL PASS unit=${bridge_unit_file}"
    ;;
  feishu-check)
    load_config
    "${lib_dir}/venv/bin/python" scripts/ops/feishu_agent_bridge.py config-check
    ;;
  feishu-enable)
    test "${AGENT_FEISHU_BRIDGE_ENABLE_CONFIRM:-}" = "ENABLE_FEISHU_AGENT_BRIDGE" || {
      echo "[agent-controller] exact Feishu bridge enable confirmation is required" >&2
      exit 2
    }
    load_config
    "${lib_dir}/venv/bin/python" scripts/ops/feishu_agent_bridge.py config-check
    systemctl --user enable --now sce-agent-feishu-bridge.service
    systemctl --user --no-pager --full status sce-agent-feishu-bridge.service
    ;;
  feishu-disable)
    test "${AGENT_FEISHU_BRIDGE_DISABLE_CONFIRM:-}" = "DISABLE_FEISHU_AGENT_BRIDGE" || {
      echo "[agent-controller] exact Feishu bridge disable confirmation is required" >&2
      exit 2
    }
    systemctl --user disable --now sce-agent-feishu-bridge.service
    ;;
  feishu-status)
    systemctl --user --no-pager --full status sce-agent-feishu-bridge.service
    ;;
  feishu-logs)
    journalctl --user -u sce-agent-feishu-bridge.service -n 120 --no-pager
    ;;
  status)
    systemctl --user --no-pager --full status sce-agent-controller.service
    ;;
  logs)
    journalctl --user -u sce-agent-controller.service -n 120 --no-pager
    ;;
  *)
    echo "usage: $0 install|check|notify-test|enable|disable|linger-enable|status|logs|feishu-install|feishu-check|feishu-enable|feishu-disable|feishu-status|feishu-logs" >&2
    exit 2
    ;;
esac
