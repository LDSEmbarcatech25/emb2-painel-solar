#pragma once

#include <Arduino.h>
#include "esp_camera.h"

class CameraService {
public:
    CameraService();

    // Inicializa a câmera
    bool begin();

    // Captura um frame
    camera_fb_t* capture();

    // Libera o frame capturado (OBRIGATÓRIO)
    void release();

    // Acessa o sensor da câmera
    sensor_t* sensor();

    // Reinicia a câmera
    void restart();

private:
    camera_fb_t* fb;

    // Configuração interna da OV5640 no ESP32-S3
    camera_config_t getConfig();
};