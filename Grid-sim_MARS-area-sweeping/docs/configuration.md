# Configuration Guide

This guide explains the structure and usage of `config.yaml`, the main configuration file for setting up and customizing the Multi-Agent Sweeping Simulator. Each section of this file defines settings for different parts of the simulation, including the SimEnvironment, agents, communication, and UI options. This configuration-based design allows for flexible and easily adjustable setups.

---

## 1. Overview

The `config.yaml` file allows you to control key simulation parameters without modifying the code. You can adjust:
- **Grid/SimEnvironment settings**: Define the dimensions, obstacles, and other environment properties.
- **Agent settings**: Configure each agent’s unique properties, such as starting position and behavior.
- **Communication settings**: Set up the server port for agent communication.
- **UI settings**: Customize the visualization if running the simulation with a UI.

---

## 2. Configuration Sections

### 2.1 SimEnvironment Settings
These settings define the grid or environment in which the agents operate.

```yaml
grid:
  rows: 10               # Number of rows in the grid
  cols: 10               # Number of columns in the grid
  obstacles:             # Optional list of obstacles in the environment
    - position: [3, 5]   # Coordinates of the obstacle
    - position: [7, 2]
  dynamic_elements:      # Optional list of elements that change over time
    - type: "moving_obstacle"
      initial_position: [2, 2]
      behavior: "horizontal"  # Movement pattern of the obstacle
```

- **rows** and **cols**: Dimensions of the grid, representing rows and columns.
- **obstacles**: List of static obstacles within the grid. Each obstacle has a `position` field specifying its coordinates.
- **dynamic_elements**: (Optional) Elements that change during the simulation. Define each dynamic element with:
  - **type**: Type of dynamic element (e.g., "moving_obstacle").
  - **initial_position**: Starting coordinates.
  - **behavior**: Movement or change pattern (e.g., "horizontal", "vertical").

### 2.2 Agent Settings
Define the parameters for each agent. Each agent’s configuration allows for individual starting positions and behaviors.

```yaml
agents:
  - id: "agent_1"                     # Unique identifier for the agent
    starting_position: [1, 1]         # Initial grid position
    behavior: "random_walk"           # Behavior strategy (e.g., random, sweeping)
    communication_range: 3            # Communication range in grid units
  - id: "agent_2"
    starting_position: [5, 5]
    behavior: "targeted_sweep"
    communication_range: 2
```

- **id**: Unique identifier for each agent, used for communication.
- **starting_position**: Initial position of the agent in the grid.
- **behavior**: Strategy the agent will follow. Examples include `"random_walk"` for random movement or `"targeted_sweep"` for a goal-oriented approach.
- **communication_range**: Specifies the distance (in grid units) within which the agent can communicate with other agents.

### 2.3 Communication Settings
This section defines the server’s port for agent communication.

```yaml
communication:
  server_port: 5000     # Port number for the server to listen for agent connections
  protocol: "TCP"       # Communication protocol (e.g., "TCP" or "UDP")
```

- **server_port**: Specifies the port on which the server listens for agent connections.
- **protocol**: Specifies the protocol for communication. Typically, TCP is used for reliable messaging.

### 2.4 UI Settings
These settings control the visualization parameters when the simulation is run in UI mode.

```yaml
ui:
  enabled: true               # Set to false to disable the UI
  grid_color: "#FFFFFF"       # Background color of the grid
  agent_color: "#0000FF"      # Color used for displaying agents
  obstacle_color: "#FF0000"   # Color for static obstacles
  dynamic_element_color: "#00FF00" # Color for dynamic elements
  resolution: [800, 600]      # Screen resolution of the visualization
  update_interval: 100        # UI update interval in milliseconds
```

- **enabled**: Boolean to enable or disable the UI visualization.
- **grid_color**, **agent_color**, **obstacle_color**, **dynamic_element_color**: Colors for different elements within the grid, specified in hexadecimal format.
- **resolution**: Width and height of the UI window in pixels.
- **update_interval**: Time (in milliseconds) between UI updates, which affects the visualization speed.

---

## 3. Adding Custom Parameters

You can add new parameters to `config.yaml` to support custom features or experimental setups. Here’s how:

1. **Define the Parameter**: Add the new setting under the relevant section, or create a new section if needed.
2. **Update the Code**: Modify the corresponding component (e.g., `SimEnvironment`, `Agent`) to read and use the new parameter.
3. **Example Custom Parameter**:
    - Adding a `speed` setting for agents:

      ```yaml
      agents:
        - id: "agent_1"
          starting_position: [1, 1]
          behavior: "random_walk"
          speed: 2          # Custom parameter for agent speed
      ```

    - Modify the `Agent` class to read this new `speed` parameter and adjust behavior accordingly.

---

## 4. Sample Configuration

Here’s an example `config.yaml` illustrating each section:

```yaml
grid:
  rows: 10
  cols: 10
  obstacles:
    - position: [3, 5]
    - position: [7, 2]

agents:
  - id: "agent_1"
    starting_position: [1, 1]
    behavior: "random_walk"
    communication_range: 3

  - id: "agent_2"
    starting_position: [5, 5]
    behavior: "targeted_sweep"
    communication_range: 2

communication:
  server_port: 5000
  protocol: "TCP"

ui:
  enabled: true
  grid_color: "#FFFFFF"
  agent_color: "#0000FF"
  obstacle_color: "#FF0000"
  dynamic_element_color: "#00FF00"
  resolution: [800, 600]
  update_interval: 100
```

This sample setup creates a 10x10 grid with two agents, static obstacles, and custom UI and communication settings.

---

This configuration guide provides the necessary details to customize and extend `config.yaml` for a variety of experimental setups in the Multi-Agent Sweeping Simulator.
