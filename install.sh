SITEDIR=$(python3 -m site --user-site)
mkdir -p "$SITEDIR"
echo "$HOME/grasp/Dynamixel2Control" > "$SITEDIR/grasp.pth"
echo "$HOME/grasp/AppliedMotionControl" >> "$SITEDIR/grasp.pth"
echo "$HOME/grasp/GPIOD" >> "$SITEDIR/grasp.pth"
echo "$HOME/grasp/controller" >> "$SITEDIR/grasp.pth"

cp startup.sh /etc/init.d/startup.sh
chmod +x /etc/init.d/startup.sh
update-rc.d startup.sh defaults

cp ./redis_6379.conf /etc/redis/
cp ./redis_6380.conf /etc/redis/
mkdir /var/lib/redis/6379
mkdir /var/lib/redis/6380