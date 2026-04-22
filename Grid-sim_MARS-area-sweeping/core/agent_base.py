import socket
import selectors
import json

import struct

from agent_lib.wagner_ant import AntSweep  # Import the AntSweep algorithm
from agent_lib.wagner_ant_filter import AntFilterSweep
from agent_lib.wagner_ant_recall_filter import AntRecallFilterSweep
from agent_lib.gs_reactive_agent import GreedySpiralRandomwalk
from agent_lib.gsr_recall_agent import GreedySpiralRandomwalkRecall
from agent_lib.wagner_henrish_ant_recall_filter import WagnerHenrishAntRecallFilterSweep

SOP = b'\x02\x03'

class Agent:
    def __init__(self, agent_id, config, server_host='localhost', server_port=5000, max_step=-1):
        print('__init__', agent_id)
        self.agent_id = agent_id
        self.max_step = max_step
        self.server_address = (server_host, server_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect_to_server()

        # Load agent-specific settings
        self.behavior = config["agents"].get("behavior", None)
        agent_id_prefix = config["agents"].get("id_prefix", "agent_")
        number_of_agents = config["agents"].get("number_of_agents", 1)
        agent_id_list = [f"{agent_id_prefix}{agent_idx}" for agent_idx in range(number_of_agents)]
        color_list = config["agents"].get("color_list", ["#0000FF"])
        print(agent_id_list)
        idx = agent_id_list.index(agent_id)
        self.agent_color = color_list[idx % len(color_list)]
        if agent_id in agent_id_list:
            idx = agent_id_list.index(agent_id)

        print(f"Agent {self.agent_id} initialized with behavior: {self.behavior}")

        # Initialize the local map
        self.local_map = {}

        # for logging and analysing
        self.sweeping_count = 0
        self.moving_count = 0
        self.done_state = False

        # Initialize the behavior-specific algorithm if applicable
        if self.behavior == "ANT_SWEEP":
            self.sweep_algorithm = AntSweep(self)  # Initialize the AntSweep algorithm
        elif self.behavior == "ANT_FILTER_SWEEP":
            self.sweep_algorithm = AntFilterSweep(self)  # Initialize the AntSweep algorithm
        elif self.behavior == "ANT_RECALL_FILTER_SWEEP":
            self.sweep_algorithm = AntRecallFilterSweep(self)  # Initialize the AntSweep algorithm
        elif self.behavior == "GSR_SWEEP":
            self.sweep_algorithm = GreedySpiralRandomwalk(self)  # Initialize the AntSweep algorithm
        elif self.behavior == "GSR_SWEEP_RECALL":
            self.sweep_algorithm = GreedySpiralRandomwalkRecall(self)  # Initialize the AntSweep algorithm
        elif self.behavior == "WH_ANT_RECALL_FILTER_SWEEP":
            self.sweep_algorithm = WagnerHenrishAntRecallFilterSweep(self)  # Initialize the AntSweep algorithm
        else:
            self.sweep_algorithm = None  # No special algorithm for random_walk

    def connect_to_server(self):
        self.socket.connect(self.server_address)
        message = {"sender": self.agent_id, "type": "connect_request"}
        self.send_request(message)  # Send connect_request only once
        print(f"Agent: {self.agent_id} connected to server.")

        response = self.receive_response()  # Wait for server response
        if response and response.get("status") == "success":
            print(f"Agent: {self.agent_id} successfully connected to the server.")
        else:
            print(f"Agent: {self.agent_id} failed to connect to the server.")

    def send_request(self, message):
        """
        Send a structured packet with SOP, length, and payload for the request.
        """
        # Convert message dictionary to JSON string and then encode it
        payload = json.dumps(message).encode('utf-8')
        length = len(payload)

        # Construct the packet: SOP (2 bytes) + Length (4 bytes) + Payload
        packet = SOP + struct.pack('!I', length) + payload
        self.socket.sendall(packet)

    def receive_response(self):
        """
        Receive a structured packet by reading SOP, length, and payload.
        """
        # Read SOP
        sop = self.socket.recv(2)
        if sop != SOP:
            print("Invalid SOP. Packet discarded.")
            return None

        # Read length header (4 bytes)
        length_data = self.socket.recv(4)
        if len(length_data) < 4:
            print("Incomplete length header. Packet discarded.")
            return None
        length = struct.unpack('!I', length_data)[0]

        # Read the payload based on the length
        payload_data = self.socket.recv(length)
        while len(payload_data) < length:
            payload_data += self.socket.recv(length - len(payload_data))

        # Decode the payload as JSON
        try:
            payload = payload_data.decode('utf-8')
            message = json.loads(payload)
            return message
        except json.JSONDecodeError:
            print("Failed to decode JSON payload.")
            return None

    def observe(self):
        message = {"sender": self.agent_id, "type": "observe"}
        self.send_request(message)
        response = self.receive_response()

        if response and response.get("status") != "success":
            print(f"Agent {self.agent_id} observe request failed.")
            print('Agent', response)

        return response.get('data', {})

    def move(self, direction):
        if direction not in ["up", "down", "left", "right"]:
            #print(f"Invalid direction: {direction}")
            return
        self.moving_count += 1

        message = {"sender": self.agent_id, "type": "move", "direction": direction}
        self.send_request(message)
        response = self.receive_response()

        if response and response.get("status") == "success":
            new_position = response.get("data", {}).get("new_position")
            #print(f"Agent {self.agent_id} moved {direction} to {new_position}")
            # Bug
            #if new_position:
            #    self.local_map[tuple(new_position)] = {"swept": False, "obstacle": False}
            return new_position
        else:
            #print(f"Agent {self.agent_id} move request failed.")
            return None

    def update_agent_status(self, status):
        message = {"sender": self.agent_id, "type": "update_status", "agent_status": status}
        self.send_request(message)

    def sweep(self, position, color=None):

        if not color:
            color = self.agent_color
        self.sweeping_count += 1

        message = {"sender": self.agent_id, "type": "sweep", "color": color}
        self.send_request(message)
        response = self.receive_response()
        #print('response from server',response)

        if response and response.get("status") == "success":
            #print(f"Agent {self.agent_id} successfully swept the cell.")
            self.local_map[tuple(position)]["swept"] = True
        else:

            print(f"Agent {self.agent_id} sweep request failed.")

    def communicate(self, target_id, data):
        """
        Sends a communication message to another agent through the environment.
        """
        message = {
            "sender": self.agent_id,
            "type": "communicate",
            "receiver": target_id,
            "data": data
        }
        self.send_request(message)
        success_flag = False
        response = self.receive_response()

        if response and response.get("status") == "success":
            success_flag = True
            #print(f"Agent {self.agent_id} successfully sent message to {target_id}")
        else:
            pass
            #print(f"Agent {self.agent_id} communication to {target_id} failed")
        return success_flag

    def update_local_map_sweep(self, position, color):
        if tuple(position) not in self.local_map:
            self.local_map[tuple(position)] = {"swept": True, "obstacle": False}
        else:
            self.local_map[tuple(position)]["swept"]= True
        message = {"sender": self.agent_id, "type": "subjective_map","position":position, "swept": True,"color": color}
        self.send_request(message)
        response = self.receive_response()
        # print('response from server',response)

        if response and response.get("status") == "success":
            # print(f"Agent {self.agent_id} successfully swept the cell.")
            pass

        else:

            print(f"Agent {self.agent_id} sweep request failed.")

    def update_local_map_obstacle(self, position, adjacent_obstacles):

        if tuple(position) not in self.local_map:

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

    def update_behavior(self):

        observation = self.observe()
        waiting = False
        stop = False

        if self.behavior == "GSR_SWEEP":
            #self.greedy_spiral_randomwalk(observation)
            waiting, stop = self.sweep_algorithm.perform_sweep(observation)
        elif self.behavior == "GSR_SWEEP_RECALL" and self.sweep_algorithm:
            waiting, stop = self.sweep_algorithm.perform_sweep(observation)
        elif self.behavior == "ANT_SWEEP" and self.sweep_algorithm:
            waiting, stop = self.sweep_algorithm.perform_sweep(observation)
        elif self.behavior == "ANT_FILTER_SWEEP" and self.sweep_algorithm:
            waiting, stop = self.sweep_algorithm.perform_sweep(observation)
        elif self.behavior == "ANT_RECALL_FILTER_SWEEP" and self.sweep_algorithm:
            waiting, stop = self.sweep_algorithm.perform_sweep(observation)
        elif self.behavior == "WH_ANT_RECALL_FILTER_SWEEP" and self.sweep_algorithm:
            waiting, stop = self.sweep_algorithm.perform_sweep(observation)


        return waiting, stop