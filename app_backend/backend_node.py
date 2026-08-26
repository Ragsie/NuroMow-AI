import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32
from nav_msgs.msg import Odometry
import json
import math
import time

class AppBackendNode(Node):
    def __init__(self):
        super().__init__('app_backend_node')
        
        # --- PUBLISHERS TO APP (via Rosbridge) ---
        self.battery_pub = self.create_publisher(String, '/battery_status', 10)
        self.rtk_pub = self.create_publisher(String, '/rtk/status', 10)
        self.status_pub = self.create_publisher(String, '/mower/status', 10)
        self.app_odom_pub = self.create_publisher(String, '/odom', 10)
        self.metrics_pub = self.create_publisher(String, '/mower/metrics', 10) 
        
        # --- SUBSCRIBERS FROM HARDWARE ---
        self.create_subscription(String, '/hw/drive_status', self.hw_status_callback, 10)
        self.create_subscription(Odometry, '/hw/odom', self.native_odom_callback, 10)
        self.create_subscription(Float32, '/hw/battery', self.hw_battery_callback, 10)
        
        # NEW: Listen to the cutter motor's current draw
        self.create_subscription(Float32, '/hw/cutter_amps', self.hw_cutter_amps_callback, 10)

        # --- SUBSCRIBERS FROM APP ---
        self.create_subscription(String, '/mower/command', self.app_command_callback, 10)

        # --- INTERNAL STATE & METRICS ---
        self.is_mapping = False
        self.cutter_amps = 0.0 # Stores latest cutter current
        
        # Metrics variables
        self.total_distance = 0.0
        self.total_mowing_seconds = 0.0
        self.charge_cycles = 0
        
        self.last_x = None
        self.last_y = None
        self.mowing_start_time = None
        self.is_charging = False

        self.metrics_timer = self.create_timer(5.0, self.publish_metrics)
        self.get_logger().info("App Backend Node started with Cutter monitoring.")

    def hw_cutter_amps_callback(self, msg):
        # Update the internal variable with live data from ESP32
        self.cutter_amps = msg.data

    def native_odom_callback(self, msg):
        x_pos = msg.pose.pose.position.x
        y_pos = msg.pose.pose.position.y
        
        # Calculate distance for Nerd Metrics
        if self.last_x is not None and self.last_y is not None:
            dist = math.sqrt((x_pos - self.last_x)**2 + (y_pos - self.last_y)**2)
            self.total_distance += dist
            
        self.last_x = x_pos
        self.last_y = y_pos
        
        app_msg = {"x": round(x_pos, 2), "y": round(y_pos, 2)}
        json_msg = String()
        json_msg.data = json.dumps(app_msg)
        self.app_odom_pub.publish(json_msg)

    def hw_battery_callback(self, msg):
        app_msg = {"percentage": msg.data}
        json_msg = String()
        json_msg.data = json.dumps(app_msg)
        self.battery_pub.publish(json_msg)

    def hw_status_callback(self, msg):
        raw_status = msg.data.lower()
        current_state = "mapping" if self.is_mapping else "mowing"
            
        if "stuck" in raw_status:
            current_state = "stuck"
        elif "dock" in raw_status:
            current_state = "docking"
        elif "charg" in raw_status:
            current_state = "charging"

        # Time tracking for mowing
        if current_state in ["mowing", "mapping"]:
            if self.mowing_start_time is None:
                self.mowing_start_time = time.time()
        else:
            if self.mowing_start_time is not None:
                self.total_mowing_seconds += (time.time() - self.mowing_start_time)
                self.mowing_start_time = None
                
        # Charge cycle tracking
        if current_state == "charging" and not self.is_charging:
            self.is_charging = True
        elif current_state != "charging" and self.is_charging:
            self.charge_cycles += 1
            self.is_charging = False

        # --- COMBINE DATA FOR APP ---
        # We inject the cutter data directly into the main status JSON
        app_msg = {
            "state": current_state,
            "cutter_amps": round(self.cutter_amps, 1),
            "blade_active": self.cutter_amps > 1.0 # True if drawing more than 1 Amp
        }
        
        json_msg = String()
        json_msg.data = json.dumps(app_msg)
        self.status_pub.publish(json_msg)

    def publish_metrics(self):
        current_mow_time = 0
        if self.mowing_start_time is not None:
            current_mow_time = time.time() - self.mowing_start_time
            
        total_mins = int((self.total_mowing_seconds + current_mow_time) / 60)
        
        metrics = {
            "distance_meters": round(self.total_distance, 1),
            "mowing_minutes": total_mins,
            "charge_cycles": self.charge_cycles
        }
        
        msg = String()
        msg.data = json.dumps(metrics)
        self.metrics_pub.publish(msg)

    def app_command_callback(self, msg):
        command = msg.data.lower()
        if command == "start_mapping":
            self.is_mapping = True
        elif command == "stop_mapping" or command == "stop":
            self.is_mapping = False

def main(args=None):
    rclpy.init(args=args)
    node = AppBackendNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
