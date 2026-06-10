#ifndef STATUS_BUILDER_H
#define STATUS_BUILDER_H

#include <ArduinoJson.h>

class StatusBuilder {
  private:
    StaticJsonDocument<256> doc;

  public:
    StatusBuilder();

    StatusBuilder& set_clima(int umidade, int temperatura);
    StatusBuilder& set_luminosidade(int ldr_esq, int ldr_dir);
    StatusBuilder& set_angulo_painel(int angulo);

    String build();
    void reset();
};

#endif