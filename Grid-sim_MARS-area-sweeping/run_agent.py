from core.agent_base import *
import time
import sys

import yaml
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an agent in the multi-agent system.")
    parser.add_argument("--agent_id", required=True, help="Unique identifier for the agent")
    parser.add_argument("--par_idx", type=int, default=0, help="Unique identifier for the parallel simulation")
    parser.add_argument(
        "--config",
        default="config_.yaml",
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
    par_idx = args.par_idx
    port = config.get("communication", {}).get("server_port", [5000])[par_idx]
    max_step = config.get("max_agent_run_step", -1)
    # Initialize the agent
    print(f'Agent connect to port: {port}, for par index: {par_idx}')

    agent = Agent(agent_id=args.agent_id, config=config, server_port=port, max_step=max_step)

    #time.sleep(0.5)  # Wait for other agents to initialize

    # Main loop
    print('Agent main loop')
    time.sleep(1)
    #print('======================================')
    step_count = 0

    try:
        while True:
            waiting, agent_stop = agent.update_behavior()
            #time.sleep(0.01 if waiting else 0.05)
            time.sleep(0.01 if waiting else 0.1)
            step_count += 1
            #time.sleep(1)
            if agent_stop or (agent.max_step > 0 and step_count >= agent.max_step):
                break

        agent.update_agent_status('stop')
        agent.socket.close()

    except KeyboardInterrupt:
        print("Agent terminated by user.")
    except Exception as e:
        print(f"Agent mainloop error Error: {e}")
        #traceback.print_exc()

