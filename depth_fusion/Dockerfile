# Start from the official ROS 2 Humble Base Image (Ubuntu 22.04 / Python 3.10)
FROM ros:humble-ros-base

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install core system packages, OpenCV, and ROS 2 dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-numpy \
    python3-opencv \
    ros-humble-cv-bridge \
    ros-humble-message-filters \
    ros-humble-sensor-msgs \
    git \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Install Rockchip NPU runtime libraries and Python RKNN-Lite2 packages
# Since GitHub Actions cross-compiles for both AMD64 and ARM64, we handle architectures gracefully
RUN mkdir -p /app/rknn_libs && \
    cd /app/rknn_libs && \
    git clone --depth 1 https://github.com/rockchip-linux/rknn-toolkit2.git && \
    # Copy librknnrt.so (the NPU driver) for RK3588 (ARM64) to the system library path
    cp rknn-toolkit2/rknpu2/runtime/Linux/librknn_api/aarch64/librknnrt.so /usr/lib/ && \
    # Install the Python RKNN-Lite2 package for Python 3.10 (Ubuntu 22.04 standard)
    pip3 install rknn-toolkit2/rknn-lite2/packages/rknn_lite2-2.1.0-cp310-cp310-linux_aarch64.whl || \
    echo "⚠️ Skipped aarch64 RKNN installation (this is an AMD64 machine running cross-compilation)." && \
    # Delete the heavy git repository to keep the Docker image size lightweight
    cd /app && rm -rf /app/rknn_libs

# Copy the pre-trained RKNN model and the fusion code
COPY ./mowerAIn-seg.rknn /app/mowerAIn-seg.rknn
COPY ./depth_fusion_node.py /app/depth_fusion_node.py

# Grant execution permissions to the script
RUN chmod +x /app/depth_fusion_node.py

# Source the ROS 2 Humble workspace and start the fusion node
ENTRYPOINT ["/bin/bash", "-c", "source /opt/ros/humble/setup.bash && python3 /app/depth_fusion_node.py"]