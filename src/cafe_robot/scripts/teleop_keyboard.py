#!/usr/bin/env python3
"""
teleop_keyboard.py — Simple keyboard teleoperation script for the café robot.

Usage:
    ros2 run cafe_robot teleop_keyboard.py
    OR
    python3 scripts/teleop_keyboard.py

Controls:
    w/x : increase/decrease linear velocity
    a/d : increase/decrease angular velocity
    s   : stop all motion
    q   : quit
"""

import sys
import termios
import tty

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

HELP_MSG = """
╔══════════════════════════════════════╗
║    ☕  Café Robot Teleop Keyboard    ║
╠══════════════════════════════════════╣
║                                      ║
║          w — forward                 ║
║    a — left    d — right             ║
║          x — backward                ║
║          s — stop                    ║
║          q — quit                    ║
║                                      ║
╚══════════════════════════════════════╝
"""

LINEAR_STEP = 0.05   # m/s per keypress
ANGULAR_STEP = 0.1   # rad/s per keypress
MAX_LINEAR = 0.5
MAX_ANGULAR = 2.0


def get_key():
    """Read a single keypress from stdin (blocking)."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


class TeleopKeyboard(Node):
    def __init__(self):
        super().__init__('teleop_keyboard')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.linear = 0.0
        self.angular = 0.0

    def run(self):
        print(HELP_MSG)
        try:
            while True:
                key = get_key()
                if key == 'w':
                    self.linear = min(self.linear + LINEAR_STEP, MAX_LINEAR)
                elif key == 'x':
                    self.linear = max(self.linear - LINEAR_STEP, -MAX_LINEAR)
                elif key == 'a':
                    self.angular = min(self.angular + ANGULAR_STEP, MAX_ANGULAR)
                elif key == 'd':
                    self.angular = max(self.angular - ANGULAR_STEP, -MAX_ANGULAR)
                elif key == 's':
                    self.linear = 0.0
                    self.angular = 0.0
                elif key == 'q' or key == '\x03':  # q or Ctrl-C
                    break

                twist = Twist()
                twist.linear.x = self.linear
                twist.angular.z = self.angular
                self.pub.publish(twist)

                self.get_logger().info(
                    f'linear={self.linear:.2f} angular={self.angular:.2f}')
        except Exception as e:
            self.get_logger().error(f'Error: {e}')
        finally:
            # Stop the robot
            self.pub.publish(Twist())


def main(args=None):
    rclpy.init(args=args)
    node = TeleopKeyboard()
    node.run()
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
