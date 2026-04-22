import random
class GreedySpiralRandomwalkRecall:
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

        self.neighbor_agent_history_idx = {}
        self.swept_history = [] # ordered_list

    def handle_communication(self,message,observation):

        data = message.get('data',{})
        if 'swept_position' in data:
            swept_position = tuple(data.get('swept_position'))
            if swept_position not in self.swept_history:
                if swept_position not in self.agent.local_map:  # for new position
                    self.agent.local_map[swept_position] = {"swept": True, "obstacle": False}
                else:
                    #self.agent.local_map[swept_position]["swept"] = True
                    self.agent.update_local_map_sweep(swept_position, 'grey')
                self.swept_history.append(swept_position)  # passing information to third-party agent
        elif 'swept_history' in data:
            swept_history = data.get('swept_history')

            for swept_position in swept_history:
                swept_position = tuple(swept_position)

                if swept_position not in self.swept_history:
                    self.agent.update_local_map_sweep(swept_position, 'cyan')
                    self.swept_history.append(swept_position) # passing information to third-party agent

        else:

            print('gsr_recall, handle_communication, unknown data:',data)

    def perform_sweep(self, observation):
        position = observation.get("position")
        heading = observation.get("heading")
        adjacent_obstacles = observation.get("adjacent_obstacles")
        simulation_status = observation.get("simulation_status")
        stop_flag = False
        messages = observation.get("messages", [])  # Default to empty list if no messages
        neighbor_set = set()
        for message in messages:
            self.handle_communication(message,observation)

            sender_id = message.get("sender", None)

            neighbor_set.add(sender_id)
            if sender_id not in self.neighbor_agent_history_idx:
                self.neighbor_agent_history_idx[sender_id] = 0


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
            self.agent.local_map[tuple(position)]["swept"] = True
            self.swept_history.append(tuple(position))

        self.agent.move(chosen_direction)
        #
        sent_message = dict(swept_position=position)

        self.agent.communicate('broadcast',sent_message)
        for listener in neighbor_set:
            #print('listener',listener)
            sent_swept_history = self.swept_history[self.neighbor_agent_history_idx[listener]:]
            sent_message = dict(swept_history=sent_swept_history)
            success_flag = self.agent.communicate(listener, sent_message)
            if success_flag:
                pass
                #self.neighbor_agent_history_idx[listener] = len(self.swept_history)


        if simulation_status == 'end':
            stop_flag = True
        waiting = False
        return waiting,stop_flag