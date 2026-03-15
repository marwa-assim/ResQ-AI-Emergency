import requests
import json

url = "http://127.0.0.1:5000/api/triage"

# Payload mimicking Kiosk submission with no vitals
payload = {
    "patient_id": "1001",
    "name": "Sara Ahmed",
    "age": 45,
    "hr": 0,
    "spo2": 0,
    "temp": 0,
    "sys_bp": 0,
    "dia_bp": 0,
    "chest_pain": False,
    "breathing": False,
    "bleeding": False,
    "fainting": False,
    "chronic": True,
    "allergy": False
}

try:
    print(f"Sending POST to {url} with payload: {json.dumps(payload, indent=2)}")
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
except Exception as e:
    print(f"Error: {e}")
