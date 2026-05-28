from machine import Pin, I2C

# Try to initialize I2C on GP4 (SDA) and GP5 (SCL)
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)

print("Scanning I2C Bus...")
devices = i2c.scan()

if len(devices) == 0:
    print("\nNO I2C DEVICES FOUND! [Errno 5] EIO is caused by wiring.")
    print("- Check that SDA is on GP4 and SCL is on GP5")
    print("- Check that power (VIN/VCC) and Ground (GND) are securely connected.")
else:
    print("\nFound I2C devices at addresses:")
    for d in devices:
        print(f"- Decimal: {d} | Hex: {hex(d)}")
