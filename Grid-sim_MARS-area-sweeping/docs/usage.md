# Usage Guide

This guide explains how to run the Multi-Agent Sweeping Simulator, with options for running in headless mode (no UI) or with UI visualization. It also covers available command-line arguments and expected outputs.

---

## 1. Basic Usage

To quickly start the simulation, use the following command:

```bash
python run_simulation.py
```

This command launches the simulation with the UI enabled, displaying the SimEnvironment and agents. If the setup and configuration are correct, you should see the grid, any specified obstacles, and agents moving according to their defined behaviors.

---

## 2. Running in Headless Mode

Headless mode allows you to run the simulation without the UI, which is useful for data collection or large-scale tests without visualization overhead. To run in headless mode, use:

```bash
python run_simulation.py --headless
```

In headless mode, the simulation runs entirely in the background. Console logs provide updates on the agents’ activities, environment changes, and communication events if logging is enabled.

### Expected Console Output (Headless Mode)
- **Agent Initialization**: Logs indicating each agent’s initial setup and position.
- **Action Updates**: Periodic logs showing agent actions, such as moving or sending messages.
- **Simulation Progress**: General progress messages or summaries after each time step.

---

## 3. Running with UI

To run the simulation with visualization, simply omit the `--headless` flag:

```bash
python run_simulation.py
```

This command opens a UI window displaying the current state of the SimEnvironment, including grid cells, agents, and obstacles. The UI updates regularly based on the `update_interval` defined in `config.yaml`.

### UI Elements
- **Grid**: Displays rows and columns based on `grid` settings in `config.yaml`.
- **Agents**: Each agent is represented by a colored icon or shape on the grid.
- **Obstacles**: Static and dynamic obstacles appear based on their positions in the configuration file.

### Expected UI Behavior
- Agents should move across the grid according to their behaviors.
- Obstacles and dynamic elements (if configured) should appear as specified.
- If any issues arise (e.g., agents not moving), check the console for error messages.

---

## 4. Command-Line Arguments

The following command-line arguments are supported:

- `--headless`: Run the simulation without UI visualization. Useful for non-visual testing and data collection.
- `--config <path>`: Specify a custom path to `config.yaml` if using an alternate configuration file.
  - **Example**:
    ```bash
    python run_simulation.py --config custom_config.yaml
    ```
- `--log`: Enable logging for detailed console outputs during simulation (if not enabled by default).
  - **Example**:
    ```bash
    python run_simulation.py --log
    ```

---

## 5. Example Scenarios

### Example 1: Basic Headless Run
This command runs the simulation in headless mode using the default `config.yaml`:

```bash
python run_simulation.py --headless
```

### Example 2: Running with Custom Configuration
If you have a custom configuration file (e.g., `config_samples/complex_env.yaml`), specify it with the `--config` argument:

```bash
python run_simulation.py --config docs/config_samples/complex_env.yaml
```

### Example 3: Running with Logging Enabled
To collect detailed logs of the simulation, use the `--log` argument:

```bash
python run_simulation.py --log
```

---

## 6. Expected Outputs

Depending on the mode and configuration, outputs include:

- **Console Logs**: In headless mode, console logs will provide details on agent actions, communications, and environment changes. Logging can be enabled or configured for more detailed output.
- **UI Updates**: In UI mode, the simulation window should update regularly, reflecting agent movements, obstacle positions, and any configured dynamic elements.

### Sample Console Output
In headless mode or with logging enabled, you may see output like the following:

```plaintext
[INFO] Agent agent_1 initialized at position [1, 1]
[INFO] Agent agent_1 moving to position [1, 2]
[INFO] Agent agent_2 requesting assistance from agent_1 at [5, 5]
[INFO] Simulation step 10 complete
```

---

This guide covers all necessary commands and expected outcomes for running the Multi-Agent Sweeping Simulator. For setup details, see the [Setup Guide](setup.md). To further customize the simulation, refer to the [Configuration Guide](configuration.md).
