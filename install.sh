SITEDIR=$(python3 -m site --user-site)
mkdir -p "$SITEDIR"
echo "$HOME/grasp/Dynamixel2Control" > "$SITEDIR/grasp.pth"
echo "$HOME/grasp/AppliedMotionControl" >> "$SITEDIR/grasp.pth"
echo "$HOME/grasp/GPIOD" >> "$SITEDIR/grasp.pth"
echo "$HOME/grasp/controller" >> "$SITEDIR/grasp.pth"

cp startup.sh /etc/init.d/
chmod +x /etc/init.d/startup.sh
update-rc.d startup.sh defaults

#cp ./redis_conf_files/redis_6379.conf /etc/redis/
cp ./redis_conf_files/redis_6380.conf /etc/redis/
#mkdir /var/lib/redis/6379
mkdir -p /var/lib/redis/6380

redis-cli -p 6380 shutdown

cp ./redis_conf_files/redis-6380-backup/appendonly6380.aof /var/lib/redis/6380/
chown redis:redis /var/lib/redis/6380/appendonly6380.aof
chmod 644 /var/lib/redis/6380/appendonly6380.aof

#/usr/bin/redis-server /etc/redis/redis_6379.conf
/usr/bin/redis-server /etc/redis/redis_6380.conf



