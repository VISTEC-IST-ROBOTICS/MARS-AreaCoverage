import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Twist,  TransformStamped
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from tf_transformations import euler_from_quaternion, quaternion_from_euler
from tf_transformations import quaternion_inverse, quaternion_multiply
from tf_transformations import quaternion_matrix
import tf2_ros
import numpy as np



def transform_to_robot_frame(target_point_world, robot_pose):
    # Robot position in world
    pos = robot_pose.position
    robot_pos = np.array([pos.x, pos.y, pos.z])

    # Robot orientation (quaternion)
    ori = robot_pose.orientation
    q = [ori.x, ori.y, ori.z, ori.w]

    # Rotation matrix from world to robot frame
    rot_matrix = quaternion_matrix(q)[:3, :3]  # Only take the rotation part

    # Translate target point to robot-centered coordinates
    vec_world = target_point_world - robot_pos

    # Rotate vector into robot frame (i.e., apply inverse rotation)
    vec_robot = rot_matrix.T @ vec_world

    return vec_robot


def create_quaternion_from_yaw(yaw):
    return quaternion_from_euler(0.0, 0.0, yaw)

def compute_heading_error(q_current, q_target):
    q_err = quaternion_multiply(q_target, quaternion_inverse(q_current))
    _, _, yaw_err = euler_from_quaternion(q_err)
    return yaw_err

def bound(x, min_val, max_val):
    return min(max(x, min_val), max_val)


class RobotController(Node):
    def __init__(self):
        super().__init__('robot_controller')
        self.declare_parameter('robot_namespace', 'robot_1')
        self.namespace = self.get_parameter('robot_namespace').get_parameter_value().string_value
        # Publisher: velocity command
        self.cmd_pub = self.create_publisher(Twist, f'/{self.namespace}/cmd_vel', 10)

        # Subscriber: pose from motion capture with matching QoS
        qos_profile = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
        )
        default_qos = QoSProfile(depth=10)
        self.pose_sub = self.create_subscription(
            PoseStamped,
            f'/vrpn_mocap/{self.namespace}/pose',
            self.pose_callback,
            qos_profile
        )
        self.target_pose_sub = self.create_subscription(
            PoseStamped,
            f'/{self.namespace}/target_pose',
            self.target_pose_callback,
            default_qos
        )
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)


        self.get_logger().info(f'RobotController node started for namespace: {self.namespace}')


        self.create_timer(0.05, self.control_loop)
        self.pose = None
        self.target_pose = None

    def target_pose_callback(self, msg: PoseStamped):
        self.target_pose = msg.pose

        self.publish_tf(msg)

    def pose_callback(self, msg: PoseStamped):
        self.pose = msg.pose

        self.publish_tf(msg)




    def control_loop(self):
        if not self.pose or not self.target_pose:
            return

        # Compute position error in robot frame
        target_point_world = np.array([
            self.target_pose.position.x,
            self.target_pose.position.y,
            self.target_pose.position.z
        ])

        error_in_robot_frame = transform_to_robot_frame(target_point_world, self.pose)
        x_err = error_in_robot_frame[0]
        y_err = error_in_robot_frame[1]
        self.get_logger().info(f"position error x={x_err:.2f}, y={y_err:.2f}")
        if abs(x_err) < 0.01:
            x_err = 0.0
        if abs(y_err) < 0.01:
            y_err = 0.0
        yaw_gain = 1
        if abs(x_err) < 0.01 and  abs(y_err) < 0.01:
            yaw_gain = 3

        # Compute yaw error
        current_q = [self.pose.orientation.x, self.pose.orientation.y,
                     self.pose.orientation.z, self.pose.orientation.w]
        target_q = [self.target_pose.orientation.x, self.target_pose.orientation.y,
                    self.target_pose.orientation.z, self.target_pose.orientation.w]

        yaw_err = compute_heading_error(current_q, target_q)

        self.get_logger().info(f"yaw_err: x={np.rad2deg(yaw_err):.2f} degs")
        if abs(yaw_err) < np.deg2rad(5):
            yaw_err = 0.0

        max_yaw_cmd = 0.5
        yaw_cmd = bound(yaw_gain * yaw_err , -max_yaw_cmd, max_yaw_cmd)

        if abs(yaw_cmd) < 0.05:
            yaw_cmd = 0.0

        cmd = Twist()

        cmd.angular.z = yaw_cmd  # No rotation





        cmd.linear.x =np.clip(x_err*15, -0.8, 0.8)
        cmd.linear.y = np.clip(y_err * 15, -0.8, 0.8)


        # Publish velocity command
        self.cmd_pub.publish(cmd)

    def publish_tf(self,msg):
        position = msg.pose.position
        orientation = msg.pose.orientation
        # Publish TF from map → base_link
        t = TransformStamped()
        t.header.stamp = msg.header.stamp  # use mocap timestamp
        t.header.frame_id = 'map'  # world or odom frame
        t.child_frame_id = 'base_link'  # robot body frame

        t.transform.translation.x = position.x
        t.transform.translation.y = position.y
        t.transform.translation.z = position.z
        t.transform.rotation = orientation

        self.tf_broadcaster.sendTransform(t)
def main(args=None):
    rclpy.init(args=args)
    node = RobotController()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

# Grid position
'''
1.37, 3.44
1.35, -1.06
-3.146,-1.034
-3.23, 3,478


'''