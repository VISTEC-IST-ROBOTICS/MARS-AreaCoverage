import json
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TransformStamped
from std_msgs.msg import String,Float32

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


# Initialize pygame
pygame.init()

# Define constants for the GUI window
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
BACKGROUND_COLOR = (255, 255, 255)
GRID_COLOR = (0, 0, 0)
LINE_WIDTH = 2

# Zoom and pan control variables




COMMUNICATION_RANGE = 2


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



class Button:
    def __init__(self, rect, text, font, idle_color, hover_color, press_color, text_color=(255, 255, 255)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.idle_color = idle_color
        self.hover_color = hover_color
        self.press_color = press_color
        self.text_color = text_color

        self.enabled = True
        self.pressed = False
        self.hovered = False
        self.clicked = False

    def draw(self, surface):
        color = self.idle_color
        if not self.enabled:
            color = (180, 180, 180)
        elif self.pressed:
            color = self.press_color
        elif self.hovered:
            color = self.hover_color

        pygame.draw.rect(surface, color, self.rect, border_radius=8)

        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def update(self, events):
        self.hovered = False
        self.clicked = False
        if not self.enabled:
            return

        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            self.hovered = True
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.pressed = True
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.pressed:
                    self.clicked = True
                    self.pressed = False
        else:
            self.pressed = False


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
        self.create_timer(0.05, self.control_loop) # 20 Hz

        # Pygame window setup
        info = pygame.display.Info()
        SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        self.gui_init()

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
        self.create_subscription(String, '/mars_env/sweep', self.handle_agent_sweep, 10)
        self.agents_control_pub = self.create_publisher(String, '/mars_env/agent_control', 10)


    def handle_agent_sweep(self,msg: String):
        try:
            data = json.loads(msg.data)
            sender = data.get("sender", "unknown")
            position = data.get("cell", None)
            self.get_logger().info(f"Agent: {sender} has swept at {position}")
            self.swept_cell.append(tuple(position[0:2]))
        except json.JSONDecodeError:
            self.get_logger().warn("Malformed JSON message")


    def handle_agent_msg(self, msg: String):

        try:
            data = json.loads(msg.data)
            sender_id = data.get("sender", "unknown")
            receiver = data.get("receiver", "unknown")
            self.get_logger().info(f"Received from agent: {sender_id} to {receiver}")
            sender = self.agents[sender_id]

            sender_pos = np.array([sender.pose.position.x,sender.pose.position.y])
            if receiver == 'BROADCAST':




                for id, _robot in self.agents.items():
                    if id != sender_id:
                        receiver_pos = np.array([_robot.pose.position.x, _robot.pose.position.y])
                        distance = np.linalg.norm(sender_pos - receiver_pos)
                        self.get_logger().info(f"distance: {distance}")
                        if distance <= COMMUNICATION_RANGE:
                            _robot.communicate(data)

            else:


                receiver_robot = self.agents[receiver]

                receiver_pos = np.array([receiver_robot.pose.position.x, receiver_robot.pose.position.y])

                distance = np.linalg.norm(sender_pos - receiver_pos)
                self.get_logger().info(f"distance: {distance}")
                if distance <= COMMUNICATION_RANGE:
                    receiver_robot.communicate(data)
        except json.JSONDecodeError:
            self.get_logger().warn("Malformed JSON message")

        # Parse sender and message



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





    def get_cell_center(self,col,row):
        return get_cell_center(self.p1, self.p2, self.p3, self.p4, row, col, self.num_row, self.num_col)
    def find_row_col(self,p_i):
        row,col = find_row_col(p_i, self.p1, self.p2, self.p3, self.p4, self.num_row, self.num_col)
        return col,row

    def gui_init(self):
        # Create buttons
        font = pygame.font.SysFont(None, 36)
        y_button = 20
        width_button = 120
        padding_button = 20
        start_button_x = 50
        pause_button_x = start_button_x + width_button + padding_button
        stop_button_x = pause_button_x + width_button + padding_button

        self.start_button = Button(
            rect=(start_button_x, y_button, width_button, 50),
            text="Start",
            font=font,
            idle_color=(0, 160, 0),
            hover_color=(0, 200, 0),
            press_color=(0, 100, 0)
        )

        self.pause_button = Button(
            rect=(pause_button_x, y_button, width_button, 50),
            text="Pause",
            font=font,
            idle_color=(160, 160, 0),
            hover_color=(200, 200, 0),
            press_color=(100, 100, 0)
        )
        self.pause_button.enabled = False  # initially disabled

        self.stop_button = Button(
            rect=(stop_button_x, y_button, width_button, 50),
            text="Stop",
            font=font,
            idle_color=(160, 0, 0),
            hover_color=(200, 0, 0),
            press_color=(100, 0, 0)
        )
        self.stop_button.enabled = False  # initially disabled

    def draw_buttons(self):
        # Update and draw buttons
        self.start_button.draw(self.screen)
        self.stop_button.draw(self.screen)
        self.pause_button.draw(self.screen)



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


        self.draw_buttons()
        # Update the display
        pygame.display.flip()

    def button_events(self,events):
        self.start_button.update(events)
        self.pause_button.update(events)
        self.stop_button.update(events)

        if self.start_button.clicked:
            self.pause_button.enabled = True
            self.stop_button.enabled = True
            self.start_button.enabled = False
            self.status = "started"
            ros_msg = String()
            ros_msg.data = self.status
            self.agents_control_pub.publish(ros_msg)

        elif self.pause_button.clicked:
            self.status = "paused"
            self.pause_button.enabled = False
            self.start_button.enabled = True
            self.stop_button.enabled = True
            ros_msg = String()
            ros_msg.data = self.status
            self.agents_control_pub.publish(ros_msg)

        elif self.stop_button.clicked:
            self.start_button.enabled = True
            self.pause_button.enabled = False
            self.stop_button.enabled = False
            self.status = "stopped"
            ros_msg = String()
            ros_msg.data = self.status
            self.agents_control_pub.publish(ros_msg)

    def event_handle(self):
        events = pygame.event.get()
        self.button_events(events)
        for event in events:

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

                    if (col,row) in self.swept_cell:
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
