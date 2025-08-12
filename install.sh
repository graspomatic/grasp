SITEDIR=$(python3 -m site --user-site)
mkdir -p "$SITEDIR"
echo "$HOME/grasp/Dynamixel2Control" > "$SITEDIR/grasp.pth"
echo "$HOME/grasp/AppliedMotionControl" >> "$SITEDIR/grasp.pth"
echo "$HOME/grasp/GPIOD" >> "$SITEDIR/grasp.pth"
echo "$HOME/grasp/controller" >> "$SITEDIR/grasp.pth"

cp startup.sh /etc/init.d/
chmod +x /etc/init.d/startup.sh
update-rc.d startup.sh defaults

#cp ./redis_conf_files/redis_6379.conf /etc/redis/
cp ./redis_conf_files/redis_6380.conf /etc/redis/
sudo chown redis:redis /etc/redis/redis_6380.conf
sudo chmod 644 /etc/redis/redis_6380.conf
sudo chown root:redis /etc/redis
sudo chmod 755 /etc/redis
#mkdir /var/lib/redis/6379
mkdir -p /var/lib/redis/6380

redis-cli -p 6380 shutdown

cp ./redis_conf_files/redis-6380-backup/appendonly6380.aof /var/lib/redis/6380/
chown redis:redis /var/lib/redis/6380/appendonly6380.aof
chmod 644 /var/lib/redis/6380/appendonly6380.aof

#/usr/bin/redis-server /etc/redis/redis_6379.conf
/usr/bin/redis-server /etc/redis/redis_6380.conf

sudo mkdir -p /shared/lab

#!/usr/bin/env bash
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
ExecStart=${PYTHON_BIN} ${PY_APP}
Restart=on-failure
RestartSec=3
# Optional envs:
# Environment=PYTHONUNBUFFERED=1
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
EOF

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


sudo apt install webdis

