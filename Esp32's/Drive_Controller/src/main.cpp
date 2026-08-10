#include <Arduino.h>
#include <micro_ros_arduino.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <geometry_msgs/msg/twist.h>
#include "driver/twai.h" // ESP32 built-in CAN-bus (TWAI) driver

// --- PIN DEFINITIONS ---
#define CAN_TX_PIN GPIO_NUM_5
#define CAN_RX_PIN GPIO_NUM_4
#define SHIELD_SENSOR_PIN 15 // Hall sensor from the Worx bumper shield

// --- MICRO-ROS VARIABLES ---
rcl_subscription_t subscriber;
geometry_msgs__msg__Twist msg;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

// --- SAFETY FLAGS ---
// 'volatile' tells the compiler that this variable can change unexpectedly (via interrupt)
volatile bool e_stop_active = false; 

// --- INTERRUPT SERVICE ROUTINE (ISR) ---
// This function executes IN MICROSECONDS when the bumper shield hits something. It halts everything else.
void IRAM_ATTR shieldHitISR() {
  e_stop_active = true;
  // TODO: Send 0 RPM directly to the VESC via CAN (TWAI) here for an immediate emergency stop!
}

// --- ROS 2 CALLBACK (Triggered when Nav2 sends movement commands) ---
void cmd_vel_callback(const void * msgin) {
  const geometry_msgs__msg__Twist * twist_msg = (const geometry_msgs__msg__Twist *)msgin;
  
  if (e_stop_active) {
    // Ignore ROS 2 commands if an E-Stop is currently active!
    return; 
  }

  // Read desired linear velocity (m/s) and angular velocity (rad/s)
  float linear_x = twist_msg->linear.x;
  float angular_z = twist_msg->angular.z;

  // TODO: Add kinematic math to convert linear_x and angular_z into right and left wheel RPM
  // TODO: Pack the RPM values into a CAN (TWAI) message and send to the Autoro Dual ESC
}

void setup() {
  Serial.begin(115200);

  // 1. Configure Worx shield Hall sensor as input with internal pullup
  pinMode(SHIELD_SENSOR_PIN, INPUT_PULLUP);
  
  // 2. Attach a hardware interrupt. Triggers when the magnet moves (FALLING edge)
  attachInterrupt(digitalPinToInterrupt(SHIELD_SENSOR_PIN), shieldHitISR, FALLING);

  // 3. Setup ESP32 TWAI (CAN-bus) - VESC typically runs at 500 kbps
  twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(CAN_TX_PIN, CAN_RX_PIN, TWAI_MODE_NORMAL);
  twai_timing_config_t t_config = TWAI_TIMING_CONFIG_500KBITS();
  twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();
  
  if (twai_driver_install(&g_config, &t_config, &f_config) == ESP_OK) {
    twai_start();
  }

  // 4. Setup Micro-ROS using the pre-compiled Arduino transport
  set_microros_serial_transports(Serial);
  delay(2000); // Give the connection time to stabilize
  
  allocator = rcl_get_default_allocator();
  rclc_support_init(&support, 0, NULL, &allocator);
  rclc_node_init_default(&node, "esp32_drive_controller", "", &support);

  // 5. Subscribe to Nav2 velocity commands
  rclc_subscription_init_default(
    &subscriber,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
    "/cmd_vel"
  );

  rclc_executor_init(&executor, &support.context, 1, &allocator);
  rclc_executor_add_subscription(&executor, &subscriber, &msg, &cmd_vel_callback, ON_NEW_DATA);
}

void loop() {
  // Let Micro-ROS check for incoming messages and keep the connection alive
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));

  // E-Stop Reset logic (When the robot is manually pulled free from an obstacle)
  if (e_stop_active && digitalRead(SHIELD_SENSOR_PIN) == HIGH) {
    // Optional: Add a debounce delay or require a specific ROS 2 command to clear the E-stop
    e_stop_active = false; 
  }
}