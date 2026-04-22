
from core.process_manager import *

def main():
    setup_logging()
    config_path = 'config_.yaml'
    config = load_config(config_path)

    repeat_simulation = config.get("repeat_simulation", 1)
    parallel_simulation = config.get("parallel_simulation", 1)
    delay_between_processes = config.get("delay", 1)
    use_powershell = config.get("use_powershell", False)

    for repreat_idx in range(repeat_simulation):
        env_process_list = []
        print(f"{repreat_idx} of repeat_simulation")

        for par_idx in range(parallel_simulation):
            logging.info(f"Starting simulation {par_idx + 1}/{repeat_simulation}")

            # Initialize and start environment process
            env_process = EnvironmentProcess(par_idx, config_path=config_path, use_powershell=use_powershell)
            env_process.start()

            # Start and monitor agents

            env_process_list.append(env_process)
        time.sleep(delay_between_processes)  # Allow environment to initialize
        for env_process in env_process_list:

            env_process.start_agents()

        while True:
            all_stopped = all(not env_process.is_running() for env_process in env_process_list)
            if all_stopped:

                pass
            #break
            #time.sleep(1)


if __name__ == "__main__":
    main()
