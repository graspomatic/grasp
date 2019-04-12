ifdown eth1
ifup eth1
/usr/bin/redis-server /etc/redis/redis_6379.conf
/usr/bin/redis-server /etc/redis/redis_6380.conf
cd /usr/bin/webis
./webdis &
