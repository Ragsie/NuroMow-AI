# Landroid_Mower_Upgrade
Taking my old landroid mower, and make it SMART.

# Why

This project started out of frustration: my current Worx M600 Plus has a bad habit of digging holes in my lawn instead of cutting the grass. Rather than just buying a new mower, I decided to build my own and learn a new tech stack along the way. While there are plenty of open-source DIY mowers available, my goal is to build this from the ground up to deeply understand the mechanics and software behind it. I want to learn by doing, not just by copying and pasting an existing setup.

I'll document the whole journey here. If you have a mower tearing up your lawn too, I hope this can serve as some inspiration for your own build.


## 🛠️ Hardware & Components (Bill of Materials)

Here is the complete overview of all components, controllers, and wiring used for the mower and the RTK base station.

(PARTS LIST IS NOT FINAL!)

| Category | Component / Model | Qty | Purpose in Project | Link |
| :--- | :--- | :---: | :---: | :--- |
| **GNSS / RTK** | Quectel LC29H(BS) | 1 | Fixed base station module (generates RTCM3). | [Link](https://www.aliexpress.com/item/1005009996916880.html?spm=a2g0o.cart.0.0.2c2938daZviOxL&mp=1&pdp_npi=6%40dis%21USD%21USD+61.03%21USD+51.88%21%21USD+51.88%21%21%21%402103138417863525074584952e1048%2112000050797148137%21ct%21DK%21753190223%21%211%210%21) |
| **GNSS / RTK** | Quectel LC29H(DA) | 1 | Mounted in the rover for cm-precise positioning. | [Link](https://www.aliexpress.com/item/1005009996916880.html?spm=a2g0o.cart.0.0.2c2938daZviOxL&mp=1&pdp_npi=6%40dis%21USD%21USD+53.46%21USD+45.44%21%21USD+45.44%21%21%21%402103138417863525074584952e1048%2112000050797148138%21ct%21DK%21753190223%21%211%210%21) |
| **GNSS / RTK** | Harxon Helix HX-103B | 2 | L1/L5 Dual-Band antennas (1x Base, 1x Rover). | [Link](https://www.aliexpress.com/item/1005011805699218.html?spm=a2g0o.cart.0.0.2c2938daZviOxL&mp=1&pdp_npi=6%40dis%21USD%21USD+21.88%21USD+20.79%21%21USD+20.79%21%21%21%402103138417863525074584952e1048%2112000056618951949%21ct%21DK%21753190223%21%212%210%21) |
| **Communication** | EBYTE E32-900T20D-V8 | 2 | LoRa Transceiver (868/915 MHz transparent UART link). | [Link](https://www.aliexpress.com/item/1005001781777362.html?spm=a2g0o.cart.0.0.2c2938daZviOxL&mp=1&pdp_npi=6%40dis%21USD%21USD+10.86%21USD+10.86%21%21USD+10.86%21%21%21%402103138417863525074584952e1048%2112000042933167507%21ct%21DK%21753190223%21%212%210%21) |
| **Motor Control** | Autoro Single ESC V6.7 BLDC FOC | 1 | Controls the mower motor.* | [Link](https://www.aliexpress.com/item/1005012438738094.html?spm=a2g0o.cart.0.0.2c2938daZviOxL&mp=1&pdp_npi=6%40dis%21USD%21USD+139.53%21USD+69.76%21%21USD+69.76%21%21%21%402103138417863525104625013e1048%2112000058389910753%21ct%21DK%21753190223%21%211%210%21) |
| **Motor Control** | Autoro Dual ESC V6.7 BLDC FOC | 1 | Controls the wheels motors.* | [Link](https://www.aliexpress.com/item/1005010188792018.html?spm=a2g0o.cart.similar_items.1.2c2938daZviOxL&utparam-url=scene%3Aimage_search%7Cquery_from%3Acart_soldout_item%7Cx_object_id%3A1005010188792018%7C_p_origin_prod%3A&algo_pvid=0bc93d53-c8f8-476f-99f1-03f2797cac93&algo_exp_id=0bc93d53-c8f8-476f-99f1-03f2797cac93&pdp_ext_f=%7B%22order%22%3A%2273%22%2C%22fromPage%22%3A%22search%22%7D&pdp_npi=6%40dis%21USD%21280.81%21126.37%21%21%211883.35%21847.51%21%402101c4ea17863530607622062e0d35%2112000051460636515%21sea%21DK%21753190223%21X%211%210%21n_tag%3A-29919%3Bd%3A3fc77c65%3Bm03_new_user%3A-29895) |
| **Power & Logic** | PLR Mini560 / Pro | 2 | Steps down battery voltage (18-28V) to clean 5V/3.3V. | [Link](https://www.aliexpress.com/item/1005005986412127.html?spm=a2g0o.cart.0.0.2c2938daZviOxL&mp=1&pdp_npi=6%40dis%21USD%21USD+7.61%21USD+2.29%21%21USD+2.29%21%21%21%402103138417863525074584952e1048%2112000035193851213%21ct%21DK%21753190223%21%215%210%21) |
| **Power & Logic** | 230V to 5V USB Power Supply | 1 | Permanent power supply for the indoor base station. | Link |
| **Power** | YOUME 5200mAh LiPo 6S 22.2V XT60 | 1 | Main battery power for the robot. | [Link](https://www.aliexpress.com/item/1005009973865436.html?spm=a2g0o.cart.0.0.2c2938daZviOxL&mp=1&pdp_npi=6%40dis%21USD%21USD+202.06%21USD+55.94%21%21USD+55.94%21%21%21%402103138417863525074584952e1048%2112000050808122502%21ct%21DK%21753190223%21%211%210%21) |
| **Power & Logic** | Daly Smart BMS 60A | 1 | Battery Management System for safe charging/discharging. | [Link](https://www.aliexpress.com/item/1005010106629071.html?spm=a2g0o.cart.0.0.2c2938daZviOxL&mp=1&pdp_npi=6%40dis%21USD%21USD+40.20%21USD+24.82%21%21USD+24.82%21%21%21%402103138417863525074584952e1048%2112000051168928142%21ct%21DK%21753190223%21%211%210%21) |
| **Safety** | 40A Car Relay + Blade Fuse Holder | 1 | Hardware E-Stop (cuts main power when Worx shield is hit). | Link |
| **Cables & Plugs** | XT60 + 12-14 AWG Silicone Wire | 1 | High-current power distribution from battery to motors. | Link |
| **Cables & Plugs** | Dupont / JST Wires (24-26 AWG) | 1 | Signal lines and data connections (UART, TX/RX, I2C). | Link |
| **Enclosure** | IP65/IP67 Plastic Junction Box | 1 | Waterproof housing for the outdoor base station electronics. | Link |
| **Navigation** | Raspberry Pi Camera Module 3 12 MP IMX708 | 1 | Camera module used for visual navigation/obstacle detection. | [Link](https://www.aliexpress.com/item/1005007870760347.html?spm=a2g0o.detail.pcDetailTopMoreOtherSeller.1.2959F7j2F7j2Ps&gps-id=pcDetailTopMoreOtherSeller&scm=1007.40050.354490.0&scm_id=1007.40050.354490.0&scm-url=1007.40050.354490.0&pvid=d96a0cbb-e2a6-48b2-b01f-b0a3f61b8196&_t=gps-id%3ApcDetailTopMoreOtherSeller%2Cscm-url%3A1007.40050.354490.0%2Cpvid%3Ad96a0cbb-e2a6-48b2-b01f-b0a3f61b8196%2Ctpp_buckets%3A668%232846%238116%232002&pdp_ext_f=%7B%22order%22%3A%22135%22%2C%22eval%22%3A%221%22%2C%22sceneId%22%3A%2230050%22%2C%22fromPage%22%3A%22recommend%22%7D&pdp_npi=6%40dis%21USD%2148.76%2139.98%21%21%21327.03%21268.16%21%400b88a96117863517429866605e0ed2%2112000056688947588%21rec%21DK%21753190223%21XZ%211%210%21n_tag%3A-29919%3Bd%3A3fc77c65%3Bm03_new_user%3A-29895&utparam-url=scene%3ApcDetailTopMoreOtherSeller%7Cquery_from%3A%7Cx_object_id%3A1005007870760347%7C_p_origin_prod%3A) |
| **Navigation** | VL53L5X V2 ToF Laser (8x8) | 2 | Time-of-Flight sensors for short-range obstacle avoidance. | [Link](https://www.aliexpress.com/item/1005006864257651.html?spm=a2g0o.cart.0.0.2c2938daZviOxL&mp=1&pdp_npi=6%40dis%21USD%21USD+60.39%21USD+19.50%21%21USD+19.50%21%21%21%402103138417863525104625013e1048%2112000038554217789%21ct%21DK%21753190223%21%212%210%21) |
| **Navigation** | BNO085 IMU | 1 | 9-axis motion sensor for accurate heading and odometry. | [Link](https://www.aliexpress.com/item/1005008036466921.html?spm=a2g0o.cart.0.0.2c2938daZviOxL&mp=1&pdp_npi=6%40dis%21USD%21USD+14.40%21USD+14.40%21%21USD+14.40%21%21%21%402103138417863525074584952e1048%2112000043355482441%21ct%21DK%21753190223%21%211%210%21) |
| **Logic** | ESP32 Microcontroller | 2 | Low-level hardware controller (VESC communication & sensors). | [Link](https://www.aliexpress.com/item/1005009127564554.html?spm=a2g0o.productlist.main.15.6b2e372d4RIHdW&algo_pvid=38f72514-61a4-4736-998a-d5fde7a06275&algo_exp_id=38f72514-61a4-4736-998a-d5fde7a06275-14&pdp_ext_f=%7B%22order%22%3A%22294%22%2C%22eval%22%3A%221%22%2C%22fromPage%22%3A%22search%22%7D&pdp_npi=6%40dis%21USD%214.85%214.85%21%21%214.85%214.85%21%402101ca9517863533363927998e0de5%2112000048011826632%21sea%21DK%21753190223%21X%211%210%21n_tag%3A-29919%3Bd%3A3fc77c65%3Bm03_new_user%3A-29895&curPageLogUid=BWnAthqSsFii&utparam-url=scene%3Asearch%7Cquery_from%3A%7Cx_object_id%3A1005009127564554%7C_p_origin_prod%3A) |
| **Logic** |  SN65HVD230 CAN Communication Module | 3 | ESP TWAI Can bus converter | [Link](https://www.aliexpress.com/item/1005009260778505.html?spm=a2g0o.productlist.main.4.2c616b58SjZNri&aem_p4p_detail=2026081002175612846935424996960001914278&algo_pvid=32880701-bc4d-4d52-b20b-f20503b5f8e8&algo_exp_id=32880701-bc4d-4d52-b20b-f20503b5f8e8-3&pdp_ext_f=%7B%22order%22%3A%22253%22%2C%22eval%22%3A%221%22%2C%22fromPage%22%3A%22search%22%7D&pdp_npi=6%40dis%21USD%212.12%212.12%21%21%2114.20%2114.20%21%402101d2e717863534764903511e0eba%2112000048518475670%21sea%21DK%21753190223%21X%211%210%21n_tag%3A-29919%3Bd%3A3fc77c65%3Bm03_new_user%3A-29895&curPageLogUid=S2uZIB9ohCEh&utparam-url=scene%3Asearch%7Cquery_from%3A%7Cx_object_id%3A1005009260778505%7C_p_origin_prod%3A&search_p4p_id=2026081002175612846935424996960001914278_1)
| **Logic** | Raspberry Pi 4B | 1 | The central brain running ROS 2 and Nav2. | Link |
| **Tools / Test** | CP2102 USB-to-UART Adapter | 1 | Used for initial PC configuration of GPS and LoRa modules. | [Link](https://www.aliexpress.com/item/1005008880984585.html?spm=a2g0o.cart.0.0.2c2938daZviOxL&mp=1&pdp_npi=6%40dis%21USD%21USD+4.22%21USD+1.56%21%21USD+1.56%21%21%21%402103138417863525074584952e1048%2112000047070490262%21ct%21DK%21753190223%21%211%210%21) |

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

### Phase 6: Advanced Vision & AI (Stop & Think)
*Instead of running resource-heavy live video AI, I am prioritizing safety through a "Stop and Think" architecture. The Pi 4B is perfectly capable of running AI models on its CPU if it is allowed to take its time.*

- [ ] Create a custom ROS 2 node that listens to the VL53L5X ToF sensors.
- [ ] Implement "Pause Routing": When ToF detects an anomaly, halt the mower completely to prevent accidents.
- [ ] Trigger the IMX219 camera to snap a single, clear still image while stationary.
- [ ] Run lightweight object detection (e.g., YOLOv8-Nano) directly on the Pi 4B CPU.
- [ ] Dynamic logic: If the AI confirms a hazard (toy/animal), route around it. If it's a false alarm (tall dandelion), resume straight path.


### Extras that did not fit phase 1-6


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
