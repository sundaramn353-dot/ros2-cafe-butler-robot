"""
navigation_launch.py — Launch Nav2 stack for café robot navigation.

Starts all Nav2 servers with lifecycle management:
  - map_server        (loads static map)
  - amcl              (localization)
  - planner_server    (global path planning)
  - controller_server (local trajectory following)
  - smoother_server   (path smoothing)
  - behavior_server   (recovery behaviors: spin, backup, wait)
  - bt_navigator      (behavior tree coordinator)
  - waypoint_follower (multi-goal navigation)
  - velocity_smoother (smooth cmd_vel output)
  - lifecycle_manager (manages all above nodes)

Usage:
    ros2 launch cafe_robot navigation_launch.py
    ros2 launch cafe_robot navigation_launch.py use_sim_time:=true
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    pkg_cafe_robot = get_package_share_directory('cafe_robot')

    # ── Launch arguments ─────────────────────────────────────────
    use_sim_time = LaunchConfiguration('use_sim_time')
    params_file = LaunchConfiguration('params_file')
    map_yaml = LaunchConfiguration('map')
    autostart = LaunchConfiguration('autostart')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use simulation clock')

    declare_params = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(
            pkg_cafe_robot, 'config', 'nav2_params.yaml'),
        description='Nav2 parameter file')

    declare_map = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(
            pkg_cafe_robot, 'maps', 'cafe_map.yaml'),
        description='Map YAML file for map_server')

    declare_autostart = DeclareLaunchArgument(
        'autostart', default_value='true',
        description='Auto-activate lifecycle nodes')

    # ── Rewrite params with use_sim_time ─────────────────────────
    configured_params = RewrittenYaml(
        source_file=params_file,
        param_rewrites={'use_sim_time': use_sim_time},
        convert_types=True,
    )

    # ── Nav2 lifecycle nodes ─────────────────────────────────────
    lifecycle_nodes = [
        'map_server',
        'amcl',
        'planner_server',
        'controller_server',
        'smoother_server',
        'behavior_server',
        'bt_navigator',
        'waypoint_follower',
        'velocity_smoother',
    ]

    # ── Map Server ───────────────────────────────────────────────
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[
            configured_params,
            {'yaml_filename': map_yaml},
        ],
    )

    # ── AMCL (Localization) ──────────────────────────────────────
    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[configured_params],
    )

    # ── Planner Server (Global Planning) ─────────────────────────
    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[configured_params],
    )

    # ── Controller Server (Local Control) ────────────────────────
    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[configured_params],
    )

    # ── Smoother Server ──────────────────────────────────────────
    smoother_server = Node(
        package='nav2_smoother',
        executable='smoother_server',
        name='smoother_server',
        output='screen',
        parameters=[configured_params],
    )

    # ── Behavior Server (Recoveries) ─────────────────────────────
    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[configured_params],
    )

    # ── BT Navigator ─────────────────────────────────────────────
    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[configured_params],
    )

    # ── Waypoint Follower ────────────────────────────────────────
    waypoint_follower = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        name='waypoint_follower',
        output='screen',
        parameters=[configured_params],
    )

    # ── Velocity Smoother ────────────────────────────────────────
    velocity_smoother = Node(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        name='velocity_smoother',
        output='screen',
        parameters=[configured_params],
    )

    # ── Lifecycle Manager ────────────────────────────────────────
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'node_names': lifecycle_nodes,
            'bond_timeout': 10.0,
            'attempt_respawn_reconnection': True,
        }],
    )

    # ── Compose ──────────────────────────────────────────────────
    return LaunchDescription([
        declare_use_sim_time,
        declare_params,
        declare_map,
        declare_autostart,

        LogInfo(msg='🧭  Launching Nav2 navigation stack …'),

        map_server,
        amcl,
        planner_server,
        controller_server,
        smoother_server,
        behavior_server,
        bt_navigator,
        waypoint_follower,
        velocity_smoother,
        lifecycle_manager,
    ])
