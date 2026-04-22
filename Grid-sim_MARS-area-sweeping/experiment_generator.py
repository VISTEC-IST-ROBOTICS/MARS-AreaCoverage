import os
import yaml
from itertools import product

'''
experiment/
└── ANT_RECALL_FILTER_SWEEP/
    ├── range_10/
    │   ├── config_.yaml
    │   └── experiment_log/
    ├── range_20/
    │   ├── config_.yaml
    │   └── experiment_log/
    ├── range_30/
    │   ├── config_.yaml
    │   └── experiment_log/
    ├── range_40/
    │   ├── config_.yaml
    │   └── experiment_log/
    └── range_50/
        ├── config.yaml
        └── experiment_log/

'''
# Base configuration template
base_config = {
    "grid": {
        "rows": 50,
        "cols": 50,
        "obstacles": []
    },
    "agents": {
        "starting_position": "random",
        "behavior": "ANT_RECALL_FILTER_SWEEP",  # Placeholder, will be updated
        "color": "orange",
        "communication_range": 10,  # Placeholder, will be updated
        "number_of_agents": 8,
        "id_prefix": "agent_",
        "color_list": ["blue", "orange", "green", "pink", "brown", "purple", "yellow"]
    },
    "communication": {
        "server_port": [5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010, 5011, 5012],
        "protocol": "TCP"
    },
    "ui": {
        "enabled": False,
        "background_color": "#FFFFFF",
        "grid_color": "#CCCCCC",
        "obstacle_color": "black",
        "agent_color": "#0000FF",
        "dynamic_element_color": "#00FF00",
        "resolution": [1000, 1000],
        "update_interval": 100
    },
    "file_dir": "./experiment_log",  # Placeholder, will be updated
    "max_agent_run_step": 10000,
    "repeat_simulation": 10,  # Placeholder, will be updated
    "parallel_simulation": 10  # Placeholder, will be updated
}

# Parameters to vary
behaviors = ["GSR_SWEEP", "GSR_SWEEP_RECALL", "ANT_SWEEP", "ANT_RECALL_FILTER_SWEEP","WH_ANT_RECALL_FILTER_SWEEP"]
#behaviors = ["ANT_RECALL_FILTER_SWEEP", "WH_ANT_RECALL_FILTER_SWEEP"]
communication_ranges = [2,3,5,10,20,30,40,50]
repeat_simulation = 10
parallel_simulation = 10

# Base directory for experiments
base_dir = "experiment-3"
os.makedirs(base_dir, exist_ok=True)

# Generate configuration files
for behavior, communication_range in product(behaviors, communication_ranges):
    # Create directory structure for behavior and communication range
    behavior_dir = os.path.join(base_dir, behavior)
    range_dir = os.path.join(behavior_dir, f"range_{communication_range}")
    experiment_log_dir = os.path.join(range_dir, "experiment_log")
    os.makedirs(experiment_log_dir, exist_ok=True)

    # Create a copy of the base configuration
    config = base_config.copy()

    # Update varied parameters
    config["agents"]["behavior"] = behavior
    config["agents"]["communication_range"] = communication_range
    config["repeat_simulation"] = repeat_simulation
    config["parallel_simulation"] = parallel_simulation

    # Set file_dir to the experiment_log directory
    config["file_dir"] = experiment_log_dir

    # Save the configuration file in the range directory
    config_filename = os.path.join(range_dir, "config.yaml")
    with open(config_filename, "w") as file:
        yaml.dump(config, file)

    print(f"Generated: {config_filename}")

print("All configuration files have been generated.")
