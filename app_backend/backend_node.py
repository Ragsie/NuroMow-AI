#!/usr/bin/env python3
from fastapi import FastAPI, WebSocket
import uvicorn
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix, BatteryState
from std_msgs.msg import Int32, Float32
from nav_msgs.msg import Odometry  # 🆕 [TILFØJET: Til kilometertæller]
import threading
import json
import asyncio
import os
import math
import time

app = FastAPI(title="NuroMow API Gateway")
clients = []

class BackendROSNode(Node):
    def __init__(self):
        super().__init__('app_backend_node')
        self.gps_sub = self.create_subscription(NavSatFix, '/gps/fix', self.gps_callback, 10)
        self.battery_sub = self.create_subscription(BatteryState, '/battery_state', self.battery_callback, 10)
        self.status_sub = self.create_subscription(Int32, '/mower/state', self.state_callback, 10)
        self.cutter_status_sub = self.create_subscription(Int32, '/cutter/status', self.cutter_status_callback, 10)
        self.cutter_current_sub = self.create_subscription(Float32, '/cutter/current', self.cutter_current_callback, 10)
        self.drive_current_sub = self.create_subscription(Float32, '/drive/current', self.drive_current_callback, 10)
        self.cutter_rpm_sub = self.create_subscription(Int32, '/cutter/rpm', self.cutter_rpm_callback, 10)

        # 🆕 [TILFØJET: Nye abonnenter til kilometertæller, GPS-satellitter og BMS-opladsningscykler]
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        self.satellites_sub = self.create_subscription(Int32, '/gps/satellites', self.satellites_callback, 10)
        self.charge_cycles_sub = self.create_subscription(Int32, '/battery/charge_cycles', self.charge_cycles_callback, 10)

        self.gps_data = {"lat": 0.0, "lon": 0.0, "status": "Intet GPS Signal", "rtk_code": 0, "rtk_text": "Intet GPS Signal", "satellites": 0}
        self.battery_v = 24.0
        self.battery_pct = 100.0
        self.battery_current = 0.0
        self.battery_temp = 25.0
        self.state = 0 # 0=STOP, 1=KLIPPER, 2=SØGER DOCK, 3=OPLADER, 4=STUCK, 5=NØDSTOP, 6=CUTTER_BLOKERET, 7=SØGER GRÆSKANT
        self.cutter_status = 0 # 0=OFF, 1=OK, 2=BLOKERET
        self.cutter_current = 0.0
        self.drive_current = 0.0
        self.cutter_rpm = 0
        self.satellites_count = 0
        self.charge_cycles = 0

        # 🆕 [TILFØJET: Persistent statistik indlæst fra Orange Pi NVMe SSD]
        self.stats_file = "/opt/nuromow/stats.json"
        self.total_distance_km = 0.0
        self.total_runtime_hours = 0.0
        self.load_stats()

        self.last_x = None
        self.last_y = None
        self.last_stats_save_time = time.time()
        self.last_runtime_tick = time.time()

        # CPU overvågning
        self.last_cpu_idle = 0
        self.last_cpu_total = 0

    def load_stats(self):
        # 🆕 [TILFØJET: Indlæs kilometertæller og runtime persistent]
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    self.total_distance_km = data.get("total_distance_km", 0.0)
                    self.total_runtime_hours = data.get("total_runtime_hours", 0.0)
            except Exception as e:
                self.get_logger().error(f"Kunne ikke læse stats-fil: {e}")
        else:
            self.save_stats()

    def save_stats(self):
        # 🆕 [TILFØJET: Gem stats persistent i JSON-fil]
        try:
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            with open(self.stats_file, 'w') as f:
                json.dump({
                    "total_distance_km": round(self.total_distance_km, 3),
                    "total_runtime_hours": round(self.total_runtime_hours, 4)
                }, f)
        except Exception as e:
            self.get_logger().error(f"Kunne ikke gemme stats-fil: {e}")

    def odom_callback(self, msg):
        # 🆕 [TILFØJET: Beregn euklidisk distance kørt fra hjulenkodere og odom-træet]
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y

        if self.last_x is not None and self.last_y is not None:
            dist_m = math.sqrt((x - self.last_x)**2 + (y - self.last_y)**2)
            if dist_m < 5.0: # Sikkerhedstærskel mod hop ved odom nulstilling
                self.total_distance_km += dist_m / 1000.0

        self.last_x = x
        self.last_y = y
        self.update_runtime_and_save()

    def update_runtime_and_save(self):
        # 🆕 [TILFØJET: Opdater driftstimer hvis maskinen kører, og gem til disk hvert 10. sekund]
        now = time.time()
        dt = now - self.last_runtime_tick
        self.last_runtime_tick = now

        if self.state in [1, 2, 7]: # Aktivt arbejdende tilstande
            self.total_runtime_hours += dt / 3600.0

        if now - self.last_stats_save_time >= 10.0:
            self.last_stats_save_time = now
            self.save_stats()
            self.broadcast_status()

    def satellites_callback(self, msg):
        # 🆕 [TILFØJET: Modtag låst satellit-antal fra Quectel LC29H GPS]
        self.satellites_count = msg.data
        self.gps_data["satellites"] = self.satellites_count
        self.broadcast_status()

    def charge_cycles_callback(self, msg):
        # 🆕 [TILFØJET: Modtag akkumulerede opladningscykler fra Daly BMS via ESP32]
        self.charge_cycles = msg.data
        self.broadcast_status()

    def gps_callback(self, msg):
        status_code = msg.status.status
        # Konverter RTK/GPS status til dansk tekst og kode til appen
        rtk_text = "Intet GPS Signal"
        if status_code == 0:
            rtk_text = "Standard GPS Fix (Groft)"
        elif status_code == 1:
            rtk_text = "RTK Float (Søger præcision)"
        elif status_code == 2:
            rtk_text = "RTK Centimeter-Fix (Perfekt)"

        self.gps_data = {
            "lat": msg.latitude,
            "lon": msg.longitude,
            "status": rtk_text,
            "rtk_code": status_code + 1 if status_code >= 0 else 0, # Omdan til 0=No fix, 1=GPS, 2=Float, 3=Fix
            "rtk_text": rtk_text,
            "satellites": self.satellites_count
        }
        self.broadcast_status()

    def battery_callback(self, msg):
        self.battery_v = msg.voltage
        self.battery_pct = msg.percentage * 100.0
        self.battery_current = msg.current
        self.battery_temp = msg.temperature
        self.broadcast_status()

    def state_callback(self, msg):
        self.state = msg.data
        self.broadcast_status()

    def cutter_status_callback(self, msg):
        self.cutter_status = msg.data
        if self.cutter_status == 2:
            self.state = 6 # CUTTER_BLOKERET systemstate
        self.broadcast_status()

    def cutter_current_callback(self, msg):
        self.cutter_current = msg.data
        self.broadcast_status()

    def drive_current_callback(self, msg):
        self.drive_current = msg.data
        self.broadcast_status()

    def cutter_rpm_callback(self, msg):
        self.cutter_rpm = msg.data
        self.broadcast_status()

    def get_system_temperature(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_raw = int(f.read().strip())
            return round(temp_raw / 1000.0, 1)
        except Exception:
            return 0.0

    def get_cpu_load(self):
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            parts = line.split()
            # CPU user, nice, system, idle, iowait, irq, softirq
            cpu_times = [int(x) for x in parts[1:5]]
            idle = cpu_times[3]
            total = sum(cpu_times)

            diff_idle = idle - self.last_cpu_idle
            diff_total = total - self.last_cpu_total

            self.last_cpu_idle = idle
            self.last_cpu_total = total

            if diff_total == 0:
                return 0.0
            return round((1.0 - (diff_idle / diff_total)) * 100.0, 1)
        except Exception:
            return 0.0

    def broadcast_status(self):
        payload = {
            "gps": self.gps_data,
            "battery": {
                "voltage": round(self.battery_v, 2),
                "percentage": round(self.battery_pct, 1),
                "current": round(self.battery_current, 2),
                "temperature_celsius": round(self.battery_temp, 1),
                "charge_cycles": self.charge_cycles # 🆕 [TILFØJET: Opladningscykler fra BMS]
            },
            "state": self.state,
            "cutter_status": self.cutter_status,
            "cutter_rpm": self.cutter_rpm,
            "power_consumption": {
                "total_bms_current_ampere": round(self.battery_current, 2),
                "drive_motors_current_ampere": round(self.drive_current, 2),
                "cutter_motor_current_ampere": round(self.cutter_current, 2),
                "cutter_motor_power_watts": round(self.battery_v * self.cutter_current, 1) # 🆕 [TILFØJET: Reelt effektforbrug i Watt]
            },
            "statistics": { # 🆕 [TILFØJET: Persistent kilometertæller og runtime statistik]
                "total_distance_km": round(self.total_distance_km, 2),
                "total_runtime_hours": round(self.total_runtime_hours, 1)
            },
            "system": {
                "cpu_temp_celsius": self.get_system_temperature(),
                "cpu_load_pct": self.get_cpu_load()
            }
        }

        for client in clients:
            try:
                asyncio.run_coroutine_threadsafe(client.send_text(json.dumps(payload)), loop)
            except Exception:
                clients.remove(client)

def start_ros():
    rclpy.init()
    ros_node = BackendROSNode()
    rclpy.spin(ros_node)
    rclpy.shutdown()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        clients.remove(websocket)

if __name__ == "__main__":
    global loop
    loop = asyncio.get_event_loop()
    ros_thread = threading.Thread(target=start_ros, daemon=True)
    ros_thread.start()
    uvicorn.run(app, host="0.0.0.0", port=8000)