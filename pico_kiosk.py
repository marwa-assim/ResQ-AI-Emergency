import time
import random
import machine
import json

# --- CONFIGURATION ---
MAC_ADDRESS = "00:1A:2B:3C:4D:5E"

# Setup onboard LED to indicate status
led = machine.Pin("LED", machine.Pin.OUT) if hasattr(machine.Pin.board, "LED") else machine.Pin(25, machine.Pin.OUT)

from machine import I2C, Pin
import max30102
import mlx90614 

# --- HARDWARE SETUP ---
try:
    i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)
    pulse_sensor = max30102.MAX30102(i2c)
    temp_sensor = mlx90614.MLX90614(i2c)
    hardware_connected = True
except Exception as e:
    print(json.dumps({"error": "Hardware setup failed: " + str(e)}))
    hardware_connected = False

def read_sensors():
    global hardware_connected
    
    if not hardware_connected:
        return None
        
    try:
        # 1. READ THE REAL MLX90614 TEMPERATURE SENSOR
        # Object temp is what is directly in front of the sensor (your finger/hand)
        real_temp = temp_sensor.read_object_temp()
        
        # 2. FINGER DETECTION LOGIC
        # A human body is ~36-37C. Ambient room is ~22-25C.
        # If the object temperature jumps above 30C, a human hand is near it!
        if real_temp > 30.0:
            # Hand detected! Read the real MAX30102 values
            hr, spo2 = pulse_sensor.read_hr_spo2()
            
            return {
                "mac_address": MAC_ADDRESS,
                "hr": hr,
                "spo2": spo2,
                "sys_bp": random.randint(110, 130), # BP still simulated (needs arm cuff)
                "dia_bp": random.randint(70, 85),
                "temp": round(real_temp, 1)
            }
        else:
            # No hand detected near the sensor, return zeros so kiosk stays empty
            return {
                "mac_address": MAC_ADDRESS,
                "hr": 0,
                "spo2": 0,
                "sys_bp": 0,
                "dia_bp": 0,
                "temp": round(real_temp, 1) # Still report the room temp
            }
            
    except Exception as e:
        print(json.dumps({"error": "Hardware read failed: " + str(e)}))
        hardware_connected = False
        return None

# --- MAIN LOOP ---
if __name__ == "__main__":
    while True:
        data = read_sensors()
        if data and data['hr'] > 0:
            # Only send to the software if a real hand is detected (hr > 0)
            print(json.dumps(data))
            
            # Flash LED rapidly to show successful human scan!
            for _ in range(3):
                led.on()
                time.sleep(0.05)
                led.off()
                time.sleep(0.05)
        else:
            # Just a slow blink to show it is waiting for a hand
            led.on()
            time.sleep(0.1)
            led.off()
        
        # Read the sensor every 2 seconds for faster response to a hand
        time.sleep(1.9)
