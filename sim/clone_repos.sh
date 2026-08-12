#!/bin/bash
# Clone le workspace ardupilot_gz en SHALLOW (--depth 1) pour minimiser le volume
# téléchargé (crucial sur réseau instable) + retry patient par repo.
set -e

cd /root/ros2_ws/src

# Timeout par tentative de clone (s) : borne les connexions qui stagnent sans
# déclencher le garde-fou lowSpeed de git (réseau RDC — il ne se déclenche pas
# sur les connexions établies mais muettes). Chaque dépôt reçoit un timeout
# adapté : les petits repos retentent vite (5 min), le gros ardupilot garde une
# grande marge (25 min, son clone légitime prend ~13 min à 400 Ko/s).
clone_retry() {
    local dir="$1" url="$2" ref="$3"
    local t="${4:-900}"   # timeout en secondes, défaut 15 min
    for i in $(seq 1 10); do
        rm -rf "$dir"
        if timeout "$t" git clone --depth 1 --single-branch --branch "$ref" "$url" "$dir" 2>>/tmp/clone.log; then
            echo "OK $dir"
            return 0
        fi
        echo "retry clone $dir ($i/10)"; sleep 30
    done
    return 1
}

# Ordre : petits dépôts d'abord (timeout court = retries rapides -> détection
# rapide d'une reprise du réseau), ardupilot en dernier (gros, timeout long).
clone_retry SITL_Models          https://github.com/ArduPilot/SITL_Models.git main 300
clone_retry ardupilot_gazebo     https://github.com/ArduPilot/ardupilot_gazebo.git ros2 300
clone_retry ardupilot_gz         https://github.com/ArduPilot/ardupilot_gz.git jazzy 300
clone_retry micro-ROS-Agent      https://github.com/micro-ROS/micro-ROS-Agent.git jazzy 600
clone_retry ros_gz               https://github.com/gazebosim/ros_gz.git jazzy 300
clone_retry sdformat_urdf        https://github.com/ros/sdformat_urdf.git jazzy 300
clone_retry ardupilot            https://github.com/ArduPilot/ardupilot.git master 1500

# sous-modules ArduPilot (nécessaires au build SITL), shallow aussi
cd /root/ros2_ws/src/ardupilot
git submodule update --init --recursive --depth 1 || echo "attention: submodules ardupilot incomplets"

echo "=== workspace cloné ==="
ls /root/ros2_ws/src/
