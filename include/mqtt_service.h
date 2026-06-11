#ifndef MQTT_SERVICE_H
#define MQTT_SERVICE_H

#include <WiFi.h>
#include <PubSubClient.h>
#include <vector>

class MqttService {
private:
  WiFiClient espClient;
  PubSubClient client;

  String topico;
  String msg;
  bool tem_mensagem = false;

  static MqttService* instance;  // usado para callback estático

  static void internal_callback(char* topic, byte* payload, unsigned int length);

public:
  MqttService(const char* broker, const char* client_id);

  void conectar_broker();

  void pub(const char* topic, const char* message);

  void sub(const char* topic);

  void sub_multiplos(const char* topicos[]);

  void loop();

  void reset();

  bool hasMessage();

  String getTopic();

  String getMessage();

  PubSubClient& getClient();

  bool begin_pub(const char* topic, size_t length, bool retained = false);
  size_t write_pub(const uint8_t* data, size_t len);
  bool end_pub();
};

#endif