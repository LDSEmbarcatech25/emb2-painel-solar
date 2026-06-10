#ifndef WIFI_SERVICE_H
#define WIFI_SERVICE_H

#include <WiFi.h>

class WIFI_SERVICE {
  private:
    const char* ssid;
    const char* password;

  public:
    // Construtor
    WIFI_SERVICE(const char* ssid, const char* password);

    // Conectar na rede
    void conectar();

    // Verifica conexão
    bool conectado();

    // Retorna IP
    String getIP();
};

#endif