# 🚜 Worx ROS 2 Autonomous Mower

[![Status: ALPHA](https://img.shields.io/badge/Status-ALPHA-red.svg)](#) [![Build Worx Mower Containers](https://github.com/Ragsie/worx-ros2-mower/actions/workflows/docker_build.yml/badge.svg)](https://github.com/Ragsie/worx-ros2-mower/actions/workflows/docker_build.yml) [![ROS 2](https://img.shields.io/badge/ROS_2-Humble-blue?logo=ros)](https://docs.ros.org/en/humble/index.html) [![CI Pipeline](https://github.com/Ragsie/worx-ros2-mower/actions/workflows/code_check.yml/badge.svg)](https://github.com/Ragsie/worx-ros2-mower/actions/workflows/code_check.yml) [![Docker YOLO](https://img.shields.io/docker/pulls/ragsie/worx-yolo-safety?logo=docker&label=YOLO)](https://hub.docker.com/r/ragsie/worx-yolo-safety) [![Docker ROSBridge](https://img.shields.io/docker/pulls/ragsie/worx-rosbridge?logo=docker&label=ROSBridge)](https://hub.docker.com/r/ragsie/worx-rosbridge)



> **🚧 ALPHA software and hardware setup 🚧**
> *Damage to your equipment may occur. Use at your own risk.*

## 💡 Why This Project?
Taking my old Landroid mower and making it SMART.

This project started out of frustration: my current Worx M600 Plus has a bad habit of digging holes in my lawn instead of cutting the grass. Rather than just buying a new mower, I decided to build my own and learn a new tech stack along the way. While there are plenty of open-source DIY mowers available, my goal is to build this from the ground up to deeply understand the mechanics and software behind it. I want to learn by doing, not just by copying and pasting an existing setup.

I'll document the whole journey here. If you have a mower tearing up your lawn too, I hope this can serve as some inspiration for your own build.

## 🤖 About The Project
An advanced, fully autonomous lawn mower built on a Worx Landroid chassis. This project upgrades the original hardware with a modern ROS 2 (Humble/Jazzy) stack, VESC motor controllers, I2C Time-of-Flight (ToF) sensors, and real-time AI vision using YOLO26 for ultimate safety.

### 🌟 Features
* **ROS 2 Nav2:** Dynamic path planning and obstacle avoidance.
* **YOLO26 AI Vision:** Real-time object detection (detects humans, pets, and custom trained objects like toys and animal waste) to trigger immediate emergency stops.
* **VESC Motor Control:** Smooth and powerful control of the drive wheels via CAN-bus.
* **Micro-ROS:** Seamless communication between the main computer and the ESP32 drive controllers.
* **100% Dockerized:** The entire brain (ROS 2, AI, Sensor nodes) runs in isolated Docker containers for extreme reliability and instant booting.

---

## 📚 Documentation (Wiki)
To keep this repository clean and easy to navigate, all detailed documentation, installation guides, parts lists, and diagrams have been moved to the **Project Wiki**.

**👉 [Click here to read the full Wiki Docs](https://github.com/Ragsie/worx-ros2-mower/wiki)**

In the Wiki you will find:
* **[Bill of Materials (Hardware & Components)](https://github.com/Ragsie/worx-ros2-mower/wiki/2-%F0%9F%9B%A0%EF%B8%8F-Hardware-&-Setup)**
* **[Project Roadmap & Phases](https://github.com/Ragsie/worx-ros2-mower/wiki/1-%F0%9F%9A%9C-Worx-ROS-2-Autonomous-Mower#3-pending-tasks-to-do)**
* **[Full Installation Guide (Host & ESP32)](https://github.com/Ragsie/worx-ros2-mower/wiki/4-%F0%9F%93%81-Codebase-Reference)**
* **[System Diagrams (Power & Data Flow)](https://github.com/Ragsie/worx-ros2-mower/wiki/2-%F0%9F%9B%A0%EF%B8%8F-Hardware-&-Setup#-power-distribution-power-bus)**

---

## ☕ Support The Project
If this project helped you or inspired your own build, consider buying me a cup of coffee. It would make my day and support me in developing more!

| Coin | QR | Address |
| :-- | :--- | :---: |
| **Bitcoin Cash** | <img width="160" height="161" alt="qrcode" src="https://github.com/user-attachments/assets/254aece9-8957-4d34-812c-885ac2e839fa" /> | `bitcoincash:qzp4c7klef8q6gxycvc84dx0fnhnfxkkpy6xda56h3` |
| **Bitcoin** | <img width="160" height="162" alt="image" src="https://github.com/user-attachments/assets/e5b1cd3d-fd26-46fc-88db-2aa931b4f5d4" /> | `3QrAPVGC3aypf3LG5DYYRnjwjKuFMzkeJE` |