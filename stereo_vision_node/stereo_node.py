import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, PointCloud2, PointField, Image
from std_msgs.msg import Header
from cv_bridge import CvBridge
import cv2
import numpy as np
import os

class StereoVisionNode(Node):
    def __init__(self):
        super().__init__('stereo_vision_node')

        # Publishers
        self.scan_publisher = self.create_publisher(LaserScan, 'scan', 10)
        self.pc_publisher = self.create_publisher(PointCloud2, 'camera/depth/points', 10)
        self.left_image_pub = self.create_publisher(Image, 'camera/left/image_raw', 10)

        self.bridge = CvBridge()

        # Camera Configuration
        cam_index = int(os.getenv('CAMERA_INDEX', '0'))
        cam_width = int(os.getenv('CAMERA_WIDTH', '2560'))
        cam_height = int(os.getenv('CAMERA_HEIGHT', '720'))
        cam_fps = int(os.getenv('CAMERA_FPS', '30'))

        self.baseline = float(os.getenv('CAMERA_BASELINE', '0.085'))
        self.focal_length = float(os.getenv('CAMERA_FOCAL_LENGTH', '700.0'))
        self.camera_fov = 1.274  # Approx 73 degrees in radians

        self.get_logger().info(f'Initializing GXIVISION Camera [{cam_index}] at {cam_width}x{cam_height} @ {cam_fps} FPS')

        # Setup OpenCV Capture (MJPEG over USB 2.0 to conserve bandwidth)
        self.cap = cv2.VideoCapture(cam_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_height)
        self.cap.set(cv2.CAP_PROP_FPS, cam_fps)

        # StereoSGBM matching - OpenCV on ARM64 automatically utilizes NEON SIMD
        self.stereo = cv2.StereoSGBM_create(
            minDisparity=0,
            numDisparities=64,
            blockSize=9,
            P1=8 * 3 * 9**2,
            P2=32 * 3 * 9**2,
            disp12MaxDiff=1,
            uniquenessRatio=10,
            speckleWindowSize=100,
            speckleRange=32
        )

        timer_period = 1.0 / float(cam_fps)
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warning('Unable to read frame from GXIVISION camera!')
            return

        h, w, _ = frame.shape
        half_w = w // 2

        # Split the wide synchronized composite frame
        left_img = frame[:, :half_w]
        right_img = frame[:, half_w:]

        stamp = self.get_clock().now().to_msg()

        # NEON-Accelerated Color Conversion
        gray_left = cv2.cvtColor(left_img, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(right_img, cv2.COLOR_BGR2GRAY)

        # Compute Stereo Disparity Map
        disparity = self.stereo.compute(gray_left, gray_right)

        # --- 1. GENERATE VIRTUAL 2D LASER SCAN ---
        band_top = h // 2 - 20
        band_bottom = h // 2 + 20
        disparity_band = disparity[band_top:band_bottom, :]
        max_disp_per_col = np.max(disparity_band, axis=0) / 16.0

        scan_msg = LaserScan()
        scan_msg.header.stamp = stamp
        scan_msg.header.frame_id = 'camera_link'
        scan_msg.angle_min = -self.camera_fov / 2.0
        scan_msg.angle_max = self.camera_fov / 2.0
        scan_msg.angle_increment = self.camera_fov / float(half_w)
        scan_msg.time_increment = 0.0
        scan_msg.range_min = 0.1
        scan_msg.range_max = 8.0

        ranges = []
        for disp in max_disp_per_col:
            if disp > 0:
                depth = (self.focal_length * self.baseline) / disp
                if scan_msg.range_min <= depth <= scan_msg.range_max:
                    ranges.append(float(depth))
                else:
                    ranges.append(float('inf'))
            else:
                ranges.append(float('inf'))

        scan_msg.ranges = ranges
        self.scan_publisher.publish(scan_msg)

        # --- 2. VECTORIZED 3D POINT CLOUD (ARM NEON & NUMPY OPTIMIZED) ---
        u_grid, v_grid = np.meshgrid(np.arange(half_w), np.arange(h))

        disp_float = disparity.astype(np.float32) / 16.0
        disp_float[disp_float <= 0] = 0.0001 # Prevent division by zero

        # Vectorized depth mapping
        Z = (self.focal_length * self.baseline) / disp_float

        cx, cy = half_w / 2.0, h / 2.0
        X = (u_grid - cx) * Z / self.focal_length
        Y = (v_grid - cy) * Z / self.focal_length

        # Filter out invalid depth points (out of range or blind zones)
        invalid = (disparity <= 0) | (Z < 0.1) | (Z > 8.0)
        X[invalid] = np.nan
        Y[invalid] = np.nan
        Z[invalid] = np.nan

        # Create structured float32 cloud array (X, Y, Z, Padding)
        points_3d = np.dstack((X, Y, Z, np.zeros_like(Z))).astype(np.float32)

        # Pack binary PointCloud2 message
        pc_msg = PointCloud2()
        pc_msg.header.stamp = stamp
        pc_msg.header.frame_id = 'camera_link'
        pc_msg.height = h
        pc_msg.width = half_w
        pc_msg.is_dense = False
        pc_msg.is_bigendian = False
        pc_msg.point_step = 16
        pc_msg.row_step = pc_msg.point_step * half_w

        pc_msg.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1)
        ]
        pc_msg.data = points_3d.tobytes()

        # Publish Left Image and PointCloud with identical timestamps
        left_image_msg = self.bridge.cv2_to_imgmsg(left_img, encoding="bgr8")
        left_image_msg.header.stamp = stamp

        self.left_image_pub.publish(left_image_msg)
        self.pc_publisher.publish(pc_msg)

def main(args=None):
    rclpy.init(args=args)
    node = StereoVisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cap.release()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()