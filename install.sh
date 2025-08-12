#!/usr/bin/env bash
set -euo pipefail

# -------- Python user site path entries --------
TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
USER_SITE="$(sudo -u "$TARGET_USER" python3 -m site --user-site)"

sudo -u "$TARGET_USER" mkdir -p "$USER_SITE"
{
  echo "$TARGET_HOME/grasp/Dynamixel2Control"
  echo "$TARGET_HOME/grasp/AppliedMotionControl"
  echo "$TARGET_HOME/grasp/GPIOD"
  echo "$TARGET_HOME/grasp/controller"
} | sudo -u "$TARGET_USER" tee "$USER_SITE/grasp.pth" >/dev/null

# -------- Redis 6380 setup --------
sudo install -d -m 755 -o root -g redis /etc/redis
sudo install -o redis -g redis -m 644 ./redis_conf_files/redis-6380.conf /etc/redis/redis-6380.conf
sudo install -d -m 770 -o redis -g redis /var/lib/redis/6380
sudo systemctl stop redis-server@6380 || true
if [ -f ./redis_conf_files/redis-6380-backup/appendonly6380.aof ]; then
  sudo install -o redis -g redis -m 644 ./redis_conf_files/redis-6380-backup/appendonly6380.aof /var/lib/redis/6380/appendonly6380.aof
fi
sudo systemctl enable --now redis-server@6380

# -------- Misc system prep --------
sudo mkdir -p /shared/lab
sudo apt -y install webdis

# -------- Service config (edit these if paths differ) --------
APP_USER="${APP_USER:-lab}"
HOME_DIR="/home/${APP_USER}"

VENV_DIR="${VENV_DIR:-${HOME_DIR}/grasp/grasp2}"
PY_APP="${PY_APP:-${HOME_DIR}/grasp/grasp_server.py}"
PY_WORKDIR="${PY_WORKDIR:-${HOME_DIR}/grasp}"

NODE_DIR="${NODE_DIR:-${HOME_DIR}/grasp/node-web-server}"
NODE_ENTRY="${NODE_ENTRY:-server.js}"

SENSOR_BIN="${SENSOR_BIN:-${HOME_DIR}/mpr121_forwarder/mpr121_forwarder}"
SENSOR_WORKDIR="${SENSOR_WORKDIR:-${HOME_DIR}/mpr121_forwarder}"

# -------- Sanity checks --------
if [[ $EUID -ne 0 ]]; then
  echo "Please run with sudo: sudo ./install.sh"
  exit 1
fi
id -u "$APP_USER" >/dev/null 2>&1 || { echo "User $APP_USER not found."; exit 1; }

PYTHON_BIN="${VENV_DIR}/bin/python"
[[ -x "$PYTHON_BIN" ]] || { echo "Python venv not found at $PYTHON_BIN"; exit 1; }
[[ -f "$PY_APP" ]] || { echo "Python app not found at $PY_APP"; exit 1; }
[[ -d "$NODE_DIR" && -f "$NODE_DIR/$NODE_ENTRY" ]] || { echo "Node app not found at $NODE_DIR/$NODE_ENTRY"; exit 1; }

NODE_BIN="$(command -v node || true)"
[[ -n "$NODE_BIN" ]] || { echo "Node.js not found in PATH. Install Node and re-run."; exit 1; }

[[ -f "$SENSOR_BIN" ]] || { echo "Sensor poller not found at $SENSOR_BIN"; exit 1; }
chmod +x "$SENSOR_BIN"

# -------- Persistent journald logs (handy on Pi) --------
mkdir -p /var/log/journal
systemctl restart systemd-journald

# -------- grasp-server.service (Python, unbuffered) --------
cat >/etc/systemd/system/grasp-server.service <<EOF
[Unit]
Description=Grasp Python server
Wants=network-online.target
After=network-online.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${PY_WORKDIR}
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

# -------- node-web.service --------
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
SyslogIdentifier=node-web
Restart=on-failure
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# -------- sensor-poller.service --------
cat >/etc/systemd/system/sensor-poller.service <<EOF
[Unit]
Description=MPR121 sensor poller

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${SENSOR_WORKDIR}
ExecStart=${SENSOR_BIN}
SyslogIdentifier=sensor-poller
Restart=on-failure
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# -------- grouping target (enable-able) --------
cat >/etc/systemd/system/grasp-stack.target <<'EOF'
[Unit]
Description=All Grasp services
Wants=grasp-server.service node-web.service sensor-poller.service
After=network-online.target

[Install]
WantedBy=multi-user.target
EOF

# -------- Remove any old SysV script if it exists --------
update-rc.d -f startup.sh remove 2>/dev/null || true
rm -f /etc/init.d/startup.sh 2>/dev/null || true

# -------- Enable + start (via target) --------
systemctl daemon-reload
systemctl enable --now grasp-stack.target

echo
echo "✔ Installed and started:"
systemctl --no-pager --full status grasp-server.service   | sed -n '1,6p' || true
systemctl --no-pager --full status node-web.service       | sed -n '1,6p' || true
systemctl --no-pager --full status sensor-poller.service  | sed -n '1,6p' || true
echo
echo "Log tips:"
echo "  journalctl -fu grasp-server.service"
echo "  journalctl -fu node-web.service"
echo "  journalctl -fu sensor-poller.service"
echo "  systemctl list-dependencies grasp-stack.target"
