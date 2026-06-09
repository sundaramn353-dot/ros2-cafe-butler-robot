#!/usr/bin/env python3
"""
cafe_robot_node.py — Finite State Machine (FSM) Node for Cafe Butler Robot.
Implements the ROS 2 Jazzy python operator command system and FSM.
"""

import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.task import Future

from std_msgs.msg import String
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from action_msgs.msg import GoalStatus
from enum import Enum, auto


class FSMState(Enum):
    IDLE = auto()
    GO_TO_KITCHEN = auto()
    WAIT_KITCHEN_CONFIRM = auto()
    GO_TO_TABLE = auto()
    WAIT_TABLE_CONFIRM = auto()
    RETURN_KITCHEN = auto()
    RETURN_HOME = auto()
    MULTI_DELIVERY = auto()
    CANCELLED = auto()


class CafeRobotNode(Node):
    """
    ROS 2 Node executing a Finite State Machine for cafe delivery operations,
    responding dynamically to operator inputs and managing Nav2 navigation goals.
    """

    def __init__(self):
        super().__init__('cafe_robot_node')

        # ── Parameters ──────────────────────────────────────────────
        # Coordinates (X, Y, Z_orient, W_orient)
        self.declare_parameter('poses.home', [-3.5, -1.0, 0.0, 1.0])
        self.declare_parameter('poses.kitchen', [-3.0, 2.8, 0.0, 1.0])
        self.declare_parameter('poses.table1', [1.5, 2.5, 0.0, 1.0])
        self.declare_parameter('poses.table2', [1.5, 0.0, 0.0, 1.0])
        self.declare_parameter('poses.table3', [1.5, -2.5, 0.0, 1.0])
        self.declare_parameter('confirm_timeout', 30.0)      # Timeout in seconds
        self.declare_parameter('require_confirmation', True) # Whether confirmation is required

        self.confirm_timeout = self.get_parameter('confirm_timeout').value
        self.require_confirmation = self.get_parameter('require_confirmation').value

        # ── FSM State ────────────────────────────────────────────────
        self.state = FSMState.IDLE
        self.order_queue = []                 # Generic queue-based order management
        self.active_waypoint_names = []       # Remaining targets in the current run
        self.current_target = None            # Current Nav2 target
        self.is_multi_delivery = False        # Flag indicating multi-table run
        self.skipping_current_table = False   # Flag indicating we are skipping the current table
        self.delivery_failed_or_canceled = False # Tracks if any table timed out or was cancelled

        self.wait_start_time = 0.0            # Timestamp for tracking confirmation timeouts

        # Action client state
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.goal_handle = None
        self.action_in_progress = False

        # ── Publishers ───────────────────────────────────────────────
        self.status_pub = self.create_publisher(String, '/robot_status', 10)
        self.legacy_status_pub = self.create_publisher(String, '/cafe_robot/status', 10)

        # ── Subscribers ──────────────────────────────────────────────
        self.order_sub = self.create_subscription(
            String, '/new_order', self.new_order_callback, 10)
        self.legacy_order_sub = self.create_subscription(
            String, '/cafe_robot/order', self.new_order_callback, 10)

        self.cancel_sub = self.create_subscription(
            String, '/cancel_order', self.cancel_order_callback, 10)
        self.legacy_cancel_sub = self.create_subscription(
            String, '/cafe_robot/cancel', self.cancel_order_callback, 10)

        self.kitchen_confirm_sub = self.create_subscription(
            String, '/kitchen_confirm', self.kitchen_confirm_callback, 10)
        self.legacy_kitchen_confirm_sub = self.create_subscription(
            String, '/cafe_robot/kitchen_confirm', self.kitchen_confirm_callback, 10)

        self.table_confirm_sub = self.create_subscription(
            String, '/table_confirm', self.table_confirm_callback, 10)
        self.legacy_table_confirm_sub = self.create_subscription(
            String, '/cafe_robot/table_confirm', self.table_confirm_callback, 10)

        # ── FSM Loop Timer (2 Hz) ────────────────────────────────────
        self.fsm_timer = self.create_timer(0.5, self.fsm_tick)

        self.get_logger().info(f"☕  Cafe Butler Robot FSM Node initialized in state: {self.state.name}")

    # ── Topic Callbacks ──────────────────────────────────────────────

    def new_order_callback(self, msg: String):
        """Receives new order table targets dynamically."""
        table_id = msg.data.strip().lower()
        if table_id in ['table1', 'table2', 'table3']:
            self.order_queue.append(table_id)
            self.get_logger().info(f"📋  Order received and queued: '{table_id.upper()}'. Current Queue: {self.order_queue}")
        else:
            self.get_logger().warn(f"📋  Rejected invalid table order: '{table_id}'")

    def cancel_order_callback(self, msg: String):
        """Processes cancel commands according to exact PDF requirements."""
        cancel_target = msg.data.strip().lower()
        self.get_logger().warn(f"🛑  Cancel command received for: '{cancel_target.upper()}'")

        # CASE A: If robot is going to kitchen and receives cancel
        if self.state == FSMState.GO_TO_KITCHEN:
            self.get_logger().warn("⚠️  CASE A: Cancelled while going to KITCHEN. Returning directly HOME.")
            self.active_waypoint_names = ['home']
            self.order_queue.clear()
            self.transition_to(FSMState.RETURN_HOME)
            if self.goal_handle:
                self.goal_handle.cancel_goal_async()
            else:
                self.action_in_progress = False
            return

        # CASE B: If robot is going to table after collecting food and receives cancel
        if self.state == FSMState.GO_TO_TABLE:
            if cancel_target in [self.current_target, 'all']:
                self.get_logger().warn(f"⚠️  CASE B: Cancelled while going to {self.current_target.upper()}. Returning KITCHEN then HOME.")
                self.delivery_failed_or_canceled = True
                self.active_waypoint_names = ['kitchen', 'home']
                self.order_queue.clear()
                self.transition_to(FSMState.RETURN_KITCHEN)
                if self.goal_handle:
                    self.goal_handle.cancel_goal_async()
                else:
                    self.action_in_progress = False
            return

        # CASE C: During multi-table delivery and receives cancel
        if self.state == FSMState.MULTI_DELIVERY:
            if cancel_target == 'all':
                self.get_logger().warn("⚠️  CASE B (Multi-Delivery): Cancelled all deliveries. Returning KITCHEN then HOME.")
                self.delivery_failed_or_canceled = True
                self.active_waypoint_names = ['kitchen', 'home']
                self.order_queue.clear()
                self.transition_to(FSMState.RETURN_KITCHEN)
                if self.goal_handle:
                    self.goal_handle.cancel_goal_async()
                else:
                    self.action_in_progress = False
                return

            if cancel_target in ['table1', 'table2', 'table3']:
                # Check if the cancelled table is in the list
                targets_to_check = [self.current_target] + self.active_waypoint_names
                if cancel_target in targets_to_check:
                    self.get_logger().warn(f"⚠️  CASE C: Skipping cancelled table '{cancel_target.upper()}'.")
                    self.delivery_failed_or_canceled = True
                    
                    # Remove it from active lists
                    if cancel_target in self.active_waypoint_names:
                        self.active_waypoint_names.remove(cancel_target)

                    if self.current_target == cancel_target:
                        self.skipping_current_table = True
                        if self.goal_handle:
                            self.goal_handle.cancel_goal_async()
                        else:
                            self.action_in_progress = False
                    else:
                        self.get_logger().info(f"✂️  Removed future target '{cancel_target.upper()}' from list. Continuing current delivery.")

        # Cancellations during Wait States
        if self.state == FSMState.WAIT_KITCHEN_CONFIRM:
            self.get_logger().warn("🛑  Cancelled while waiting at kitchen. Returning HOME.")
            self.active_waypoint_names = ['home']
            self.transition_to(FSMState.RETURN_HOME)

        elif self.state == FSMState.WAIT_TABLE_CONFIRM:
            if cancel_target in [self.current_target, 'all']:
                self.get_logger().warn(f"🛑  Cancelled while waiting at {self.current_target.upper()}.")
                self.delivery_failed_or_canceled = True
                if self.is_multi_delivery and self.active_waypoint_names:
                    # Proceed to the next table in multi-delivery
                    self.get_logger().info("⏭️  Proceeding to remaining multi-delivery targets.")
                    self.transition_to(FSMState.MULTI_DELIVERY)
                else:
                    # No more tables, return kitchen then home
                    self.active_waypoint_names = ['kitchen', 'home']
                    self.transition_to(FSMState.RETURN_KITCHEN)
            elif cancel_target in self.active_waypoint_names:
                self.get_logger().warn(f"🛑  Cancelled future target '{cancel_target.upper()}' while waiting at {self.current_target.upper()}.")
                self.delivery_failed_or_canceled = True
                self.active_waypoint_names.remove(cancel_target)

    def kitchen_confirm_callback(self, msg: String):
        """Processes kitchen confirmation to dispatch to tables."""
        if self.state == FSMState.WAIT_KITCHEN_CONFIRM:
            self.get_logger().info("✅  Kitchen confirmation received. Food collected!")
            if len(self.active_waypoint_names) > 1:
                self.is_multi_delivery = True
                self.transition_to(FSMState.MULTI_DELIVERY)
            else:
                self.is_multi_delivery = False
                self.transition_to(FSMState.GO_TO_TABLE)

    def table_confirm_callback(self, msg: String):
        """Processes table confirmations upon arrival."""
        table_id = msg.data.strip().lower()
        if self.state == FSMState.WAIT_TABLE_CONFIRM:
            if table_id == self.current_target:
                self.get_logger().info(f"✅  Table confirmation received for '{table_id.upper()}'. Food served!")
                
                # Check next actions
                if self.is_multi_delivery and self.active_waypoint_names:
                    # Proceed to the next table
                    self.transition_to(FSMState.MULTI_DELIVERY)
                elif self.is_multi_delivery:
                    # All multi-delivery targets completed
                    if self.delivery_failed_or_canceled:
                        self.get_logger().info("🏁  Multi-deliveries finished with some failures/cancellations. Returning KITCHEN then HOME.")
                        self.active_waypoint_names = ['kitchen', 'home']
                        self.transition_to(FSMState.RETURN_KITCHEN)
                    else:
                        self.get_logger().info("🏁  All multi-deliveries completed successfully. Returning HOME.")
                        self.active_waypoint_names = ['home']
                        self.transition_to(FSMState.RETURN_HOME)
                else:
                    # Single table complete
                    if self.delivery_failed_or_canceled:
                        self.get_logger().info("🏁  Single delivery finished with failure/cancellation. Returning KITCHEN then HOME.")
                        self.active_waypoint_names = ['kitchen', 'home']
                        self.transition_to(FSMState.RETURN_KITCHEN)
                    else:
                        self.get_logger().info("🏁  Single delivery completed successfully. Returning HOME.")
                        self.active_waypoint_names = ['home']
                        self.transition_to(FSMState.RETURN_HOME)
            else:
                self.get_logger().warn(f"⚠️  Received confirmation for '{table_id.upper()}' but currently at '{self.current_target.upper()}'.")

    # ── FSM Engine (Tick) ────────────────────────────────────────────

    def transition_to(self, new_state: FSMState):
        """Logs and processes FSM transitions."""
        self.get_logger().info(f"🔄  FSM Transition: {self.state.name} ➔ {new_state.name}")
        self.state = new_state

    def fsm_tick(self):
        """Periodic FSM tick executing state behaviors and publishing status."""
        # 1. Publish status representation
        status_msg = String()
        status_info = f"State: {self.state.name}"
        if self.current_target:
            status_info += f" | Target: {self.current_target.upper()}"
        if self.active_waypoint_names:
            status_info += f" | Queue: {self.active_waypoint_names}"
        
        status_msg.data = status_info
        self.status_pub.publish(status_msg)
        self.legacy_status_pub.publish(status_msg)

        # Dynamically read parameters
        self.require_confirmation = self.get_parameter('require_confirmation').value
        self.confirm_timeout = self.get_parameter('confirm_timeout').value

        # 2. State behavior logic
        if self.state == FSMState.IDLE:
            if self.order_queue:
                self.active_waypoint_names = list(self.order_queue)
                self.order_queue.clear()
                self.delivery_failed_or_canceled = False
                self.skipping_current_table = False
                self.transition_to(FSMState.GO_TO_KITCHEN)

        elif self.state == FSMState.GO_TO_KITCHEN:
            if not self.action_in_progress:
                self.current_target = 'kitchen'
                self.send_navigation_goal('kitchen')

        elif self.state == FSMState.WAIT_KITCHEN_CONFIRM:
            now = self.get_clock().now().nanoseconds / 1e9
            if not self.require_confirmation:
                if now - self.wait_start_time >= 2.0:
                    self.get_logger().info("✅  No confirmation required. Automatically proceeding from kitchen.")
                    if len(self.active_waypoint_names) > 1:
                        self.is_multi_delivery = True
                        self.transition_to(FSMState.MULTI_DELIVERY)
                    else:
                        self.is_multi_delivery = False
                        self.transition_to(FSMState.GO_TO_TABLE)
            else:
                # Check for kitchen confirmation timeout
                if now - self.wait_start_time > self.confirm_timeout:
                    self.get_logger().error("⏰  Kitchen confirmation TIMEOUT! Returning directly HOME.")
                    self.active_waypoint_names = ['home']
                    self.transition_to(FSMState.RETURN_HOME)

        elif self.state == FSMState.GO_TO_TABLE:
            if not self.action_in_progress:
                if self.active_waypoint_names:
                    self.current_target = self.active_waypoint_names.pop(0)
                    self.send_navigation_goal(self.current_target)
                else:
                    self.transition_to(FSMState.RETURN_HOME)

        elif self.state == FSMState.MULTI_DELIVERY:
            if not self.action_in_progress:
                if self.active_waypoint_names:
                    self.current_target = self.active_waypoint_names.pop(0)
                    self.send_navigation_goal(self.current_target)
                else:
                    # No more tables left in multi-delivery list
                    if self.delivery_failed_or_canceled:
                        self.get_logger().info("🏁  All tables visited. Returning KITCHEN then HOME.")
                        self.active_waypoint_names = ['kitchen', 'home']
                        self.transition_to(FSMState.RETURN_KITCHEN)
                    else:
                        self.get_logger().info("🏁  All tables visited successfully. Returning HOME.")
                        self.active_waypoint_names = ['home']
                        self.transition_to(FSMState.RETURN_HOME)

        elif self.state == FSMState.WAIT_TABLE_CONFIRM:
            now = self.get_clock().now().nanoseconds / 1e9
            if not self.require_confirmation:
                if now - self.wait_start_time >= 2.0:
                    self.get_logger().info(f"✅  No confirmation required at {self.current_target.upper()}. Food served!")
                    if self.is_multi_delivery and self.active_waypoint_names:
                        self.transition_to(FSMState.MULTI_DELIVERY)
                    elif self.is_multi_delivery:
                        if self.delivery_failed_or_canceled:
                            self.get_logger().info("🏁  Multi-deliveries finished with some failures/cancellations. Returning KITCHEN then HOME.")
                            self.active_waypoint_names = ['kitchen', 'home']
                            self.transition_to(FSMState.RETURN_KITCHEN)
                        else:
                            self.get_logger().info("🏁  All multi-deliveries completed successfully. Returning HOME.")
                            self.active_waypoint_names = ['home']
                            self.transition_to(FSMState.RETURN_HOME)
                    else:
                        if self.delivery_failed_or_canceled:
                            self.get_logger().info("🏁  Single delivery finished with failure/cancellation. Returning KITCHEN then HOME.")
                            self.active_waypoint_names = ['kitchen', 'home']
                            self.transition_to(FSMState.RETURN_KITCHEN)
                        else:
                            self.get_logger().info("🏁  Single delivery completed successfully. Returning HOME.")
                            self.active_waypoint_names = ['home']
                            self.transition_to(FSMState.RETURN_HOME)
            else:
                # Check for table confirmation timeout
                if now - self.wait_start_time > self.confirm_timeout:
                    self.get_logger().error(f"⏰  Table confirmation TIMEOUT at {self.current_target.upper()}!")
                    self.delivery_failed_or_canceled = True
                    if self.is_multi_delivery and self.active_waypoint_names:
                        self.get_logger().info("⏭️  Proceeding to remaining multi-delivery targets.")
                        self.transition_to(FSMState.MULTI_DELIVERY)
                    else:
                        self.get_logger().warn("🍳  No remaining tables. Returning KITCHEN then HOME.")
                        self.active_waypoint_names = ['kitchen', 'home']
                        self.transition_to(FSMState.RETURN_KITCHEN)

        elif self.state == FSMState.RETURN_KITCHEN:
            if not self.action_in_progress:
                if self.active_waypoint_names and self.active_waypoint_names[0] == 'kitchen':
                    self.active_waypoint_names.pop(0)
                self.current_target = 'kitchen'
                self.send_navigation_goal('kitchen')

        elif self.state == FSMState.RETURN_HOME:
            if not self.action_in_progress:
                if self.active_waypoint_names and self.active_waypoint_names[0] == 'home':
                    self.active_waypoint_names.pop(0)
                self.current_target = 'home'
                self.send_navigation_goal('home')

    # ── Action Client Implementations ────────────────────────────────

    def send_navigation_goal(self, target_name):
        """Sends a single navigation goal to the target location via NavigateToPose."""
        self.action_in_progress = True
        self.get_logger().info(f"🚚  Navigating to {target_name.upper()}...")

        # Resolve coordinates
        param_name = f"poses.{target_name}"
        try:
            coords = self.get_parameter(param_name).value
            if not coords or len(coords) < 4:
                raise ValueError("Insufficient coordinates")
            x, y, z, w = [float(val) for val in coords]
        except Exception as e:
            self.get_logger().error(f"❌  Cannot resolve coordinates for pose '{target_name}': {e}")
            self.action_in_progress = False
            self.handle_navigation_failure()
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.orientation.z = z
        goal_msg.pose.pose.orientation.w = w

        self.action_future = self.nav_client.send_goal_async(
            goal_msg, feedback_callback=self.navigation_feedback_callback)
        self.action_future.add_done_callback(self.navigation_response_callback)

    def navigation_feedback_callback(self, feedback_msg):
        """Callback triggered by Nav2 with tracking information."""
        feedback = feedback_msg.feedback
        dist = feedback.distance_remaining
        self.get_logger().info(f"📈  Distance remaining to {self.current_target.upper()}: {dist:.2f}m", throttle_duration_sec=3.0)

    def navigation_response_callback(self, future: Future):
        """Callback for goal acceptance/rejection."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error(f"❌  Goal to {self.current_target.upper()} was rejected by Nav2!")
            self.action_in_progress = False
            self.handle_navigation_failure()
            return

        self.goal_handle = goal_handle
        
        self.result_future = goal_handle.get_result_async()
        self.result_future.add_done_callback(self.navigation_result_callback)

    def navigation_result_callback(self, future: Future):
        """Callback for goal execution result."""
        result = future.result()
        status = result.status
        self.action_in_progress = False
        self.goal_handle = None

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f"🏁  Arrived at {self.current_target.upper()} successfully!")
            self.handle_navigation_success()
        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().warn(f"⚠️  Goal to {self.current_target.upper()} was cancelled.")
            self.handle_navigation_cancelled()
        else:
            self.get_logger().error(f"❌  Goal to {self.current_target.upper()} failed with status: {status}")
            self.handle_navigation_failure()

    # ── State Navigation Success/Failure/Cancel Handlers ────────────

    def handle_navigation_success(self):
        """Handles state transitions on successful navigation arrival."""
        if self.state == FSMState.GO_TO_KITCHEN:
            self.wait_start_time = self.get_clock().now().nanoseconds / 1e9
            self.transition_to(FSMState.WAIT_KITCHEN_CONFIRM)

        elif self.state in [FSMState.GO_TO_TABLE, FSMState.MULTI_DELIVERY]:
            self.wait_start_time = self.get_clock().now().nanoseconds / 1e9
            self.transition_to(FSMState.WAIT_TABLE_CONFIRM)

        elif self.state == FSMState.RETURN_KITCHEN:
            self.transition_to(FSMState.RETURN_HOME)

        elif self.state == FSMState.RETURN_HOME:
            self.current_target = None
            self.transition_to(FSMState.IDLE)

    def handle_navigation_cancelled(self):
        """Handles state transitions when navigation gets cancelled."""
        skipping = self.skipping_current_table
        self.skipping_current_table = False

        if skipping:
            self.get_logger().info(f"⏭️  Successfully skipped table '{self.current_target.upper()}'.")
            if self.active_waypoint_names:
                self.transition_to(FSMState.MULTI_DELIVERY)
            else:
                self.get_logger().warn("🍳  No remaining tables. Returning KITCHEN then HOME.")
                self.active_waypoint_names = ['kitchen', 'home']
                self.transition_to(FSMState.RETURN_KITCHEN)

    def handle_navigation_failure(self):
        """Fallbacks to returning home in case of failures."""
        self.get_logger().error(f"❌  Navigation failed during state {self.state.name}. Returning HOME.")
        self.active_waypoint_names = ['home']
        self.transition_to(FSMState.RETURN_HOME)


def main(args=None):
    rclpy.init(args=args)
    node = CafeRobotNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("🛑  FSM Node shutdown requested via KeyboardInterrupt.")
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
