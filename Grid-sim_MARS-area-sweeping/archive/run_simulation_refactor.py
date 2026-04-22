import subprocess
import yaml
import time
import os
import sys
import psutil
import logging


class AgentProcess:
    """
    A class to manage agent subprocesses with configurable execution methods.
    """
    def __init__(self, agent_id, use_powershell=False):
        """
        Initialize the AgentProcess.

        :param agent_id: The ID of the agent.
        :param use_powershell: Whether to use PowerShell for execution.
        """
        self.agent_id = agent_id
        self.use_powershell = use_powershell
        self.process = None

    def start(self):
        """
        Start the agent process.
        """
        if self.use_powershell:
            command = [
                "powershell", "-Command", "Start-Process", "powershell",
                "-ArgumentList", f"'-NoExit', 'python', 'run_agent.py', --agent_id, '{self.agent_id}'"
            ]
        else:
            command = [sys.executable, "run_agent.py", "--agent_id", self.agent_id]

        try:
            self.process = subprocess.Popen(command)
            logging.info(f"Started agent {self.agent_id} with PID {self.process.pid}")
        except Exception as e:
            logging.error(f"Failed to start agent {self.agent_id}: {e}")
            self.process = None

    def is_running(self):
        """
        Check if the agent process is still running.

        :return: True if the process is running, False otherwise.
        """
        return self.process is not None and self.process.poll() is None

    def terminate(self):
        """
        Terminate the agent process.
        """
        if self.is_running():
            self.process.terminate()
            logging.info(f"Terminated agent {self.agent_id} with PID {self.process.pid}")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def load_config(config_path="config_.yaml"):
    try:
        with open(config_path, "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML: {e}")
        sys.exit(1)


def start_environment():
    """
    Start the environment process.
    """
    try:
        process = subprocess.Popen([sys.executable, "run_environment.py"])
        logging.info(f"Started environment with PID {process.pid}")
        return process
    except Exception as e:
        logging.error(f"Failed to start environment: {e}")
        sys.exit(1)


def terminate_process(process):
    """
    Terminate a single process.
    """
    if process and process.poll() is None:
        process.terminate()
        logging.info(f"Terminated process PID {process.pid}")


def monitor_environment(env_process):
    """
    Monitor the environment process and detect if it stops running.
    """
    try:
        parent = psutil.Process(env_process.pid)
        while True:
            time.sleep(1)
            if not parent.is_running():
                logging.warning("Environment process has stopped.")
                break
    except psutil.NoSuchProcess:
        logging.warning("Environment process not found.")
    except KeyboardInterrupt:
        logging.info("Simulation interrupted by user.")


def main():
    setup_logging()
    config = load_config()

    repeat_simulation = config.get("repeat_simulation", 1)
    delay_between_processes = config.get("delay", 1)
    use_powershell = config.get("use_powershell", False)

    for repeat in range(repeat_simulation):
        logging.info(f"Starting simulation {repeat + 1}/{repeat_simulation}")

        # Start environment process
        env_process = start_environment()

        time.sleep(delay_between_processes)  # Allow environment to initialize

        # Start agent processes
        agent_processes = []
        for agent_config in config.get("agents", []):
            agent_id = str(agent_config.get("id"))
            agent = AgentProcess(agent_id, use_powershell=use_powershell)
            agent.start()
            agent_processes.append(agent)

        try:
            monitor_environment(env_process)
        except KeyboardInterrupt:
            logging.info("Shutting down simulation...")
            break

        # Clean up
        for agent in agent_processes:
            agent.terminate()
        terminate_process(env_process)
        logging.info("All processes terminated.")


if __name__ == "__main__":
    main()
