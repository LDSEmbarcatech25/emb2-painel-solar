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

  // ponteiro para callback de mensagem
  void (*userCallback)(String, String) = nullptr;

public:
  MqttService(const char* broker, const char* client_id)
    : client(espClient) {
    client.setServer(broker, 1883);
  }

  void conectar_broker() {
    while (!client.connected()) {
      Serial.println("Conectando MQTT...");

      if (client.connect("ESP32")) {
        Serial.println("foi");
      } else {
        Serial.print("falhou, rc=");
        Serial.println(client.state());
        delay(2000);
      }
    }
  }

  void pub(const char* topic, const char* message) {
    client.publish(topic, message);
  }

  void sub(const char* topic) {
    client.subscribe(topic);
  }

  void sub_multiplos(const char* topicos[]) {
    
    for(int i = 0;i < sizeof(topicos) / sizeof(topicos[0]);i++){ 
      client.subscribe(topicos[i]);
      delay(2000);
    }
  }

  void loop() {
    client.loop();
  }

  // equivalente ao msg_log do MicroPython
  static void internal_callback(char* topic, byte* payload, unsigned int length) {
    Serial.print("Topico: ");
    Serial.println(topic);

    Serial.print("Mensagem: ");
    for (int i = 0; i < length; i++) {
      Serial.print((char)payload[i]);
    }
    Serial.println();
  }

  void reset() {
    tem_mensagem = false;
    msg = "";
    topico = "";
  }

  PubSubClient& getClient() {
    return client;
  }

  bool begin_pub(const char* topic, size_t length, bool retained = false) {
    return client.beginPublish(topic, length, retained);
  }

  size_t write_pub(const uint8_t* data, size_t len) {
    return client.write(data, len);
  }

  bool end_pub() {
    return client.endPublish();
  }
};