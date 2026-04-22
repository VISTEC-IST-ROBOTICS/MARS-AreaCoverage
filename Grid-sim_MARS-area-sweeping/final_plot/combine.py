import os
import yaml
import numpy as np
import matplotlib.pyplot as plt

# -------------------------------------------------
# IEEE-style font configuration
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

range_list = [
    'range_2','range_3','range_5','range_10',
    'range_20','range_30','range_40','range_50'
]

algorithms = [
    "GSR_SWEEP",
    "GSR_SWEEP_RECALL",
    "ANT_SWEEP",
    "ANT_RECALL_FILTER_SWEEP",
]

# -------------------------------------------------
# Label renaming (SEMANTIC ONLY)
# -------------------------------------------------
Custom_lagend = {
    "ANT_SWEEP": "Baseline",
    "ANT_RECALL_FILTER_SWEEP": "Baseline+",
    "GSR_SWEEP": "S-Baseline",
    "GSR_SWEEP_RECALL": "S-Baseline+",
}

# -------------------------------------------------
# Result storage
# -------------------------------------------------
results = {}

if os.path.exists(experiment_folder):
    for alg in algorithms:
        results[alg] = {
            'efficiency': [],
            'efficiency_sd': [],
            'time': [],
            'time_sd': [],
            'task_completeness': [],
            'task_completeness_sd': [],
            'time_sd_agents': [],
        }

        subfolder_path = os.path.join(experiment_folder, alg)

        for comm_range in range_list:
            folder_path = os.path.join(subfolder_path, comm_range, 'experiment_log')

            if os.path.exists(folder_path):
                all_yaml_files = read_yaml_files_in_folder(folder_path)

                eff_list, step_list = [], []
                comp_list, agent_sd_list = [], []

                for _, content in all_yaml_files.items():
                    env = content['env_statistic']
                    agents = content['agents_statistic']

                    task_cells = env['task_cells_num']
                    swept_cells = env.get('swept_cells_num', task_cells)

                    swept_sum = sum(a['swept_count'] for a in agents.values())
                    max_moves = max(a['move_count'] for a in agents.values())
                    move_counts = [a['move_count'] for a in agents.values()]

                    eff_list.append(task_cells / swept_sum * 100)
                    step_list.append(max_moves)
                    comp_list.append(swept_cells / task_cells * 100)
                    agent_sd_list.append(np.std(move_counts))

                results[alg]['efficiency'].append(np.mean(eff_list))
                results[alg]['efficiency_sd'].append(np.std(eff_list))
                results[alg]['time'].append(np.mean(step_list))
                results[alg]['time_sd'].append(np.std(step_list))
                results[alg]['task_completeness'].append(np.mean(comp_list))
                results[alg]['task_completeness_sd'].append(np.std(comp_list))
                results[alg]['time_sd_agents'].append(np.mean(agent_sd_list))


# -------------------------------------------------
# X-axis
# -------------------------------------------------
range_numeric = [int(r.split('_')[1]) for r in range_list]

baseline_algs = ["ANT_SWEEP", "ANT_RECALL_FILTER_SWEEP"]
sbaseline_algs = ["GSR_SWEEP", "GSR_SWEEP_RECALL"]

os.makedirs("figures", exist_ok=True)

# =================================================
# 1) TASK EFFICIENCY
# =================================================
fig, axs = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

for alg in baseline_algs:
    axs[0].errorbar(range_numeric, results[alg]['efficiency'],
                    yerr=results[alg]['efficiency_sd'],
                    marker='o', capsize=5, label=Custom_lagend[alg])

axs[0].set_ylabel("Task Efficiency (%)")
axs[0].set_title("Baseline Methods")
axs[0].legend()
axs[0].grid(alpha=0.3)

for alg in sbaseline_algs:
    axs[1].errorbar(range_numeric, results[alg]['efficiency'],
                    yerr=results[alg]['efficiency_sd'],
                    marker='o', capsize=5, label=Custom_lagend[alg])

axs[1].set_xlabel("Communication Range (cells)")
axs[1].set_ylabel("Task Efficiency (%)")
axs[1].set_title("S-Baseline Methods")
axs[1].legend()
axs[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig("figures/task_efficiency.png")
plt.close()


# =================================================
# 2) TIME TO COMPLETION
# =================================================
fig, axs = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

for alg in baseline_algs:
    axs[0].errorbar(range_numeric, results[alg]['time'],
                    yerr=results[alg]['time_sd'],
                    marker='o', capsize=5, label=Custom_lagend[alg])

axs[0].set_ylabel("Time to Completion (steps)")
axs[0].set_title("Baseline Methods")
axs[0].legend()
axs[0].grid(alpha=0.3)

for alg in sbaseline_algs:
    axs[1].errorbar(range_numeric, results[alg]['time'],
                    yerr=results[alg]['time_sd'],
                    marker='o', capsize=5, label=Custom_lagend[alg])

axs[1].set_xlabel("Communication Range (cells)")
axs[1].set_ylabel("Time to Completion (steps)")
axs[1].set_title("S-Baseline Methods")
axs[1].legend()
axs[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig("figures/time_to_completion.png")
plt.close()


# =================================================
# 3) TASK COMPLETENESS
# =================================================
fig, axs = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

for alg in baseline_algs:
    axs[0].errorbar(range_numeric, results[alg]['task_completeness'],
                    yerr=results[alg]['task_completeness_sd'],
                    marker='o', capsize=5, label=Custom_lagend[alg])

axs[0].set_ylabel("Task Completeness (%)")
axs[0].set_title("Baseline Methods")
axs[0].legend()
axs[0].grid(alpha=0.3)

for alg in sbaseline_algs:
    axs[1].errorbar(range_numeric, results[alg]['task_completeness'],
                    yerr=results[alg]['task_completeness_sd'],
                    marker='o', capsize=5, label=Custom_lagend[alg])

axs[1].set_xlabel("Communication Range (cells)")
axs[1].set_ylabel("Task Completeness (%)")
axs[1].set_title("S-Baseline Methods")
axs[1].legend()
axs[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig("figures/task_completeness.png")
plt.close()


# =================================================
# 4) STD OF AGENT OPERATING TIME
# =================================================
fig, axs = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

for alg in baseline_algs:
    axs[0].plot(range_numeric, results[alg]['time_sd_agents'],
                marker='o', label=Custom_lagend[alg])

axs[0].set_ylabel("Std. of Operating Time (steps)")
axs[0].set_title("Baseline Methods")
axs[0].legend()
axs[0].grid(alpha=0.3)

for alg in sbaseline_algs:
    axs[1].plot(range_numeric, results[alg]['time_sd_agents'],
                marker='o', label=Custom_lagend[alg])

axs[1].set_xlabel("Communication Range (cells)")
axs[1].set_ylabel("Std. of Operating Time (steps)")
axs[1].set_title("S-Baseline Methods")
axs[1].legend()
axs[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig("figures/agent_time_std.png")
plt.close()
