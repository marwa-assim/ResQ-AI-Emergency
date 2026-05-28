import requests
import time
import json
import random

# Simulated ESP32 Bridge for ResQ AI
# In production, the ESP32 sends a POST request here directly

WEBHOOK_URL = "http://127.0.0.1:5000/api/iot/webhook"
MAC_ADDRESS = "AA:BB:CC:DD:EE:11"  # Must exist in IoTDevice table

def simulate_esp32_telemetry():
    print("Starting ESP32 Bridge Simulation...")
    while True:
        hr = random.randint(70, 95)
        spo2 = random.randint(95, 100)
        
        payload = {
            "mac_address": MAC_ADDRESS,
            "hr": hr,
            "spo2": spo2,
            "fall_detected": False
        }
        
        # Simulate a sudden critical drop (10% chance)
        if random.random() < 0.1:
            payload["spo2"] = random.randint(80, 88)
            print("WARNING: Simulated critical SpO2 drop!")
            
        try:
            res = requests.post(WEBHOOK_URL, json=payload)
            print(f"Sent telemetry: {payload} | Response: {res.status_code}")
        except Exception as e:
            print(f"Failed to connect to ResQ: {e}")
            
        time.sleep(5)  # Send every 5 seconds

if __name__ == "__main__":
    simulate_esp32_telemetry()
