import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from sensor_msgs.msg import Image, PointCloud2
import message_filters
from cv_bridge import CvBridge
import cv2
import numpy as np
import struct
import os

try:
    from rknnlite.api import RKNNLite
    NPU_AVAILABLE = True
except ImportError:
    NPU_AVAILABLE = False

class DepthFusionNode(Node):
    def __init__(self):
        super().__init__('depth_fusion_node')

        # Publishers
        self.estop_pub = self.create_publisher(Bool, 'e_stop', 10)
        self.bridge = CvBridge()

        # Dynamic Configurations
        self.min_safe_distance = float(os.getenv('MIN_SAFE_DISTANCE', '1.0'))
        self.danger_classes = [0, 3, 4]  # 0: dog, 3: poo, 4: toy

        # Initialize RK3588 NPU
        if NPU_AVAILABLE:
            self.get_logger().info('Initializing Rockchip NPU Engine...')
            self.rknn = RKNNLite()
            ret = self.rknn.load_rknn('./mowerAIn-seg.rknn')
            if ret != 0:
                self.get_logger().error('Failed to load RKNN model!')
            self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_AUTO)
        else:
            self.get_logger().warn('NPU Offline: Object detection disabled, running depth pass-through.')

        # Synchronized Subscriptions (message_filters)
        self.image_sub = message_filters.Subscriber(self, Image, 'camera/left/image_raw')
        self.pc_sub = message_filters.Subscriber(self, PointCloud2, 'camera/depth/points')

        # Time synchronize with 50ms maximum slop tolerance
        self.ts = message_filters.ApproximateTimeSynchronizer(
            [self.image_sub, self.pc_sub],
            queue_size=10,
            slop=0.05
        )
        self.ts.registerCallback(self.sync_callback)
        self.get_logger().info('Depth Fusion synchronizer successfully registered.')

    def get_3d_point(self, pc_msg, u, v):
        """Extracts X, Y, Z coordinates from structured PointCloud2 byte stream."""
        if u < 0 or u >= pc_msg.width or v < 0 or v >= pc_msg.height:
            return None

        # Calculate byte index offset
        offset = (v * pc_msg.row_step) + (u * pc_msg.point_step)

        try:
            # Unpack 3 x 32-bit float variables (x, y, z)
            x, y, z = struct.unpack_from('fff', pc_msg.data, offset)

            # Filter out invalid NaN floats
            if np.isnan(x) or np.isnan(y) or np.isnan(z):
                return None
            return (x, y, z)
        except Exception:
            return None

    def sync_callback(self, image_msg, pc_msg):
        """Triggered automatically when image and point cloud timestamps align."""
        frame = self.bridge.imgmsg_to_cv2(image_msg, desired_encoding='bgr8')
        h, w, _ = frame.shape
        danger_detected = False

        if NPU_AVAILABLE:
            # Resize image to model resolution (800x800)
            img_resized = cv2.resize(frame, (800, 800))
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

            # Execute hardware inference
            outputs = self.rknn.inference(inputs=[img_rgb])
            pred = outputs[0]
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
                    if class_id in self.danger_classes:
                        cx, cy, w_box, h_box = row[0:4]
                        x_box = int(cx - (w_box / 2))
                        y_box = int(cy - (h_box / 2))

                        boxes.append([x_box, y_box, int(w_box), int(h_box)])
                        scores.append(float(max_score))
                        class_ids.append(class_id)

            indices = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, 0.45)

            if len(indices) > 0:
                for i in indices.flatten():
                    class_id = class_ids[i]
                    box = boxes[i]

                    # Compute centroid in 2D
                    u_center = box[0] + box[2] // 2
                    v_center = box[1] + box[3] // 2

                    # Map coordinates back to native PointCloud resolution
                    u_scaled = int(u_center * (pc_msg.width / 800.0))
                    v_scaled = int(v_center * (pc_msg.height / 800.0))

                    # Direct binary PointCloud retrieval
                    point_3d = self.get_3d_point(pc_msg, u_scaled, v_scaled)

                    if point_3d is not None:
                        x, y, z_depth = point_3d
                        self.get_logger().info(
                            f'Object {class_id} confirmed at 3D coordinate: X={x:.2f}m, Y={y:.2f}m, Z_depth={z_depth:.2f}m'
                        )

                        # Danger Zone Proximity Evaluation
                        if z_depth < self.min_safe_distance:
                            self.get_logger().warn(f'CRITICAL BRAKE: Obstacle [{class_id}] within hazard boundary ({z_depth:.2f}m)!')
                            danger_detected = True
                            break

        # Publish emergency stop state
        estop_msg = Bool()
        estop_msg.data = danger_detected
        self.estop_pub.publish(estop_msg)

def main(args=None):
    rclpy.init(args=args)
    node = DepthFusionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if NPU_AVAILABLE:
            node.rknn.release()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()