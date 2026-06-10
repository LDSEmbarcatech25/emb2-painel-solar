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
         const char* password = nullptr)
      : client(espClient),
        mqtt_user(user),
        mqtt_password(password)
    {
      client.setServer(broker, 1883);
      client.setCallback([this](char* topic, byte* payload, unsigned int length) {
        this->receber_msg(topic, payload, length);
      });
    }

    void conectar_mqtt() {
      while (!client.connected()) {
        Serial.print("Conectando MQTT...");

        if (client.connect("ESP32", mqtt_user, mqtt_password)) {
          Serial.println(" conectado!");
        } else {
          Serial.print(" falhou, rc=");
          Serial.print(client.state());
          Serial.println(" tentando novamente em 2s");
          delay(2000);
        }
      }
    }

    void sub(const char* topic) {
      client.subscribe(topic);
    }

    void pub(const char* topic, const char* message) {
      client.publish(topic, message);
    }

    void check() {
      client.loop();
    }

    void receber_msg(char* topic, byte* payload, unsigned int length) {
      topico = String(topic);

      msg = "";
      for (unsigned int i = 0; i < length; i++) {
        msg += (char)payload[i];
      }

      Serial.print("Topico: ");
      Serial.println(topico);

      Serial.print("Mensagem: ");
      Serial.println(msg);
    }
};