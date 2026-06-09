#!/usr/bin/env python3
"""
test_single_delivery.py — Automated Test Script for Single Delivery Workflow.

Triggers Test Case 1 (HOME → KITCHEN → TABLE → HOME):
  1. Monitors /cafe_robot/status to detect when the FSM node is ready (IDLE state).
  2. Publishes an order (default: table1) to /cafe_robot/order.
  3. Displays real-time progress of states and confirmations.
  4. Exits once the robot successfully returns to IDLE state at HOME.

Usage:
    python3 src/cafe_robot/scripts/test_single_delivery.py --target table1
"""

import sys
import argparse
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class DeliveryTester(Node):
    """
    ROS 2 Node to automate and monitor the Single Delivery Workflow test case.
    """

    def __init__(self, target_table: str):
        super().__init__('delivery_tester')
        self.target_table = target_table
        self.last_state = None
        self.fsm_ready = False
        self.workflow_started = False
        self.workflow_completed = False

        # ── Publishers & Subscribers ─────────────────────────────────
        self.order_pub = self.create_publisher(String, '/cafe_robot/order', 10)
        self.status_sub = self.create_subscription(
            String, '/cafe_robot/status', self.status_callback, 10)

        # Watchdog timer (runs at 1Hz)
        self.timer_count = 0
        self.watchdog_timer = self.create_timer(1.0, self.watchdog_tick)

        self.get_logger().info(f"🧪  Single Delivery Workflow Test initialized. Target: '{self.target_table}'")
        print(f"\n🚀  Starting test case: HOME ➔ KITCHEN ➔ {self.target_table.upper()} ➔ HOME")
        print("="*65)
        print("⏳  Waiting for FSM Node to initialize and become ready...")

    def watchdog_tick(self):
        """Warns the user if FSM initialization is taking a while."""
        if self.fsm_ready or self.workflow_started:
            self.watchdog_timer.cancel()
            return

        self.timer_count += 1
        if self.timer_count >= 15:
            print("\n⚠️  Warning: FSM Node is taking longer than expected to become ready.")
            print("💡  Make sure you launched 'cafe_bringup_launch.py' and 'cafe_robot_node' is running.\n")
            self.timer_count = 0

    def send_order(self):
        """Sends the target order to start the workflow."""
        msg = String()
        msg.data = self.target_table
        self.order_pub.publish(msg)
        
        self.get_logger().info(f"📢  Published order for target table: '{self.target_table}'")
        self.workflow_started = True

    def status_callback(self, msg: String):
        """Monitors and prints FSM transitions in real-time."""
        status_text = msg.data
        
        # Parse state from status string: "State: <STATE> | ..."
        try:
            state_part = status_text.split('|')[0].replace('State:', '').strip()
        except IndexError:
            return

        if state_part != self.last_state:
            self.last_state = state_part
            print(f"🔹 [FSM Status Update] State: {state_part}")
            
            # Watch for FSM becoming ready
            if not self.fsm_ready and state_part == "IDLE":
                self.fsm_ready = True
                print("✅  FSM Node is ready! Dispatching order...")
                # Schedule order publication after a brief delay
                self.create_timer(1.0, self.send_order)

            # Watch for completion condition
            if self.workflow_started:
                if state_part == "IDLE":
                    print("="*65)
                    print(f"🎉  TEST SUCCESS: Robot arrived back at HOME in IDLE state!")
                    print("="*65)
                    self.workflow_completed = True
                    rclpy.shutdown()
                elif state_part == "CANCELLED":
                    print("="*65)
                    print(f"⚠️  TEST FAILED: Workflow cancelled / aborted!")
                    print("="*65)
                    self.workflow_completed = True
                    rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Test Single Delivery Workflow.")
    parser.add_argument('--target', type=str, default='table1', 
                        choices=['table1', 'table2', 'table3'],
                        help="Target table ID (default: table1)")
    
    # Strip ROS 2 arguments from parser args
    args, unknown = parser.parse_known_args()

    rclpy.init()
    node = DeliveryTester(args.target)

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        print("\n🛑  Test interrupted.")
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
