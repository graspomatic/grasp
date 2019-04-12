ifdown eth1
ifup eth1
/etc/init.d/redis-server-6379 stop
/etc/init.d/redis-server-6379 start
/etc/init.d/redis-server-6380 stop
/etc/init.d/redis-server-6380 start
cd /usr/bin
./webdis &
