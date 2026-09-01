#!/bin/bash
# --- STARTUP SCRIPT FOR STEREO VISION NODE ---

echo "Starting ROS 2 Launch sequence..."
# Assumes the AI model is baked into the /app directory via Docker build
exec ros2 launch /app/launch/mower.launch.py
