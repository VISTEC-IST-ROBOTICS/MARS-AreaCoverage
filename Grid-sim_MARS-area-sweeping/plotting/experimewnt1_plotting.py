import os
import yaml
import matplotlib.pyplot as plt
import numpy as np

def read_yaml_files_in_folder(folder_path):
    """
    Reads all YAML files in the specified folder and returns their contents as a dictionary.

    Args:
        folder_path (str): The path to the folder containing YAML files.

    Returns:
        dict: A dictionary where keys are filenames and values are the loaded YAML content.
    """
    yaml_data = {}

    # Iterate over all files in the folder
    for file_name in os.listdir(folder_path):
        # Check if the file has a .yaml or .yml extension
        if file_name.endswith(('.yaml', '.yml')):
            file_path = os.path.join(folder_path, file_name)

            # Open and load the YAML file
            with open(file_path, 'r') as yaml_file:
                try:
                    content = yaml.safe_load(yaml_file)
                    yaml_data[file_name] = content
                except yaml.YAMLError as e:
                    print(f"Error loading {file_name}: {e}")

    return yaml_data


# Get the relative path to the 'experiment' folder
experiment_folder = os.path.join(os.path.dirname(__file__), "..", "experiment")

# Convert to an absolute path (optional but recommended)
experiment_folder = os.path.abspath(experiment_folder)

# Print the path to verify
print(f"Experiment folder path: {experiment_folder}")

# Example: Listing contents of the 'experiment' folder
if os.path.exists(experiment_folder):
    print("Contents of the 'experiment' folder:")
    alg_list = os.listdir(experiment_folder)
    for alg in alg_list:
        subfolder_path = os.path.join(experiment_folder, alg)
        comm_range_list = os.listdir(subfolder_path)
        efficiency_by_commrange = []
        time_to_complte_by_commrange = []
        range_list = ['range_5', 'range_10', 'range_20', 'range_30', 'range_40', 'range_50']
        for comm_range in range_list:
            folder_path = os.path.join(subfolder_path, comm_range,'experiment_log')

            all_yaml_files = read_yaml_files_in_folder(folder_path)
            task_eff_list = []
            step_required_list = []
            for file_name, content in all_yaml_files.items():
                print(f"\nFile: {file_name}")

                env_statistic = content['env_statistic']
                task_cells_num = env_statistic['task_cells_num']
                agents_statistic = content['agents_statistic']
                agent_id_list = agents_statistic.keys()
                sum_swept_count = 0
                max_move_list = []
                for agent_id in agent_id_list:
                    swept_count = agents_statistic[agent_id]['swept_count']
                    sum_swept_count += swept_count
                    max_move_list.append(agents_statistic[agent_id]['move_count'])
                    print(agents_statistic[agent_id])
                task_eff = task_cells_num / sum_swept_count * 100
                task_eff_list.append(task_eff)
                step_required_list.append(max(max_move_list))
            efficiency_by_commrange.append(np.mean(task_eff_list))
            time_to_complte_by_commrange.append(np.mean(step_required_list))
        plt.figure(1)
        plt.plot(efficiency_by_commrange,'-o',label=alg)
        plt.legend()
        plt.figure(2)
        plt.plot(time_to_complte_by_commrange,'-o', label=alg)
        plt.legend()

    plt.show()


else:
    print("The 'experiment' folder does not exist.")
