"""
cafe_robot_launch.py — Main launch file for the café butler robot.

Launches:
  1. Gazebo Harmonic simulation (ros_gz_sim)
  2. Robot State Publisher (URDF → TF)
  3. Nav2 navigation stack
  4. RViz2 visualization
  5. cafe_robot_node

Usage:
    ros2 launch cafe_robot cafe_robot_launch.py
    ros2 launch cafe_robot cafe_robot_launch.py use_sim_time:=true
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    GroupAction,
    LogInfo,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    # ── Package paths ────────────────────────────────────────────────
    pkg_cafe_robot = get_package_share_directory('cafe_robot')
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # ── Launch arguments ─────────────────────────────────────────────
    use_sim_time = LaunchConfiguration('use_sim_time')
    world_file = LaunchConfiguration('world')
    nav2_params_file = LaunchConfiguration('nav2_params')
    rviz_config = LaunchConfiguration('rviz_config')
    launch_rviz = LaunchConfiguration('launch_rviz')
    launch_gazebo = LaunchConfiguration('launch_gazebo')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use Gazebo simulation clock')

    declare_world = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_cafe_robot, 'worlds', 'cafe_world.sdf'),
        description='Path to Gazebo SDF world file')

    declare_nav2_params = DeclareLaunchArgument(
        'nav2_params',
        default_value=os.path.join(pkg_cafe_robot, 'config', 'nav2_params.yaml'),
        description='Path to Nav2 parameter YAML file')

    declare_rviz_config = DeclareLaunchArgument(
        'rviz_config',
        default_value=os.path.join(pkg_cafe_robot, 'rviz', 'cafe_robot.rviz'),
        description='Path to RViz configuration file')

    declare_launch_rviz = DeclareLaunchArgument(
        'launch_rviz', default_value='true',
        description='Launch RViz2 visualisation')

    declare_launch_gazebo = DeclareLaunchArgument(
        'launch_gazebo', default_value='true',
        description='Launch Gazebo Harmonic simulation')

    # ── Gazebo Harmonic ──────────────────────────────────────────────
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={
            'gz_args': ['-r -v4 ', world_file],
            'on_exit_shutdown': 'true',
        }.items(),
        condition=IfCondition(launch_gazebo),
    )

    # ── Nav2 navigation stack ────────────────────────────────────────
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2_bringup, 'launch', 'navigation_launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'params_file': nav2_params_file,
        }.items(),
    )

    # ── RViz2 ────────────────────────────────────────────────────────
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(launch_rviz),
    )

    # ── Café robot node ──────────────────────────────────────────────
    cafe_robot_node = Node(
        package='cafe_robot',
        executable='cafe_robot_node',
        name='cafe_robot_node',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'robot_name': 'cafe_butler',
            'status_rate': 2.0,
            'obstacle_threshold': 0.5,
            'linear_speed': 0.3,
            'angular_speed': 0.5,
        }],
    )

    # ── Compose ──────────────────────────────────────────────────────
    return LaunchDescription([
        # Arguments
        declare_use_sim_time,
        declare_world,
        declare_nav2_params,
        declare_rviz_config,
        declare_launch_rviz,
        declare_launch_gazebo,

        # Info
        LogInfo(msg='☕  Launching Café Robot stack …'),

        # Actions
        gazebo,
        nav2_bringup,
        rviz2_node,
        cafe_robot_node,
    ])
