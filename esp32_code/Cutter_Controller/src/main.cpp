#include <Arduino.h>
#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/int32.h>
#include <driver/twai.h>

#define CAN_TX_PIN GPIO_NUM_21
#define CAN_RX_PIN GPIO_NUM_22

// Autoro Single ESC (Cutter VESC ID)
#define VESC_CUTTER_ID 3

#include <std_msgs/msg/float32.h>

rcl_subscription_t subscriber;
rcl_publisher_t status_pub;                 // 🆕 [TILFØJET: ROS 2 Klipper-status udgiver]
rcl_publisher_t rpm_pub;                    // 🆕 [TILFØJET: ROS 2 Klipper-RPM udgiver]
rcl_publisher_t current_pub;                // 🆕 [TILFØJET: ROS 2 Klipper-strøm udgiver]
std_msgs__msg__Int32 msg_speed;
std_msgs__msg__Int32 status_msg;            // 🆕 [TILFØJET: ROS 2 status-meddelelse]
std_msgs__msg__Int32 rpm_msg;               // 🆕 [TILFØJET: ROS 2 RPM-meddelelse]
std_msgs__msg__Float32 current_msg;         // 🆕 [TILFØJET: ROS 2 strøm-meddelelse]
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

int32_t expected_erpm = 0;                  // 🆕 [TILFØJET: Forventet kniv-ERPM]
int32_t actual_rpm = 0;                     // 🆕 [TILFØJET: Faktisk kniv-RPM]
float actual_current = 0.0;                 // 🆕 [TILFØJET: Faktisk kniv-strøm Ampere]
bool cutter_blocked = false;                // 🆕 [TILFØJET: Overbelastning / Blokeret-flag]
unsigned long last_status_publish = 0;

void init_twai() {
    twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(CAN_TX_PIN, CAN_RX_PIN, TWAI_MODE_NORMAL);
    twai_timing_config_t t_config = TWAI_TIMING_CONFIG_500KBITS();
    twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();

    if (twai_driver_install(&g_config, &t_config, &f_config) == ESP_OK) {
        twai_start();
    }
}

// Indstil knivens omdrejningstal (ERPM)
void set_cutter_rpm(int32_t erpm) {
    twai_message_t message;
    message.identifier = (0x03 << 8) | VESC_CUTTER_ID; // CAN_PACKET_SET_RPM
    message.extd = 1;
    message.data_length_code = 4;

    message.data[0] = (erpm >> 24) & 0xFF;
    message.data[1] = (erpm >> 16) & 0xFF;
    message.data[2] = (erpm >> 8) & 0xFF;
    message.data[3] = erpm & 0xFF;

    twai_transmit(&message, pdMS_TO_TICKS(10));
}

// 🆕 [TILFØJET: Overvågning af VESC telemetry til status, RPM og strømmåling]
void read_vesc_telemetry() {
    twai_message_t rx_msg;
    // Læs CAN frames
    while (twai_receive(&rx_msg, 0) == ESP_OK) {
        uint32_t id = rx_msg.identifier;
        uint8_t cmd = (id >> 8) & 0xFF;
        uint8_t sender_id = id & 0xFF;

        if (sender_id == VESC_CUTTER_ID) {
            if (cmd == 0x09) { // CAN_PACKET_STATUS_1 (RPM, Current, Duty)
                int32_t rpm = (rx_msg.data[0] << 24) | (rx_msg.data[1] << 16) | (rx_msg.data[2] << 8) | rx_msg.data[3];
                float current = ((int16_t)((rx_msg.data[4] << 8) | rx_msg.data[5])) / 10.0;

                // Gem værdier til måling
                actual_rpm = rpm / 10; // VESC rapporterer ERPM, vi dividerer med 10 (for en 10-polet motor) til reel RPM
                actual_current = current;

                // BLOKERINGSTEST: Hvis kniven skal køre (ERPM > 1000),
                // men faktisk RPM er under 100 (kniven står stille/sidder fast)
                // og strømmen samtidigt er tårnhøj (> 15.0A), så er klipperen blokeret!
                if (expected_erpm > 1000 && abs(rpm) < 100 && current > 15.0) {
                    cutter_blocked = true;
                    set_cutter_rpm(0); // Nødstop af klipperen omgående for at skåne motor og legetøj!
                    actual_rpm = 0;
                    actual_current = 0.0;
                }
            }
        }
    }

    // Publicer klipperstatus, RPM og strøm til ROS 2 en gang i sekundet
    unsigned long now = millis();
    if (now - last_status_publish >= 1000) {
        last_status_publish = now;

        // 🆕 Udgiv status, RPM og strøm
        status_msg.data = cutter_blocked ? 2 : (expected_erpm > 0 ? 1 : 0);
        rpm_msg.data = actual_rpm;
        current_msg.data = actual_current;

        rcl_publish(&status_pub, &status_msg, NULL);
        rcl_publish(&rpm_pub, &rpm_msg, NULL);
        rcl_publish(&current_pub, &current_msg, NULL);
    }
}

void subscription_callback(const void * msvgin) {
    const std_msgs__msg__Int32 * msg = (const std_msgs__msg__Int32 *)msvgin;
    expected_erpm = msg->data;

    // Hvis vi modtager en hastighedskommando på 0 (stop klipperen),
    // kan vi "re-arme" systemet og fjerne blokeringsfejlen.
    if (expected_erpm == 0) {
        cutter_blocked = false;
    }

    if (!cutter_blocked) {
        set_cutter_rpm(expected_erpm);
    } else {
        set_cutter_rpm(0); // Forbliv slukket indtil systemet nulstilles af brugeren (ved at sende 0)
    }
}

void setup() {
    init_twai();
    set_microros_transports();

    allocator = rcl_get_default_allocator();
    rclc_support_init(&support, 0, NULL, &allocator);
    rclc_node_init_default(&node, "cutter_controller", "", &support);

    // Initialiser ROS 2 abonnement på /cutter/speed
    rclc_subscription_init_default(
        &subscriber,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
        "/cutter/speed"
    );

    // Initialiser ROS 2 udgiver på /cutter/status 🆕 [TILFØJET: Udgiver til klipperstatus]
    rclc_publisher_init_default(
        &status_pub,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
        "/cutter/status"
    );

    // Initialiser ROS 2 udgiver på /cutter/rpm 🆕 [TILFØJET: Udgiver til klipper RPM]
    rclc_publisher_init_default(
        &rpm_pub,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
        "/cutter/rpm"
    );

    // Initialiser ROS 2 udgiver på /cutter/current 🆕 [TILFØJET: Udgiver til klipper strømstyrke]
    rclc_publisher_init_default(
        &current_pub,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32),
        "/cutter/current"
    );

    rclc_executor_init(&executor, &support.context, 1, &allocator);
    rclc_executor_add_subscription(&executor, &subscriber, &msg_speed, &subscription_callback, ON_NEW_DATA);
}

void loop() {
    rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
    read_vesc_telemetry(); // 🆕 [TILFØJET: Polling af VESC CAN statusbeskeder]
    delay(10);
}