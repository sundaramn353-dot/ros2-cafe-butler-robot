#!/usr/bin/env python3
"""
cafe_operator_node.py — Interactive Operator CLI Node for Cafe Butler Robot.
Publishes commands based on terminal input and displays robot status.
"""

import sys
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class CafeOperatorNode(Node):
    """
    ROS 2 Node providing a CLI interface to control the Cafe Butler Robot.
    """

    def __init__(self):
        super().__init__('cafe_operator_node')

        # ── Publishers ───────────────────────────────────────────────
        self.new_order_pub = self.create_publisher(String, '/new_order', 10)
        self.cancel_order_pub = self.create_publisher(String, '/cancel_order', 10)
        self.kitchen_confirm_pub = self.create_publisher(String, '/kitchen_confirm', 10)
        self.table_confirm_pub = self.create_publisher(String, '/table_confirm', 10)

        # ── Subscriber ───────────────────────────────────────────────
        self.status_sub = self.create_subscription(
            String, '/robot_status', self.status_callback, 10)

        self.last_status_msg = ""
        self.get_logger().info("☕  Cafe Operator Terminal Node initialized.")

    def status_callback(self, msg: String):
        """Prints the robot status when it changes."""
        status_text = msg.data.strip()
        if status_text != self.last_status_msg:
            self.last_status_msg = status_text
            # Print status cleanly to terminal
            print(f"\n[STATUS UPDATE] {status_text}")
            print("operator > ", end="", flush=True)

    def run_cli_loop(self):
        """Continuously reads user inputs from the terminal in a loop."""
        print("\n" + "="*65)
        print("☕  FRENCH CAFE ROBOT - DISPATCH & OPERATOR CONTROL TERMINAL")
        print("="*65)
        print("Supported Commands:")
        print("  - order <table_id(s)>  (e.g., 'order table1', 'order table1 table2 table3')")
        print("  - cancel <table_id>    (e.g., 'cancel table1')")
        print("  - confirm kitchen      (confirm food collected at kitchen)")
        print("  - confirm <table_id>   (confirm food served at table)")
        print("  - status               (print current robot status)")
        print("  - exit                 (quit the operator node)")
        print("="*65)

        while rclpy.ok():
            try:
                user_input = input("operator > ").strip().lower()
                if not user_input:
                    continue
                
                if user_input == 'exit':
                    print("🚪  Shutting down operator terminal...")
                    break
                
                parts = user_input.split(maxsplit=1)
                cmd = parts[0]
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "order":
                    # Split arg by spaces or commas to support multiple tables
                    tables = [t.strip().lower() for t in arg.replace(',', ' ').split() if t.strip()]
                    valid_tables = ["table1", "table2", "table3"]
                    
                    invalid = [t for t in tables if t not in valid_tables]
                    if invalid:
                        print(f"❌  Invalid table ID(s): {invalid}. Available: table1, table2, table3.")
                    elif not tables:
                        print("❌  Please specify at least one table. E.g. 'order table1 table2'")
                    else:
                        for table in tables:
                            msg = String()
                            msg.data = table
                            self.new_order_pub.publish(msg)
                            self.get_logger().info(f"Published order request for: '{table.upper()}'")
                
                elif cmd == "cancel":
                    if arg in ["table1", "table2", "table3", "all"]:
                        msg = String()
                        msg.data = arg
                        self.cancel_order_pub.publish(msg)
                        self.get_logger().info(f"Published cancel request for: '{arg.upper()}'")
                    else:
                        print(f"❌  Invalid cancel target: '{arg}'. Use table1, table2, table3, or 'all'.")

                elif cmd == "confirm":
                    if arg == "kitchen":
                        msg = String()
                        msg.data = "confirm"
                        self.kitchen_confirm_pub.publish(msg)
                        self.get_logger().info("Published KITCHEN confirmation.")
                    elif arg in ["table1", "table2", "table3"]:
                        msg = String()
                        msg.data = arg
                        self.table_confirm_pub.publish(msg)
                        self.get_logger().info(f"Published confirmation for: '{arg.upper()}'")
                    else:
                        print(f"❌  Invalid confirmation target: '{arg}'. Use 'kitchen', 'table1', 'table2', 'table3'.")

                elif cmd == "status":
                    if self.last_status_msg:
                        print(f"\n[CURRENT STATUS] {self.last_status_msg}")
                    else:
                        print("\n[INFO] Waiting for robot status publication...")

                else:
                    print(f"❌  Unknown command: '{cmd}'. Try 'order', 'cancel', 'confirm', or 'status'.")

            except (KeyboardInterrupt, EOFError):
                print("\n🚪  Shutting down operator terminal...")
                break


def main(args=None):
    rclpy.init(args=args)
    node = CafeOperatorNode()

    # Spin the node in a background thread to receive callbacks/status updates
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    # Run the interactive CLI loop in the main thread
    node.run_cli_loop()

    # Clean shutdown
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
