```
sudo apt install redis-server -y
redis-cli ping
sudo systemctl enable redis-server
sudo systemctl start redis-server



cd ~
git clone https://github.com/graspomatic/grasp.git
cd grasp
sudo ./install.sh
sudo reboot

cd ~/grasp
python3 -m venv grasp2
source grasp2/bin/activate
pip install numpy redis dynamixel-sdk gpiod

```

Install ethernet adapter for 2nd interface with motors

```
nmcli con show
sudo nmcli con mod "Wired connection 2" ipv4.addresses 100.0.0.1/24
sudo nmcli con mod "Wired connection 2" ipv4.method manual
sudo nmcli con mod "Wired connection 2" ipv4.gateway ""
sudo nmcli con mod "Wired connection 2" ipv4.dns ""

```

Install nodejs

```
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
cd ~/grasp/node-web-server
rm -f package‑lock.json  
rm -rf node_modules
npm install express socket.io --save
node server.js
```

Install webdis
```
sudo apt install webdis
```

Check for I2C touch sensors
```
sudo i2cdetect -y 1
BUS=1
ADDR=0x5a
sudo i2cset -y $BUS $ADDR 0x5E 0x00

for E in {0..11}; do
  T_REG=$((0x41 + E*2))
  R_REG=$((0x42 + E*2))
  sudo i2cset -y $BUS $ADDR $T_REG 0x0F
  sudo i2cset -y $BUS $ADDR $R_REG 0x0A
done

sudo i2cset -y $BUS $ADDR 0x5E 0x8F

sudo i2cget -y $BUS $ADDR 0x00 w
(should be 0x0000)
(touch)
sudo i2cget -y $BUS $ADDR 0x00 w
(should be not 0x0000)


git clone https://github.com/SheinbergLab/mpr121_forwarder.git
cd mpr121_fowarder
chmod +x setup_i2c.sh
./setup_i2c.sh
sudo reboot
i2cdetect -y 1
cd mpr121_fowarder
make
./mpr121_forwarder 

```


Start everything
```
source grasp/grasp2/bin/activate
python grasp/grasp_server.py

sudo /usr/bin/redis-server /etc/redis/redis_6380.conf

sudo systemctl status webdis

cd grasp/node-web-server
node server.js
'''

Check servers

```
# One service (status + last few log lines)
systemctl status grasp-server.service
systemctl status node-web.service
systemctl status sensor-poller.service

# Are they active? (machine-parsable)
systemctl is-active grasp-server.service node-web.service sensor-poller.service

# Group target (what it includes)
systemctl status grasp-stack.target
systemctl list-dependencies grasp-stack.target

# Follow one service
journalctl -fu grasp-server.service
journalctl -fu node-web.service
journalctl -fu sensor-poller.service

# (Optional) follow all three together
journalctl -f -u grasp-server.service -u node-web.service -u sensor-poller.service

journalctl -b -u grasp-server.service --no-pager
journalctl -b -u node-web.service --no-pager
journalctl -b -u sensor-poller.service --no-pager

# Restart all three at once (recommended)
sudo systemctl restart grasp-server.service node-web.service sensor-poller.service

# or stop/start via the target (forces a full restart of the trio)
sudo systemctl stop grasp-stack.target && sudo systemctl start grasp-stack.target

# Restart just one
sudo systemctl restart grasp-server.service

```



