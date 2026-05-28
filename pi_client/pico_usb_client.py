import serial
import time
import requests
import json

# ==========================================
# WINDOWS PICO USB LISTENER
# Run this on your Windows PC!
# ==========================================

# ⚠️ CHANGE THIS to the COM port shown in the bottom-right corner of Thonny! (e.g. 'COM4', 'COM5')
SERIAL_PORT = 'COM3' 
BAUD_RATE = 115200

# Your ResQ AI Emergency Flask backend endpoint
API_ENDPOINT = "http://127.0.0.1:5000/api/wearable/data"

def main():
    print(f"🔌 Trying to connect to Pico on {SERIAL_PORT}...")
    try:
        # Note: You MUST close Thonny before running this script, because Windows 
        # only allows one program to talk to the COM port at a time!
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print("✅ Successfully connected to Raspberry Pi Pico!")
        print("Listening for sensor data...\n")
        
        while True:
            if ser.in_waiting > 0:
                # Read the data the Pico is printing securely over USB
                line = ser.readline().decode('utf-8').strip()
                
                # Check if it's our JSON format {"temp": 37.5, "hr": ...}
                if line.startswith("{") and line.endswith("}"):
                    try:
                        data = json.loads(line)
                        # Add a fake "smartwatch" ID so the Triage AI knows it's a wearable
                        data["device_id"] = "PICO-SENSOR-01"
                        
                        print(f"🌡️  Received from Sensors: {data}")
                        
                        # Send it straight into the Flask App!
                        response = requests.post(API_ENDPOINT, json=data)
                        if response.status_code == 200:
                            print("🏥 Sent to ResQ System successfully!")
                        else:
                            print(f"⚠️ App rejected data: {response.text}")
                    except Exception as e:
                        print(f"⚠️ Error formatting data: {e}")
                else:
                    print(f"PICO SYSTEM MESSAGE: {line}")
            time.sleep(0.1)
            
    except serial.SerialException:
        print(f"\n❌ ERROR: Could not open {SERIAL_PORT}.")
        print("1. Did you change 'COM3' to match your actual COM port?")
        print("2. Is Thonny still open? (You must close Thonny to free up the port for this script!)")

if __name__ == "__main__":
    main()
