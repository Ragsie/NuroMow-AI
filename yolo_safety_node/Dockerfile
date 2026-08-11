# Start from the official ROS 2 Humble base image
FROM ros:humble-ros-base

# Install system dependencies required for OpenCV and basic Python pip
RUN apt-get update && apt-get install -y \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 1. TVING CPU-VERSIONEN AF PYTORCH FØRST (Dette sparer mange gigabytes)
RUN pip3 install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Installer Ultralytics og den lette version af OpenCV uden grafiske værktøjer
RUN pip3 install --no-cache-dir ultralytics opencv-python-headless

# Set the working directory inside the container
WORKDIR /app

# (Sørg for at kopiere dine scripts ind i containeren - tilføjet her for en sikkerheds skyld)
COPY . /app/

# The ROS 2 base image automatically sources '/opt/ros/humble/setup.bash' 
# via its default entrypoint. We just need to tell it which script to run.
CMD ["python3", "yolo_node.py"]