# Conteneur ROS2 Humble : MAVROS + nodes joy_bridge / flight_control / pid_tuner
FROM ros:humble-ros-base-jammy

ENV DEBIAN_FRONTEND=noninteractive

# MAVROS + CycloneDDS (plus stable que FastDDS avec MAVROS) + outils colcon
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-mavros \
    ros-humble-mavros-extras \
    ros-humble-rmw-cyclonedds-cpp \
    python3-colcon-common-extensions \
    netcat-openbsd \
    && /opt/ros/humble/lib/mavros/install_geographiclib_datasets.sh \
    && rm -rf /var/lib/apt/lists/*

# DDS par défaut : CycloneDDS (évite le bug "invalid allocator" de MAVROS+FastDDS)
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Workspace ROS2
WORKDIR /ros_ws
COPY src ./src

RUN . /opt/ros/humble/setup.sh \
    && colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD []
