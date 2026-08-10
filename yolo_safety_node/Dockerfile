# Start from the official ROS 2 Humble base image
FROM ros:humble-ros-base

# Install system dependencies required for OpenCV and basic Python pip
RUN apt-get update && apt-get install -y \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Ultralytics (YOLO) and OpenCV via pip
RUN pip3 install --no-cache-dir ultralytics opencv-python

# Set the working directory inside the container
WORKDIR /app

# The ROS 2 base image automatically sources '/opt/ros/humble/setup.bash' 
# via its default entrypoint. We just need to tell it which script to run.
CMD ["python3", "yolo_node.py"]