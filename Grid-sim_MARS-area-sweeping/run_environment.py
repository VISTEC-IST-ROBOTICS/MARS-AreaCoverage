import time
import yaml
import pygame
import threading
from core.sim_env import SimEnvironment
import datetime
import os
import argparse
import sys
from matplotlib import pyplot as plt

# Load configuration from YAML file
def load_config(config_path="config_.yaml"):
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    return config


def initialize_ui_settings(ui_config):
    """Extract UI settings from the configuration."""
    settings = {
        "enabled": ui_config.get("enabled", False),
        "background_color": pygame.Color(ui_config.get("background_color", "#FFFFFF")),
        "grid_color": pygame.Color(ui_config.get("grid_color", "#CCCCCC")),
        "obstacle_color": pygame.Color(ui_config.get("obstacle_color", "#FF0000")),
        "dynamic_element_color": pygame.Color(ui_config.get("dynamic_element_color", "#00FF00")),
        "resolution": ui_config.get("resolution", [800, 600]),
        "update_interval": ui_config.get("update_interval", 100)
    }
    return settings


def draw_grid(screen, rows, cols, cell_size, color):
    """Draws the grid lines on the screen."""
    for x in range(0, cols * cell_size, cell_size):
        pygame.draw.line(screen, color, (x, 0), (x, rows * cell_size))
    for y in range(0, rows * cell_size, cell_size):
        pygame.draw.line(screen, color, (0, y), (cols * cell_size, y))


def draw_obstacles(screen, obstacles, cell_size, color):
    """Draws obstacles on the grid."""
    for obstacle in obstacles:
        x, y = obstacle["position"]
        pygame.draw.rect(screen, color, pygame.Rect(x * cell_size, y * cell_size, cell_size, cell_size))


def draw_swept_cells(screen, swept_cells, cell_size):
    """Draws each swept cell with the color of the agent that swept it."""
    for position, color in swept_cells.copy().items():
        x, y = position
        pygame.draw.rect(screen, pygame.Color(color), pygame.Rect(x * cell_size, y * cell_size, cell_size, cell_size))


def draw_agents(screen, agent_states, cell_size):
    """Draws agents on the grid with a black outline, agent color, and a line indicating heading."""
    for agent_id, state in agent_states.items():
        x, y = state["position"]
        color = pygame.Color(state["color"])  # Retrieve agent-specific color

        # Calculate the agent's center position
        center = (x * cell_size + cell_size // 2, y * cell_size + cell_size // 2)

        # Draw the black outline first
        pygame.draw.circle(screen, pygame.Color("black"), center, cell_size // 3 + 2)

        # Draw the agent with its specific color on top of the black outline
        pygame.draw.circle(screen, color, center, cell_size // 3)

        # Draw a line to indicate heading
        heading = state["heading"]
        if heading == "up":
            end_pos = (center[0], center[1] - cell_size // 2)
        elif heading == "down":
            end_pos = (center[0], center[1] + cell_size // 2)
        elif heading == "left":
            end_pos = (center[0] - cell_size // 2, center[1])
        elif heading == "right":
            end_pos = (center[0] + cell_size // 2, center[1])
        else:
            continue  # Skip if the heading is unknown or not set

        # Draw the heading line in black
        pygame.draw.line(screen, pygame.Color("black"), center, end_pos, 2)  # Draw line with width 2


def all_cells_swept(sim_env):
    """
    Check if all cells in the grid have been swept.

    Args:
        sim_env (SimEnvironment): The simulation environment instance.

    Returns:
        bool: True if all cells are swept, False otherwise.
    """
    total_cells = sim_env.grid_dimensions[0] * sim_env.grid_dimensions[1]
    swept_cells = len(sim_env.grid["swept_cells"])

    # Check if the number of swept cells matches the total number of cells
    return swept_cells == total_cells


def all_agent_stop(sim_env):
    agents_status = sim_env.agents_state.keys()


def save_dict_to_yaml(data, file_dir=".", file_prefix="experiment_log"):
    """
    Save a dictionary to a YAML file in the given order with a unique name.

    Args:
        data (dict): The dictionary to save.
        file_dir (str): The directory where the file will be saved.
        file_prefix (str): The prefix for the unique filename.

    Returns:
        str: The full path of the saved file.
    """
    # Ensure the data is a dictionary
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary.")

    # Generate a unique filename with timestamp and UUID
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{file_prefix}_{timestamp}.yaml"
    os.makedirs(file_dir, exist_ok=True)
    filepath = os.path.join(file_dir, filename)

    # Save the dictionary to a YAML file

    with open(filepath, "w") as file:
        yaml.dump(data, file, sort_keys=False)  # Disable sorting to maintain order

    return filepath


def env_statistic(sim_env):
    total_cells = sim_env.grid_dimensions[0] * sim_env.grid_dimensions[1]
    task_cells = total_cells - len(sim_env.grid["obstacles"])
    swept_cells = len(sim_env.grid["swept_cells"])
    return {'task_cells_num': task_cells, 'swept_cells_num': swept_cells}


def main():
    # Load configuration and initialize environment
    parser = argparse.ArgumentParser(description="Run an agent in the multi-agent system.")
    parser.add_argument("--par_idx", type=int, default=0, help="Unique identifier for the parallel simulation")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to the configuration file (default: config_.yaml)"
    )
    args = parser.parse_args()

    # Load configuration
    try:
        with open(args.config, "r") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Configuration file '{args.config}' not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file '{args.config}': {e}")
        sys.exit(1)

    #config = load_config("config_.yaml")
    environment = SimEnvironment(config, args.par_idx)
    ui_settings = initialize_ui_settings(config.get("ui", {}))

    # If UI is disabled, only run the environment without visualization
    if  ui_settings["enabled"]:
        pygame.init()

    # Initialize Pygame if UI is enabled

    rows, cols = config["grid"]["rows"], config["grid"]["cols"]
    cell_size = min(ui_settings["resolution"][0] // cols, ui_settings["resolution"][1] // rows)
    file_dir = './default_data_dir'

    if "file_dir" in config:
        file_dir = config["file_dir"]
    screen_size = (cols * cell_size, rows * cell_size)
    if ui_settings["enabled"]:
        screen = pygame.display.set_mode(screen_size)
        pygame.display.set_caption("SimEnvironment Visualization")
    clock = pygame.time.Clock()

    # Start environment in a separate thread
    environment_thread = threading.Thread(target=environment.run, daemon=True)
    environment_thread.start()

    running = True
    display_idx = -1 # for objective view
    while running:
        if ui_settings["enabled"]:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        pass
                    if event.key == pygame.K_DOWN:
                        pass
                    if event.key == pygame.K_LEFT:
                        if display_idx <= -1:
                            display_idx = len(environment.agents_state)-1
                        else:
                            display_idx -= 1

                    if event.key == pygame.K_RIGHT:
                        display_idx += 1
                        if display_idx >= len(environment.agents_state):
                            display_idx = -1

                        pygame.display.set_caption("Moved Right")

            # Fill background and draw grid, obstacles, and agents
            screen.fill(ui_settings["background_color"])  # Use background color for fill
            draw_grid(screen, rows, cols, cell_size, ui_settings["grid_color"])  # Draw grid lines
            draw_obstacles(screen, config["grid"]["obstacles"], cell_size, ui_settings["obstacle_color"])
            # Draw swept cells with the agent's color

            if display_idx == -1:
                pygame.display.set_caption("Global map")
                draw_swept_cells(screen, environment.grid["swept_cells"], cell_size)
            else:
                agent_id = list(environment.agents_state.keys())[display_idx]
                pygame.display.set_caption(f"Subjective map {agent_id}")
                draw_swept_cells(screen, environment.agent_subjective_grid[agent_id]["swept_cells"], cell_size)




            draw_agents(screen, environment.agents_state, cell_size)  # Draw each agent with its specific color

            pygame.display.flip()
        clock.tick(1000 // ui_settings["update_interval"])

        all_stopped = all(agent["status"] == "stop" for agent in environment.agents_state.values()) and len(environment.agents_state) > 0

        if  all_cells_swept(environment):
            environment.simulation_status = 'end'
        if all_stopped :
            print("All agents are in 'stop' status.")

            log_data = {'env_statistic':env_statistic(environment),'agents_statistic':environment.agents_statistic }
            path = save_dict_to_yaml(log_data, file_dir)
            sweeping_progress = environment.sweeping_progress
            #plt.plot(list(sweeping_progress.keys()), list(sweeping_progress.values()))
            #plt.show()

            break
    if ui_settings["enabled"]:
        pygame.quit()


if __name__ == "__main__":
    main()
    print('runenvironment: exit...')
