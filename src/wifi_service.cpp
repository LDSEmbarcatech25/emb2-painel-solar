#include <WiFi.h>

class WIFI {
  private:
    const char* nome_rede;
    const char* senha_rede;

  public:
    WIFI(const char* ssid, const char* password) {
      nome_rede = ssid;
      senha_rede = password;
    }

    bool esta_conectado() {
      return WiFi.status() == WL_CONNECTED;
    }

    void conectar_rede() {
      if (!esta_conectado()) {
        Serial.println("Conectando...");

        WiFi.mode(WIFI_STA);
        WiFi.begin(nome_rede, senha_rede);

        while (!esta_conectado()) {
          delay(1000);
          Serial.println("Tentando conectar...");
        }
      }

      Serial.println("Conectado!");
      Serial.print("WiFi config: ");
      Serial.println(WiFi.localIP());
    }
};