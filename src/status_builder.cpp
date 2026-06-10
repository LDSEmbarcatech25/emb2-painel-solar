#include <ArduinoJson.h>

class StatusBuilder {
  private:
    StaticJsonDocument<256> doc;

  public:
    StatusBuilder& set_clima(int umidade, int temperatura) {
      JsonObject clima = doc.createNestedObject("clima");
      clima["umidade"] = umidade;
      clima["temperatura"] = temperatura;
      return *this;
    }

    StatusBuilder& set_luminosidade(int ldr_esq, int ldr_dir) {
      JsonObject luz = doc.createNestedObject("luminosidade");
      luz["LDR_Esq"] = ldr_esq;
      luz["LDR_Dir"] = ldr_dir;
      return *this;
    }

    StatusBuilder& set_angulo_painel(int angulo) {
      doc["angulo_painel"] = angulo;
      return *this;
    }

    String build() {
      String output;
      serializeJson(doc, output);
      return output;
    }
};