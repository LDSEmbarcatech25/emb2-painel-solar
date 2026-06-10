#ifndef MQTT_H
#define MQTT_H

#include <PubSubClient.h>
#include <WiFiClient.h>
#include <WiFi.h>

class MQTTService {
  private:
    WiFiClient espClient;
    PubSubClient client;

    String topico;
    String msg;

    const char* mqtt_user;
    const char* mqtt_password;

  public:
    MQTTService(const char* broker,
         const char* client_id = "ESP32",
         const char* user = nullptr,
         const char* password = nullptr);

    void conectar_mqtt();
    void sub(const char* topic);
    void pub(const char* topic, const char* message);
    void check();

    void receber_msg(char* topic, byte* payload, unsigned int length);
};

#endif