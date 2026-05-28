import machine
from machine import I2C, Pin
import network
import urequests
import time
import json
import max30102
import mlx90614

# --- CONFIGURATION ---
WIFI_SSID = "YOUR_WIFI_NAME"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
WEBHOOK_URL = "http://192.168.X.X:5000/api/iot/webhook" # Replace with your laptop's local IP
MAC_ADDRESS = "AA:BB:CC:DD:EE:FF" # ESP32 MAC Address

# --- HARDWARE SETUP ---
# ESP32 Default I2C pins: SDA = 21, SCL = 22
try:
    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
    pulse_sensor = max30102.MAX30102(i2c)
    temp_sensor = mlx90614.MLX90614(i2c)
    hardware_connected = True
except Exception as e:
    print("Hardware setup failed:", e)
    hardware_connected = False

# --- WIFI SETUP ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to Wi-Fi...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
    print('Wi-Fi Connected! IP:', wlan.ifconfig()[0])

# --- MAIN LOOP ---
connect_wifi()

while True:
    if hardware_connected:
        try:
            # Read real temp
            real_temp = temp_sensor.read_object_temp()
            
            # Finger Detection Logic
            if real_temp > 30.0:
                hr, spo2 = pulse_sensor.read_hr_spo2()
                
                payload = {
                    "mac_address": MAC_ADDRESS,
                    "hr": hr,
                    "spo2": spo2,
                    "sys_bp": 120, # Simulated BP for the watch
                    "dia_bp": 80,
                    "temp": round(real_temp, 1)
                }
                
                # Send over Wi-Fi
                print("Sending Data:", payload)
                try:
                    response = urequests.post(
                        WEBHOOK_URL,
                        json=payload,
                        headers={'Content-Type': 'application/json'}
                    )
                    response.close()
                    print("Success!")
                except Exception as req_e:
                    print("Wi-Fi POST failed:", req_e)
                    
            else:
                print("Waiting for wrist/finger... Temp:", round(real_temp, 1))
                
        except Exception as e:
            print("Sensor read failed:", e)
            
    time.sleep(2) # Read every 2 seconds
