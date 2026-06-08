from machine import I2C

class Bh1750:
    def __init__(self,i2c:I2C,bh1720_addr=0x23):
        self.i2c = i2c
        self.bh1720_addr = bh1720_addr

        self.i2c.writeto(self.bh1720_addr,b'\x01')
        self.i2c.writeto(self.bh1720_addr,b'\x10')

    def ler_luminosidade(self):
        try:
            dados = self.i2c.readfrom(self.bh1720_addr, 2)
            lux = (dados[0] << 8) | dados[1]
            return round(lux / 1.2)
        except Exception as e:
            print(e)
            return None