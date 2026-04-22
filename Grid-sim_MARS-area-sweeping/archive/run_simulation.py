import subprocess
import yaml
import time
import os
import sys
import psutil

def load_config(config_path="config_.yaml"):
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    return config


def main():
    # Load the configuration
    config = load_config("../config_.yaml")

    # Start the environment process in a new PowerShell window
    repeat_simulation = 1
    if 'repeat_simulation' in config:
        repeat_simulation = config['repeat_simulation']

    for repeat_simulation_count in range(repeat_simulation):
        env_process = subprocess.Popen(
            [sys.executable, 'run_environment.py'],
        )

        time.sleep(1)
        # Start each agent in a separate PowerShell window
        agent_processes = []
        print('initialize agents')
        for agent_config in config["agents"]:
            agent_id = agent_config["id"]
            print('agent_id:', agent_id)

            # Using a separate variable for the command to improve readability
            #for powershell pop-up
            command = [
                "powershell", "-Command", "Start-Process", "powershell",
                "-ArgumentList", f"'-NoExit', 'python', 'run_agent.py', '{agent_id}'"
            ]
            # for no pop-up
            command = [
                sys.executable,  # This uses the current Python interpreter
                "run_agent.py",  # The script to be executed
                agent_id  # The agent ID passed as an argument
            ]

            process = subprocess.Popen(command)
            agent_processes.append(process)

        # Keep the main script running and monitor for exit signals
        try:
            while True:
                time.sleep(1)  # Keep the main process alive and responsive
                try:
                    # Use psutil to get the process object of the parent
                    parent = psutil.Process(env_process.pid)
                    # Get all child processes
                    children = parent.children(recursive=True)
                    # Check if any child is still running
                    #print( any(child.is_running() for child in children))
                except psutil.NoSuchProcess:
                    print('No susch process')
                    os.system("taskkill /F /IM powershell.exe /T")
                    break
            # The parent process no
        except KeyboardInterrupt:
            print("Shutting down simulation...")

            # Use taskkill to forcefully close all PowerShell processes running the scripts
            os.system("taskkill /F /IM powershell.exe /T")

            print("All processes terminated.")


if __name__ == "__main__":
    main()
