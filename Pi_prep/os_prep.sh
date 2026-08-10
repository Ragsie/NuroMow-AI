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
# Note: raspi-config might not be installed by default on plain Ubuntu Server.
# If it fails, I2C can also be enabled by adding 'dtparam=i2c_arm=on' to /boot/firmware/config.txt
sudo apt-get install raspi-config -y || true
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0

# 4. Grant hardware permissions to the current user (and Docker daemon)
echo "🔑 Granting user permissions for I2C, Serial (USB), and Video (Camera)..."
sudo usermod -aG i2c $USER 
sudo usermod -aG dialout $USER
sudo usermod -aG video $USER

# 5. Install Docker and Docker Compose
echo "🐳 Installing Docker Engine and Docker Compose..."
# Remove any old conflicting packages
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove -y $pkg; done

# Add Docker's official GPG key and repository
sudo apt-get update
sudo apt-get install ca-certificates curl -y
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install the actual Docker packages
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y

# Add current user to the Docker group so you can run containers without 'sudo'
sudo usermod -aG docker $USER

echo "✅ Host provisioning complete! The system is fully ready for docker-compose."
echo "⚠️  Please REBOOT your machine now by typing: sudo reboot"