import threading
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.signals import SignalHandlerOptions
from rclpy.qos import QoSProfile, HistoryPolicy, ReliabilityPolicy
from sensor_msgs.msg import Image
import numpy as np
import cv2
from gz.transport13 import Node as GzNode
from gz.msgs10.pose_v_pb2 import Pose_V
import math
import time

ARUCO_DICT = cv2.aruco.DICT_4X4_50
POSE_TOPIC = "/world/default/pose/info"
MODEL_NAME = "x500_mono_cam_down_0"
HFOV = 1.74
TOPIC = "/world/default/model/x500_mono_cam_down_0/link/camera_link/sensor/camera/image"
QOS = QoSProfile(
    depth=1,
    history=HistoryPolicy.KEEP_LAST,
    reliability=ReliabilityPolicy.RELIABLE,
)
    
class MarkerDetector(Node):
    def __init__(self):
        super().__init__("marker_detector")
        self.latest = None
        dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
        params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(dictionary, params)
        self.create_subscription(Image, TOPIC, self.on_frame, QOS)
        self.altitude = None
        self.gz = GzNode()
        self.gz.subscribe(Pose_V, POSE_TOPIC, self.on_pose)
        
    def on_frame(self, msg):
        frame = np.frombuffer(msg.data, dtype = np.uint8).reshape(msg.height, msg.width, 3)
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        detect_start = time.perf_counter()
        corners, ids, _ = self.detector.detectMarkers(gray)
        detect_end = time.perf_counter()
        detect_time = detect_end - detect_start
        
        detected = (ids is not None)
        err_x = err_y = err_x_m = err_y_m = math.nan     
        alt = self.altitude
        if alt is None:
            alt = math.nan   
        if detected:
            center = corners[0][0].mean(axis=0)
            err_x = center[0] - msg.width / 2
            err_y = center[1] - msg.height / 2
            
            focal = (msg.width / 2) / math.tan(HFOV / 2)
            err_x_m = err_x * alt/focal
            err_y_m = err_y * alt/focal
            if not (math.isnan(err_x_m) or math.isnan(err_y_m)):
                self.latest = (err_x_m, err_y_m, time.monotonic())           
        detect_ms = (detect_time) * 1000
        
    def on_pose(self, msg):
        for pose in msg.pose:
            if pose.name == MODEL_NAME:
                self.altitude = pose.position.z
                return


def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = MarkerDetector()
    executor = SingleThreadedExecutor()
    executor.add_node(node)

    t1 = threading.Thread(target=executor.spin, daemon=True)
    t1.start()
    
    try:
        while True:
            latest_pos = node.latest
            if latest_pos:
                latest_x, latest_y, latest_time = latest_pos
                print(f"x: {latest_x:.2f}, y: {latest_y:.2f}, age: {(time.monotonic() - latest_time):.3f}")
            else:
                print("node.latest unavailable")
            time.sleep(.05)
            
    except KeyboardInterrupt:
        pass
        
    finally:
        executor.shutdown()
        t1.join(timeout=2)
        node.destroy_node()
        rclpy.try_shutdown()
         
if __name__ == "__main__":
    main()