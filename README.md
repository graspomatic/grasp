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

Start everything
```
source grasp/grasp2/bin/activate
python grasp/grasp_server.py

sudo systemctl status webdis

cd grasp/node-web-server
node server.js
'''
