FROM ros:humble-ros-base

# 1. Capture the target architecture (amd64 or arm64) from Docker Buildx
ARG TARGETARCH

# Combine all system packages into a single layer and clean up to keep the image small and fast
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-numpy \
    python3-opencv \
    ros-humble-robot-state-publisher \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip

# 2. Install Python packages conditionally based on the architecture
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        echo "Building for ARM64: Installing Rockchip NPU runtime..." && \
        pip3 install --no-cache-dir rknn-toolkit-lite2==2.3.2; \
    elif [ "$TARGETARCH" = "amd64" ]; then \
        echo "Building for x86_64: Skipping RKNN Lite (NPU hardware not present on PC)..."; \
    else \
        echo "Unsupported architecture: $TARGETARCH" && exit 1; \
    fi

WORKDIR /app
COPY . /app/

CMD ["python3", "stereo_node.py"]

# Make the startup script executable
RUN chmod +x /app/start_vision.sh

# Run the startup script instead of launching python directly
CMD ["/app/start_vision.sh"]
