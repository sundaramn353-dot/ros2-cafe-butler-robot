"""
spawn_robot_launch.py — Spawn TurtleBot3 Waffle in the café world.

Launches:
  1. Gazebo Harmonic with café world
  2. robot_state_publisher (URDF → /tf, /robot_description)
  3. ros_gz_sim create (spawn robot at home position)
  4. ros_gz_bridge (bridge /scan, /odom, /tf, /cmd_vel, /imu, /clock)
  5. RViz2 (optional)

Usage:
    ros2 launch cafe_robot spawn_robot_launch.py
    ros2 launch cafe_robot spawn_robot_launch.py launch_rviz:=true
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
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions.command import Command
from launch.substitutions.find_executable import FindExecutable

from launch_ros.actions import Node


def generate_launch_description():
    # ── Package paths ────────────────────────────────────────────
    pkg_cafe_robot = get_package_share_directory('cafe_robot')
    pkg_nav2_tb3_sim = get_package_share_directory('nav2_minimal_tb3_sim')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # ── Launch arguments ─────────────────────────────────────────
    use_sim_time = LaunchConfiguration('use_sim_time')
    launch_rviz = LaunchConfiguration('launch_rviz')
    world_file = LaunchConfiguration('world')
    robot_sdf = LaunchConfiguration('robot_sdf')

    # Robot spawn pose — HOME position in café
    x_pose = LaunchConfiguration('x_pose')
    y_pose = LaunchConfiguration('y_pose')
    z_pose = LaunchConfiguration('z_pose')
    yaw = LaunchConfiguration('yaw')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use Gazebo simulation clock')

    declare_launch_rviz = DeclareLaunchArgument(
        'launch_rviz', default_value='true',
        description='Launch RViz2')

    declare_world = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(
            pkg_cafe_robot, 'worlds', 'cafe_world.sdf'),
        description='Gazebo world file')

    declare_robot_sdf = DeclareLaunchArgument(
        'robot_sdf',
        default_value=os.path.join(
            pkg_nav2_tb3_sim, 'urdf', 'gz_waffle.sdf.xacro'),
        description='TurtleBot3 SDF xacro for Gazebo spawning')

    # Home position in café: (-3.5, -1.0)
    declare_x = DeclareLaunchArgument(
        'x_pose', default_value='-3.5',
        description='Robot X spawn position')
    declare_y = DeclareLaunchArgument(
        'y_pose', default_value='-1.0',
        description='Robot Y spawn position')
    declare_z = DeclareLaunchArgument(
        'z_pose', default_value='0.01',
        description='Robot Z spawn position')
    declare_yaw = DeclareLaunchArgument(
        'yaw', default_value='0.0',
        description='Robot yaw spawn orientation')

    # ── Environment: Gazebo model paths ──────────────────────────
    set_gz_resource_path = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        os.path.join(pkg_nav2_tb3_sim, 'models'))
    set_gz_resource_path2 = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        str(Path(os.path.join(pkg_nav2_tb3_sim)).parent.resolve()))

    # ── 1. Gazebo Harmonic ───────────────────────────────────────
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={
            'gz_args': ['-r -v4 ', world_file],
            'on_exit_shutdown': 'true',
        }.items(),
    )

    # ── 2. Robot State Publisher (URDF for RViz/TF) ──────────────
    urdf_file = os.path.join(
        pkg_nav2_tb3_sim, 'urdf', 'turtlebot3_waffle.urdf')
    with open(urdf_file, 'r') as f:
        robot_description_content = f.read()

    # Fix mesh paths: upstream URDF has broken paths missing the
    # turtlebot3_model/meshes/ subdirectory
    robot_description_content = robot_description_content.replace(
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
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'robot_description': robot_description_content,
        }],
    )

    # ── 3. Spawn robot in Gazebo ─────────────────────────────────
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-name', 'turtlebot3_waffle',
            '-string', Command([
                FindExecutable(name='xacro'), ' ',
                robot_sdf]),
            '-x', x_pose,
            '-y', y_pose,
            '-z', z_pose,
            '-Y', yaw,
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

    # ── 5. RViz2 ─────────────────────────────────────────────────
    rviz_config = os.path.join(
        pkg_cafe_robot, 'rviz', 'cafe_robot.rviz')

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(launch_rviz),
    )

    # ── Compose ──────────────────────────────────────────────────
    return LaunchDescription([
        # Declare arguments
        declare_use_sim_time,
        declare_launch_rviz,
        declare_world,
        declare_robot_sdf,
        declare_x,
        declare_y,
        declare_z,
        declare_yaw,

        # Environment
        set_gz_resource_path,
        set_gz_resource_path2,

        LogInfo(msg='☕  Spawning TurtleBot3 in Café World …'),

        # Actions
        gazebo,
        robot_state_publisher,
        spawn_robot,
        bridge,
        rviz2,
    ])
