FROM ros:humble-ros-base

RUN apt-get update && apt-get install -y \
    ros-humble-rosbridge-server \
    && rm -rf /var/lib/apt/lists/*

# Starter websocket-serveren på standardporten (9090)
CMD ["ros2", "launch", "rosbridge_server", "rosbridge_websocket_launch.xml"]