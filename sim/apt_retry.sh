#!/bin/bash
# apt-get update ROBUSTE : réessaie jusqu'à ce que le dépôt ROS2 (packages.ros.org)
# soit réellement chargé (vérifié par la résolution de ros-jazzy-mavros).
# Le réseau (RDC) est instable : sans ça, apt-get update "réussit" mais ignore
# le dépôt ROS2 -> packages introuvables.
for i in $(seq 1 15); do
    apt-get update > /tmp/apt_update.log 2>&1
    if apt-cache policy ros-jazzy-mavros 2>/dev/null | grep -q "Candidate"; then
        echo "apt-get update OK (depot ROS2 charge, tentative $i)"
        exit 0
    fi
    echo "reseau instable : nouvelle tentative apt-get update ($i/15)"
    sleep 15
done
echo "ECHEC : impossible de charger le depot ROS2"
cat /tmp/apt_update.log
exit 1
