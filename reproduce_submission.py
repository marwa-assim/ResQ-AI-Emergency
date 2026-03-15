import requests
import json
import time

URL = "http://127.0.0.1:5000/api/triage"

def test_submission():
    payload = {
        "patient_id": f"TEST-{int(time.time())}",
        "name": "Test Patient",
        "age": 45,
        "hr": 110,
        "spo2": 96,
        "temp": 38.5,
        "sys_bp": 140,
        "dia_bp": 90,
        "chest_pain": True,
        "breathing": False,
        "bleeding": False,
        "fainting": False,
        "chronic": False,
        "allergy": False
    }
    
    print(f"Sending Payload to {URL}...")
    try:
        r = requests.post(URL, json=payload)
        print(f"Status Code: {r.status_code}")
        print("Response Text:")
        print(r.text)
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    test_submission()
