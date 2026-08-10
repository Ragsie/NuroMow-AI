import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool  # We use a simple True/False message for the E-stop
import cv2
from ultralytics import YOLO

class YoloSafetyNode(Node):
    def __init__(self):
        super().__init__('yolo_safety_node')

        # 1. Create a Publisher that can send True/False messages on '/e_stop'
        self.publisher_ = self.create_publisher(Bool, 'e_stop', 10)

        # 2. Load the AI model (Using the ultra-fast YOLO26 Nano)
        self.get_logger().info('Loading YOLO model...')
        self.model = YOLO("yolo26n.pt")

        # 3. Start the camera (0 is default, change to 1 if using multiple cameras)
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.get_logger().error('Critical error: Could not open camera!')

        # 4. Danger classes from COCO dataset: 0 = Person, 15 = Cat, 16 = Dog
        self.danger_classes = [0, 15, 16]

        # 5. Create a timer that runs the callback exactly 1 time per second (1.0 Hz)
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.get_logger().info('YOLO Safety Node started. Scanning for hazards...')

    def timer_callback(self):
        # Read a single frame from the camera
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warning('Lost connection to the camera!')
            return

        # Run AI on the frame (verbose=False keeps the terminal output clean)
        results = self.model(frame, verbose=False)
        danger_detected = False

        # Check all objects that YOLO detected in this single frame
        for box in results[0].boxes:
            class_id = int(box.cls[0])
            
            # Was a person, dog, or cat detected?
            if class_id in self.danger_classes:
                class_name = self.model.names[class_id]
                self.get_logger().warn(f'E-STOP TRIGGERED! Object in front of mower: {class_name.upper()}')
                danger_detected = True

        # Create the ROS message and publish it to the network
        msg = Bool()
        msg.data = danger_detected # Becomes True if danger, otherwise False
        self.publisher_.publish(msg)

        # Print a heartbeat message occasionally so we know it's alive (without spamming)
        if not danger_detected:
            self.get_logger().info('Coast is clear.', throttle_duration_sec=5.0) 

def main(args=None):
    rclpy.init(args=args)
    node = YoloSafetyNode()
    
    try:
        # Spin keeps the script running until we shut it down
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Shut down gracefully and release the webcam
        node.cap.release()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()