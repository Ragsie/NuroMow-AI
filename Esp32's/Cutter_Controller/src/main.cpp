#include <Arduino.h>
#include <micro_ros_arduino.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/bool.h> // Using a simple True/False command for Blade On/Off
#include "driver/twai.h"       // ESP32 built-in CAN-bus (TWAI) driver

// --- PIN DEFINITIONS ---
#define CAN_TX_PIN GPIO_NUM_5
#define CAN_RX_PIN GPIO_NUM_4
#define BLADE_STATUS_LED 2     // On-board LED to indicate if the blade motor is spinning

// --- MICRO-ROS VARIABLES ---
rcl_subscription_t subscriber;
std_msgs__msg__Bool msg;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

// --- MOWER STATE ---
bool blade_is_running = false;
const float MAX_ALLOWED_AMPS = 15.0; // Safety threshold for the cutting motor

// --- ROS 2 CALLBACK (Triggered when Pi sends Blade On/Off command) ---
void blade_control_callback(const void * msgin) {
  const std_msgs__msg__Bool * in_msg = (const std_msgs__msg__Bool *)msgin;
  
  blade_is_running = in_msg->data;

  if (blade_is_running) {
    // TODO: Send target RPM command via CAN (TWAI) to the Single VESC to spin up the blade
    digitalWrite(BLADE_STATUS_LED, HIGH);
  } else {
    // TODO: Send 0 RPM / Brake command via CAN (TWAI) to stop the blade safely
    digitalWrite(BLADE_STATUS_LED, LOW);
  }
}

void setup() {
  Serial.begin(115200);

  // Configure status LED
  pinMode(BLADE_STATUS_LED, OUTPUT);
  digitalWrite(BLADE_STATUS_LED, LOW);

  // Setup ESP32 TWAI (CAN-bus) - VESC typically runs at 500 kbps
  twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(CAN_TX_PIN, CAN_RX_PIN, TWAI_MODE_NORMAL);
  twai_timing_config_t t_config = TWAI_TIMING_CONFIG_500KBITS();
  twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();
  
  if (twai_driver_install(&g_config, &t_config, &f_config) == ESP_OK) {
    twai_start();
  }

  // Setup Micro-ROS over Serial transport
  set_microros_serial_transports(Serial);
  delay(2000); // Give the connection time to stabilize
  
  allocator = rcl_get_default_allocator();
  rclc_support_init(&support, 0, NULL, &allocator);
  rclc_node_init_default(&node, "esp32_mower_blade_controller", "", &support);

  // Subscribe to the blade control topic (/mower/blade_enabled)
  rclc_subscription_init_default(
    &subscriber,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool),
    "/mower/blade_enabled"
  );

  rclc_executor_init(&executor, &support.context, 1, &allocator);
  rclc_executor_add_subscription(&executor, &subscriber, &msg, &blade_control_callback, ON_NEW_DATA);
}

void loop() {
  // Keep micro-ROS connection alive and check for incoming commands
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));

  // --- SAFETY OVERLOAD MONITORING ---
  if (blade_is_running) {
    // TODO: Request status frame (telemetry) from Single VESC via CAN bus
    // float current_amps = get_vesc_current();
    // 
    // if (current_amps > MAX_ALLOWED_AMPS) {
    //   // Current is too high (something is jamming the blade) - Shut down immediately!
    //   blade_is_running = false;
    //   digitalWrite(BLADE_STATUS_LED, LOW);
    //   // TODO: Send stop command to VESC
    // }
  }
}
