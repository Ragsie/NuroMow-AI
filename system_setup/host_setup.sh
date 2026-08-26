#!/bin/bash
# Complete Docker Host Provisioning Script for "Worx ROS 2 Mower" (Orange Pi 5 Edition)
# Target OS: Ubuntu (Joshua Riek / Orange Pi OS) for RK3588

if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run with sudo!"
  exit 1
fi

echo "Preparing Orange Pi 5 host machine for Docker-based Worx Mower..."

# 1. Debloat
echo "Removing bloatware..."
sudo systemctl stop snapd
sudo apt-get purge cloud-init snapd modemmanager multipath-tools unattended-upgrades -y
sudo apt-get autoremove -y

# 2. Update packages
echo "Updating system..."
sudo apt-get update && sudo apt-get upgrade -y

# 3. Grant hardware permissions (NPU, Serial, Video)
echo "Granting user permissions for NPU, Serial, and Video..."
sudo usermod -aG dialout "$USER"
sudo usermod -aG video "$USER"

# Ensure the NPU device has the right permissions (if it exists)
if [ -e /dev/rknn ]; then
  sudo chmod 0666 /dev/rknn
fi

# 4. Install Docker
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

echo "Rebooting the system to apply changes..."
sudo reboot
