#!/usr/bin/env python3
"""joy_bridge_node — reçoit les sticks de la RC-N1 en UDP et publie /joy.

Protocole UDP : un datagramme JSON par paquet, ex.
    {"lx": 0, "ly": 0, "rx": 0, "ry": 0, "cam": 0}

Les valeurs DJI (±32767) sont normalisées en [-1.0, 1.0] dans sensor_msgs/Joy.
Axes publiés :  [lx, ly, rx, ry, cam]
Boutons :       [] (les boutons physiques ne sont pas lus pour l'instant)

Node ROS2. Paramètres :
    udp_port   (int, 7777)  port UDP en écoute
    topic      (str, "/joy")
"""

import json
import socket

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy

MAX_DJI = 32767.0


class JoyBridge(Node):
    def __init__(self):
        super().__init__('joy_bridge')
        self.declare_parameter('udp_port', 7777)
        self.declare_parameter('topic', '/joy')
        port = self.get_parameter('udp_port').value
        topic = self.get_parameter('topic').value

        self.pub = self.create_publisher(Joy, topic, 10)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', port))
        self.sock.setblocking(False)
        self.get_logger().info(f'En écoute UDP sur le port {port} -> topic {topic}')

        self.timer = self.create_timer(0.005, self._poll)  # 200 Hz

    def _poll(self):
        try:
            data, _ = self.sock.recvfrom(2048)
        except BlockingIOError:
            return
        try:
            st = json.loads(data.decode())
        except (ValueError, UnicodeDecodeError):
            return

        msg = Joy()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.axes = [
            st.get('lx', 0) / MAX_DJI,
            st.get('ly', 0) / MAX_DJI,
            st.get('rx', 0) / MAX_DJI,
            st.get('ry', 0) / MAX_DJI,
            st.get('cam', 0) / MAX_DJI,
        ]
        msg.buttons = []
        self.pub.publish(msg)

    def destroy_node(self):
        self.sock.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = JoyBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
