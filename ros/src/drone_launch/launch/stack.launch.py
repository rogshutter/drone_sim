#!/usr/bin/env python3
"""stack.launch.py — lance TOUT le simulateur moderne.

- ardupilot_gz_bringup : ArduPilot SITL + Gazebo Harmonic (+ RViz si écran)
- MAVROS : pont MAVLink <-> ROS2 (se connecte au SITL en localhost)
- nos nodes : joy_bridge (RC-N1 UDP), flight_control (sticks->RC), pid_tuner

RViz (vue 3D) s'ouvre seulement si une variable DISPLAY est présente.
"""

import os

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    has_display = bool(os.environ.get('DISPLAY'))

    # Choix du drone : FRAME=x500 -> notre x500 ArduPilot ; sinon iris (défaut).
    frame = os.environ.get('FRAME', 'iris').lower()

    if frame == 'x500':
        # SITL + Gazebo avec le modèle x500 (meshes officiels Holybro).
        gz = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                get_package_share_directory('drone_launch')
                + '/launch/x500_sim.launch.py'
            ),
            launch_arguments={
                'rviz': 'true' if has_display else 'false',
            }.items(),
        )
    else:
        # SITL + Gazebo Harmonic (ardupilot_gz_bringup, iris), RViz si écran.
        gz = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                get_package_share_directory('ardupilot_gz_bringup')
                + '/launch/iris_runway.launch.py'
            ),
            launch_arguments={
                'rviz': 'true' if has_display else 'false',
            }.items(),
        )

    return LaunchDescription([
        gz,
        Node(
            package='mavros',
            executable='mavros_node',
            name='mavros',
            output='screen',
            parameters=[{'fcu_url': 'tcp://127.0.0.1:5760', 'gcs_url': ''}],
            respawn=True,
            respawn_delay=5.0,
        ),
        Node(package='joy_bridge', executable='joy_bridge_node',
             name='joy_bridge', output='screen', respawn=True, respawn_delay=5.0),
        Node(package='flight_control', executable='flight_control_node',
             name='flight_control', output='screen', respawn=True, respawn_delay=5.0),
        Node(package='pid_tuner', executable='pid_tuner_node',
             name='pid_tuner', output='screen', respawn=True, respawn_delay=5.0),
    ])
