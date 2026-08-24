#!/bin/bash
# Complete Docker Host Provisioning Script for "Worx ROS 2 Mower" (Orange Pi 5 Edition)
# Target OS: Ubuntu (Joshua Riek / Orange Pi OS) for RK3588

if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run with sudo!"
    exit 1
fi

# ==========================================
# USER CONFIGURATION (EDIT THESE FOR TRUENAS)
# ==========================================
# NOTE: Set these before running the script on a real machine.
# If the IP or NFS path is wrong, the host setup will fail or the AI model will never mount.
TRUENAS_IP="192.168.X.X" # Insert your jupyterlab IP here
NFS_SHARE_PATH="/mnt/pool_name/deploy" # Insert the full path to your NFS share
LOCAL_MOUNT_POINT="/mnt/nfs/deploy" 
# ==========================================

# TODO: Verify that the target host is an ARM64 system, since the Docker image and RKNN drivers are architecture-specific.

echo "Preparing Orange Pi 5 host machine for Docker-based Worx Mower..."

# 1. Debloat
echo "Removing bloatware..."
sudo systemctl stop snapd
sudo apt-get purge cloud-init snapd modemmanager multipath-tools unattended-upgrades -y
sudo apt-get autoremove -y

# 2. Update packages and install NFS tools
echo "Updating system and installing NFS client..."
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install nfs-common -y

# 3. Setup TrueNAS NFS Mount (Auto-mount on demand to prevent boot hangs over Wi-Fi)
echo "Configuring persistent NFS mount for AI deployment..."
sudo mkdir -p "$LOCAL_MOUNT_POINT"

# Check if the mount is already in fstab to prevent duplicates on rerun
if ! grep -q "$LOCAL_MOUNT_POINT" /etc/fstab; then
    echo "Adding NFS entry to /etc/fstab..."
    # x-systemd.automount ensures it only connects when the folder is accessed
    # _netdev tells the system to wait for network availability
    # soft,retrans=3,timeo=14 prevents permanent hangs on bad Wi-Fi
    echo "$TRUENAS_IP:$NFS_SHARE_PATH $LOCAL_MOUNT_POINT nfs noauto,x-systemd.automount,x-systemd.idle-timeout=1min,soft,retrans=3,timeo=14,_netdev 0 0" | sudo tee -a /etc/fstab
    
    # Reload systemd and start the automount service
    sudo systemctl daemon-reload
    sudo systemctl restart local-fs.target
else
    echo "NFS mount already exists in /etc/fstab. Skipping."
fi

# 4. Grant hardware permissions (NPU, Serial, Video)
echo "Granting user permissions for NPU, Serial, and Video..."
# Ensure dialout and video groups exist and user is added
sudo usermod -aG dialout "$USER"
sudo usermod -aG video "$USER"

# Make sure the NPU device has the right permissions (if it exists)
if [ -e /dev/rknn ]; then
    sudo chmod 0666 /dev/rknn
fi

# 5. Install Docker
# NOTE: This script assumes Ubuntu/Debian package management and Docker repository access.
# If the machine is not Debian-based, the install commands will need to be adapted.
echo "Installing Docker..."
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove -y $pkg; done
sudo apt-get install ca-certificates curl -y
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# shellcheck disable=SC1091
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
sudo usermod -aG docker "$USER"

echo "Pulling latest Docker containers..."
# TODO: Check that the compose file matches the host architecture and that all required containers are present.
if [ -f "docker-compose.yml" ]; then
    docker compose pull
    sudo DOCKER_DEFAULT_PLATFORM=linux/arm64 docker compose up -d
else
    echo "docker-compose.yml not found. Skipping."
fi

echo "Rebooting the system to apply changes..."
sudo reboot
