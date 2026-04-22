import os
import yaml
import numpy as np
import matplotlib.pyplot as plt

# -------------------------------------------------
# IEEE-style font configuration (UNCHANGED)
# -------------------------------------------------
plt.rcParams.update({
    'font.size': 20,
    'axes.titlesize': 20,
    'axes.labelsize': 20,
    'xtick.labelsize': 20,
    'ytick.labelsize': 20,
    'legend.fontsize': 20,
    'figure.titlesize': 30
})

# -------------------------------------------------
# YAML reader (UNCHANGED)
# -------------------------------------------------
def read_yaml_files_in_folder(folder_path):
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


# -------------------------------------------------
# Experiment configuration (UNCHANGED)
# -------------------------------------------------
experiment_folder = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "experiment-3")
)

range_list = ['range_2','range_3','range_5','range_10','range_20','range_30','range_40','range_50']

algorithms = [
    "GSR_SWEEP",
    "GSR_SWEEP_RECALL",
    "ANT_SWEEP",
    "ANT_RECALL_FILTER_SWEEP",
]

# -------------------------------------------------
# Label renaming (UNCHANGED)
# -------------------------------------------------
Custom_lagend = {
    "ANT_SWEEP": "Baseline",
    "ANT_RECALL_FILTER_SWEEP": "Baseline+",
    "GSR_SWEEP": "S-Baseline",
    "GSR_SWEEP_RECALL": "S-Baseline+",
}

# -------------------------------------------------
# Result storage (UNCHANGED)
# -------------------------------------------------
results = {}

if os.path.exists(experiment_folder):
    for alg in algorithms:
        results[alg] = {
            'efficiency': [],
            'efficiency_sd': [],
            'time': [],
            'time_sd': []
        }

        subfolder_path = os.path.join(experiment_folder, alg)

        for comm_range in range_list:
            folder_path = os.path.join(subfolder_path, comm_range, 'experiment_log')

            if os.path.exists(folder_path):
                all_yaml_files = read_yaml_files_in_folder(folder_path)

                task_eff_list = []
                step_required_list = []

                for file_name, content in all_yaml_files.items():
                    env_statistic = content['env_statistic']
                    task_cells_num = env_statistic['task_cells_num']

                    agents_statistic = content['agents_statistic']
                    sum_swept_count = sum(
                        agent['swept_count'] for agent in agents_statistic.values()
                    )
                    max_moves = max(
                        agent['move_count'] for agent in agents_statistic.values()
                    )

                    task_eff_list.append(task_cells_num / sum_swept_count * 100)
                    step_required_list.append(max_moves)

                results[alg]['efficiency'].append(np.mean(task_eff_list))
                results[alg]['efficiency_sd'].append(np.std(task_eff_list))
                results[alg]['time'].append(np.mean(step_required_list))
                results[alg]['time_sd'].append(np.std(step_required_list))


# -------------------------------------------------
# X-axis preparation (UNCHANGED)
# -------------------------------------------------
range_numeric = [int(r.split('_')[1]) for r in range_list]


# =================================================
# TASK EFFICIENCY — LINE PLOTS (UPPER / LOWER)
# =================================================
fig, axs = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

# ---------- Upper: Baseline / Baseline+ ----------
baseline_algs = ["ANT_SWEEP", "ANT_RECALL_FILTER_SWEEP"]
for alg in baseline_algs:
    axs[0].errorbar(
        range_numeric,
        results[alg]['efficiency'],
        yerr=results[alg]['efficiency_sd'],
        marker='o',
        linestyle='-',
        capsize=5,
        label=Custom_lagend[alg]
    )

axs[0].set_ylabel("Task Efficiency (%)")
axs[0].set_title("Baseline Methods")
axs[0].legend()
axs[0].grid(alpha=0.3)

# ---------- Lower: S-Baseline / S-Baseline+ ----------
sbaseline_algs = ["GSR_SWEEP", "GSR_SWEEP_RECALL"]
for alg in sbaseline_algs:
    axs[1].errorbar(
        range_numeric,
        results[alg]['efficiency'],
        yerr=results[alg]['efficiency_sd'],
        marker='o',
        linestyle='-',
        capsize=5,
        label=Custom_lagend[alg]
    )

axs[1].set_xlabel("Communication Range")
axs[1].set_ylabel("Task Efficiency (%)")
axs[1].set_title("S-Baseline Methods")
axs[1].legend()
axs[1].grid(alpha=0.3)

plt.tight_layout()
plt.show()


# =================================================
# TIME TO COMPLETION — LINE PLOTS (UPPER / LOWER)
# =================================================
fig, axs = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

# ---------- Upper: Baseline / Baseline+ ----------
for alg in baseline_algs:
    axs[0].errorbar(
        range_numeric,
        results[alg]['time'],
        yerr=results[alg]['time_sd'],
        marker='o',
        linestyle='-',
        capsize=5,
        label=Custom_lagend[alg]
    )

axs[0].set_ylabel("Time to Completion (steps)")
axs[0].set_title("Baseline Methods")
axs[0].legend()
axs[0].grid(alpha=0.3)

# ---------- Lower: S-Baseline / S-Baseline+ ----------
for alg in sbaseline_algs:
    axs[1].errorbar(
        range_numeric,
        results[alg]['time'],
        yerr=results[alg]['time_sd'],
        marker='o',
        linestyle='-',
        capsize=5,
        label=Custom_lagend[alg]
    )

axs[1].set_xlabel("Communication Range")
axs[1].set_ylabel("Time to Completion (steps)")
axs[1].set_title("S-Baseline Methods")
axs[1].legend()
axs[1].grid(alpha=0.3)

plt.tight_layout()
plt.show()
