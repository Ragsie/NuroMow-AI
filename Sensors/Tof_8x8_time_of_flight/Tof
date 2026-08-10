import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range  # Using a standard ROS message for distance
import board
import busio
import adafruit_tca9548a
from adafruit_vl53l5cx import VL53L5CX

class ToFSensorNode(Node):
    def __init__(self):
        super().__init__('tof_sensor_node')
        
        # 1. Start the I2C bus on the Raspberry Pi
        i2c = board.I2C()
        
        # 2. Connect to the Multiplexer (TCA9548A)
        self.tca = adafruit_tca9548a.TCA9548A(i2c)
        
        self.get_logger().info("Multiplexer found! Initializing sensors...")
        
        # 3. Tell the Pi which channel the sensors are connected to
        # self.tca[0] means "Channel 0 on the multiplexer"
        self.sensor_front_left = VL53L5CX(self.tca[0])
        self.sensor_front_right = VL53L5CX(self.tca[1])
        
        # 4. Set the sensors to range continuously (e.g., 15 Hz)
        self.sensor_front_left.start_ranging()
        self.sensor_front_right.start_ranging()
        
        # 5. Create ROS 2 Publishers (The topics Nav2 listens to)
        self.pub_left = self.create_publisher(Range, 'sensors/tof_left', 10)
        self.pub_right = self.create_publisher(Range, 'sensors/tof_right', 10)
        
        # 6. Run the read function 10 times a second (0.1 sec timer)
        self.timer = self.create_timer(0.1, self.read_sensors_callback)

    def read_sensors_callback(self):
        # --- Read and send data for LEFT sensor ---
        if self.sensor_front_left.data_ready:
            # Get 8x8 grid data (64 distances). 
            # (In practice, you might just use the average of the center, or send everything as a PointCloud)
            distance_data = self.sensor_front_left.distance
            
            msg = Range()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "tof_left_link"
            msg.range = distance_data[36] # Example: Read the zone in the center
            
            self.pub_left.publish(msg)

        # --- Read and send data for RIGHT sensor ---
        if self.sensor_front_right.data_ready:
            distance_data = self.sensor_front_right.distance
            # ... pack and send just like the left one ...
            
            # Example placeholder for right sensor:
            # msg_right = Range()
            # msg_right.header.stamp = self.get_clock().now().to_msg()
            # msg_right.header.frame_id = "tof_right_link"
            # msg_right.range = distance_data[36]
            # self.pub_right.publish(msg_right)

def main(args=None):
    rclpy.init(args=args)
    node = ToFSensorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()