#!/bin/bash
# Lance le simulateur moderne : ArduPilot SITL + Gazebo Harmonic + RViz
# (vue 3D) + MAVROS + nos nodes (joy_bridge / flight_control / pid_tuner).
# Tous dans le meme workspace ROS2 -> MAVLink en localhost, aucun probleme de reseau.
set -e

ln -sf /usr/bin/python3 /usr/bin/python || true

# ressources Gazebo : modeles/mondes du projet (montes) + meshes x500 (image).
export GZ_SIM_RESOURCE_PATH="${GZ_SIM_RESOURCE_PATH:-/sim/models:/sim/worlds}:/opt/gz_models/models"

source /opt/ros/jazzy/setup.bash
source /root/ros2_ws/install/setup.bash

# Les URI SDF `package://ardupilot_gazebo/...` se resolvent depuis le dossier
# *share* du paquet (parent de models/), pas depuis models/ lui-meme. Le hook
# ament n'ajoute que models/ et worlds/ : sans cette ligne, Gazebo charge un
# monde vide, le SITL reste sans capteurs JSON, et rien ne vole.
_apgz_share="$(ros2 pkg prefix ardupilot_gazebo)/share"
export GZ_SIM_RESOURCE_PATH="${_apgz_share}:${GZ_SIM_RESOURCE_PATH}"
export SDF_PATH="${_apgz_share}${SDF_PATH:+:$SDF_PATH}"

echo "============================================================"
echo " Lancement du simulateur (SITL + Gazebo Harmonic + nodes)"
echo "   - QGroundControl : connexion MAVLink (voir start.bat)"
echo "   - Vue 3D         : RViz s'ouvre si DISPLAY est defini"
echo "   - Manette RC-N1  : scripts/run_dji.bat (UDP 7777)"
echo "============================================================"

exec ros2 launch drone_launch stack.launch.py "$@"
