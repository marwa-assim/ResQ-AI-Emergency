import requests
import time
import random

# The URL of the local Flask app's webhook
WEBHOOK_URL = "http://127.0.0.1:5000/api/iot/webhook"

def send_telemetry():
    # Generate simulated hardware sensor data
    data = {
        "mac_address": "00:1A:2B:3C:4D:5E",
        "hr": random.randint(60, 110),
        "spo2": random.randint(92, 100),
        "sys_bp": random.randint(110, 140),
        "dia_bp": random.randint(70, 90),
        "temp": round(random.uniform(36.5, 38.5), 1)
    }
    
    try:
        print(f"Sending telemetry to Kiosk: {data}")
        response = requests.post(WEBHOOK_URL, json=data)
        if response.status_code == 200:
            print("Success! Kiosk frontend should now update.")
        else:
            print(f"Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    print("Starting Kiosk Hardware Simulator...")
    print("Make sure your Flask app (app.py) is running!")
    while True:
        input("\nPress ENTER to scan a patient's vitals (or CTRL+C to quit)...")
        send_telemetry()
