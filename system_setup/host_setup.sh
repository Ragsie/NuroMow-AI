#!/usr/bin/env bash
# NuroMow Host setup for Radxa Dragon Q6A (Qualcomm QCS6490, Ubuntu 24.04 LTS / Radxa OS R2)
set -e

echo "=== Initializing NuroMow Host Setup for Radxa Dragon Q6A ==="

# 1. Create or load the central configuration file (nuromow.env) [updated for MIPI CSI and Qualcomm]
ENV_FILE="$(dirname "$0")/nuromow.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "No nuromow.env found. Creating default configuration..."
    sudo mkdir -p /etc/nuromow
    # Copy/create file with default values
    sudo tee "$ENV_FILE" > /dev/null << 'EOF'
NUROMOW_TRACK_WIDTH=0.40
NUROMOW_ROBOT_RADIUS=0.28
NUROMOW_NAV2_INFLATION_RADIUS=0.48

NUROMOW_VESC_LEFT_ID=1
NUROMOW_VESC_RIGHT_ID=2

# --- 3D STEREO MIPI CSI CAMERA SPECIFICATIONS ---
# Standard baseline for IMX219 binocular is 60mm (0.06m)
NUROMOW_CAMERA_BASELINE=0.06
NUROMOW_CAMERA_FOCAL_LENGTH=350.0

# --- SENSOR POSITIONS (URDF OFFSETS IN METERS) ---
NUROMOW_CAMERA_HEIGHT_Z=0.10
NUROMOW_CAMERA_OFFSET_X=0.25
NUROMOW_CAMERA_PITCH_Y=0.0
NUROMOW_GPS_OFFSET_X=-0.15
NUROMOW_GPS_HEIGHT_Z=0.25

# MIPI CSI camera devices (Dual IMX219 registers as separate nodes)
NUROMOW_CAMERA_DEVICE_LEFT="/dev/video0"
NUROMOW_CAMERA_DEVICE_RIGHT="/dev/video1"

# --- MLOPS / LOCAL NFS AI TRAINING SERVER ---
NUROMOW_NFS_SERVER_IP=""
NUROMOW_NFS_SHARE="/mnt/nfs/nuromow_raw"
EOF
    # Also create a symlink in /etc for easy access
    sudo ln -sf "$(realpath "$ENV_FILE")" /etc/nuromow/nuromow.env
fi

# Export variables so they are available throughout the system at runtime
# [FIXED: ShellCheck SC2046 and SC2163 compatible import via POSIX source]
# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
. "$ENV_FILE"
set +a

# 2. Update the system and install core tools + NFS support + Qualcomm FastRPC daemons
echo "Updating the system and installing system components..."
sudo apt-get update && sudo apt-get install -y \
    curl     git     udev     can-utils     v4l-utils     python3-pip     nfs-common     fastrpc     libcdsprpc1     libadsprpc1

# Ensure the FastRPC daemon (cdsprpcd) is running and starts at boot for NPU access
sudo systemctl enable --now fastrpc || true

# 2.5 Create a datamapper and configure optional NFS auto-mount for the AI training server
echo "Configuring datamapper and filesystem..."
sudo mkdir -p /opt/nuromow/models
sudo mkdir -p /opt/nuromow/incoming_raw
sudo chmod -R 777 /opt/nuromow

# Create a persistent stats file on the SSD if it does not exist
if [ ! -f /opt/nuromow/stats.json ]; then
    echo '{"total_distance_km": 0.0, "total_runtime_hours": 0.0}' | sudo tee /opt/nuromow/stats.json > /dev/null
    sudo chmod 777 /opt/nuromow/stats.json
fi

if [ -n "$NUROMOW_NFS_SERVER_IP" ]; then
    echo "Local AI training server found ($NUROMOW_NFS_SERVER_IP). Configuring systemd automount in /etc/fstab..."
    if ! grep -q "$NUROMOW_NFS_SHARE" /etc/fstab; then
        echo "Adding mount rule to /etc/fstab..."
        echo "${NUROMOW_NFS_SERVER_IP}:${NUROMOW_NFS_SHARE} /opt/nuromow/incoming_raw nfs defaults,noauto,x-systemd.automount,x-systemd.device-timeout=10,_netdev,rw,nofail 0 0" | sudo tee -a /etc/fstab
    fi
    echo "Reloading systemd and mounting NFS..."
    sudo systemctl daemon-reload || true
    sudo mount /opt/nuromow/incoming_raw || true
fi

# 2.6 Enable MIPI CSI device tree overlays on the Radxa board
echo "Enabling MIPI CSI device tree overlays for dual IMX219 (camera) via rsetup..."
# On Radxa OS, the 'rsetup' CLI tool is used to configure overlays automatically
if command -v rsetup &> /dev/null; then
    # Enable overlays for dual IMX219 cameras on the MIPI CSI bus
    sudo rsetup service enable overlay imx219-dual || true
    echo "Dual IMX219 MIPI CSI camera overlay enabled. Restart required."
else
    echo "rsetup not found. Make sure the dual IMX219 overlay is enabled manually in /boot/config.txt"
fi

# 3. Install Docker and configure permissions
if ! [ -x "$(command -v docker)" ]; then
    echo "Docker not found. Installing Docker Engine..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    sudo usermod -aG docker "$USER"
    rm get-docker.sh
fi

# 4. Create udev rules to provide stable symbolic links to the hardware
echo "Configuring udev rules for USB devices (ESP32, GPS)..."
sudo tee /etc/udev/rules.d/99-nuromow.rules << 'EOF'
# ESP32 Micro-ROS Controller (CP2102 USB-to-UART)
SUBSYSTEMS=="usb", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="ttyUSB_esp32", MODE="0666"

# Quectel LC29H RTK-GPS Receiver (Rover)
SUBSYSTEMS=="usb", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="ttyUSB_gps_rover", MODE="0666"
EOF

# Reload udev rules
sudo udevadm control --reload-rules && sudo udevadm trigger
echo "Udev rules reloaded."

# 5. Optimize the performance profile (Kryo Gold & Silver CPU cores + GPU + Hexagon NPU for performance)
echo "Setting Qualcomm QCS6490 CPU and NPU cores to Performance mode..."
for governor in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo "performance" | sudo tee "$governor" || true
done
# Optimize Hexagon NPU/DSP frequency
echo "performance" | sudo tee /sys/class/devfreq/*qcom,kgsl-3d0/governor || true

echo "=== System Setup Complete! Please restart your Radxa board to load the MIPI CSI overlays. ==="