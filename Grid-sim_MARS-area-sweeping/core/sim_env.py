import socket
import time

import select
import json
import struct
import random
import math

SOP = b'\x02\x03'


class SimEnvironment:
    def __init__(self, config, par_idx=0):
        self.host = config.get("communication", {}).get("host", "localhost")
        self.port = config.get("communication", {}).get("server_port", [5000])[par_idx]

        self.grid_dimensions = (config["grid"]["rows"], config["grid"]["cols"])

        # Initialize grid, agent states, and mailboxes
        self.grid = {
            "obstacles": config["grid"].get("obstacles", []),
            "dimensions": self.grid_dimensions,
            "swept_cells": {}
        }
        self.total_cells = self.grid_dimensions[0] * self.grid_dimensions[1]
        self.task_cells = self.total_cells - len(self.grid["obstacles"])
        self.config = config
        self.agent_configs = config["agents"]
        self.agents_state = {}
        self.mailboxes = {}  # Mailbox for each agent

        # Initialize server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"SimEnvironment server listening on {self.host}:{self.port}")

        self.clients = {}
        self.agents_statistic = {}
        self.agent_subjective_grid = {}
        self.sweeping_progress = {}
        self.simulation_status = 'run'


    def run(self):
        while True:
            # Monitor the server socket and all client sockets
            read_sockets, _, _ = select.select([self.server_socket] + list(self.clients.values()), [], [])

            for sock in read_sockets:
                if sock == self.server_socket:
                    # Handle new connection
                    conn, addr = self.server_socket.accept()
                    print(f"SimEnvironment: New connection from {addr}")

                    # Receive the initial message to get the agent_id
                    initial_message = self.receive_response(conn)
                    if not initial_message or "sender" not in initial_message:
                        print("Invalid initial message. Closing connection.")
                        conn.close()
                        continue

                    agent_id = initial_message["sender"]
                    print(f"SimEnvironment: Agent {agent_id} connected.")

                    # Add the new client and initialize its state
                    self.clients[agent_id] = conn
                    self.mailboxes[agent_id] = []  # Initialize mailbox
                    self.initialize_agent(agent_id)

                    # Send a success response back to the agent
                    response = {"status": "success"}
                    self.send_request(conn, response)
                    number_of_agents = self.agent_configs.get("number_of_agents", 1)
                    if len(self.clients) == number_of_agents:
                        self.start_time = time.time()
                        print(f"all agent initialized at {self.start_time}")

                else:
                    # Handle messages from existing clients
                    try:
                        message = self.receive_response(sock)
                        if message:
                            # Find the agent_id associated with this socket
                            agent_id = next((k for k, v in self.clients.items() if v == sock), None)
                            if agent_id:
                                #print(f"SimEnvironment: Received message from {agent_id}: {message}")
                                response = self.process_message(agent_id, message)
                                self.send_request(sock, response)
                        else:
                            pass
                            #print('sim_env,run error')
                    except (ConnectionResetError, json.JSONDecodeError):
                        # Handle client disconnection
                        agent_id = next((k for k, v in self.clients.items() if v == sock), None)
                        if agent_id:
                            print(f"SimEnvironment: Agent {agent_id} disconnected.")
                            sock.close()
                            del self.clients[agent_id]
                            #del self.agents_state[agent_id]
                            #del self.mailboxes[agent_id]

    def handle_connect_request(self, agent_id):

        conn, addr = self.server_socket.accept()

        agent_id = self.receive_response(conn).get("sender")  # Receive agent_id as initial message
        self.clients[agent_id] = conn
        self.mailboxes[agent_id] = []  # Initialize mailbox
        self.initialize_agent(agent_id)
        print(f"EnvServer:Agent {agent_id} connected from {addr} massage: {self.receive_response(conn)}")
        response = self.process_message(agent_id, {"status": "success"})
        self.send_request(conn, response)

    def initialize_agent(self, agent_id):

        number_of_agents = self.agent_configs.get("number_of_agents", 1)
        agent_id_prefix = self.agent_configs.get("id_prefix", "agent_")
        agent_id_list = [f"{agent_id_prefix}{agent_idx}" for agent_idx in range(number_of_agents)]
        if agent_id in agent_id_list:
            idx = agent_id_list.index(agent_id)
            print(agent_id)
            self.agents_statistic[agent_id] = {}
            self.agents_statistic[agent_id]['move_count'] = 0
            self.agents_statistic[agent_id]['swept_count'] = 0
            position = self.get_random_position()
            heading = random.choice(["up", "down", "left", "right"])
            communication_range = self.agent_configs.get("communication_range",
                                                         -1)  # Default range is 1 if not specified
            color_list = self.agent_configs.get("color_list", ["#0000FF"])
            self.agents_state[agent_id] = {
                "position": position,
                "heading": heading,
                "color": color_list[idx % len(color_list)],
                "communication_range": communication_range,
                "status": 'Operating'
            }

            self.mailboxes[agent_id] = []  # Ensure mailbox is initialized

            self.agent_subjective_grid[agent_id]= {
                "obstacles": self.config["grid"].get("obstacles", []),
                "dimensions": self.grid_dimensions,
                "swept_cells": {}
            }
            return
        #self.agents_state[agent_id] = {"position": (0, 0), "heading": "up", "color": "#0000FF", "communication_range": 1}

    def update_status(self, agent_id, agent_status):
        self.agents_state[agent_id]["status"] = agent_status

    def get_random_position(self):
        """Generates a random, unoccupied position within grid bounds."""
        grid_rows, grid_cols = self.grid_dimensions
        obstacles = {tuple(ob["position"]) for ob in self.grid["obstacles"]}

        while True:
            position = (random.randint(0, grid_rows - 1), random.randint(0, grid_cols - 1))
            if position not in obstacles and all(agent["position"] != position for agent in self.agents_state.values()):
                return position

    def process_message(self, agent_id, message):

        if message.get("type") == "move":
            direction = message.get("direction")
            self.agents_statistic[agent_id]['move_count'] += 1
            return self.handle_move(agent_id, direction)
        elif message.get("type") == "observe":
            return self.handle_observe(agent_id)
        elif message.get("type") == "sweep":
            self.agents_statistic[agent_id]['swept_count'] += 1
            return self.handle_sweep(agent_id,message)
        elif message.get("type") == "subjective_map":
            return self.handle_subjective_map_update(agent_id, message)
        elif message.get("type") == "communicate":
            target_id = message.get("receiver")
            data = message.get("data")
            return self.handle_communication(agent_id, target_id, data)
        elif message.get("type") == "retrieve_messages":
            return self.retrieve_messages(agent_id)
        elif message.get("type") == "update_status":
            agent_status = message.get("agent_status")
            return self.update_status(agent_id, agent_status)

        else:
            print(f'SimEvn: process_message eroor from unknown type "{message.get("type")}"')
            return {"status": "error", "reason": f'unknown command of {message.get("type")}'}

    def handle_communication(self, agent_id, target_id, data):
        message = {
            "sender": agent_id,
            "type": "communication",
            "data": data
        }

        sender_position = self.agents_state[agent_id]["position"]
        sender_range = self.agents_state[agent_id]["communication_range"]

        if target_id == "broadcast":
            for other_id, other_state in self.agents_state.items():
                if other_id != agent_id:
                    distance = self.calculate_distance(sender_position, other_state["position"])
                    if distance <= sender_range:
                        self.mailboxes[other_id].append(message)
            #print(f"Broadcasted message from {agent_id} within range.")
            return {"status": "success", "type": "broadcast"}
        elif target_id in self.mailboxes:
            target_position = self.agents_state[target_id]["position"]
            if self.calculate_distance(sender_position, target_position) <= sender_range:
                self.mailboxes[target_id].append(message)
                #print(f"Forwarded message from {agent_id} to {target_id}.")
                return {"status": "success", "type": "direct"}
            else:
                #print(f"Failed to send message from {agent_id} to {target_id}: Out of range of {sender_range}.")
                return {"status": "error", "reason": "target agent out of range"}
        else:
            print(f"Failed to send message from {agent_id} to {target_id}: Target not connected.")
            return {"status": "error", "reason": "target agent not connected"}

    def calculate_distance(self, pos1, pos2):
        return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)

    def retrieve_messages(self, agent_id):
        if agent_id in self.mailboxes:
            messages = self.mailboxes[agent_id]
            self.mailboxes[agent_id] = []  # Clear mailbox after retrieval
            #print(f"Agent {agent_id} retrieved messages: {messages}")
            return {"status": "success", "messages": messages}
        else:
            #print(f"Agent {agent_id} has no mailbox.")
            return {"status": "error", "reason": "mailbox not found"}

    def handle_sweep(self, agent_id,message):
        agent_position = self.agents_state[agent_id]["position"]
        agent_color = self.agents_state[agent_id]["color"]

        self.agent_subjective_grid[agent_id]['swept_cells'][agent_position] = agent_color

        if agent_position not in self.grid["swept_cells"]:
            self.grid["swept_cells"][agent_position] = agent_color
            move = max([int(agent_stat['move_count']) for agent_stat in self.agents_statistic.values()])
            self.sweeping_progress[len(self.grid["swept_cells"])] = move

        #print(f"Cell {agent_position} swept by {agent_id} with color {agent_color}")
        return {"status": "success"}
    def handle_subjective_map_update(self, agent_id,message):
        sweep_color = message["color"]
        sweep_pos = tuple(message['position'])
        self.agent_subjective_grid[agent_id]['swept_cells'][sweep_pos] = sweep_color

        # print(f"Cell {agent_position} swept by {agent_id} with color {agent_color}")
        return {"status": "success"}
    def handle_observe(self, agent_id):

        agent_state = self.agents_state.get(agent_id)
        if agent_state:
            position = agent_state["position"]
            heading = agent_state["heading"]

            # Adjust observation range by increasing offsets
            observation_range = 2  # Extend to two cells in each direction
            adjacent_positions = [
                (position[0] + dx, position[1] + dy)
                for dx in range(-observation_range, observation_range + 1)
                for dy in range(-observation_range, observation_range + 1)
                if not (dx == 0 and dy == 0)  # Exclude the agent's own position
            ]

            # Determine obstacle state for each observed cell
            obstacles = {tuple(ob["position"]) for ob in self.grid["obstacles"]}
            grid_rows, grid_cols = self.grid_dimensions
            adjacent_obstacles = {
                str(pos): (pos in obstacles) if 0 <= pos[0] < grid_rows and 0 <= pos[1] < grid_cols else True
                for pos in adjacent_positions
            }

            # Retrieve and clear mailbox messages for the agent
            mailbox_messages = self.mailboxes.get(agent_id, [])
            self.mailboxes[agent_id] = []  # Clear mailbox after retrieval

            # Include mailbox messages in the observation response
            return {
                "status": "success",

                "data": {
                    "position": position,
                    "heading": heading,
                    "adjacent_obstacles": adjacent_obstacles,
                    "messages": mailbox_messages,  # Add messages to the response
                    "simulation_status": self.simulation_status  # external signal to stop agent
                }
            }
        return {"status": "error", "reason": "agent not found"}

    def handle_move(self, agent_id, direction):
        if direction not in ["up", "down", "left", "right"]:
            return {"status": "error", "reason": "invalid direction"}
        current_position = self.agents_state[agent_id]["position"]
        new_position = self.calculate_new_position(current_position, direction)
        if (0 <= new_position[0] < self.grid_dimensions[0] and
                0 <= new_position[1] < self.grid_dimensions[1] and
                new_position not in [tuple(ob["position"]) for ob in self.grid["obstacles"]]):
            self.agents_state[agent_id]["position"] = new_position
            self.agents_state[agent_id]["heading"] = direction
            return {"status": "success", "data": {"new_position": new_position}}
        return {"status": "error", "reason": "move out of bounds or into obstacle"}

    def calculate_new_position(self, current_position, direction):
        x, y = current_position
        if direction == "up":
            return (x, y - 1)
        elif direction == "down":
            return (x, y + 1)
        elif direction == "left":
            return (x - 1, y)
        elif direction == "right":
            return (x + 1, y)

    def send_request(self, sock, message):
        payload = json.dumps(message).encode('utf-8')
        length = len(payload)
        packet = SOP + struct.pack('!I', length) + payload
        sock.sendall(packet)

    def receive_response(self, sock):
        try:
            sop = sock.recv(2)
        except Exception as e:
            print('Error at sim_env,receive_response,sop = sock.recv(2)', sock, e)
            sock.close()
            self.clients = {k: v for k, v in self.clients.items() if v != sock}
            return None
        if sop != SOP:
            #print("Invalid SOP. Packet discarded.")
            return None

        length_data = sock.recv(4)
        if len(length_data) < 4:
            print("Incomplete length header. Packet discarded.")
            return None
        length = struct.unpack('!I', length_data)[0]

        payload_data = sock.recv(length)
        while len(payload_data) < length:
            payload_data += sock.recv(length - len(payload_data))

        try:
            payload = payload_data.decode('utf-8')
            message = json.loads(payload)
            #print('==========receive_response==========')
            #print(payload)
            return message
        except json.JSONDecodeError:
            print("Failed to decode JSON payload.")
            return None
