#!/usr/bin/env python3
"""
cafe_goal_navigator.py — Action client node to send navigation goals to Nav2.

Reads target coordinates from ROS parameters (loaded from a YAML file),
connects to the /navigate_to_pose action server, sends goals, handles real-time
feedback (distance remaining, estimated time of arrival), and reports results.

Usage:
    ros2 run cafe_robot cafe_goal_navigator --ros-args --params-file src/cafe_robot/config/cafe_poses.yaml -p target:=table1
"""

import sys
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.task import Future

from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from action_msgs.msg import GoalStatus


class CafeGoalNavigator(Node):
    """
    ROS 2 Action Client Node for Nav2 NavigateToPose.
    """

    def __init__(self):
        super().__init__('cafe_goal_navigator')

        # ── Parameters ──────────────────────────────────────────────
        self.declare_parameter('target', 'home')  # Target location
        
        # Declare pose coordinates with defaults (in case YAML isn't loaded)
        self.declare_parameter('poses.home', [-3.5, -1.0, 0.0, 1.0])
        self.declare_parameter('poses.kitchen', [-3.5, 3.0, 0.0, 1.0])
        self.declare_parameter('poses.table1', [2.5, 2.5, 0.0, 1.0])
        self.declare_parameter('poses.table2', [2.5, 0.0, 0.0, 1.0])
        self.declare_parameter('poses.table3', [2.5, -2.5, 0.0, 1.0])

        self.target = self.get_parameter('target').get_parameter_value().string_value
        
        # ── Action Client ────────────────────────────────────────────
        self.action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        
        # Feedback throttling state
        self.last_feedback_time = 0.0
        self.goal_handle = None

        self.get_logger().info('🧭  Cafe Goal Navigator initialized.')

    def send_goal_to_target(self):
        """Finds the coordinates for the target pose and sends the goal."""
        param_name = f'poses.{self.target}'
        
        if not self.has_parameter(param_name):
            self.get_logger().error(f"❌  Target '{self.target}' is not defined in poses config!")
            self.get_logger().info("Available targets: home, kitchen, table1, table2, table3")
            sys.exit(1)

        try:
            pose_coords = self.get_parameter(param_name).value
            if not pose_coords or len(pose_coords) < 4:
                raise ValueError("Coordinates empty or insufficient length")
            x, y, z, w = [float(val) for val in pose_coords]
        except Exception as e:
            self.get_logger().error(f"❌  Invalid coordinates for target '{self.target}': {e}")
            sys.exit(1)

        self.get_logger().info(f"📍  Target: '{self.target}' -> X: {x:.2f}, Y: {y:.2f}, Orient(z/w): ({z:.2f}/{w:.2f})")

        # Wait for Action Server
        self.get_logger().info('⏳  Waiting for /navigate_to_pose action server...')
        if not self.action_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error('❌  Action server /navigate_to_pose not available!')
            sys.exit(1)

        # Create goal message
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.position.z = 0.0
        goal_msg.pose.pose.orientation.z = z
        goal_msg.pose.pose.orientation.w = w

        self.get_logger().info(f"🚀  Sending goal to {self.target}...")

        send_goal_future = self.action_client.send_goal_async(
            goal_msg, 
            feedback_callback=self.feedback_callback
        )
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future: Future):
        """Handles the server's acceptance/rejection of the goal."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('❌  Goal was rejected by the Nav2 action server!')
            sys.exit(1)

        self.goal_handle = goal_handle
        self.get_logger().info('✅  Goal accepted by server. Navigating...')

        # Request result
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        """Processes real-time feedback from Nav2."""
        feedback = feedback_msg.feedback
        now = self.get_clock().now().nanoseconds / 1e9

        # Throttle feedback logging to once every 2 seconds
        if now - self.last_feedback_time >= 2.0:
            dist = feedback.distance_remaining
            # Convert duration to seconds
            time_remaining = feedback.estimated_time_remaining.sec + (feedback.estimated_time_remaining.nanosec / 1e9)
            
            self.get_logger().info(
                f"📈  Feedback: Remaining Distance: {dist:.2f}m | ETA: {time_remaining:.1f}s"
            )
            self.last_feedback_time = now

    def get_result_callback(self, future: Future):
        """Handles the completion of the navigation task."""
        result = future.result()
        status = result.status

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f"🎉  SUCCESS! Successfully arrived at '{self.target}'!")
        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().warn('⚠️  Navigation was canceled!')
        elif status == GoalStatus.STATUS_ABORTED:
            self.get_logger().error('❌  Navigation aborted! Path is likely blocked.')
        else:
            self.get_logger().error(f"❌  Navigation failed with status code: {status}")

        # Shutdown node on completion
        rclpy.shutdown()

    def cancel_goal(self):
        """Cancels the active goal if it exists."""
        if self.goal_handle is not None:
            self.get_logger().info('🛑  Canceling the active navigation goal...')
            self.goal_handle.cancel_goal_async()


def main(args=None):
    rclpy.init(args=args)
    
    # Enable command-line argument override for 'target' parameter
    node = CafeGoalNavigator()
    
    node.send_goal_to_target()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('🛑  Interrupted by user.')
        node.cancel_goal()
        # Wait a short duration for cancel to propagate
        node.get_logger().info('🔌  Shutting down navigator...')
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
