#include <Arduino.h>
#include <micro_ros_arduino.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <geometry_msgs/msg/twist.h>
#include <std_msgs/msg/bool.h> // NEW: We need true/false (Bool) messages
#include "driver/twai.h"

// --- PIN DEFINITIONS ---
#define CAN_TX_PIN GPIO_NUM_5
#define CAN_RX_PIN GPIO_NUM_4
#define SHIELD_SENSOR_PIN 15

// --- MICRO-ROS VARIABLES ---
rcl_subscription_t cmd_vel_subscriber;
geometry_msgs__msg__Twist twist_msg;

rcl_subscription_t e_stop_subscriber; // NEW: An extra subscriber for emergency stop
std_msgs__msg__Bool e_stop_msg;       // NEW: Variable to store the emergency stop message

rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

// --- PHYSICAL DIMENSIONS ---
const float WHEEL_RADIUS = 0.1075; // 107.5 mm
const float WHEEL_BASE = 0.350;   // 350 mm

// --- SAFETY FLAGS (Split into Physical and AI) ---
volatile bool bumper_e_stop_active = false; 
bool ai_e_stop_active = false; 

// --- VESC CAN-BUS CONSTANTS ---
const uint8_t VESC_ID_RIGHT = 1; 
const uint8_t VESC_ID_LEFT = 2;  
const uint32_t VESC_CAN_PACKET_SET_RPM = 3; 
const int POLE_PAIRS = 15; // Remember to update this value from the VESC Tool!

// --- HELPER FUNCTION: Send RPM to VESC ---
void send_vesc_rpm(uint8_t controller_id, float target_rpm) {
  twai_message_t message;
  message.identifier = (VESC_CAN_PACKET_SET_RPM << 8) | controller_id;
  message.extd = 1; 
  message.rtr = 0;  
  message.data_length_code = 4; 
  
  int32_t erpm = (int32_t)(target_rpm * POLE_PAIRS);
  
  message.data[0] = (erpm >> 24) & 0xFF;
  message.data[1] = (erpm >> 16) & 0xFF;
  message.data[2] = (erpm >> 8) & 0xFF;
  message.data[3] = erpm & 0xFF;
  
  twai_transmit(&message, pdMS_TO_TICKS(1));
}

// --- KINEMATICS ---
void calculate_motor_rpm(float v, float omega, float &rpm_right, float &rpm_left) {
  float v_r = v + (omega * WHEEL_BASE / 2.0);
  float v_l = v - (omega * WHEEL_BASE / 2.0);
  rpm_right = (v_r * 60.0) / (2.0 * PI * WHEEL_RADIUS);
  rpm_left  = (v_l * 60.0) / (2.0 * PI * WHEEL_RADIUS);
}

// --- ISR: Physical shield hits an obstacle ---
void IRAM_ATTR shieldHitISR() {
  bumper_e_stop_active = true;
}

// --- NEW CALLBACK: YOLO AI sends an e-stop signal ---
void e_stop_callback(const void * msgin) {
  const std_msgs__msg__Bool * msg = (const std_msgs__msg__Bool *)msgin;
  
  // Update flag (True if danger is detected, False if the coast is clear)
  ai_e_stop_active = msg->data;

  // If AI detects danger, force the wheels to 0 RPM immediately!
  if (ai_e_stop_active) {
    send_vesc_rpm(VESC_ID_RIGHT, 0.0);
    send_vesc_rpm(VESC_ID_LEFT, 0.0);
  }
}

// --- CALLBACK: Nav2 sends driving commands ---
void cmd_vel_callback(const void * msgin) {
  const geometry_msgs__msg__Twist * msg = (const geometry_msgs__msg__Twist *)msgin;
  
  // Safety check: Ignore command if bumper is hit OR AI sees a hazard!
  if (bumper_e_stop_active || ai_e_stop_active) {
    return; 
  }

  float linear_x = msg->linear.x;
  float angular_z = msg->angular.z;

  float rpm_right = 0.0;
  float rpm_left = 0.0;
  calculate_motor_rpm(linear_x, angular_z, rpm_right, rpm_left);

  send_vesc_rpm(VESC_ID_RIGHT, rpm_right);
  send_vesc_rpm(VESC_ID_LEFT, rpm_left);
}

void setup() {
  Serial.begin(115200);

  pinMode(SHIELD_SENSOR_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(SHIELD_SENSOR_PIN), shieldHitISR, FALLING);

  twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(CAN_TX_PIN, CAN_RX_PIN, TWAI_MODE_NORMAL);
  twai_timing_config_t t_config = TWAI_TIMING_CONFIG_500KBITS();
  twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();
  
  if (twai_driver_install(&g_config, &t_config, &f_config) == ESP_OK) {
    twai_start();
  }

  set_microros_transports();
  delay(2000); 
  
  allocator = rcl_get_default_allocator();
  rclc_support_init(&support, 0, NULL, &allocator);
  rclc_node_init_default(&node, "esp32_drive_controller", "", &support);

  // Subscribe to /cmd_vel (Driving)
  rclc_subscription_init_default(
    &cmd_vel_subscriber, &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist), "/cmd_vel"
  );

  // NEW: Subscribe to /e_stop (AI Safety)
  rclc_subscription_init_default(
    &e_stop_subscriber, &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool), "/e_stop"
  );

  // NOTE: We changed the executor capacity from 1 to 2 because we now have TWO subscriptions to handle!
  rclc_executor_init(&executor, &support.context, 2, &allocator);
  rclc_executor_add_subscription(&executor, &cmd_vel_subscriber, &twist_msg, &cmd_vel_callback, ON_NEW_DATA);
  rclc_executor_add_subscription(&executor, &e_stop_subscriber, &e_stop_msg, &e_stop_callback, ON_NEW_DATA);
}

void loop() {
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));

  // Reset logic for the physical shield
  if (bumper_e_stop_active && digitalRead(SHIELD_SENSOR_PIN) == HIGH) {
    bumper_e_stop_active = false; 
  }
}