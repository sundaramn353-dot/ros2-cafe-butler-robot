#!/usr/bin/env python3
"""
cancel_order.py — Interactive CLI tool to cancel cafe_robot orders from the terminal.

Usage:
    ros2 run cafe_robot cancel_order
"""

import sys
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class CancelOrderCLI(Node):
    """
    ROS 2 Node that provides an interactive CLI to publish cancellation requests.
    """

    def __init__(self):
        super().__init__('cancel_order_cli')
        self.cancel_pub = self.create_publisher(String, '/cafe_robot/cancel', 10)
        self.get_logger().info("☕  Interactive Cancel Order CLI initialized.")

    def run(self):
        print("\n" + "="*55)
        print("☕  FRENCH CAFE ROBOT - INTERACTIVE CANCELLATION TERMINAL")
        print("="*55)
        print("Instructions:")
        print("  - Type table name to cancel (e.g., 'table1', 'table2', 'table3')")
        print("  - Type 'all' or 'cancel' to cancel the entire active run")
        print("  - Type 'exit' to quit this terminal")
        print("="*55)

        while rclpy.ok():
            try:
                user_input = input("\nEnter order/table to cancel > ").strip().lower()
                if user_input == 'exit':
                    print("🚪  Exiting interactive cancel terminal.")
                    break
                if not user_input:
                    continue

                # Publish message to cancellation topic
                msg = String()
                msg.data = user_input
                self.cancel_pub.publish(msg)
                print(f"📢  Published cancellation request for: '{user_input.upper()}'")
            except (KeyboardInterrupt, EOFError):
                print("\n🚪  Exiting interactive cancel terminal.")
                break


def main(args=None):
    rclpy.init(args=args)
    node = CancelOrderCLI()
    
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
