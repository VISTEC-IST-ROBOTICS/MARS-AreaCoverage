
from lib.pg_draw import *
import sys
from robot_agent import RobotAgent
from MALC_agent import SweepingAgent, get_mega_cell, AgentState
import random
import numpy as np
import time
import queue
import networkx as nx
import yaml


seed = int(time.time())
#seed = 1750858733
random.seed(seed)
print("Seed used:", seed)
import logging
logging.basicConfig(
    filename='MEGA-ANT_limcomm.log',
    level=logging.INFO,  # Set the minimum level
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logging.info(f'Seed used: {seed}')



NUM_ROBOT  = 16
ROWS = 30
COLS = 30
CELL_SIZE = 20
COMMUNICATION_RANGE = CELL_SIZE * 6
#COMMUNICATION_RANGE = CELL_SIZE * 100
WIDTH = COLS * CELL_SIZE
HEIGHT = ROWS * CELL_SIZE

pygame.display.set_caption("2D Grid Robot Navigation")
clock = pygame.time.Clock()

# === GLOBAL STATE for view switching ===
view_mode = 'GLOBAL'
selected_agent_idx = 0
view_idx = 0

class Environment:
    def __init__(self, ROWS, COLS, CELL_SIZE):
        self.ROWS = ROWS
        self.COLS = COLS
        self.CELL_SIZE = CELL_SIZE
        self.WIDTH = COLS * CELL_SIZE
        self.HEIGHT = ROWS * CELL_SIZE

        self.swept_cell = {}
        self.obstruct_cells = []
        self.robot_dict = {}
        self.communication_queue = queue.Queue()
        pygame_init(COLS, ROWS, CELL_SIZE)

    def sweep(self, cell, color=(200, 200, 200)):
        if cell not in self.swept_cell:
            self.swept_cell[cell] = {'color': color}

    def cell_observation(self, cells):
        res = []
        for cell in cells:
            if cell in self.obstruct_cells or cell[0] < 0 or cell[0] >= COLS or cell[1] < 0 or cell[1] >= ROWS:
                res.append(1)
            else:
                res.append(0)
        return res

    def neighbor_observation(self, agent_id):
        sender_robot = self.robot_dict[agent_id]
        sender_pos = np.array([sender_robot.x, sender_robot.y])
        neighbors = []
        for id, _robot in self.robot_dict.items():
            if id != agent_id:
                receiver_pos = np.array([_robot.x, _robot.y])
                distance = np.linalg.norm(sender_pos - receiver_pos)
                if distance <= CELL_SIZE * 5:
                    neighbors.append(id)

        return neighbors

    def communication(self, msg):
        receiver = msg['receiver']
        sender = msg['sender']

        if receiver == 'BROADCAST':
            sender_robot = self.robot_dict[sender]
            sender_pos = np.array([sender_robot.x, sender_robot.y])

            for id, _robot in self.robot_dict.items():
                if id != sender:
                    receiver_pos = np.array([_robot.x, _robot.y])
                    distance = np.linalg.norm(sender_pos - receiver_pos)
                    if distance <= COMMUNICATION_RANGE:

                        _robot.mailbox.put(msg)

        else:
            sender_robot = self.robot_dict[sender]
            sender_pos = np.array([sender_robot.x, sender_robot.y])

            receiver_robot = self.robot_dict[receiver]

            receiver_pos = np.array([receiver_robot.x, receiver_robot.y])



            distance = np.linalg.norm(sender_pos - receiver_pos)
            if distance <= COMMUNICATION_RANGE:
                receiver_robot.mailbox.put(msg)

    def spawn_robot(self, id, start_cell, heading, color):
        start_col, start_row = start_cell
        new_robot = RobotAgent(id, start_col=start_col, start_row=start_row, heading=heading, cell_size=self.CELL_SIZE,
                               observation_func=self.cell_observation, neighbor_observation_func=self.neighbor_observation,
                               comm_func=self.communication, sweep_func=self.sweep, color=color)
        self.robot_dict[id] = new_robot


# load config
def load_grid_config(self, config_path):
    try:
        with open(config_path, 'r') as f:
            self.grid_config = yaml.safe_load(f)
        self.get_logger().info(f"Loaded grid config from: {config_path}")
    except Exception as e:
        self.get_logger().error(f"Failed to load grid config: {e}")
        self.grid_config = None

    grid_corners = self.grid_config.get('grid_corners', {})
    self.p1 = np.array(grid_corners.get('p1', [0, 0]))
    self.p2 = np.array(grid_corners.get('p2', [0, 0]))
    self.p3 = np.array(grid_corners.get('p3', [0, 0]))
    self.p4 = np.array(grid_corners.get('p4', [0, 0]))

    self.get_logger().info(f"Grid Corners Loaded:")
    self.get_logger().info(f"P1: {self.p1}")
    self.get_logger().info(f"P2: {self.p2}")
    self.get_logger().info(f"P3: {self.p3}")
    self.get_logger().info(f"P4: {self.p4}")

    # Find the bounding box for scaling
    self.grid_corners = [self.p1, self.p2, self.p3, self.p4]
    self.min_x = min(corner[0] for corner in self.grid_corners)
    self.max_x = max(corner[0] for corner in self.grid_corners)
    self.min_y = min(corner[1] for corner in self.grid_corners)
    self.max_y = max(corner[1] for corner in self.grid_corners)
    #
    self.num_row = self.grid_config.get('num_row', 0)
    self.num_col = self.grid_config.get('num_col', 0)
    info = pygame.display.Info()
    SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h
    scale_x = 0.8*SCREEN_WIDTH / (self.max_x - self.min_x)
    scale_y = 0.8*SCREEN_HEIGHT / (self.max_y - self.min_y)
    self.scale = min(scale_x,scale_y)

    # Find the center of the grid for panning
    self.center_x = (self.min_x + self.max_x) / 2
    self.center_y = (self.min_y + self.max_y) / 2

# === SETUP ENVIRONMENT ===
environment = Environment(ROWS, COLS, CELL_SIZE)

mega_rows = ROWS // 2
mega_cols = COLS // 2
available_mega_cell = [(col, row) for row in range(mega_rows) for col in range(mega_cols)]

for idx in range(NUM_ROBOT):
    if available_mega_cell:
        chosen_mega_cell = random.choice(available_mega_cell)
        available_mega_cell.remove(chosen_mega_cell)
        subcell_pos = np.array([(0, 0), (0, 1), (1, 0), (1, 1)])
        abs_subcell_pos = subcell_pos + np.array(chosen_mega_cell) * 2
        start_cells = random.choice(abs_subcell_pos)
        color = list(robot_colors.keys())[idx % len(list(robot_colors.keys()))]
        heading = 0
        environment.spawn_robot(f'robot_{idx}', start_cells, heading, color)


#sweepingAgent_list = [SweepingAgent(environment.robot_dict[f'robot_{i}']) for i in range(NUM_ROBOT)]
sweepingAgent_dict = {
    robot_id: SweepingAgent(robot)
    for robot_id, robot in environment.robot_dict.items()
}


sim_start = False

def display_agent_state():
    # Initialize directed graph
    G = nx.DiGraph()

    print("=== Agent States ===")
    for robot_id, agent in sweepingAgent_dict.items():
        pos = get_mega_cell(agent.robot)
        print(robot_id, agent.robot.color, agent.state, pos)

        if agent.state ==AgentState.SWAP_POSITION:
            swap_agent = agent.position_swap_agent
            color = environment.robot_dict[swap_agent].color
            print("↪ swapping with:", swap_agent, color)

        elif agent.state == AgentState.STOP:
            print("↪ stop cause:", agent.stop_cause)

        elif agent.state == AgentState.WAITING:
            print("↪ waiting for:", agent.waiting_list)

        elif agent.state == AgentState.BLOCKED:
            print("↪ blocked by:", agent.blocking_agent_list)
            for blocker in agent.blocking_agent_list:
                G.add_edge(robot_id, blocker)

    print("\n=== Dependency Graph ===")
    for u, v in G.edges():
        print(f"{u} → {v}")

    # Attempt cycle detection
    try:
        cycle = nx.find_cycle(G, orientation='original')
        print("\n🚨 Dependency cycle detected:")
        for edge in cycle:
            print(f"{edge[0]} → {edge[1]}")
    except nx.exception.NetworkXNoCycle:
        print("\n✅ No dependency cycles detected.")


for robot_id, agent in sweepingAgent_dict.items():
    agent.check_mailbox_thread.start()
    agent.update_thread.start()

# === MAIN LOOP ===
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print("Seed used:", seed)
            for robot_id, agent in sweepingAgent_dict.items():
                agent.run_flag = False
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                sim_start = not sim_start
                for robot_id, agent in sweepingAgent_dict.items():
                    agent.run_flag = sim_start
                if not sim_start:
                    display_agent_state()


                print(f'sim_start = {sim_start}')
            elif event.key == pygame.K_v:
                view_mode = 'AGENT' if view_mode == 'GLOBAL' else 'GLOBAL'
                print(f"Switched to {view_mode} view")
            elif event.key == pygame.K_RIGHT:
                selected_agent_idx = (selected_agent_idx + 1) % NUM_ROBOT
                print(f"Selected agent: {selected_agent_idx}")
            elif event.key == pygame.K_LEFT:
                selected_agent_idx = (selected_agent_idx - 1) % NUM_ROBOT
                print(f"Selected agent: {selected_agent_idx}")

    if sim_start:
        all_stop = True
        for robot_id, agent in sweepingAgent_dict.items():
            #agent.update()
            if agent.state != 'STOP':
                all_stop = False
        if all_stop:
            print('all agent have stopped')

        for robot_id_1, agent_1 in sweepingAgent_dict.items():
            for robot_id_2, agent_2 in sweepingAgent_dict.items():
                if agent_1 == agent_2:
                    continue
                agent_1_pos = get_mega_cell(agent_1.robot)
                agent_2_pos = get_mega_cell(agent_2.robot)
                if agent_1_pos == agent_2_pos:
                    if agent_1.position_swap_flag and agent_2.position_swap_flag:
                        continue
                    sim_start = False

                    for robot_id, agent in sweepingAgent_dict.items():
                        agent.run_flag = sim_start
                    print(f'Error: two agents ({agent_1.robot.id,agent_2.robot.id})occupied the same cell at {agent_1_pos}')

                    break
            if not sim_start:
                break
    #print('view_idx',view_idx)
    idx += 1
    if idx >= 10:
        idx = 0
    else:
        continue

    if view_idx >= NUM_ROBOT:
        view_idx = 0
    if view_mode == 'GLOBAL':
        draw_grid(environment.swept_cell, environment.obstruct_cells, COLS, ROWS, CELL_SIZE)
    else:
        agent_keys = list(sweepingAgent_dict.keys())  # ordered list of keys
        agent = sweepingAgent_dict[agent_keys[selected_agent_idx]]

        subjective_swept = {}
        for mega_cell in agent.swept_mega_cell:
            mc_col, mc_row = mega_cell
            for dx in range(2):
                for dy in range(2):
                    cell = (mc_col * 2 + dx, mc_row * 2 + dy)
                    subjective_swept[cell] = {'color': (100, 100, 255)}
        draw_subjective_grid(subjective_swept, environment.obstruct_cells, COLS, ROWS, CELL_SIZE,agent.robot.color)


    for id, robot in environment.robot_dict.items():
        pos = robot.get_position()
        angle = robot.get_yaw()
        draw_triangle_agent(pos[0], pos[1], angle, color=robot.color, CELL_SIZE=CELL_SIZE)

    for id1, robot1 in environment.robot_dict.items():
        for id2, robot2 in environment.robot_dict.items():
            if id1 != id2:
                pos1 = robot1.get_position()
                pos2 = robot2.get_position()
                distance = np.linalg.norm(np.array(pos1) - np.array(pos2))
                if distance <= COMMUNICATION_RANGE:
                    draw_communication_line(pos1, pos2)

    draw_mouse_cursor(CELL_SIZE=CELL_SIZE * 2)
    pygame.display.flip()

    clock.tick(1000)

