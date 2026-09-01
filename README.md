# 🚜 NuroMow Autonomous LawnMower

[![Status: ALPHA](https://img.shields.io/badge/Status-ALPHA-red.svg)](#) [![Build Worx Mower Containers](https://github.com/Ragsie/NuroMow-AI/actions/workflows/docker_build.yml/badge.svg)](https://github.com/Ragsie/NuroMow-AI/actions/workflows/docker_build.yml) [![ROS 2](https://img.shields.io/badge/ROS_2-Humble-blue?logo=ros)](https://docs.ros.org/en/humble/index.html) [![Wiki Docs](https://img.shields.io/badge/Docs-Wiki-blue?logo=github)](https://github.com/Ragsie/NuroMow-AI/wiki) [![CI Pipeline](https://github.com/Ragsie/NuroMow-AI/actions/workflows/code_check.yml/badge.svg)](https://github.com/Ragsie/NuroMow-AI/actions/workflows/code_check.yml) [![Docker AIVision](https://img.shields.io/docker/pulls/ragsie/worx-stereo-vision?logo=docker&label=worx-stereo-vision)](https://hub.docker.com/r/ragsie/worx-stereo-vision) [![Docker ROSBridge](https://img.shields.io/docker/pulls/ragsie/worx-rosbridge?logo=docker&label=ROSBridge)](https://hub.docker.com/r/ragsie/worx-rosbridge)


### 🚧 ALPHA software and hardware setup 🚧
* damage to your equipment may occur.

# NuroMow AI
Taking my old Landroid mower, and making it SMART with NuroMow AI.

### The Companion App 📱 [![Build and Release NuroMow AI](https://github.com/Ragsie/NuroMow-AI_app/actions/workflows/build.yml/badge.svg)](https://github.com/Ragsie/NuroMow-AI_app/actions/workflows/build.yml)
Control and monitor the mower in real-time with the official Flutter companion app! 
👉 **[Get the NuroMow AI App here](https://github.com/Ragsie/NuroMow-AI_app)** 

### Why
This project started out of frustration: my current Worx M600 Plus has a bad habit of digging holes in my lawn instead of cutting the grass. Rather than just buying a new mower, I decided to build my own and learn a new tech stack along the way. While there are plenty of open-source DIY mowers available, my goal is to build this from the ground up to deeply understand the mechanics and software behind it. I want to learn by doing, not just by copying and pasting an existing setup.

I'll document the whole journey here. If you have a mower tearing up your lawn too, I hope this can serve as an inspiration for your own build.

### 🤖 NuroMow AI Architecture
An advanced, fully autonomous lawn mower built on a Worx Landroid chassis. This project upgrades the original hardware with a modern ROS 2 (Humble/Jazzy) stack, VESC motor controllers, and real-time depth and AI vision using YOLO26n-seg retrained on a my own dataset for ultimate safety.

#### 🌟 Features
*   **ROS 2 Nav2:** Dynamic path planning and obstacle avoidance.
*   **AI Vision:** Real-time object detection (detects humans, pets, and custom trained objects like toys and animal waste) to trigger immediate emergency stops.
*   **Depth Vision:** A stereo camera providing visual navigation data to the mower, working in tandem with AI Vision.
*   **VESC Motor Control:** Smooth and powerful control of the drive wheels via CAN-bus.
*   **Micro-ROS:** Seamless communication between the main computer and the ESP32 drive controllers.
*   **100% Dockerized:** The entire brain (ROS 2, AI, Sensor nodes) runs in isolated Docker containers for extreme reliability and instant booting.
*   **AI Updates:** Regular AI model updates with automatic download and setup (see [wiki](https://github.com/Ragsie/NuroMow-AI/wiki)). The MowerAI is a YOLO26n-seg model, retrained on my own dataset and converted for deployment.

---

## 📚 Documentation (Wiki)
To keep this repository clean and easy to navigate, all detailed documentation, installation guides, parts lists, and diagrams have been moved to the **Project Wiki**.

**👉 [Click here to read the full Wiki Docs](https://github.com/Ragsie/NuroMow-AI/wiki)**

In the Wiki you will find:
* **[Bill of Materials (Hardware & Components)](https://github.com/Ragsie/NuroMow-AI/wiki/2-%F0%9F%9B%A0%EF%B8%8F-Hardware-&-Setup)**
* **[Project Roadmap & Phases](https://github.com/Ragsie/NuroMow-AI/wiki/1-%F0%9F%9A%9C-Worx-ROS-2-Autonomous-Mower#3-pending-tasks-to-do)**
* **[Full Installation Guide (Host & ESP32)](https://github.com/Ragsie/NuroMow-AI/wiki/4-%F0%9F%93%81-Codebase-Reference)**
* **[System Diagrams (Power & Data Flow)](https://github.com/Ragsie/NuroMow-AI/wiki/2-%F0%9F%9B%A0%EF%B8%8F-Hardware-&-Setup#-power-distribution-power-bus)**

---

# License, Credits & Inspiration 🛠️

This project is built upon the fantastic work of the open-source community, but with a completely unique hardware philosophy.

### 🔌 Hardware Philosophy: 100% Off-The-Shelf (DIY)
While the original OpenMower project by Clemens Elflein is primarily designed to run on his custom, proprietary replacement motherboards, **this AI project is built 100% on standardized, off-the-shelf (OTS) components**. 

the plan is to strip all the original electronics from a Worx lawnmower chassis and rebuilt it completely from scratch using:
*   **Orange Pi 5 Ultra** (Main computer with hardware NPU acceleration)
*   **ESP32** & **Autoro VESC 6.7 ESCs** (Drive and cutter motor control) 
*   **Quectel LC29H** (Budget-friendly, millimeter-precise RTK-GNSS) 
*   **GXIVISION 3D Stereo USB Camera** (Real-time AI vision and e-stop) 

This makes our hardware platform extremely inexpensive, highly accessible, and completely independent of proprietary hardware manufacturers!

### 🤝 Acknowledgement of Software & Concepts
Although the hardware architecture is OFF the shelf components, I would like to send a huge thank you to the projects that have inspired us and provided the software building blocks we use under the hood:

*   **[OpenMower](https://github.com/ClemensElflein/OpenMower) by Clemens Elflein:** For the pioneering concept of converting Worx chassises into RTK-guided ROS robots (licensed under GPL-3.0)
*   **[YOLO26n-seg by Ultralytics](https://github.com/ultralytics/ultralytics):** For the lightning-fast AI segmentation system running locally on the NPU (licensed under AGPL-3.0)
*   **[ROS 2 (Robot Operating System)](https://www.ros.org/):** The robust middleware framework driving our entire messaging and node architecture (licensed under Apache 2.0) 
*   **[micro-ROS](https://micro.ros.org/):** For bringing ROS 2 seamlessly onto our ESP32 microcontroller (licensed under Apache 2.0)

---

## ☕ Support The Project
If this project helped you or inspired your own build, consider buying me a cup of coffee. It would make my day and support me in developing more!
please note that this project is, and will always remain, **100% free and open-source** under the **GNU GPLv3 License** in accordance with the licenses of our upstream dependencies.

* **Buy Me A coffie:**  https://buymeacoffee.com/Ragsie

| Coin | QR | Address |
| :-- | :--- | :---: |
| **Bitcoin Cash** | <img width="160" height="161" alt="qrcode" src="https://github.com/user-attachments/assets/254aece9-8957-4d34-812c-885ac2e839fa" /> | `bitcoincash:qzp4c7klef8q6gxycvc84dx0fnhnfxkkpy6xda56h3` |
| **Bitcoin** | <img width="160" height="162" alt="image" src="https://github.com/user-attachments/assets/e5b1cd3d-fd26-46fc-88db-2aa931b4f5d4" /> | `3QrAPVGC3aypf3LG5DYYRnjwjKuFMzkeJE` |
