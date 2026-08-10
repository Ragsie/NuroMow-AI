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

// --- PHYSICAL DIMENSIONS (in meters) ---
const float WHEEL_RADIUS = 0.112; 
const float WHEEL_BASE = 0.403;

// --- KINEMATICS: ROS 2 to RPM ---
void calculate_motor_rpm(float v, float omega, float &rpm_right, float &rpm_left) {
  // 1. Calculate the speed of each wheel in m/s
  float v_r = v + (omega * WHEEL_BASE / 2.0);
  float v_l = v - (omega * WHEEL_BASE / 2.0);

  // 2. Convert m/s to revolutions per minute (RPM)
  rpm_right = (v_r * 60.0) / (2.0 * PI * WHEEL_RADIUS);
  rpm_left  = (v_l * 60.0) / (2.0 * PI * WHEEL_RADIUS);
}

// --- ODOMETRY: RPM back to ROS 2 ---
void calculate_robot_velocity(float rpm_right, float rpm_left, float &v, float &omega) {
  // 1. Convert RPM back to m/s for each wheel
  float v_r = (rpm_right * 2.0 * PI * WHEEL_RADIUS) / 60.0;
  float v_l = (rpm_left * 2.0 * PI * WHEEL_RADIUS) / 60.0;

  // 2. Calculate the robot's true forward speed (v) and turning speed (omega)
  v = (v_r + v_l) / 2.0;
  omega = (v_r - v_l) / WHEEL_BASE;
}

// --- SAFETY FLAGS ---
// 'volatile' tells the compiler that this variable can change unexpectedly (via interrupt)
volatile bool e_stop_active = false; 

// --- INTERRUPT SERVICE ROUTINE (ISR) ---
// This function executes IN MICROSECONDS when the bumper shield hits something. It halts everything else.
void IRAM_ATTR shieldHitISR() {
  e_stop_active = true;
  // TODO: Send 0 RPM directly to the VESC via CAN (TWAI) here for an immediate emergency stop!
}

// --- VESC CAN-BUS CONSTANTS ---
const uint8_t VESC_ID_RIGHT = 1; // Change if your right motor has a different CAN ID in VESC Tool
const uint8_t VESC_ID_LEFT = 2;  // Change if your left motor has a different CAN ID in VESC Tool
const uint32_t VESC_CAN_PACKET_SET_RPM = 3; // VESC command ID for setting RPM
const int POLE_PAIRS = 15; // TODO: Opdater dette tal, når du har fundet det i VESC Tool!

// --- HELPER FUNCTION: Send RPM to VESC ---
void send_vesc_rpm(uint8_t controller_id, float target_rpm) {
  twai_message_t message;
  
  // VESC uses 29-bit Extended CAN IDs. The format is: (Command ID << 8) | Controller ID
  message.identifier = (VESC_CAN_PACKET_SET_RPM << 8) | controller_id;
  message.extd = 1; // 1 = Extended ID (29-bit)
  message.rtr = 0;  // 0 = Standard data frame
  message.data_length_code = 4; // We are sending a 32-bit integer (4 bytes)
  
  // Calculate ERPM (Electrical RPM) by multiplying physical RPM with Pole Pairs
  int32_t erpm = (int32_t)(target_rpm * POLE_PAIRS);
  
  // VESC expects data in Big Endian format (highest byte first)
  message.data[0] = (erpm >> 24) & 0xFF;
  message.data[1] = (erpm >> 16) & 0xFF;
  message.data[2] = (erpm >> 8) & 0xFF;
  message.data[3] = erpm & 0xFF;
  
  // Send the message on the CAN bus (Wait max 1 tick if bus is busy)
  twai_transmit(&message, pdMS_TO_TICKS(1));
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

  // 1. Add kinematic math to convert linear_x and angular_z into right and left wheel RPM
  float rpm_right = 0.0;
  float rpm_left = 0.0;
  calculate_motor_rpm(linear_x, angular_z, rpm_right, rpm_left);

  // 2. Pack the RPM values into a CAN (TWAI) message and send to the Autoro Dual ESC
  send_vesc_rpm(VESC_ID_RIGHT, rpm_right);
  send_vesc_rpm(VESC_ID_LEFT, rpm_left);
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
  set_microros_transports();
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