#!/usr/bin/env python3
"""flight_control_node — sticks RC-N1 -> vol façon DJI (ArduPilot via MAVROS).

Deux rôles :

1) PILOTAGE MANUEL (comme une vraie radio DJI)
   sensor_msgs/Joy -> mavros_msgs/OverrideRCIn, mapping Mode 2 :
       RC1  Roll     <- axes[2] (RX)  stick droit horizontal
       RC2  Pitch    <- axes[3] (RY)  stick droit vertical
       RC3  Throttle <- axes[1] (LY)  stick gauche vertical
       RC4  Yaw      <- axes[0] (LX)  stick gauche horizontal
   Chaque valeur [-1,1] -> [1000,2000] (centre 1500).

2) DÉCOLLAGE / ARRÊT PAR GESTE « V » (DJI CSC)
   Le geste « V » = les DEUX sticks poussés vers le BAS et l'un vers l'AUTRE
   (coins intérieurs), maintenu ~1,2 s. Comme sur DJI :
       - au sol (désarmé) -> passe en GUIDED, arme, décolle (takeoff_alt),
         puis bascule en LOITER : les sticks pilotent façon DJI (lâcher = vol
         stationnaire).
       - en vol           -> passe en LAND : atterrissage + désarmement auto.

   Machine à états : DISARMED -> ARMING -> TAKEOFF -> FLYING -> LANDING -> ...

Le geste est volontairement robuste au signe (gauche/droite selon la radio) :
on exige seulement les deux verticaux en butée basse ET les deux horizontaux
en butée de signes opposés (la forme en V). Ajustez les seuils si besoin.

Node ROS2. Paramètres :
    rate_hz            (int,   50)       cadence de publication
    rc_override        (str, "/mavros/rc/override")
    takeoff_alt        (float, 2.5)      altitude de décollage (m)
    fly_mode           (str, "LOITER")   mode de vol après décollage (DJI-like)
    gesture_hold_s     (float, 1.2)      durée de maintien du geste « V »
    gesture_cooldown_s (float, 3.0)      délai anti-rebond entre deux gestes
    v_down_thresh      (float, 0.85)     seuil « stick vers le bas »
    v_side_thresh      (float, 0.6)      seuil « stick sur le côté »
"""

import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Float64
from mavros_msgs.msg import OverrideRCIn, State
from mavros_msgs.srv import SetMode, CommandBool, CommandTOL


def _to_pwm(v):
    """[-1, 1] -> [1000, 2000]"""
    return int(1500 + max(-1.0, min(1.0, v)) * 500)


# États de la machine
DISARMED = 'DISARMED'   # au sol, moteurs coupés — en attente du geste « V »
ARMING = 'ARMING'       # séquence GUIDED -> arm -> takeoff
TAKEOFF = 'TAKEOFF'     # montée jusqu'à takeoff_alt
FLYING = 'FLYING'       # vol piloté aux sticks (LOITER)
LANDING = 'LANDING'     # atterrissage automatique (LAND)


class FlightControl(Node):
    def __init__(self):
        super().__init__('flight_control')
        self.declare_parameter('rate_hz', 50)
        self.declare_parameter('rc_override', '/mavros/rc/override')
        self.declare_parameter('takeoff_alt', 2.5)
        self.declare_parameter('fly_mode', 'LOITER')
        self.declare_parameter('gesture_hold_s', 1.2)
        self.declare_parameter('gesture_cooldown_s', 3.0)
        self.declare_parameter('v_down_thresh', 0.85)
        self.declare_parameter('v_side_thresh', 0.6)

        rate = self.get_parameter('rate_hz').value
        self.takeoff_alt = float(self.get_parameter('takeoff_alt').value)
        self.fly_mode = self.get_parameter('fly_mode').value
        self.gesture_hold_s = float(self.get_parameter('gesture_hold_s').value)
        self.gesture_cooldown_s = float(self.get_parameter('gesture_cooldown_s').value)
        self.v_down = float(self.get_parameter('v_down_thresh').value)
        self.v_side = float(self.get_parameter('v_side_thresh').value)

        # Entrées / sorties
        self.sub_joy = self.create_subscription(Joy, '/joy', self._on_joy, 1)
        self.sub_state = self.create_subscription(State, '/mavros/state', self._on_state, 10)
        self.sub_alt = self.create_subscription(
            Float64, '/mavros/global_position/rel_alt', self._on_alt, 10)
        self.pub_rc = self.create_publisher(
            OverrideRCIn, self.get_parameter('rc_override').value, 10)

        # Services MAVROS (arm/désarm, changement de mode, décollage)
        self.cli_mode = self.create_client(SetMode, '/mavros/set_mode')
        self.cli_arm = self.create_client(CommandBool, '/mavros/cmd/arming')
        self.cli_takeoff = self.create_client(CommandTOL, '/mavros/cmd/takeoff')

        # État interne
        self.axes = [0.0] * 5
        self.mav = State()            # dernier /mavros/state
        self.rel_alt = 0.0            # altitude relative (m)
        self.phase = DISARMED
        self.rc_live = False          # override actif seulement quand throttle recentré
        self._g_start = None          # début du maintien du geste
        self._cooldown_until = 0.0    # anti-rebond
        self._cmd_stamp = 0.0         # throttle des appels de service

        self.timer = self.create_timer(1.0 / rate, self._tick)
        self.get_logger().info(
            'flight_control prêt (façon DJI). Geste « V » (deux sticks en bas, '
            'vers l\'intérieur) : décolle au sol, atterrit en vol.')

    # ------------------------------------------------------------------ entrées
    def _on_joy(self, msg):
        if len(msg.axes) >= 4:
            self.axes = list(msg.axes[:5]) + [0.0] * max(0, 5 - len(msg.axes))

    def _on_state(self, msg):
        self.mav = msg

    def _on_alt(self, msg):
        self.rel_alt = float(msg.data)

    # --------------------------------------------------------------- geste « V »
    def _v_shape(self):
        """Vrai si les sticks forment un « V » : verticaux bas + horizontaux
        en butée de signes opposés (l'un vers l'autre)."""
        lx, ly, rx, ry = self.axes[0], self.axes[1], self.axes[2], self.axes[3]
        both_down = (ly < -self.v_down) and (ry < -self.v_down)
        sides = (abs(lx) > self.v_side) and (abs(rx) > self.v_side) and (lx * rx < 0)
        return both_down and sides

    def _gesture_fired(self, now):
        """Vrai UNE fois quand le « V » est maintenu assez longtemps (et hors
        anti-rebond). Réarme le cooldown."""
        if self._v_shape():
            if self._g_start is None:
                self._g_start = now
            if (now - self._g_start) >= self.gesture_hold_s and now >= self._cooldown_until:
                self._cooldown_until = now + self.gesture_cooldown_s
                self._g_start = None
                return True
        else:
            self._g_start = None
        return False

    # -------------------------------------------------------------- appels MAVROS
    def _throttled(self, now, period=1.0):
        """Limite la fréquence des (ré)émissions de commandes de service."""
        if (now - self._cmd_stamp) >= period:
            self._cmd_stamp = now
            return True
        return False

    def _set_mode(self, mode):
        if self.cli_mode.service_is_ready():
            req = SetMode.Request()
            req.custom_mode = mode
            self.cli_mode.call_async(req)
            self.get_logger().info(f'-> mode {mode}')

    def _arm(self, value):
        if self.cli_arm.service_is_ready():
            req = CommandBool.Request()
            req.value = value
            self.cli_arm.call_async(req)
            self.get_logger().info('-> arm' if value else '-> disarm')

    def _takeoff(self):
        if self.cli_takeoff.service_is_ready():
            req = CommandTOL.Request()
            req.altitude = self.takeoff_alt
            self.cli_takeoff.call_async(req)
            self.get_logger().info(f'-> takeoff {self.takeoff_alt:.1f} m')

    # ------------------------------------------------------------------- sorties
    def _release_rc(self):
        """Aucun override : on laisse l'autopilote (GUIDED/TAKEOFF/LAND) piloter."""
        msg = OverrideRCIn()
        for i in range(8):
            msg.channels[i] = 0          # 0 = pas d'override sur ce canal
        self.pub_rc.publish(msg)

    def _publish_sticks(self):
        """Override RC depuis les sticks (Mode 2), en vol."""
        msg = OverrideRCIn()
        msg.channels[0] = _to_pwm(self.axes[2])   # roll     <- RX
        msg.channels[1] = _to_pwm(self.axes[3])   # pitch    <- RY
        msg.channels[2] = _to_pwm(self.axes[1])   # throttle <- LY
        msg.channels[3] = _to_pwm(self.axes[0])   # yaw      <- LX
        for i in range(4, 8):
            msg.channels[i] = 0          # on ne touche pas au canal de mode (géré via MAVROS)
        self.pub_rc.publish(msg)

    # ---------------------------------------------------------------- boucle 50 Hz
    def _tick(self):
        now = time.monotonic()
        fired = self._gesture_fired(now)
        armed = self.mav.armed
        mode = self.mav.mode

        if self.phase == DISARMED:
            self._release_rc()
            if fired:
                self.get_logger().info('Geste « V » détecté au sol -> décollage.')
                self.phase = ARMING
                self._cmd_stamp = 0.0    # autorise un envoi immédiat

        elif self.phase == ARMING:
            # Séquence non bloquante : GUIDED -> arm -> takeoff, pilotée par l'état.
            self._release_rc()
            if mode != 'GUIDED':
                if self._throttled(now):
                    self._set_mode('GUIDED')
            elif not armed:
                if self._throttled(now):
                    self._arm(True)
            else:
                if self._throttled(now):
                    self._takeoff()
                    self.phase = TAKEOFF

        elif self.phase == TAKEOFF:
            self._release_rc()
            if not armed:
                # décollage refusé / désarmé -> on repart de zéro
                self.get_logger().warn('Désarmé pendant le décollage -> retour au sol.')
                self.phase = DISARMED
            elif self.rel_alt >= 0.95 * self.takeoff_alt:
                self.get_logger().info(
                    f'Altitude {self.rel_alt:.1f} m atteinte -> passage en {self.fly_mode}.')
                self._set_mode(self.fly_mode)
                self.rc_live = False       # attend le recentrage du throttle
                self.phase = FLYING

        elif self.phase == FLYING:
            if not armed:
                self.get_logger().info('Désarmé -> au sol.')
                self.phase = DISARMED
                self._release_rc()
            elif fired:
                self.get_logger().info('Geste « V » détecté en vol -> atterrissage.')
                self._set_mode('LAND')
                self.phase = LANDING
                self._release_rc()
            else:
                # Sécurité : on n'active l'override qu'une fois le throttle recentré,
                # sinon le geste « V » (throttle en bas) ferait plonger le drone.
                if not self.rc_live and abs(self.axes[1]) < 0.25:
                    self.rc_live = True
                if self.rc_live:
                    self._publish_sticks()
                else:
                    self._release_rc()

        elif self.phase == LANDING:
            self._release_rc()
            if not armed:
                self.get_logger().info('Atterri et désarmé.')
                self.phase = DISARMED


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
