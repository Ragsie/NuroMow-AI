#include <Arduino.h>
#include <micro_ros_arduino.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/bool.h> 
#include "driver/twai.h"
#include <std_msgs/msg/float32.h> // Required to send Ampere data

// --- PIN DEFINITIONS ---
// ESP32 built-in CAN-bus (TWAI) driver
#define CAN_TX_PIN GPIO_NUM_5
#define CAN_RX_PIN GPIO_NUM_4
#define BLADE_STATUS_LED 2 // On-board LED to indicate if the blade motor is spinning

// --- VESC CAN-BUS CONSTANTS ---
const uint8_t VESC_ID_CUTTER = 3;             // Make sure to set this ID in VESC Tool for the Single ESC
const uint32_t VESC_CAN_PACKET_SET_RPM = 3;   // Command to set RPM
const uint32_t VESC_CAN_PACKET_STATUS = 9;    // Status 1 contains RPM, Current, and Duty Cycle
const int POLE_PAIRS = 7;                     // Update this based on your cutter motor via VESC Tool wizard!
const float BLADE_TARGET_RPM = 3000.0;        // Desired mowing speed (adjust as needed)

// --- MICRO-ROS VARIABLES ---
rcl_subscription_t subscriber;
std_msgs__msg__Bool msg;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

// --- MICRO-ROS PUBLISHERS ---
rcl_publisher_t amps_publisher;
std_msgs__msg__Float32 amps_msg;

// --- MOWER STATE & SAFETY ---
bool blade_is_running = false;
const float MAX_ALLOWED_AMPS = 15.0; // Safety threshold for the cutting motor
float current_motor_amps = 0.0;      // Stores the live current reading from the VESC
unsigned long last_can_send = 0;     // Timer to prevent CAN-bus spamming

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

// --- HELPER FUNCTION: Read VESC Telemetry (Amps) ---
void read_vesc_telemetry() {
    twai_message_t rx_message;
    
    // Read all messages in the queue (0 = non-blocking)
    while (twai_receive(&rx_message, 0) == ESP_OK) {
        uint8_t packet_id = rx_message.identifier >> 8;
        uint8_t vesc_id = rx_message.identifier & 0xFF;

        // Only listen to the cutter motor and standard status packet
        if (vesc_id == VESC_ID_CUTTER && packet_id == VESC_CAN_PACKET_STATUS) {
            // In STATUS_1, Motor Current (Amps * 10) is located in byte 4 and 5
            int16_t amps_raw = (rx_message.data[4] << 8) | rx_message.data[5];
            current_motor_amps = (float)amps_raw / 10.0;
        }
    }
}

// --- ROS 2 CALLBACK (Triggered when Pi sends Blade On/Off command) ---
void blade_control_callback(const void * msgin) {
    const std_msgs__msg__Bool* in_msg = (const std_msgs__msg__Bool *)msgin;
    
    // Update the state flag
    blade_is_running = in_msg->data;

    if (blade_is_running) {
        digitalWrite(BLADE_STATUS_LED, HIGH);
    } else {
        // Send a direct 0 RPM / Brake command to stop the blade safely
        send_vesc_rpm(VESC_ID_CUTTER, 0.0);
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
    set_microros_transports();
    delay(2000); // Give the connection time to stabilize
    
    allocator = rcl_get_default_allocator();
    rclc_support_init(&support, 0, NULL, &allocator);
    rclc_node_init_default(&node, "esp32_mower_blade_controller", "", &support);

    // Subscribe to the blade control topic
    rclc_subscription_init_default(
        &subscriber,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool),
        "/mower/blade_enabled"
    );

    // Publisher for Cutter Motor Amps
    rclc_publisher_init_default(
        &amps_publisher,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32),
        "/hw/cutter_amps"
    );

    rclc_executor_init(&executor, &support.context, 1, &allocator);
    rclc_executor_add_subscription(&executor, &subscriber, &msg, &blade_control_callback, ON_NEW_DATA);
}

void loop() {
    rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));

    // 1. Always read incoming telemetry from the VESC
    read_vesc_telemetry();

    // 2. Safety Overload Monitoring & Keep-Alive
    if (blade_is_running) {
        
        // If current spikes above our safety limit (blade is jammed!)
        if (current_motor_amps > MAX_ALLOWED_AMPS) {
            blade_is_running = false;
            digitalWrite(BLADE_STATUS_LED, LOW);
            
            // Send multiple stop commands to ensure it halts!
            send_vesc_rpm(VESC_ID_CUTTER, 0.0);
            delay(10);
            send_vesc_rpm(VESC_ID_CUTTER, 0.0);
            
            Serial.println("E-STOP: Cutter Motor Jammed! Power cut.");
        } 
        // Normal operation: VESC requires a constant stream of commands, 
        // otherwise its internal watchdog will shut it down after 1 second.
        else {
            unsigned long current_millis = millis();
            if (current_millis - last_can_send >= 50) { // Send target RPM every 50ms (20Hz)
                send_vesc_rpm(VESC_ID_CUTTER, BLADE_TARGET_RPM);
                last_can_send = current_millis;
            }
        }
    }
    // 3. Publish live current (Amps) to ROS 2 backend
    amps_msg.data = current_motor_amps;
    rcl_publish(&amps_publisher, &amps_msg, NULL);
}
