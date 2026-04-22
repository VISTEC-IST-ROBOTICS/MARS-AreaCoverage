#include <micro_ros_arduino.h>
#include <geometry_msgs/msg/twist.h>
#include "M5StickCPlus.h"
#include "M5_RoverC.h"
#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/float32.h>
#include "AXP192.h"
#include <esp_wifi.h>

#define BASE_NAME "ant_4"
#define NODE_NAME BASE_NAME
#define CMD_VEL_TOPIC "/" BASE_NAME "/cmd_vel"
#define VBATT_TOPIC "/" BASE_NAME "/vbatt"




#define LED_PIN 10


M5_RoverC roverc;
rcl_publisher_t publisher;
rcl_subscription_t subscriber;
geometry_msgs__msg__Twist msg;
rcl_publisher_t battery_publisher;
std_msgs__msg__Float32 battery_msg;

rclc_support_t support;
rcl_allocator_t allocator;
rclc_executor_t executor;
rcl_timer_t timer;
rcl_node_t node;

unsigned long msg_timeout = millis();

#if defined(LED_BUILTIN)
#define LED_PIN LED_BUILTIN
#else
#define LED_PIN 10
#endif

#define RCCHECK(fn) \
  { \
    rcl_ret_t temp_rc = fn; \
    if ((temp_rc != RCL_RET_OK)) { \
      Serial.print("Failed: "); \
      Serial.print(#fn); \
      error_loop(); \
    } \
  }

#define RCSOFTCHECK(fn) \
  { \
    rcl_ret_t temp_rc = fn; \
    if ((temp_rc != RCL_RET_OK)) {} \
  }

#include <stdint.h>

// FNV-1a 32-bit hash (constexpr-capable)
constexpr uint32_t uros_hash_name(const char *s, uint32_t h = 2166136261u) {
  return (*s == 0) ? h : uros_hash_name(s + 1, (h ^ (uint8_t)*s) * 16777619u);
}

// Wrapper that guarantees nonzero (avoid 0 key just in case)
constexpr uint32_t uros_client_key_from_name(const char *s) {
  uint32_t h = uros_hash_name(s);
  return (h == 0u) ? 0xFFFFFFFFu : h;
}



void error_loop() {
  for (int i = 0; i < 20; i++) {
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(100);
  }
  delay(100);     // Optional: allow time for serial to flush
  esp_restart();  // Soft reset
}

void timer_callback(rcl_timer_t *timer, int64_t last_call_time) {
  RCLC_UNUSED(last_call_time);
  if (timer != NULL) {
    float vbat = M5.Axp.GetBatVoltage();
    screen_update(vbat);
    battery_msg.data = vbat;
    RCSOFTCHECK(rcl_publish(&battery_publisher, &battery_msg, NULL));
  }
  if (millis() - msg_timeout >= 2000) {
    roverc.setSpeed(0, 0, 0);
  }
}

void screen_update(float vbat) {
  M5.Lcd.fillScreen(GREEN);

  M5.Lcd.setTextColor(BLACK, GREEN);
  M5.Lcd.setTextSize(2);

  // Display agent info
  M5.Lcd.setCursor(5, 5);
  M5.Lcd.println("Agent: " NODE_NAME);  // Macro expands to string

  M5.Lcd.setCursor(5, 30);
  M5.Lcd.println("Topic:");
  M5.Lcd.setCursor(5, 50);
  M5.Lcd.println(CMD_VEL_TOPIC);  // Macro expands to string
  M5.Lcd.setCursor(5, 70);
  M5.Lcd.print("Vbatt:");
  M5.Lcd.println(vbat);  // Macro expands to string
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
  msg_timeout = millis();
}

void setup() {

  //set_microros_wifi_transports("WIFI SSID", "WIFI PASS", "192.168.1.57", 8888);
  M5.begin();
  roverc.begin();
  M5.Lcd.fillScreen(BLACK);
  Serial.begin(115200);
  delay(1000);
  // Set unique client key (change per device!)



  M5.Lcd.setRotation(1);
  M5.Lcd.fillScreen(RED);

  M5.Lcd.setTextColor(BLACK, RED);
  M5.Lcd.setTextSize(2);

  // Display agent info
  M5.Lcd.setCursor(5, 5);
  M5.Lcd.println("Agent: " NODE_NAME);  // Macro expands to string

  M5.Lcd.setCursor(5, 30);
  M5.Lcd.println("Topic:");
  M5.Lcd.setCursor(5, 50);
  M5.Lcd.println(CMD_VEL_TOPIC);  // Macro expands to string
  M5.Lcd.setCursor(5, 70);
  M5.Lcd.print("Vbatt:");
  float vbat = M5.Axp.GetBatVoltage();
  M5.Lcd.println(vbat);  // Macro expands to string


  set_microros_wifi_transports("DualArm_2.4G", "11223344", "192.168.1.132", 8888);

  Serial.println("Set microros wifi");
  // Get MAC address safely using esp_wifi_get_mac



  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);

  delay(2000);


  allocator = rcl_get_default_allocator();

  // --- Create and modify init_options to set a fixed client_key ---
  rcl_init_options_t init_options;
  RCCHECK(rcl_init_options_init(&init_options, allocator));

  rmw_init_options_t *rmw_options = rcl_init_options_get_rmw_init_options(&init_options);

  uint32_t CLIENT_KEY = uros_client_key_from_name(NODE_NAME);

  Serial.print("CLIENT_KEY:");
  Serial.println(CLIENT_KEY,HEX);

  rmw_uros_options_set_client_key(CLIENT_KEY, rmw_options);

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

  RCCHECK(rclc_publisher_init_best_effort(
    &battery_publisher,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32),
    VBATT_TOPIC));
  // create timer,
  const unsigned int timer_timeout = 1000;
  RCCHECK(rclc_timer_init_default(
    &timer,
    &support,
    RCL_MS_TO_NS(timer_timeout),
    timer_callback));

  // Create executor
  RCCHECK(rclc_executor_init(&executor, &support.context, 2, &allocator));

  // Add subscription to executor
  RCCHECK(rclc_executor_add_subscription(&executor, &subscriber, &msg, &subscription_callback, ON_NEW_DATA));
  RCCHECK(rclc_executor_add_timer(&executor, &timer));
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
