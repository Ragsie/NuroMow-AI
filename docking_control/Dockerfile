FROM ubuntu:24.04

# Sørg for at køre uden interaktive prompts under installation
ENV DEBIAN_FRONTEND=noninteractive

# Installer ROS 2 Humble basisafhængigheder og rclpy
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-rclpy \
    python3-nav2-msgs \
    python3-geometry-msgs \
    python3-sensor-msgs \
    python3-std-srvs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kopier kildekoden over i containeren
COPY docking_node.py .

# Kør docking noden som standard kommando
CMD ["python3", "docking_node.py"]