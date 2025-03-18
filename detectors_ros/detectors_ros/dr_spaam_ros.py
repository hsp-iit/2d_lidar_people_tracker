import numpy as np
import rclpy
import sys

import typing

# Lifecycle nodes provide the same interface as normal nodes in ros2
# For more infos check https://github.com/ros2/demos/tree/rolling/lifecycle_py
# from rclpy.node import Node
from rclpy.lifecycle import Node
from rclpy.lifecycle import Publisher
from rclpy.lifecycle import State
from rclpy.lifecycle import TransitionCallbackReturn

from rclpy.parameter import Parameter

from sensor_msgs.msg import LaserScan, Image
from geometry_msgs.msg import Point, Pose, PoseArray
from visualization_msgs.msg import Marker

from dr_spaam.detector import Detector
from dr_spaam.utils import utils as u
import cv2
from cv_bridge import CvBridge


class DrSpaamROS(Node):
    """ROS node to detect pedestrian using DROW3 or DR-SPAAM."""

    def __init__(self):
        super().__init__("dr_spaam_ros")
        self._read_params()
        self._detector = Detector(
            self.weight_file,
            model=self.detector_model,
            gpu=self.use_gpu,
            stride=self.stride,
            panoramic_scan=self.panoramic_scan,
        )
        # self._init() # is now called in onConfigure

    def _read_params(self):
        """
        @brief      Reads parameters from ROS server.
        """
        self.declare_parameter("weight_file", "/home/morpheus/code/2d_lidar_people_tracker/detectors_ros/checkpoints/ckpt_jrdb_ann_dr_spaam_e20.pth")
        self.declare_parameter("conf_thresh", 0.8)
        self.declare_parameter("stride", 2)
        self.declare_parameter("detector_model", "DR-SPAAM")
        self.declare_parameter("panoramic_scan", True)	
        self.declare_parameter("use_gpu", False)	
		
        self.weight_file = str(self.get_parameter("weight_file").value)
        self.conf_thresh = float(self.get_parameter("conf_thresh").value)
        self.stride = int(self.get_parameter("stride").value)
        self.detector_model = str(self.get_parameter("detector_model").value)
        self.panoramic_scan = bool(self.get_parameter("panoramic_scan").value)
        self.use_gpu = bool(self.get_parameter("use_gpu").value)

    def read_subscriber_param(self, name):
        """
        @brief      Convenience function to read subscriber parameter.
        """
        self.declare_parameter("subscriber/" + name + "/topic", "laser")
        self.declare_parameter("subscriber/" + name + "/queue_size", 10)
	
        topic = str(self.get_parameter("subscriber/" + name + "/topic").value)
        queue_size = int(self.get_parameter("subscriber/" + name + "/queue_size").value)
        return topic, queue_size

    def read_publisher_param(self, name):
        """
        @brief      Convenience function to read publisher parameter.
        """
        self.declare_parameter("publisher/" + name + "/topic", "dr_spaam_" + name)
        self.declare_parameter("publisher/" + name + "/queue_size", 10)
        self.declare_parameter("publisher/" + name + "/latch", False)

        topic = str(self.get_parameter("publisher/" + name + "/topic").value)
        queue_size = int(self.get_parameter("publisher/" + name + "/queue_size").value)
        latch = bool(self.get_parameter("publisher/" + name + "/latch").value)
        return topic, queue_size, latch
    
    def _init(self):
        """
        @brief      Initialize ROS connection.
        """
        # Publisher
        topic, queue_size, latch = self.read_publisher_param("detections")
        self._dets_pub = self.create_lifecycle_publisher(
            PoseArray, topic, queue_size #, latch=latch
        )

        topic, queue_size, latch = self.read_publisher_param("rviz")
        self._rviz_pub = self.create_lifecycle_publisher(
            Marker, topic, queue_size #, latch=latch
        )

        # Subscriber
        topic, queue_size = self.read_subscriber_param("scan")

        # There does not exists for the time being a lifecycle_subscriber
        # https://github.com/ros2/demos/issues/488
        # So we will keep on reading even if the process is stopped
        self._scan_sub = self.create_subscription(
            LaserScan, topic, self._scan_callback, queue_size
        )

        self.br = CvBridge()
        #self.video_out = cv2.VideoWriter('/tmp/output.avi', cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), 20.0, (512,512))

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        self._init()
        self.get_logger().info('on_configure() is called.')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        # The different behaviour of publishers will be
        # defined in _scan_callback
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        return super().on_deactivate(state)

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        """
        Cleanup the node, after a cleaning-up transition is requested.

        on_cleanup callback is being called when the lifecycle node
        enters the "cleaning up" state.

        :return: The state machine either invokes a transition to the "unconfigured" state or stays
            in "inactive" depending on the return value.
            TransitionCallbackReturn.SUCCESS transitions to "unconfigured".
            TransitionCallbackReturn.FAILURE transitions to "inactive".
            TransitionCallbackReturn.ERROR or any uncaught exceptions to "errorprocessing"
        """
        self.destroy_publisher(self._dets_pub)
        self.destroy_publisher(self._rviz_pub)
        self.destroy_subscription(self._scan_sub)

        self.get_logger().info('on_cleanup() is called.')
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """
        Shutdown the node, after a shutting-down transition is requested.

        on_shutdown callback is being called when the lifecycle node
        enters the "shutting down" state.

        :return: The state machine either invokes a transition to the "finalized" state or stays
            in the current state depending on the return value.
            TransitionCallbackReturn.SUCCESS transitions to "unconfigured".
            TransitionCallbackReturn.FAILURE transitions to "inactive".
            TransitionCallbackReturn.ERROR or any uncaught exceptions to "errorprocessing"
        """
        self.destroy_publisher(self._dets_pub)
        self.destroy_publisher(self._rviz_pub)
        self.destroy_subscription(self._scan_sub)

        self.get_logger().info('on_shutdown() is called.')
        return TransitionCallbackReturn.SUCCESS

    def _scan_callback(self, msg):
        
        if (self._dets_pub is None or not self._dets_pub.is_activated
            or self._rviz_pub is None or not self._rviz_pub.is_activated
        ):
            self.get_logger().info('Lifecycle publisher is deactivated. Messages are not published.')
            return
        
        if (
            self._dets_pub.get_subscription_count() == 0
            and self._rviz_pub.get_subscription_count() == 0
        ):
            return

        # TODO check the computation here
        if not self._detector.is_ready():
            self._detector.set_laser_fov(
                np.rad2deg(msg.angle_increment * len(msg.ranges))
            )

        scan = np.array(msg.ranges)
        scan[scan == 0.0] = 29.99
        scan[np.isinf(scan)] = 29.99
        scan[np.isnan(scan)] = 29.99

        # t = time.time()
        dets_xy, dets_cls, _ = self._detector(scan)
        # print("[DrSpaamROS] End-to-end inference time: %f" % (t - time.time()))

        # confidence threshold
        conf_mask = (dets_cls >= self.conf_thresh).reshape(-1)
        dets_xy = dets_xy[conf_mask]
        dets_cls = dets_cls[conf_mask]

        # convert to ros msg and publish
        dets_msg = detections_to_pose_array(dets_xy, dets_cls)
        dets_msg.header = msg.header
        self._dets_pub.publish(dets_msg)

        rviz_msg = detections_to_rviz_marker(dets_xy, dets_cls)
        rviz_msg.header = msg.header
        self._rviz_pub.publish(rviz_msg)


def detections_to_rviz_marker(dets_xy, dets_cls, color = (1.0, 0.0, 0.0, 1.0)):
    """
    @brief     Convert detection to RViz marker msg. Each detection is marked as
               a circle approximated by line segments.
    """
    msg = Marker()
    msg.action = Marker.ADD
    msg.ns = "dr_spaam_ros"
    msg.id = 0
    msg.type = Marker.LINE_LIST
    #msg.header.frame_id = "mobile_base_double_lidar"
    # set quaternion so that RViz does not give warning
    msg.pose.orientation.x = 0.0
    msg.pose.orientation.y = 0.0
    msg.pose.orientation.z = 0.0
    msg.pose.orientation.w = 1.0

    msg.scale.x = 0.03  # line width
    msg.color.r = color[0]
    msg.color.g = color[1]
    msg.color.b = color[2]    
    msg.color.a = color[3]

    # circle
    r = 0.4
    ang = np.linspace(0, 2 * np.pi, 20)
    xy_offsets = r * np.stack((np.cos(ang), np.sin(ang)), axis=1)

    # to msg
    for d_xy, d_cls in zip(dets_xy, dets_cls):
        d_xy = -d_xy
        for i in range(len(xy_offsets) - 1):
            # start point of a segment
            p0 = Point()
            p0.x = d_xy[0] + xy_offsets[i, 0]
            p0.y = d_xy[1] + xy_offsets[i, 1]
            p0.z = 0.0
            msg.points.append(p0)

            # end point
            p1 = Point()
            p1.x = d_xy[0] + xy_offsets[i + 1, 0]
            p1.y = d_xy[1] + xy_offsets[i + 1, 1]
            p1.z = 0.0
            msg.points.append(p1)

    return msg


def detections_to_pose_array(dets_xy, dets_cls):
    pose_array = PoseArray()
    for d_xy, d_cls in zip(dets_xy, dets_cls):
        d_xy = -d_xy
        # Detector uses following frame convention:
        # x forward, y rightward, z downward, phi is angle w.r.t. x-axis
        p = Pose()
        p.position.x = float(d_xy[0])
        p.position.y = float(d_xy[1])
        p.position.z = 0.0
        pose_array.poses.append(p)

    return pose_array


def main(args=None):
    rclpy.init(args=args)
    executor = rclpy.executors.SingleThreadedExecutor()
    node = DrSpaamROS()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        node.destroy_node()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
