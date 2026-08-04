#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"
repo_root="$(git rev-parse --show-toplevel)"
branch="$(git branch --show-current)"
user_home="$(getent passwd "$(id -u)" | cut -d: -f6)"
config_dir="${user_home}/.config/sce-agent-controller"
config_file="${config_dir}/controller.env"
lib_dir="${user_home}/.local/lib/sce-agent-controller"
unit_dir="${user_home}/.config/systemd/user"
unit_file="${unit_dir}/sce-agent-controller.service"

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
    install -d -m 0755 "${lib_dir}" "${unit_dir}"
    install -m 0755 scripts/ops/codex_agent_controller.py "${lib_dir}/codex_agent_controller.py"
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
  status)
    systemctl --user --no-pager --full status sce-agent-controller.service
    ;;
  logs)
    journalctl --user -u sce-agent-controller.service -n 120 --no-pager
    ;;
  *)
    echo "usage: $0 install|check|notify-test|enable|disable|linger-enable|status|logs" >&2
    exit 2
    ;;
esac
