# Start from the official ROS 2 Humble base image
FROM ros:humble-ros-base

# Install system dependencies for I2C communication
RUN apt-get update && apt-get install -y \
    python3-pip \
    i2c-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Python libraries for I2C and the VL53L5X sensor logic
RUN pip3 install --no-cache-dir smbus2 vl53l5cx

# Set the working directory inside the container
WORKDIR /app

# Run the ToF sensor script when the container starts
CMD ["python3", "tof_node.py"]