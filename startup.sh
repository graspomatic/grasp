ifdown eth1
ifup eth1
/etc/init.d/redis-server-6380 start
/etc/init.d/redis-server-6379 start
cd /usr/bin
./webdis &
