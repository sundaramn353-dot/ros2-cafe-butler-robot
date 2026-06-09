# Maps Directory
#
# Place your map files here after running SLAM:
#   - cafe_map.yaml   (map server metadata)
#   - cafe_map.pgm    (occupancy grid image)
#
# Generate a map with:
#   ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true
#   ros2 run nav2_map_server map_saver_cli -f maps/cafe_map
