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
import pygame

from robot_controller.geometry_lib import *
from robot_controller.critical_check import critical_check
from robot_controller_interfaces.srv import CellObservation

# Initialize pygame
pygame.init()

# Define constants for the GUI window
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
BACKGROUND_COLOR = (255, 255, 255)
GRID_COLOR = (0, 0, 0)
LINE_WIDTH = 2

# Zoom and pan control variables







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


class Agent:
    def __init__(self,name,parent_node):
        self.name = name
        self.pose = None
        self.pose_sub = None
        self.pose_pub = None
        self.parent_node = parent_node
        self.color = 'red'
        self.inbox_pub = None

    def pose_sub_callback(self,msg):
        self.pose = msg.pose

        #self.parent_node.get_logger().info(f"{self.name }: {msg}")
    def communicate(self, msg: dict):
        # Add sender ID
        try:
            json_str = json.dumps(msg)
            ros_msg = String()
            ros_msg.data = json_str
            self.inbox_pub.publish(ros_msg)
            self.parent_node.get_logger().info(f"forward msg to {self.name}")



        except (TypeError, ValueError) as e:
            self.parent_node.get_logger().error(f"Failed to serialize message: {e}")



class MarsEnv(Node):
    def __init__(self):
        super().__init__('mars_env')
        self.config = None
        self.grid_config = None
        self.agents = {}



        self.declare_parameter('config_path', '')


        config_path = self.get_parameter('config_path').get_parameter_value().string_value

        self.load_config(config_path)

        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        self.pose = None
        self.create_timer(0.05, self.control_loop)

        # Pygame window setup
        info = pygame.display.Info()
        SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)

        pygame.display.set_caption('Grid Map Display')
        self.pygame_running_flag = True
        self.target_pose = None # (x,y,yaw) for simplicity
        self.state = 'IDLE'

        # for sweeping
        self.swept_cell = []
        self.path = []
        self.path_idx = 0
        #
        self.pauseflag = True

        self.create_subscription(String, '/mars_env/inbox', self.handle_agent_msg, 10)
        self.cell_obs_srv = self.create_service(
            CellObservation,
            'cell_observation',
            self.handle_cell_observation
        )

    def handle_cell_observation(self, request, response):
        col = request.col
        row = request.row
        mega_cell = get_mega_cell(col, row)

        occupied = self.is_mcell_obstruct(mega_cell)
        response.occupied = occupied

        self.get_logger().info(f"Service call: cell_observation({col},{row}) -> {occupied}")
        return response

    def handle_agent_msg(self, msg: String):

        try:
            data = json.loads(msg.data)
            sender = data.get("sender", "unknown")
            receiver = data.get("receiver", "unknown")
            self.get_logger().info(f"Received from agent: {sender} to {receiver}")
            if receiver == 'BROADCAST':
                sender_robot = self.agents[sender]

                #sender_pos = np.array([sender_robot.x, sender_robot.y])

                for id, _robot in self.agents.items():
                    if id != sender:
                        #receiver_pos = np.array([_robot.x, _robot.y])
                        #distance = np.linalg.norm(sender_pos - receiver_pos)
                        #if distance <= COMMUNICATION_RANGE:
                        _robot.communicate(data)

            else:
                sender_robot = self.agents[sender]
                #sender_pos = np.array([sender_robot.x, sender_robot.y])

                receiver_robot = self.agents[receiver]

                #receiver_pos = np.array([receiver_robot.x, receiver_robot.y])

                #distance = np.linalg.norm(sender_pos - receiver_pos)
                #if distance <= COMMUNICATION_RANGE:
                receiver_robot.communicate(data)
        except json.JSONDecodeError:
            self.get_logger().warn("Malformed JSON message")

        # Parse sender and message

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

    def load_config(self,config_path):
        print('load_config: ',config_path)
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

        info = pygame.display.Info()
        SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h
        scale_x = 0.8 * SCREEN_WIDTH / (self.max_x - self.min_x)
        scale_y = 0.8 * SCREEN_HEIGHT / (self.max_y - self.min_y)
        self.scale = min(scale_x, scale_y)

        self.center_x = (self.min_x + self.max_x) / 2
        self.center_y = (self.min_y + self.max_y) / 2

    def load_agent_config(self, agent_config):
        self.agents = {}
        for agent_name, agent_data in agent_config.items():
            current_pos_topic = agent_data.get('current_pos_topic', '')
            target_pos_topic = agent_data.get('target_pos_topic', '')
            color = agent_data.get('color', 'red')
            qos_profile = QoSProfile(
                reliability=ReliabilityPolicy.BEST_EFFORT,
                history=HistoryPolicy.KEEP_LAST,
                depth=1
            )


            self.agents[agent_name] = Agent(agent_name,self)
            self.agents[agent_name].pose_pub = self.create_publisher(PoseStamped, target_pos_topic, 10)
            self.agents[agent_name].pose_sub =  self.create_subscription(PoseStamped,current_pos_topic,self.agents[agent_name].pose_sub_callback,qos_profile),
            self.agents[agent_name].color = color
            self.agents[agent_name].inbox_pub = self.create_publisher(String, f'/{agent_name}/inbox', 10)

            self.get_logger().info(f"Loaded agent {agent_name}:")
            self.get_logger().info(f"  Current topic: {current_pos_topic}")
            self.get_logger().info(f"  Target topic: {target_pos_topic}")


    def pose_callback(self, msg: PoseStamped):
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
        robot_x, robot_y = self.pose.position.x, self.pose.position.y
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


    def control_loop(self):
        self.update_gui()







    def observe_kernel(self, kernel_cells):

        res = []
        for mega_cells in kernel_cells:

            if not self.is_mcell_obstruct(mega_cells) and mega_cells not in self.swept_cell:
                res.append(0)
            else:
                res.append(1)
        return res
    def critical_ckeck(self,kernel_observe):
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



    def event_handle(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.pygame_running_flag = False
                self.get_logger().info(f"pygame.quit ...")
                pygame.quit()
                return

            elif event.type == pygame.KEYDOWN:
                pan_const = 0.1
                if event.key == pygame.K_EQUALS:
                    self.scale *= 1.1
                    self.get_logger().info(f"Zoom-in, scale:{self.scale:0.2f}")

                elif event.key == pygame.K_MINUS:
                    self.scale /= 1.1
                elif event.key == pygame.K_LEFT:
                    self.center_x  -= pan_const
                elif event.key == pygame.K_RIGHT:
                    self.center_x  += pan_const
                elif event.key == pygame.K_UP:
                    self.center_y -= pan_const
                elif event.key == pygame.K_DOWN:
                    self.center_y  += pan_const
                elif event.key == pygame.K_SPACE:
                    self.pauseflag = not  self.pauseflag
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 2: # Left-Mouse click
                screen_x, screen_y = pygame.mouse.get_pos()
                world_x, world_y = self.screen_to_world(screen_x, screen_y)
                print(f"Clicked at world coordinates: ({world_x:.2f}, {world_y:.2f})")
                p_i = (world_x, world_y )

                col,row = self.find_row_col(p_i)
                print(f"cell pos (row,col) ({row:d}, {col:d})")
                target_x,target_y  = self.get_cell_center(col, row)
                target_yaw = 0
                if  self.pose:
                    x, y = self.pose.position.x, self.pose.position.y
                    target_yaw = np.arctan2(target_y - y, target_x - x)
                self.target_pose = (target_x,target_y , target_yaw)
                print(f"target_pose: ({self.target_pose[0]:.2f}, {self.target_pose[1]:.2f})")
                self.publish_target_pose(target_x,target_y,yaw = target_yaw)

    def get_cell_center(self,col,row):
        return get_cell_center(self.p1, self.p2, self.p3, self.p4, row, col, self.num_row, self.num_col)
    def find_row_col(self,p_i):
        row,col = find_row_col(p_i, self.p1, self.p2, self.p3, self.p4, self.num_row, self.num_col)
        return col,row
    def update_gui(self):


        self.event_handle()
        # Handle Pygame events (for zoom and pan)

        # Clear the screen
        self.screen.fill(BACKGROUND_COLOR)

        # Scale and translate grid corners to fit within screen size
        self.screen.fill(BACKGROUND_COLOR)

        # Draw grid if available
        if self.grid_config:
            self.draw_grid(self.grid_config)
        else:
            self.get_logger().info(f"Error, no self.grid_config")

        # Draw robot
        for agent_name, agent in self.agents.items():

            if agent.pose:
                self.draw_robot(agent.pose,agent.color)


        if self.pose:
            self.draw_robot(self.pose)


        # Update the display
        pygame.display.flip()

    def draw_grid(self, grid_config):
        try:
            corners = [tuple(corner) for corner in self.grid_corners]
            transformed = [self.world_to_screen(x, y) for (x, y) in corners]
            pygame.draw.polygon(self.screen, GRID_COLOR, transformed, LINE_WIDTH)
            font = pygame.font.Font(None, 24)  # Use default font, size 24

            # Draw row lines
            row_alpha_range = np.linspace(0, 1, self.num_row)
            for row_alpha in row_alpha_range:
                x1 = row_alpha * self.p1[0] + (1 - row_alpha) * self.p4[0]
                y1 = row_alpha * self.p1[1] + (1 - row_alpha) * self.p4[1]
                screen_pos1 = self.world_to_screen(x1, y1)
                pygame.draw.circle(self.screen, (255, 0, 0), screen_pos1, 10)

                x2 = row_alpha * self.p2[0] + (1 - row_alpha) * self.p3[0]
                y2 = row_alpha * self.p2[1] + (1 - row_alpha) * self.p3[1]
                screen_pos2 = self.world_to_screen(x2, y2)
                pygame.draw.circle(self.screen, (200, 0, 0), screen_pos2, 10)

            # Draw column lines
            col_beta_range = np.linspace(0, 1, self.num_col)
            for col_beta in col_beta_range:
                x = col_beta * self.p1[0] + (1 - col_beta) * self.p2[0]
                y = col_beta * self.p1[1] + (1 - col_beta) * self.p2[1]
                screen_pos = self.world_to_screen(x, y)
                pygame.draw.circle(self.screen, (0, 255, 0), screen_pos, 10)

                x = col_beta * self.p4[0] + (1 - col_beta) * self.p3[0]
                y = col_beta * self.p4[1] + (1 - col_beta) * self.p3[1]
                screen_pos = self.world_to_screen(x, y)
                pygame.draw.circle(self.screen, (0, 255, 0), screen_pos, 10)
            for row in range(self.num_row):
                for col in range( self.num_col):
                    x,y = get_cell_center(self.p1, self.p2, self.p3, self.p4, row, col, self.num_row, self.num_col)
                    screen_pos = self.world_to_screen(x, y)
                    mcell = get_mega_cell(col,row)
                    if mcell in self.swept_cell:
                        pygame.draw.circle(self.screen, (0, 255, 0), screen_pos, 10)
                    else:
                        pygame.draw.circle(self.screen, (200, 200, 200), screen_pos, 10)
                    label = f"{row},{col}"
                    text_surface = font.render(label, True, (0, 0, 0))  # black text
                    text_rect = text_surface.get_rect(center=(screen_pos[0], screen_pos[1] - 10))
                    #self.screen.blit(text_surface, text_rect)


            # Add labels for corners

            labels = ['P1', 'P2', 'P3', 'P4']
            for i, (screen_pos, label) in enumerate(zip(transformed, labels)):
                text_surface = font.render(label, True, (0, 0, 0))  # black text
                text_rect = text_surface.get_rect(center=(screen_pos[0], screen_pos[1] - 10))
                #self.screen.blit(text_surface, text_rect)


        except Exception as e:
            self.get_logger().error(f"Error drawing grid: {e}")

    def draw_robot(self, pose,color):
        x, y = pose.position.x, pose.position.y
        screen_pos = self.world_to_screen(x, y)
        pygame.draw.circle(self.screen, color, screen_pos, 20)

        # Draw heading
        q = [pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w]
        _, _, yaw = euler_from_quaternion(q)
        heading_length = 0.5
        dx = heading_length * np.cos(yaw)
        dy = heading_length * np.sin(yaw)
        heading_pos = self.world_to_screen(x + dx, y + dy)
        pygame.draw.line(self.screen, (0, 0, 0), screen_pos, heading_pos, 2)

        #
        p_i = (x,y)
        alpha,beta = solve_alpha_beta(p_i,self.p1,self.p2,self.p3,self.p4)

        #
        x1 = alpha * self.p1[0] + (1 - alpha) * self.p4[0]
        y1 = alpha * self.p1[1] + (1 - alpha) * self.p4[1]
        screen_pos1 = self.world_to_screen(x1, y1)
        #
        x2 = alpha * self.p2[0] + (1 - alpha) * self.p3[0]
        y2 = alpha * self.p2[1] + (1 - alpha) * self.p3[1]
        screen_pos2 = self.world_to_screen(x2, y2)
        #pygame.draw.line(self.screen, (255, 0, 0), screen_pos1, screen_pos2, 2)
        #

        # Corrected green line
        x1 = beta * self.p1[0] + (1 - beta) * self.p2[0]
        y1 = beta * self.p1[1] + (1 - beta) * self.p2[1]
        screen_pos1 = self.world_to_screen(x1, y1)

        x2 = beta * self.p4[0] + (1 - beta) * self.p3[0]
        y2 = beta * self.p4[1] + (1 - beta) * self.p3[1]
        screen_pos2 = self.world_to_screen(x2, y2)

        #pygame.draw.line(self.screen, (0, 255, 0), screen_pos1, screen_pos2, 2)
        #
        col, row = self.find_row_col(p_i)

        #self.get_logger().info(f"row:{row}, col:{col}")
        p_i = self.get_cell_center(col,row)



        screen_pos2 = self.world_to_screen(p_i[0], p_i[1])
        pygame.draw.circle(self.screen, (0, 0, 255), screen_pos2, 10)



    def draw_target(self):

        # draw target
        x, y,yaw = self.target_pose
        screen_pos = self.world_to_screen(x, y)
        pygame.draw.circle(self.screen, (100, 100, 100), screen_pos, 20)

        # Draw heading

        heading_length = 0.5
        dx = heading_length * np.cos(yaw)
        dy = heading_length * np.sin(yaw)
        heading_pos = self.world_to_screen(x + dx, y + dy)
        pygame.draw.line(self.screen, (100, 100, 100), screen_pos, heading_pos, 2)

    def world_to_screen(self, x, y):
        # Translate to center around (0, 0)
        info = pygame.display.Info()
        SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h
        x_rel = x - self.center_x
        y_rel = y - self.center_y

        # Flip y-axis (so +y is up) and scale
        screen_x = int(SCREEN_WIDTH // 2 + x_rel * self.scale)
        screen_y = int(SCREEN_HEIGHT // 2 - y_rel * self.scale)

        return (screen_x, screen_y)

    def screen_to_world(self, screen_x, screen_y):
        info = pygame.display.Info()
        SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h

        # Translate screen to centered coordinates
        x_rel = (screen_x - SCREEN_WIDTH // 2) / self.scale
        y_rel = -(screen_y - SCREEN_HEIGHT // 2) / self.scale  # Flip Y back

        # Add center offset
        world_x = x_rel + self.center_x
        world_y = y_rel + self.center_y

        return (world_x, world_y)


def main(args=None):
    rclpy.init(args=args)
    node = MarsEnv()
    while rclpy.ok() and node.pygame_running_flag:
        #node.get_logger().info("RobotNav node running")
        rclpy.spin_once(node)
    node.get_logger().info("RobotNav node stopping")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
