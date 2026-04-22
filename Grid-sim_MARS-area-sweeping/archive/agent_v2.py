# agent.py
import networkx as nx
from critical_check import *
class Agent:
    def __init__(self, pos, heading=(1, 0), color='white'):
        self.pos = pos  # Position as a tuple (x, y)
        #self.pos = (0,1)

        self.color = color  # Store color as a simple attribute
        self.heading = heading  # Default heading (x, y)
        #self.heading = (-1, 0)
        self.critical_record = []
    def turn_left(self):
        """Turn the agent left (counterclockwise)."""
        directions = [(1, 0), (0, -1), (-1, 0), (0, 1)]  # Right, Up, Left, Down
        current_index = directions.index(self.heading)
        self.heading = directions[(current_index + 1) % len(directions)]

    def turn_right(self):
        """Turn the agent right (clockwise)."""
        directions = [(1, 0), (0, -1), (-1, 0), (0, 1)]  # Right, Up, Left, Down
        current_index = directions.index(self.heading)
        self.heading = directions[(current_index - 1) % len(directions)]

    def _turn_left(self,heading):
        """Turn the agent left (counterclockwise)."""
        directions = [(1, 0), (0, -1), (-1, 0), (0, 1)]  # Right, Up, Left, Down
        current_index = directions.index(heading)
        return directions[(current_index + 1) % len(directions)]

    def _turn_right(self,heading):
        """Turn the agent right (clockwise)."""
        directions = [(1, 0), (0, -1), (-1, 0), (0, 1)]  # Right, Up, Left, Down
        current_index = directions.index(heading)
        return  directions[(current_index - 1) % len(directions)]
    def _turn_back(self,heading):
        """Turn the agent right (clockwise)."""
        directions = [(1, 0), (0, -1), (-1, 0), (0, 1)]  # Right, Up, Left, Down
        current_index = directions.index(heading)
        return  directions[(current_index - 2) % len(directions)]

    def action(self, observation):
        """Return heading as the agent's action based on observation."""

        front = observation[0][1]
        left = observation[1][0]
        right  = observation[1][2]
        back = observation[2][1]
        #print(left)

        critical_key = self.critical_key(observation)
        #print(observation)
        is_critical = critical_check(critical_key) == 'critical'
        if is_critical:
            self.critical_record.append(self.pos)

        left_heading = self._turn_left(self.heading)
        left_pos = self._move(self.pos,left_heading)

        front_heading = self.heading
        front_pos = self._move(self.pos, front_heading)

        right_heading = self._turn_right(self.heading)
        right_pos = self._move(self.pos, right_heading)

        back_heading = self._turn_back(self.heading)
        back_pos = self._move(self.pos, back_heading)

        if left == 'UNSWEEP' and left_pos not in self.critical_record:
            self.turn_left()
            self.move()
        elif front == 'UNSWEEP'  and front_pos not in self.critical_record:
            self.move()
        elif right == 'UNSWEEP'  and right_pos not in self.critical_record:
            self.turn_right()
            self.move()
        elif back == 'UNSWEEP'  and back_pos not in self.critical_record:
            self.turn_right()
            self.turn_right()
            self.move()
        elif left == 'UNSWEEP':
            self.turn_left()
            self.move()
        elif front == 'UNSWEEP':
            self.move()
        elif right == 'UNSWEEP':
            self.turn_right()
            self.move()
        elif back == 'UNSWEEP':
            self.turn_right()
            self.turn_right()
            self.move()

        if is_critical:

            return None
        else:
            return 'SWEEP'

    def critical_key(self,observation):
        key = []
        for i in range(3):
            for j in range(3):
                if i*3+j == 4:
                    key.append(4)
                elif observation[i][j] == 'UNSWEEP':
                    key.append(i*3+j)
        return tuple(key)
    def move(self):
        """Update position based on heading."""
        self.pos = (self.pos[0] + self.heading[0], self.pos[1] + self.heading[1])
    def _move(self,pos,heading):
        """Update position based on heading."""
        return (pos[0] + heading[0], pos[1] + heading[1])
