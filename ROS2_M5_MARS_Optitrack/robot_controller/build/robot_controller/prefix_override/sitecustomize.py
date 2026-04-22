import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/meng/microros_agent_ws/robot_controller/install/robot_controller'
