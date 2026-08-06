# Landroid_Mower_Upgrade
Taking my old landroid mower, and make it SMART.

#Why
This project started out of frustration: my current Worx M600 Plus has a bad habit of digging holes in my lawn instead of cutting the grass. Rather than just buying a new mower, I decided to build my own and learn a new tech stack along the way. While there are plenty of open-source DIY mowers available, my goal is to build this from the ground up to deeply understand the mechanics and software behind it. I want to learn by doing, not just by copying and pasting an existing setup.

I'll document the whole journey here. If you have a mower tearing up your lawn too, I hope this can serve as some inspiration for your own build.


## 🛠️ Hardware & Components (Bill of Materials)

Here is a list of the hardware I am using for this build. 

| Component / Part | Purpose in Project | Qty | Status | Link / Info |
| :--- | :--- | :---: | :--- | :--- |
| **Worx Landroid M600 Plus** | Donor chassis (motors, wheels, floating shield for collision). | 1 | Owned | - |
| **Raspberry Pi 4B** | The Brain. Runs ROS 2 (Nav2) and handles path planning. | 1 | Owned | - |
| **ESP32** | Low-level controller. Reads Hall-sensors (collision) and commands VESCs. | 1 | To buy | - |
| **Quectel LC29H** | RTK-GPS Modules for centimeter precision (1 for Base, 1 for Rover). | 2 | Ordered | [Insert Link] |
| **EBYTE LoRa Module** | Wireless transmission of RTCM data from Base to Rover. | 2 | Ordered | [Insert Link] |
| **VESC / Motor Controllers** | Precise control of the drive and mower motors. | - | Planning | - |
| **Mini560 Pro** | Buck converters to safely step down 6S battery power to 5V logic. | - | Ordered | - |


## 🗺️ Project Roadmap

For now to keep things manageable, I have divided the build into logical phases:

### Phase 1: Teardown & Power Routing
- [ ] Strip the Worx M600 of its original mainboard.
- [ ] Map out the original wiring (motors, Hall sensors).
- [ ] Install the 6S BMS and route power safely through fuses.
- [ ] Install Mini560 Pro buck converters for clean 5V to the Pi and GPS.

### Phase 2: RTK-GPS Base Station
- [ ] Configure Quectel LC29H as Base (Survey-in/Fixed mode) via PC.
- [ ] Configure EBYTE LoRa modules (matching baud rate and channel).
- [ ] Direct hardware wiring: Base GPS (TX) -> Base LoRa (RX). No microcontroller needed.

### Phase 3: Rover Low-Level (ESP32)
- [ ] Code PlatformIO on ESP32 to communicate with VESC controllers.
- [ ] Wire the Worx floating shield's Hall sensors directly to the ESP32 for hardware E-stop.
- [ ] Direct hardware wiring: Rover LoRa (TX) -> Rover GPS UART2 (RX).

### Phase 4: Rover High-Level (ROS 2 & Pi 4)
- [ ] Install ROS 2 and configure Nav2 on the Raspberry Pi.
- [ ] Feed RTK-fixed NMEA data from the Quectel GPS to ROS via USB.
- [ ] Implement Smac Planner to allow for reversing (Y-turns in sharp corners).

### Phase 5: Field Testing & Tuning
- [ ] Record the first geofence polygon using a controller.
- [ ] Test the physical collision detection (floating shield vs. objects).
- [ ] Fine-tune the 90-degree corner navigation.

### Extras that did not fit phase 1-5



# 📐 Diagrams

###🔌 Power Distribution (Power Bus)

Here is a diagram of the Power Distribution (changes may occur)
```
=================================================================================
                            POWER DISTRIBUTION (POWER BUS)
=================================================================================

  [ 6S LiPo Battery (22.2V nominal / 25.2V full) ]
               │
               ▼
      [ Daly 6S BMS (60A) ]
               │
               ▼
      [ 40A Main Fuse ]
               │
      ┌────────┴────────────────────────┬─────────────────────────────────┐
      │ (22.2V Main Bus)                │                                 │
      ▼                                 ▼                                 ▼
 [ Autoro Dual ESC ]          [ Automotive Relay / E-Stop ]     [ Optional 3A-5A Fuse ]
 (Drive Motors L + R)                   │                                 │
                                        ▼                         ┌───────┴───────┐
                              [ Autoro Single ESC ]               ▼               ▼
                              (Mower Motor)               [ Mini560 Pro ]  [ Mini560 Pro ]
                                                           (For Pi 4B)     (Electronics)
                                                                  │               │
                                                                  ▼               ▼
                                                          [ Pi 4B (5V) ]   [ ESP32/Sens ]
```

### 🔀 Data & Signal Flow

Here is a diagram of how the logic is gonna be connected. (changes may occur)

```
=================================================================================
                      2. DATA & SIGNAL FLOW (ROS 2 & SENSORS)
=================================================================================

 BASE STATION (Stationary in garden/house):
 [ 230V -> 5V ] ──> [ Quectel LC29H (BS) ] ──> [ E32 LoRa Tx ] ──( 868 MHz Radio )──┐
                          │                                                         │
                     (Harxon Ant.)                                                  │
                                                                                    │
────────────────────────────────────────────────────────────────────────────────────│
 ROVER / ROBOT:                                                                     │
                     (Harxon Ant.)                                                  │
                          │                                                         │
 [ EBYTE E32 LoRa Rx ] ───┴──> [ Quectel LC29H (DA) ]                               │
                                       │                                            │
                                  (USB / NMEA)                                      │
                                       ▼                                            │
 [ Pi Camera IMX219 ] ──(CSI Cable)──> [ Raspberry Pi 4B ] <────────────────────────┘
 [ BNO085 IMU ] ───────(I2C - Pin 3,5)─>   (ROS 2 / Nav2)
 [ 2x VL53L5X ToF ] ───(I2C + XSHUT)──>      │
                                             │ (USB Serial - micro-ROS @ 921600 baud)
                                             ▼
                                    [ ESP32 Drive MCU ]
                                             │
                                       (CAN-bus / TWAI)
                                             │
                                ┌────────────┴────────────┐
                                ▼                         ▼
                       [ Autoro Dual ESC ]       [ Autoro Single ESC ]
                       (Wheels L+R Encoder)       (Mower Telemetry)

 ```
