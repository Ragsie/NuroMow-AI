import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
import cv2
import numpy as np
import os
from rknnlite.api import RKNNLite # Rockchip NPU API

class StereoVisionNode(Node):
    def __init__(self):
        super().__init__('stereo_vision_node')
        self.publisher_ = self.create_publisher(Bool, 'e_stop', 10)
        
        # 1. Initialize NPU for YOLO
        self.get_logger().info('Loading RKNN YOLO model onto NPU...')
        self.rknn = RKNNLite()
        
        # NOTE: Model must be pre-converted to .rknn on a PC!
        ret = self.rknn.load_rknn('./yolo26n.rknn')
        if ret != 0:
            self.get_logger().error('Failed to load RKNN model!')
            
        ret = self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_AUTO)
        if ret != 0:
            self.get_logger().error('Failed to init NPU runtime!')

        # 2. Setup Camera Configuration (Pulled from Docker Environment Variables)
        cam_width = int(os.getenv('CAMERA_WIDTH', '2560'))
        cam_height = int(os.getenv('CAMERA_HEIGHT', '720'))
        cam_fps = int(os.getenv('CAMERA_FPS', '10'))
        
        # Physical camera parameters for real-world depth calculation
        self.baseline = float(os.getenv('CAMERA_BASELINE', '0.06')) # 6 cm default
        self.focal_length = float(os.getenv('CAMERA_FOCAL_LENGTH', '700.0')) # Pixels
        self.min_safe_distance = float(os.getenv('MIN_SAFE_DISTANCE', '1.0')) # Meters

        self.get_logger().info(f'Configuring camera to {cam_width}x{cam_height} at {cam_fps} FPS')
        self.get_logger().info(f'Stereo Params: Baseline={self.baseline}m, Focal Length={self.focal_length}px')

        # 3. Initialize Stereo Camera (GXIVISION 720P)
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_width) 
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_height)
        self.cap.set(cv2.CAP_PROP_FPS, cam_fps)

        # 4. Setup StereoBM for Depth Calculation
        self.stereo = cv2.StereoSGBM_create(
            minDisparity=0,
            numDisparities=64, # Must be divisible by 16
            blockSize=9,
            P1=8 * 3 * 9 ** 2,
            P2=32 * 3 * 9 ** 2,
            disp12MaxDiff=1,
            uniquenessRatio=10,
            speckleWindowSize=100,
            speckleRange=32
        )

        self.danger_classes = [0, 15, 16] # Person, Cat, Dog
        
        timer_period = 1.0 / float(cam_fps)
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warning('Lost connection to the stereo camera!')
            return

        # Split the side-by-side frame into left and right images
        h, w, _ = frame.shape
        half_w = w // 2
        left_img = frame[:, :half_w]
        right_img = frame[:, half_w:]

        danger_detected = False

        # --- DEPTH CHECK (Real-world meters) ---
        gray_left = cv2.cvtColor(left_img, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(right_img, cv2.COLOR_BGR2GRAY)
        disparity = self.stereo.compute(gray_left, gray_right)
        
        # Calculate disparity in the center of the view
        center_disp_raw = np.mean(disparity[h//2-50:h//2+50, half_w//2-50:half_w//2+50])
        # StereoSGBM multiplies disparity by 16 for sub-pixel accuracy, so we divide by 16
        center_disp = center_disp_raw / 16.0 

        # Prevent division by zero
        if center_disp > 0:
            # Formula: Depth = (Focal Length * Baseline) / Disparity
            depth_meters = (self.focal_length * self.baseline) / center_disp
            
            if depth_meters < self.min_safe_distance:
                self.get_logger().warn(f'E-STOP: Object too close! Distance: {depth_meters:.2f}m')
                danger_detected = True

        # --- NPU YOLO CHECK (Running on left image) ---
        if not danger_detected:
            img_resized = cv2.resize(left_img, (640, 640))
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
            
            # Run inference on NPU
            outputs = self.rknn.inference(inputs=[img_rgb])
            
            # (Post-processing logic for RKNN YOLO outputs goes here)
            detected_classes = [] # Placeholder for parsed output
            
            for class_id in detected_classes:
                if class_id in self.danger_classes:
                    self.get_logger().warn('E-STOP: Danger class detected by NPU!')
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
        node.rknn.release()
        node.cap.release()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
