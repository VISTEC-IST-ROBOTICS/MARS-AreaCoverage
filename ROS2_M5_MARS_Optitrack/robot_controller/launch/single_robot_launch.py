from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Declare a configurable launch argument
        DeclareLaunchArgument(
            'robot_namespace',
            default_value='robot_1',
            description='Namespace for the robot'
        ),

        # Start micro-ROS agent
        # Start the micro-ROS agent using ros2 run
        ExecuteProcess(
            cmd=['ros2', 'run', 'micro_ros_agent', 'micro_ros_agent', 'udp4', '--port', '8888'],
            name='micro_ros_agent',
            output='screen',
            shell=True
        ),

        # Start VRPN MoCap client
        ExecuteProcess(
            cmd=[
                'ros2', 'launch', 'vrpn_mocap', 'client.launch.yaml',
                'server:=192.168.2.18',
                'port:=3883'
            ],
            output='screen'
        ),

        # Start robot_nav_node
        Node(
            package='robot_controller',
            executable='robot_nav_node',
            name='robot_nav_node',
            parameters=[
                {'robot_namespace': LaunchConfiguration('robot_namespace')},
                {'grid_config_path': '/home/meng/microros_agent_ws/robot_controller/robot_controller/config/gridmap.yaml'}
            ],
            output='screen'
        ),

        # Start robot_controller_node
        Node(
            package='robot_controller',
            executable='robot_controller_node',
            name='robot_controller_node',
            parameters=[
                {'robot_namespace': LaunchConfiguration('robot_namespace')}
            ],
            output='screen'
        )
    ])
