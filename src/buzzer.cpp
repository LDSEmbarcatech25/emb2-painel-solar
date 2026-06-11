#include <cstdint>
#include <Arduino.h>
class Buzzer {
    private:
        const uint8_t PINO;

    public:
        Buzzer(uint8_t pino) : PINO(pino) {
            pinMode(PINO, OUTPUT);
            digitalWrite(PINO, LOW);
        }

        void ligar() {
            digitalWrite(PINO, HIGH);
        }

        void desligar() {
            digitalWrite(PINO, LOW);
        }

        void beep(int duracao){
            ligar();
            delay(duracao);
            desligar();
        }
};