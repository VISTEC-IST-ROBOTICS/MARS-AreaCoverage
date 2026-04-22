# Experiment Logging

## Combined Data
The experiment data from `experimentlog.yaml` and agent communication range from `config.yaml` allow us to analyze the system performance effectively.

### Environment Statistics
- **Total Task Cells**: 97
- **Total Swept Cells**: 96

### Agent Statistics
| Agent ID   | Move Count | Swept Count |
|------------|------------|-------------|
| Agent 1    | 152        | 33          |
| Agent 2    | 148        | 13          |
| Agent 3    | 149        | 14          |
| Agent 4    | 159        | 23          |
| Agent 5    | 149        | 17          |

## Key Performance Metrics

### 1. Task Completeness Percentage
Percentage of task completion is calculated as:

```
Task Completeness = (Swept Cells / Task Cells) * 100
```

Substituting values:

```
Task Completeness = (96 / 97) * 100 = 98.97%
```

### 2. Move Count Standard Deviation (STD)
The standard deviation of agents' move counts reflects movement consistency and potential live-lock behavior. A higher STD may indicate inefficiencies or stuck agents.

Move counts: `[152, 148, 149, 159, 149]`

Using the standard deviation formula:

```
STD = sqrt((Σ (x - mean)^2) / N)
```

Result: **STD = 4.2**

### 3. Task Efficiency
Task efficiency measures how effectively agents are sweeping task cells:

```
Task Efficiency = Task Cells / Sum of Agent Swept Counts
```

Substituting values:

```
Task Efficiency = 97 / (33 + 13 + 14 + 23 + 17) = 0.84
```

**Interpretation**: Each agent, on average, contributes to sweeping 0.84 task cells.

### 4. Time of Completion
Time of completion is the **maximum move count** recorded at 90% task completeness:

- 90% Task Completeness:

```
90% of Task Cells = 97 * 0.9 = 87.3 ≈ 87
```

- From agent logs, the first time all agents collectively sweep 87 cells is at **Move Count = 159**.

**Result**: Time of Completion = **159 timesteps**



