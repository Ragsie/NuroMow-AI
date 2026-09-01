#!/usr/bin/env bash
# NuroMow Værtsopsætning til Orange Pi 5 Ultra (RK3588, Ubuntu 22.04 LTS / Debian 12)
set -e

echo "=== Initialiserer NuroMow Host Setup ==="

# 1. Opret eller indlæs central konfigurationsfil (nuromow.env) 🆕 [HELT NY INTEGRATION: Single Source of Truth]
ENV_FILE="$(dirname "$0")/nuromow.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Ingen nuromow.env fundet. Opretter standard konfiguration..."
    sudo mkdir -p /etc/nuromow
    # Kopier/opret fil med standardværdier
    sudo tee "$ENV_FILE" > /dev/null << 'EOF'
NUROMOW_TRACK_WIDTH=0.40
NUROMOW_ROBOT_RADIUS=0.28
NUROMOW_NAV2_INFLATION_RADIUS=0.48
NUROMOW_VESC_LEFT_ID=1
NUROMOW_VESC_RIGHT_ID=2
NUROMOW_CAMERA_BASELINE=0.06
NUROMOW_CAMERA_FOCAL_LENGTH=350.0
NUROMOW_CAMERA_HEIGHT_Z=0.10
NUROMOW_CAMERA_OFFSET_X=0.25
NUROMOW_CAMERA_PITCH_Y=0.0
NUROMOW_GPS_OFFSET_X=-0.15
NUROMOW_GPS_HEIGHT_Z=0.25

# --- MLOPS / LOKAL NFS AI TRÆNINGSSERVER ---
# Angiv IP på din lokale GPU server (f.eks. 192.168.1.100). Lad være tom ("") hvis ikke brugt.
NUROMOW_NFS_SERVER_IP=""
NUROMOW_NFS_SHARE="/mnt/nfs/nuromow_raw"
EOF
    # Opret også et link i /etc til nem adgang
    sudo ln -sf "$(realpath "$ENV_FILE")" /etc/nuromow/nuromow.env
fi

# Eksporter variabler, så de er tilgængelige i systemet under kørslen
export $(grep -v '^#' "$ENV_FILE" | xargs)

# 2. Opdater system og installer grundlæggende værktøjer + NFS support
sudo apt-get update && sudo apt-get install -y     curl     git     udev     can-utils     v4l-utils     python3-pip     nfs-common

# 2.5 Opret datamapper og opsæt eventuel NFS Auto-mount til AI-træningsserver
echo "Konfigurerer datamapper og filsystem..."
sudo mkdir -p /opt/nuromow/models
sudo mkdir -p /opt/nuromow/incoming_raw
sudo chmod -R 777 /opt/nuromow

# 🆕 [TILFØJET: Opret persistent statistik-fil til kilometertæller og driftstimer]
if [ ! -f /opt/nuromow/stats.json ]; then
    echo '{"total_distance_km": 0.0, "total_runtime_hours": 0.0}' | sudo tee /opt/nuromow/stats.json
    sudo chmod 777 /opt/nuromow/stats.json
fi

if [ -n "$NUROMOW_NFS_SERVER_IP" ]; then # 🆕 [OPDATERET: Tilføjet robust NFS systemd-automount til MLOps]
    echo "Lokal AI Træningsserver fundet ($NUROMOW_NFS_SERVER_IP). Konfigurerer systemd-automount i /etc/fstab..."
    # Kontroller om linjen allerede findes
    if ! grep -q "$NUROMOW_NFS_SHARE" /etc/fstab; then
        echo "Tilføjer mount-regel til /etc/fstab..."
        echo "${NUROMOW_NFS_SERVER_IP}:${NUROMOW_NFS_SHARE} /opt/nuromow/incoming_raw nfs defaults,noauto,x-systemd.automount,x-systemd.device-timeout=10,_netdev,rw,nofail 0 0" | sudo tee -a /etc/fstab
    fi
    echo "Genindlæser systemd og mounter NFS..."
    sudo systemctl daemon-reload || true
    sudo mount /opt/nuromow/incoming_raw || true
else
    echo "Ingen lokal NFS AI-træningsserver angivet i nuromow.env. Billeder gemmes lokalt på NVMe-disken."
fi

# 3. Installer Docker og konfigurer tilladelser
if ! [ -x "$(command -v docker)" ]; then
    echo "Docker ikke fundet. Installerer Docker Engine..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

# 4. Opret udev-regler for at give faste symbolske links til hardwaren
echo "Konfigurerer udev-regler for USB-enheder (ESP32, GPS, Kamera)..."
sudo tee /etc/udev/rules.d/99-nuromow.rules << 'EOF'
# ESP32 Micro-ROS Controller (CP2102 USB-to-UART)
SUBSYSTEMS=="usb", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="ttyUSB_esp32", MODE="0666"

# Quectel LC29H RTK-GPS Modtager (Rover)
SUBSYSTEMS=="usb", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="ttyUSB_gps_rover", MODE="0666"

# GXIVISION 3D Stereo Kamera (USB-enhed)
SUBSYSTEMS=="video4linux", ATTRS{idVendor}=="0c45", ATTRS{idProduct}=="6366", SYMLINK+="video_stereo", MODE="0666"
EOF

# Genindlæs udev-regler
sudo udevadm control --reload-rules && sudo udevadm trigger
echo "Udev-regler genindlæst. Enheder vil nu få korrekte navne (f.eks. /dev/ttyUSB_esp32)."

# 5. Optimer ydelsesprofilen (Set CPU & NPU Governors til 'performance')
echo "Sætter RK3588 CPU- og NPU-kerner til Performance-mode..."
echo "performance" | sudo tee /sys/devices/system/cpu/cpufreq/policy0/scaling_governor || true
echo "performance" | sudo tee /sys/devices/system/cpu/cpufreq/policy4/scaling_governor || true
echo "performance" | sudo tee /sys/devices/system/cpu/cpufreq/policy6/scaling_governor || true
echo "performance" | sudo tee /sys/class/devfreq/fb000000.npu/governor || true

echo "=== System Setup Gennemført! ==="