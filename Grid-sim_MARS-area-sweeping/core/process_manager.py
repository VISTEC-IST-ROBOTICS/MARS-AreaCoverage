import subprocess
import yaml
import time
import sys
import psutil
import logging

class ProcessBase:
    """
    Base class for managing subprocesses.
    """

    def __init__(self, command):
        """
        Initialize the process with a given command.

        :param command: The command to execute the subprocess.
        """
        self.command = command
        self.process = None

    def start(self):
        """
        Start the subprocess.
        """
        try:
            self.process = subprocess.Popen(self.command)
            logging.info(f"Started process with PID {self.process.pid}")
        except Exception as e:
            logging.error(f"Failed to start process: {e}")
            self.process = None

    def is_running(self):
        """
        Check if the process is running.

        :return: True if the process is running, False otherwise.
        """
        return self.process is not None and self.process.poll() is None

    def terminate(self):
        """
        Terminate the subprocess.
        """
        if self.is_running():
            try:
                self.process.terminate()
                self.process.wait()
                logging.info(f"Terminated process with PID {self.process.pid}")
            except Exception as e:
                logging.error(f"Failed to terminate process: {e}")


class AgentProcess(ProcessBase):
    """
    Class to manage agent subprocesses.
    """

    def __init__(self, agent_id, par_idx=0, config_path='config.yaml',use_powershell=False):
        """
        Initialize the AgentProcess.

        :param agent_id: The ID of the agent.
        :param use_powershell: Whether to use PowerShell for execution.
        """
        if use_powershell:
            command = [
                "powershell", "-Command",
                "Start-Process", "powershell",
                "-ArgumentList", f"'-NoExit', 'python', 'run_agent.py', '--agent_id', '{agent_id}',--par_idx, {par_idx})"
            ]
        else:
            command = [sys.executable, "run_agent.py", "--agent_id", str(agent_id),'--par_idx', str(par_idx),'--config',config_path]
            print(config_path)
        super().__init__(command)


class EnvironmentProcess(ProcessBase):
    """
    Class to manage the environment subprocess and associated agent processes.
    """
    def __init__(self, par_idx=0, config_path=None, use_powershell=False):
        """
        Initialize the EnvironmentProcess.

        :param par_idx: The index of the simulation run.
        :param config: Configuration dictionary.
        :param use_powershell: Whether to use PowerShell for agent execution.
        """
        #print(f'Initialized EnvironmentProcess with par_ixd: {par_idx}')
        if not config_path:
            config_path = 'config.yaml'
        command = [sys.executable, "run_environment.py", "--par_idx", str(par_idx),'--config',config_path]
        super().__init__(command)
        self.config_path = config_path
        self.config  = load_config(config_path)
        self.use_powershell = use_powershell
        self.agent_processes = []
        self.par_idx = par_idx

    def start_agents(self,use_powershell=False):
        """
        Start all agent processes as per the configuration.
        """
        agents_config =self.config.get("agents", {})
        number_of_agents =  agents_config.get("number_of_agents", 1)
        agent_id_prefix = agents_config.get("id_prefix", "agent_")
        for agent_idx in range(number_of_agents):

            agent_id = f"{agent_id_prefix}{agent_idx}"
            agent = AgentProcess(agent_id,self.par_idx,config_path=self.config_path,  use_powershell=use_powershell)
            agent.start()
            self.agent_processes.append(agent)
            logging.info(f"Agent {agent_id} of par_idx:{self.par_idx } started.")
        #time.sleep(10)

    def monitor(self):
        """
        Monitor the environment process and handle interruptions.
        """
        try:
            parent = psutil.Process(self.process.pid)
            while True:
                time.sleep(1)
                if not parent.is_running():
                    logging.warning("Environment process has stopped.")
                    break
        except psutil.NoSuchProcess:
            logging.warning("Environment process not found.")
        except KeyboardInterrupt:
            logging.info("Simulation interrupted by user.")
            self.terminate_all()

    def terminate_all(self):
        """
        Terminate all agent and environment processes.
        """
        logging.info("Terminating all processes...")
        for agent in self.agent_processes:
            agent.terminate()
        self.terminate()
        logging.info("All processes terminated.")



def setup_logging():
    """
    Setup logging configuration.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def load_config(config_path="config_.yaml"):
    """
    Load the configuration file.

    :param config_path: Path to the configuration file.
    :return: Parsed configuration dictionary.
    """
    try:
        with open(config_path, "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML: {e}")
        sys.exit(1)


def monitor_environment(env_process):
    """
    Monitor the environment process and detect if it stops running.

    :param env_process: Instance of EnvironmentProcess.
    """
    try:
        parent = psutil.Process(env_process.process.pid)
        while True:
            time.sleep(1)
            if not parent.is_running():
                logging.warning("Environment process has stopped.")
                break
    except psutil.NoSuchProcess:
        logging.warning("Environment process not found.")
    except KeyboardInterrupt:
        logging.info("Simulation interrupted by user.")