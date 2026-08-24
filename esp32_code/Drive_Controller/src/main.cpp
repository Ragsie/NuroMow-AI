#include <Arduino.h>
#include <micro_ros_arduino.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <geometry_msgs/msg/twist.h>
#include <geometry_msgs/msg/vector3.h> // Used for dynamic configuration updates
#include <std_msgs/msg/bool.h>
#include <std_msgs/msg/float32.h>
#include <std_msgs/msg/string.h> // Added so status_msg works
#include "driver/twai.h"

// --- PIN DEFINITIONS ---
#define CAN_TX_PIN GPIO_NUM_5
#define CAN_RX_PIN GPIO_NUM_4
#define SHIELD_SENSOR_PIN 15

// NOTE: SHIELD_SENSOR_PIN is wired as an active-low bumper input.
// If the physical sensor wiring is inverted, the emergency stop will never clear correctly.

// --- VESC CAN-BUS CONSTANTS ---
const uint8_t VESC_ID_RIGHT = 1;
const uint8_t VESC_ID_LEFT = 2;
const uint32_t VESC_CAN_PACKET_SET_RPM = 3;
const uint32_t VESC_CAN_PACKET_STATUS_5 = 15; // Includes battery voltage
const int POLE_PAIRS = 15;

// NOTE: Validate the VESC controller IDs and RPM packet format against your actual hardware.
// Different firmware builds can use different CAN packet layouts.

// --- BATTERY CONSTANTS (Adjust to your battery) ---
const float BATTERY_MAX_VOLTAGE = 21.0; // 100% for 5S Li-ion
const float BATTERY_MIN_VOLTAGE = 15.0; // 0% for 5S Li-ion
float current_battery_voltage = 20.0;   // Stores the latest measurement

// TODO: Calibrate BATTERY_MAX_VOLTAGE and BATTERY_MIN_VOLTAGE against a real voltage meter.
// The percentage logic is only as accurate as the configured battery limits.

// --- MICRO-ROS VARIABLES ---
// TODO: Add a watchdog or heartbeat message so the backend can detect a dead ESP32 connection.
rcl_publisher_t battery_publisher;
std_msgs__msg__Float32 battery_msg;

rcl_subscription_t cmd_vel_subscriber;
geometry_msgs__msg__Twist twist_msg;

rcl_subscription_t e_stop_subscriber;
std_msgs__msg__Bool e_stop_msg;

rcl_subscription_t config_subscriber;                  
geometry_msgs__msg__Vector3 config_msg;                

rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

// data transmit
rcl_publisher_t status_publisher;
std_msgs__msg__String status_msg;

// --- DYNAMIC PHYSICAL DIMENSIONS (Mutable for runtime updates) ---
float wheel_radius = 0.1075; // Default: 10.75 cm (converted to meters)
float wheel_base = 0.350;    // Default: 35.0 cm track width (converted to meters)

// --- SAFETY FLAGS ---
volatile bool bumper_e_stop_active = false;
bool ai_e_stop_active = false;


// --- HELPER FUNCTION: Send RPM to VESC ---
// WARNING: This assumes the VESC expects signed ERPM values in the format used by the VESC toolchain.
// If the firmware or controller is different, the sign or byte order may need to be adjusted.
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

// --- KINEMATICS (Using dynamic variables) ---
// NOTE: wheel_base and wheel_radius are runtime-adjustable via /robot_config.
// This is useful for calibration, but it also means the robot behavior can change unexpectedly if that topic is misconfigured.
void calculate_motor_rpm(float v, float omega, float &rpm_right, float &rpm_left) {
  float v_r = v + (omega * wheel_base / 2.0);
  float v_l = v - (omega * wheel_base / 2.0);
  rpm_right = (v_r * 60.0) / (2.0 * PI * wheel_radius);
  rpm_left  = (v_l * 60.0) / (2.0 * PI * wheel_radius);
}

// --- ISR: Physical bumper hits an obstacle ---
void IRAM_ATTR shieldHitISR() {
  bumper_e_stop_active = true;
}

// --- CALLBACK: YOLO AI sends an emergency stop signal ---
void e_stop_callback(const void * msgin) {
  const std_msgs__msg__Bool * msg = (const std_msgs__msg__Bool *)msgin;
  ai_e_stop_active = msg->data;

  if (ai_e_stop_active) {
    send_vesc_rpm(VESC_ID_RIGHT, 0.0);
    send_vesc_rpm(VESC_ID_LEFT, 0.0);
  }
}

// --- NEW CALLBACK: Update kinematics parameters dynamically at runtime ---
void config_callback(const void * msgin) {
  const geometry_msgs__msg__Vector3 * msg = (const geometry_msgs__msg__Vector3 *)msgin;
  
  if (msg->x > 0.0) {
    wheel_radius = msg->x;
  }
  if (msg->y > 0.0) {
    wheel_base = msg->y;
  }
}

// --- CALLBACK: Nav2 sends driving commands ---
void cmd_vel_callback(const void * msgin) {
  const geometry_msgs__msg__Twist * msg = (const geometry_msgs__msg__Twist *)msgin;
  
  if (bumper_e_stop_active || ai_e_stop_active) {
    return;
  }

  float linear_x = msg->linear.x;
  float angular_z = msg->angular.z;

  if (abs(linear_x) < 0.05 && abs(angular_z) > 0.0) {
    if (angular_z > 0) {
        angular_z = 0.2; 
    } else {
        angular_z = -0.2;
    }
     linear_x = (linear_x >= 0) ? 0.05 : -0.05; 
  }

  float rpm_right = 0.0;
  float rpm_left = 0.0;
  calculate_motor_rpm(linear_x, angular_z, rpm_right, rpm_left);

  send_vesc_rpm(VESC_ID_RIGHT, rpm_right);
  send_vesc_rpm(VESC_ID_LEFT, rpm_left);
}

// --- READ VESC TELEMETRY FUNCTION ---
void read_vesc_telemetry() {
    twai_message_t rx_message;
    
    while (twai_receive(&rx_message, 0) == ESP_OK) {
        uint8_t packet_id = rx_message.identifier >> 8;
        
        if (packet_id == VESC_CAN_PACKET_STATUS_5) {
            int16_t volts_raw = (rx_message.data[4] << 8) | rx_message.data[5];
            current_battery_voltage = (float)volts_raw / 10.0;
        }
    }
}

// --- CALCULATE BATTERY PERCENTAGE FUNCTION ---
float get_battery_percentage() {
    if (current_battery_voltage >= BATTERY_MAX_VOLTAGE) return 1.0;
    if (current_battery_voltage <= BATTERY_MIN_VOLTAGE) return 0.0;
    
    return (current_battery_voltage - BATTERY_MIN_VOLTAGE) / (BATTERY_MAX_VOLTAGE - BATTERY_MIN_VOLTAGE);
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

  // IMPORTANT: Publishers must be initialized AFTER rclc_node_init_default.
  // TODO: Add a publisher for a richer state message (charging, idle, emergency_stop, etc.).
  rclc_publisher_init_default(
    &battery_publisher,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32),
    "/hw/battery"
  );
  
  rclc_publisher_init_default(
    &status_publisher,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
    "/hw/drive_status"
  );

  rclc_subscription_init_default(
    &cmd_vel_subscriber, &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist), "/cmd_vel"
  );

  rclc_subscription_init_default(
    &e_stop_subscriber, &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool), "/e_stop"
  );

  rclc_subscription_init_default(
    &config_subscriber, &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Vector3), "/robot_config"
  );

  rclc_executor_init(&executor, &support.context, 3, &allocator);
  rclc_executor_add_subscription(&executor, &cmd_vel_subscriber, &twist_msg, &cmd_vel_callback, ON_NEW_DATA);
  rclc_executor_add_subscription(&executor, &e_stop_subscriber, &e_stop_msg, &e_stop_callback, ON_NEW_DATA);
  rclc_executor_add_subscription(&executor, &config_subscriber, &config_msg, &config_callback, ON_NEW_DATA);
}

void loop() {
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));

  if (bumper_e_stop_active && digitalRead(SHIELD_SENSOR_PIN) == HIGH) {
    bumper_e_stop_active = false;
  }
  
  // 1. Read the CAN bus for new battery voltage from the VESC
  read_vesc_telemetry();
  
  // 2. Convert the measured voltage to a percentage (0.0 to 1.0)
  battery_msg.data = get_battery_percentage();
  
  // 3. Send the percentage to the Python backend
  rcl_publish(&battery_publisher, &battery_msg, NULL);

  // 4. Send the robot's drive status to the backend
  // TODO: Replace the hardcoded status with a real state machine (mowing, docking, charging, stopped, error).
  status_msg.data.data = (char*)"MOWING"; // Ensures correct type casting
  status_msg.data.size = strlen(status_msg.data.data);
  rcl_publish(&status_publisher, &status_msg, NULL);
}