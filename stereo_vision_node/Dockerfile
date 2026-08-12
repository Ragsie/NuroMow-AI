FROM ros:humble-ros-base

RUN apt-get update && apt-get install -y \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install OpenCV and dependencies
RUN pip3 install --no-cache-dir opencv-python numpy

# Install Rockchip NPU runtime lite (Ensure this pip package is compatible with your Orange Pi OS version)
# The exact URL might change depending on the RKNN toolkit version, but this is the standard approach:
RUN pip3 install --no-cache-dir rknn-toolkit-lite2

WORKDIR /app
COPY . /app/

CMD ["python3", "stereo_node.py"
