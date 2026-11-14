#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo: sudo ./install.sh" >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${AUTOHEALX_INSTALL_DIR:-/opt/autohealx}"
SERVICE_NAME="autohealx-agent"

command -v python3 >/dev/null || { echo "python3 is required." >&2; exit 1; }
command -v bash >/dev/null || { echo "bash is required." >&2; exit 1; }
mkdir -p "$INSTALL_DIR"
install -m 0755 "$SCRIPT_DIR/agent.py" "$INSTALL_DIR/agent.py"
install -m 0755 "$SCRIPT_DIR/monitor.sh" "$INSTALL_DIR/monitor.sh"
if [[ ! -f "$INSTALL_DIR/config.json" ]]; then
  install -m 0600 "$SCRIPT_DIR/config.json" "$INSTALL_DIR/config.json"
else
  echo "Keeping existing $INSTALL_DIR/config.json"
fi

cat >"/etc/systemd/system/${SERVICE_NAME}.service" <<UNIT
[Unit]
Description=AutoHealX Linux Monitoring Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/agent.py
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
ProtectHome=true
PrivateTmp=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
echo "Installed. Edit $INSTALL_DIR/config.json, then run:"
echo "  sudo systemctl restart $SERVICE_NAME"
