ifdown eth1
ifup eth1
/usr/bin/redis-server /etc/redis/redis_6379.conf
/usr/bin/redis-server /etc/redis/redis_6380.conf
cd /usr/bin/webdis
webdis /home/root/grasp/webdis_conf_files/webdis.json

dserv -d
dserv_tcp -d
dserv_send -d