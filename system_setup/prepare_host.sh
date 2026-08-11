#!/bin/bash
# Complete Docker Host Provisioning Script for "Worx ROS 2 Mower"
# Target OS: Ubuntu Server 24.04 LTS (64-bit)
# Note: Run this script as a normal user with sudo privileges.

echo "🚀 Preparing host machine for Docker-based Worx Mower..."

# 1. Remove unnecessary background services (Debloat to save CPU/RAM)
echo "🧹 Removing background bloatware (snapd, cloud-init, modemmanager, etc.)..."
sudo systemctl stop snapd
sudo apt-get purge cloud-init snapd modemmanager multipath-tools unattended-upgrades -y
sudo apt-get autoremove -y

# 2. Update and upgrade the system
echo "🔄 Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# 3. Enable hardware interfaces (I2C for VL53L5X ToF sensors and SPI)
echo "🔌 Enabling I2C and SPI interfaces on the host..."
sudo apt-get install raspi-config -y || true
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0

# 4. Grant hardware permissions to the current user (and Docker daemon)
echo "🔑 Granting user permissions for I2C, Serial (USB), and Video (Camera)..."
sudo usermod -aG i2c "$USER" 
sudo usermod -aG dialout "$USER"
sudo usermod -aG video "$USER"

# 5. Install Docker and Docker Compose
echo "🐳 Installing Docker Engine and Docker Compose..."
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove -y $pkg; done

sudo apt-get update
sudo apt-get install ca-certificates curl -y
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# shellcheck disable=SC1091
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
sudo usermod -aG docker "$USER"

echo "📥 Pulling latest Docker containers from Docker Hub..."
# Sørg for at stå i den mappe hvor din docker-compose.yml ligger, før du kører scriptet,
# eller angiv stien dertil. Her antager vi, at scriptet køres fra projektmappen.
if [ -f "docker-compose.yml" ]; then
    docker compose pull
    echo "🚀 Starting Docker containers..."
    docker compose up -d
else
    echo "⚠️ docker-compose.yml not found in current directory. Skipping pull/up."
fi

echo "✅ Host provisioning & deployment complete!"
echo "⚠️ Please note: Group permissions (docker, i2c, dialout, video) require a re-login or reboot to take effect."
echo "🔄 Rebooting the system to apply changes..."
sudo reboot