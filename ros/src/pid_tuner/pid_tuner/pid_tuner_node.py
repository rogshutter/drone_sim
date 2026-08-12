#!/usr/bin/env python3
"""pid_tuner_node — régler les gains PID d'ArduPilot en direct depuis ROS2.

L'étudiant change un paramètre ROS2, il est appliqué immédiatement à l'autopilote
via le service MAVROS /mavros/param/set. Le drone réagit dans Gazebo/QGC.

Exemples :
    ros2 param set /pid_tuner ATC_RAT_PIT_P 6.0
    ros2 param set /pid_tuner ATC_RAT_PIT_D 0.02
    ros2 param get  /pid_tuner ATC_RAT_PIT_P

Paramètres déclarés (gains cascade ArduPilot, cf. chapitre 2.12 du corpus) :
    ATC_ANG_PIT_P / ATC_ANG_ROL_P : boucle extérieure (angle)
    ATC_RAT_PIT_P / I / D          : boucle intérieure (vitesse de rotation), tangage
    ATC_RAT_ROL_P / I / D          : roulis
    ATC_RAT_YAW_P / I / D          : lacet
    INS_GYRO_FILTER                : fréquence de coupure du filtre gyro (chapitre 2.8)
"""

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from mavros_msgs.srv import ParamSet, ParamGet
from geometry_msgs.msg import PoseStamped

# paramètre ArduPilot -> valeur par défaut indicative (iris SITL)
DEFAULTS = {
    'ATC_ANG_PIT_P': 6.0,
    'ATC_ANG_ROL_P': 6.0,
    'ATC_RAT_PIT_P': 0.135,
    'ATC_RAT_PIT_I': 0.135,
    'ATC_RAT_PIT_D': 0.0036,
    'ATC_RAT_ROL_P': 0.135,
    'ATC_RAT_ROL_I': 0.135,
    'ATC_RAT_ROL_D': 0.0036,
    'ATC_RAT_YAW_P': 0.2,
    'ATC_RAT_YAW_I': 0.1,
    'ATC_RAT_YAW_D': 0.0,
    'INS_GYRO_FILTER': 90.0,
}


class PidTuner(Node):
    def __init__(self):
        super().__init__('pid_tuner')

        for name, default in DEFAULTS.items():
            self.declare_parameter(name, default)

        # Services MAVROS
        self.srv_set = self.create_client(ParamSet, '/mavros/param/set')
        self.srv_get = self.create_client(ParamGet, '/mavros/param/get')
        self.get_logger().info('pid_tuner prêt. Ex. : ros2 param set /pid_tuner ATC_RAT_PIT_P 6.0')

        # Retour visuel : attitude du drone (pour voir la réaction)
        self.attitude = None
        self.create_subscription(PoseStamped, '/mavros/local_position/pose', self._on_pose, 10)
        self.create_timer(1.0, self._status)

        # Applique les valeurs d'origine depuis l'autopilote après un court délai (une fois)
        self._pull_timer = self.create_timer(3.0, self._pull_defaults)

    def _on_pose(self, msg):
        self.attitude = msg

    def _pull_defaults(self):
        self._pull_timer.cancel()  # une seule passe
        for name in DEFAULTS:
            if not self.srv_get.wait_for_service(timeout_sec=0.2):
                continue
            req = ParamGet.Request()
            req.param_id = name
            fut = self.srv_get.call_async(req)
            fut.add_done_callback(lambda f, n=name: self._got_value(n, f))

    def _got_value(self, name, future):
        try:
            res = future.result()
            if res.success:
                val = res.value.real if res.value.integer == 0 else float(res.value.integer)
                if val > 0:
                    self.set_parameters([Parameter(name, value=val)])
                    self.get_logger().info(f'{name} lu depuis ArduPilot : {val}')
        except Exception:
            pass

    def set_parameters(self, params):
        """Intercepte les modifications de paramètres pour les pousser vers ArduPilot."""
        result = super().set_parameters(params)
        for p in params:
            if p.name in DEFAULTS and self.srv_set.wait_for_service(timeout_sec=0.5):
                req = ParamSet.Request()
                req.param_id = p.name
                req.value.real = float(p.value)
                self.srv_set.call_async(req)
                self.get_logger().info(f'PID appliqué : {p.name} = {p.value}')
        return result

    def _status(self):
        a = self.attitude
        if a is not None:
            r, p, y = a.pose.orientation.x, a.pose.orientation.y, a.pose.orientation.z
            self.get_logger().info(f'attitude r/p/y = {r:+.2f} {p:+.2f} {y:+.2f}', throttle_duration_sec=2.0)
        else:
            self.get_logger().info('en attente de l\'attitude du drone ...', throttle_duration_sec=5.0)


def main(args=None):
    rclpy.init(args=args)
    node = PidTuner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
