#pragma once

#include <Arduino.h>
#include "camera_service.h"
#include "esp_camera.h"

class CameraService {
public:
    CameraService() : fb(nullptr) {}

    bool begin() {
        camera_config_t config = getConfig();

        esp_err_t err = esp_camera_init(&config);
        if (err != ESP_OK) {
            Serial.printf("Erro câmera: 0x%x\n", err);
            return false;
        }

        sensor_t *s = esp_camera_sensor_get();
        if (s) {
            s->set_brightness(s, 0);
            s->set_contrast(s, 0);
            s->set_saturation(s, 0);
        }

        Serial.println("Camera inicializada com sucesso!");
        return true;
    }

    camera_fb_t* capture() {
        fb = esp_camera_fb_get();

        if (!fb) {
            Serial.println("Erro ao capturar frame");
            return nullptr;
        }

        return fb;
    }

    void release() {
        if (fb) {
            esp_camera_fb_return(fb);
            fb = nullptr;
        }
    }

    sensor_t* sensor() {
        return esp_camera_sensor_get();
    }

    void restart() {
        esp_camera_deinit();
        begin();
    }

private:
    camera_fb_t* fb;

    camera_config_t getConfig() {
        camera_config_t config = {};

        // 📌 ESP32-S3 + OV5640 (ajuste se necessário)
        config.pin_pwdn  = -1;
        config.pin_reset = -1;

        config.pin_xclk = 10;

        config.pin_sccb_sda = 40;
        config.pin_sccb_scl = 39;

        config.pin_d7 = 48;
        config.pin_d6 = 11;
        config.pin_d5 = 12;
        config.pin_d4 = 14;
        config.pin_d3 = 16;
        config.pin_d2 = 18;
        config.pin_d1 = 17;
        config.pin_d0 = 15;

        config.pin_vsync = 38;
        config.pin_href  = 47;
        config.pin_pclk  = 13;

        config.xclk_freq_hz = 20000000;

        config.ledc_timer   = LEDC_TIMER_0;
        config.ledc_channel = LEDC_CHANNEL_0;

        // 📷 OV5640 (Arduino-friendly)
        config.pixel_format = PIXFORMAT_JPEG;

        if (psramFound()) {
            config.frame_size = FRAMESIZE_HD;
            config.fb_count = 2;
            config.grab_mode = CAMERA_GRAB_LATEST;
        } else {
            config.frame_size = FRAMESIZE_VGA;
            config.fb_count = 1;
        }

        return config;
    }
};