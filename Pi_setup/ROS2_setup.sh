#!/bin/bash
# Complete Provisioning Script for "Worx ROS 2 Mower"
# Target OS: Ubuntu Server 24.04 LTS (64-bit) for Raspberry Pi 4B
# Note: Run this script as a normal user with sudo privileges.

echo "🚀 Starting installation for the Worx Mower Brain..."

# 1. Remove unnecessary background services (Debloat to save CPU/RAM)
echo "🧹 Removing background bloatware (snapd, cloud-init, modemmanager, etc.)..."
sudo systemctl stop snapd
sudo apt-get purge cloud-init snapd modemmanager multipath-tools unattended-upgrades -y
sudo apt-get autoremove -y

# 2. Update and upgrade the system
echo "🔄 Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# 3. Enable I2C (for VL53L5X ToF sensors) and SPI
echo "🔌 Enabling I2C and SPI interfaces..."
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0
# Add current user to the i2c group to allow sensor reading without sudo
sudo usermod -aG i2c $USER 

# 4. Install ROS 2 Jazzy (Base version without heavy desktop GUI)
echo "🤖 Installing ROS 2 Jazzy..."
sudo apt-get install software-properties-common curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt-get update
sudo apt-get install ros-jazzy-ros-base python3-colcon-common-extensions -y

# 5. Install Nav2 (Navigation and Routing)
echo "🗺️ Installing Nav2 routing engine..."
sudo apt-get install ros-jazzy-navigation2 ros-jazzy-nav2-bringup -y

# 6. Install Micro-ROS Agent (For ESP32 communication)
echo "📡 Setting up Micro-ROS Agent..."
mkdir -p ~/microros_ws/src
cd ~/microros_ws/src
git clone -b jazzy https://github.com/micro-ROS/micro_ros_setup.git
cd ~/microros_ws
source /opt/ros/jazzy/setup.bash
sudo apt-get install python3-rosdep -y
sudo rosdep init || true # Ignores error if rosdep is already initialized
rosdep update
rosdep install --from-paths src --ignore-src -y
colcon build
source install/local_setup.bash
ros2 run micro_ros_setup create_agent_ws.sh
ros2 run micro_ros_setup build_agent.sh

# 7. Install Camera (IMX708) and AI (YOLO) dependencies
echo "📷 Installing camera tools and YOLOv8 for 'Stop & Think' AI vision..."
sudo apt-get install libcamera-apps python3-opencv python3-pip -y
# Note: Ubuntu 24.04 enforces virtual environments for Python. 
# We use --break-system-packages because this is a dedicated, single-purpose robot device.
pip3 install ultralytics smbus2 --break-system-packages

# 8. Configure .bashrc to auto-source ROS 2 environments
echo "⚙️ Configuring .bashrc..."
if ! grep -q "ros/jazzy/setup.bash" ~/.bashrc; then
    echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
fi
if ! grep -q "microros_ws/install/local_setup.bash" ~/.bashrc; then
    echo "source ~/microros_ws/install/local_setup.bash" >> ~/.bashrc
fi

echo "✅ Setup complete! The system is fully provisioned."
echo "⚠️  Please REBOOT your Raspberry Pi now by typing: sudo reboot"
