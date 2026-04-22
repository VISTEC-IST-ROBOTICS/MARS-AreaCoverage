import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from rclpy.qos import qos_profile_sensor_data

import matplotlib.pyplot as plt
from collections import deque, defaultdict
import time

class BatteryMonitor(Node):
    def __init__(self):
        super().__init__('battery_monitor')
        self.subscribers = {}
        self.history = defaultdict(lambda: deque(maxlen=200))  # Store 200 recent points
        self.start_time = time.time()

        self.get_logger().info("Waiting for topics to appear...")

        self.discovery_timer = self.create_timer(2.0, self.discover_battery_topics)

        self.enable_plotting = True
        if self.enable_plotting:
            plt.ion()
            self.fig, self.ax = plt.subplots()
            self.plot_timer = self.create_timer(0.5, self.plot_loop)

    def discover_battery_topics(self):
        topics = self.get_topic_names_and_types()
        for topic_name, types in topics:
            if topic_name.endswith('/vbatt') and topic_name not in self.subscribers:
                if 'std_msgs/msg/Float32' in types:
                    self.subscribers[topic_name] = self.create_subscription(
                        Float32,
                        topic_name,
                        lambda msg, t=topic_name: self.vbatt_callback(msg, t),
                        qos_profile_sensor_data
                    )
                    self.get_logger().info(f"Subscribed to: {topic_name}")

    def vbatt_callback(self, msg, topic_name):
        timestamp = time.time() - self.start_time
        self.history[topic_name].append((timestamp, msg.data))
        self.get_logger().info(f"{topic_name}: {msg.data:.2f} V")

    def plot_loop(self):
        if not self.history:
            return

        self.ax.clear()
        self.ax.set_title("Battery Voltage Over Time")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Voltage (V)")

        for topic_name, data in self.history.items():
            times, volts = zip(*data)
            self.ax.plot(times, volts, label=topic_name)

        self.ax.legend(loc='upper right')
        self.ax.set_ylim(0, 5)  # You can adjust voltage range
        self.ax.grid(True)
        self.fig.tight_layout()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()


def main(args=None):
    rclpy.init(args=args)
    node = BatteryMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
