#!/usr/bin/env python3
"""flight_control_node — convertit sensor_msgs/Joy en RC override ArduPilot.

Mapping (Mode 2 DJI — stick gauche = gaz/lacet, stick droit = tangage/roulis) :
    RC1  Roll    <- axes[2]  (RX)  stick droit horizontal
    RC2  Pitch   <- axes[3]  (RY)  stick droit vertical
    RC3  Throttle<- axes[1]  (LY)  stick gauche vertical
    RC4  Yaw     <- axes[0]  (LX)  stick gauche horizontal
    RC5  Mode    <- molette caméra (axes[4]) : fond gauche / fond droit

Chaque valeur est convertie de [-1,1] en [1000,2000] (centre 1500), la plage
attendue par mavros_msgs/OverrideRCIn.

Node ROS2. Paramètres :
    rate_hz      (int, 50)  cadence de publication
    rc_override  (str, "/mavros/rc/override")
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from mavros_msgs.msg import OverrideRCIn


def _to_pwm(v):
    """[-1, 1] -> [1000, 2000]"""
    return int(1500 + v * 500)


class FlightControl(Node):
    def __init__(self):
        super().__init__('flight_control')
        self.declare_parameter('rate_hz', 50)
        self.declare_parameter('rc_override', '/mavros/rc/override')
        rate = self.get_parameter('rate_hz').value

        self.sub = self.create_subscription(Joy, '/joy', self._on_joy, 1)
        self.pub = self.create_publisher(OverrideRCIn,
                                         self.get_parameter('rc_override').value, 10)

        # Dernier état reçu ; RC désactivé au démarrage (1500 = neutre, 0 = pas d'override)
        self.axes = [0.0] * 5
        self.armed = False
        self.timer = self.create_timer(1.0 / rate, self._publish)
        self.get_logger().info('flight_control prêt (50 Hz)')

    def _on_joy(self, msg):
        if len(msg.axes) >= 4:
            self.axes = list(msg.axes[:5])
        # petit débounce : si tous les sticks sont au centre depuis le boot, on attend
        # une première entrée non neutre pour armer la commande
        if not self.armed and any(abs(a) > 0.05 for a in self.axes[:4]):
            self.armed = True
            self.get_logger().info('Première commande manette reçue, RC override actif.')

    def _publish(self):
        if not self.armed:
            return
        msg = OverrideRCIn()
        msg.channels[0] = _to_pwm(self.axes[2])  # roll     <- stick droit horizontal (RX)
        msg.channels[1] = _to_pwm(self.axes[3])  # pitch    <- stick droit vertical (RY)
        msg.channels[2] = _to_pwm(self.axes[1])  # throttle <- stick gauche vertical (LY)
        msg.channels[3] = _to_pwm(self.axes[0])  # yaw      <- stick gauche horizontal (LX)
        # molette caméra -> canal 5 (mode de vol), centre = 1500
        cam = self.axes[4]
        if cam > 0.7:
            msg.channels[4] = 1600
        elif cam < -0.7:
            msg.channels[4] = 1400
        else:
            msg.channels[4] = 1500
        # canaux restants à 0 = pas d'override sur ces canaux
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = FlightControl()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
