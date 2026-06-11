#ifndef BUZZER_H
#define BUZZER_H

#include <Arduino.h>

class Buzzer {
private:
    const uint8_t PINO;

public:
    explicit Buzzer(uint8_t pino);

    void ligar();
    void desligar();
    void beep(int duracao);
};

#endif