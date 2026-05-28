import ustruct

class MLX90614:
    def __init__(self, i2c, address=0x5A):
        self.i2c = i2c
        self.address = address

    def read_reg(self, reg_addr):
        data = self.i2c.readfrom_mem(self.address, reg_addr, 3)
        return ustruct.unpack('<H', data)[0]

    def read_object_temp(self):
        raw = self.read_reg(0x07)
        return (raw * 0.02) - 273.15
        
    def read_ambient_temp(self):
        raw = self.read_reg(0x06)
        return (raw * 0.02) - 273.15
