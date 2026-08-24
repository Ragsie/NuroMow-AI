FROM ros:humble-ros-base

RUN apt-get update && apt-get install -y \
    ros-humble-rosbridge-server \
    && rm -rf /var/lib/apt/lists/*

# Start the websocket server on the default port (9090)
# NOTE: The bridge exposes ROS topics to web clients; ensure the firewall and network policy allow the required traffic.
CMD ["ros2", "launch", "rosbridge_server", "rosbridge_websocket_launch.xml"]