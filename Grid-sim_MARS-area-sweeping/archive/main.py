import pygame
import sys
import random
import math
from agent_v2 import Agent  # Import the Agent class
import numpy as np
# Initialize pygame
pygame.init()
num_agents = 2  # You can change this to test with different numbers of agents
# Set up display
GRID_SIZE = 20  # Size of each cell in pixels
rows, cols = 40, 40  # 20x20 grid
width, height = cols * GRID_SIZE, rows * GRID_SIZE  # Screen size
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Multi-Agent Grid")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DEFAULT_COLOR = WHITE

# Define constants for update intervals
UPDATE_INTERVAL = 50  # Interval in milliseconds (e.g., 500ms or 0.5 seconds)
UPDATE_EVENT = pygame.USEREVENT + 1  # Custom event ID for the timer

# Set up the timer event to trigger every UPDATE_INTERVAL milliseconds
pygame.time.set_timer(UPDATE_EVENT, UPDATE_INTERVAL)

# Predefined color palette
color_palette = [
    (255, 0, 0),  # Red
    (0, 255, 0),  # Green
    (0, 0, 255),  # Blue
    (255, 255, 0),  # Yellow
    (255, 165, 0),  # Orange
    (128, 0, 128),  # Purple
    (0, 255, 255),  # Cyan
    (255, 192, 203)  # Pink
]

# Define state colors
OBSTRUCT_COLOR = BLACK
UNSWEEP_COLOR = WHITE

# Initialize the grid with tuples of (state, color)
# By default, cells are 'UNSWEEP' and colored white
grid = [[('UNSWEEP', UNSWEEP_COLOR) for _ in range(cols)] for _ in range(rows)]


# Generate unique position for agents
def generate_unique_position(occupied_positions):
    """Generate a unique position that is not occupied."""
    while True:
        pos = (random.randint(0, cols - 1), random.randint(0, rows - 1))
        if pos not in occupied_positions:
            occupied_positions.add(pos)
            return pos


# Generate a random heading direction
def generate_random_heading():
    """Generate a random heading as a vector."""
    direction_vectors = {
        0: (1, 0),  # Right
        1: (0, -1),  # Up
        2: (-1, 0),  # Left
        3: (0, 1)  # Down
    }
    random_heading_key = random.randint(0, 3)
    return direction_vectors[random_heading_key]


# Function to initialize agents
def initialize_agents(num_agents):
    """Initialize a list of Agent objects with unique positions and random headings."""
    agents = []
    occupied_positions = set()

    for i in range(num_agents):
        pos = generate_unique_position(occupied_positions)

        # Choose color from palette or randomize if palette is exceeded
        if i < len(color_palette):
            color = color_palette[i]
        else:
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

        heading = generate_random_heading()
        agent = Agent(pos=pos, heading=heading, color=color)
        agents.append(agent)

    return agents


# Initialize agents

agents = initialize_agents(num_agents)

# Function to get the observation kernel (3x3) around an agent
# Mapping for rotations based on heading
HEADING_ROTATIONS = {
    (1, 0): 1,  # Right
    (0, -1): 0,  # Up
    (-1, 0): 3,
    (0, 1): 2
}


def get_observation(position, heading):
    """Return a rotated 3x3 observation kernel around the agent's position based on heading."""
    x, y = position
    observation = []

    # Create the initial 3x3 kernel around the agent's position
    for dy in range(-1, 2):
        row = []
        for dx in range(-1, 2):
            nx, ny = x + dx, y + dy
            # Check boundaries
            if 0 <= nx < cols and 0 <= ny < rows:
                row.append(grid[ny][nx][0])  # Append cell state only
            else:
                row.append('OBSTRUCT')  # Interpret out-of-bounds as 'OBSTRUCT'
        observation.append(row)

    # Convert the observation to a numpy array for rotation
    observation = np.array(observation)

    # Rotate based on the agent's heading
    rotations = HEADING_ROTATIONS[heading]
    rotated_observation = np.rot90(observation, k=rotations)

    return tuple(map(tuple, rotated_observation))  # Convert back to tuple of tuples for consistency



# Draw grid
def draw_grid():
    """Draw the grid on the screen with colors based on cell states."""
    for row in range(rows):
        for col in range(cols):
            cell_state, cell_color = grid[row][col]
            rect = pygame.Rect(col * GRID_SIZE, row * GRID_SIZE, GRID_SIZE, GRID_SIZE)
            pygame.draw.rect(screen, cell_color, rect)  # Fill cell with state color
            pygame.draw.rect(screen, BLACK, rect, 1)  # Draw cell border


# Draw an individual agent
def draw_agent(screen, agent):
    """Draw the agent on the screen using pygame."""
    # Calculate agent's position in pixels
    x = agent.pos[0] * GRID_SIZE + GRID_SIZE // 2
    y = agent.pos[1] * GRID_SIZE + GRID_SIZE // 2
    pygame.draw.circle(screen, agent.color, (x, y), GRID_SIZE // 2 - 2)

    # Draw heading line based on the agent's heading vector
    line_length = GRID_SIZE // 2
    end_x = x + int(line_length * agent.heading[0])
    end_y = y + int(line_length * agent.heading[1])
    pygame.draw.line(screen, BLACK, (x, y), (end_x, end_y), 2)



def sweep_cell(position, agent_color):
    """Update the cell state to 'SWEEP' and color it with the agent's color."""
    x, y = position
    # Check if the cell is within the grid and is in the 'UNSWEEP' state
    if 0 <= x < cols and 0 <= y < rows and grid[y][x][0] == 'UNSWEEP':
        grid[y][x] = ('SWEEP', agent_color)

# Main update and draw function
def update_function():



    for agent in agents:
        observation = get_observation(agent.pos,agent.heading)
        sweep_pos = agent.pos
        action = agent.action(observation)
        if action == 'SWEEP':
            sweep_cell(sweep_pos, agent.color)



    draw_grid()  # Draw the grid
    for agent in agents:



        draw_agent(screen, agent)  # Draw each agent
    pygame.display.flip()  # Update display


# Main game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == UPDATE_EVENT:
            # Call the update function when the timer event occurs
            update_function()

# Quit pygame
pygame.quit()
sys.exit()
