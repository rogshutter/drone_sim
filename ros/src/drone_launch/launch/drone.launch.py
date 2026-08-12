#!/usr/bin/env python3
"""drone.launch.py — lance la stack ROS2 complète.

- mavros (pont MAVLink <-> ROS2) vers le conteneur `sim` (ArduPilot SITL)
- joy_bridge : UDP (RC-N1) -> /joy
- flight_control : /joy -> /mavros/rc/override
- pid_tuner : paramètres ROS2 -> paramètres ArduPilot

Paramètre : fcu_url (défaut tcp://sim:5760)
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    fcu_url = LaunchConfiguration('fcu_url', default='tcp://sim:5760')

    return LaunchDescription([
        Node(
            package='mavros',
            executable='mavros_node',
            name='mavros',
            output='screen',
            parameters=[{'fcu_url': fcu_url, 'gcs_url': ''}],
            respawn=True,
            respawn_delay=3.0,
        ),
        Node(
            package='joy_bridge',
            executable='joy_bridge_node',
            name='joy_bridge',
            output='screen',
            respawn=True,
            respawn_delay=3.0,
        ),
        Node(
            package='flight_control',
            executable='flight_control_node',
            name='flight_control',
            output='screen',
            respawn=True,
            respawn_delay=3.0,
        ),
        Node(
            package='pid_tuner',
            executable='pid_tuner_node',
            name='pid_tuner',
            output='screen',
            respawn=True,
            respawn_delay=3.0,
        ),
    ])
