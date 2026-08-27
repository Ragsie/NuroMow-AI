#!/bin/bash
# Complete Docker Host Provisioning Script for "OpenMow AI" / "Worx ROS 2 Mower"
# Target OS: Ubuntu (Joshua Riek / Orange Pi OS / Raspberry Pi OS)

if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: This script must be run with sudo!"
  exit 1
fi

echo "======================================================"
echo "🚀 OpenMow AI - Host Provisioning & Deployment Setup"
echo "======================================================"
echo ""
echo "Select deployment profile:"
echo "  1) Cloud Mode (Pure OTA via GitHub & Watchtower - No Local Server)"
echo "  2) Local Mode (Mounts Local Server for Dataset Collection / Active Learning)"
echo ""
read -rp "Enter choice [1 or 2]: " DEPLOY_MODE

# Validate Input
if [[ "$DEPLOY_MODE" != "1" && "$DEPLOY_MODE" != "2" ]]; then
    echo "❌ Invalid selection. Aborting."
    exit 1
fi

# 1. Debloat
echo "🧹 Removing unnecessary bloatware..."
systemctl stop snapd 2>/dev/null || true
apt-get purge cloud-init snapd modemmanager multipath-tools unattended-upgrades -y
apt-get autoremove -y

# 2. Update packages
echo "🔄 Updating system packages..."
apt-get update && apt-get upgrade -y

# 3. Grant hardware permissions (NPU, Serial, Video, I2C)
echo "🔑 Setting up hardware access permissions..."
TARGET_USER="${SUDO_USER:-$USER}"
usermod -aG dialout "$TARGET_USER"
usermod -aG video "$TARGET_USER"
usermod -aG i2c "$TARGET_USER" 2>/dev/null || true

if [ -e /dev/rknn ]; then
  chmod 0666 /dev/rknn
fi

# 4. Mode-specific configuration (Local Server & Dataset Pipeline)
if [ "$DEPLOY_MODE" == "2" ]; then
    echo "📁 Configuring Local Storage & Training Pipelines..."
    apt-get install nfs-common -y
    
    read -rp "Enter Local Server IP (e.g., 192.168.1.100): " SERVER_IP
    read -rp "Enter Server NFS Export Path (e.g., /mnt/pool/openmow): " SERVER_PATH

    mkdir -p /mnt/local_ai_server
    
    # Mount NFS share
    echo "🔗 Connecting to ${SERVER_IP}:${SERVER_PATH}..."
    mount -t nfs "${SERVER_IP}:${SERVER_PATH}" /mnt/local_ai_server 2>/dev/null || echo "⚠️ Warning: Could not mount NFS immediately. Ensure server is online."

    # Add to /etc/fstab for persistence
    FSTAB_ENTRY="${SERVER_IP}:${SERVER_PATH} /mnt/local_ai_server nfs defaults,_netdev,nofail 0 0"
    if ! grep -q "/mnt/local_ai_server" /etc/fstab; then
        echo "$FSTAB_ENTRY" >> /etc/fstab
    fi

    # Create local drop folders on target server for the Grounded-SAM pipeline
    mkdir -p /mnt/local_ai_server/incoming_raw
    mkdir -p /mnt/local_ai_server/models

    # Create an environment flag for docker-compose / ROS 2
    echo "AI_MODE=local" > .env
    echo "UPLOAD_RAW_FRAMES=true" >> .env
    echo "LOCAL_STORAGE_PATH=/mnt/local_ai_server" >> .env
    echo "✅ Local Mode configured. Dataset buffer mapped to /mnt/local_ai_server/incoming_raw"
else
    echo "☁️ Configuring Cloud Mode..."
    echo "AI_MODE=cloud" > .env
    echo "UPLOAD_RAW_FRAMES=false" >> .env
    echo "LOCAL_STORAGE_PATH=/dev/null" >> .env
    echo "✅ Cloud Mode configured. Watchtower and container models active."
fi

# 5. Install Docker & Compose Plugin
echo "🐳 Installing Docker Engine..."
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do 
    apt-get remove -y "$pkg" 2>/dev/null || true
done

apt-get install ca-certificates curl -y
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
usermod -aG docker "$TARGET_USER"

# 6. Start the Docker Stack
echo "📥 Pulling and launching Docker services..."
if [ -f "docker-compose.yaml" ] || [ -f "docker-compose.yml" ]; then
    sudo -u "$TARGET_USER" docker compose pull
    sudo -u "$TARGET_USER" docker compose up -d
else
    echo "⚠️ docker-compose.yaml not found. Skipping automatic container start."
fi

echo "======================================================"
echo "✅ Setup successfully finished!"
echo "🔄 Rebooting machine to apply permission changes..."
echo "======================================================"
reboot
