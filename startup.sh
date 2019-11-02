ifdown eth0
ifup eth0
/usr/bin/redis-server /etc/redis/redis_6380.conf

dserv -d
dserv_tcp -d
dserv_send -d
dserv_log -d
obssync -d
touch_sensor -i 10 -d


/bin/mount diddy.neuro.brown.edu:/mnt/SharedDrives/Labfiles /shared/lab

webdis /home/root/grasp/webdis_conf_files/webdis.json &
