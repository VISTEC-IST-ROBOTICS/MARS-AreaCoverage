# This file contain sweeping algorithm responsible to navigate the robot agent
# This is second attempt after I found the broadcasting method is not applicable for limited communication
# as it required continuous broadcasting to work
# This approach will use ask and reply mechanism instead to get latest data

import time

import numpy as np
from robot_controller.critical_check import critical_check


import logging
import os

from enum import Enum, auto

class AgentState(Enum):
    INIT = auto()
    IDLE = auto()
    MOVING = auto()
    WAITING = auto()
    BLOCKED = auto()
    SWAP_POSITION = auto()
    MOVING_OUT = auto()
    REVERSING = auto()
    REVERSING_BLOCKED = auto()
    STOP = auto()
    CHANGE_HEADING = auto()

    def __str__(self):
        return self.name


def get_cell(robot_agent,initial = False):
    """Return current (col, row) based on current position"""
    col, row = robot_agent.get_col_row(initial)
    return (col, row)


def get_mega_cell(robot_agent):
    """Return (col, row) of the mega cell (2x2)"""
    col, row = get_cell(robot_agent)
    mega_col = (col // 2)
    mega_row = (row // 2)
    return (mega_col, mega_row)


def get_sub_cell_offset(robot_agent):
    col, row = get_cell(robot_agent)  # Get current cell position

    # Calculate the offset within the mega-cell (mod 2 to get 0 or 1 offset)
    offset_x = col % 2  # 0 or 1
    offset_y = row % 2  # 0 or 1

    # Return the sub-cell index based on position within the 2x2 mega-cell
    sub_cell_index = offset_y * 2 + offset_x
    return (offset_x, offset_y)


def get_sub_cell_index(robot_agent):
    """
    0 | 1
    ------
    2 | 3

    Return sub-cell index [0, 1, 2, 3] inside the current mega-cell
    """

    # Calculate the offset within the mega-cell (mod 2 to get 0 or 1 offset)
    offset_x, offset_y = get_sub_cell_offset(robot_agent)

    # Return the sub-cell index based on position within the 2x2 mega-cell
    sub_cell_index = offset_y * 2 + offset_x
    return sub_cell_index


class SweepingAgent:
    TIMESTEP = 0.1
    PING_TIMEOUT = TIMESTEP * 10
    WAIT_TIME =  TIMESTEP * 10
    CASCADE_BLOCKER_PING_TIMEOUT = TIMESTEP * 10



    def __init__(self, parent_node):
        self.parent_node  = parent_node
        self.robot = parent_node.robot

        self.swept_mega_cell = [] # this one for navigation
        self.swept_mega_cell_record = [] # this one for keeping record
        self.state = AgentState.INIT
        self.motion_idx = 0
        self.path = []
        self.sweep_flag = False

        self.dst_mega_cell = None
        self.waiting_flag = False

        self.neighbor_state = {}
        self.waiting_list = {}

        self.visited_megacell = []
        self.cell_dir = {} # for recording direction of visited cell
        self.critical_sweep = False
        self.position_swap_flag = False
        self.position_swap_agent = None
        self.position_to_swap = None

        self.useless_flag = False

        self.useless_pos = None
        self.useless_dir = None
        self.useless_count = 0

        self.terminate_flag = False
        self.stop_cause = ''


        self.ping_result = []
        self.run_flag = False
        self.logger_init()
        self.blocking_flag = False
        self.blocking_agent_list = []
        self.chosen_direction = None

        self.received_blocking_cascade_result = None

        self.heading = None # NORTH,EAST,WEST,SOUTH, update at choose_dir
        self.heading_after_reverse = None # for return to previouse heading before reversing
        self.loop_reversing_flag = False
        self.reverse_path = []
        self.dst_before_reverse = None
        self.chosen_heading = None
        self.robot.get_logger().info("Agent init....")
        self.move_timer = None

    def logger_init(self):
        log_dir = "agents_log"

        os.makedirs(log_dir, exist_ok=True)  # Ensure the directory exists

        log_file = os.path.join(log_dir, f"{self.robot.id}.log")

        self.agent_logger = logging.getLogger(f"agent_{self.robot.id}")  # Unique name per agent
        #logger_handler = logging.FileHandler(log_file)
        logger_handler = logging.FileHandler(log_file, mode='w')

        #logger_handler.setFormatter(logging.Formatter('[%(asctime)s] AGENT - %(message)s', datefmt='%H:%M:%S'))
        formatter = logging.Formatter(
            '[%(asctime)s.%(msecs)03d] AGENT - %(message)s',
            datefmt='%H:%M:%S'
        )
        logger_handler.setFormatter(formatter)
        #self.agent_logger.addHandler(logger_handler)
        self.agent_logger.setLevel(logging.INFO)

        self.agent_logger.propagate = False  # Prevent duplicate logging via root logger
        self.agent_logger.info("Agent initialized.")



    def update(self):
        if self.state == AgentState.INIT:
            col,row = get_cell(self.robot,initial = True)
            if col is None or row is None:
                # no pose data available
                return


            self.ping_agents()

            self.state = AgentState.IDLE


        elif self.state == AgentState.IDLE:

            self.motion_idx = 0
            mega_cell = get_mega_cell(self.robot)
            self.agent_logger.info(f"====================Agent IDLE at pos {mega_cell}====================")
            self.robot.get_logger().info(f"====================Agent IDLE at pos {mega_cell}====================")
            self.robot.subcell_orientation()  # set a robot center of the cell

            if self.robot.is_idle():
                stop = self.choose_dir()
                self.communicate()  # update target direction

                if stop:

                    self.stop_cause += f', No valid direction given from choose_dir()'
                    self.state =  AgentState.MOVING
                    self.terminate_flag = True
                    self.agent_logger.info(f"robot stop, perform final sweep {self.sweep_flag}")


                    if self.sweep_flag:
                        self.robot.sweep()


                self.state = AgentState.MOVING
                self.move_timer = time.time()

            self.robot.update()




        elif self.state ==  AgentState.MOVING:

            '''
            moving inside mega-cell, doesn't required neigbor information
            '''

            if self.robot.is_idle():
                self.agent_logger.info(f"Agent MOVING at motion_idx {self.motion_idx} of {len(self.path)}")
                if self.sweep_flag and self.motion_idx < len(self.path) - 1:
                    mega_cell = get_mega_cell(self.robot)
                    self.agent_logger.info(f"Agent SWEEP at  {mega_cell}")
                    self.robot.sweep()

                if self.motion_idx < len(self.path) - 2:
                    crr_col, crr_row = self.path[self.motion_idx]
                    self.motion_idx += 1
                    nxt_col, nxt_row = self.path[self.motion_idx]
                    self.robot.set_target(crr_col, crr_row, nxt_col, nxt_row)
                elif self.terminate_flag:
                    if self.chosen_direction == 'STOP':

                        if self.motion_idx < len(self.path) - 1:
                            crr_col, crr_row = self.path[self.motion_idx]
                            self.motion_idx += 1
                            nxt_col, nxt_row = self.path[self.motion_idx]
                            self.robot.set_target( crr_col, crr_row,nxt_col, nxt_row)
                        else:
                            self.robot.sweep()
                            self.state = AgentState.STOP
                    else:
                        self.state =  AgentState.STOP
                        self.agent_logger.info('Go to STOP state from self.terminate_flag')
                else:
                    self.state = AgentState.WAITING
                    self.agent_logger.info('Go to WAITING state')
            else:
                self.robot.update()
                time_elapse = time.time() - self.move_timer
                if time_elapse >= 5:
                    self.agent_logger.info('Agent stuck')



        elif self.state == AgentState.REVERSING:
            print('agent reversing...',self.robot.id)

            self.agent_logger.info('====================REVERSING====================')
            if self.robot.is_idle():
                if len(self.reverse_path)>0:
                    target_cell = self.reverse_path.pop(0) # get next target megacell in reverse path
                    self.get_reverse_direction(target_cell)
                    self.state = AgentState.MOVING
                    self.motion_idx = 0  ## need to reset motion index
                    self.agent_logger.info(f'target_cell: {target_cell}')

                else:
                    self.agent_logger.info('Done reversing, need to rotate to original heading')
                    self.loop_reversing_flag = False
                    self.motion_idx = 0
                    self.change_heading(self.heading_after_reverse)
                    self.state = AgentState.CHANGE_HEADING



            self.robot.update()


        elif self.state == AgentState.CHANGE_HEADING:
            if self.robot.is_idle():
                self.agent_logger.info(f"Agent CHANGE_HEADING at motion_idx {self.motion_idx} of {len(self.path)}")

                if self.motion_idx < len(self.path) - 1:
                    crr_col, crr_row = self.path[self.motion_idx]
                    self.motion_idx += 1
                    nxt_col, nxt_row = self.path[self.motion_idx]
                    self.robot.set_target(crr_col, crr_row, nxt_col, nxt_row)

                else:
                    self.state = AgentState.IDLE
                    self.agent_logger.info('Go to IDLE state')
            self.robot.update()

        elif self.state ==  AgentState.WAITING:
            '''
            waiting need information from neigbor
            previousely, neigbor send information when it change the state
            '''
            self.robot.get_logger().info("Agent waiting")
            self.robot.get_logger().info(f"====================Agent WAITING====================")
            if self.robot.is_idle():  # wait for robot to finish moving
                self.agent_logger.info('WAITING_STATE')
                self.waiting_check()
                if self.terminate_flag:
                    self.state = AgentState.STOP
                else:
                    if self.blocking_flag:
                        if self.loop_reversing_flag:
                            self.state = AgentState.REVERSING_BLOCKED
                        else:
                            self.state = AgentState.BLOCKED
                    elif self.position_swap_flag:
                        self.state = AgentState.SWAP_POSITION
                    elif not self.waiting_flag:
                        self.agent_logger.info('not self.waiting_flag -> MOVING_OUT')
                        self.state = AgentState.MOVING_OUT
                    else:
                        # still waiting
                        time.sleep(self.WAIT_TIME)

                # self.communicate()  # this line is mandatory

            self.robot.update()
            #self.communicate()

        elif self.state == AgentState.BLOCKED :
            self.blocking_check()
            if self.terminate_flag:
                self.state =  AgentState.STOP
            elif self.loop_reversing_flag:
                self.state = AgentState.REVERSING
            elif  self.blocking_flag:
                self.agent_logger.info('STATE-UPDATE: still blocked')
                if self.position_swap_flag:
                    self.agent_logger.info('position_swap_flag = True')
                    self.state = AgentState.SWAP_POSITION
                time.sleep(self.WAIT_TIME)
            else:
                self.state =  AgentState.WAITING
        elif self.state == AgentState.REVERSING_BLOCKED:
            self.reverse_blocking_check()


            if self.blocking_flag:
                self.agent_logger.info('STATE-UPDATE: still blocked')
                if self.position_swap_flag:
                    self.agent_logger.info('position_swap_flag = True')
                    self.agent_logger.info(f'dst_mega_cell:{self.dst_mega_cell}')
                    self.state = AgentState.SWAP_POSITION
                time.sleep(self.WAIT_TIME)
            else:
                self.state = AgentState.WAITING
        elif self.state == AgentState.SWAP_POSITION:  # moving out of mega-cell

            if self.robot.is_idle():
                self.swap_position()


            self.robot.update()


        elif self.state == AgentState.MOVING_OUT:  # moving out of mega-cell


            if self.robot.is_idle():
                self.agent_logger.info(
                    f"======================MOVING_OUT {self.robot.id}, {self.robot.color}=======================")
                self.agent_logger.info(f'{self.robot.id}, {self.robot.color}, moving out to {self.dst_mega_cell}')
                if self.motion_idx < len(self.path) - 1:
                    crr_col, crr_row = self.path[self.motion_idx]
                    self.motion_idx += 1
                    nxt_col, nxt_row = self.path[self.motion_idx]
                    self.robot.set_target(crr_col, crr_row, nxt_col, nxt_row)
                else:
                    self.state =  AgentState.IDLE

            self.robot.update()
            #self.communicate()
        elif self.state ==  AgentState.STOP:
            mega_cell = get_mega_cell(self.robot)
            self.robot.get_logger().info(f"====================Agent STOP at pos {mega_cell}====================")

            pass

    def swap_position(self):
        self.ping_agents()
        self.agent_logger.info(f"Ping results: {[msg['sender'] for msg in self.ping_result]}")

        # Find the ping return from the position_swap_agent
        swap_agent_data = next(
            (msg for msg in self.ping_result if msg['sender'] == self.position_swap_agent), None
        )

        if not swap_agent_data:
            self.agent_logger.warning(f"No ping result from {self.position_swap_agent}")
            return

        swap_agent_flag = swap_agent_data['data'].get('position_swap', False)
        swap_agent_pos = tuple(swap_agent_data['data'].get('mega_cell'))


        # Case 1: continue swap motion
        if self.motion_idx < len(self.path) - 1:
            if swap_agent_flag:
                self.agent_logger.info(
                    f"====================== SWAP_POSITION {self.robot.id}, {self.robot.color} ======================="
                )


                crr_col, crr_row = self.path[self.motion_idx]
                self.motion_idx += 1
                nxt_col, nxt_row = self.path[self.motion_idx]
                self.robot.set_target(crr_col, crr_row, nxt_col, nxt_row)
        else:
            # Case 2: check if swap is done
            if swap_agent_pos == self.position_to_swap:
                if self.loop_reversing_flag:
                    self.state = AgentState.REVERSING
                else:
                    self.state = AgentState.IDLE
                self.position_swap_flag = False

    def get_reverse_direction(self, tar_megacell):
        self.agent_logger.info(
            f"======================get_reverse_direction {self.robot.id}, {self.robot.color}=======================")

        # Step 1: Get robot heading based on sub-cell index
        sub_cell_index = get_sub_cell_index(self.robot)
        subcell_heading = {
            0: 'EAST',
            1: 'SOUTH',
            2: 'NORTH',
            3: 'WEST'
        }
        curr_heading = subcell_heading[sub_cell_index]
        self.heading = curr_heading

        def rotate_list(lst, n):
            return lst[n:] + lst[:n]

        # Step 2: Define direction offsets and mega-cell info
        dir_to_offset = {
            'EAST': (1, 0),
            'SOUTH': (0, 1),
            'WEST': (-1, 0),
            'NORTH': (0, -1)
        }
        current_mega_cell = get_mega_cell(self.robot)
        mcol, mrow = current_mega_cell

        # Step 3: Determine heading toward the target mega cell
        dcol = tar_megacell[0] - current_mega_cell[0]
        drow = tar_megacell[1] - current_mega_cell[1]
        if (dcol, drow) == (1, 0):
            chosen_heading = 'EAST'
        elif (dcol, drow) == (0, 1):
            chosen_heading = 'SOUTH'
        elif (dcol, drow) == (-1, 0):
            chosen_heading = 'WEST'
        elif (dcol, drow) == (0, -1):
            chosen_heading = 'NORTH'
        else:
            chosen_heading = 'STOP'  # or raise an error if not adjacent

        dst_mega_cell = tar_megacell
        self.agent_logger.info(f"chosen_heading: {chosen_heading}")
        self.agent_logger.info(f"dst_mega_cell: {dst_mega_cell}")
        self.dst_mega_cell = dst_mega_cell

        # Step 4: Determine relative direction based on heading difference
        heading_to_index = {
            'EAST': 0,
            'SOUTH': 1,
            'WEST': 2,
            'NORTH': 3
        }
        index_to_direction = {
            0: 'FRONT',
            1: 'RIGHT',
            2: 'BACK',
            3: 'LEFT'
        }

        curr_index = heading_to_index[curr_heading]
        target_index = heading_to_index.get(chosen_heading, curr_index)  # default to no change if STOP
        delta = (target_index - curr_index) % 4
        chosen_direction = index_to_direction[delta]
        self.chosen_direction = chosen_direction

        self.agent_logger.info(f"chosen_direction: {chosen_direction}")

        # Step 5: Define relative path
        sub_cell_travel_path = {
            "LEFT": [(0, 0), (0, -1)],
            "FRONT": [(0, 0), (1, 0), (2, 0)],
            "RIGHT": [(0, 0), (1, 0), (1, 1), (1, 2)],
            "BACK": [(0, 0), (0, 1), (-1, 1)],
            "STOP": [(0, 0)]
        }

        rel_path = np.array(sub_cell_travel_path[chosen_direction])

        # Step 6: Rotate subcell path according to current heading
        def rotate_subcell(cell, times):
            subcell_rotate = {
                (0, 0): (1, 0),
                (1, 0): (1, 1),
                (1, 1): (0, 1),
                (0, 1): (0, 0),
                (0, -1): (2, 0),
                (2, 0): (1, 2),
                (1, 2): (-1, 1),
                (-1, 1): (0, -1),
            }
            for _ in range(times):
                cell = tuple(cell)
                if cell not in subcell_rotate:
                    raise ValueError(f"Missing rotation mapping for {cell}")
                cell = subcell_rotate[cell]
            return cell

        rotate_steps = heading_to_index[curr_heading]
        abs_path = []
        for subcell in rel_path:
            rotated = rotate_subcell(subcell, rotate_steps)
            abs_cell = (mcol * 2 + rotated[0], mrow * 2 + rotated[1])
            abs_path.append(abs_cell)

        # Step 7: Store final path
        self.path = abs_path




    def mega_cell_observation(self, abs_neighbor_mega_cells):
        rel_sub_cell = np.array([(0, 0), (0, 1), (1, 0), (1, 1)])

        res = []
        for mega_cells in abs_neighbor_mega_cells:
            cell_res = self.robot.mega_cell_observation(mega_cells)  # occupancy observe

            res.append(cell_res) # return 1 or 0, 1 meant occupied

        return res

    def communicate(self):
        """Send out current robot state as a broadcast message."""
        comm_data = {
            'mega_cell': get_mega_cell(self.robot),
            'swept': self.sweep_flag,
            'color': self.robot.color,
            'dst_mega_cell': self.dst_mega_cell,
            'waiting_list': self.waiting_list,
            'state': self.state,
            'timestamp': time.time(),
            'position_swap': self.position_swap_flag,
            'useless': self.useless_flag,
        }

        msg = {
            'sender': self.robot.id,
            'receiver': 'BROADCAST',
            'instruction': 'INFORM',
            'data': comm_data
        }

        self.robot.communicate(msg)

    def ping_response(self, reciever):
        """Send out current robot state as a broadcast message."""
        #self.agent_logger.info(f'ping response to:{reciever}')

        comm_data = {
            'mega_cell': get_mega_cell(self.robot),
            'swept': self.sweep_flag,
            'color': self.robot.color,
            'dst_mega_cell': self.dst_mega_cell,
            'waiting_list': self.waiting_list,
            'state': self.state,
            'timestamp': time.time(),
            'position_swap': self.position_swap_flag,
            'useless': self.useless_flag,
            'waiting_flag': self.waiting_flag,
            'blocking_agent_list': self.blocking_agent_list,
            'len_swept_record' : len(self.swept_mega_cell_record)
        }

        msg = {
            'sender': self.robot.id,
            'receiver': reciever,
            'instruction': 'PING_RETURN',
            'data': comm_data
        }
        #self.agent_logger.info(msg)

        self.robot.communicate(msg)

    def ping_agents(self):

        #self.agent_logger.info(f"Ping.")
        msg = {
            'sender': self.robot.id,
            'receiver': 'BROADCAST',
            'instruction': 'PING',

        }
        self.ping_result = []  # reset buffer
        self.robot.communicate(msg)

        time.sleep(self.PING_TIMEOUT)
        '''
        do this in case of some normal message arrived
        '''
        self.update_neighbor_swept()

    def update_neighbor_swept(self):
        # using ping result to update neighbor
        self.agent_logger.info(f'====================update_neighbor_swept====================')
        for msg in self.ping_result:
            nb_id = msg['sender']
            data = msg['data']

            nb_pos = data['mega_cell']
            nb_color = data['color']
            nb_waiting_list = data['waiting_list']
            nb_dst_mega_cell = data['dst_mega_cell']
            nb_state = data['state']
            len_swept_record = data['len_swept_record']
            # check with last update
            if nb_id not in self.neighbor_state:
                self.neighbor_state[nb_id] = {}
            last_len_swept_record = self.neighbor_state[nb_id].get('len_swept_record',0)
            self.agent_logger.info(f'neighbor_ID:{nb_id}')
            self.agent_logger.info(f'len_swept_record:{len_swept_record}')
            self.agent_logger.info(f'last_len_swept_record:{last_len_swept_record}')
            if len_swept_record > last_len_swept_record:
                self.swept_data_request(nb_id,last_len_swept_record)


    def swept_data_request(self,target_id,starting_idx):

        #self.agent_logger.info(f"Ping.")
        comm_data = {
            'field':'swept_mega_cell_record',
            'start_idx':starting_idx
        }

        msg = {
            'sender': self.robot.id,
            'receiver': target_id,
            'instruction': 'REQUEST',
            'data': comm_data

        }
        self.robot.communicate(msg)


    def read_msg(self,msg):
        sender = msg['sender']
        instruction = msg['instruction']

        if instruction == 'PING':
            self.ping_response(sender)
        elif instruction == 'PING_RETURN':
            self.ping_result.append(msg)
            self.agent_logger.info(f"I got PING_RETURN")
            self.agent_logger.info(msg)

        elif instruction == 'CASCADE_BLOCKER_PING':
            self.forward_cascade_blocker_ping(msg)

        elif instruction == 'CASCADE_BLOCKER_PING_RETURN':

            self.cascade_blocker_ping_return_handle(msg)


        elif instruction == 'INFORM':
            data = msg['data']

            # Collect swept cell if applicable
            if data.get('swept'):
                self.update_neighbor_sweep(sender, data['mega_cell'])

            # Initialize entry if new sender
            if sender not in self.neighbor_state:
                self.neighbor_state[sender] = {}
            if data.get('swept_mega_cell_record'):
                self.agent_logger.info(f'got swept_mega_cell_record {data.get("swept_mega_cell_record")} from {sender}')
                for swept_megacell in data.get('swept_mega_cell_record'):
                    self.update_neighbor_sweep(sender, swept_megacell)
                len_swept_mega_cell_record = data.get('len_swept_mega_cell_record')

                self.neighbor_state[sender]['len_swept_record'] = len_swept_mega_cell_record

            # Update all data fields
            # self.neighbor_state[sender].update(data)
        elif instruction == 'REQUEST':
            data = msg['data']
            field = data['field']
            if field == 'swept_mega_cell_record':
                start_idx = data['start_idx']
                self.agent_logger.info(f'got swept_mega_cell_record request at {start_idx}')
                self.response_swept_record(sender, start_idx)




    def response_swept_record(self,target,start_idx):
        comm_data = {
            'mega_cell': get_mega_cell(self.robot),

            'color': self.robot.color,
            'dst_mega_cell': self.dst_mega_cell,
            'waiting_list': self.waiting_list,
            'state': self.state,
            'timestamp': time.time(),
            'position_swap': self.position_swap_flag,
            'useless': self.useless_flag,
            'swept_mega_cell_record': self.swept_mega_cell_record[start_idx:-1],
            'len_swept_mega_cell_record': len(self.swept_mega_cell_record),


        }

        msg = {
            'sender': self.robot.id,
            'receiver': target,
            'instruction': 'INFORM',
            'data': comm_data
        }

        self.robot.communicate(msg)

    def cascade_blocker_ping(self,blocker_id,visited_ids = None):
        self.agent_logger.info(f'cascade_blocker_ping, blocker_id:{blocker_id}')
        if visited_ids is None:
            visited_ids = []
        visited_ids.append(self.robot.id)
        comm_data = {
           'visited_ids': visited_ids, # only required this
        }

        msg = {
            'sender': self.robot.id,
            'receiver': blocker_id,
            'instruction': 'CASCADE_BLOCKER_PING',
            'data': comm_data
        }

        self.robot.communicate(msg)

        #time.sleep(self.CASCADE_BLOCKER_PING_TIMEOUT)
        '''
        do this in case of some normal message arrived
        '''
    def forward_cascade_blocker_ping(self, msg):
        visited_ids = msg['data'].get('visited_ids', [])
        sender_id = msg['sender']
        visited_ids = visited_ids.copy()  # Prevent shared mutation!


        #self.agent_logger.info(f"Received CASCADE_BLOCKER_PING from {sender_id}")
        #self.agent_logger.info(f"Visited chain so far: {visited_ids}")

        if self.state == AgentState.BLOCKED and self.blocking_agent_list:
            next_blocker = self.blocking_agent_list[0]
            if next_blocker in visited_ids:
                #self.agent_logger.info(f"Detected loop: {next_blocker} already in visited_ids")
                # no need for forward it further, it's time to return
                self.cascade_blocker_ping_return(sender_id,visited_ids)
            else:
                #self.agent_logger.info(f"{self.robot.id} is BLOCKED by {next_blocker}, forwarding cascade ping")
                self.cascade_blocker_ping(blocker_id=next_blocker, visited_ids=visited_ids)
        else:
            #self.agent_logger.info(
            #    f"{self.robot.id} is not blocked further (state = {self.state}, blockers = {self.blocking_agent_list})")
            self.cascade_blocker_ping_return(sender_id,visited_ids)

    def cascade_blocker_ping_return(self,target_id,traceback_ids,agent_data_list = None):
        '''For sending return packet'''
        if agent_data_list is None:
            agent_data_list = []
        my_data = {
            'id': self.robot.id,
            'mega_cell': get_mega_cell(self.robot), # required to determing the highest priority
            'state': self.state,
            'timestamp': time.time(),
            'blocking_agent_list': self.blocking_agent_list,

        }
        agent_data_list.append(my_data)
        comm_data = {
            'agent_data_list': agent_data_list,
            'traceback_ids': traceback_ids,
        }

        msg = {
            'sender': self.robot.id,
            'receiver': target_id,
            'instruction': 'CASCADE_BLOCKER_PING_RETURN',
            'data': comm_data
        }
        # self.agent_logger.info(msg)

        self.robot.communicate(msg)

    def cascade_blocker_ping_return_handle(self, msg):
        '''For handling incoming return packet'''
        traceback_ids = msg['data'].get('traceback_ids', [])
        agent_data_list = msg['data'].get('agent_data_list', [])

        if traceback_ids[0] == self.robot.id:
            '''This agent initiated the CBP'''
            self.agent_logger.info('The blocker cascade ping has returned')
            self.agent_logger.info(f"Traceback chain: {traceback_ids}")
            self.agent_logger.info(f"Agent data list: {agent_data_list}")

            my_data = {
                'id': self.robot.id,
                'mega_cell': get_mega_cell(self.robot),  # required to determing the highest priority
                'state': self.state,
                'timestamp': time.time(),
                'blocking_agent_list': self.blocking_agent_list,

            }
            agent_data_list.append(my_data)
            self.received_blocking_cascade_result = {
                'traceback_ids': traceback_ids,
                'agent_data_list': agent_data_list
            }
        else:
            # Forward the return packet to the agent before you in the traceback
            my_index = traceback_ids.index(self.robot.id)
            target = traceback_ids[my_index - 1]
            self.cascade_blocker_ping_return(target_id=target,
                                             traceback_ids=traceback_ids,
                                             agent_data_list=agent_data_list)



    def update_neighbor_sweep(self,sender, sweep_megacell):
        sweep_megacell = tuple(sweep_megacell)
        # Building kernel
        kernel = []
        for d_row in [-1, 0, 1]:
            for d_col in [-1, 0, 1]:
                kernel.append((sweep_megacell[0] + d_col, sweep_megacell[1] + d_row))

        kernel_res = self.mega_cell_observation(kernel)

        key = []

        for idx, nb_mcell in enumerate(kernel):
            if kernel_res[idx] == 0 and nb_mcell not in self.swept_mega_cell:
                key.append(idx)

        critical = critical_check(tuple(key))

        if sweep_megacell not in self.swept_mega_cell_record:
            self.swept_mega_cell_record.append(sweep_megacell)
            self.agent_logger.info(f"append data from {sender} cell ({sweep_megacell}) to self.swept_mega_cell_record")
            self.agent_logger.info(self.swept_mega_cell_record)

        if critical != 'critical' and sweep_megacell != self.dst_mega_cell:
            self.swept_mega_cell.append(sweep_megacell)
            #self.agent_logger.info(f"Update swept_mega_cell from {sender}, {sweep_megacell}")


    def waiting_check(self):
        '''
        This function required intensive communication

        :return:
        '''
        self.agent_logger.info('====================Waiting check=======================')
        self.robot.get_logger().info('====================Waiting check=======================')

        #print(f"Agent:{self.robot.id}, {self.robot.color}")
        my_position = get_mega_cell(self.robot)

        my_dst = self.dst_mega_cell
        self.agent_logger.info(f'My position {my_position}')
        self.agent_logger.info(f'My destination {my_dst}')

        self.robot.get_logger().info(f'My position {my_position}')
        self.robot.get_logger().info(f'My destination {my_dst}')


        waiting_flag = False
        blocking_flag = False
        waiting_list = []
        LEFT_ADJACENT = (my_position[0] - 1, my_position[1])
        DOWN_ADJACENT = (my_position[0], my_position[1] + 1)
        waiting_zone = [
            LEFT_ADJACENT,  # left
            DOWN_ADJACENT,  # down
            (my_position[0] - 1, my_position[1] + 1),  # left-down
            (my_position[0] + 1, my_position[1] + 1),  # right-down
        ]
        dst_x, dst_y = my_dst
        dst_adj_zone = [
            (dst_x - 1, dst_y),  # left
            (dst_x + 1, dst_y),  # right
            (dst_x, dst_y - 1),  # up
            (dst_x, dst_y + 1),  # down
        ]

        self.ping_agents()
        self.robot.get_logger().info(f'len of ping result {len(self.ping_result)}')

        same_dst_winner_flag = False
        nb_with_not_same_dst_flag = False

        for msg in self.ping_result:
            nb_id = msg['sender']
            data = msg['data']

            nb_pos = tuple(data['mega_cell'])
            nb_color = data['color']
            nb_waiting_list = data['waiting_list']
            nb_dst_mega_cell = tuple(data['dst_mega_cell'])
            nb_state = data['state']


            self.agent_logger.info((nb_id, nb_color, 'pos:', nb_pos, nb_state))
            #self.robot.get_logger().info((nb_id, nb_color, 'pos:', nb_pos, nb_state))
            self.robot.get_logger().info(
                f"{nb_id}, {nb_color}, pos: {nb_pos}, state: {nb_state}"
            )

            if nb_pos in waiting_zone and nb_state !=  AgentState.STOP and nb_state != AgentState.BLOCKED and nb_state != AgentState.REVERSING_BLOCKED:
                '''
                other agent in waiting zone. ignored the stopped anf blocked agents
                '''
                self.agent_logger.info(f'My neighbor dependency is occupied by {nb_id}, {nb_color} at, {nb_pos}, with {nb_state}')
                self.agent_logger.info(('nb_waiting_list', nb_waiting_list))

                waiting_flag = True
                # we can discard this
                self.agent_logger.info("waiting_flag = True")
                if nb_id not in waiting_list:
                    waiting_list.append(nb_id)

            if self.dst_mega_cell == nb_pos:
                '''
                destination occupied by other agent
                '''
                blocking_flag = True

            if nb_pos in dst_adj_zone:

                if self.dst_mega_cell == nb_dst_mega_cell:
                    # same destination wait
                    '''
                    Same-destination wait
                    '''
                    self.agent_logger.info(
                        f'My destination ({self.dst_mega_cell})  is the same as  {nb_id}, {nb_color} at, {nb_pos} with {nb_state}')
                    if nb_state ==  AgentState.STOP:
                        self.agent_logger.info('I will not wait for stopped agent')
                    if nb_state == AgentState.BLOCKED or nb_state == AgentState.REVERSING_BLOCKED:
                        self.agent_logger.info('I will not wait for blocked agent')
                    else:
                        '''
                        need to check the priority if we should update agent's state to WAITING or BLOCKED
                        '''
                        if my_position[0] < nb_pos[0]:
                            self.agent_logger.info("I shall be blocked, condition: I am on the left")

                            blocking_flag = True
                            self.agent_logger.info("blocking_flag = True")
                            pass
                        elif my_position[0] == nb_pos[0]:
                            if my_position[1] < nb_pos[1]:
                                self.agent_logger.info("I shall be blocked, I am on top")
                                blocking_flag = True
                                self.agent_logger.info("blocking_flag = True")
                            else:
                                '''
                                their is some agent at lower priority which is not in stop or blocked state,
                                seem like it not aware of this agent so we need to wait
                                '''
                                if nb_state != AgentState.BLOCKED and nb_state != AgentState.REVERSING_BLOCKED:
                                    self.agent_logger.info(f"{nb_id} have lower priority but candidate was not in BLOCKED state yet")
                                    self.agent_logger.info("waiting_flag = True")
                                    waiting_flag = True
                                    if nb_id not in waiting_list:
                                        waiting_list.append(nb_id)
                                else:
                                    self.agent_logger.info("I am going to move in with same destination conflict")
                                    same_dst_winner_flag = True


                        else:
                            '''
                            their is some agent at lower priority which is not in stop or blocked state,
                            seem like it not aware of this agent so we need to wait
                            '''
                            if nb_state != AgentState.BLOCKED and nb_state != AgentState.REVERSING_BLOCKED:
                                self.agent_logger.info(f"{nb_id} have lower priority but not in BLOCKED state yet")
                                self.agent_logger.info("waiting_flag = True")
                                waiting_flag = True
                                if nb_id not in waiting_list:
                                    waiting_list.append(nb_id)
                else:
                    self.agent_logger.info('This agent in ADJ zone but not has same destination')
                    nb_with_not_same_dst_flag = True
                    if nb_id not in waiting_list:
                        waiting_list.append(nb_id) # just in case


        if same_dst_winner_flag and nb_with_not_same_dst_flag:
            self.agent_logger.info('We need that adj agent with different dst to go first')
            waiting_flag = True
            self.agent_logger.info("waiting_flag = True")


        self.waiting_list = waiting_list
        self.waiting_flag = waiting_flag
        self.blocking_flag = blocking_flag
        if not waiting_flag and not blocking_flag:
            self.agent_logger.info('Delay_check: Free to go')
        elif blocking_flag:
            self.agent_logger.info('This agent got blocked')
        self.robot.get_logger().info('====================[Done] Waiting check=======================')


    def has_higher_priority(self, pos_a, pos_b):
        return pos_a[0] > pos_b[0] or (pos_a[0] == pos_b[0] and pos_a[1] < pos_b[1])

    def trace_blocking_chain(self, blocking_agent_list):
        visited = set()
        forward_chain = [self.robot.id]
        current_blocker = blocking_agent_list[0] if blocking_agent_list else None

        my_pos = get_mega_cell(self.robot)
        highest_priority = True

        # === Forward chain: who blocks me
        while current_blocker and current_blocker not in visited:
            self.agent_logger.info(f"Current blocker {current_blocker}")
            visited.add(current_blocker)

            blocker_msg = next((msg for msg in self.ping_result if msg['sender'] == current_blocker), None)
            if blocker_msg is None:
                self.agent_logger.info(f"Blocker {current_blocker} not found -> Partial blocking")
                self.partial_blocking_flag = True
                forward_chain.append(current_blocker)
                break

            blocker_data = blocker_msg['data']
            blocker_state = blocker_data['state']
            blocker_pos = blocker_data['mega_cell']
            next_blocking_list = blocker_data.get('blocking_agent_list', [])

            forward_chain.append(current_blocker)

            # Priority check (forward chain)
            if not self.has_higher_priority(my_pos, blocker_pos):
                highest_priority = False
                self.agent_logger.info(
                    f"{self.robot.id} does NOT have higher priority than {current_blocker} at {blocker_pos}")

            if (blocker_state != AgentState.BLOCKED and  blocker_state != AgentState.REVERSING_BLOCKED) or not next_blocking_list:
                break

            current_blocker = next_blocking_list[0]



        # === Logging results
        forward_str = " -> ".join(forward_chain)
        self.agent_logger.info(f"Blocking forward chain: {forward_str}")

        all_blocked = True

        full_chain_ids = set(forward_chain) # Not: backward chain make no sense sine single agent could blocked multiple agent

        for agent_id in full_chain_ids:
            if agent_id == self.robot.id:
                continue  # Skip self if already checked
            msg = next((msg for msg in self.ping_result if msg['sender'] == agent_id), None)
            if msg:
                data = msg['data']
                state = data['state']
                blocking_list = data.get('blocking_agent_list', [])

                if (state != AgentState.BLOCKED  and state != AgentState.REVERSING_BLOCKED) or len(blocking_list) == 0:
                    self.agent_logger.info(
                        f"{agent_id} is NOT properly BLOCKED (state = {state}, blockers = {blocking_list})")
                    all_blocked = False
            else:
                self.agent_logger.info(f"{agent_id} not found in ping result")



        self.all_blocked_in_chain_flag = all_blocked
        if all_blocked:
            self.agent_logger.info("All agents in the dependency chain are BLOCKED.")
            self.highest_priority_flag = highest_priority
            if highest_priority:
                self.agent_logger.info(f"{self.robot.id} has the HIGHEST priority in the entire dependency segment.")
                #print(self.robot.id, 'has the HIGHEST priority ')
                return True
        else:
            self.agent_logger.info("Not all agents in the dependency chain are BLOCKED.")
            return False




    def blocking_check(self):
        '''
        This function required intensive communication

        :return:
        '''
        blocking_agent_list = []
        self.agent_logger.info('====================Blocking check=======================')
        # print(f"Agent:{self.robot.id}, {self.robot.color}")
        my_position = get_mega_cell(self.robot)

        my_dst = self.dst_mega_cell
        self.agent_logger.info(f'My position {my_position}')
        self.agent_logger.info(f'My destination {my_dst}')

        blocking_flag = False

        self.ping_agents()

        for msg in self.ping_result:
            nb_id = msg['sender']
            data = msg['data']

            nb_pos = tuple(data['mega_cell'])
            nb_color = data['color']
            nb_dst_mega_cell = tuple(data['dst_mega_cell'])
            nb_state = data['state']
            nb_swept = data['swept']


            self.agent_logger.info((nb_id, nb_color, 'pos:', nb_pos, nb_state))

            if self.dst_mega_cell == nb_pos:
                '''
                Agent want to go in the megacell occupied by neighbor agent
                '''
                self.agent_logger.info(
                    f'My destination ({self.dst_mega_cell}) is occupied by {nb_id}, {nb_color}  at, {nb_pos} with {nb_state}')
                if nb_state ==  AgentState.STOP:
                    '''
                    agent target got block by STOP agent,
                    '''
                    self.terminate_flag = True
                    self.agent_logger.info('The blocker is STOP state, this agent will STOP')
                    self.stop_cause += f', My destination ({self.dst_mega_cell}) is occupied by {nb_id}, {nb_color}  at, {nb_pos} with {nb_state}'

                if  (nb_state == AgentState.SWAP_POSITION or nb_state == AgentState.BLOCKED or nb_state == AgentState.REVERSING_BLOCKED) and nb_dst_mega_cell == my_position:
                    # remove 'and not nb_swept'

                    self.position_swap_flag = True
                    self.position_swap_agent = nb_id
                    self.position_to_swap = nb_dst_mega_cell
                    blocking_flag = True
                    self.agent_logger.info("blocking_flag = True, proceeding position swapping")

                else:

                    self.agent_logger.info(('Still blocked', nb_state, nb_swept))

                    blocking_flag = True
                    self.agent_logger.info("blocking_flag = True")
                    blocking_agent_list.append(nb_id)



            if self.dst_mega_cell and self.dst_mega_cell == nb_dst_mega_cell:
                # same destination wait
                self.agent_logger.info(
                    f'My destination ({self.dst_mega_cell})  is the same as  {nb_id}, {nb_color} at, {nb_pos} with {nb_state}')
                if nb_state ==  AgentState.STOP:
                    self.agent_logger.info('I will not wait for stopped agent')
                if nb_state == AgentState.BLOCKED or nb_state == AgentState.REVERSING_BLOCKED:
                    self.agent_logger.info('I will not wait for BLOCKED agent')
                else:
                    self.agent_logger.info(('Still blocked', nb_state, nb_swept))

                    blocking_flag = True
                    self.agent_logger.info("blocking_flag = True")
                    blocking_agent_list.append(nb_id)
                    pass


        self.blocking_flag = blocking_flag
        # === Log full blocking dependency chain ===
        if blocking_flag and blocking_agent_list:
            initiate_cascade_blocker_ping = self.trace_blocking_chain(blocking_agent_list)
            if initiate_cascade_blocker_ping:
                self.agent_logger.info('initiate cascade_blocker_ping')
                self.received_blocking_cascade_result = {} # reset buffer
                self.cascade_blocker_ping(blocking_agent_list[0])
                time.sleep(self.CASCADE_BLOCKER_PING_TIMEOUT)
                self.agent_logger.info(self.received_blocking_cascade_result)
                self.blocking_cascade_handle() # this functionalso update loop_reversing_flag
                self.agent_logger.info(f' self.loop_reversing_flag: { self.loop_reversing_flag}')
                if self.loop_reversing_flag:
                    self.heading_after_reverse = self.chosen_heading
                    self.dst_before_reverse = self.dst_mega_cell
                    self.agent_logger.info(f'loop_reversing, heading_after_reverse:{self.heading_after_reverse }')



        else:
            self.agent_logger.info('Blocking check: Free to go')

        self.blocking_agent_list = blocking_agent_list
        if self.terminate_flag:
            self.agent_logger.info('This agent will be terminate')
            self.state =  AgentState.STOP
    def reverse_blocking_check(self):
        '''
        This function required intensive communication

        :return:
        '''
        blocking_agent_list = []
        self.agent_logger.info('====================Reverse-Blocking check=======================')
        # print(f"Agent:{self.robot.id}, {self.robot.color}")
        my_position = get_mega_cell(self.robot)

        my_dst = self.dst_mega_cell
        self.agent_logger.info(f'My position {my_position}')
        self.agent_logger.info(f'My destination {my_dst}')

        blocking_flag = False

        self.ping_agents()

        for msg in self.ping_result:
            nb_id = msg['sender']
            data = msg['data']

            nb_pos = tuple(data['mega_cell'])
            nb_color = data['color']
            nb_dst_mega_cell = tuple(data['dst_mega_cell'])
            nb_state = data['state']
            nb_swept = data['swept']


            self.agent_logger.info((nb_id, nb_color, 'pos:', nb_pos, nb_state))

            if self.dst_mega_cell == nb_pos:
                '''
                Agent want to go in the megacell occupied by neighbor agent
                '''
                self.agent_logger.info(
                    f'My destination ({self.dst_mega_cell}) is occupied by {nb_id}, {nb_color}  at, {nb_pos} with {nb_state}')
                if nb_state ==  AgentState.STOP:
                    '''
                    agent target got block by STOP agent,
                    '''
                    self.terminate_flag = True
                    self.agent_logger.info('The blocker is STOP state, this agent will STOP')
                    self.stop_cause += f', My destination ({self.dst_mega_cell}) is occupied by {nb_id}, {nb_color}  at, {nb_pos} with {nb_state}'

                if  (nb_state == AgentState.SWAP_POSITION or nb_state == AgentState.BLOCKED) and nb_dst_mega_cell == my_position:
                    # remove 'and not nb_swept'

                    self.position_swap_flag = True
                    self.position_swap_agent = nb_id
                    self.position_to_swap = nb_dst_mega_cell
                    blocking_flag = True
                    self.agent_logger.info("reverse-blocking check : blocking_flag = True, proceeding position swapping")

                else:

                    self.agent_logger.info(('Still blocked', nb_state, nb_swept))

                    blocking_flag = True
                    self.agent_logger.info("blocking_flag = True")
                    blocking_agent_list.append(nb_id)



            if self.dst_mega_cell and self.dst_mega_cell == nb_dst_mega_cell:
                # same destination wait
                self.agent_logger.info(
                    f'My destination ({self.dst_mega_cell})  is the same as  {nb_id}, {nb_color} at, {nb_pos} with {nb_state}')
                if nb_state ==  AgentState.STOP:
                    self.agent_logger.info('I will not wait for stopped agent')
                if nb_state == AgentState.BLOCKED:
                    self.agent_logger.info('I will not wait for BLOCKED agent')
                else:
                    self.agent_logger.info(('Still blocked', nb_state, nb_swept))

                    blocking_flag = True
                    self.agent_logger.info("blocking_flag = True")
                    blocking_agent_list.append(nb_id)
                    pass


        self.blocking_flag = blocking_flag
        # === Log full blocking dependency chain ===
        if not blocking_flag:

            self.agent_logger.info('Blocking check: Free to go')

        self.blocking_agent_list = blocking_agent_list
        if self.terminate_flag:
            self.agent_logger.info('This agent will be terminate')
            self.state =  AgentState.STOP

    def blocking_cascade_handle(self):
        '''
        Analyze the result from received_blocking_cascade_result to:
        - Build a true dependency graph from agent_data_list
        - Detect if a blocking loop exists
        - Determine whether self.robot.id is inside the loop
        - Determine whether self.robot has the highest priority in the loop
        '''
        self.agent_logger.info("==================== Blocking Cascade Handle =======================")
        result = self.received_blocking_cascade_result
        agent_data_list = result.get('agent_data_list', [])
        self.agent_logger.info('agent_data_list')
        self.agent_logger.info(agent_data_list)

        # Step 1: Build agent_id → blocker_id map and id → position map
        blocking_map = {}
        id_to_pos = {}

        for agent_data in agent_data_list:
            agent_id = agent_data.get('id')
            blocker_list = agent_data.get('blocking_agent_list', [])
            mega_cell = agent_data.get('mega_cell')

            if agent_id:
                id_to_pos[agent_id] = mega_cell
                if blocker_list:
                    blocking_map[agent_id] = blocker_list[0]

        self.agent_logger.info(f"Constructed blocking map: {blocking_map}")

        # Step 2: Detect cycle using DFS
        visited = set()
        loop_detected = False
        loop_path = []

        def dfs(node, path):
            nonlocal loop_detected, loop_path
            if node in path:
                loop_detected = True
                loop_path = path[path.index(node):] + [node]
                return
            if node in visited or node not in blocking_map:
                return
            visited.add(node)
            path.append(node)
            dfs(blocking_map[node], path)
            path.pop()

        for agent_id in blocking_map:
            if loop_detected:
                break
            dfs(agent_id, [])

        # Step 3: Result logging
        if loop_detected:
            self.agent_logger.info(f"Dependency loop detected: {' -> '.join(loop_path)}")
            self.in_dependency_loop_flag = self.robot.id in loop_path
            if self.in_dependency_loop_flag:
                self.agent_logger.info(f"{self.robot.id} is inside the dependency ring.")

                # Step 4: Check for highest priority
                my_pos = id_to_pos.get(self.robot.id)
                highest = True
                for other_id in loop_path:
                    if other_id == self.robot.id:
                        continue
                    other_pos = id_to_pos.get(other_id)
                    if other_pos and self.has_higher_priority(other_pos, my_pos):
                        highest = False
                        break

                if highest:
                    self.agent_logger.info(f"{self.robot.id} has the HIGHEST priority in the loop.")
                    self.loop_reversing_flag = True
                    # contruct reversing_path

                    # Step 1: Remove duplicate closing element if present
                    # Step 1: Clean the loop (remove closing duplicate)
                    self.agent_logger.info(f"loop_path:{loop_path}")
                    trimmed_loop_path = loop_path[:-1]
                    self.agent_logger.info(f"trimmed_loop_path:{trimmed_loop_path}")
                    idx = trimmed_loop_path.index(self.robot.id)
                    rotated_loop = trimmed_loop_path[idx:] + trimmed_loop_path[:idx]
                    self.agent_logger.info(f"rotated_loop:{rotated_loop}")
                    reversed_ids_loop = list(reversed(rotated_loop))
                    self.agent_logger.info(f"reversed_ids_loop:{reversed_ids_loop}")
                    trimmed_reversed_ids_loop = reversed_ids_loop[:-1]
                    self.reverse_path = [id_to_pos[aid] for aid in trimmed_reversed_ids_loop if aid in id_to_pos]

                    self.agent_logger.info(f"self.reverse_path:{self.reverse_path}")






                else:
                    self.agent_logger.info(f"{self.robot.id} does NOT have the highest priority in the loop.")
                    self.loop_reversing_flag = False
            else:
                self.agent_logger.info(f"{self.robot.id} is NOT inside the dependency ring.")
                self.in_dependency_loop_flag = False
                self.loop_reversing_flag = False
        else:
            self.agent_logger.info("No dependency loop detected.")
            self.in_dependency_loop_flag = False
            self.loop_reversing_flag = False

    def change_heading(self, desire_heading):
        '''
        Change heading within megacell by moving to another subcell via orthogonal steps.
        Headings: 'EAST', 'SOUTH', 'NORTH', 'WEST'
        '''

        self.agent_logger.info("==================== change_heading ====================")

        # Determine current megacell and subcell index
        mcol, mrow = get_mega_cell(self.robot)
        sub_cell_index = get_sub_cell_index(self.robot)

        index_to_heading = {
            0: 'EAST',
            1: 'SOUTH',
            2: 'NORTH',
            3: 'WEST'
        }
        heading_to_index = {v: k for k, v in index_to_heading.items()}

        curr_heading = index_to_heading[sub_cell_index]
        self.agent_logger.info(f'Current Heading: {curr_heading}')
        self.agent_logger.info(f'Desired Heading: {desire_heading}')

        if desire_heading not in heading_to_index:
            self.agent_logger.warning("Invalid desired heading.")
            return

        # Subcell positions for each heading (within megacell)
        heading_to_offset = {
            'EAST': (0, 0),
            'SOUTH': (1, 0),
            'NORTH': (0, 1),
            'WEST': (1, 1),
        }

        curr_offset = heading_to_offset[curr_heading]
        target_offset = heading_to_offset[desire_heading]

        # Compute absolute subcell position
        def to_abs(offset):
            return (mcol * 2 + offset[0], mrow * 2 + offset[1])

        curr_abs = to_abs(curr_offset)
        target_abs = to_abs(target_offset)

        if curr_abs == target_abs:
            self.path = [curr_abs]
            self.agent_logger.info("Already at desired heading (STOP).")
            return

        # Build path using only horizontal/vertical moves (no diagonal)
        path = [curr_abs]
        cx, cy = curr_offset
        tx, ty = target_offset

        # First move in x (col), then y (row) — or reverse, both valid
        while cx != tx:
            cx += 1 if tx > cx else -1
            path.append(to_abs((cx, cy)))
        while cy != ty:
            cy += 1 if ty > cy else -1
            path.append(to_abs((cx, cy)))

        self.path = path
        self.agent_logger.info(f"Heading change path: {self.path}")

    def choose_dir(self):

        self.agent_logger.info(f"======================Update {self.robot.id}, {self.robot.color}=======================")

        # Step 1: Get robot heading based on sub-cell index
        sub_cell_index = get_sub_cell_index(self.robot)
        # print(f'sub_cell_index:{sub_cell_index}')
        subcell_heading = {
            0: 'EAST',
            1: 'SOUTH',
            2: 'NORTH',
            3: 'WEST'
        }
        curr_heading = subcell_heading[sub_cell_index]
        self.heading = curr_heading

        # Step 2: Determine direction priority relative to heading
        dir_priority = ['NORTH', 'EAST', 'SOUTH', 'WEST']  # assuming facing EAST
        heading_to_rotate_num = {
            'EAST': 0,
            'SOUTH': 1,
            'WEST': 2,
            'NORTH': 3
        }

        def rotate_list(lst, n):
            return lst[n:] + lst[:n]

        rotate_steps = heading_to_rotate_num[curr_heading]
        dir_priority = rotate_list(dir_priority, rotate_steps)

        # Step 3: Define direction offsets and mega-cell info
        dir_to_offset = {
            'EAST': (1, 0),
            'SOUTH': (0, 1),
            'WEST': (-1, 0),
            'NORTH': (0, -1)
        }
        current_mega_cell = get_mega_cell(self.robot)
        mcol, mrow = current_mega_cell

        # Step 4: Build absolute neighbor mega-cell list in the same order as dir_priority
        abs_neighbor_mega_cells = []

        for move_dir in dir_priority:
            dcol, drow = dir_to_offset[move_dir]
            neighbor = (mcol + dcol, mrow + drow)
            abs_neighbor_mega_cells.append(neighbor)

        # Step 5: Check observations (batch) and pick first available neighbor
        res = self.mega_cell_observation(abs_neighbor_mega_cells)
        rel_dir = ['LEFT', 'FRONT', 'RIGHT', 'BACK']  # aligns with rotated dir_priority
        chosen_direction = 'STOP'
        dst_mega_cell = None
        chosen_heading = None
        for idx, mcell in enumerate(abs_neighbor_mega_cells):
            if tuple(mcell) not in self.swept_mega_cell and res[idx] == 0:
                chosen_direction = rel_dir[idx]
                chosen_heading = dir_priority[idx]
                dst_mega_cell = tuple(mcell)
                break
        self.chosen_heading = chosen_heading
        self.agent_logger.info(f"chosen_heading:{chosen_heading}")
        self.agent_logger.info(f"dst_mega_cell:{dst_mega_cell}")
        # Final assignment
        self.dst_mega_cell = dst_mega_cell
        self.critical_sweep = False
        # record_direction
        if current_mega_cell not in self.visited_megacell:
            self.visited_megacell.append(current_mega_cell)

        if current_mega_cell not in self.cell_dir:
            self.cell_dir[current_mega_cell] = [chosen_heading]
        else:

            if chosen_heading not in self.cell_dir[current_mega_cell]:
                self.cell_dir[current_mega_cell].append(chosen_heading)
            elif chosen_heading in self.cell_dir[current_mega_cell]:
                # equivalent to  chosen_heading  in self.cell_dir[current_mega_cell]

                self.agent_logger.info(f'{self.robot.id}:{self.robot.color} USELESS_STATE, flag:{self.useless_flag}')

                if not self.useless_flag:
                    # only allow single agent to be useless
                    self.useless_flag = True
                    self.useless_count = 0
                    # print('I set my useless flag to True')
                    self.useless_pos = current_mega_cell
                    self.useless_dir = chosen_heading

                else:
                    # second time visit 'self.useless_pos'
                    if len(self.cell_dir[current_mega_cell]) == 1:
                        unswept_nb_mcell_count = 0
                        for idx, mcell in enumerate(abs_neighbor_mega_cells):
                            if tuple(mcell) not in self.swept_mega_cell and res[idx] == 0:
                                unswept_nb_mcell_count += 1
                        if unswept_nb_mcell_count == 2:
                            self.critical_sweep = True
                            self.agent_logger.info('Critical sweep!!!')

                    if current_mega_cell == self.useless_pos:
                        self.useless_count += 1
                    if self.useless_count >= 2:
                        # print('='*10+'Terminate'+'='*10)
                        chosen_direction = 'STOP'
                        self.stop_cause += f', {self.robot.id}:{self.robot.color} is raising terminate flag by useless_count >= 2'
                        self.critical_sweep = True
                        self.terminate_flag = True
                        self.dst_mega_cell = None

        # Building kernel
        kernel = []
        for d_row in [-1, 0, 1]:
            for d_col in [-1, 0, 1]:
                kernel.append((current_mega_cell[0] + d_col, current_mega_cell[1] + d_row))

        kernel_res = self.mega_cell_observation(kernel)
        key = []
        for idx, nb_mcell in enumerate(kernel):
            if kernel_res[idx] == 0 and nb_mcell not in self.swept_mega_cell:
                key.append(idx)

        critical = critical_check(tuple(key))

        if critical == 'critical' and not self.critical_sweep:
            self.sweep_flag = False
        else:
            self.sweep_flag = True

        sub_cell_coverage_path = {
            # list of sub-cell index by assume that agent start from sub-cell index 0 give next relative direction
            "LEFT": [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0), (0, -1)],
            "FRONT": [(0, 0), (0, 1), (1, 1), (1, 0), (2, 0)],
            "RIGHT": [(0, 0), (1, 0), (1, 1), (0, 1), (1, 1), (1, 2)],
            "BACK": [(0, 0), (1, 0), (1, 1), (0, 1), (-1, 1)],
            "STOP": [(0, 0), (1, 0), (1, 1), (0, 1), ],  # swept final cell
        }

        sub_cell_travel_path = {
            # list of sub-cell index by assume that agent start from sub-cell index 0 give next relative direction
            "LEFT": [(0, 0), (0, -1)],
            "FRONT": [(0, 0), (1, 0), (2, 0)],
            "RIGHT": [(0, 0), (1, 0), (1, 1), (1, 2)],
            "BACK": [(0, 0), (0, 1), (-1, 1)],
            "STOP": [(0, 0)],  # swept final cell
        }

        self.agent_logger.info(f" self.terminate_flag:{ self.terminate_flag}")
        if self.terminate_flag:
            self.sweep_flag = True
            chosen_direction = 'STOP'

        self.chosen_direction = chosen_direction

        self.agent_logger.info(f" self.sweep_flag:{self.sweep_flag}")
        already_swept_by_other = False
        if self.sweep_flag:
            # reset dir
            self.cell_dir = {}
            if current_mega_cell in self.swept_mega_cell_record:
                rel_path = np.array(sub_cell_travel_path[chosen_direction])
                #self.sweep_flag = False
                already_swept_by_other = True
            else:
                rel_path = np.array(sub_cell_coverage_path[chosen_direction])
            self.useless_flag = False
        else:
            rel_path = np.array(sub_cell_travel_path[chosen_direction])

        # Create the rotation matrix

        # Rotate each vector by multiplying with the rotation matrix

        def rotate_subcell(cell, times):
            subcell_rotate = {
                (0, 0): (1, 0),
                (1, 0): (1, 1),
                (1, 1): (0, 1),
                (0, 1): (0, 0),
                (0, -1): (2, 0),
                (2, 0): (1, 2),
                (1, 2): (-1, 1),
                (-1, 1): (0, -1),
            }
            for _ in range(times):
                cell = tuple(cell)
                if cell not in subcell_rotate:
                    raise ValueError(f"Missing rotation mapping for {cell}")
                cell = subcell_rotate[cell]
            return cell

        # Step 4: Get mega-cell position
        mcol, mrow = get_mega_cell(self.robot)

        # Step 5: Convert to absolute path
        abs_path = []

        for subcell in rel_path:
            rotated = rotate_subcell(subcell, rotate_steps)
            abs_cell = (mcol * 2 + rotated[0], mrow * 2 + rotated[1])
            abs_path.append(abs_cell)

        # Step 6: Store path
        self.path = abs_path

        self.agent_logger.info(
            f" self.sweep_flag:{self.sweep_flag},  current_mega_cell  in self.swept_mega_cell:{current_mega_cell in self.swept_mega_cell}")


        if current_mega_cell not in self.swept_mega_cell and self.sweep_flag:
            self.agent_logger.info(f"append current cell ({current_mega_cell}) to self.swept_mega_cell")
            self.swept_mega_cell.append(current_mega_cell)

            if current_mega_cell not in self.swept_mega_cell_record:
                self.swept_mega_cell_record.append(current_mega_cell)
                self.agent_logger.info(f"append current cell ({current_mega_cell}) to self.swept_mega_cell_record")
                self.agent_logger.info(self.swept_mega_cell_record)
            elif already_swept_by_other:
                pass
                self.sweep_flag = False
        if chosen_direction == 'STOP':
            return True

        return False
