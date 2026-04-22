import socket
import json
import time
import sys
import random
import yaml
from core.critical_check import *

class Agent:
    def __init__(self, agent_id, config, server_host='localhost', server_port=5000):
        print('__init__', agent_id)
        self.agent_id = agent_id
        self.server_address = (server_host, server_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect_to_server()

        # Load agent-specific settings
        self.behavior = next((a.get("behavior", "random_walk") for a in config["agents"] if a["id"] == agent_id),
                             "random_walk")
        print(f"Agent {self.agent_id} initialized with behavior: {self.behavior}")

        # Initialize the local map
        self.local_map = {}
        self.visited_cell = set()
        self.cell_direction = {}
        self.tour_count = 0

    def connect_to_server(self):
        self.socket.connect(self.server_address)
        self.socket.sendall(self.agent_id.encode())
        print(f"Agent {self.agent_id} connected to server.")

    def send_request(self, message):
        self.socket.sendall(json.dumps(message).encode())
        print(f"Agent {self.agent_id} sent message: {message}")

    def receive_response(self):
        response = self.socket.recv(1024).decode()
        if response:
            message = json.loads(response)
            print(f"Agent {self.agent_id} received response: {message}")
            return message
        return None

    def observe(self):
        message = {"sender": self.agent_id, "type": "observe"}
        self.send_request(message)
        response = self.receive_response()

        if response and response.get("status") == "success":
            position = response.get("data", {}).get("position")
            heading = response.get("data", {}).get("heading")
            adjacent_obstacles = response.get("data", {}).get("adjacent_obstacles")
            print(f"Agent {self.agent_id} position: {position}, heading: {heading}")
            print(adjacent_obstacles)

            return position, heading, adjacent_obstacles
        else:
            print(f"Agent {self.agent_id} observe request failed.")
            return None, None, None

    def move(self, direction):
        if direction not in ["up", "down", "left", "right"]:
            print(f"Invalid direction: {direction}")
            return

        message = {"sender": self.agent_id, "type": "move", "direction": direction}
        self.send_request(message)
        response = self.receive_response()

        if response and response.get("status") == "success":
            new_position = response.get("data", {}).get("new_position")
            print(f"Agent {self.agent_id} moved {direction} to {new_position}")
            if new_position:
                self.local_map[tuple(new_position)] = {"swept": False, "obstacle": False}
            return new_position
        else:
            print(f"Agent {self.agent_id} move request failed.")
            return None

    def sweep(self, position):
        message = {"sender": self.agent_id, "type": "sweep"}
        self.send_request(message)
        response = self.receive_response()

        if response and response.get("status") == "success":
            print(f"Agent {self.agent_id} successfully swept the cell.")
            self.local_map[tuple(position)]["swept"] = True
        else:
            print(f"Agent {self.agent_id} sweep request failed.")

    def update_local_map(self, position, adjacent_obstacles):
        if position:
            self.local_map[tuple(position)] = {"swept": False, "obstacle": False}

        for pos_str, is_obstacle in adjacent_obstacles.items():
            try:
                pos = tuple(int(num) for num in pos_str.strip("()").split(","))
                if pos in self.local_map:
                    self.local_map[pos]["obstacle"] = is_obstacle
                else:
                    self.local_map[pos] = {"swept": False, "obstacle": is_obstacle}
            except ValueError:
                print(f"Could not parse position: {pos_str}")

    def greedy_randomwalk(self, position, heading, adjacent_obstacles):
        self.update_local_map(position, adjacent_obstacles)

        directions = {
            "up": (position[0], position[1] - 1),
            "down": (position[0], position[1] + 1),
            "left": (position[0] - 1, position[1]),
            "right": (position[0] + 1, position[1])
        }

        unswept_moves = [
            direction for direction, new_pos in directions.items()
            if new_pos in self.local_map and not self.local_map[new_pos].get("swept", False)
               and not self.local_map[new_pos].get("obstacle", False)
        ]

        if unswept_moves:
            chosen_direction = heading if heading in unswept_moves else random.choice(unswept_moves)
        else:
            chosen_direction = random.choice(list(directions.keys()))

        self.sweep(position)
        self.local_map[tuple(position)]["swept"] = True
        self.move(chosen_direction)

    def spiral_randomwalk(self, position, heading, adjacent_obstacles):
        self.update_local_map(position, adjacent_obstacles)

        directions = {
            "up": (position[0], position[1] - 1),
            "down": (position[0], position[1] + 1),
            "left": (position[0] - 1, position[1]),
            "right": (position[0] + 1, position[1])
        }

        unswept_moves = [
            direction for direction, new_pos in directions.items()
            if new_pos in self.local_map and not self.local_map[new_pos].get("swept", False)
               and not self.local_map[new_pos].get("obstacle", False)
        ]

        rel_dir = ['up', 'left', 'down', 'right']
        heading_index = rel_dir.index(heading)
        chosen_direction = None
        if unswept_moves:
            for idx in range(4):
                candidate_direction = rel_dir[(heading_index - 1 + idx) % 4]
                if candidate_direction in unswept_moves:
                    chosen_direction = candidate_direction
                    break
        if not chosen_direction:
            chosen_direction = random.choice(list(directions.keys()))

        self.move(chosen_direction)
        self.sweep(position)
        self.local_map[tuple(position)]["swept"] = True

    def get_kernel(self, cell_position):
        """
        Generates a 3x3 kernel of boolean values around the specified cell position.
        Each value is True if the cell is unswept and not obstructed, False otherwise.
        """
        x, y = cell_position

        # Define the relative positions for a 3x3 kernel centered on the target cell
        relative_positions = [
            (-1, -1), (0, -1), (1, -1),  # Top row
            (-1, 0), (0, 0), (1, 0),  # Middle row (center cell at (0, 0))
            (-1, 1), (0, 1), (1, 1)  # Bottom row
        ]

        # Initialize the kernel
        kernel = []
        print('get_kernel')
        # Loop over relative positions to determine the state of each adjacent cell
        idx = 0
        critical_key = []
        for dx, dy in relative_positions:

            pos = (x + dx, y + dy)
            print(pos)

            # Check if the position is in the local map and meets the conditions
            if pos in self.local_map:
                cell_data = self.local_map[pos]
                # Set True if unswept and not obstructed; otherwise, set False
                is_unswept_and_unobstructed = not cell_data.get("swept", False) and not cell_data.get("obstacle", False)
            else:
                # If the position is outside the local map, treat it as obstructed
                is_unswept_and_unobstructed = False
            if is_unswept_and_unobstructed:
                critical_key.append(idx)
            idx += 1
            kernel.append(is_unswept_and_unobstructed)

        # Reshape kernel into a 3x3 grid if needed (optional)
        kernel_3x3 = [
            kernel[0:3],  # Top row
            kernel[3:6],  # Middle row
            kernel[6:9]  # Bottom row
        ]

        return kernel_3x3,tuple(critical_key)


    def ant_sweep(self, position, heading, adjacent_obstacles):
        #single Wagner Ant
        self.update_local_map(position, adjacent_obstacles)
        kernel,ckey = self.get_kernel(position)
        print('=====Kernal=====')
        print(kernel[0])
        print(kernel[1])
        print(kernel[2])
        print(ckey)
        print(critical_check(ckey))
        directions = {
            "up": (position[0], position[1] - 1),
            "down": (position[0], position[1] + 1),
            "left": (position[0] - 1, position[1]),
            "right": (position[0] + 1, position[1])
        }

        unswept_moves = [
            direction for direction, new_pos in directions.items()
            if new_pos in self.local_map and not self.local_map[new_pos].get("swept", False)
               and not self.local_map[new_pos].get("obstacle", False)
        ]

        rel_dir = ['up', 'left', 'down', 'right']
        heading_index = rel_dir.index(heading)
        chosen_direction = None
        if unswept_moves:
            for idx in range(4):
                candidate_direction = rel_dir[(heading_index - 1 + idx) % 4]
                if candidate_direction in unswept_moves:
                    chosen_direction = candidate_direction
                    break
        else:
            chosen_direction = None

        if critical_check(ckey) == 'not_critical':
            self.sweep(position)
            self.local_map[tuple(position)]["swept"] = True
            # For Wagner ant
            self.visited_cell = set()
            self.tour_count = 0
        else:
            if tuple(position) not in self.cell_direction: #New cell found
                self.cell_direction[tuple(position)] = set()
                #self.tour_count = 0 #### Why??????

            self.cell_direction[tuple(position)].add(heading)

            if tuple(position) in self.visited_cell:
                self.tour_count += 1
                self.visited_cell = set()
            self.visited_cell.add(tuple(position))

            if self.tour_count >= 2 :
                if len(self.cell_direction[tuple(position)]) == 1 and len(unswept_moves) < 3:
                    #print(self.cell_direction[tuple(position)])
                    #print('tour count:', self.tour_count, self.cell_direction[tuple(position)])
                    #print(len(unswept_moves))
                    #time.sleep(2)
                    self.sweep(position)
                    self.visited_cell = set()
                    self.tour_count = 0

        if chosen_direction:
            self.move(chosen_direction)
    def update_behavior(self):
        position, heading, adjacent_obstacles = self.observe()

        if position and heading:
            if self.behavior == "random_walk":
                self.greedy_randomwalk(position, heading, adjacent_obstacles)
            elif self.behavior == "ANT_SWEEP":
                self.ant_sweep(position, heading, adjacent_obstacles)


# Main code to execute the agent, reading agent_id from command-line arguments
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_agent.py <agent_id>")
        sys.exit(1)

    agent_id = sys.argv[1]

    with open("../config_.yaml", "r") as file:
        config = yaml.safe_load(file)

    agent = Agent(agent_id=agent_id, config=config)

    while True:
        agent.update_behavior()
        time.sleep(0.1)
