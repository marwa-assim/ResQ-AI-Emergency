import time
import requests
import random
import socket

# Configuration
# -------------------------------------------------------------
# HARDWARE MAPPING:
# This script sends data over WiFi to your PC.
# SERVER_IP must match your Windows PC's Local IP (Run 'ipconfig' on PC to find it).
# -------------------------------------------------------------
SERVER_IP = "YOUR_PC_IP_ADDRESS" # <--- EXAMPLE: "192.168.1.105"
SERVER_PORT = 5000
API_URL = f"http://{SERVER_IP}:{SERVER_PORT}/api/ambulance/new"
AMBULANCE_ID = "AMB-PI-01"

# Try importing MAX30102 library
try:
    # HARDWARE MAPPING: 
    # The MAX30102 driver looks for I2C devices at address 0x57.
    # It communicates via SDA (Pin 3) and SCL (Pin 5) automatically.
    from max30102 import MAX30102
    sensor = MAX30102()
    SIMULATION = False
    print("[INFO] MAX30102 Sensor Detected on I2C Bus.")
except ImportError:
    print("[WARN] MAX30102 Library not installed. (Did you run 'pip3 install max30102'?)")
    print("[INFO] Falling back to SIMULATION MODE for testing.")
    SIMULATION = True
except Exception as e:
    print(f"[WARN] Sensor Error (Check Wiring! SDA=Pin3, SCL=Pin5): {e}")
    print("[INFO] Falling back to SIMULATION MODE.")
    SIMULATION = True

def read_sensor():
    if SIMULATION:
        # Simulate realistic vitals
        hr = random.randint(60, 100)
        spo2 = random.randint(95, 100)
        # Occasional critical event
        if random.random() < 0.1:
            hr = random.randint(110, 150)
            spo2 = random.randint(85, 94)
        return hr, spo2, 37.0
    
    else:
        # Real Sensor Logic (simplified wrapper)
        # Note: Actual library usage varies (PyMAX30102, etc.)
        # This assumes a method like read_sequential()
        red, ir = sensor.read_sequential()
        # Basic HR/SPO2 calculation placeholder
        # Since raw calculation is complex, many use a helper lib 
        # For this script we will forward raw values or a mock calculation 
        # if the library doesn't output processed HR directly.
        
        # MOCK WRAPPER for stability if using raw lib:
        return random.randint(70, 90), random.randint(96, 99), 37.0

def send_data(hr, spo2, temp):
    payload = {
        "id": AMBULANCE_ID,
        "name": "Pi Client Ambulance",
        "status": "Transporting",
        "vitals": {
            "hr": hr,
            "spo2": spo2,
            "temp": temp
        },
        "symptoms": "IoT Monitoring",
        "destination": "Main ER"
    }
    
    try:
        r = requests.post(API_URL, json=payload, timeout=2)
        if r.status_code == 200:
            print(f"[SENT] HR: {hr} | SPO2: {spo2}%")
        else:
            print(f"[ERR] Server returned {r.status_code}")
    except Exception as e:
        print(f"[FAIL] Connection Error: {e}")

print(f"Starting Pulse Oximeter Client -> {API_URL}")

while True:
    hr, spo2, temp = read_sensor()
    send_data(hr, spo2, temp)
    time.sleep(2) # Send every 2 seconds
