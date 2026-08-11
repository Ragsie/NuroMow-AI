import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import smbus2
import time
import math

# We use the standard VL53L5CX library for Python
from vl53l5cx import VL53L5CX

# Hardware Constants
MUX_ADDRESS = 0x70      # Default I2C address for the TCA9548A Multiplexer
TOF_I2C_BUS = 1         # Standard I2C bus on Raspberry Pi / Mini PC
MUX_CHANNEL = 0         # The port on the Multiplexer where the ToF is connected (SD0/SC0)

class TofSensorNode(Node):
    def __init__(self):
        super().__init__('tof_sensor_node')
        
        # 1. Create a Publisher for Nav2
        # LaserScan is natively understood by Nav2 for obstacle avoidance
        self.publisher_ = self.create_publisher(LaserScan, 'tof_scan', 10)
        
        self.bus = smbus2.SMBus(TOF_I2C_BUS)
        self.get_logger().info('Initializing I2C Multiplexer and VL53L5X ToF Sensor...')
        
        # 2. Open the correct channel on the Multiplexer
        self.select_mux_channel(MUX_CHANNEL)
        
        # 3. Initialize the 8x8 ToF sensor
        self.tof = VL53L5CX(i2c_bus=self.bus, i2c_address=0x29)
        
        if not self.tof.is_alive():
            self.get_logger().error('CRITICAL: VL53L5X not detected. Check I2C wiring!')
            return
            
        self.tof.init()
        self.tof.set_resolution(8 * 8)          # Set to 64 zones (8x8 grid)
        self.tof.set_ranging_frequency_hz(15)   # 15 frames per second is optimal for motion
        self.tof.start_ranging()
        
        # 4. Timer to read and publish data at 15 Hz
        self.timer = self.create_timer(1.0 / 15.0, self.timer_callback)
        self.get_logger().info('ToF Sensor Node started! Translating 3D grid to 1D LaserScan.')

    def select_mux_channel(self, channel):
        """ The TCA9548A switches channels based on the bits in a single byte """
        if channel < 0 or channel > 7:
            return
        # Write 1 << channel (e.g., channel 0 = 00000001) to the multiplexer
        self.bus.write_byte(MUX_ADDRESS, 1 << channel)
        time.sleep(0.01) # Brief pause to let the I2C bus settle

    def timer_callback(self):
        # Check if the sensor has a new frame ready
        if self.tof.check_data_ready():
            ranging_data = self.tof.get_ranging_data()
            
            # The distance_mm array contains 64 values.
            # We compress this into an 8-point LaserScan by finding the minimum 
            # distance in each of the 8 vertical columns.
            distances_mm = ranging_data.distance_mm
            columns_min = [float('inf')] * 8
            
            for i in range(64):
                col = i % 8 # Determines which of the 8 columns the zone belongs to
                dist = distances_mm[i]
                
                # Ignore invalid readings (0 or negative) and find the closest object in the column
                if dist > 0 and dist < columns_min[col]:
                    columns_min[col] = dist
                    
            # Create the ROS 2 LaserScan message
            scan = LaserScan()
            scan.header.stamp = self.get_clock().now().to_msg()
            scan.header.frame_id = 'tof_link' # The physical center-front of the mower
            
            # VL53L5X has a 45-degree horizontal Field of View (FOV)
            fov_rad = math.radians(45.0)
            scan.angle_min = -fov_rad / 2.0
            scan.angle_max = fov_rad / 2.0
            scan.angle_increment = fov_rad / 8.0 # 8 separate reading zones
            
            scan.range_min = 0.02 # 2 cm blind spot
            scan.range_max = 4.0  # 4 meters max range
            
            # Convert mm to meters for the ROS 2 standard
            scan.ranges = []
            for dist_mm in columns_min:
                if dist_mm != float('inf'):
                    scan.ranges.append(dist_mm / 1000.0)
                else:
                    scan.ranges.append(float('inf')) # Clear path (no obstacle seen)
                    
            self.publisher_.publish(scan)

def main(args=None):
    rclpy.init(args=args)
    node = TofSensorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Stop laser safely before shutting down
        node.tof.stop_ranging()
        node.bus.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()