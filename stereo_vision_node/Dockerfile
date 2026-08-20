FROM ros:humble-ros-base

RUN apt-get update && apt-get install -y \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# debugging
RUN python3 --version && uname -m

# Install OpenCV and dependencies
RUN apt-get update && apt-get install -y python3-numpy python3-opencv python3-pip

# Install Rockchip NPU runtime lite (Ensure this pip package is compatible with your Orange Pi OS version)
# The exact URL might change depending on the RKNN toolkit version, but this is the standard approach:
RUN pip3 install --no-cache-dir https://github.com/airockchip/rknn-toolkit2/raw/master/rknn-toolkit-lite2/packages/rknn_toolkit_lite2-2.2.0-cp310-cp310-linux_aarch64.whl

WORKDIR /app
COPY . /app/

CMD ["python3", "stereo_node.py"]
