from machine import Pin, PWM

class Servo:
    def __init__(self,pin,freq:int=50,duty:int=0):
        self.pino_pwm = PWM(Pin(pin), freq=freq, duty_u16=duty)

    def mover(self,duty:int):
        self.pino_pwm.duty_u16(duty)