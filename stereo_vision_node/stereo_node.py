import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from sensor_msgs.msg import LaserScan  # Required for Virtual LiDAR
import cv2
import numpy as np
import os

# --- 1. SAFE IMPORT (Prevent crash on x86 PC) ---
try:
    from rknnlite.api import RKNNLite
    NPU_AVAILABLE = True
except ImportError:
    NPU_AVAILABLE = False
    print("WARNING: rknnlite module not found! Running in CPU/Test mode without NPU.")

class StereoVisionNode(Node):
    def __init__(self):
        super().__init__('stereo_vision_node')
        
        # Publishers
        self.publisher_ = self.create_publisher(Bool, 'e_stop', 10)
        self.scan_publisher_ = self.create_publisher(LaserScan, 'scan', 10)
        
        # --- 2. CONDITIONAL NPU INITIALIZATION ---
        if NPU_AVAILABLE:
            self.get_logger().info('Loading RKNN YOLO model onto NPU...')
            self.rknn = RKNNLite()
            
            # Load the exported RKNN model
            ret = self.rknn.load_rknn('./yolo26n-seg.rknn')
            if ret != 0:
                self.get_logger().error('Failed to load RKNN model!')
                
            ret = self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_AUTO)
            if ret != 0:
                self.get_logger().error('Failed to init NPU runtime!')
        else:
            self.get_logger().warn('NPU DISABLED: Stereo depth active, YOLO offline.')

        # Setup Camera Configuration
        cam_width = int(os.getenv('CAMERA_WIDTH', '2560'))
        cam_height = int(os.getenv('CAMERA_HEIGHT', '720'))
        cam_fps = int(os.getenv('CAMERA_FPS', '10'))
        
        self.baseline = float(os.getenv('CAMERA_BASELINE', '0.06'))
        self.focal_length = float(os.getenv('CAMERA_FOCAL_LENGTH', '700.0'))
        self.min_safe_distance = float(os.getenv('MIN_SAFE_DISTANCE', '1.0'))
        
        # Camera Horizontal Field of View in radians (Approx 60 degrees)
        self.camera_fov = 1.047 

        self.get_logger().info(f'Configuring camera to {cam_width}x{cam_height} at {cam_fps} FPS')
        
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_width) 
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_height)
        self.cap.set(cv2.CAP_PROP_FPS, cam_fps)

        self.stereo = cv2.StereoSGBM_create(
            minDisparity=0,
            numDisparities=64,
            blockSize=9,
            P1=8 * 3 * 9 ** 2,
            P2=32 * 3 * 9 ** 2,
            disp12MaxDiff=1,
            uniquenessRatio=10,
            speckleWindowSize=100,
            speckleRange=32
        )

        # Danger IDs based on custom dataset (0: dog, 3: poo, 4: toy)
        self.danger_classes = [0, 3, 4] 
        
        timer_period = 1.0 / float(cam_fps)
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warning('Lost connection to the stereo camera!')
            return

        h, w, _ = frame.shape
        half_w = w // 2
        left_img = frame[:, :half_w]
        right_img = frame[:, half_w:]

        danger_detected = False

        # --- VIRTUAL LIDAR (DEPTH CHECK) ---
        gray_left = cv2.cvtColor(left_img, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(right_img, cv2.COLOR_BGR2GRAY)
        disparity = self.stereo.compute(gray_left, gray_right)
        
        # Extract a horizontal "slice" from the middle of the image (40 pixels high)
        band_top = h // 2 - 20
        band_bottom = h // 2 + 20
        disparity_band = disparity[band_top:band_bottom, :]
        
        # Find the closest object in each vertical column
        max_disp_per_col = np.max(disparity_band, axis=0) / 16.0 
        
        # Create the LaserScan message
        scan_msg = LaserScan()
        scan_msg.header.stamp = self.get_clock().now().to_msg()
        scan_msg.header.frame_id = 'camera_link' # Crucial for TF mapping
        
        scan_msg.angle_min = -self.camera_fov / 2.0
        scan_msg.angle_max = self.camera_fov / 2.0
        scan_msg.angle_increment = self.camera_fov / float(half_w)
        scan_msg.time_increment = 0.0
        scan_msg.range_min = 0.1 
        scan_msg.range_max = 8.0 
        
        ranges = []
        closest_distance = float('inf')

        for disp in max_disp_per_col:
            if disp > 0:
                depth = (self.focal_length * self.baseline) / disp
                if scan_msg.range_min <= depth <= scan_msg.range_max:
                    ranges.append(float(depth))
                    if depth < closest_distance:
                        closest_distance = depth
                else:
                    ranges.append(float('inf'))
            else:
                ranges.append(float('inf'))
                
        scan_msg.ranges = ranges
        self.scan_publisher_.publish(scan_msg)

        # Hardware E-STOP functionality for proximity
        if closest_distance < self.min_safe_distance:
            self.get_logger().warn(f'E-STOP: Object too close! Distance: {closest_distance:.2f}m')
            danger_detected = True

        # --- 3. CONDITIONAL NPU YOLO CHECK ---
        if not danger_detected and NPU_AVAILABLE:
            img_resized = cv2.resize(left_img, (640, 640))
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
            
            outputs = self.rknn.inference(inputs=[img_rgb])
            
            # --- NON-MAXIMUM SUPPRESSION (NMS) ---
            pred = outputs[0][0]
            if pred.shape[0] < pred.shape[1]:
                pred = np.transpose(pred)

            boxes, scores, class_ids = [], [], []
            num_classes = 7
            conf_threshold = 0.50
            
            for row in pred:
                class_scores = row[4:4 + num_classes]
                max_score = np.max(class_scores)
                
                if max_score > conf_threshold:
                    class_id = np.argmax(class_scores)
                    cx, cy, w_box, h_box = row[0:4]
                    x = int(cx - (w_box / 2))
                    y = int(cy - (h_box / 2))
                    
                    boxes.append([x, y, int(w_box), int(h_box)])
                    scores.append(float(max_score))
                    class_ids.append(class_id)

            indices = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, 0.45)
            
            detected_classes = []
            if len(indices) > 0:
                for i in indices.flatten():
                    detected_classes.append(class_ids[i])

            for class_id in detected_classes:
                if class_id in self.danger_classes:
                    self.get_logger().warn(f'E-STOP: Danger class ID {class_id} detected by AI!')
                    danger_detected = True
                    break

        # --- PUBLISH COMMAND ---
        msg = Bool()
        msg.data = danger_detected
        self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = StereoVisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if NPU_AVAILABLE:
            node.rknn.release()
        node.cap.release()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
