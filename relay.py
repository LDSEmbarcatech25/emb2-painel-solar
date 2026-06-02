from machine import Pin

class Relay:
    def __init__(self,pin:int,value:int=0):
        self.pin = Pin(pin, Pin.OUT,value=value)

    def ligar(self):
        self.pin.value(1)

    def desligar(self):
        self.pin.value(0)