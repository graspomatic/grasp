#!/usr/bin/env bash
set -euo pipefail

# Figure out which user’s Python site-packages to modify
TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
USER_SITE="$(sudo -u "$TARGET_USER" python3 -m site --user-site)"

# Write grasp.pth into that user’s site-packages
sudo -u "$TARGET_USER" mkdir -p "$USER_SITE"
{
  echo "$TARGET_HOME/grasp/Dynamixel2Control"
  echo "$TARGET_HOME/grasp/AppliedMotionControl"
  echo "$TARGET_HOME/grasp/GPIOD"
  echo "$TARGET_HOME/grasp/controller"
} | sudo -u "$TARGET_USER" tee "$USER_SITE/grasp.pth" >/dev/null

# Install init script
sudo cp startup.sh /etc/init.d/startup.sh
sudo chmod +x /etc/init.d/startup.sh
sudo update-rc.d startup.sh defaults

# Ensure redis config dir exists and copy config with correct perms
sudo install -d -m 755 -o root -g redis /etc/redis
sudo install -o redis -g redis -m 644 ./redis_conf_files/redis_6380.conf /etc/redis/redis_6380.conf

# Ensure data dir exists with redis ownership
sudo install -d -m 770 -o redis -g redis /var/lib/redis/6380

# Stop existing 6380 instance if present (ignore failure)
redis-cli -p 6380 shutdown || true

# Seed AOF backup if available
if [ -f ./redis_conf_files/redis-6380-backup/appendonly6380.aof ]; then
  sudo install -o redis -g redis -m 644 ./redis_conf_files/redis-6380-backup/appendonly6380.aof /var/lib/redis/6380/appendonly6380.aof
fi

# Start redis on 6380 with the provided config
sudo /usr/bin/redis-server /etc/redis/redis_6380.conf

# Make shared dir
sudo mkdir -p /shared/lab

sudo apt install webdis

set -euo pipefail

# ---- CONFIG: change if paths differ ----
APP_USER="${APP_USER:-lab}"
HOME_DIR="/home/${APP_USER}"

VENV_DIR="${VENV_DIR:-${HOME_DIR}/grasp/grasp2}"
PY_APP="${PY_APP:-${HOME_DIR}/grasp/grasp_server.py}"
PY_WORKDIR="${PY_WORKDIR:-${HOME_DIR}/grasp}"

NODE_DIR="${NODE_DIR:-${HOME_DIR}/grasp/node-web-server}"
NODE_ENTRY="${NODE_ENTRY:-server.js}"

SENSOR_BIN="${SENSOR_BIN:-${HOME_DIR}/mpr121_forwarder/mpr121_forwarder}"
SENSOR_WORKDIR="${SENSOR_WORKDIR:-${HOME_DIR}/mpr121_forwarder}"

# ---- checks ----
if [[ $EUID -ne 0 ]]; then
  echo "Please run with sudo: sudo ./install.sh"
  exit 1
fi

id -u "$APP_USER" >/dev/null 2>&1 || { echo "User $APP_USER not found."; exit 1; }

PYTHON_BIN="${VENV_DIR}/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python venv not found at $PYTHON_BIN"
  exit 1
fi

if [[ ! -f "$PY_APP" ]]; then
  echo "Python app not found at $PY_APP"
  exit 1
fi

if [[ ! -d "$NODE_DIR" || ! -f "$NODE_DIR/$NODE_ENTRY" ]]; then
  echo "Node app not found at $NODE_DIR/$NODE_ENTRY"
  exit 1
fi

NODE_BIN="$(command -v node || true)"
if [[ -z "${NODE_BIN}" ]]; then
  echo "Node.js not found in PATH. Install Node (e.g., via apt or nvm) and re-run."
  exit 1
fi

if [[ ! -f "$SENSOR_BIN" ]]; then
  echo "Sensor poller not found at $SENSOR_BIN"
  exit 1
fi
chmod +x "$SENSOR_BIN"

# persistent journald logs (handy on Pi)
mkdir -p /var/log/journal
systemctl restart systemd-journald

# ---- grasp-server.service ----
cat >/etc/systemd/system/grasp-server.service <<EOF
[Unit]
Description=Grasp Python server
Wants=network-online.target
After=network-online.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${PY_WORKDIR}
# Run Python unbuffered so print() shows up immediately in journald
ExecStart=${PYTHON_BIN} -u ${PY_APP}
Environment=PYTHONUNBUFFERED=1
SyslogIdentifier=grasp-server
Restart=on-failure
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ---- node-web.service ----
cat >/etc/systemd/system/node-web.service <<EOF
[Unit]
Description=Node web server
Wants=network-online.target
After=network-online.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${NODE_DIR}
ExecStart=${NODE_BIN} ${NODE_DIR}/${NODE_ENTRY}
Environment=NODE_ENV=production
Restart=on-failure
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ---- sensor-poller.service ----
cat >/etc/systemd/system/sensor-poller.service <<EOF
[Unit]
Description=MPR121 sensor poller

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${SENSOR_WORKDIR}
ExecStart=${SENSOR_BIN}
Restart=on-failure
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ---- grouping target ----
cat >/etc/systemd/system/grasp-stack.target <<'EOF'
[Unit]
Description=All Grasp services
Wants=grasp-server.service node-web.service sensor-poller.service
After=network-online.target

[Install]
WantedBy=multi-user.target
EOF

# ---- clean up any legacy SysV init script so it doesn't confuse things ----
if systemctl list-unit-files | grep -q '^startup.service'; then
  systemctl disable startup.service || true
fi
update-rc.d -f startup.sh remove 2>/dev/null || true
rm -f /etc/init.d/startup.sh 2>/dev/null || true



# ---- enable + start ----
systemctl daemon-reload
systemctl enable grasp-stack.target
systemctl start grasp-stack.target

echo
echo "✔ Installed and started:"
echo "    - grasp-server.service"
echo "    - node-web.service"
echo "    - sensor-poller.service"
echo "    - grasp-stack.target (group)"
echo
echo "Status (short):"
systemctl --no-pager --full status grasp-server.service | sed -n '1,5p' || true
systemctl --no-pager --full status node-web.service   | sed -n '1,5p' || true
systemctl --no-pager --full status sensor-poller.service | sed -n '1,5p' || true
echo
echo "Log tips:"
echo "  journalctl -u grasp-server.service -f"
echo "  journalctl -u node-web.service -f"
echo "  journalctl -u sensor-poller.service -f"
echo "  systemctl list-dependencies grasp-stack.target"

sudo tee /etc/systemd/system/grasp-stack.target >/dev/null <<'EOF'
[Unit]
Description=All Grasp services
Wants=grasp-server.service node-web.service sensor-poller.service
After=network-online.target

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now grasp-stack.target



