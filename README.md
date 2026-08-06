# Landroid_Mower_Upgrade
Taking my old landroid mower, and make it SMART.

#Why
This project started out of frustration: my current Worx M600 Plus has a bad habit of digging holes in my lawn instead of cutting the grass. Rather than just buying a new mower, I decided to build my own and learn a new tech stack along the way. While there are plenty of open-source DIY mowers available, my goal is to build this from the ground up to deeply understand the mechanics and software behind it. I want to learn by doing, not just by copying and pasting an existing setup.

I'll document the whole journey here. If you have a mower tearing up your lawn too, I hope this can serve as some inspiration for your own build.


## 🛠️ Hardware & Components (Bill of Materials)

Here is the complete overview of all components, controllers, and wiring used for the mower and the RTK base station.

| Category | Component / Model | Qty | Purpose in Project | Link |
| :--- | :--- | :---: | :---: | :--- |
| **GNSS / RTK** | Quectel LC29H(BS) | 1 | Fixed base station module (generates RTCM3). | [Link]() |
| **GNSS / RTK** | Quectel LC29H(DA) | 1 | Mounted in the rover for cm-precise positioning. | [Link]() |
| **GNSS / RTK** | Harxon Helix HX-103B | 2 | L1/L5 Dual-Band antennas (1x Base, 1x Rover). | [Link]() |
| **Communication** | EBYTE E32-900T20D-V8 | 2 | LoRa Transceiver (868/915 MHz transparent UART link). | [Link]() |
| **Motor Control** | Autoro Single ESC V6.7 BLDC FOC | 1 | Controls the mower motors.* | [Link]() |
| **Motor Control** | Autoro Dual ESC V6.7 BLDC FOC | 1 | Controls the wheels motor.* | [Link]() |
| **Power & Logic** | PLR Mini560 / Pro | 2 | Steps down battery voltage (18-28V) to clean 5V/3.3V. | [Link]() |
| **Power & Logic** | 230V to 5V USB Power Supply | 1 | Permanent power supply for the indoor base station. | [Link]() |
| **Power** | YOUME 5200mAh LiPo 6S 22.2V XT60 | 1 | Main battery power for the robot. | [Link]() |
| **Power & Logic** | Daly Smart BMS 60A | 1 | Battery Management System for safe charging/discharging. | [Link]() |
| **Safety** | 40A Car Relay + Blade Fuse Holder | 1 | Hardware E-Stop (cuts main power when Worx shield is hit). | [Link]() |
| **Cables & Plugs** | XT60 + 12-14 AWG Silicone Wire | 1 | High-current power distribution from battery to motors. | [Link]() |
| **Cables & Plugs** | Dupont / JST Wires (24-26 AWG) | 1 | Signal lines and data connections (UART, TX/RX, I2C). | [Link]() |
| **Enclosure** | IP65/IP67 Plastic Junction Box | 1 | Waterproof housing for the outdoor base station electronics. | [Link]() |
| **Navigation** | Raspberry Pi 5 8MP IMX219 (77°) | 1 | Camera module used for visual navigation/obstacle detection. | [Link]() |
| **Navigation** | VL53L5X V2 ToF Laser (8x8) | 2 | Time-of-Flight sensors for short-range obstacle avoidance. | [Link]() |
| **Navigation** | BNO085 IMU | 1 | 9-axis motion sensor for accurate heading and odometry. | [Link]() |
| **Logic** | ESP32 Microcontroller | 2 | Low-level hardware controller (VESC communication & sensors). | [Link]() |
| **Logic** | Raspberry Pi 4B | 1 | The central brain running ROS 2 and Nav2. | [Link]() |
| **Tools / Test** | CP2102 USB-to-UART Adapter | 1 | Used for initial PC configuration of GPS and LoRa modules. | [Link]() |

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

### 🔌 Power Distribution (Power Bus)

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
