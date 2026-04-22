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


# Example usage
folder_path = "C:\\Users\\mengi\\Documents\\GitHub\\grid-evn_MARS-area-sweeping\\gsr_experiment_8agent_10comrange_40x40map"  # Replace with your folder path
all_yaml_files = read_yaml_files_in_folder(folder_path)

# Print the loaded YAML data
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
    task_eff = task_cells_num/sum_swept_count*100
    task_eff_list.append(task_eff)
    step_required_list.append(max(max_move_list))

plt.hist(task_eff_list, bins=30, edgecolor='black', alpha=0.7)
plt.title('Task efficiency %')
plt.xlabel('Task efficiency %')
plt.figure()
plt.hist(step_required_list, bins=30, edgecolor='black', alpha=0.7)
plt.title('step_required_list')
plt.xlabel('step_required_list')
plt.show()