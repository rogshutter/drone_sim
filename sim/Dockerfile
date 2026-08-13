# =============================================================================
# Conteneur SIMULATION — stack MODERNE, propre et durable
#   Ubuntu 24.04 (noble) + ROS2 Jazzy + Gazebo Harmonic + ardupilot_gz
#   + ArduPilot SITL (version figée) + MAVROS + nodes pédagogiques
#
# Un SEUL conteneur : le stack moderne est un seul workspace ROS2 (ardupilot_gz
# lance SITL + Gazebo + RViz ensemble). MAVROS et les nodes (joy_bridge,
# flight_control, pid_tuner, obstacle_avoid) tournent au même endroit,
# MAVLink en localhost -> aucun problème de réseau inter-conteneurs.
# =============================================================================
FROM ros:jazzy-ros-base-noble

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# ---------------------------------------------------------------------------
# Miroir apt ROS2 (par défaut : dépôt officiel packages.ros.org)
# ---------------------------------------------------------------------------
# Certains réseaux (ex. RDC) bloquent packages.ros.org (hébergé chez osuosl) :
# apt-get update échoue et le dépôt ROS2 ne charge jamais -> paquets introuvables.
# Pour utiliser un miroir, passer ROS2_APT_MIRROR au build (docker-compose.yml le
# relaie via la variable d'environnement du même nom). On peut lister PLUSIEURS
# miroirs (séparés par des espaces) : apt tentera le suivant si le précédent
# échoue. Miroirs couvrant noble :
#   https://mirrors.huaweicloud.com/ros2/ubuntu
#   https://mirrors.cloud.tencent.com/ros2/ubuntu
#   https://mirrors.aliyun.com/ros2/ubuntu
ARG ROS2_APT_MIRROR=http://packages.ros.org/ros2/ubuntu
RUN sed -i "s|^URIs:.*|URIs: ${ROS2_APT_MIRROR}|" /etc/apt/sources.list.d/ros2.sources \
    && sed -i "s|^Types:.*|Types: deb|" /etc/apt/sources.list.d/ros2.sources \
    && cat /etc/apt/sources.list.d/ros2.sources

# IPv4 forcé : les réseaux sans IPv6 routable évitent les timeouts d'attente IPv6
RUN printf 'Acquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/98ipv4

# Robustesse réseau : réessaie les téléchargements apt (réseaux instables)
RUN printf 'Acquire::Retries "6";\nAcquire::http::Timeout "30";\n' > /etc/apt/apt.conf.d/99retries
COPY sim/apt_retry.sh /root/apt_retry.sh
RUN chmod +x /root/apt_retry.sh

# ---------------------------------------------------------------------------
# Outils de base + compilateur
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget curl ca-certificates \
    build-essential cmake pkg-config \
    python3 python3-dev python3-pip python3-numpy \
    python3-vcstool python3-rosdep \
    python3-colcon-common-extensions \
    netcat-openbsd \
    lsb-release sudo \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Dépôt OSRF (Gazebo Harmonic) + rosdep gazebo + MAVROS
# ---------------------------------------------------------------------------
RUN wget https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable noble main" > /etc/apt/sources.list.d/gazebo-stable.list \
    && wget https://raw.githubusercontent.com/osrf/osrf-rosdep/master/gz/00-gazebo.list -O /etc/ros/rosdep/sources.list.d/00-gazebo.list \
    && /root/apt_retry.sh \
    && apt-get install -y --no-install-recommends \
        ros-jazzy-mavros ros-jazzy-mavros-extras \
        ros-jazzy-rmw-cyclonedds-cpp \
    && timeout 180 /opt/ros/jazzy/lib/mavros/install_geographiclib_datasets.sh \
       || echo "AVERTISSEMENT: datasets GeographicLib non installés (réseau bloquant geographiclib.net). MAVROS continue sans correction géoïde." \
    && rm -rf /var/lib/apt/lists/*

ENV GZ_VERSION=harmonic
# CycloneDDS : plus stable que FastDDS avec MAVROS (évite le bug "invalid allocator")
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# ---------------------------------------------------------------------------
# Workspace ROS2 : ardupilot_gz + dépendances (réfs Jazzy) + nos nodes
# ---------------------------------------------------------------------------
RUN mkdir -p /root/ros2_ws/src
COPY sim/clone_repos.sh /root/clone_repos.sh
RUN chmod +x /root/clone_repos.sh

# git robustesse réseau (clones interrompus -> échec rapide + retry patient)
# - http.connectTimeout : une connexion TCP/TLS muette est abandonnée après 60 s
# - http.version HTTP/1.1 : évite le stall HTTP/2 (connexion établie mais aucune
#   donnée, très fréquent sur réseau RDC) — le garde-fou lowSpeedTime ne s'y
#   applique pas.
RUN git config --global http.lowSpeedLimit 1000 \
    && git config --global http.lowSpeedTime 120 \
    && git config --global http.connectTimeout 60 \
    && git config --global http.version HTTP/1.1 \
    && git config --global http.postBuffer 524288000

# clones SHALLOW (--depth 1) : beaucoup moins de volume à télécharger sur réseau instable
RUN /root/clone_repos.sh

# ---------------------------------------------------------------------------
# Modèle visuel x500 (Holybro) depuis PX4/PX4-gazebo-models (licence BSD-3).
# Sert au frame optionnel FRAME=x500. Récupéré en sparse (x500 + x500_base) et
# posé sur /opt/gz_models/models, ajouté à GZ_SIM_RESOURCE_PATH au runtime.
# ---------------------------------------------------------------------------
RUN mkdir -p /opt/gz_models/models \
    && git clone --depth 1 --filter=blob:none --sparse \
       https://github.com/PX4/PX4-gazebo-models.git /tmp/px4models \
    && git -C /tmp/px4models sparse-checkout set models/x500 models/x500_base \
    && cp -r /tmp/px4models/models/x500 /tmp/px4models/models/x500_base /opt/gz_models/models/ \
    && rm -rf /tmp/px4models \
    || echo "AVERTISSEMENT: modèle x500 non récupéré (frame x500 indisponible, iris reste OK)."

# nos nodes pédagogiques (joy_bridge, flight_control, pid_tuner, obstacle_avoid, drone_launch)
COPY ros/src /root/ros2_ws/src/

RUN cd /root/ros2_ws \
    && . /opt/ros/jazzy/setup.sh \
    && /root/apt_retry.sh \
    && rosdep update \
    && rosdep install --from-paths src --ignore-src -y \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# microxrceddsgen : générateur requis par ardupilot_sitl (support DDS/ROS2).
# Sans lui, `colcon build ardupilot_sitl` échoue : "Could not find the program
# ['microxrceddsgen']". On le construit depuis ArduPilot/Micro-XRCE-DDS-Gen
# (Java + Gradle) et on l'expose sur le PATH.
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/* \
    && git clone --recurse-submodules --depth 1 \
       https://github.com/ArduPilot/Micro-XRCE-DDS-Gen.git /root/Micro-XRCE-DDS-Gen \
    && cd /root/Micro-XRCE-DDS-Gen \
    && ./gradlew assemble \
    && ln -sf /root/Micro-XRCE-DDS-Gen/scripts/microxrceddsgen /usr/local/bin/microxrceddsgen \
    && microxrceddsgen -version || true

# ---------------------------------------------------------------------------
# Prérequis Python d'ArduPilot (waf + génération MAVLink/DroneCAN). REQUIS AVANT
# le colcon build de ardupilot_sitl : sinon le waf build échoue tout de suite
# (génération de code). empy est ÉPINGLÉ car empy 4.x casse le build ArduPilot.
# ---------------------------------------------------------------------------
ENV PIP_BREAK_SYSTEM_PACKAGES=1
RUN ln -sf /usr/bin/python3 /usr/bin/python || true \
    && pip3 install --no-cache-dir empy==3.3.4 future pexpect pymavlink MAVProxy

# 1) le stack ardupilot_gz (SITL+Gazebo+RViz)
RUN cd /root/ros2_ws \
    && . /opt/ros/jazzy/setup.sh \
    && export PATH="$PATH:/root/Micro-XRCE-DDS-Gen/scripts" \
    && colcon build --packages-up-to ardupilot_gz_bringup --cmake-args -DCMAKE_BUILD_TYPE=Release

# 2) nos nodes pédagogiques
RUN cd /root/ros2_ws \
    && . /opt/ros/jazzy/setup.sh \
    && colcon build --packages-select joy_bridge flight_control pid_tuner obstacle_avoid drone_launch --symlink-install

# ---------------------------------------------------------------------------
# ArduPilot SITL (version figée, principe du corpus)
# ---------------------------------------------------------------------------
ARG ARDUPILOT_VERSION=Copter-4.5.7
RUN git clone --depth 1 --branch ${ARDUPILOT_VERSION} https://github.com/ArduPilot/ardupilot.git /ardupilot \
    && cd /ardupilot \
    && git submodule update --init --recursive --depth 1

RUN ln -sf /usr/bin/python3 /usr/bin/python || true
# (Prérequis Python déjà installés plus haut, empy épinglé à 3.3.4.)

RUN cd /ardupilot \
    && ./waf configure --board sitl \
    && ./waf copter

# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------
COPY sim/entrypoint.sh /
RUN chmod +x /entrypoint.sh

EXPOSE 5760 14550/udp 7777/udp

ENTRYPOINT ["/entrypoint.sh"]
