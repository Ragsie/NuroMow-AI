#!/bin/bash
# --- STARTUP SCRIPT FOR STEREO VISION NODE ---

# Define paths
NFS_DEPLOY_MODEL="/mnt/truenas_deploy/yolo26n-seg.rknn"
LOCAL_MODEL="/app/yolo26n-seg.rknn"

echo "Checking for updated AI model on TrueNAS..."

# 1. Check if the NFS mount is reachable and the model exists
if [ -f "$NFS_DEPLOY_MODEL" ]; then
    
    # 2. Check if the network model is newer than our local model, OR if we have no local model yet
    if [ "$NFS_DEPLOY_MODEL" -nt "$LOCAL_MODEL" ] || [ ! -f "$LOCAL_MODEL" ]; then
        echo "🚀 New model detected on the server! Downloading to robot..."
        cp "$NFS_DEPLOY_MODEL" "$LOCAL_MODEL"
        echo "✅ Update complete."
    else
        echo "👍 Local model is already up to date."
    fi

else
    echo "⚠️ WARNING: Could not reach TrueNAS or deploy folder is empty."
    echo "Fallback: Proceeding with existing local model (if available)."
fi

# 3. Start the actual ROS 2 Node
echo "Starting Stereo Vision ROS 2 Node..."
exec python3 stereo_node.py
