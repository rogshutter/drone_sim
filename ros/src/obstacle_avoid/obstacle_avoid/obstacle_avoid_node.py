#!/usr/bin/env python3
"""Exemple d'évitement d'obstacle.

Principe (le pattern "sentir -> décider -> commander") :
    1. SENTIR   : écoute un télémètre avant (topic sensor_msgs/Range "/range/forward")
    2. DÉCIDER  : si un obstacle est trop proche, on recule ; sinon on avance
    3. COMMANDER: publie une consigne de vitesse sur /mavros/setpoint_velocity/cmd_vel

Pour que l'autopilote suive ces consignes, il faut être en mode OFFBOARD (voir la
documentation docs/ECRIRE_SES_SCRIPTS.md). Deux services sont exposés pour ça :
    ros2 service call /obstacle_avoid/arm std_srvs/srv/SetBool "{data: true}"
    ros2 service call /obstacle_avoid/offboard std_srvs/srv/SetBool "{data: true}"

Paramètres (réglables à la volée) :
    forward_speed  (float, 2.0)  vitesse d'avance (m/s)
    safe_distance  (float, 3.0)  distance déclenchant l'évitement (m)
    avoid_speed    (float, 1.0)  vitesse de recul (m/s)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Range
from geometry_msgs.msg import TwistStamped
from mavros_msgs.srv import SetMode, CommandBool
from std_srvs.srv import SetBool


class ObstacleAvoid(Node):
    def __init__(self):
        super().__init__('obstacle_avoid')
        self.declare_parameter('forward_speed', 2.0)
        self.declare_parameter('safe_distance', 3.0)
        self.declare_parameter('avoid_speed', 1.0)

        self.distance = float('inf')  # pas d'obstacle tant qu'on n'a rien mesuré

        # SENTIR : télémètre avant (Gazebo ou simulé via `ros2 topic pub`)
        self.create_subscription(Range, '/range/forward', self._on_range,
                                 qos_profile_sensor_data)

        # COMMANDER : consigne de vitesse -> MAVROS -> ArduPilot (mode OFFBOARD)
        self.cmd_pub = self.create_publisher(TwistStamped, '/mavros/setpoint_velocity/cmd_vel', 10)

        # Services : armer + passer en OFFBOARD
        self.srv_arm = self.create_service(SetBool, 'arm', self._arm)
        self.srv_offboard = self.create_service(SetBool, 'offboard', self._offboard)

        # Boucle de commande à 10 Hz
        self.create_timer(0.1, self._command)

        self.get_logger().info(
            'obstacle_avoid prêt. Pour voler : '
            'service arm, service offboard, puis ros2 topic pub /range/forward ...')

    # --- SENTIR ---
    def _on_range(self, msg):
        # sensor_msgs/Range : champ `range` en mètres
        self.distance = msg.range

    # --- DÉCIDER + COMMANDER ---
    def _command(self):
        sp = TwistStamped()
        sp.header.stamp = self.get_clock().now().to_msg()
        sp.header.frame_id = 'map'

        fs = self.get_parameter('forward_speed').value
        sd = self.get_parameter('safe_distance').value
        av = self.get_parameter('avoid_speed').value

        if self.distance < sd:
            # obstacle proche : reculer (vitesse négative) et garder l'altitude
            sp.twist.linear.x = -av
            self.get_logger().info(f'Obstacle à {self.distance:.2f} m -> recul', throttle_duration_sec=0.5)
        else:
            # voie libre : avancer
            sp.twist.linear.x = fs
        self.cmd_pub.publish(sp)

    # --- Services de mise en route ---
    def _arm(self, req, res):
        cli = self.create_client(CommandBool, '/mavros/cmd/arming')
        if not cli.wait_for_service(timeout_sec=2.0):
            res.success = False
            res.message = 'service /mavros/cmd/arming indisponible'
            return res
        call = cli.call_async(CommandBool.Request(value=req.data))
        rclpy.spin_until_future_complete(self, call)
        res.success = call.result().success
        res.message = 'arm' if req.data else 'disarm'
        return res

    def _offboard(self, req, res):
        cli = self.create_client(SetMode, '/mavros/set_mode')
        if not cli.wait_for_service(timeout_sec=2.0):
            res.success = False
            res.message = 'service /mavros/set_mode indisponible'
            return res
        mode = 'OFFBOARD' if req.data else 'STABILIZE'
        call = cli.call_async(SetMode.Request(custom_mode=mode))
        rclpy.spin_until_future_complete(self, call)
        res.success = call.result().mode_sent
        res.message = f'mode {mode}'
        return res


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleAvoid()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
