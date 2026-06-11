#include <Arduino.h>

class Relay {
  private:
    int _pin;

  public:
    Relay(int pin, int value = 0) {
      _pin = pin;
      pinMode(_pin, OUTPUT);
      digitalWrite(_pin, value);
    }

    void ligar() {
      digitalWrite(_pin, HIGH);
    }

    void desligar() {
      digitalWrite(_pin, LOW);
    }
};