#include <Arduino.h>
#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <geometry_msgs/msg/twist.h>
#include "driver/twai.h" // ESP32's indbyggede CAN-bus (TWAI) driver

// --- PIN DEFINITIONER ---
#define CAN_TX_PIN GPIO_NUM_5
#define CAN_RX_PIN GPIO_NUM_4
#define SHIELD_SENSOR_PIN 15 // Hall-sensoren fra Worx-skjoldet

// --- MICRO-ROS VARIABLER ---
rcl_subscription_t subscriber;
geometry_msgs__msg__Twist msg;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

// --- SIKKERHEDS-FLAG ---
// 'volatile' fortæller chippen, at denne variabel kan ændre sig ud af det blå (via interrupt)
volatile bool e_stop_active = false; 

// --- INTERRUPT SERVICE ROUTINE (ISR) ---
// Denne funktion kører PÅ MILLISEKUNDET skjoldet rammer noget. Den afbryder alt andet.
void IRAM_ATTR shieldHitISR() {
  e_stop_active = true;
  // TODO: Send 0 RPM direkte til VESC via CAN (TWAI) her for øjeblikkeligt stop!
}

// --- ROS 2 CALLBACK (Når Nav2 vil køre) ---
void cmd_vel_callback(const void * msgin) {
  const geometry_msgs__msg__Twist * twist_msg = (const geometry_msgs__msg__Twist *)msgin;
  
  if (e_stop_active) {
    // Ignorer ROS 2 kommandoer, hvis vi er i E-Stop!
    return; 
  }

  // Aflæs den ønskede fart (meter i sekundet) og sving (radianer i sekundet)
  float linear_x = twist_msg->linear.x;
  float angular_z = twist_msg->angular.z;

  // TODO: Matematik der omregner linear_x og angular_z til højre og venstre hjul RPM
  // TODO: Pak RPM-værdierne i en CAN (TWAI) besked og send til Autoro Dual ESC
}

void setup() {
  Serial.begin(115200);

  // 1. Opsæt Worx-skjoldets Hall-sensor som Input med Pullup
  pinMode(SHIELD_SENSOR_PIN, INPUT_PULLUP);
  
  // 2. Sæt en hardware-afbrydelse (Interrupt). Udløses når magneten flytter sig (FALLING/RISING)
  attachInterrupt(digitalPinToInterrupt(SHIELD_SENSOR_PIN), shieldHitISR, FALLING);

  // 3. Opsæt ESP32 TWAI (CAN-bus) - VESC kører typisk 500 kbps
  twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(CAN_TX_PIN, CAN_RX_PIN, TWAI_MODE_NORMAL);
  twai_timing_config_t t_config = TWAI_TIMING_CONFIG_500KBITS();
  twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();
  
  if (twai_driver_install(&g_config, &t_config, &f_config) == ESP_OK) {
    twai_start();
  }

  // 4. Opsæt Micro-ROS
  set_microros_serial_transports(Serial);
  delay(2000); // Giv forbindelsen tid til at starte
  
  allocator = rcl_get_default_allocator();
  rclc_support_init(&support, 0, NULL, &allocator);
  rclc_node_init_default(&node, "esp32_drive_controller", "", &support);

  // 5. Abonner på Nav2's fart-kommandoer
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
  // Lad Micro-ROS tjekke for nye beskeder og holde forbindelsen i live
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));

  // E-Stop Reset logik (Hvis man trækker robotten fri af forhindringen)
  if (e_stop_active && digitalRead(SHIELD_SENSOR_PIN) == HIGH) {
    // Sæt en forsinkelse ind, eller kræv en ROS 2 kommando for at ophæve E-stop
    e_stop_active = false; 
  }
}
