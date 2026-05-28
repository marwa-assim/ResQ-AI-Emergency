import serial
import serial.tools.list_ports
import requests
import json
import time
import sys

# The URL of your Flask app's webhook
WEBHOOK_URL = "http://127.0.0.1:5000/api/iot/webhook"

def find_pico_port():
    print("Searching for Raspberry Pi Pico...")
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # The Pico often identifies with specific VID:PID or descriptions,
        # but for simplicity we will just look for 'Serial' or let the user choose.
        print(f"Found port: {port.device} - {port.description}")
        if "USB Serial Device" in port.description or "Board in FS mode" in port.description:
            return port.device
    
    # Fallback to asking user if auto-detect fails
    if ports:
        return ports[-1].device # Just guess the last one
    return None

def main():
    print("=== ResQ AI Kiosk Serial Bridge ===")
    port = find_pico_port()
    if not port:
        print("No COM ports found. Is your Pico plugged in?")
        sys.exit(1)
        
    print(f"Connecting to Pico on {port}...")
    try:
        # The Pico usually communicates at 115200 baud
        ser = serial.Serial(port, 115200, timeout=1)
        print("Connected! Listening for telemetry...")
    except Exception as e:
        print(f"Failed to open serial port: {e}")
        sys.exit(1)

    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if not line:
                    continue
                    
                try:
                    # Try to parse the incoming line as JSON
                    data = json.loads(line)
                    print(f"\n[Pico] Received: {data}")
                    
                    # Forward it to the Flask app
                    response = requests.post(WEBHOOK_URL, json=data)
                    if response.status_code == 200:
                        print("[Bridge] Successfully beamed to Kiosk UI!")
                    else:
                        print(f"[Bridge] Flask server returned error: {response.status_code}")
                except json.JSONDecodeError:
                    # If it's not JSON, just print it as debug info
                    print(f"[Pico Debug] {line}")
                    
        except KeyboardInterrupt:
            print("\nClosing bridge...")
            ser.close()
            sys.exit(0)
        except Exception as e:
            print(f"Error reading from serial: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
