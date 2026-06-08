from machine import I2C

import struct

class Mpu6050:
    def __init__(self,i2c:I2C,mpu_addr:int=0x68,mpu_pwr_reg:int=0x6B,mpu_accel_reg:int=0x3B):
        self.i2c = i2c
        self.mpu_addr = mpu_addr
        self.mpu_pwr_reg = mpu_pwr_reg
        self.mpu_accel_reg = mpu_accel_reg

        self.i2c.writeto_mem(self.mpu_addr, self.mpu_pwr_reg, b'\x00')


    def leitura_acelerometro(self):
        try:
            raw = self.i2c.readfrom_mem(self.mpu_addr, self.mpu_accel_reg, 6)
            ax_raw, ay_raw, az_raw = struct.unpack('>hhh', raw)
            return ax_raw / 16384.0, ay_raw / 16384.0, az_raw / 16384.0
        except Exception as e:
            print(e)
            return 0.0, 0.0, 1.0