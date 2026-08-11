#!/bin/bash
# Complete Docker Host Provisioning Script for "Worx ROS 2 Mower"
# Target OS: Ubuntu Server 24.04 LTS (64-bit)
# Note: Run this script as a normal user with sudo privileges.

echo "🚀 Preparing host machine for Docker-based Worx Mower..."

# Check if the effective user ID (EUID) is NOT equal to 0
if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run with sudo!"
  exit 1
fi
echo "The script is now running with root privileges!"

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
# Make sure you are in the directory where your docker-compose.yml is located before running the script,
# or specify the path to it. Here we assume the script is run from the project directory.
echo "📥 Pulling latest Docker containers from Docker Hub..."
if [ -f "docker-compose.yml" ]; then
    docker compose pull
    echo "🚀 Starting Docker containers..."
    docker compose up -d
fi

# Check if containers are actually running before cleaning up
if docker compose ps | grep -q "Up"; then
# ... (your existing script that sets up the system) ...

echo "starting Worx Landroid containers..."

# ==========================================
# INSTALL PORTAINER
# ==========================================

echo "Installing Portainer Web UI..."

# 1. Create a virtual hard drive for Portainer's settings (ignore error if it exists)
sudo docker volume create portainer_data || true

# 2. Download and start Portainer
sudo docker run -d -p 8000:8000 -p 9443:9443 --name portainer \
    --restart=always \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v portainer_data:/data \
    portainer/portainer-ce:latest

echo "Setup complete! You can access Portainer at: https://<RASPBERRY_PI_IP>:9443"
echo "cleaning up temporary repository files..."
wait 5
    echo "🧹 Cleaning up temporary repository files..."
     Find the path where the script is running from, and go up one level
     CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
     PROJECT_ROOT="$(dirname "$CURRENT_DIR")"

    # Ensure we don't accidentally delete the system root!
    if [[ "$PROJECT_ROOT" == /home/* ]]; then
        echo "🗑️ Deleting project folder: $PROJECT_ROOT"
        rm -rf "$PROJECT_ROOT"
    fi
else
    echo "⚠️ Docker containers failed to start. Please check the logs. Skipping cleanup."
fi

echo "✅ Host provisioning & deployment complete!"
echo "⚠️ Please note: Group permissions (docker, i2c, dialout, video) require a re-login or reboot to take effect."
echo "🔄 Rebooting the system in 5 seconds to apply changes..."
wait 5
sudo reboot
