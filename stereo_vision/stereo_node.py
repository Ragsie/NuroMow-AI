#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import cv2
import numpy as np
from sensor_msgs.msg import LaserScan, Image
from cv_bridge import CvBridge

class StereoNode(Node):
    def __init__(self):
        super().__init__('stereo_node')
        self.publisher_scan = self.create_publisher(LaserScan, '/scan', 10)
        self.publisher_depth = self.create_publisher(Image, '/stereo/depth_image', 10)
        self.bridge = CvBridge()

        # ROS 2 Parametre med standardværdier (Arves dynamisk fra nuromow.env via launch) 🆕 [DYNAMISKE PARAMETRE]
        self.declare_parameter('video_device', '/dev/video_stereo')
        self.declare_parameter('frame_id', 'camera_link')
        self.declare_parameter('baseline', 0.06)          # GXIVISION 60 mm baseline
        self.declare_parameter('focal_length', 350.0)      # Brændvidde i pixels
        self.declare_parameter('camera_height_z', 0.10)    # Monteringshøjde over jorden (meter)
        self.declare_parameter('camera_offset_x', 0.25)    # Fremadrettet afstand fra base_link rotationscentrum (meter)
        self.declare_parameter('camera_pitch_y', 0.0)      # Hældningsvinkel i radianer (0.0 = vandret, positive = nedad)

        device = self.get_parameter('video_device').get_parameter_value().string_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self.baseline = self.get_parameter('baseline').get_parameter_value().double_value
        self.focal_length = self.get_parameter('focal_length').get_parameter_value().double_value
        self.camera_height_z = self.get_parameter('camera_height_z').get_parameter_value().double_value
        self.camera_offset_x = self.get_parameter('camera_offset_x').get_parameter_value().double_value
        self.camera_pitch_y = self.get_parameter('camera_pitch_y').get_parameter_value().double_value

        self.cap = cv2.VideoCapture(device)
        if not self.cap.isOpened():
            self.get_logger().error(f"Kunne ikke åbne stereokameraet: {device}")
            return

        self.get_logger().info(f"Stereo Node startet. Baseline={self.baseline}m, FocalLength={self.focal_length}px, Height={self.camera_height_z}m, Pitch={self.camera_pitch_y}rad")
        self.timer = self.create_timer(0.05, self.process_frame) # 20 FPS (50ms)

    def process_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warn("Kunne ikke læse billede fra kameraet.")
            return

        # Opdel side-by-side stereobillede (Venstre & Højre strøm)
        h, w, _ = frame.shape
        left_img = frame[0:h, 0:w//2]
        right_img = frame[0:h, w//2:w]

        # Konverter til gråtoner (Grayscale)
        gray_left = cv2.cvtColor(left_img, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(right_img, cv2.COLOR_BGR2GRAY)

        # Beregn stereodisparitet med OpenCV StereoSGBM (Semi-Global Block Matching)
        stereo = cv2.StereoSGBM_create(
            minDisparity=0,
            numDisparities=64,
            blockSize=9,
            P1=8 * 3 * 9 * 9,
            P2=32 * 3 * 9 * 9,
            disp12MaxDiff=1,
            uniquenessRatio=10,
            speckleWindowSize=100,
            speckleRange=32
        )
        disparity = stereo.compute(gray_left, gray_right).astype(np.float32) / 16.0

        # Undgå division med nul og beregn dybdekort: Z = (focal_length * baseline) / disparity
        disparity[disparity <= 0] = 0.1
        depth_map = (self.focal_length * self.baseline) / disparity

        # Publicer det beregnede dybdebillede til visualisering/fejlfinding
        depth_msg = self.bridge.cv2_to_imgmsg(depth_map, encoding="32FC1")
        depth_msg.header.stamp = self.get_clock().now().to_msg()
        depth_msg.header.frame_id = self.frame_id
        self.publisher_depth.publish(depth_msg)

        # ==========================================
        #  3D VIRTUAL LIDAR-ALGORITME MED PITCH-KOMPENSERING 🆕 [HELT OMSKREVET: Modulær 3D-til-2D projektion og højde-filtrering]
        # ==========================================
        # Downsample-grid for at opretholde 20 FPS på Orange Pi (CPU-venlig, men tæt nok til forhindringer)
        step = 4
        rows = np.arange(h // 4, h - 10, step) # Udeluk himmel og helt tæt kofanger
        cols = np.arange(0, w // 2, step)
        v_grid, u_grid = np.meshgrid(rows, cols, indexing='ij')

        # Hent dybdeværdier
        z_c = depth_map[v_grid, u_grid]

        # Validitetsmaske for dybde (arbejdsområde: 0.15m til 4.0m)
        valid_mask = (z_c > 0.15) & (z_c < 4.0)

        if not np.any(valid_mask):
            # Ingen gyldige dybdemålinger; publicer tomt scan for at undgå at hænge
            self.publish_empty_scan(w // 2)
            return

        z_c = z_c[valid_mask]
        v_coords = v_grid[valid_mask]
        u_coords = u_grid[valid_mask]

        # Kameraets optiske center
        cx = (w // 2) / 2.0
        cy = h / 2.0

        # Beregn 3D punkter i kameraets eget koordinatsystem (Standard ROS Camera frame: Z=frem, X=højre, Y=ned)
        x_c = (u_coords - cx) * z_c / self.focal_length
        y_c = (v_coords - cy) * z_c / self.focal_length

        # Trigonometrisk rotation (pitch-kompensation) og translation til base_link (robottens rotationscentrum på jorden)
        theta = self.camera_pitch_y
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)

        # 3D transformation til robot-koordinater:
        # X_r: Afstand fremad fra robottens rotationscentrum (base_link)
        # Y_r: Afstand til venstre (venstre er positiv, højre er negativ)
        # Z_r: Højde over jorden (base_link jordsniveau er 0.0)
        X_r = z_c * cos_t - y_c * sin_t + self.camera_offset_x
        Y_r = -x_c
        Z_r = -y_c * cos_t - z_c * sin_t + self.camera_height_z

        # HINDRINGS-FILTRERING:
        # Vi filtrerer græsset og fliserne fra ved kun at betragte punkter, der rager op over græshøjde (fx >= 5 cm),
        # men som er lavere end robottens fysiske krop (fx <= 45 cm) for at ignorere grene over robotten.
        obstacle_mask = (Z_r >= 0.05) & (Z_r <= 0.45) & (X_r > 0.1) & (X_r < 4.0)

        X_obs = X_r[obstacle_mask]
        Y_obs = Y_r[obstacle_mask]

        # Konverter de registrerede hindringspunkter til 2D-polære koordinater (Afstand R og Vinkel alpha)
        R_obs = np.sqrt(X_obs**2 + Y_obs**2)
        alpha_obs = np.arctan2(Y_obs, X_obs)

        # Opret standardiseret LaserScan-meddelelse til Nav2
        scan = LaserScan()
        scan.header.stamp = self.get_clock().now().to_msg()
        scan.header.frame_id = self.frame_id

        # Kameraets vandrette FOV er ca. 90 grader (1.5708 radianer)
        fov_rad = 1.5708
        num_readings = w // 2
        scan.angle_min = -fov_rad / 2.0
        scan.angle_max = fov_rad / 2.0
        scan.angle_increment = fov_rad / num_readings
        scan.time_increment = 0.0
        scan.scan_time = 0.05
        scan.range_min = 0.15
        scan.range_max = 4.0

        # Initialiser alle målinger med uendelig afstand (betyder ingen hindring registreret i den retning)
        scan_ranges = np.full(num_readings, float('inf'))

        # Find bin-indeks for hvert hindringspunkt
        bin_indices = ((alpha_obs - scan.angle_min) / scan.angle_increment).astype(int)

        # Sørg for at indeks holdes inden for arrayets grænser (mellem -45 og +45 grader)
        valid_bins = (bin_indices >= 0) & (bin_indices < num_readings)
        bin_indices = bin_indices[valid_bins]
        R_obs = R_obs[valid_bins]

        # For hvert vinkel-bin skal vi kun gemme den mindste afstand (det tætteste objekt)
        for idx, r in zip(bin_indices, R_obs):
            if r < scan_ranges[idx]:
                scan_ranges[idx] = r

        # Erstat eventuelle resterende uendelig-værdier med NaN (standard i ROS til "intet objekt fundet")
        scan.ranges = np.where(np.isinf(scan_ranges), float('nan'), scan_ranges).tolist()

        self.publisher_scan.publish(scan)

    def publish_empty_scan(self, num_readings):
        scan = LaserScan()
        scan.header.stamp = self.get_clock().now().to_msg()
        scan.header.frame_id = self.frame_id
        fov_rad = 1.5708
        scan.angle_min = -fov_rad / 2.0
        scan.angle_max = fov_rad / 2.0
        scan.angle_increment = fov_rad / num_readings
        scan.time_increment = 0.0
        scan.scan_time = 0.05
        scan.range_min = 0.15
        scan.range_max = 4.0
        scan.ranges = [float('nan')] * num_readings
        self.publisher_scan.publish(scan)

def main(args=None):
    rclpy.init(args=args)
    node = StereoNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()