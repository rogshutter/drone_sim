#!/bin/bash
# NB : on n'attend PAS le SITL en se connectant à son port TCP 5760 : ArduPilot SITL
# n'accepte qu'une connexion à la fois sur ce port, et une simple vérification la
# consommerait. MAVROS (respawn) se connecte lui-même dès que sim:5760 est prêt.
set -e

source /opt/ros/humble/setup.bash

# Rebuild du workspace à chaque démarrage : les sources sont montées en volume
# (./ros/src) donc les scripts étudiants sont pris en compte sans reconstruire l'image.
cd /ros_ws
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source /ros_ws/install/setup.bash

exec ros2 launch drone_launch drone.launch.py "$@"
