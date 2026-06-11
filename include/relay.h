#ifndef RELAY_H
#define RELAY_H

#include <Arduino.h>

class Relay {
  private:
    int _pin;

  public:
    Relay(int pin, int value = 0);

    void ligar();
    void desligar();
};

#endif