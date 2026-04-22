Absolutely! Here's the **full `README.md`** as a Markdown script you can directly save into your package directory:

---

```markdown
# Robot Controller

This ROS 2 package controls a robot using pose data from an OptiTrack motion capture system via `vrpn_mocap`, and sends velocity commands to the robot. The robot receives commands through `/robot_1/cmd_vel`, and pose is received from `/vrpn_mocap/robot_1/pose`.

---

## ✅ Prerequisites

Make sure the following packages are installed and built in your workspace:

- `micro_ros_agent`
- `vrpn_mocap`
- `robot_controller` (this package)

---

## 🚀 How to Run

Follow these steps to launch the full system:

### 1. Source your workspace

```bash
cd microros_agent_ws/
source install/setup.bash
```

---

### 2. Start the micro-ROS Agent

This allows communication with your micro-ROS robot over UDP:

```bash
ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888
```

---

### 3. Launch the OptiTrack VRPN Node

This connects to your OptiTrack server to receive motion capture data:

```bash
ros2 launch vrpn_mocap client.launch.yaml server:=192.168.2.18 port:=3883
```

> 🔧 Replace `192.168.2.18` with your actual OptiTrack server IP address if different.

---

### 4. Run the Robot Controller Node

This node subscribes to the pose and publishes velocity commands:

```bash
ros2 run robot_controller robot_controller_node
```

You should see logs like:

```
[INFO] [robot_controller]: Received pose: x=1.23, y=0.45
```

---

## 🧭 Topics Used

| Topic                          | Type                         | Role         |
|-------------------------------|------------------------------|--------------|
| `/vrpn_mocap/robot_1/pose`     | `geometry_msgs/msg/PoseStamped` | Subscriber   |
| `/robot_1/cmd_vel`            | `geometry_msgs/msg/Twist`        | Publisher    |

---

## 📦 About the Package

This package includes:

- A ROS 2 Python node: `robot_controller_node`
- Logic to convert mocap pose to basic velocity commands
- QoS compatibility with `vrpn_mocap` using `BEST_EFFORT` policy

---