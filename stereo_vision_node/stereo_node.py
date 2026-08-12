import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
import cv2
import numpy as np
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

        # 2. Initialize Stereo Camera (GXIVISION 720P)
        # Often stereo cameras combine left/right into a single wide frame (e.g., 2560x720)
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560) 
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # 3. Setup StereoBM for Depth Calculation
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
        self.timer = self.create_timer(1.0, self.timer_callback) # 1 FPS

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

        # --- DEPTH CHECK ---
        gray_left = cv2.cvtColor(left_img, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(right_img, cv2.COLOR_BGR2GRAY)
        disparity = self.stereo.compute(gray_left, gray_right)
        
        # Calculate rough depth (Requires actual calibration constants for your specific GXIVISION lens)
        # If the center area is extremely close, trigger stop.
        center_disp = np.mean(disparity[h//2-50:h//2+50, half_w//2-50:half_w//2+50])
        if center_disp > 400: # Threshold depends on calibration
            self.get_logger().warn('E-STOP: Physical object too close (Depth)!')
            danger_detected = True

        # --- NPU YOLO CHECK (Running on left image) ---
        if not danger_detected:
            # Resize image to match YOLO input (e.g., 640x640)
            img_resized = cv2.resize(left_img, (640, 640))
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
            
            # Run inference on NPU
            outputs = self.rknn.inference(inputs=[img_rgb])
            
            # (Post-processing logic for RKNN YOLO outputs goes here)
            # This involves parsing the output tensor to find class_ids and confidences.
            # Assuming a parsed list of detected class_ids:
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
