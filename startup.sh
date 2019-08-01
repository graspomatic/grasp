ifdown eth0
ifup eth0
/usr/bin/redis-server /etc/redis/redis_6379.conf
/usr/bin/redis-server /etc/redis/redis_6380.conf

/usr/bin/dserv -d
/usr/bin/dserv_tcp -d
/usr/bin/dserv_send -d

/bin/mount diddy.neuro.brown.edu:/mnt/SharedDrives/Labfiles /shared/lab

webdis /home/root/grasp/webdis_conf_files/webdis.json &