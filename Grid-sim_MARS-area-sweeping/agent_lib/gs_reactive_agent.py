import random






class GreedySpiralRandomwalk:
    def __init__(self, agent):
        """
        Initialize AntSweep with a reference to the agent instance.
        """
        self.agent = agent
        self.visited_cells = set()
        self.cell_directions = {}
        self.tour_count = 0
        self.delay_flag = False
        self.agent_occupied_flag = False
        self.leave_occupied_cell_dependency = []
        self.neighbor_agent_by_dir = {
            "up": [],
            "down": [],
            "left": [],
            "right": []
        }
        self.neighbor_agent = {}
        self.neighbor_critical_sweep_flag = False

    def handle_communication(self,message,observation):


        data = message.get('data',{})
        if 'swept_position' in data:
            swept_position = tuple(data.get('swept_position'))
            if tuple(swept_position) in self.agent.local_map:
                is_pos_swept = self.agent.local_map[tuple(swept_position)].get("swept", False)
                if not is_pos_swept:
                    self.agent.update_local_map_sweep(swept_position,'grey')
            else:
                self.agent.update_local_map_sweep(swept_position, 'grey')


    def perform_sweep(self, observation):
        position = observation.get("position")

        heading = observation.get("heading")
        adjacent_obstacles = observation.get("adjacent_obstacles")
        simulation_status = observation.get("simulation_status")
        stop_flag = False
        messages = observation.get("messages", [])  # Default to empty list if no messages

        for message in messages:
            self.handle_communication(message,observation)

        self.agent.update_local_map_obstacle(position, adjacent_obstacles)



        directions = {
            "up": (position[0], position[1] - 1),
            "down": (position[0], position[1] + 1),
            "left": (position[0] - 1, position[1]),
            "right": (position[0] + 1, position[1])
        }

        unswept_moves = [
            direction for direction, new_pos in directions.items()
            if new_pos in self.agent.local_map and not self.agent.local_map[new_pos].get("swept", False)
               and not self.agent.local_map[new_pos].get("obstacle", False)
        ]
        chosen_direction = random.choice(list(directions.keys()))
        if unswept_moves:
            rel_dir = ["up", "left", "down", "right"]
            heading_index = rel_dir.index(heading)

            for offset in range(4):
                candidate_direction = rel_dir[(heading_index - 1 + offset) % 4]
                if candidate_direction in unswept_moves:
                    chosen_direction = candidate_direction

        crr_pos_swept = self.agent.local_map[tuple(position)].get("swept", False)



        if not crr_pos_swept:
            self.agent.sweep(position)
            #self.agent.update_local_map_sweep(position)


        self.agent.move(chosen_direction)

        send_message = dict(swept_position=position)
        self.agent.communicate('broadcast',send_message)


        if simulation_status == 'end':
            pass
            stop_flag = True
        waiting = False



        return waiting,stop_flag