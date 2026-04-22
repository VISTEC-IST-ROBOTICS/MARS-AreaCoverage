#include <micro_ros_arduino.h>
#include <geometry_msgs/msg/twist.h>
#include "M5StickCPlus.h"
#include "M5_RoverC.h"
#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include "esp_system.h"  // Needed for esp_restart()
#include <std_msgs/msg/int32.h>

#define LED_PIN 10
#define NODE_NAME "ant_1"
#define CMD_VEL_TOPIC "/ant_1/cmd_vel"

M5_RoverC roverc;
rcl_publisher_t publisher;
rcl_subscription_t subscriber;
geometry_msgs__msg__Twist msg;

rclc_support_t support;
rcl_allocator_t allocator;
rclc_executor_t executor;
rcl_node_t node;

#if defined(LED_BUILTIN)
#define LED_PIN LED_BUILTIN
#else
#define LED_PIN 10
#endif

#define RCCHECK(fn) \
  { \
    rcl_ret_t temp_rc = fn; \
    if ((temp_rc != RCL_RET_OK)) { error_loop(); } \
  }
#define RCSOFTCHECK(fn) \
  { \
    rcl_ret_t temp_rc = fn; \
    if ((temp_rc != RCL_RET_OK)) {} \
  }


void error_loop() {
  for (int i = 0; i < 10; i++) {
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(100);
  }
  delay(100);     // Optional: allow time for serial to flush
  esp_restart();  // Soft reset
}

void timer_callback(rcl_timer_t *timer, int64_t last_call_time) {
  RCLC_UNUSED(last_call_time);
  if (timer != NULL) {
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
  //set_microros_wifi_transports("WIFI SSID", "WIFI PASS", "192.168.1.57", 8888);
  M5.Lcd.fillScreen(BLACK);
  delay(1000);
  M5.begin();
  roverc.begin();
  M5.Lcd.setRotation(1);
  M5.Lcd.fillScreen(RED);

  M5.Lcd.setTextColor(BLACK, RED);
  M5.Lcd.setTextSize(2);

  // Display agent info
  M5.Lcd.setCursor(5, 5);
  M5.Lcd.println("Agent: " NODE_NAME);  // Macro expands to string

  M5.Lcd.setCursor(5, 30);
  M5.Lcd.println("Topic:");
  M5.Lcd.setCursor(0, 50);
  M5.Lcd.println(CMD_VEL_TOPIC);  // Macro expands to string


  set_microros_wifi_transports("DualArm_2.4G", "11223344", "192.168.1.132", 8888);

  Serial.println("Set microros wifi");



  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);

  delay(2000);

  delay(2000);
  allocator = rcl_get_default_allocator();

  // --- Create and modify init_options to set a fixed client_key ---
  rcl_init_options_t init_options;
  RCCHECK(rcl_init_options_init(&init_options, allocator));

  rmw_init_options_t *rmw_options = rcl_init_options_get_rmw_init_options(&init_options);

  // Set unique client key (change per device!)
  rmw_uros_options_set_client_key(0x12345677, rmw_options);

  // Init rclc_support using the customized init_options
  RCCHECK(rclc_support_init_with_options(&support, 0, NULL, &init_options, &allocator));

  // Create node
  RCCHECK(rclc_node_init_default(&node, NODE_NAME, "", &support));

  // Create subscriber
  RCCHECK(rclc_subscription_init_default(
    &subscriber,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
    CMD_VEL_TOPIC));

  // Create executor
  RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));

  // Add subscription to executor
  RCCHECK(rclc_executor_add_subscription(&executor, &subscriber, &msg, &subscription_callback, ON_NEW_DATA));
}

void loop() {

  M5.update();

  if (M5.BtnB.wasPressed()) {
    Serial.println("BtnB pressed. Restarting...");
    delay(100);     // Optional: allow time for serial to flush
    esp_restart();  // Soft reset
  }

  RCCHECK(rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10)));
}
