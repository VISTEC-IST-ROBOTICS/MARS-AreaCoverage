#include <micro_ros_arduino.h>

#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <geometry_msgs/msg/twist.h>
//#include "M5StickCPlus.h"
#include "M5_RoverC.h"
const char *robot_namespace = "ant_2";

M5_RoverC roverc;

rcl_subscription_t subscriber;
geometry_msgs__msg__Twist msg;
rclc_executor_t executor;
rcl_allocator_t allocator;
rclc_support_t support;
rcl_node_t node;


#define LED_PIN 10

#define RCCHECK(fn) \
  { \
    rcl_ret_t temp_rc = fn; \
    if ((temp_rc != RCL_RET_OK)) { error_loop(); } \
  }
#define RCSOFTCHECK(fn) \
  { \
    rcl_ret_t temp_rc = fn; \
    if ((temp_rc != RCL_RET_OK)) { error_loop(); } \
  }

enum states {
  WAITING_AGENT,
  AGENT_AVAILABLE,
  AGENT_CONNECTED,
  AGENT_DISCONNECTED
} state;

void error_loop() {
  while (1) {
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(100);
  }
}

//twist message cb
void subscription_callback(const void *msgin) {
  const geometry_msgs__msg__Twist *msg = (const geometry_msgs__msg__Twist *)msgin;

  Serial.print("Received linear.x: ");
  Serial.println(msg->linear.x);
  Serial.print(" linear.y: ");
  Serial.println(msg->linear.y);
  Serial.print(" angular.z: ");
  Serial.println(msg->angular.z);
  int fw_speed = msg->linear.x * 100;
  int side_speed = msg->linear.y * 100;
  int rotate_speed = msg->angular.z * 100;
  Serial.print(fw_speed);
  Serial.print(",");
  Serial.print(side_speed);
  Serial.print(",");
  Serial.println(rotate_speed);

  roverc.setSpeed(side_speed, fw_speed, rotate_speed);
}

void setup() {
  Serial.begin(115200);

  delay(2000);
  Serial.println("System begin");
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);

  //set_microros_wifi_transports("INTERFACES", "brainvistec", "10.204.71.214", 8888);
  set_microros_wifi_transports("DualArm_2.4G", "11223344", "192.168.1.132", 8888);
  //10.204.191.69

  Serial.println("Set microros wifi");
  //M5.begin();
  roverc.begin(&Wire, 21, 22);

  //M5.Lcd.setRotation(1);
  //M5.Lcd.fillScreen(RED);



  delay(2000);
  Serial.println("System begin");

  allocator = rcl_get_default_allocator();

  //create init_options
  RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));

  // create node
  RCCHECK(rclc_node_init_default(&node, robot_namespace, "", &support));

  // Create subscriber with a dynamically constructed topic name
  std::string topic_name = "/" + std::string(robot_namespace) + "/cmd_vel";
  RCCHECK(rclc_subscription_init_default(
    &subscriber,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
    topic_name.c_str()));  // Pass the C-style string to the ROS2 function

  // Create executor
  RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));

  // Add the subscriber to the executor
  RCCHECK(rclc_executor_add_subscription(&executor, &subscriber, &msg, &subscription_callback, ON_NEW_DATA));

  state = AGENT_DISCONNECTED;
  while (true) {
    if (state == AGENT_DISCONNECTED) {

      if (rmw_uros_ping_agent(100, 1) == RMW_RET_OK) {
        state = AGENT_CONNECTED;
        digitalWrite(LED_PIN, HIGH);
        Serial.println("AGENT_CONNECTED");
        //M5.Lcd.fillScreen(GREEN);
        break;
      }
    }
    delay(100);
  }
}

void loop() {
  delay(10);
  RCCHECK(rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10)));
}
