FROM ros:humble-ros-base

# Combine all system packages into a single layer and clean up to keep the image small and fast
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-numpy \
    python3-opencv \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Debugging (Displays the Python version and architecture in the GitHub Actions log)
RUN python3 --version && uname -m

# Install Rockchip NPU runtime lite (v2.3.2 for Python 3.10)
RUN pip3 install --no-cache-dir https://github.com/airockchip/rknn-toolkit2/raw/master/rknn-toolkit-lite2/packages/rknn_toolkit_lite2-2.3.2-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl

WORKDIR /app
COPY . /app/

# Run the node. The built-in ROS entrypoint automatically sources ROS 2 beforehand
CMD ["python3", "stereo_node.py"]
