import json
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TransformStamped
from std_msgs.msg import String

from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from tf_transformations import (
    euler_from_quaternion,
    quaternion_from_euler,
    quaternion_inverse,
    quaternion_multiply,
    quaternion_matrix,
)
import tf2_ros

import yaml


from robot_controller.geometry_lib import *
from robot_controller.critical_check import critical_check
from robot_controller.MALC_agent import SweepingAgent,AgentState

# Define constants for the GUI window
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
BACKGROUND_COLOR = (255, 255, 255)
GRID_COLOR = (0, 0, 0)
LINE_WIDTH = 2

# Zoom and pan control variables
from enum import Enum

class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.name
        return super().default(obj)






def compute_heading_error(q_current, q_target):
    q_err = quaternion_multiply(q_target, quaternion_inverse(q_current))
    _, _, yaw_err = euler_from_quaternion(q_err)
    return yaw_err




def get_mega_cell(col, row):
    """Return (col, row) of the mega cell (2x2)"""
    mega_col = (col // 2)
    mega_row = (row // 2)
    return (mega_col, mega_row)


def get_sub_cell_offset(col, row):

    # Calculate the offset within the mega-cell (mod 2 to get 0 or 1 offset)
    offset_x = col % 2  # 0 or 1
    offset_y = row % 2  # 0 or 1

    return (offset_x, offset_y)


def get_sub_cell_index(col, row):
    """
    0 | 1
    ------
    2 | 3

    Return sub-cell index [0, 1, 2, 3] inside the current mega-cell
    """

    offset_x, offset_y = get_sub_cell_offset(col, row)
    # Return the sub-cell index based on position within the 2x2 mega-cell
    sub_cell_index = offset_y * 2 + offset_x
    return sub_cell_index

def extract_xy_yaw_from_pose(pose):
    x = pose.position.x
    y = pose.position.y

    # Extract orientation as quaternion
    q = pose.orientation
    quaternion = [q.x, q.y, q.z, q.w]

    # Convert quaternion to Euler angles (roll, pitch, yaw)
    roll, pitch, yaw = euler_from_quaternion(quaternion)

    return x, y, yaw
def create_quaternion_from_yaw(yaw):
    return quaternion_from_euler(0.0, 0.0, yaw)

class Robot:
    def __init__(self, parent_node: "SweepingAgentNode"):
        self.id = parent_node.agent_name
        self.color = parent_node.agent_color
        self.parent_node = parent_node

    def get_col_row(self):
        if self.parent_node.pose is None:
            return None, None  # Consistent return type

        robot_x, robot_y, _ = self.parent_node.get_xy_yaw()
        robot_pos = (robot_x, robot_y)
        col, row = self.parent_node.find_row_col(robot_pos)
        return col, row
    def get_logger(self):
        return self.parent_node.get_logger()

    def communicate(self, msg: dict):
        # Add sender ID
        try:
            json_str = json.dumps(msg, cls=EnumEncoder)

            ros_msg = String()
            ros_msg.data = json_str
            self.parent_node.broker_pub.publish(ros_msg)

            self.get_logger().info(f"Agent {self.id} sent message to broker: {json_str}")
        except (TypeError, ValueError) as e:
            self.get_logger().error(f"Failed to serialize message: {e}")


    def is_idle(self):
        x_err, y_err, yaw_err = self.parent_node.get_pose_error()
        if np.abs(x_err) < 0.05 and np.abs(y_err) < 0.05 and yaw_err < np.deg2rad(10):
            return True
        return False

    def subcell_orientation(self):
        self.parent_node.subcell_pose_orientation()

    def set_target(self,crr_col,crr_row,nxt_col,nxt_row):

        cell_x, cell_y = self.parent_node.get_cell_center(crr_col,crr_row)
        next_cell_x, next_cell_y = self.parent_node.get_cell_center(nxt_col, nxt_row)
        target_yaw = np.arctan2(next_cell_y - cell_y, next_cell_x - cell_x)
        self.parent_node.target_pose = (next_cell_x, next_cell_y, target_yaw)
        self.parent_node.publish_target_pose(next_cell_x, next_cell_y, yaw=target_yaw)

    def update(self):

        pass
    def mega_cell_observation(self,cell):
        return 0

    def sweep(self):
        pass



def restore_agent_state_enum(obj):
    if isinstance(obj, dict):
        return {
            key: restore_agent_state_enum(value)
            for key, value in obj.items()
        }
    elif isinstance(obj, list):
        return [restore_agent_state_enum(item) for item in obj]
    elif isinstance(obj, str):
        try:
            return AgentState[obj]
        except KeyError:
            return obj
    else:
        return obj


class SweepingAgentNode(Node):

    def __init__(self):
        super().__init__('sweeping_agent')
        self.config = None
        self.grid_config = None


        self.declare_parameter('robot_namespace', '')
        self.declare_parameter('config_path', '')


        config_path = self.get_parameter('config_path').get_parameter_value().string_value

        self.load_config(config_path)

        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        self.pose = None
        self.create_timer(1, self.update_loop)
        self.broker_pub = self.create_publisher(String, '/mars_env/inbox', 10)
        self.create_subscription(String, f'/{self.agent_name}/inbox', self.handle_broker_msg, 10)
        self.robot = Robot(self)
        self.sweeping_agent = SweepingAgent(self)


    def handle_broker_msg(self, msg: String):

        try:
            data = json.loads(msg.data)
            sender = data.get("sender", "unknown")
            receiver = data.get("receiver", "unknown")
            self.get_logger().info(f"Received from agent: {sender} to {receiver}")
            data_enum = restore_agent_state_enum(data)
            #self.get_logger().info(data)
            self.get_logger().info(str(data_enum))
            self.sweeping_agent.read_msg(data_enum)

        except json.JSONDecodeError:
            self.get_logger().warn("Malformed JSON message")

    def publish_target_pose(self, x, y, z=0.0, yaw=0.0):
        msg = PoseStamped()

        # Use current time (optional, but good practice)
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'  # or 'world', 'odom', etc.

        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.position.z = z

        # Convert yaw to quaternion
        q = quaternion_from_euler(0.0, 0.0, yaw)
        msg.pose.orientation.x = q[0]
        msg.pose.orientation.y = q[1]
        msg.pose.orientation.z = q[2]
        msg.pose.orientation.w = q[3]

        self.target_pose_pub.publish(msg)
        #self.get_logger().info(f"Published goal: ({x:.2f}, {y:.2f}, {z:.2f}, yaw={yaw:.2f})")

    def load_config(self, config_path):
        print('load_config: ', config_path)
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            self.get_logger().info(f"Loaded grid config from: {config_path}")
        except Exception as e:
            self.get_logger().error(f"Failed to load grid config: {e}")
            self.grid_config = None
            # Separate parts of the config
        map_config = self.config.get('map', {})
        agent_config = self.config.get('agents', {})

        self.load_grid_config(map_config)
        self.load_agent_config(agent_config)

    def load_grid_config(self, map_config):
        self.get_logger().info('==========load_grid_config===========')
        self.grid_config = map_config
        #self.get_logger().info(self.grid_config)

        grid_corners = map_config.get('grid_corners', {})
        self.p1 = np.array(grid_corners.get('p1', [0, 0]))
        self.p2 = np.array(grid_corners.get('p2', [0, 0]))
        self.p3 = np.array(grid_corners.get('p3', [0, 0]))
        self.p4 = np.array(grid_corners.get('p4', [0, 0]))

        self.get_logger().info(f"Grid Corners Loaded:")
        self.get_logger().info(f"P1: {self.p1}")
        self.get_logger().info(f"P2: {self.p2}")
        self.get_logger().info(f"P3: {self.p3}")
        self.get_logger().info(f"P4: {self.p4}")

        self.grid_corners = [self.p1, self.p2, self.p3, self.p4]
        self.min_x = min(corner[0] for corner in self.grid_corners)
        self.max_x = max(corner[0] for corner in self.grid_corners)
        self.min_y = min(corner[1] for corner in self.grid_corners)
        self.max_y = max(corner[1] for corner in self.grid_corners)

        self.num_row = map_config.get('num_row', 0)
        self.num_col = map_config.get('num_col', 0)

    def load_agent_config(self, agent_config):
        agent_name = self.get_parameter('robot_namespace').get_parameter_value().string_value

        if agent_name not in agent_config:
            self.get_logger().error(f"No config found for agent '{agent_name}'")
            return

        agent_data = agent_config[agent_name]

        current_pos_topic = agent_data.get('current_pos_topic', '')
        target_pos_topic = agent_data.get('target_pos_topic', '')
        self.agent_color = agent_data.get('color', 'red')

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        self.agent_name = agent_name
        self.target_pose_pub = self.create_publisher(PoseStamped, target_pos_topic, 10)
        self.current_pose_sub= self.create_subscription(PoseStamped, current_pos_topic, self.current_pos_callback, qos_profile)


        self.get_logger().info(f"Loaded agent {agent_name}:")
        self.get_logger().info(f"  Current topic: {current_pos_topic}")
        self.get_logger().info(f"  Target topic: {target_pos_topic}")

    def current_pos_callback(self, msg: PoseStamped):
        self.pose = msg.pose


    def get_xy_yaw(self):
        x, y, yaw = extract_xy_yaw_from_pose(self.pose)
        return x, y, yaw

    def get_pose_error(self):
        x, y, yaw = self.get_xy_yaw()
        tar_x, tar_y, tar_yaw = self.target_pose
        q = self.pose.orientation
        q_cur = [q.x, q.y, q.z, q.w]
        q_tar = create_quaternion_from_yaw(tar_yaw)
        yaw_err = compute_heading_error(q_cur, q_tar)
        return tar_x - x, tar_y - y, yaw_err


    def subcell_pose_orientation(self):

        robot_x, robot_y , robot_yaw = self.get_xy_yaw()
        robot_pos = (robot_x, robot_y)


        col, row = self.find_row_col(robot_pos)
        cell_x, cell_y = self.get_cell_center(col, row)
        subcell_idx = get_sub_cell_index(col, row)
        self.get_logger().info("subcell_pose_orientation")
        self.get_logger().info(f"sub-cell index: {subcell_idx} from ({col},{row}), pos: {robot_x:.2f},{robot_y:.2f}")
        error = np.abs(cell_x - robot_x) > 0.05 and np.abs(cell_y - robot_y) > 0.05
        next_subcell_clockwise = {
            0: (1,0),
            1: (0,1),
            3: (-1,0),
            2: (0,-1)
        }

        # Compute the offset of the next subcell in clockwise direction
        current_idx = subcell_idx

        head_col, head_row = next_subcell_clockwise[current_idx]
        self.get_logger().info(f"heading_cell: ({head_col},{head_row})")

        heading_cell_x, heading_cell_y = self.get_cell_center(col + head_col, row + head_row)
        target_yaw = np.arctan2(heading_cell_y - cell_y, heading_cell_x - cell_x)
        self.target_pose = (cell_x, cell_y, target_yaw)
        self.publish_target_pose(cell_x, cell_y, yaw=target_yaw)
        self.get_logger().info(f"robot_pos: ({robot_x:.2f},{robot_y:.2f}), heading, {np.rad2deg(robot_yaw):.2f}")
        self.get_logger().info(f"target_pose: ({cell_x:.2f},{cell_y:.2f}), heading, {np.rad2deg(target_yaw):.2f}")


    def update_loop(self):
        self.sweeping_agent.update()
        pass





    def observe_kernel(self, kernel_cells):

        res = []
        for mega_cells in kernel_cells:

            if not self.is_mcell_obstruct(mega_cells) and mega_cells not in self.swept_cell:
                res.append(0)
            else:
                res.append(1)
        return res
    def critical_check(self,kernel_observe):
        key = []

        for idx, nb_mcell in enumerate(kernel_observe):
            if kernel_observe[idx] == 0 and nb_mcell not in self.swept_cell:
                key.append(idx)

        critical = critical_check(tuple(key))
        ret = False
        if critical == 'critical':
            ret = True
        self.get_logger().info(f"critical_check's key: {key},{ret}")
        return ret
    def is_mcell_obstruct(self, mega_cell):
        """
        Checks if the given mega cell is outside the valid grid boundaries.

        :param mega_cell: Tuple[int, int] representing (col, row) of the mega cell
        :return: True if obstructed (i.e., out of bounds), False otherwise
        """
        col, row = mega_cell
        max_col = self.num_col // 2
        max_row = self.num_row // 2

        return not (0 <= col < max_col and 0 <= row < max_row)

    def publish_tf(self, msg):
        position = msg.pose.position
        orientation = msg.pose.orientation

        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = 'map'


        t.transform.translation.x = position.x
        t.transform.translation.y = position.y
        t.transform.translation.z = position.z

        t.transform.rotation = orientation
        self.tf_broadcaster.sendTransform(t)



    def get_cell_center(self,col,row):
        return get_cell_center(self.p1, self.p2, self.p3, self.p4, row, col, self.num_row, self.num_col)
    def find_row_col(self,p_i):
        row,col = find_row_col(p_i, self.p1, self.p2, self.p3, self.p4, self.num_row, self.num_col)
        return col,row


def main(args=None):
    rclpy.init(args=args)
    node = SweepingAgentNode()
    while rclpy.ok() :
        #node.get_logger().info("RobotNav node running")
        rclpy.spin_once(node)
    node.get_logger().info("sweeping_agent node stopping")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
