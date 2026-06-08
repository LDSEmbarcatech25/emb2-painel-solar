from machine import I2C
import time

class Hdc1080:
    def __init__(self, i2c:I2C, hdc_addr:int=0x40):
        self.i2c = i2c
        self.hdc_addr = hdc_addr

    def ler_temperatura_umidade(self):
        try:
            self.i2c.writeto(self.hdc_addr, b'\x00')
            time.sleep_ms(15)
            dados = self.i2c.readfrom(self.hdc_addr, 4)
            t_raw = (dados[0] << 8) | dados[1]
            h_raw = (dados[2] << 8) | dados[3]
            return round(((t_raw / 65536.0) * 165.0 - 40.0), 1), round(((h_raw / 65536.0) * 100.0), 1)
        except:
            return 0.0, 0.0
