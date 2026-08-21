import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from sensor_msgs.msg import LaserScan
import cv2
import numpy as np
import os

# --- 1. SAFE IMPORT (Prevent crash on PC) ---
# Safe import: Check if we are running on the Orange Pi (NPU) or a standard PC (x86)
try:
    from rknnlite.api import RKNNLite
    NPU_AVAILABLE = True
except ImportError:
    NPU_AVAILABLE = False
    print("WARNING: rknnlite module not found! Running in CPU/Test mode without NPU.")

class StereoVisionNode(Node):
    def __init__(self):
        super().__init__('stereo_vision_node')
        self.publisher_ = self.create_publisher(Bool, 'e_stop', 10)
        
        # --- 2. CONDITIONAL NPU INITIALIZATION ---
        if NPU_AVAILABLE:
            self.get_logger().info('Loading RKNN YOLO model onto NPU...')
            self.rknn = RKNNLite()
            
            ret = self.rknn.load_rknn('./yolo26n.rknn')
            if ret != 0:
                self.get_logger().error('Failed to load RKNN model!')
                
            ret = self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_AUTO)
            if ret != 0:
                self.get_logger().error('Failed to init NPU runtime!')
        else:
            self.get_logger().warn('NPU DISABLED: Stereo depth is active, but YOLO object detection is offline.')

        # Setup Camera Configuration
        cam_width = int(os.getenv('CAMERA_WIDTH', '2560'))
        cam_height = int(os.getenv('CAMERA_HEIGHT', '720'))
        cam_fps = int(os.getenv('CAMERA_FPS', '10'))
        
        self.baseline = float(os.getenv('CAMERA_BASELINE', '0.06'))
        self.focal_length = float(os.getenv('CAMERA_FOCAL_LENGTH', '700.0'))
        self.min_safe_distance = float(os.getenv('MIN_SAFE_DISTANCE', '1.0'))

        self.get_logger().info(f'Configuring camera to {cam_width}x{cam_height} at {cam_fps} FPS')
        self.get_logger().info(f'Stereo Params: Baseline={self.baseline}m, Focal Length={self.focal_length}px')

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

        self.danger_classes = [0, 15, 16] 
        
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

        # --- DEPTH CHECK (Always runs - both on NPU and PC) ---
        gray_left = cv2.cvtColor(left_img, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(right_img, cv2.COLOR_BGR2GRAY)
        disparity = self.stereo.compute(gray_left, gray_right)
        
        center_disp_raw = np.mean(disparity[h//2-50:h//2+50, half_w//2-50:half_w//2+50])
        center_disp = center_disp_raw / 16.0 

        if center_disp > 0:
            depth_meters = (self.focal_length * self.baseline) / center_disp
            
            if depth_meters < self.min_safe_distance:
                self.get_logger().warn(f'E-STOP: Object too close! Distance: {depth_meters:.2f}m')
                danger_detected = True

        # --- 3. CONDITIONAL NPU YOLO CHECK (Skipped on PC) ---
        if not danger_detected and NPU_AVAILABLE:
            img_resized = cv2.resize(left_img, (640, 640))
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
            
            outputs = self.rknn.inference(inputs=[img_rgb])
            
            # Placeholder: We still need your NMS function here to parse 'outputs'
            detected_classes = [] 
            
            for class_id in detected_classes:
                if class_id in self.danger_classes:
                    self.get_logger().warn('E-STOP: Danger class detected by NPU!')
                    danger_detected = True
                    break

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
        # --- 4. SAFE SHUTDOWN ---
        if NPU_AVAILABLE:
            node.rknn.release()
        node.cap.release()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
