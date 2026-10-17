#!/usr/bin/env bash
set -euo pipefail
umask 077
source_dir="$(cd "$(dirname "$0")" && pwd)"
dispatch_root="${SCE_DISPATCH_ROOT:-$HOME/workspace/.sce-dispatch}"
unit_dir="$HOME/.config/systemd/user"
[[ "$dispatch_root" = "$HOME/workspace/.sce-dispatch" ]] || { echo 'Only the registered private inbox root is supported'; exit 2; }
[[ -f "$dispatch_root/config.json" ]] || { echo 'Initialize the inbox before installing'; exit 2; }
[[ ! -L "$dispatch_root" ]] || exit 2
mkdir -p "$dispatch_root/lib" "$unit_dir"
install -m 600 "$source_dir/agent_dispatch_inbox.py" "$dispatch_root/lib/agent_dispatch_inbox.py"
install -m 600 "$source_dir/../../docs/ops/agent_dispatch_inbox.md" "$dispatch_root/README.md"
cat > "$unit_dir/sce-dispatch-review.service" <<EOF
[Unit]
Description=SCE private receipt review (proposal only)
[Service]
Type=oneshot
UMask=0077
Environment="PATH=$PATH"
ExecStart=/usr/bin/python3 $dispatch_root/lib/agent_dispatch_inbox.py --root $dispatch_root review-once
TimeoutStartSec=300
KillMode=control-group
NoNewPrivileges=true
EOF
cat > "$unit_dir/sce-dispatch-review.timer" <<'EOF'
[Unit]
Description=Check SCE executor receipts every 30 seconds
[Timer]
OnStartupSec=10
OnUnitInactiveSec=30
Unit=sce-dispatch-review.service
[Install]
WantedBy=timers.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now sce-dispatch-review.timer
systemctl --user is-active sce-dispatch-review.timer
