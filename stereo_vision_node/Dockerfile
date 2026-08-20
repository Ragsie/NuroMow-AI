FROM ros:humble-ros-base

# Combine all system packages into a single layer and clean up to keep the image small and fast
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-numpy \
    python3-opencv \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Debugging (Displays the Python version and architecture in the GitHub Actions log. It MUST say aarch64)
RUN python3 --version && uname -m

# Upgrade pip to the latest version (crucial for supporting modern 'manylinux' wheel formats)
RUN pip3 install --upgrade pip

# Install Rockchip NPU runtime lite directly via PyPI
RUN pip3 install --no-cache-dir rknn-toolkit-lite2==2.3.2

WORKDIR /app
COPY . /app/

# Run the node. The built-in ROS entrypoint automatically sources ROS 2 beforehand
CMD ["python3", "stereo_node.py"]
