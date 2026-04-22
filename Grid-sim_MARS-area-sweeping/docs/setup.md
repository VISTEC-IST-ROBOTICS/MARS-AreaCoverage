# Setup Guide

This guide provides step-by-step instructions to set up the Multi-Agent Sweeping Simulator, including installing dependencies, configuring `config.yaml`, and verifying the installation.

---

## 1. Prerequisites

### System Requirements
- **Python**: Version 3.8 or higher
- **Operating System**: Compatible with Windows, macOS, and Linux
- **Network Configuration**: If running with communication enabled, ensure that the specified server port in `config.yaml` is open for communication.

### Required Libraries
The primary dependency for this project is `pygame`, which is used for visualization (optional). Additional dependencies are listed in `requirements.txt`.

---

## 2. Installation Steps

### Step 1: Clone the Repository
First, clone the project repository to your local machine.

```bash
git clone https://github.com/your-username/multi-agent-sweeping-simulator.git
cd multi-agent-sweeping-simulator
```

### Step 2: Create a Virtual Environment (Recommended)
It’s recommended to use a virtual environment to manage dependencies.

```bash
python3 -m venv env
source env/bin/activate  # For macOS/Linux
env\Scripts\activate     # For Windows
```

### Step 3: Install Dependencies
Install the required dependencies from `requirements.txt`.

```bash
pip install -r requirements.txt
```

### Step 4: Install `pygame` (if not installed)
If `pygame` is not included in `requirements.txt`, install it separately.

```bash
pip install pygame
```

---

## 3. Configuring `config.yaml`

1. **Locate the File**: Open `config.yaml` in the project root directory.
2. **Set Up Initial Parameters**:
   - Adjust the **SimEnvironment settings** (e.g., grid size, obstacles).
   - Configure **Agent settings** for initial positions and behavior.
   - Define the **Communication settings** (e.g., server port).
   - Customize **UI settings** if running the simulation with visualization.
3. **Refer to the Configuration Guide**: For a full breakdown of parameters, refer to [Configuration Guide](configuration.md).

---

## 4. Verification

### Step 1: Run a Basic Test
Run the following command to verify that the project setup is complete and dependencies are correctly installed:

```bash
python run_simulation.py --headless
```

This will run the simulation in headless mode, without the UI. If the setup is successful, you should see logs or console outputs confirming that the agents are running in the SimEnvironment.

### Step 2: Test with UI (Optional)
To test the setup with the UI enabled, run:

```bash
python run_simulation.py
```

This should launch a window displaying the grid and any configured agents or obstacles. If you encounter issues, ensure `pygame` was installed successfully.

---

## 5. Troubleshooting

- **Port Conflicts**: If the specified server port is already in use, update the `server_port` in `config.yaml` under the `communication` section.
- **Dependency Errors**: If you encounter dependency installation errors, ensure your Python version is compatible and that you’re using a virtual environment.

---

With these steps completed, the Multi-Agent Sweeping Simulator should be fully set up and ready to run. For additional information on running and customizing the simulation, see the [Usage Guide](usage.md).

