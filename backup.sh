mount diddy.neuro.brown.edu:/mnt/SharedDrives/Labfiles /shared/lab

cp /var/lib/redis/6380/appendonly6380.aof /shared/lab/stimuli/grasp

mv -- /shared/lab/stimuli/grasp/appendonly6380.aof "/shared/lab/stimuli/grasp/$(mktemp --dry-run appendonly6380.aofXXXXXXX)"
