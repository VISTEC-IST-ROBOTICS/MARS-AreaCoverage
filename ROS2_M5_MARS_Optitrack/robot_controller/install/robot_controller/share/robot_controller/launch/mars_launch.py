import yaml
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    config_path = '/home/meng/microros_agent_ws/robot_controller/robot_controller/config/config.yaml'

    # Launch argument to control terminal usage
    use_terminals_arg = DeclareLaunchArgument(
        'use_terminals',
        default_value='true',
        description='Launch sweeping_agent nodes in new terminals'
    )

    use_terminals = LaunchConfiguration('use_terminals')

    # Load the YAML config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    agents = config.get('agents', {})

    launch_description = [use_terminals_arg]

    # Micro-ROS agent
    launch_description.append(
        ExecuteProcess(
            cmd=['ros2', 'run', 'micro_ros_agent', 'micro_ros_agent', 'udp4', '--port', '8888'],
            name='micro_ros_agent',
            output='screen',
            shell=True
        )
    )

    # VRPN client
    launch_description.append(
        ExecuteProcess(
            cmd=[
                'ros2', 'launch', 'vrpn_mocap', 'client.launch.yaml',
                'server:=192.168.2.18',
                'port:=3883'
            ],
            output='screen'
        )
    )

    # Environment node
    launch_description.append(
        Node(
            package='robot_controller',
            executable='env_node',
            name='env_node',
            parameters=[{'config_path': config_path}],
            output='screen'
        )
    )

    # Per-agent nodes
    for agent_name in agents:
        node_name = f"{agent_name}_sweeping_agent"

        # robot_controller_node (in-screen)
        launch_description.append(
            Node(
                package='robot_controller',
                executable='robot_controller_node',
                name=f"{agent_name}_controller_node",
                parameters=[{'robot_namespace': agent_name}],
                output='log',
                arguments=['--ros-args', '--log-level', f'{agent_name}_controller_node:=error']

            )
        )

        # Conditional terminal or inline launch
        launch_description.append(
            ExecuteProcess(
                cmd=[
                    'bash', '-c',
                    f"""
                    if [ "$USE_TERMINALS" = "true" ]; then
                        gnome-terminal -- bash -c 'ros2 run robot_controller sweeping_agent \
                        --ros-args -r __node:={node_name} \
                        -p robot_namespace:={agent_name} \
                        -p config_path:={config_path}; exec bash'
                    else
                        ros2 run robot_controller sweeping_agent \
                        --ros-args -r __node:={node_name} \
                        -p robot_namespace:={agent_name} \
                        -p config_path:={config_path}
                    fi
                    """
                ],
                output='screen',
                shell=True,
                additional_env={'USE_TERMINALS': use_terminals}
            )
        )

    return LaunchDescription(launch_description)
