import os
import yaml
import numpy as np
import matplotlib.pyplot as plt
plt.rcParams.update({
    'font.size': 20,  # Set global font size
    'axes.titlesize': 20,  # Title font size
    'axes.labelsize': 20,  # Axes label font size
    'xtick.labelsize': 20,  # X-tick label font size
    'ytick.labelsize': 20,  # Y-tick label font size
    'legend.fontsize': 20,  # Legend font size
    'figure.titlesize': 30  # Figure title font size
})
def read_yaml_files_in_folder(folder_path):
    """
    Reads all YAML files in the specified folder and returns their contents as a dictionary.

    Args:
        folder_path (str): The path to the folder containing YAML files.

    Returns:
        dict: A dictionary where keys are filenames and values are the loaded YAML content.
    """
    yaml_data = {}
    for file_name in os.listdir(folder_path):
        if file_name.endswith(('.yaml', '.yml')):
            file_path = os.path.join(folder_path, file_name)
            with open(file_path, 'r') as yaml_file:
                try:
                    content = yaml.safe_load(yaml_file)
                    yaml_data[file_name] = content
                except yaml.YAMLError as e:
                    print(f"Error loading {file_name}: {e}")
    return yaml_data

# Initialize paths and variables
experiment_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "experiment-3"))
range_list = ['range_2','range_3','range_5', 'range_10', 'range_20', 'range_30', 'range_40', 'range_50']
#algorithms = ["GSR_SWEEP", "GSR_SWEEP_RECALL", "ANT_SWEEP", "ANT_RECALL_FILTER_SWEEP"]

#algorithms = [  "ANT_RECALL_FILTER_SWEEP",'WH_ANT_RECALL_FILTER_SWEEP']
algorithms = ["GSR_SWEEP", "GSR_SWEEP_RECALL", "ANT_SWEEP", "ANT_RECALL_FILTER_SWEEP","WH_ANT_RECALL_FILTER_SWEEP"]
Custom_lagend = {
    "GSR_SWEEP":"GSR",
    "GSR_SWEEP_RECALL":"GSR+",
    "ANT_SWEEP":"ANT",
    "ANT_RECALL_FILTER_SWEEP":"ANT+",
    'WH_ANT_RECALL_FILTER_SWEEP':'WH_ANT+'
}


results = {}

if os.path.exists(experiment_folder):
    for alg in algorithms:
        results[alg] = {'task_completeness': [], 'task_completeness_sd': [], 'time_sd': []}
        subfolder_path = os.path.join(experiment_folder, alg)
        for comm_range in range_list:
            folder_path = os.path.join(subfolder_path, comm_range, 'experiment_log')
            if os.path.exists(folder_path):
                all_yaml_files = read_yaml_files_in_folder(folder_path)
                task_completeness_list = []
                move_count_SD_list = []
                for file_name, content in all_yaml_files.items():
                    env_statistic = content['env_statistic']
                    task_cells_num = env_statistic['task_cells_num']
                    swept_cells_num = env_statistic['swept_cells_num']
                    agents_statistic = content['agents_statistic']
                    max_moves = max(agent['move_count'] for agent in agents_statistic.values())
                    task_completeness_list.append(swept_cells_num / task_cells_num * 100)
                    move_count_SD_list.append(np.std([agent['move_count'] for agent in agents_statistic.values()]))
                results[alg]['task_completeness'].append(np.mean(task_completeness_list))
                results[alg]['task_completeness_sd'].append(np.std(task_completeness_list))
                results[alg]['time_sd'].append(np.mean(move_count_SD_list))

# Convert range_list to numeric values for labeling (e.g., 'range_5' -> 5)
range_numeric = [int(r.split('_')[1]) for r in range_list]

# Plot bar graphs
x = np.arange(len(range_list))  # Range indices
bar_width = 0.2
colors = ['b', 'g', 'r', 'y']

# Task Completeness
plt.figure(figsize=(12, 6))
for i, alg in enumerate(algorithms):
    plt.bar(
        x + i * bar_width,
        results[alg]['task_completeness'],
        yerr=results[alg]['task_completeness_sd'],
        width=bar_width,
        label=Custom_lagend[alg],
        capsize=5,
    )
plt.xticks(x + bar_width * (len(algorithms) - 1) / 2, range_numeric)  # Use numeric labels
plt.xlabel("Communication Range")
plt.ylabel("Task Completeness (%)")
plt.title("Task Completeness by Communication Range")
plt.legend(loc='lower right')
plt.tight_layout()

# Standard Deviation of Agent Operating Time (Move Count)
plt.figure(figsize=(12, 6))
for i, alg in enumerate(algorithms):
    plt.bar(
        x + i * bar_width,
        results[alg]['time_sd'],
        width=bar_width,
        label=Custom_lagend[alg],
        capsize=5,
    )
plt.xticks(x + bar_width * (len(algorithms) - 1) / 2, range_numeric)  # Use numeric labels
plt.xlabel("Communication Range")
plt.ylabel("Standard Deviation of Operating Time (steps)")
plt.title("Standard Deviation of Agent Operating Time by Communication Range")
plt.legend()
plt.tight_layout()

plt.show()
