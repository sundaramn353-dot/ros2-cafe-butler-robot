"""
gazebo_world_launch.py — Launch only the Gazebo Harmonic café world.

Usage:
    ros2 launch cafe_robot gazebo_world_launch.py
    ros2 launch cafe_robot gazebo_world_launch.py headless:=true
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_cafe_robot = get_package_share_directory('cafe_robot')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    world_file = LaunchConfiguration('world')
    headless = LaunchConfiguration('headless')

    declare_world = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(
            pkg_cafe_robot, 'worlds', 'cafe_world.sdf'),
        description='Full path to the Gazebo SDF world file')

    declare_headless = DeclareLaunchArgument(
        'headless', default_value='false',
        description='Run Gazebo without GUI (headless mode)')

    # Gazebo Harmonic via ros_gz_sim
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={
            'gz_args': ['-r -v4 ', world_file],
            'on_exit_shutdown': 'true',
        }.items(),
    )

    return LaunchDescription([
        declare_world,
        declare_headless,
        LogInfo(msg='☕  Launching Café Gazebo World …'),
        gazebo,
    ])
