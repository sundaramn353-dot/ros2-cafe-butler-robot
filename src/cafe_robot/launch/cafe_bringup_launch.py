"""
cafe_bringup_launch.py — Complete café robot bringup.

Single command to launch everything:
  1. Gazebo Harmonic (café world)
  2. TurtleBot3 spawn + robot_state_publisher + ros_gz_bridge
  3. Nav2 navigation stack (map_server, AMCL, planner, controller, etc.)
  4. RViz2 with Nav2 displays
  5. Initial pose publisher (auto-localize at home position)

Usage:
    ros2 launch cafe_robot cafe_bringup_launch.py
"""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    TimerAction,
    ExecuteProcess,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions.command import Command
from launch.substitutions.find_executable import FindExecutable

from launch_ros.actions import Node


def generate_launch_description():
    pkg_cafe_robot = get_package_share_directory('cafe_robot')
    pkg_nav2_tb3_sim = get_package_share_directory('nav2_minimal_tb3_sim')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # ── Arguments ────────────────────────────────────────────────
    use_sim_time = LaunchConfiguration('use_sim_time')
    launch_rviz = LaunchConfiguration('launch_rviz')
    x_pose = LaunchConfiguration('x_pose')
    y_pose = LaunchConfiguration('y_pose')

    declare_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true')
    declare_rviz = DeclareLaunchArgument(
        'launch_rviz', default_value='true')
    declare_x = DeclareLaunchArgument(
        'x_pose', default_value='-3.5',
        description='Robot X spawn (HOME position)')
    declare_y = DeclareLaunchArgument(
        'y_pose', default_value='-1.0',
        description='Robot Y spawn (HOME position)')

    # ── Env vars for Gazebo model paths ──────────────────────────
    set_gz_path1 = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        os.path.join(pkg_nav2_tb3_sim, 'models'))
    set_gz_path2 = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        str(Path(pkg_nav2_tb3_sim).parent.resolve()))

    # ── 1. Gazebo Harmonic ───────────────────────────────────────
    world_file = os.path.join(pkg_cafe_robot, 'worlds', 'cafe_world.sdf')
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={
            'gz_args': f'-r -v4 {world_file}',
            'on_exit_shutdown': 'true',
        }.items(),
    )

    # ── 2. Robot State Publisher ─────────────────────────────────
    urdf_file = os.path.join(
        pkg_nav2_tb3_sim, 'urdf', 'turtlebot3_waffle.urdf')
    with open(urdf_file, 'r') as f:
        robot_desc = f.read()

    # Fix mesh paths: upstream URDF has broken paths missing the
    # turtlebot3_model/meshes/ subdirectory
    robot_desc = robot_desc.replace(
        'package://nav2_minimal_tb3_sim/models/waffle_base.dae',
        'package://nav2_minimal_tb3_sim/models/turtlebot3_model/meshes/waffle_base.dae'
    ).replace(
        'package://nav2_minimal_tb3_sim/models/tire.dae',
        'package://nav2_minimal_tb3_sim/models/turtlebot3_model/meshes/tire.dae'
    ).replace(
        'package://nav2_minimal_tb3_sim/models/lds.dae',
        'package://nav2_minimal_tb3_sim/models/turtlebot3_model/meshes/lds.dae'
    ).replace(
        'package://nav2_minimal_tb3_sim/models/r200.dae',
        'package://nav2_minimal_tb3_sim/models/turtlebot3_model/meshes/r200.dae'
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'use_sim_time': use_sim_time,
            'robot_description': robot_desc,
        }],
        output='screen',
    )

    # ── 3. Spawn robot ───────────────────────────────────────────
    robot_sdf = os.path.join(
        pkg_nav2_tb3_sim, 'urdf', 'gz_waffle.sdf.xacro')
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-name', 'turtlebot3_waffle',
            '-string', Command([
                FindExecutable(name='xacro'), ' ', robot_sdf]),
            '-x', x_pose, '-y', y_pose, '-z', '0.01',
            '-Y', '0.0',
        ],
    )

    # ── 4. ros_gz_bridge ─────────────────────────────────────────
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{
            'config_file': os.path.join(
                pkg_cafe_robot, 'config', 'bridge_config.yaml'),
            'expand_gz_topic_names': True,
            'use_sim_time': True,
        }],
        output='screen',
    )

    # ── 5. Nav2 navigation stack (delayed 5s for Gazebo startup) ─
    nav2_launch = TimerAction(
        period=5.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_cafe_robot,
                                 'launch', 'navigation_launch.py')),
                launch_arguments={
                    'use_sim_time': 'true',
                    'params_file': os.path.join(
                        pkg_cafe_robot, 'config', 'nav2_params.yaml'),
                    'map': os.path.join(
                        pkg_cafe_robot, 'maps', 'cafe_map.yaml'),
                    'autostart': 'true',
                }.items(),
            ),
        ],
    )

    # ── 6. Auto-initial pose publisher (delayed 10s for AMCL startup)
    auto_initial_pose = TimerAction(
        period=10.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    'ros2', 'topic', 'pub', '--once', '/initialpose',
                    'geometry_msgs/msg/PoseWithCovarianceStamped',
                    '{"header": {"frame_id": "map"}, "pose": {"pose": {"position": {"x": -3.5, "y": -1.0, "z": 0.0}, "orientation": {"w": 1.0}}}}'
                ],
                output='screen'
            )
        ]
    )

    # ── 7. RViz2 ─────────────────────────────────────────────────
    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(
            pkg_cafe_robot, 'rviz', 'nav2_cafe.rviz')],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(launch_rviz),
    )

    return LaunchDescription([
        declare_sim_time,
        declare_rviz,
        declare_x,
        declare_y,

        set_gz_path1,
        set_gz_path2,

        LogInfo(msg='☕  Full Café Robot Bringup — Gazebo + Nav2 + RViz …'),

        gazebo,
        robot_state_publisher,
        spawn_robot,
        bridge,
        nav2_launch,
        auto_initial_pose,
        rviz2,
    ])
