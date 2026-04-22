from setuptools import find_packages, setup
from glob import glob

package_name = 'robot_controller'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),  # Ensure launch files are included
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='meng',
    maintainer_email='meng.inventor@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'robot_controller_node = robot_controller.robot_controller_node:main',
            'robot_nav_node = robot_controller.robot_nav_node:main',
            'env_node = robot_controller.env_node:main',
            'sweeping_agent = robot_controller.sweeping_agent:main',
            'battery_monitor_node = robot_controller.battery_monitor_node:main',

            
        ],
    },
)

