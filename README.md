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
pip install numpy redis dynamixel-sdk



```
