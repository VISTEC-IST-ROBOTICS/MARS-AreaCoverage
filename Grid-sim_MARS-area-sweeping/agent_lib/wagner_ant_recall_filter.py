import time
import traceback
from core.critical_check import critical_check


class AntRecallFilterSweep:
    # Match original Wagner's approach
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
        # For recall
        self.neighbor_agent_history_idx = {}
        self.swept_history = [] # ordered_list

    def update_swept_history(self,position,adjacent_obstacles ):
        data = {
            'swept_position':position,
            'adjacent_obstacles':adjacent_obstacles
        }
        self.swept_history.append(data)


    def handle_communication(self,message,observation):
        my_position = tuple(observation.get("position"))
        sender_id = message.get('sender',None)
        message_data = message.get('data',{})
        sender_position = tuple(message_data.get('position'))
        swept_position = tuple(message_data.get('swept_position'))
        sender_adjacent_obstacles = message_data.get('adjacent_obstacles')
        self.agent.update_local_map_obstacle(swept_position, sender_adjacent_obstacles)
        heading = message_data.get('heading')

        critical_swept = message_data.get('critical_swept')
        if critical_swept:
            self.neighbor_critical_sweep_flag = critical_swept
        adjacent_positions = [
            (my_position[0] - 1, my_position[1]),  # left
            (my_position[0], my_position[1] + 1),  # down
            (my_position[0] - 1, my_position[1]+1),  # left-down
            (my_position[0] + 1, my_position[1] + 1),  # right-down
        ]


        if sender_position in adjacent_positions:
            self.delay_flag = True  # Set flag if `position` is adjacent and to the left or above

        if sender_position == my_position:
            self.agent_occupied_flag = True

            if sender_id in self.leave_occupied_cell_dependency:
                self.delay_flag = True

        directions = {
            "up": (my_position[0], my_position[1] - 1),
            "down": (my_position[0], my_position[1] + 1),
            "left": (my_position[0] - 1, my_position[1]),
            "right": (my_position[0] + 1, my_position[1])
        }


        # Check if the sending agent is in any of the defined directions
        for direction, dir_position in directions.items():
            if sender_position == dir_position:
                self.neighbor_agent_by_dir[direction].append(sender_id)
                self.neighbor_agent[sender_id] = dict(position=sender_position,heading = heading)

                break  # Stop after adding to one direction

        swept = message_data.get('swept')
        return
        if swept:
            kernel, critical_key = self.get_kernel(swept_position)

            # Communication filter implemented here
            if critical_check(critical_key) == "not_critical":
                self.agent.update_local_map_sweep(swept_position,'grey')
                #self.swept_history.append(swept_position)  # passing information to third-party agent
            if swept_position not in [instant['swept_position'] for instant in self.swept_history]:
                self.update_swept_history(swept_position, sender_adjacent_obstacles)

           

        else:
            if swept_position not in self.cell_directions:
                self.cell_directions[swept_position] = set() # just initialize variable
            #self.cell_directions[position].add(heading) # this line break the algorithm

    def handle_communication_swept_history(self,message,observation):

        my_position = tuple(observation.get("position"))
        data = message.get('data', {})
        swept_history = data.get('swept_history')

        #print(swept_history)
        for swept_dict in swept_history:
            swept_position = tuple(swept_dict['swept_position'])
            adjacent_obstacles = swept_dict['adjacent_obstacles']
            self.agent.update_local_map_obstacle(swept_position, adjacent_obstacles)
        for swept_dict in swept_history:

            swept_position = tuple(swept_dict['swept_position'])


            if swept_position not in [instant['swept_position'] for instant in self.swept_history]:
                kernel, critical_key = self.get_kernel(swept_position)
                # filter
                if critical_check(critical_key) == "not_critical" and my_position != swept_position:
                    self.agent.update_local_map_sweep(swept_position,'grey')
                    #self.swept_history.append(swept_position)  # passing information to third-party agent
                self.update_swept_history(swept_position, adjacent_obstacles)



    def perform_sweep(self, observation):
        '''

        :param observation:
        :return:

        Procedure
        1. decide whether to sweep current cell or not
        2. decide next move
        3. check dependency and decide whether to move or not
        4. send information
        5. wait for timestep

        '''

        waiting = False
        stop = False
        """
        Perform the ANT_SWEEP logic to determine the next action.
        """

        position = tuple(observation.get("position"))
        new_position = position
        heading = observation.get("heading")
        adjacent_obstacles = observation.get("adjacent_obstacles")
        messages = observation.get("messages", [])  # Default to empty list if no messages
        simulation_status = observation.get("simulation_status")

        # Reset flags
        self.delay_flag = False
        self.agent_occupied_flag = False
        self.neighbor_agent_by_dir = {
            "up": [],
            "down": [],
            "left": [],
            "right": []
        }
        self.neighbor_agent = {}
        self.neighbor_critical_sweep_flag = False

        neighbor_set = set()
        for message in messages:

            data = message.get('data', {})
            if 'swept_history' in data:
                # handle swept history
                self.handle_communication_swept_history(message,observation)
            else:
                self.handle_communication(message,observation)
                sender_id = message.get("sender", None)

                neighbor_set.add(sender_id)
                if sender_id not in self.neighbor_agent_history_idx:
                    # Register sender_id
                    self.neighbor_agent_history_idx[sender_id] = 0


        if self.delay_flag:
            waiting = True
        if self.neighbor_critical_sweep_flag:
            self.visited_cells.clear()
            self.tour_count = 0


        # Update local map with the latest observation data
        self.agent.update_local_map_obstacle(position, adjacent_obstacles)

        # Determine if the current cell is critical by analyzing the 3x3 kernel
        kernel, critical_key = self.get_kernel(position)


        # Identify unswept and obstacle-free adjacent cells
        unswept_moves = self.get_unswept_moves(position)

        # Choose the next direction based on heading and available moves
        chosen_direction = self.choose_direction(heading, unswept_moves)

        swept = False
        critical_swept = False



        # Move in the chosen direction if one was selected
        if chosen_direction :
            if chosen_direction == 'right':
                #print('chose move right')
                if len(self.neighbor_agent_by_dir[chosen_direction]) > 0:
                    for agent_id in self.neighbor_agent_by_dir[chosen_direction]:
                        if self.neighbor_agent[agent_id].get('header') != 'left':
                            #print('Delay from right agent')
                            self.delay_flag = True
                else:
                    pass
                    #print(self.neighbor_agent_by_dir[chosen_direction])

            if chosen_direction == 'up':
                #print('chose move up')
                if len(self.neighbor_agent_by_dir[chosen_direction]) > 0:
                    for agent_id in self.neighbor_agent_by_dir[chosen_direction]:
                        if self.neighbor_agent[agent_id].get('header') != 'down':
                            self.delay_flag = True
                            #print('Delay from upper agent')
                else:
                    pass
                    #print(self.neighbor_agent_by_dir[chosen_direction])
                    # Perform action based on whether the cell is critical or non-critical


            if not self.delay_flag:
                if not self.agent_occupied_flag:
                    if critical_check(critical_key) == "not_critical":
                        self.sweep_and_reset(position)
                        swept = True
                        #self.swept_history.append(position)
                        self.update_swept_history(position,adjacent_obstacles)
                    else:
                        critical_swept = self.handle_critical_cell(position, heading, unswept_moves)
                        swept = critical_swept

                self.agent.move(chosen_direction)
                self.leave_occupied_cell_dependency = self.neighbor_agent_by_dir[chosen_direction].copy()
                directions = {
                    "up": (position[0], position[1] - 1),
                    "down": (position[0], position[1] + 1),
                    "left": (position[0] - 1, position[1]),
                    "right": (position[0] + 1, position[1])
                }
                new_position = directions[chosen_direction]
            else:
                pass
                #print('/////////////////Waiting////////////////////')

        else:
            if not self.agent.local_map[position]["swept"]:
                self.sweep_and_reset(position)
            else:
                print('Agent stopped')
                stop = True


        send_message = dict(position=new_position,heading=heading,swept=swept,critical_swept=critical_swept,swept_position=position,adjacent_obstacles=adjacent_obstacles)
        self.agent.communicate('broadcast',send_message)

        for listener in neighbor_set:
            #print('listener',listener)
            sent_swept_history = self.swept_history[self.neighbor_agent_history_idx[listener]:]
            sent_message = dict(swept_history=sent_swept_history)
            success_flag = self.agent.communicate(listener, sent_message)
            if success_flag:
                pass
                self.neighbor_agent_history_idx[listener] = len(self.swept_history)

        if simulation_status == 'end':
            stop = True
        return waiting,stop
    def get_kernel(self, cell_position):
        """
        Generate a 3x3 kernel of boolean values around the specified cell.
        Each value is True if the cell is unswept and not obstructed, otherwise False.
        """
        x, y = cell_position
        relative_positions = [
            (-1, -1), (0, -1), (1, -1),
            (-1, 0), (0, 0), (1, 0),
            (-1, 1), (0, 1), (1, 1)
        ]

        # Construct the kernel and identify critical keys
        kernel = [
            not (self.agent.local_map.get((x + dx, y + dy), {}).get("swept", True) or
                 self.agent.local_map.get((x + dx, y + dy), {}).get("obstacle", False))
            for dx, dy in relative_positions
        ]
        critical_key = [idx for idx, is_open in enumerate(kernel) if is_open]

        # Format kernel as 3x3 grid
        kernel_3x3 = [kernel[0:3], kernel[3:6], kernel[6:9]]
        return kernel_3x3, tuple(critical_key)

    def get_unswept_moves(self, position):
        """
        Identify unswept, obstacle-free adjacent cells.
        """
        directions = {
            "up": (position[0], position[1] - 1),
            "down": (position[0], position[1] + 1),
            "left": (position[0] - 1, position[1]),
            "right": (position[0] + 1, position[1])
        }
        return [
            direction for direction, new_pos in directions.items()
            if new_pos in self.agent.local_map and
               not self.agent.local_map[new_pos].get("swept", False) and
               not self.agent.local_map[new_pos].get("obstacle", False)
        ]

    def choose_direction(self, heading, unswept_moves):
        """
        Choose the next move direction based on the current heading and available unswept moves.
        """
        rel_dir = ["up", "left", "down", "right"]
        heading_index = rel_dir.index(heading)

        for offset in range(4):
            candidate_direction = rel_dir[(heading_index - 1 + offset) % 4]
            if candidate_direction in unswept_moves:
                return candidate_direction
        return None  # No preferred direction found

    def sweep_and_reset(self, position):
        """
        Sweep the current cell and reset counters for a new cycle.
        """

        if position not in [instant['swept_position'] for instant in self.swept_history]:
            self.agent.sweep(position)
            self.agent.local_map[tuple(position)]["swept"] = True
        else:
            self.agent.update_local_map_sweep(position, 'grey')
        self.visited_cells.clear()
        self.tour_count = 0

    def handle_critical_cell(self, position, heading, unswept_moves):
        """
        Handle the behavior for critical cells based on Wagner's algorithm.
        """
        pos_tuple = tuple(position)
        swept = False
        # Track visited directions for the current cell
        if pos_tuple not in self.cell_directions:
            self.cell_directions[pos_tuple] = set()
        self.cell_directions[pos_tuple].add(heading)

        # Track repeated visits to manage tours
        if pos_tuple in self.visited_cells:
            self.tour_count += 1
            self.visited_cells.clear()
        self.visited_cells.add(pos_tuple)



        # Check conditions to sweep the cell after multiple visits
        if self.tour_count >= 2 and len(self.cell_directions[pos_tuple]) == 1 and len(unswept_moves) == 2:
            self.sweep_and_reset(position)
            swept = True
        return swept

