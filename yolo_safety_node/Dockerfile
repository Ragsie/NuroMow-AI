# Start from the official ROS 2 Humble base image
FROM ros:humble-ros-base

# Installer KUN python3-pip. Fjern libgl1 og libglib2.0-0, da headless ikke bruger dem.
RUN apt-get update && apt-get install -y \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Installer PyTorch CPU-versionen først
RUN pip3 install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Installer ultralytics, afinstaller den tunge opencv-python automatisk, og installer den lette headless version
RUN pip3 install --no-cache-dir ultralytics \
    && pip3 uninstall -y opencv-python \
    && pip3 install --no-cache-dir opencv-python-headless

# Set the working directory inside the container
WORKDIR /app

# Kopier dine filer ind
COPY . /app/

# Kør dit script
CMD ["python3", "yolo_node.py"]