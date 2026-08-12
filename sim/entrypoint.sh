#!/bin/bash
# Lance le simulateur moderne : ArduPilot SITL + Gazebo Harmonic + RViz
# (vue 3D) + MAVROS + nos nodes (joy_bridge / flight_control / pid_tuner).
# Tous dans le meme workspace ROS2 -> MAVLink en localhost, aucun probleme de reseau.
set -e

ln -sf /usr/bin/python3 /usr/bin/python || true

# ressources Gazebo personnalisees (modeles X500, mondes) montees depuis le projet
export GZ_SIM_RESOURCE_PATH="${GZ_SIM_RESOURCE_PATH:-/sim/models:/sim/worlds}"

source /opt/ros/jazzy/setup.bash
source /root/ros2_ws/install/setup.bash

echo "============================================================"
echo " Lancement du simulateur (SITL + Gazebo Harmonic + nodes)"
echo "   - QGroundControl : connexion MAVLink (voir start.bat)"
echo "   - Vue 3D         : RViz s'ouvre si DISPLAY est defini"
echo "   - Manette RC-N1  : scripts/run_dji.bat (UDP 7777)"
echo "============================================================"

exec ros2 launch drone_launch stack.launch.py "$@"
