ifdown eth0
ifup eth0
/usr/bin/redis-server /etc/redis/redis_6379.conf
/usr/bin/redis-server /etc/redis/redis_6380.conf
webdis /home/root/grasp/webdis_conf_files/webdis.json

dserv -d
dserv_tcp -d
dserv_send -d

mount diddy.neuro.brown.edu:/mnt/SharedDrives/Labfiles /shared/lab