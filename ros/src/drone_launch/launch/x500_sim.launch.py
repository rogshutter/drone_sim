#!/usr/bin/env python3
"""x500_sim.launch.py — SITL ArduPilot + Gazebo Harmonic pour le x500.

Équivalent de ardupilot_gz `iris_runway.launch.py` + `robots/iris.launch.py`,
mais pour NOTRE modèle x500 :
    - ArduPilot SITL (model=json) avec les params x500 (/sim/config/gazebo-x500.parm)
    - Gazebo (serveur + GUI) avec le monde /sim/worlds/x500_runway.world

MAVROS et les nodes (joy_bridge, flight_control, pid_tuner) sont lancés à part
par stack.launch.py. Sélection du frame : variable d'environnement FRAME=x500.
"""
import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

# Emplacements montés depuis le projet (voir docker-compose.yml)
X500_WORLD = os.environ.get('X500_WORLD', '/sim/worlds/x500_runway.world')
X500_PARM = os.environ.get('X500_PARM', '/sim/config/gazebo-x500.parm')


def generate_launch_description():
    pkg_ardupilot_sitl = get_package_share_directory('ardupilot_sitl')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # ArduPilot SITL (mêmes réglages que le lancement iris officiel).
    sitl_dds = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [PathJoinSubstitution([FindPackageShare('ardupilot_sitl'),
                                   'launch', 'sitl_dds_udp.launch.py'])]
        ),
        launch_arguments={
            'transport': 'udp4',
            'port': '2019',
            'synthetic_clock': 'True',
            'wipe': 'False',
            'model': 'json',
            'speedup': '1',
            'slave': '0',
            'instance': '0',
            'defaults': X500_PARM + ',' + os.path.join(
                pkg_ardupilot_sitl, 'config', 'default_params', 'dds_udp.parm'),
            'sim_address': '127.0.0.1',
            'master': 'tcp:127.0.0.1:5760',
            'sitl': '127.0.0.1:5501',
        }.items(),
    )

    # Gazebo serveur (monde x500) + GUI.
    gz_server = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f'{Path(pkg_ros_gz_sim) / "launch" / "gz_sim.launch.py"}'
        ),
        launch_arguments={'gz_args': f'-v4 -s -r {X500_WORLD}'}.items(),
    )
    gz_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f'{Path(pkg_ros_gz_sim) / "launch" / "gz_sim.launch.py"}'
        ),
        launch_arguments={'gz_args': '-v4 -g'}.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='false',
                              description='(ignoré pour x500)'),
        gz_server,
        gz_gui,
        sitl_dds,
    ])
