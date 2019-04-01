SITEDIR=$(python3 -m site --user-site)
mkdir -p "$SITEDIR"
echo "$HOME/grasp/Dynamixel2Control" > "$SITEDIR/grasp.pth"
echo "$HOME/grasp/AppliedMotionControl" >> "$SITEDIR/grasp.pth"
echo "$HOME/grasp/GPIOD" >> "$SITEDIR/grasp.pth"
echo "$HOME/grasp/controller" >> "$SITEDIR/grasp.pth"

chmod +x ./startup.sh
update-rc.d startup.sh defaults