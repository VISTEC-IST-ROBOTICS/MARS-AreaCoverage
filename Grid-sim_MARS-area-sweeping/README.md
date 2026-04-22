# Multi-Agent Sweeping Simulator

A modular, configurable, and decentralized simulator for multi-agent systems. This project supports independent, configurable agents operating in a shared environment with optional visualization. Designed to facilitate research and development in multi-agent communication, behavior customization, and decentralized systems.

---

## Features

- **Decentralized Communication**: Agents communicate indirectly through a broker-like environment, simulating a decentralized network.
- **Modular Architecture**: Each component is independently designed, allowing easy replacement or extension of agents, environments, and visualizations.
- **Interchangeability**: Researchers and developers can easily implement their own agents, environment types, or UI visualizations.
- **Configurable Simulation**: Set up agents, environment parameters, and visualization settings using a configuration file.

## Project Structure

```plaintext
project-repo/
├── run_simulation.py          # Main entry point for running the simulation (with or without UI)
├── config.yaml                # Main configuration file for agents, environment, and UI
├── core/                      # Core components for simulation
│   ├── environment_broker.py  # Environment and message broker
│   ├── agent_base.py          # Base Agent class with communication methods
│   └── utils.py               # Utility functions for serialization, configuration loading
├── ui/                        # Visualization components
│   ├── visualization.py       # Main UI component using pygame
│   └── ui_helpers.py          # Helper functions for UI rendering and settings
└── docs/                      # Documentation
    ├── architecture.md        # Detailed architecture and design principles
    ├── setup.md               # Setup and installation instructions
    ├── usage.md               # Usage guide for running in headless/UI modes
    ├── configuration.md       # Configuration guide for modifying config.yaml
    ├── extending.md           # Guide for extending components (agents, environments, etc.)
    └── config_samples/        # Sample configuration files
        ├── basic_sweep.yaml   # Config for a basic sweeping task
        └── complex_env.yaml   # Config for a complex dynamic environment
```

## Getting Started

### Prerequisites

Ensure you have the following installed:
- Python 3.8+
- `pygame` (if using the visualization)

To install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Simulation

#### 1. With UI (Visual Mode)

To run the simulation with a graphical display:
```bash
python run_simulation.py
```

#### 2. Headless Mode

To run the simulation in headless mode (without visualization):
```bash
python run_simulation.py --headless
```

This mode is useful for running large-scale tests or collecting data without the overhead of a UI.

---

## Configuration

The configuration file `config.yaml` allows full customization of the simulation parameters:
- **Grid Settings**: Define the grid dimensions, obstacles, and any dynamic elements.
- **Agent Settings**: Set up agent parameters, including starting position, behavior types, and communication options.
- **UI Settings**: Customize the visualization appearance, such as colors, resolution, and grid display options.

For a detailed guide, see the [Configuration Guide](docs/configuration.md).

## Documentation

- [Architecture](docs/architecture.md): Detailed explanation of the system's modular architecture, designed for interchangeability.
- [Setup](docs/setup.md): Step-by-step installation and setup instructions.
- [Usage](docs/usage.md): Instructions on running the simulation in various modes.
- [Configuration Guide](docs/configuration.md): Guide to modifying `config.yaml` for custom setups.
- [Extending the Project](docs/extending.md): Instructions for implementing custom agents, environments, and UI components.

## Extending the Project

The simulator is designed for easy extension:
- **Agents**: Implement custom behaviors, communication methods, or decision-making logic.
- **Environment**: Create new types of environments or modify the broker behavior for custom communication needs.
- **UI**: Replace or expand the `pygame` visualization for alternative or additional displays.

For more information, see [Extending the Project](docs/extending.md).

---

## Sample Configurations

Explore example configurations in `docs/config_samples/`:
- **basic_sweep.yaml**: Basic sweeping task with two agents in a static environment.
- **complex_env.yaml**: A larger, dynamic environment with more agents and obstacles.

## License

This project is open-source and available for modification and use under the MIT License.

---

## Contributing

Contributions are welcome! Please see our [Contribution Guidelines](docs/contributing.md) (if applicable) for details.
